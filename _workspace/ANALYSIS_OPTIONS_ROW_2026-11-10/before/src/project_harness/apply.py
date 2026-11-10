"""PH-051-08: bounded, journaled *product* apply (not automatic execution).

Only the trusted host kernel may call this after the independent sandbox verifier.
The agent never receives this module or a writable canonical mount.  A journal
and immutable backups live in the already-separated per-Run execution root;
no project-local control artifact is published until the product commit is
complete.  PH-051-09 will provide the governed CLI/Run orchestration and
PH-051-10 handles orphan cleanup across Run lifecycles.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
from typing import Any, Callable, Iterator, Mapping

from .errors import SafetyViolation, ValidationFailure
from .execution_roots import _load_bound_sources
from .executors.result import MAX_AGENT_RESULT_BYTES, MAX_PERSISTED_LOG_BYTES, _ref_ids
from .hashing import sha256_bytes
from .safety import (EXCLUDED_PRODUCT_ROOT_DIRS, EXCLUDED_PRODUCT_ROOT_FILES,
                     safe_disposable_baseline_revision, scan_changed_product_secrets,
                     scan_exact_secret)
from .serialization import canonical_json_bytes, load_data
from .util import utc_now
from .workspace import (check_control_plane, diff_snapshots,
                        record_phase_boundary, secure_read_agent_result, validate_scope)

_RUN = re.compile(r"RUN-[A-Z0-9]+(?:-[A-Z0-9]+)*(?:@[1-9][0-9]*)?\Z")
_SHA = re.compile(r"sha256:[a-f0-9]{64}\Z")
_TREE = re.compile(r"tree:sha256:[a-f0-9]{64}\Z")
_MAX_FILES = 10000  # fail closed on exceptionally large unbounded write sets
_MAX_CHANGED_FILE_BYTES = 64 * 1024 * 1024  # bounded staging/restore, not a DLP limit
_MAX_PATH_BYTES = 4096
_JOURNAL = "apply-journal"
_JOURNAL_VERSION = 1


class ApplyFailure(ValidationFailure):
    """Bounded reason-code contract; no supplied secret values in diagnostics."""
    def __init__(self, reason_code: str, message: str):
        super().__init__(message, {"reason_code": reason_code})
        self.reason_code = reason_code


def _reject(reason: str, description: str) -> None:
    raise ApplyFailure(reason, description)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _exclusive_write(path: Path, source: bytes, *, mode: int = 0o600) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as out:
            out.write(source)
            out.flush()
            os.fsync(out.fileno())
    finally:
        os.close(fd)
    _fsync_dir(path.parent)


def _replace_json(path: Path, content: dict[str, Any]) -> None:
    temp = path.parent / ("." + path.name + ".writing")
    if temp.exists() or temp.is_symlink():
        _reject("APPLY_FAILED_RECOVERABLE", "Unrecovered journal temporary record")
    _exclusive_write(temp, canonical_json_bytes(content))
    os.replace(temp, path)
    _fsync_dir(path.parent)


def _regular_bytes(path: Path, *, size_limit: int | None = None) -> bytes:
    """Pinned no-follow bounded read (also rejects hardlinks and unsafe inode swaps)."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        _reject("SCOPE_VIOLATION", "Nonregular or linked file in apply input")
    if size_limit is not None and before.st_size > size_limit:
        _reject("SCOPE_VIOLATION", "Oversized bounded apply input")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            _reject("SCOPE_VIOLATION", "Apply source changed while opening")
        chunks = []
        total = 0
        while part := os.read(fd, 65536):
            chunks.append(part)
            total += len(part)
            if size_limit is not None and total > size_limit:
                _reject("SCOPE_VIOLATION", "Oversized bounded apply input")
        after = os.fstat(fd)
        if (opened.st_size, opened.st_mtime_ns, opened.st_ino, opened.st_dev) != (after.st_size, after.st_mtime_ns, after.st_ino, after.st_dev):
            _reject("BASELINE_CHANGED", "Apply source changed during read")
        if (path.lstat().st_ino, path.lstat().st_dev) != (opened.st_ino, opened.st_dev):
            _reject("BASELINE_CHANGED", "Apply source path was replaced")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _file_sha(path: Path) -> str:
    h = hashlib.sha256()
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        _reject("SCOPE_VIOLATION", "Unsafe file in product apply tree")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        opened = os.fstat(fd)
        if (opened.st_ino, opened.st_dev) != (before.st_ino, before.st_dev) or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            _reject("SCOPE_VIOLATION", "Unsafe product file during scan")
        while part := os.read(fd, 1024 * 1024):
            h.update(part)
        after = os.fstat(fd)
        if (opened.st_size, opened.st_mtime_ns, opened.st_dev, opened.st_ino) != (after.st_size, after.st_mtime_ns, after.st_dev, after.st_ino):
            _reject("BASELINE_CHANGED", "Product file changed during scan")
        if (path.lstat().st_ino, path.lstat().st_dev) != (opened.st_ino, opened.st_dev):
            _reject("BASELINE_CHANGED", "Product entry changed during scan")
        return h.hexdigest()
    finally:
        os.close(fd)


def _valid_rel(name: str) -> None:
    if (not isinstance(name, str) or not name or name.startswith("/") or "\\" in name or ":" in name or
        "\x00" in name or len(name.encode("utf-8")) > _MAX_PATH_BYTES or
        any(p in ("", ".", "..") for p in name.split("/")) or
        any(ord(c) < 32 or ord(c) == 127 for c in name)):
        _reject("SCOPE_VIOLATION", "Unsafe or noncanonical relative product path")
    parts = name.split("/")
    if any(part in {".harness", ".git"} for part in parts) or parts[0] in EXCLUDED_PRODUCT_ROOT_DIRS or parts[0] in EXCLUDED_PRODUCT_ROOT_FILES:
        _reject("SCOPE_VIOLATION", "Path targets protected/ignored product-control boundary")
    if any(part in {"__pycache__", ".pytest_cache", "node_modules", ".venv"} for part in parts):
        _reject("SCOPE_VIOLATION", "Excluded generated path in disposable product")


def _scan_files(root: Path, *, disposable: bool) -> dict[str, dict[str, Any]]:
    """Enumerate regular files; reject *all* unexpected objects in disposable tree.

    The same named-file digest representation is used by independent verifier.
    Canonical distribution/control exclusions are excluded only at canonical root.
    """
    if root.is_symlink() or not root.is_dir():
        _reject("SCOPE_VIOLATION", "Product root must be an independent directory")
    records: dict[str, dict[str, Any]] = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        base = Path(current)
        kept = []
        for name in sorted(dirs):
            rel = (base / name).relative_to(root).as_posix()
            info = (base / name).lstat()
            if not disposable and base == root and name in EXCLUDED_PRODUCT_ROOT_DIRS:
                continue
            if not disposable and name in {"__pycache__", ".pytest_cache"}:
                continue
            _valid_rel(rel)
            if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
                _reject("SCOPE_VIOLATION", "Non-directory or symlink in product tree")
            kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            rel = (base / name).relative_to(root).as_posix()
            if not disposable and (name == ".DS_Store" or (base == root and name in EXCLUDED_PRODUCT_ROOT_FILES)):
                continue
            _valid_rel(rel)
            meta = (base / name).lstat()
            if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1:
                _reject("SCOPE_VIOLATION", "Special file, symlink or hardlink in product")
            # Only ordinary file modes; no SUID/SGID/sticky or mode-only changes.
            if stat.S_IMODE(meta.st_mode) not in {0o644, 0o755, 0o600, 0o700, 0o664, 0o775}:
                _reject("SCOPE_VIOLATION", "Unsupported product file mode")
            records[rel] = {"sha256": _file_sha(base / name), "size": meta.st_size,
                            "mode": stat.S_IMODE(meta.st_mode)}
            if len(records) > _MAX_FILES:
                _reject("SCOPE_VIOLATION", "Excessive product file count")
    return records


def _compatible_snapshot(files: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {name: {"sha256": meta["sha256"], "size": meta["size"]} for name, meta in files.items()}


def _validate_verified(verification: Mapping[str, Any], current: dict[str, dict[str, Any]],
                       before: dict[str, dict[str, Any]]) -> str:
    if (not isinstance(verification, dict) or verification.get("status") != "PASS" or
        verification.get("reason_code") is not None or verification.get("apply_allowed") is not False or
        verification.get("verified_subjects") != ["RUNTIME_TASK_VERIFICATION"]):
        _reject("VERIFICATION_FAILED", "Independent sandbox PASS result is required")
    results = verification.get("command_results")
    if not isinstance(results, list) or not results or any(
        not isinstance(x, dict) or x.get("exit_code") != 0 or x.get("termination_reason") != "EXITED"
        for x in results
    ):
        _reject("VERIFICATION_FAILED", "Independent commands were not successful")
    if verification.get("verified_product_files") != _compatible_snapshot(current):
        _reject("VERIFICATION_FAILED", "Disposable product changed after independent verification")
    if verification.get("diff") != diff_snapshots(_compatible_snapshot(before), _compatible_snapshot(current)):
        _reject("VERIFICATION_FAILED", "Verified file-level diff does not match current product")
    # Hash the exact result contract, never the volatile Python object identity.
    return "sha256:" + sha256_bytes(canonical_json_bytes(verification))


def _evidence_id(run_ref: str) -> str:
    base, sep, rev = run_ref.partition("@")
    return "EVD-APPLY-" + base + "-R" + (rev if sep else "1")


def _runtime(project: Path, execution_root: Path) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    project = project.resolve(strict=True)
    execution_root = Path(execution_root).absolute()
    if not _RUN.fullmatch(execution_root.name) or project == execution_root or project in execution_root.parents or execution_root in project.parents:
        _reject("SCOPE_VIOLATION", "Apply root must be a separate exact per-Run execution tree")
    for ancestor in (execution_root, *execution_root.parents):
        if ancestor.is_symlink():
            _reject("SCOPE_VIOLATION", "Symlink ancestor in execution root")
    if not execution_root.is_dir() or not (execution_root / "product").is_dir() or not (execution_root / "control").is_dir():
        _reject("SCOPE_VIOLATION", "Incomplete or missing disposable execution root")
    state = load_data(project / ".harness/state/CURRENT_STATE.yaml").get("state")
    active = state.get("active_run") if isinstance(state, dict) else None
    if not isinstance(active, dict) or active.get("run_ref") != execution_root.name or not _RUN.fullmatch(execution_root.name):
        _reject("VERIFICATION_FAILED", "Apply Run is not the current reserved Run")
    binding_path = project / ".harness/runtime/EXECUTION_BINDINGS" / (execution_root.name + ".yaml")
    if binding_path.is_symlink() or not binding_path.is_file():
        _reject("VERIFICATION_FAILED", "Missing exact trusted execution binding")
    binding = load_data(binding_path).get("execution_binding")
    if (not isinstance(binding, dict) or binding.get("run_ref") != active["run_ref"] or
        any(binding.get(k) != active.get(k) for k in ("task_ref", "run_plan_ref", "prompt_bundle_ref", "context_packet_ref"))):
        _reject("VERIFICATION_FAILED", "Stale or mismatched Run binding")
    # The trusted PH-051-04 root builder fixed this directory, never an agent path.
    if binding.get("execution_ref") != f"{binding.get('project_id')}/executions/{active['run_ref']}":
        _reject("VERIFICATION_FAILED", "Run execution reference mismatch")
    if execution_root.parent.name != "executions" or execution_root.parent.parent.name != binding.get("project_id"):
        _reject("VERIFICATION_FAILED", "Execution root does not match project/Run identity")
    if binding.get("runtime_root_digest") != "sha256:" + sha256_bytes(str(execution_root.parent.parent.parent).encode()):
        _reject("VERIFICATION_FAILED", "Execution root is not bound to this configured runtime root")
    # PH-051-04 binds canonical control and the copied projection by hashes.
    sources, refs = _load_bound_sources(project, active)
    if binding.get("projection_sources") != refs or binding.get("projection_files") != {
        name: "sha256:" + sha256_bytes(value) for name, value in sources.items()
    }:
        _reject("VERIFICATION_FAILED", "Run projection no longer matches canonical JIT")
    for name, value in sources.items():
        if _regular_bytes(execution_root / "control" / name, size_limit=max(len(value), 1)) != value:
            _reject("VERIFICATION_FAILED", "Run control projection was modified")
    task = load_data(execution_root / "control/task-contract.yaml").get("task")
    if not isinstance(task, dict) or f"{task.get('id')}@{task.get('revision')}" != active.get("task_ref"):
        _reject("VERIFICATION_FAILED", "Run Task Contract mismatch")
    return active, binding, project, execution_root


def _check_secrets(project: Path, active: dict[str, Any], task: dict[str, Any],
                   source: Path, changed: list[str], diff: dict[str, list[str]],
                   secret_values: Mapping[str, str]) -> None:
    if (not isinstance(secret_values, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v
                                                    for k, v in secret_values.items())):
        _reject("SECRET_REFERENCE_MISSING", "Missing or invalid bound secret values")
    # Profile refs, if configured, are exact kernel-trusted fields; caller may
    # not suppress configured env-secret names by passing an empty dictionary.
    lock = load_data(project / ".harness/config/PROJECT_LOCK.yaml").get("project_lock", {})
    execution = lock.get("execution", {})
    if execution.get("mode") != "LOCAL_AUTOMATIC":
        _reject("VERIFICATION_FAILED", "Automatic apply is not active in accepted project policy")
    ref = execution.get("adapter_profile_ref")
    if not isinstance(ref, str) or not re.fullmatch(r"ADP-[A-Z0-9-]+@[1-9][0-9]*", ref):
        _reject("SECRET_REFERENCE_MISSING", "Missing exact adapter profile for secret policy")
    profile_path = project / ".harness/config/ADAPTERS" / (ref + ".yaml")
    if profile_path.is_symlink() or not profile_path.is_file():
        _reject("SECRET_REFERENCE_MISSING", "Exact adapter secret reference record missing")
    profile = load_data(profile_path).get("agent_adapter_profile", {})
    expected_names = {s[4:] for s in profile.get("secret_environment_refs", []) if isinstance(s, str) and s.startswith("ENV:")}
    if set(secret_values) != expected_names or len(expected_names) != len(profile.get("secret_environment_refs", [])):
        _reject("SECRET_REFERENCE_MISSING", "Secret values not exactly bound to adapter references")
    # No declarative product secret scan policy exists in v0.5.1 contracts.
    # Never silently ignore a future mandatory scan contract.
    if any("secret_scan" in obj or "secret_scan_policy" in obj for obj in (task, execution)):
        _reject("SCOPE_VIOLATION", "Unsupported mandatory project secret scan policy")
    if changed and scan_changed_product_secrets(source, changed, dict(secret_values)):
        _reject("SECRET_LEAK_DETECTED", "Exact supplied secret detected in changed product files")
    ids = _ref_ids(active["run_ref"])
    exec_path = project / ".harness/runtime/EXECUTION_RESULTS" / (ids["execution"] + ".yaml")
    if exec_path.is_symlink() or not exec_path.is_file():
        _reject("RESULT_INVALID", "Missing kernel-owned normalized execution result")
    rec = load_data(exec_path).get("execution_result", {})
    if (rec.get("id") != ids["execution"] or rec.get("run_ref") != active["run_ref"].split("@")[0] + "@" +
            (active["run_ref"].rsplit("@", 1)[1] if "@" in active["run_ref"] else "1") or
        rec.get("agent_result_ref") != ids["agent"] or
        rec.get("adapter_profile_ref") != execution.get("adapter_profile_ref") or
        rec.get("sandbox_profile_ref") != execution.get("sandbox_profile_ref") or
        rec.get("result_status") != "COMPLETED" or
        rec.get("termination_reason") != "EXITED" or type(rec.get("exit_code")) is not int or rec["exit_code"] != 0):
        _reject("RESULT_INVALID", "Normalized execution record is not independently eligible")
    agent_path = project / ".harness/runtime/AGENT_RESULTS" / (active["run_ref"] + ".json")
    if agent_path.is_symlink() or not agent_path.is_file():
        _reject("RESULT_INVALID", "Missing kernel-persisted Agent Result")
    payload = _regular_bytes(agent_path, size_limit=MAX_AGENT_RESULT_BYTES)
    if scan_exact_secret(payload, dict(secret_values)):
        _reject("SECRET_LEAK_DETECTED", "Exact supplied secret detected in Agent Result")
    result, _, _ = secure_read_agent_result(project, agent_path.relative_to(project).as_posix())
    if result.get("run_ref") != active["run_ref"] or result.get("task_ref") != active["task_ref"] or result.get("status") != "COMPLETED":
        _reject("RESULT_INVALID", "Kernel-persisted Agent Result has wrong Run or Task")
    # Agent declaration must also agree with independently observed changes.
    if result.get("changes") != diff:
        _reject("SCOPE_VIOLATION", "Agent declaration differs from verified actual write set")
    if scan_exact_secret(result, dict(secret_values)):
        _reject("SECRET_LEAK_DETECTED", "Decoded Agent Result contains supplied secret")
    for channel in ("stdout", "stderr"):
        artifact_ref = rec.get(f"{channel}_artifact_ref")
        if artifact_ref is None:
            continue
        if artifact_ref != ids[channel]:
            _reject("RESULT_INVALID", "Normalized log reference is not exact")
        path = project / ".harness/runtime/EXECUTION_LOGS" / (artifact_ref + ".log")
        data = _regular_bytes(path, size_limit=MAX_PERSISTED_LOG_BYTES)
        if scan_exact_secret(data, dict(secret_values)):
            _reject("SECRET_LEAK_DETECTED", "Exact supplied secret detected in bounded kernel log")


def _verification_inputs(project: Path, root: Path, verification: dict[str, Any],
                         secret_values: Mapping[str, str]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    active, binding, _, _ = _runtime(project, root)
    if check_control_plane(project, active)["status"] != "PASS":
        _reject("VERIFICATION_FAILED", "Canonical control plane differs from Run boundary")
    before_digest = safe_disposable_baseline_revision(project)
    saved = binding.get("execution_baseline", {})
    if not _TREE.fullmatch(saved.get("canonical_product_digest") or "") or saved.get("canonical_product_digest") != before_digest:
        _reject("BASELINE_CHANGED", "Canonical product differs from saved execution baseline")
    if saved.get("snapshot_product_digest") != saved["canonical_product_digest"]:
        _reject("BASELINE_CHANGED", "Saved disposable baseline was inconsistent")
    task = load_data(root / "control/task-contract.yaml")["task"]
    canonical = _scan_files(project, disposable=False)
    product = _scan_files(root / "product", disposable=True)
    proof = _validate_verified(verification, product, canonical)
    diff = diff_snapshots(_compatible_snapshot(canonical), _compatible_snapshot(product))
    if verification.get("scope", {}).get("status") != "PASS":
        _reject("SCOPE_VIOLATION", "Independent verification did not authorize write scope")
    scope = task.get("scope") or {}
    if not isinstance(scope, dict) or not isinstance(scope.get("write"), list) or not isinstance(scope.get("forbidden"), list):
        _reject("SCOPE_VIOLATION", "Missing exact Task Contract scopes")
    status = validate_scope(diff, scope)
    if status["status"] != "PASS" or status != verification.get("scope"):
        _reject("SCOPE_VIOLATION", "Actual path set is outside verified Task Contract")
    changed = sorted(diff["added"] + diff["modified"] + diff["deleted"])
    for name in changed:
        _valid_rel(name)
    # Path presence is its own check; expected_paths are expected artifacts,
    # not an invented assertion that every pre-existing artifact must change.
    required_paths = task.get("verification", {}).get("expected_paths", [])
    if not isinstance(required_paths, list) or any(not isinstance(p, str) for p in required_paths):
        _reject("SCOPE_VIOLATION", "Malformed expected artifact paths")
    for rel in required_paths:
        _valid_rel(rel)
        if rel not in product:
            _reject("SCOPE_VIOLATION", "Task expected product artifact is absent")
    if any(product[path]["mode"] != (0o755 if canonical[path]["mode"] & 0o111 else 0o644)
           for path in product.keys() & canonical.keys()):
        _reject("SCOPE_VIOLATION", "Permission-only or combined mode changes not authorized")
    _check_secrets(project, active, task, root / "product", diff["added"] + diff["modified"], diff, secret_values)
    if scan_exact_secret(verification.get("command_results", []), dict(secret_values)):
        _reject("SECRET_LEAK_DETECTED", "Secret detected in verification diagnostics")
    if safe_disposable_baseline_revision(project) != before_digest:
        _reject("BASELINE_CHANGED", "Canonical baseline drifted during apply planning")
    return active, binding, {"before": canonical, "after": product, "diff": diff, "proof": proof,
                              "before_digest": before_digest, "task": task}


def _write_plan(project: Path, root: Path, active: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    before, after, diff = context["before"], context["after"], context["diff"]
    ops: list[dict[str, Any]] = []
    for category, operation in (("added", "CREATE"), ("modified", "REPLACE"), ("deleted", "DELETE")):
        for name in diff[category]:
            old, new = before.get(name), after.get(name)
            ops.append({"path": name, "operation": operation,
                        "sha256_before": "sha256:" + old["sha256"] if old else None,
                        "sha256_after": "sha256:" + new["sha256"] if new else None,
                        "mode_before": old["mode"] if old else None,
                        "mode_after": (old["mode"] if old else new["mode"]) if new else None,
                        "temp": ".ph05108-" + hashlib.sha256((active["run_ref"] + ":" + name).encode()).hexdigest()[:20] + ".tmp"})
    ops.sort(key=lambda x: x["path"])
    if len(ops) > _MAX_FILES:
        _reject("SCOPE_VIOLATION", "Excessive changed file count")
    if any((after[op["path"]]["size"] if op["sha256_after"] else 0) > _MAX_CHANGED_FILE_BYTES or
           (before[op["path"]]["size"] if op["sha256_before"] else 0) > _MAX_CHANGED_FILE_BYTES
           for op in ops):
        _reject("SCOPE_VIOLATION", "Changed file exceeds bounded apply file size")
    return {"journal_version": _JOURNAL_VERSION, "state": "PREPARED", "run_ref": active["run_ref"],
            "task_ref": active["task_ref"], "baseline_before": context["before_digest"],
            "baseline_after": "tree:sha256:" + _tree_digest_from_sources(root / "product", after),
            "verification_ref": context["proof"], "evidence_id": _evidence_id(active["run_ref"]),
            "ops": ops}


def _tree_digest_from_sources(product: Path, entries: dict[str, dict[str, Any]]) -> str:
    """Stream canonical tree-hash; never materialize a whole product in RAM."""
    tree = hashlib.sha256()
    for rel in sorted(entries):
        _valid_rel(rel)
        tree.update(rel.encode("utf-8") + b"\0")
        parent = _pin_dir(product, rel)
        try:
            name = rel.rsplit("/", 1)[-1]
            fd = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), dir_fd=parent)
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                    _reject("SCOPE_VIOLATION", "Unsafe file in disposable digest")
                file_digest = hashlib.sha256()
                count = 0
                while chunk := os.read(fd, 1024 * 1024):
                    tree.update(chunk)
                    file_digest.update(chunk)
                    count += len(chunk)
                after = os.fstat(fd)
                if ((before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size) !=
                    (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size) or
                    count != entries[rel]["size"] or file_digest.hexdigest() != entries[rel]["sha256"]):
                    _reject("BASELINE_CHANGED", "Disposable source changed during file-level digest")
            finally:
                os.close(fd)
        finally:
            os.close(parent)
        tree.update(b"\0")
    return tree.hexdigest()


def _journal_path(root: Path) -> Path:
    return root / _JOURNAL


@contextmanager
def _apply_lock(project: Path) -> Iterator[None]:
    if os.name != "posix":
        _reject("SANDBOX_UNAVAILABLE", "Automatic apply requires the Linux rootless sandbox; Windows host apply forbidden")
    import fcntl  # Only in the automatic Linux apply path.
    # Linux flock on an existing directory inode needs no new unsanctioned
    # project-control file. All Harness apply/recovery calls share this lock.
    fd = os.open(project / ".harness/runtime", os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _pin_dir(root: Path, relative: str, *, create: bool = False) -> int:
    """Walk existing directories through no-follow directory FDs, not realpath."""
    fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try:
        for part in relative.split("/")[:-1]:
            if create:
                try:
                    os.mkdir(part, mode=0o755, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
            new_fd = os.open(part, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0), dir_fd=fd)
            os.close(fd)
            fd = new_fd
        return fd
    except Exception:
        os.close(fd)
        raise


def _check_at(fd: int, leaf: str, expected: str | None) -> None:
    try:
        info = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        if expected is None:
            return
        _reject("BASELINE_CHANGED", "Target product file was removed during apply")
    if expected is None or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _reject("BASELINE_CHANGED", "Target file unexpectedly exists or is unsafe")
    # A changed source or stale baseline is not rewritten silently.
    current = hashlib.sha256()
    file_fd = os.open(leaf, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0), dir_fd=fd)
    try:
        opened = os.fstat(file_fd)
        if opened.st_ino != info.st_ino or opened.st_dev != info.st_dev or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            _reject("BASELINE_CHANGED", "Target inode changed during apply")
        while part := os.read(file_fd, 65536):
            current.update(part)
    finally:
        os.close(file_fd)
    if "sha256:" + current.hexdigest() != expected:
        _reject("BASELINE_CHANGED", "Target bytes changed during apply")


def _copy_to_target(fd: int, leaf: str, stage: Path, op: dict[str, Any]) -> None:
    temp = op["temp"]
    if "/" in temp or temp == leaf:
        _reject("APPLY_FAILED_RECOVERABLE", "Invalid durable write plan temporary name")
    data = _regular_bytes(stage, size_limit=_MAX_CHANGED_FILE_BYTES)
    if "sha256:" + sha256_bytes(data) != op["sha256_after"]:
        _reject("APPLY_FAILED_RECOVERABLE", "Staged content digest mismatch")
    target_fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), op["mode_after"], dir_fd=fd)
    try:
        with os.fdopen(target_fd, "wb", closefd=False) as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.fchmod(target_fd, op["mode_after"])
        os.fsync(target_fd)
    finally:
        os.close(target_fd)
    os.replace(temp, leaf, src_dir_fd=fd, dst_dir_fd=fd)
    os.fsync(fd)


def _apply_one(project: Path, journal: Path, op: dict[str, Any], i: int) -> None:
    rel = op["path"]
    _valid_rel(rel)
    fd = _pin_dir(project, rel, create=op["operation"] == "CREATE")
    try:
        leaf = rel.rsplit("/", 1)[-1]
        _check_at(fd, leaf, op["sha256_before"])
        if op["operation"] == "DELETE":
            os.unlink(leaf, dir_fd=fd)
            os.fsync(fd)
        else:
            _copy_to_target(fd, leaf, journal / "stage" / f"{i:06d}", op)
    finally:
        os.close(fd)


def _make_journal(project: Path, root: Path, plan: dict[str, Any]) -> Path:
    journal = _journal_path(root)
    journal.mkdir(mode=0o700)
    _fsync_dir(root)
    (journal / "stage").mkdir(mode=0o700)
    (journal / "backup").mkdir(mode=0o700)
    for i, op in enumerate(plan["ops"]):
        name = f"{i:06d}"
        if op["sha256_before"]:
            data = _regular_bytes(project / op["path"], size_limit=_MAX_CHANGED_FILE_BYTES)
            if "sha256:" + sha256_bytes(data) != op["sha256_before"]:
                _reject("BASELINE_CHANGED", "Old product bytes changed during backup")
            _exclusive_write(journal / "backup" / name, data)
        if op["sha256_after"]:
            data = _regular_bytes(root / "product" / op["path"], size_limit=_MAX_CHANGED_FILE_BYTES)
            if "sha256:" + sha256_bytes(data) != op["sha256_after"]:
                _reject("BASELINE_CHANGED", "Disposable source modified during staging")
            _exclusive_write(journal / "stage" / name, data)
    _fsync_dir(journal / "stage")
    _fsync_dir(journal / "backup")
    _replace_json(journal / "journal.json", plan)
    _fsync_dir(journal)
    return journal


def _write_evidence(project: Path, plan: dict[str, Any]) -> Path:
    evidence_dir = project / ".harness/evidence"
    if evidence_dir.is_symlink() or not evidence_dir.is_dir():
        _reject("APPLY_FAILED_RECOVERABLE", "Unsafe canonical evidence directory")
    payload = {"apply_evidence": {
        "id": plan["evidence_id"], "run_ref": plan["run_ref"] if "@" in plan["run_ref"] else plan["run_ref"] + "@1",
        "verification_ref": plan["verification_ref"],
        "baseline_before": plan["baseline_before"].removeprefix("tree:"),
        "baseline_after": plan["baseline_after"].removeprefix("tree:"),
        "status": "PASS",
        "write_set": [{key: op[key] for key in ("path", "operation", "sha256_before", "sha256_after")}
                      for op in plan["ops"]], "applied_at": utc_now(),
    }}
    path = evidence_dir / (plan["evidence_id"] + ".yaml")
    _exclusive_write(path, canonical_json_bytes(payload))
    return path


def _validate_journal(project: Path, root: Path) -> dict[str, Any]:
    path = _journal_path(root)
    if path.is_symlink() or not path.is_dir():
        _reject("APPLY_FAILED_RECOVERABLE", "Unsafe apply journal directory")
    document = path / "journal.json"
    if document.is_symlink() or not document.is_file():
        _reject("APPLY_FAILED_RECOVERABLE", "Incomplete/stale journal requires quarantine")
    plan = json.loads(_regular_bytes(document, size_limit=4_000_000))
    if (not isinstance(plan, dict) or set(plan) != {"journal_version", "state", "run_ref", "task_ref", "baseline_before", "baseline_after", "verification_ref", "evidence_id", "ops"} or
        plan.get("journal_version") != _JOURNAL_VERSION or plan.get("state") not in {"PREPARED", "COMMITTED"} or
        not isinstance(plan.get("ops"), list) or len(plan["ops"]) > _MAX_FILES or
        not _TREE.fullmatch(plan.get("baseline_before") or "") or not _TREE.fullmatch(plan.get("baseline_after") or "") or
        not _SHA.fullmatch(plan.get("verification_ref") or "") or plan.get("run_ref") != root.name or
        plan.get("evidence_id") != _evidence_id(root.name)):
        _reject("APPLY_FAILED_RECOVERABLE", "Apply journal is corrupt or unrelated")
    for folder in ("stage", "backup"):
        dirname = path / folder
        if dirname.is_symlink() or not dirname.is_dir():
            _reject("APPLY_FAILED_RECOVERABLE", "Journal stage/backup directory unsafe")
    for index, op in enumerate(plan["ops"]):
        if not isinstance(op, dict) or set(op) != {"path", "operation", "sha256_before", "sha256_after", "mode_before", "mode_after", "temp"}:
            _reject("APPLY_FAILED_RECOVERABLE", "Invalid journal write set")
        _valid_rel(op["path"])
        if op["operation"] not in {"CREATE", "REPLACE", "DELETE"} or any(
            x is not None and not _SHA.fullmatch(x) for x in (op["sha256_before"], op["sha256_after"])
        ) or op["temp"] != ".ph05108-" + hashlib.sha256((plan["run_ref"] + ":" + op["path"]).encode()).hexdigest()[:20] + ".tmp":
            _reject("APPLY_FAILED_RECOVERABLE", "Unsafe journal operation")
        if ((op["operation"] == "CREATE" and op["sha256_before"] is not None) or
            (op["operation"] == "DELETE" and op["sha256_after"] is not None) or
            (op["operation"] == "REPLACE" and (op["sha256_before"] is None or op["sha256_after"] is None))):
            _reject("APPLY_FAILED_RECOVERABLE", "Invalid journal operation pre/postconditions")
        allowed_modes = {0o600, 0o644, 0o755, 0o700, 0o664, 0o775}
        if ((op["sha256_before"] is None and op["mode_before"] is not None) or
            (op["sha256_before"] is not None and type(op["mode_before"]) is not int) or
            (op["sha256_before"] is not None and op["mode_before"] not in allowed_modes) or
            (op["sha256_after"] is None and op["mode_after"] is not None) or
            (op["sha256_after"] is not None and type(op["mode_after"]) is not int) or
            (op["sha256_after"] is not None and op["mode_after"] not in allowed_modes)):
            _reject("APPLY_FAILED_RECOVERABLE", "Unsafe journal file mode")
        for field, expected, folder in (("sha256_before", op["sha256_before"], "backup"), ("sha256_after", op["sha256_after"], "stage")):
            source = path / folder / f"{index:06d}"
            if plan["state"] == "PREPARED" and expected and (not source.is_file() or "sha256:" + sha256_bytes(_regular_bytes(source, size_limit=_MAX_CHANGED_FILE_BYTES)) != expected):
                _reject("APPLY_FAILED_RECOVERABLE", "Journal staged/backup bytes corrupted")
    if [op["path"] for op in plan["ops"]] != sorted(set(op["path"] for op in plan["ops"])):
        _reject("APPLY_FAILED_RECOVERABLE", "Duplicate or unsorted write-set entries")
    return plan


def _cleanup_journal(root: Path, *, incomplete: bool = False) -> None:
    """Atomically retire journal before cleanup (crash after rename is safe).

    After the rename, rollback or commit has already been durably decided; a
    crash may leave an orphan cleanup directory, never a half-known journal.
    PH-051-10 owns wider orphan pruning.
    """
    journal = _journal_path(root)
    cleanup = root / ".apply-cleanup"
    if journal.is_symlink() or cleanup.exists() or cleanup.is_symlink():
        _reject("APPLY_FAILED_RECOVERABLE", "Unsafe/occupied apply cleanup path")
    if not journal.exists():
        return
    names = {p.name for p in journal.iterdir()}
    allowed = {"stage", "backup", "journal.json"}
    if incomplete:
        allowed.add(".journal.json.writing")
    if names - allowed:
        _reject("APPLY_FAILED_RECOVERABLE", "Unexpected journal entries require quarantine")
    for folder in ("stage", "backup"):
        target = journal / folder
        if target.is_symlink() or (target.exists() and not target.is_dir()):
            _reject("APPLY_FAILED_RECOVERABLE", "Unsafe stage/backup directory")
        if target.is_dir():
            for p in target.iterdir():
                if p.is_symlink() or not p.is_file() or p.stat().st_nlink != 1 or not re.fullmatch(r"[0-9]{6}", p.name):
                    _reject("APPLY_FAILED_RECOVERABLE", "Unsafe staged/backup path")
    os.rename(journal, cleanup)
    _fsync_dir(root)
    for folder in ("stage", "backup"):
        target = cleanup / folder
        if target.is_dir():
            for p in target.iterdir():
                p.unlink()
            target.rmdir()
    (cleanup / "journal.json").unlink(missing_ok=True)
    if incomplete:
        (cleanup / ".journal.json.writing").unlink(missing_ok=True)
    cleanup.rmdir()
    _fsync_dir(root)


def _rollback(project: Path, root: Path, plan: dict[str, Any]) -> None:
    """Repeatable rollback; refuse overriding an unrelated concurrent edit."""
    for i, op in reversed(list(enumerate(plan["ops"]))):
        path = op["path"]
        # CREATE may have made parent directories; missing ones need no rollback.
        parent_path = project / path.rsplit("/", 1)[0] if "/" in path else project
        if not parent_path.exists():
            if op["sha256_before"] is not None:
                _reject("APPLY_FAILED_RECOVERABLE", "Old parent vanished during recovery")
            continue
        fd = _pin_dir(project, path)
        try:
            leaf = path.rsplit("/", 1)[-1]
            try:
                info = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                info = None
            if info is not None:
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    _reject("APPLY_FAILED_RECOVERABLE", "Unsafe current path during rollback")
                digest = hashlib.sha256()
                file_fd = os.open(leaf, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=fd)
                try:
                    while part := os.read(file_fd, 65536):
                        digest.update(part)
                finally:
                    os.close(file_fd)
                if "sha256:" + digest.hexdigest() not in (op["sha256_before"], op["sha256_after"]):
                    _reject("APPLY_FAILED_RECOVERABLE", "Concurrent product edit during rollback; manual recovery")
            # Any partially-written temp is known by exact journal operation.
            try:
                tmp_info = os.stat(op["temp"], dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                tmp_info = None
            if tmp_info:
                if not stat.S_ISREG(tmp_info.st_mode) or tmp_info.st_nlink != 1:
                    _reject("APPLY_FAILED_RECOVERABLE", "Unsafe per-file staging object during rollback")
                os.unlink(op["temp"], dir_fd=fd)
                os.fsync(fd)
            if op["sha256_before"] is None:
                if info:
                    os.unlink(leaf, dir_fd=fd)
                    os.fsync(fd)
            elif info and "sha256:" + digest.hexdigest() == op["sha256_before"]:
                if stat.S_IMODE(info.st_mode) != op["mode_before"]:
                    os.chmod(leaf, op["mode_before"], dir_fd=fd, follow_symlinks=False)
                    os.fsync(fd)
            else:
                old = _regular_bytes(_journal_path(root) / "backup" / f"{i:06d}", size_limit=_MAX_CHANGED_FILE_BYTES)
                if "sha256:" + sha256_bytes(old) != op["sha256_before"]:
                    _reject("APPLY_FAILED_RECOVERABLE", "Rollback backup digest invalid")
                tmp_name = op["temp"]
                temp_fd = os.open(tmp_name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), op["mode_before"], dir_fd=fd)
                try:
                    with os.fdopen(temp_fd, "wb", closefd=False) as out:
                        out.write(old)
                        out.flush()
                        os.fsync(out.fileno())
                    os.fchmod(temp_fd, op["mode_before"])
                finally:
                    os.close(temp_fd)
                os.replace(tmp_name, leaf, src_dir_fd=fd, dst_dir_fd=fd)
                os.fsync(fd)
        finally:
            os.close(fd)
    # Remove empty dirs created by CREATEs, deepest first, but never erase
    # content added by another process. Directories are not evidence.
    candidates = set()
    for op in plan["ops"]:
        if op["operation"] == "CREATE":
            pieces = op["path"].split("/")[:-1]
            for depth in range(1, len(pieces) + 1):
                candidates.add("/".join(pieces[:depth]))
    for relative in sorted(candidates, key=lambda s: (-len(s.split("/")), s)):
        candidate = project / relative
        if candidate.is_symlink():
            _reject("APPLY_FAILED_RECOVERABLE", "Unsafe directory during cleanup")
        try:
            candidate.rmdir()  # only empty directories
            _fsync_dir(candidate.parent)
        except (FileNotFoundError, OSError):
            pass
    evidence = project / ".harness/evidence" / (plan["evidence_id"] + ".yaml")
    if evidence.is_symlink():
        _reject("APPLY_FAILED_RECOVERABLE", "Evidence path replaced by symlink")
    if evidence.exists():
        evidence.unlink()
        _fsync_dir(evidence.parent)
    if safe_disposable_baseline_revision(project) != plan["baseline_before"]:
        _reject("APPLY_FAILED_RECOVERABLE", "Rollback product digest does not match saved baseline")


def _recover_locked(project: Path, root: Path, active: dict[str, Any]) -> dict[str, Any]:
    journal = _journal_path(root)
    if not journal.exists() and not journal.is_symlink():
        return {"status": "NO_JOURNAL"}
    if not (journal / "journal.json").exists():
        # The protocol NEVER touches a canonical file until this complete
        # PREPARED journal has been fsync'd; partial staging has no mutations.
        binding = load_data(project / ".harness/runtime/EXECUTION_BINDINGS" / (active["run_ref"] + ".yaml"))["execution_binding"]
        if safe_disposable_baseline_revision(project) != binding["execution_baseline"]["canonical_product_digest"]:
            _reject("APPLY_FAILED_RECOVERABLE", "Incomplete staging journal and baseline drift; quarantine")
        _cleanup_journal(root, incomplete=True)
        return {"status": "ROLLED_BACK", "idempotent": True}
    plan = _validate_journal(project, root)
    if plan["run_ref"] != active["run_ref"] or plan["task_ref"] != active["task_ref"]:
        _reject("APPLY_FAILED_RECOVERABLE", "Journal belongs to a different current Run")
    if plan["state"] == "COMMITTED":
        if safe_disposable_baseline_revision(project) != plan["baseline_after"]:
            _reject("APPLY_FAILED_RECOVERABLE", "Committed after-baseline drifted; quarantine")
        evidence = project / ".harness/evidence" / (plan["evidence_id"] + ".yaml")
        record = load_data(evidence).get("apply_evidence", {}) if evidence.is_file() and not evidence.is_symlink() else {}
        if record.get("id") != plan["evidence_id"] or record.get("verification_ref") != plan["verification_ref"]:
            _reject("APPLY_FAILED_RECOVERABLE", "Committed evidence missing or inconsistent")
        _cleanup_journal(root)
        return {"status": "APPLIED", "idempotent": True, "evidence_ref": plan["evidence_id"]}
    _rollback(project, root, plan)
    # If a crash occurred after the evidence/boundary, reseal the restored
    # project-control tree. No pre-existing historical record is overwritten.
    record_phase_boundary(project, active, phase="PRODUCT_APPLY_RECOVERED_ROLLBACK",
                          kernel_written_paths=[], recorded_at=utc_now())
    _cleanup_journal(root)
    return {"status": "ROLLED_BACK", "idempotent": True}


def recover_apply(project_root: Path, execution_root: Path) -> dict[str, Any]:
    """Explicit deterministic recovery, always invoked before the next apply.

    PH-051-10 will wire this into full restart/orphan Run recovery.  A corrupt
    or conflicting journal is quarantined and never optimistically cleared.
    """
    if os.name != "posix":
        _reject("SANDBOX_UNAVAILABLE", "Automatic apply is unsupported on native Windows")
    project = Path(project_root).resolve(strict=True)
    with _apply_lock(project):
        active, _, project, root = _runtime(project, Path(execution_root))
        return _recover_locked(project, root, active)


def apply_verified_diff(project_root: Path, execution_root: Path, *,
                        verification: dict[str, Any], secret_values: Mapping[str, str],
                        fault_hook: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Apply exact independently verified changes; never mark Task DONE.

    `fault_hook` is for deterministic tests of interruption/crash boundaries;
    do not pass it from untrusted agent data. BaseException emulates abrupt
    process death; subsequent `recover_apply` must restore all-old/all-new.
    """
    if os.name != "posix":
        _reject("SANDBOX_UNAVAILABLE", "Automatic apply is unsupported on native Windows")
    project = Path(project_root).resolve(strict=True)
    with _apply_lock(project):
        active, _, project, root = _runtime(project, Path(execution_root))
        # Retired cleanup leftovers do not contain an active journal. A
        # separate PH-051-10 orphan cleanup handles those after host crash.
        recovery = _recover_locked(project, root, active)
        if recovery["status"] == "ROLLED_BACK":
            _reject("APPLY_FAILED_RECOVERABLE", "Previous interrupted apply recovered; reverify for a new attempt")
        if recovery["status"] == "APPLIED":
            return recovery
        evidence_path = project / ".harness/evidence" / (_evidence_id(active["run_ref"]) + ".yaml")
        if evidence_path.is_symlink():
            _reject("APPLY_FAILED_RECOVERABLE", "Unsafe pre-existing apply evidence")
        if evidence_path.exists():
            record = load_data(evidence_path).get("apply_evidence", {})
            if (record.get("run_ref") == (active["run_ref"] if "@" in active["run_ref"] else active["run_ref"] + "@1") and
                _SHA.fullmatch(record.get("baseline_after") or "") and
                safe_disposable_baseline_revision(project) == "tree:" + record["baseline_after"] and
                check_control_plane(project, active)["status"] == "PASS"):
                return {"status": "APPLIED", "idempotent": True, "evidence_ref": _evidence_id(active["run_ref"])}
            _reject("APPLY_FAILED_RECOVERABLE", "Conflicting immutable Apply Evidence")
        active, binding, context = _verification_inputs(project, root, verification, secret_values)
        plan = _write_plan(project, root, active, context)
        journal = None
        committed = False
        try:
            if _journal_path(root).exists() or _journal_path(root).is_symlink():
                _reject("APPLY_FAILED_RECOVERABLE", "An apply journal already exists")
            journal = _make_journal(project, root, plan)
            if fault_hook:
                fault_hook("JOURNAL_PREPARED")
            if safe_disposable_baseline_revision(project) != plan["baseline_before"]:
                _reject("BASELINE_CHANGED", "Canonical changed before first apply operation")
            # Independent verifier's exact bytes may not be replaced by agent
            # after staging. Verify the saved staged candidate *again*.
            if (_scan_files(root / "product", disposable=True) != context["after"] or
                "tree:sha256:" + _tree_digest_from_sources(root / "product", context["after"]) != plan["baseline_after"]):
                _reject("VERIFICATION_FAILED", "Disposable files changed during write-plan staging")
            for i, op in enumerate(plan["ops"]):
                _apply_one(project, journal, op, i)
                if fault_hook:
                    fault_hook(f"AFTER_OPERATION_{i + 1}")
            if safe_disposable_baseline_revision(project) != plan["baseline_after"]:
                _reject("BASELINE_CHANGED", "Post-apply canonical digest did not match staged plan")
            if fault_hook:
                fault_hook("PRODUCT_APPLIED")
            evidence = _write_evidence(project, plan)
            if fault_hook:
                fault_hook("EVIDENCE_WRITTEN")
            record_phase_boundary(project, active, phase="PRODUCT_APPLY_VERIFIED",
                                  kernel_written_paths=[evidence.relative_to(project).as_posix()],
                                  recorded_at=utc_now())
            if check_control_plane(project, active)["status"] != "PASS":
                _reject("APPLY_FAILED_RECOVERABLE", "Post-apply control-plane protection failed")
            if fault_hook:
                fault_hook("BEFORE_COMMIT_MARKER")
            plan["state"] = "COMMITTED"
            _replace_json(journal / "journal.json", plan)
            committed = True
            if fault_hook:
                fault_hook("COMMITTED")
            _cleanup_journal(root)
            return {"status": "APPLIED", "idempotent": False, "evidence_ref": plan["evidence_id"],
                    "verification_ref": plan["verification_ref"], "baseline_before": plan["baseline_before"],
                    "baseline_after": plan["baseline_after"], "write_set": len(plan["ops"])}
        except Exception as exc:
            # The signed product commit cannot be described as a rollback just
            # because post-commit cleanup failed; this is truthful success.
            if committed:
                if (safe_disposable_baseline_revision(project) == plan["baseline_after"] and
                    check_control_plane(project, active)["status"] == "PASS"):
                    return {"status": "APPLIED", "idempotent": False, "evidence_ref": plan["evidence_id"],
                            "cleanup_pending": True, "baseline_after": plan["baseline_after"]}
                raise ApplyFailure("APPLY_FAILED_RECOVERABLE", "Committed apply requires inspection") from exc
            # In-process failures prior to durable commit roll back via journal;
            # if the marker itself reached COMMITTED, recovery reports success.
            if _journal_path(root).exists() or _journal_path(root).is_symlink():
                try:
                    recovery = _recover_locked(project, root, active)
                    if recovery["status"] == "APPLIED":
                        return recovery
                except Exception as recovery_error:
                    raise ApplyFailure("APPLY_FAILED_RECOVERABLE", "Apply interrupted; durable journal requires recovery") from recovery_error
            if isinstance(exc, ApplyFailure):
                raise
            raise ApplyFailure("APPLY_FAILED_RECOVERABLE", "Atomic product apply failed; old baseline recovered") from exc

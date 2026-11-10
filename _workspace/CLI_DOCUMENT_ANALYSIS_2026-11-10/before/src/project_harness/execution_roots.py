"""PH-051-04 — per-Run disposable product and bounded read-only control.

This is an explicit internal/Python API, NOT an automatic executor. No CLI or
canonical product apply is enabled until PH-051-08/09. A caller must provide an
independent runtime root, and the exact currently reserved Run is resolved from
canonical control records, never from an agent-supplied path.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
from typing import Any

from .errors import SafetyViolation, ValidationFailure
from .hashing import sha256_bytes, sha256_file, tree_hash
from .project_input import execution_policy_issues
from .safety import copy_disposable_product, safe_disposable_baseline_revision
from .serialization import canonical_json_bytes, load_data, write_data
from .util import utc_now
from .workspace import check_control_plane, record_phase_boundary
from .sandbox.profiles import SandboxPolicyError, validate_execution_mounts

_RUN_ID = re.compile(r"RUN-[A-Z0-9]+(?:-[A-Z0-9]+)*\Z")
_PROJECT_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_CONTROL_FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_BINDING_VERSION = 1


def _safe_exact_relative(root: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or "\x00" in relative:
        raise SafetyViolation("Untrusted control path", relative)
    posix = PurePosixPath(relative)
    if posix.is_absolute() or any(p in {"", ".", ".."} for p in relative.split("/")):
        raise SafetyViolation("Control reference must be exact and relative", relative)
    if len(posix.parts) < 3 or posix.parts[0] != ".harness":
        raise SafetyViolation("Control projection may only use explicit .harness records", relative)
    path = root
    for piece in posix.parts:
        path /= piece
        try:
            details = path.lstat()
        except OSError as exc:
            raise ValidationFailure("Required exact Run artifact missing", relative) from exc
        if stat.S_ISLNK(details.st_mode):
            raise SafetyViolation("Symlink in Run control source", relative)
    if not path.is_file() or path.stat().st_nlink != 1:
        raise SafetyViolation("Run control source must be a single regular file", relative)
    return path


def _read_exact(root: Path, relative: Any, envelope: str, ref: str, *, revisioned: bool = False) -> bytes:
    path = _safe_exact_relative(root, relative)
    contents = path.read_bytes()
    data = load_data(path)
    body = data.get(envelope) if isinstance(data, dict) else None
    if not isinstance(body, dict):
        raise ValidationFailure("Wrong envelope in Run control source", relative)
    expected = ref.split("@", 1)[0] if revisioned else ref
    actual = body.get("id")
    if actual != expected:
        raise ValidationFailure("Run artifact ID mismatch", {"path": relative, "actual": actual, "expected": expected})
    if revisioned:
        if "@" not in ref or not ref.rsplit("@", 1)[1].isdigit() or type(body.get("revision")) is not int or int(ref.rsplit("@", 1)[1]) != body["revision"]:
            raise ValidationFailure("Run task revision mismatch", {"path": relative, "ref": ref})
    return contents


def _task_path(root: Path, task_ref: str) -> str:
    if not isinstance(task_ref, str) or "@" not in task_ref:
        raise ValidationFailure("Expected revisioned current Task ref", task_ref)
    task_id, rev = task_ref.rsplit("@", 1)
    if not _CONTROL_FILE.fullmatch(task_id) or not rev.isdigit() or int(rev) < 1:
        raise ValidationFailure("Invalid Task ref", task_ref)
    index = load_data(_safe_exact_relative(root, ".harness/tasks/INDEX.yaml"))["task_index"]
    path = index.get("current", {}).get(task_id)
    if path != f".harness/tasks/{task_ref}.yaml":
        raise ValidationFailure("Current Task index is not exact Run binding", {"task_ref": task_ref, "current": path})
    return path


def _load_bound_sources(root: Path, active: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, str]]:
    run_ref, task_ref = active["run_ref"], active["task_ref"]
    run_plan_ref = active["run_plan_ref"]
    bundle_ref = active["prompt_bundle_ref"]
    context_ref = active["context_packet_ref"]
    entries = {
        "prompt-bundle.md": (active["prompt_markdown_path"], None, None),
        "prompt-bundle.yaml": (active["prompt_bundle_path"], "compiled_prompt_bundle", bundle_ref),
        "context-packet.json": (active["context_packet_path"], "context_packet", context_ref),
        "task-contract.yaml": (_task_path(root, task_ref), "task", task_ref),
        "run-plan.yaml": (active["run_plan_path"], "run_plan", run_plan_ref),
    }
    # The filenames are deterministic and selected by trusted Kernel, not user input.
    expected_paths = {
        "prompt-bundle.md": f".harness/prompts/BUNDLES_BY_RUN/{bundle_ref}.md",
        "prompt-bundle.yaml": f".harness/prompts/BUNDLES_BY_RUN/{bundle_ref}.yaml",
        "context-packet.json": f".harness/context/PACKETS_BY_RUN/{context_ref}.yaml",
        "run-plan.yaml": f".harness/runtime/RUN_PLANS/{run_plan_ref}@1.yaml",
    }
    for name, expected in expected_paths.items():
        if entries[name][0] != expected:
            raise ValidationFailure("Noncanonical current Run artifact path", {"file": name, "actual": entries[name][0], "expected": expected})
    sources: dict[str, bytes] = {}
    bindings: dict[str, str] = {}
    for name, (relative, envelope, ref) in entries.items():
        raw = _safe_exact_relative(root, relative).read_bytes() if envelope is None else _read_exact(root, relative, envelope, ref, revisioned=name == "task-contract.yaml")
        if name == "prompt-bundle.md":
            pass
        else:
            body = load_data(root / relative)[envelope]
            if body.get("task_ref") != task_ref and name != "task-contract.yaml":
                raise ValidationFailure("Run control artifact bound to another Task", name)
            if name in ("prompt-bundle.yaml", "context-packet.json") and body.get("run_ref") != run_ref:
                raise ValidationFailure("Run control artifact bound to another Run", name)
            if name == "run-plan.yaml" and (body.get("prompt_bundle_ref") != bundle_ref or body.get("context_packet_ref") != context_ref):
                raise ValidationFailure("Run Plan references inconsistent JIT", name)
        sources[name] = raw
        bindings[name] = relative
    prompt_sha = load_data(root / entries["prompt-bundle.yaml"][0])["compiled_prompt_bundle"]["prompt_text_sha256"]
    if prompt_sha != "sha256:" + sha256_bytes(sources["prompt-bundle.md"]):
        raise ValidationFailure("Prompt Bundle text digest mismatch", bundle_ref)
    # Only the five allowed, non-secret execution policy keys are projected.
    lock_path = _safe_exact_relative(root, ".harness/config/PROJECT_LOCK.yaml")
    lock = load_data(lock_path).get("project_lock")
    policy = lock.get("execution") if isinstance(lock, dict) else None
    keys = {"mode", "adapter_profile_ref", "sandbox_profile_ref", "network_mode", "completion_policy"}
    if not isinstance(policy, dict) or set(policy) != keys or execution_policy_issues(policy):
        raise ValidationFailure("Current PROJECT_LOCK execution policy is invalid or unbounded", execution_policy_issues(policy))
    sources["permitted-config.json"] = canonical_json_bytes({"execution": {key: policy[key] for key in sorted(keys)}})
    bindings["permitted-config.json"] = ".harness/config/PROJECT_LOCK.yaml#execution"
    schema = Path(__file__).parent / "resources/schemas/agent_task_result.schema.json"
    sources["agent-task-result.schema.json"] = schema.read_bytes()
    bindings["agent-task-result.schema.json"] = "SCHEMA-AGENT-TASK-RESULT@1"
    return sources, bindings


def _control_plane_digest(root: Path) -> str:
    """Hash canonical control metadata, excluding this builder's own bindings.

    No secret contents are copied into a projection by this function. Changes to
    other control files during creation are detected by a before/after digest.
    """
    control = root / ".harness"
    h = hashlib.sha256()
    for current, dirs, files in os.walk(control, followlinks=False):
        base = Path(current)
        rel = base.relative_to(control).as_posix()
        for dirname in dirs:
            if (base / dirname).is_symlink():
                raise SafetyViolation("Symlink directory in canonical control", str(base / dirname))
        dirs[:] = sorted(d for d in dirs if (rel, d) not in {
            ("runtime", "EXECUTION_BINDINGS"), ("runtime", "OPERATION_JOURNAL"),
        })
        for name in sorted(files):
            path = base / name
            if path.is_symlink() or not path.is_file():
                raise SafetyViolation("Unsafe canonical control file", str(path.relative_to(root)))
            relative = path.relative_to(control).as_posix()
            h.update(relative.encode("utf-8") + b"\0")
            h.update(sha256_file(path).encode("ascii") + b"\0")
    return "sha256:" + h.hexdigest()


def _check_disjoint(canonical: Path, runtime_root: Path) -> Path:
    if not runtime_root.is_absolute():
        raise SafetyViolation("Runtime root must be an absolute explicit path", str(runtime_root))
    if any(part in {".", ".."} for part in runtime_root.parts) or runtime_root == Path("/"):
        raise SafetyViolation("Unbounded runtime root", str(runtime_root))
    # No implicit resolution of an attacker-controlled symlink parent.
    for ancestor in reversed((runtime_root, *runtime_root.parents)):
        if ancestor.is_symlink():
            raise SafetyViolation("Runtime root has a symlink ancestor", str(ancestor))
    normalized = runtime_root.resolve(strict=False)
    if canonical == normalized or canonical in normalized.parents or normalized in canonical.parents:
        raise SafetyViolation("Runtime root overlaps canonical project", str(runtime_root))
    if normalized == Path.home().resolve():
        raise SafetyViolation("Runtime root cannot be host home")
    return normalized


def _root_contents_digest(root: Path) -> str:
    """Exact canonical tree-hash algorithm over regular, unlinked files only."""
    paths: list[Path] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        base = Path(current)
        for name in dirs:
            if (base / name).is_symlink():
                raise SafetyViolation("Symlinked directory in disposable snapshot", str(base / name))
        dirs[:] = sorted(dirs)
        for name in sorted(files):
            path = base / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise SafetyViolation("Unsafe file in disposable product/projection", str(path))
            paths.append(path)
    return "tree:sha256:" + tree_hash(root, paths)


def _verify_projection(control: Path, expected: dict[str, str]) -> None:
    actual = {p.relative_to(control).as_posix() for p in control.iterdir()}
    if actual != set(expected):
        raise SafetyViolation("Control projection entries changed", {"actual": sorted(actual), "expected": sorted(expected)})
    for name, digest in expected.items():
        path = control / name
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o222:
            raise SafetyViolation("Control projection file is not read-only regular", name)
        if "sha256:" + sha256_file(path) != digest:
            raise SafetyViolation("Control projection bytes changed", name)
    if control.lstat().st_mode & 0o222:
        raise SafetyViolation("Control projection directory must be read-only")


def check_execution_baseline(project_root: Path, binding: dict[str, Any]) -> dict[str, str]:
    """No apply here: expose a deterministic BASELINE_CHANGED readiness check."""
    current = safe_disposable_baseline_revision(project_root)
    before = (binding.get("execution_baseline") or {}).get("canonical_product_digest")
    return {"status": "PASS" if current == before else "BASELINE_CHANGED", "expected": before, "actual": current}


def prepare_execution_root(project_root: Path, runtime_root: Path, *, run_ref: str | None = None) -> dict[str, Any]:
    """Prepare/replay one exact current Run without running agent or changing product.

    Returns paths exclusively to the trusted caller; the project-local binding
    stores bounded digests/refs, never an absolute execution root or raw files.
    """
    canonical = Path(project_root).expanduser().resolve(strict=True)
    runtime = _check_disjoint(canonical, Path(runtime_root).expanduser())
    state = load_data(_safe_exact_relative(canonical, ".harness/state/CURRENT_STATE.yaml"))["state"]
    active = state.get("active_run")
    if not isinstance(active, dict) or not isinstance(active.get("run_ref"), str):
        raise ValidationFailure("No active reserved Run for disposable execution")
    actual_run = active["run_ref"]
    if run_ref is not None and run_ref != actual_run:
        raise ValidationFailure("Requested Run does not match active Run", {"requested": run_ref, "active": actual_run})
    if not _RUN_ID.fullmatch(actual_run):
        raise ValidationFailure("Malformed Run ID", actual_run)
    project = load_data(_safe_exact_relative(canonical, ".harness/config/PROJECT.yaml"))["project"]
    project_id = project.get("id")
    if not isinstance(project_id, str) or not _PROJECT_ID.fullmatch(project_id):
        raise ValidationFailure("Unsafe project ID for runtime path", project_id)
    # A fresh execution root is never nested within canonical control/product.
    root = runtime / project_id / "executions" / actual_run
    if root == canonical or canonical in root.parents or root in canonical.parents:
        raise SafetyViolation("Unsafe execution root location", str(root))
    binding_path = canonical / ".harness/runtime/EXECUTION_BINDINGS" / f"{actual_run}.yaml"
    if binding_path.parent.is_symlink() or binding_path.is_symlink():
        raise SafetyViolation("Execution binding path/parent is a symlink", str(binding_path))
    # Never accept a forged binding or re-seal unrelated control tampering.
    # The existing signed operation journal is the v0.5.0 control-plane fence.
    if check_control_plane(canonical, active)["status"] != "PASS":
        raise SafetyViolation("Control-plane integrity FAILED before disposable root preparation", actual_run)
    baseline = safe_disposable_baseline_revision(canonical)
    if binding_path.exists():
        binding_doc = load_data(binding_path)
        binding = binding_doc.get("execution_binding") if isinstance(binding_doc, dict) else None
        if not isinstance(binding, dict) or binding.get("run_ref") != actual_run or binding.get("project_id") != project_id:
            raise ValidationFailure("Existing execution binding is incompatible", actual_run)
        if binding.get("runtime_root_digest") != "sha256:" + sha256_bytes(str(runtime).encode("utf-8")):
            raise ValidationFailure("Run bound to a different runtime root", actual_run)
        if any(binding.get(name) != active.get(name) for name in (
            "run_plan_ref", "task_ref", "prompt_bundle_ref", "context_packet_ref"
        )):
            raise ValidationFailure("Stale binding no longer refers to current Run records", actual_run)
        # An exact Run replay must not trust digests written in a tampered
        # metadata record. Recompute the allowlist directly from trusted JIT.
        current_sources, current_refs = _load_bound_sources(canonical, active)
        expected_projection = {name: "sha256:" + sha256_bytes(payload)
                               for name, payload in current_sources.items()}
        if binding.get("projection_sources") != current_refs or binding.get("projection_files") != expected_projection:
            raise ValidationFailure("Run projection metadata diverged from exact control records", actual_run)
        if binding.get("execution_baseline", {}).get("control_plane_digest") != _control_plane_digest(canonical):
            raise ValidationFailure("Control plane baseline changed since Run snapshot", actual_run)
        if check_execution_baseline(canonical, binding)["status"] != "PASS":
            raise ValidationFailure("BASELINE_CHANGED: canonical product modified since Run snapshot", actual_run)
        if not root.is_dir() or root.is_symlink():
            raise ValidationFailure("Existing execution root is missing or unsafe", str(root))
        try:
            validate_execution_mounts({"execution_root": root, "canonical_project_root": canonical,
                                       "product_dir": root / "product", "control_dir": root / "control", "output_dir": root / "output"})
        except SandboxPolicyError as exc:
            raise SafetyViolation("Existing execution mounts are unsafe", str(exc)) from exc
        if _root_contents_digest(root / "product") != binding["execution_baseline"]["snapshot_product_digest"]:
            raise ValidationFailure("Existing execution snapshot modified; cannot replay preparation", actual_run)
        _verify_projection(root / "control", binding["projection_files"])
        if any((root / "output").iterdir()):
            raise ValidationFailure("Existing output is not empty; cannot replay preparation", actual_run)
        return {"status": "PREPARED", "run_ref": actual_run, "idempotent": True,
                "execution_root": str(root), "product_dir": str(root / "product"),
                "control_dir": str(root / "control"), "output_dir": str(root / "output"),
                "execution_baseline": binding["execution_baseline"]}

    # Load the strict, current JIT sources *before* writing anything to the project.
    sources, refs = _load_bound_sources(canonical, active)
    before_control = _control_plane_digest(canonical)
    runtime_parent = root.parent
    # Reject symlinks not just at runtime_root, but also at the newly-derived
    # project-id/executions parents, before touching any tree below them.
    for parent in reversed((runtime_parent, *runtime_parent.parents)):
        if parent.is_symlink():
            raise SafetyViolation("Symlink in execution root parent", str(parent))
    runtime_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if runtime_parent.resolve(strict=True) != runtime_parent:
        raise SafetyViolation("Execution root parent changed during preparation")
    if root.exists() or root.is_symlink():
        raise ValidationFailure("Orphan or concurrent execution root exists; manual recovery required", str(root))
    # Exclusive mkdir is the per-Run reservation. Incomplete/crash roots are
    # quarantined by refusal, not adopted by another Run (PH-051-10 cleanup).
    try:
        root.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ValidationFailure("Concurrent execution root reservation", actual_run) from exc
    try:
        for name in ("product", "control", "output"):
            (root / name).mkdir(mode=0o755)
        copy_disposable_product(canonical, root / "product")
        snapshot_digest = _root_contents_digest(root / "product")
        if snapshot_digest != baseline or safe_disposable_baseline_revision(canonical) != baseline:
            raise ValidationFailure("BASELINE_CHANGED: project modified while snapshotting", {"before": baseline, "copy": snapshot_digest})
        control_dir = root / "control"
        for name, payload in sources.items():
            if not _CONTROL_FILE.fullmatch(name):
                raise SafetyViolation("Unsafe projected filename", name)
            path = control_dir / name
            with path.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            path.chmod(0o444)
        control_dir.chmod(0o555)
        projection_digests = {name: "sha256:" + sha256_bytes(data) for name, data in sources.items()}
        _verify_projection(control_dir, projection_digests)
        if _control_plane_digest(canonical) != before_control or safe_disposable_baseline_revision(canonical) != baseline:
            raise ValidationFailure("BASELINE_CHANGED: canonical source changed during projection")
        try:
            validate_execution_mounts({"execution_root": root, "canonical_project_root": canonical,
                                       "product_dir": root / "product", "control_dir": control_dir, "output_dir": root / "output"})
        except SandboxPolicyError as exc:
            raise SafetyViolation("Disposable mounts failed Podman boundary validation", str(exc)) from exc
        binding = {
            "schema_version": _BINDING_VERSION, "project_id": project_id, "run_ref": actual_run,
            "run_plan_ref": active["run_plan_ref"], "task_ref": active["task_ref"],
            "prompt_bundle_ref": active["prompt_bundle_ref"], "context_packet_ref": active["context_packet_ref"],
            "execution_ref": f"{project_id}/executions/{actual_run}",
            "runtime_root_digest": "sha256:" + sha256_bytes(str(runtime).encode("utf-8")),
            "execution_baseline": {
                "canonical_product_digest": baseline, "snapshot_product_digest": snapshot_digest,
                "control_plane_digest": before_control, "base_revision": baseline,
                "task_ref": active["task_ref"], "prompt_bundle_ref": active["prompt_bundle_ref"],
                "run_plan_ref": active["run_plan_ref"],
            },
            "projection_sources": refs, "projection_files": projection_digests,
        }
        write_data(binding_path, {"execution_binding": binding})
        # The journal is not itself included in our frozen source-control digest.
        # Check all unchanged sources *before* authorizing this one Kernel write.
        if _control_plane_digest(canonical) != before_control or safe_disposable_baseline_revision(canonical) != baseline:
            raise ValidationFailure("BASELINE_CHANGED after binding write")
        # Make the exact metadata file a legitimate new signed phase boundary.
        # Otherwise v0.5.0's validate-project would correctly report an
        # unauthorized extra .harness file after this builder's operation.
        record_phase_boundary(canonical, active, phase="EXECUTION_ROOT_PREPARED",
                              kernel_written_paths=[binding_path.relative_to(canonical).as_posix()],
                              recorded_at=utc_now())
    except Exception:
        # Safe in-process recovery only; host crash/orphans are PH-051-10.
        # Nothing under canonical product is changed. A published binding must
        # never be left pointing at a cleaned-up root.
        if binding_path.exists():
            binding_path.unlink()
        (root / "control").chmod(0o755) if (root / "control").exists() else None
        shutil.rmtree(root)
        raise
    return {"status": "PREPARED", "run_ref": actual_run, "idempotent": False,
            "execution_root": str(root), "product_dir": str(root / "product"),
            "control_dir": str(root / "control"), "output_dir": str(root / "output"),
            "execution_baseline": binding["execution_baseline"]}


# PH-051-10 host-only termination/retirement boundary. None of these paths
# are exposed to the agent, bundled into a handoff, or treated as evidence.
def _runtime_execution_parent(project_root: Path, runtime_root: Path) -> tuple[Path, Path]:
    canonical = Path(project_root).expanduser().resolve(strict=True)
    runtime = _check_disjoint(canonical, Path(runtime_root).expanduser())
    project_doc = load_data(_safe_exact_relative(canonical, ".harness/config/PROJECT.yaml"))["project"]
    project_id = project_doc.get("id")
    if not isinstance(project_id, str) or not _PROJECT_ID.fullmatch(project_id):
        raise SafetyViolation("Untrusted execution project identity")
    parent = runtime / project_id
    if parent.is_symlink():
        raise SafetyViolation("Project runtime container is a symlink")
    if parent.exists():
        details = parent.lstat()
        if not stat.S_ISDIR(details.st_mode) or details.st_uid != os.geteuid():
            raise SafetyViolation("Project runtime directory is not owned by executor")
        # PH-051-04 created an intermediate project directory with the host
        # umask (typically 0755). Tighten this *within* the trusted 0700
        # runtime base before inspecting retired run bytes. Never replace it.
        if details.st_mode & 0o077:
            parent.chmod(0o700)
    else:
        parent.mkdir(mode=0o700)
    return canonical, parent


def _runtime_run_root(project_root: Path, runtime_root: Path, run_ref: str) -> tuple[Path, Path]:
    if not isinstance(run_ref, str) or not _RUN_ID.fullmatch(run_ref):
        raise SafetyViolation("Unsafe Run identity for cleanup")
    _, parent = _runtime_execution_parent(project_root, runtime_root)
    executions = parent / "executions"
    if executions.is_symlink():
        raise SafetyViolation("Execution directory symlink")
    if executions.exists():
        details = executions.lstat()
        if not stat.S_ISDIR(details.st_mode) or details.st_uid != os.geteuid():
            raise SafetyViolation("Untrusted execution directory")
        if details.st_mode & 0o077:
            executions.chmod(0o700)
    return parent, executions / run_ref


def _erase_transient_run_secrets(run_root: Path) -> None:
    """Securely unlink small bounded host-only env files, never follow links.

    Files may be absent after ordinary TemporaryDirectory cleanup. The entire
    disposable tree is always private; a suspicious file blocks deletion and
    remains quarantined for explicit operator inspection.
    """
    for directory in run_root.iterdir():
        if not directory.name.startswith(".ph05110-env-"):
            continue
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or info.st_uid != os.geteuid():
            raise SafetyViolation("Unsafe transient host secret directory")
        contents = list(directory.iterdir())
        if len(contents) > 1 or any(item.name != "environment" for item in contents):
            raise SafetyViolation("Unrecognized transient secret file")
        for item in contents:
            metadata = item.lstat()
            if (not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or
                    metadata.st_nlink != 1 or metadata.st_uid != os.geteuid() or
                    metadata.st_size > 1024 * 1024):
                raise SafetyViolation("Unsafe transient secret file")
            flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(item, flags)
            try:
                opened = os.fstat(fd)
                if (opened.st_ino, opened.st_dev) != (metadata.st_ino, metadata.st_dev):
                    raise SafetyViolation("Host secret changed during erasure")
                remaining = metadata.st_size
                while remaining:
                    chunk = min(remaining, 8192)
                    os.write(fd, b"\0" * chunk)
                    remaining -= chunk
                os.fsync(fd)
            finally:
                os.close(fd)
            item.unlink()
        directory.rmdir()


def finalize_execution_root(project_root: Path, runtime_root: Path, *, run_ref: str,
                            quarantine: bool = False) -> dict[str, Any]:
    """Retire the exact per-Run disposable root without touching product/control.

    Caller must first attest that matching Podman children terminated and that
    any active product apply journal was recovered. A quarantine is never
    adopted as input to a new Run. Cleanup failure does not alter Run outcome.
    """
    try:
        parent, root = _runtime_run_root(project_root, runtime_root, run_ref)
        if not root.exists() and not root.is_symlink():
            return {"status": "ALREADY_CLEANED", "run_ref": run_ref}
        if root.is_symlink() or not root.is_dir() or root.stat().st_uid != os.geteuid():
            raise SafetyViolation("Untrusted per-Run execution root")
        if (root / ".apply-journal").exists() or (root / ".apply-journal").is_symlink():
            raise SafetyViolation("Apply recovery must precede disposable-root retirement")
        bucket = parent / ("quarantine" if quarantine else "retired")
        if bucket.is_symlink():
            raise SafetyViolation("Unsafe execution retirement directory")
        bucket.mkdir(mode=0o700, exist_ok=True)
        if bucket.stat().st_uid != os.geteuid() or bucket.stat().st_mode & 0o077:
            raise SafetyViolation("Untrusted execution retirement directory")
        target = bucket / (run_ref + "-" + os.urandom(8).hex())
        root.rename(target)  # no further retry can claim the same partial root
        from .stage_transactions import _fsync_directory
        _fsync_directory(root.parent)
        _fsync_directory(bucket)
        try:
            _erase_transient_run_secrets(target)
            if quarantine:
                return {"status": "QUARANTINED", "run_ref": run_ref}
            if not shutil.rmtree.avoids_symlink_attacks:
                raise SafetyViolation("Host cannot safely remove an untrusted disposable tree")
            control = target / "control"
            if control.exists():
                details = control.lstat()
                if not stat.S_ISDIR(details.st_mode) or stat.S_ISLNK(details.st_mode):
                    raise SafetyViolation("Unsafe read-only projection during cleanup")
                control.chmod(0o700)  # host owner only; container has ended
            shutil.rmtree(target)
            _fsync_directory(bucket)
            return {"status": "CLEANED", "run_ref": run_ref}
        except (OSError, SafetyViolation):
            return {"status": "CLEANUP_FAILED", "run_ref": run_ref,
                    "quarantined": True}
    except (OSError, SafetyViolation, ValidationFailure):
        return {"status": "CLEANUP_FAILED", "run_ref": run_ref,
                "quarantined": False}


def quarantine_orphan_execution_roots(project_root: Path, runtime_root: Path, *,
                                     exclude: set[str] | None = None) -> dict[str, Any]:
    """Discover abandoned Run roots after container shutdown is verified.

    Unknown/unsafe directory entries cause a conservative failure, never
    recursive deletion outside the private project runtime directory.
    """
    try:
        parent, _ = _runtime_run_root(project_root, runtime_root, "RUN-RECOVERY")
        executions = parent / "executions"
        if not executions.exists():
            return {"status": "PASS", "quarantined": [], "cleanup_failures": []}
        if executions.is_symlink() or not executions.is_dir():
            raise SafetyViolation("Unsafe runtime executions directory")
        quarantined: list[str] = []
        failures: list[str] = []
        for item in sorted(executions.iterdir()):
            if not _RUN_ID.fullmatch(item.name) or item.is_symlink() or not item.is_dir():
                raise SafetyViolation("Untrusted orphan execution root entry", item.name)
            if item.name in (exclude or set()):
                continue
            outcome = finalize_execution_root(project_root, runtime_root, run_ref=item.name,
                                              quarantine=True)
            if outcome["status"] == "QUARANTINED":
                quarantined.append(item.name)
            elif outcome["status"] == "CLEANUP_FAILED":
                failures.append(item.name)
        return {"status": "PASS" if not failures else "BLOCKED",
                "quarantined": quarantined, "cleanup_failures": failures}
    except (OSError, ValidationFailure, SafetyViolation) as exc:
        return {"status": "BLOCKED", "reason_code": "SANDBOX_POLICY_FAILURE",
                "diagnostic": type(exc).__name__}

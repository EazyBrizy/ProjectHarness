from __future__ import annotations

import fnmatch
import json
import os
from pathlib import Path
import stat
from typing import Any

from .errors import SafetyViolation, ValidationFailure
from .hashing import sha256_bytes, sha256_file
from .serialization import canonical_json_bytes, load_data, write_data
from .platform_fs import _native_io_path, native_walk

EXCLUDED_ROOT_DIRS = {".harness", ".git", "node_modules", ".venv", "venv", "__pycache__"}
EXCLUDED_NAMES = {".DS_Store"}
PROTECTED_ROOT_FILES = {
    "AGENTS.md",
    "CODEX_START.md",
    "HANDOFF_SUMMARY.md",
    "PROJECT.md",
    "ARCHITECTURE.md",
    "TECHNOLOGY.md",
    "ROADMAP.md",
    "STATUS.md",
    "MANIFEST.sha256",
    "VALIDATION_REPORT.json",
}
EXCLUDED_ROOT_FILES = set(PROTECTED_ROOT_FILES)
AGENT_RESULT_MAX_BYTES = 1024 * 1024
OPERATION_JOURNAL_SCHEMA_VERSION = 1


def snapshot_product(root: Path) -> dict[str, dict[str, Any]]:
    root = root.resolve()
    result: dict[str, dict[str, Any]] = {}
    for current, dirs, files in native_walk(root):
        base = Path(current)
        if base == root:
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_ROOT_DIRS)
        else:
            dirs[:] = sorted(d for d in dirs if d not in {"__pycache__", ".pytest_cache"})
        for name in sorted(files):
            if name in EXCLUDED_NAMES or (base == root and name in EXCLUDED_ROOT_FILES):
                continue
            path = base / name
            if path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            result[rel] = {
                "sha256": sha256_file(path),
                "size": _native_io_path(path).stat().st_size,
            }
    return result


def diff_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list[str]]:
    before_keys = set(before)
    after_keys = set(after)
    added = sorted(after_keys - before_keys)
    deleted = sorted(before_keys - after_keys)
    modified = sorted(
        path
        for path in before_keys & after_keys
        if before[path].get("sha256") != after[path].get("sha256")
        or before[path].get("size") != after[path].get("size")
    )
    return {"added": added, "modified": modified, "deleted": deleted}


def path_matches(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        p = pattern.replace("\\", "/")
        if p in {"**", "*"}:
            return True
        if p.endswith("/**"):
            prefix = p[:-3].rstrip("/")
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatchcase(normalized, p):
            return True
    return False


def validate_scope(diff: dict[str, list[str]], scope: dict[str, Any]) -> dict[str, Any]:
    writes = [str(item) for item in scope.get("write", [])]
    forbidden = [str(item) for item in scope.get("forbidden", [])]
    changed = sorted(diff["added"] + diff["modified"] + diff["deleted"])
    forbidden_hits = [path for path in changed if path_matches(path, forbidden)]
    outside = [path for path in changed if not path_matches(path, writes)]
    return {
        "status": "PASS" if not forbidden_hits and not outside else "FAIL",
        "changed_paths": changed,
        "forbidden_hits": forbidden_hits,
        "outside_write_scope": outside,
        "declared_write_scope": writes,
        "declared_forbidden_scope": forbidden,
    }


def _record_for_path(path: Path) -> dict[str, Any]:
    info = _native_io_path(path).lstat()
    if stat.S_ISLNK(info.st_mode):
        return {"type": "SYMLINK", "target": os.readlink(path), "size": info.st_size, "nlink": info.st_nlink}
    if not stat.S_ISREG(info.st_mode):
        return {"type": "NON_REGULAR", "mode": info.st_mode, "size": info.st_size, "nlink": info.st_nlink}
    return {
        "type": "REGULAR",
        "sha256": sha256_file(path),
        "size": info.st_size,
        "nlink": info.st_nlink,
    }


def scan_protected_control_plane(root: Path, *, exclude_paths: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """Return every protected file-like path without following symlinks.

    `.harness/**` is default-protected. Generated root views are protected too.
    Only exact protocol anchor paths supplied by the Kernel may be excluded to
    avoid self-referential snapshot/journal hashing.
    """
    root = root.resolve()
    excluded = {item.replace("\\", "/") for item in (exclude_paths or set())}
    result: dict[str, dict[str, Any]] = {}
    harness = root / ".harness"
    if harness.exists():
        for current, dirs, files in native_walk(harness, followlinks=False):
            base = Path(current)
            retained_dirs: list[str] = []
            for name in sorted(dirs):
                path = base / name
                rel = path.relative_to(root).as_posix()
                if rel in excluded:
                    continue
                if path.is_symlink():
                    result[rel] = _record_for_path(path)
                else:
                    retained_dirs.append(name)
            dirs[:] = retained_dirs
            for name in sorted(files):
                path = base / name
                rel = path.relative_to(root).as_posix()
                if rel in excluded:
                    continue
                result[rel] = _record_for_path(path)
    for name in sorted(PROTECTED_ROOT_FILES):
        path = root / name
        if path.exists() or path.is_symlink():
            if name not in excluded:
                result[name] = _record_for_path(path)
    return result


def snapshot_protected_control_plane(
    root: Path,
    *,
    expected_paths: list[str],
    allowed_agent_output_path: str,
) -> dict[str, Any]:
    excluded = set(expected_paths)
    files = scan_protected_control_plane(root, exclude_paths=excluded)
    return {
        "files": files,
        "expected_paths": list(expected_paths),
        "allowed_agent_output_path": allowed_agent_output_path,
    }


def diff_protected_control_plane(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    allowed_agent_output_path: str | None,
) -> dict[str, Any]:
    ignored = {allowed_agent_output_path} if allowed_agent_output_path else set()
    before = {key: value for key, value in (baseline or {}).items() if key not in ignored}
    after = {key: value for key, value in (current or {}).items() if key not in ignored}
    before_keys = set(before)
    after_keys = set(after)
    deleted = sorted(before_keys - after_keys)
    unexpected = sorted(after_keys - before_keys)
    changed: list[str] = []
    unsafe: list[dict[str, Any]] = []
    for path in sorted(before_keys & after_keys):
        old = before[path]
        new = after[path]
        if old.get("type", "REGULAR") != new.get("type", "REGULAR"):
            changed.append(path)
            unsafe.append({"path": path, "reason": f"type changed to {new.get('type')}"})
            continue
        if new.get("type", "REGULAR") != "REGULAR":
            unsafe.append({"path": path, "reason": f"protected path is {new.get('type')}"})
        elif int(new.get("nlink", 1)) != 1:
            unsafe.append({"path": path, "reason": f"protected regular file has {new.get('nlink')} hardlinks"})
        if (
            old.get("sha256") != new.get("sha256")
            or old.get("size") != new.get("size")
            or old.get("nlink", 1) != new.get("nlink", 1)
        ):
            changed.append(path)
    for path in unexpected:
        item = after[path]
        if item.get("type", "REGULAR") != "REGULAR":
            unsafe.append({"path": path, "reason": f"unexpected protected path is {item.get('type')}"})
    return {
        "status": "PASS" if not changed and not deleted and not unexpected and not unsafe else "FAIL",
        "changed": changed,
        "deleted": deleted,
        "unexpected": unexpected,
        "unsafe": unsafe,
    }


def _journal_relative(active: dict[str, Any]) -> str:
    value = active.get("operation_journal_path")
    if value:
        return str(value)
    run_ref = str(active.get("run_ref") or "UNKNOWN")
    return f".harness/runtime/OPERATION_JOURNAL/{run_ref}.yaml"


def write_snapshot(
    path: Path,
    root: Path,
    *,
    task_ref: str,
    run_ref: str,
    allowed_agent_output_path: str,
    operation_journal_path: str,
    trusted_task: dict[str, Any] | None = None,
    implementation_stage: str | None = None,
    maintenance_route: str | None = None,
    maintenance_plan_ref: str | None = None,
) -> dict[str, Any]:
    snapshot_rel = path.resolve().relative_to(root.resolve()).as_posix()
    expected_paths = [snapshot_rel, operation_journal_path]
    product_files = snapshot_product(root)
    snapshot = {
        "task_ref": task_ref,
        "run_ref": run_ref,
        "root": ".",
        "product_files": product_files,
        "protected_control_plane": snapshot_protected_control_plane(
            root,
            expected_paths=expected_paths,
            allowed_agent_output_path=allowed_agent_output_path,
        ),
        "trusted_task_contract": trusted_task,
    }
    if implementation_stage is not None:
        snapshot["implementation_stage"] = implementation_stage
    if maintenance_route is not None:
        snapshot["maintenance_route"] = maintenance_route
        snapshot["maintenance_plan_ref"] = maintenance_plan_ref
    value = {"snapshot": snapshot}
    write_data(path, value)
    return value


def _boundary_payload(
    *,
    sequence: int,
    phase: str,
    previous_digest: str | None,
    protected: dict[str, Any],
    kernel_written_paths: list[str],
    recorded_at: str,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "phase": phase,
        "previous_boundary_digest": previous_digest,
        "protected_control_plane": protected,
        "kernel_written_paths": sorted(set(kernel_written_paths)),
        "recorded_at": recorded_at,
    }


def record_phase_boundary(
    root: Path,
    active: dict[str, Any],
    *,
    phase: str,
    kernel_written_paths: list[str] | None = None,
    recorded_at: str,
) -> dict[str, Any]:
    root = root.resolve()
    journal_rel = _journal_relative(active)
    journal_path = root / journal_rel
    allowed = str(active.get("allowed_agent_output_path") or f".harness/runtime/AGENT_RESULTS/{active['run_ref']}.json")
    protected = {
        "files": scan_protected_control_plane(root, exclude_paths={journal_rel}),
        "expected_paths": [journal_rel],
        "allowed_agent_output_path": allowed,
    }
    if journal_path.exists():
        journal_doc = load_data(journal_path)
        journal = journal_doc.get("operation_journal")
        if not isinstance(journal, dict):
            raise SafetyViolation("Operation journal envelope is invalid", journal_rel)
    else:
        journal = {
            "schema_version": OPERATION_JOURNAL_SCHEMA_VERSION,
            "run_ref": active["run_ref"],
            "task_ref": active["task_ref"],
            "snapshot_ref": active.get("snapshot_ref"),
            "implementation_stage": active.get("implementation_stage"),
            "boundaries": [],
        }
        if active.get("maintenance_route") is not None:
            journal["maintenance_route"] = active.get("maintenance_route")
            journal["maintenance_plan_ref"] = active.get("maintenance_plan_ref")
        journal_doc = {"operation_journal": journal}
        journal = journal_doc["operation_journal"]
    if journal.get("run_ref") != active.get("run_ref") or journal.get("task_ref") != active.get("task_ref"):
        raise SafetyViolation("Operation journal is bound to another run", journal_rel)
    boundaries = journal.setdefault("boundaries", [])
    previous = boundaries[-1].get("boundary_digest") if boundaries else None
    payload = _boundary_payload(
        sequence=len(boundaries) + 1,
        phase=phase,
        previous_digest=previous,
        protected=protected,
        kernel_written_paths=kernel_written_paths or [],
        recorded_at=recorded_at,
    )
    boundary = {**payload, "boundary_digest": f"sha256:{sha256_bytes(canonical_json_bytes(payload))}"}
    boundaries.append(boundary)
    write_data(journal_path, journal_doc)
    return boundary


def load_phase_boundary(root: Path, active: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    journal_rel = _journal_relative(active)
    journal_path = root / journal_rel
    if not _native_io_path(journal_path).exists():
        snapshot = load_data(root / active["snapshot_path"])["snapshot"]
        return {
            "sequence": 0,
            "phase": "RUN_RESERVED_SNAPSHOT",
            "protected_control_plane": snapshot["protected_control_plane"],
            "kernel_written_paths": [],
            "boundary_digest": None,
        }
    info = _native_io_path(journal_path).lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SafetyViolation("Operation journal must be an exact regular file", journal_rel)
    journal = load_data(journal_path).get("operation_journal")
    if not isinstance(journal, dict) or journal.get("schema_version") != OPERATION_JOURNAL_SCHEMA_VERSION:
        raise SafetyViolation("Operation journal schema is invalid", journal_rel)
    if journal.get("run_ref") != active.get("run_ref") or journal.get("task_ref") != active.get("task_ref"):
        raise SafetyViolation("Operation journal run/task binding is invalid", journal_rel)
    previous: str | None = None
    boundaries = journal.get("boundaries") or []
    if not boundaries:
        raise SafetyViolation("Operation journal has no signed phase boundary", journal_rel)
    for expected_sequence, boundary in enumerate(boundaries, 1):
        payload = {key: boundary.get(key) for key in (
            "sequence", "phase", "previous_boundary_digest", "protected_control_plane", "kernel_written_paths", "recorded_at"
        )}
        expected_digest = f"sha256:{sha256_bytes(canonical_json_bytes(payload))}"
        if boundary.get("sequence") != expected_sequence or boundary.get("previous_boundary_digest") != previous or boundary.get("boundary_digest") != expected_digest:
            raise SafetyViolation("Operation journal boundary chain is invalid", {"path": journal_rel, "sequence": expected_sequence})
        previous = boundary["boundary_digest"]
    return boundaries[-1]


def secure_read_agent_result(
    root: Path,
    expected_relative: str,
    *,
    max_bytes: int = AGENT_RESULT_MAX_BYTES,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    root = root.resolve()
    normalized = expected_relative.replace("\\", "/")
    result_root = (root / ".harness/runtime/AGENT_RESULTS").resolve()
    path = root / normalized
    try:
        resolved_parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise ValidationFailure("Agent Task Result parent directory is missing", normalized) from exc
    if resolved_parent != result_root:
        raise SafetyViolation("Agent Task Result path escapes the exact result channel", normalized)
    try:
        before = path.lstat()
    except FileNotFoundError as exc:
        raise ValidationFailure("Agent Task Result is missing", normalized) from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise SafetyViolation("Agent Task Result must be a regular file, not a symlink or special file", normalized)
    if before.st_nlink != 1:
        raise SafetyViolation("Agent Task Result hardlinks are not allowed", {"path": normalized, "nlink": before.st_nlink})
    if before.st_size > max_bytes:
        raise SafetyViolation("Agent Task Result exceeds the distribution size limit", {"path": normalized, "size": before.st_size, "limit": max_bytes})
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise SafetyViolation("Agent Task Result changed type while being read", normalized)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise SafetyViolation("Agent Task Result was replaced while being opened", normalized)
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    finally:
        os.close(fd)
    if len(data) > max_bytes:
        raise SafetyViolation("Agent Task Result exceeds the distribution size limit", {"path": normalized, "limit": max_bytes})
    def unique_pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def reject_constant(value):
        raise ValueError('nonfinite JSON number')
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ValidationFailure("Agent Task Result must be valid UTF-8 JSON", {"path": normalized, "error": str(exc)}) from exc
    if not isinstance(value, dict):
        raise ValidationFailure("Agent Task Result must be a JSON object")
    digest = f"sha256:{sha256_bytes(data)}"
    metadata = {
        "path": normalized,
        "sha256": digest,
        "size": len(data),
        "device": opened.st_dev,
        "inode": opened.st_ino,
    }
    return value, digest, metadata


def assert_agent_result_unchanged(root: Path, metadata: dict[str, Any]) -> None:
    value, digest, current = secure_read_agent_result(root, str(metadata["path"]))
    del value
    if digest != metadata.get("sha256") or current.get("device") != metadata.get("device") or current.get("inode") != metadata.get("inode"):
        raise SafetyViolation("Agent Task Result changed after validation", {"expected": metadata, "current": current})


def check_control_plane(
    root: Path,
    active: dict[str, Any],
    *,
    allow_missing_agent_result: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    try:
        boundary = load_phase_boundary(root, active)
    except (SafetyViolation, ValidationFailure) as exc:
        return {
            "status": "FAIL",
            "phase": "UNKNOWN",
            "changed": [],
            "deleted": [],
            "unexpected": [],
            "unsafe": [{"path": _journal_relative(active), "reason": str(exc)}],
            "agent_result": {"status": "NOT_CHECKED"},
        }
    protected = boundary.get("protected_control_plane") or {}
    expected_paths = {str(item) for item in protected.get("expected_paths") or []}
    allowed = str(protected.get("allowed_agent_output_path") or active.get("allowed_agent_output_path") or "")
    current = scan_protected_control_plane(root, exclude_paths=expected_paths)
    diff = diff_protected_control_plane(protected.get("files") or {}, current, allowed_agent_output_path=allowed)
    agent_check: dict[str, Any] = {"status": "ABSENT", "path": allowed}
    if allowed:
        candidate = root / allowed
        if candidate.exists() or candidate.is_symlink():
            try:
                value, digest, metadata = secure_read_agent_result(root, allowed)
                agent_check = {
                    "status": "PASS",
                    "path": allowed,
                    "sha256": digest,
                    "size": metadata["size"],
                    "schema_version": value.get("schema_version"),
                    "task_ref": value.get("task_ref"),
                    "run_ref": value.get("run_ref"),
                }
                if value.get("task_ref") != active.get("task_ref") or value.get("run_ref") != active.get("run_ref"):
                    raise ValidationFailure("Agent Task Result references another task/run")
            except (SafetyViolation, ValidationFailure) as exc:
                agent_check = {"status": "FAIL", "path": allowed, "reason": str(exc)}
        elif not allow_missing_agent_result:
            agent_check = {"status": "FAIL", "path": allowed, "reason": "required Agent Task Result is missing"}
    status = "PASS" if diff["status"] == "PASS" and agent_check["status"] in {"PASS", "ABSENT"} else "FAIL"
    return {**diff, "status": status, "phase": boundary.get("phase"), "boundary_digest": boundary.get("boundary_digest"), "agent_result": agent_check}

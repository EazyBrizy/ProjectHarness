"""PH-051-06: exact sandbox output and kernel-owned, unverified results.

The PH-051-02 preliminary classifier remains for unbound protocol test doubles.
Only an exact current Run may publish a schema-validated Agent Result; neither
the agent declaration nor process exit authorizes verification/apply/complete.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
from datetime import datetime, timezone
from typing import Any, Mapping

from project_harness.hashing import sha256_bytes
from project_harness.safety import scan_exact_secret, redact_exact_secrets
from project_harness.serialization import canonical_json_bytes, load_data
from project_harness.util import utc_now
from project_harness.workspace import check_control_plane, record_phase_boundary


_ALLOWED_REASON_CODES = frozenset({
    "EXECUTOR_UNAVAILABLE", "EXECUTOR_EXIT_NONZERO", "EXECUTOR_TIMEOUT",
    "SANDBOX_UNAVAILABLE", "SANDBOX_POLICY_FAILURE", "RESULT_MISSING",
    "RESULT_INVALID", "OUTPUT_LIMIT_EXCEEDED", "NETWORK_NOT_APPROVED",
    "SECRET_REFERENCE_MISSING", "SECRET_LEAK_DETECTED", "SCOPE_VIOLATION",
    "BASELINE_CHANGED", "VERIFICATION_FAILED", "APPLY_FAILED_RECOVERABLE",
})
# This bounded preliminary read does NOT constitute complete result-channel validation.
_MAX_PRELIMINARY_RESULT_BYTES = 1024 * 1024


def _failure(reason: str, exit_code: int | None) -> dict[str, Any]:
    return {
        "status": "BLOCKED" if reason in {
            "SANDBOX_UNAVAILABLE", "SANDBOX_POLICY_FAILURE", "NETWORK_NOT_APPROVED",
            "SECRET_REFERENCE_MISSING", "SECRET_LEAK_DETECTED", "SCOPE_VIOLATION", "BASELINE_CHANGED",
        } else "FAILED_RETRYABLE",
        "reason_code": reason,
        "exit_code": exit_code,
        "result_validated": False,
    }


def classify_process_result(process_result: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """Reject optimistic success; retain only minimal nonsecret process metadata."""
    if not isinstance(process_result, dict) or not isinstance(output_dir, Path):
        return _failure("RESULT_INVALID", None)
    code = process_result.get("exit_code")
    if isinstance(code, bool) or (code is not None and not isinstance(code, int)):
        return _failure("RESULT_INVALID", None)
    # Error fields are emitted by the *trusted sandbox runner*, not the agent's JSON.
    reason = process_result.get("reason_code")
    if reason is not None:
        if not isinstance(reason, str) or reason not in _ALLOWED_REASON_CODES:
            return _failure("SANDBOX_POLICY_FAILURE", code)
        return _failure(reason, code)
    if process_result.get("output_limit_exceeded") is True:
        return _failure("OUTPUT_LIMIT_EXCEEDED", code)
    termination = process_result.get("termination_reason")
    if not isinstance(termination, str):
        return _failure("SANDBOX_POLICY_FAILURE", code)
    if termination == "TIMED_OUT":
        return _failure("EXECUTOR_TIMEOUT", code)
    if termination == "SANDBOX_UNAVAILABLE":
        return _failure("SANDBOX_UNAVAILABLE", code)
    if termination not in {"EXITED", "SIGNALED"}:
        return _failure("SANDBOX_POLICY_FAILURE", code)
    if termination == "SIGNALED" or code is None or code != 0:
        return _failure("EXECUTOR_EXIT_NONZERO", code)
    path = output_dir / "agent-result.json"
    try:
        directory = output_dir.lstat()
        if not stat.S_ISDIR(directory.st_mode):
            return _failure("RESULT_INVALID", code)
        metadata = path.lstat()
    except FileNotFoundError:
        return _failure("RESULT_MISSING", code)
    except (OSError, ValueError):
        return _failure("RESULT_INVALID", code)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1 or metadata.st_size > _MAX_PRELIMINARY_RESULT_BYTES:
        return _failure("RESULT_INVALID", code)
    fd: int | None = None
    try:
        # O_NOFOLLOW+fstat prevent the initial syntax probe following a swapped
        # agent-result symlink. PH-051-06 still owns the full channel contract.
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        active = os.fstat(fd)
        if (not stat.S_ISREG(active.st_mode) or active.st_nlink != 1 or
                (active.st_dev, active.st_ino) != (metadata.st_dev, metadata.st_ino) or
                active.st_size > _MAX_PRELIMINARY_RESULT_BYTES):
            return _failure("RESULT_INVALID", code)
        data = os.read(fd, _MAX_PRELIMINARY_RESULT_BYTES + 1)
        if len(data) > _MAX_PRELIMINARY_RESULT_BYTES or not isinstance(json.loads(data.decode("utf-8")), dict):
            return _failure("RESULT_INVALID", code)
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        return _failure("RESULT_INVALID", code)
    finally:
        if fd is not None:
            os.close(fd)
    return {
        "status": "PENDING_RESULT_VALIDATION",
        "reason_code": None,
        "exit_code": 0,
        "result_validated": False,
        "next_step": "PH-051-06 exact result-channel and schema validation",
    }


# This is a *different* API from the PH-051-02 preliminary syntax probe.
# Keeping the preliminary function makes existing unauthenticated protocol
# fixtures harmless; a bound adapter must use normalize_exact_execution_result.
MAX_AGENT_RESULT_BYTES = 1024 * 1024
MAX_PERSISTED_LOG_BYTES = 256 * 1024
_RUN_REF = re.compile(r"RUN-[A-Z0-9][A-Z0-9-]*(?:@[1-9][0-9]*)?\Z")
_TASK_REF = re.compile(r"TSK-[A-Z0-9][A-Z0-9-]*(?:@[1-9][0-9]*)?\Z")
_PROFILE_REF = {"adapter": re.compile(r"ADP-[A-Z0-9][A-Z0-9-]*@[1-9][0-9]*\Z"),
                "sandbox": re.compile(r"SBX-[A-Z0-9][A-Z0-9-]*@[1-9][0-9]*\Z")}
_RESTRICTED_OUTPUT = frozenset({"agent-result.json"})
_AGENT_REQUIRED = frozenset({"schema_version", "task_ref", "run_ref", "status", "summary",
                             "changes", "commands", "tests", "evidence", "blockers"})
_AGENT_OPTIONAL = frozenset({"notes", "stage_scope_violations"})
_ENV_NAME = re.compile(r"[A-Z_][A-Z0-9_]*\Z")
_UNSAFE_ENV = frozenset({"PATH", "HOME", "ENV", "SHELL", "BASH_ENV", "PYTHONPATH",
                         "PYTHONHOME", "LD_PRELOAD", "LD_LIBRARY_PATH", "SSH_AUTH_SOCK",
                         "GIT_ASKPASS", "GIT_SSH_COMMAND"})
_SECRETISH_ENV = re.compile(r"(?:^|_)(?:KEY|TOKEN|SECRET|PASSWORD|PASS|CREDENTIAL|COOKIE|AUTH|SSH|OPENAI|CODEX|GITHUB)(?:_|$)")


class ResultChannelError(ValueError):
    """No untrusted result/log/secret bytes appear in public error messages."""

    def __init__(self, reason_code: str, description: str):
        self.reason_code = reason_code
        super().__init__(description)


def resolve_execution_environment(profile: Mapping[str, Any],
                                  environment: Mapping[str, str] | None = None) -> tuple[dict[str, str], dict[str, str]]:
    """Resolve only pinned ADP allowlist and ENV:name references, never full env.

    Return (nonsecret+secret container env, secret values for *in-memory* scan).
    No secret values are written to a schema/Run plan or returned in diagnostics.
    The caller may pass the values only to the trusted sandbox runner in memory.
    """
    host = os.environ if environment is None else environment
    ordinary = profile.get("environment_allowlist")
    refs = profile.get("secret_environment_refs")
    if not isinstance(ordinary, list) or not isinstance(refs, list) or len(ordinary) > 32 or len(refs) > 16:
        raise ResultChannelError("SANDBOX_POLICY_FAILURE", "invalid environment reference policy")
    if len(set(ordinary)) != len(ordinary) or len(set(refs)) != len(refs):
        raise ResultChannelError("SANDBOX_POLICY_FAILURE", "duplicate environment references")
    result: dict[str, str] = {}
    secrets: dict[str, str] = {}
    for name in ordinary:
        if (not isinstance(name, str) or not _ENV_NAME.fullmatch(name) or name in _UNSAFE_ENV
                or _SECRETISH_ENV.search(name)):
            raise ResultChannelError("SANDBOX_POLICY_FAILURE", "unsafe ordinary environment variable")
        if name in host:
            result[name] = _safe_environment_value(host[name], secret=False)
    for ref in refs:
        if not isinstance(ref, str) or not ref.startswith("ENV:") or not _ENV_NAME.fullmatch(ref[4:]):
            raise ResultChannelError("SANDBOX_POLICY_FAILURE", "only ENV:name secret references are allowed")
        name = ref[4:]
        if name in ordinary or name in secrets:
            raise ResultChannelError("SANDBOX_POLICY_FAILURE", "duplicate/conflicting secret reference")
        if name not in host or not isinstance(host[name], str) or not host[name]:
            raise ResultChannelError("SECRET_REFERENCE_MISSING", f"missing required environment reference: {name}")
        secrets[name] = _safe_environment_value(host[name], secret=True)
        result[name] = secrets[name]
    return result, secrets


def _safe_environment_value(value: Any, *, secret: bool) -> str:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 8192 or any(
        ord(c) < 32 or ord(c) == 127 for c in value
    ):
        raise ResultChannelError("SANDBOX_POLICY_FAILURE", "invalid bounded environment value")
    # Do not place credentials in error strings. Whitespace and '=' inside a
    # *value* are legal; CR/LF/NUL are not (env-file injection / record split).
    return value


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_constant: str) -> None:
    raise ValueError("nonfinite JSON number")


def _read_exact_result(output_dir: Path, *, owner_uid: int) -> bytes:
    """Use lstat/O_NOFOLLOW/fstat with inode+mode+size checks and bounded read."""
    if not isinstance(output_dir, Path) or not output_dir.is_absolute() or output_dir.name != "output":
        raise ResultChannelError("RESULT_INVALID", "output directory must be exact mounted output")
    for ancestor in (output_dir, *output_dir.parents):
        try:
            meta = ancestor.lstat()
        except OSError as exc:
            raise ResultChannelError("RESULT_INVALID", "output path is missing") from exc
        if stat.S_ISLNK(meta.st_mode) or not stat.S_ISDIR(meta.st_mode):
            raise ResultChannelError("RESULT_INVALID", "unsafe output directory component")
    if output_dir.stat().st_uid != owner_uid:
        raise ResultChannelError("RESULT_INVALID", "unexpected result directory owner")
    try:
        entries = {entry.name for entry in output_dir.iterdir()}
    except OSError as exc:
        raise ResultChannelError("RESULT_INVALID", "unreadable output directory") from exc
    if entries - _RESTRICTED_OUTPUT:
        raise ResultChannelError("RESULT_INVALID", "undeclared additional sandbox output")
    if "agent-result.json" not in entries:
        raise ResultChannelError("RESULT_MISSING", "agent result file is missing")
    path = output_dir / "agent-result.json"
    try:
        before = path.lstat()
    except OSError as exc:
        raise ResultChannelError("RESULT_INVALID", "result metadata unavailable") from exc
    if (not stat.S_ISREG(before.st_mode) or before.st_uid != owner_uid or before.st_nlink != 1
            or stat.S_IMODE(before.st_mode) not in {0o600, 0o400}
            or not 0 < before.st_size <= MAX_AGENT_RESULT_BYTES):
        raise ResultChannelError("RESULT_INVALID", "result file type/owner/mode/size invalid")
    fd = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        opened = os.fstat(fd)
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or
            (opened.st_dev, opened.st_ino, opened.st_uid, opened.st_mode, opened.st_size) !=
            (before.st_dev, before.st_ino, before.st_uid, before.st_mode, before.st_size)):
            raise ResultChannelError("RESULT_INVALID", "result file changed during open")
        data = bytearray()
        while len(data) <= MAX_AGENT_RESULT_BYTES:
            chunk = os.read(fd, min(65536, MAX_AGENT_RESULT_BYTES + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(fd)
        if (len(data) != before.st_size or len(data) > MAX_AGENT_RESULT_BYTES or
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) !=
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)):
            raise ResultChannelError("RESULT_INVALID", "result file changed during bounded read")
        # A rename exchange after open must not make the accepted name differ.
        final = path.lstat()
        if (final.st_dev, final.st_ino) != (opened.st_dev, opened.st_ino):
            raise ResultChannelError("RESULT_INVALID", "result name was replaced during read")
        return bytes(data)
    except OSError as exc:
        raise ResultChannelError("RESULT_INVALID", "cannot safely read exact result") from exc
    finally:
        if fd is not None:
            os.close(fd)


def validate_exact_result_channel(output_dir: Path, *, run_ref: str, task_ref: str,
                                  secret_values: Mapping[str, str] | None = None,
                                  owner_uid: int | None = None) -> tuple[dict[str, Any], bytes]:
    """Validate existing SCHEMA-AGENT-TASK-RESULT@1, exact Run/Task and leaks.

    `result_validated` never means independently verified product changes.
    """
    if (not isinstance(run_ref, str) or not _RUN_REF.fullmatch(run_ref) or
        not isinstance(task_ref, str) or not _TASK_REF.fullmatch(task_ref)):
        raise ResultChannelError("RESULT_INVALID", "unbound Run/Task identity")
    raw = _read_exact_result(output_dir, owner_uid=os.geteuid() if owner_uid is None else owner_uid)
    if scan_exact_secret(raw, secret_values or {}):
        raise ResultChannelError("SECRET_LEAK_DETECTED", "secret found in raw result")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_object_no_duplicates,
                           parse_constant=_reject_constant)
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise ResultChannelError("RESULT_INVALID", "invalid UTF-8/JSON agent result") from exc
    if scan_exact_secret(value, secret_values or {}):
        raise ResultChannelError("SECRET_LEAK_DETECTED", "secret found in parsed result")
    if not isinstance(value, dict) or not _AGENT_REQUIRED.issubset(value) or set(value) - (_AGENT_REQUIRED | _AGENT_OPTIONAL):
        raise ResultChannelError("RESULT_INVALID", "Agent Task Result schema properties mismatch")
    if (type(value["schema_version"]) is not int or value["schema_version"] != 1 or
        value["task_ref"] != task_ref or value["run_ref"] != run_ref or
        value["status"] not in {"COMPLETED", "BLOCKED", "FAILED"} or
        not isinstance(value["summary"], str) or not value["summary"].strip()):
        raise ResultChannelError("RESULT_INVALID", "Agent Task Result identity/status/schema invalid")
    changes = value["changes"]
    if (not isinstance(changes, dict) or set(changes) != {"added", "modified", "deleted"} or
        any(not isinstance(changes[key], list) or any(not isinstance(x, str) for x in changes[key])
            for key in changes)):
        raise ResultChannelError("RESULT_INVALID", "Agent Task Result changes invalid")
    if any(not isinstance(value.get(key), list) for key in ("commands", "tests", "evidence", "blockers")):
        raise ResultChannelError("RESULT_INVALID", "Agent Task Result arrays invalid")
    for key in _AGENT_OPTIONAL:
        if key in value and (not isinstance(value[key], list) or
            (key == "stage_scope_violations" and any(not isinstance(x, str) for x in value[key]))):
            raise ResultChannelError("RESULT_INVALID", "Agent Task Result optional array invalid")
    return value, canonical_json_bytes(value)


def _bounded_logs(process_result: dict[str, Any], secrets: Mapping[str, str]) -> tuple[dict[str, bytes], bool]:
    logs: dict[str, bytes] = {}
    leaked = False
    for label in ("stdout", "stderr"):
        value = process_result.get(label, "")
        if not isinstance(value, str):
            raise ResultChannelError("RESULT_INVALID", "runner log is not bounded text")
        # Check entire bounded runner output *before* shortening for persistence.
        if scan_exact_secret(value, secrets):
            leaked = True
        clean = redact_exact_secrets(value, secrets)
        raw = clean.encode("utf-8")
        if len(raw) > MAX_PERSISTED_LOG_BYTES:
            raise ResultChannelError("OUTPUT_LIMIT_EXCEEDED", "runner output exceeds bounded log storage")
        logs[label] = raw
    return logs, leaked


def _validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 48:
        raise ResultChannelError("RESULT_INVALID", "trusted runner timestamp missing")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("naive")
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError as exc:
        raise ResultChannelError("RESULT_INVALID", "runner timestamp invalid") from exc


def _ref_ids(run_ref: str) -> dict[str, str]:
    root, rev = run_ref.rsplit("@", 1) if "@" in run_ref else (run_ref, "1")
    suffix = root + "-R" + rev
    return {"execution": "ART-EXECUTION-" + suffix, "agent": "ART-AGENT-" + suffix,
            "stdout": "ART-STDOUT-" + suffix, "stderr": "ART-STDERR-" + suffix}


def _secure_control_dir(root: Path, name: str) -> Path:
    """Create a kernel-owned directory without following untrusted symlinks."""
    base = root
    for part in (".harness", "runtime", name):
        base /= part
        try:
            info = base.lstat()
        except FileNotFoundError:
            if part in {".harness", "runtime"}:
                raise ResultChannelError("RESULT_INVALID", "missing canonical control parent")
            base.mkdir(mode=0o700)
            info = base.lstat()
        if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
            raise ResultChannelError("RESULT_INVALID", "unsafe control output directory")
    return base


def _exclusive_bytes(path: Path, contents: bytes) -> None:
    fd: int | None = None
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as stream:
            fd = None
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise ResultChannelError("RESULT_INVALID", "cannot persist immutable kernel result") from exc
    finally:
        if fd is not None:
            os.close(fd)


def _publish_verified_schema_only(project_root: Path, record: dict[str, Any],
                                  agent_json: bytes, logs: dict[str, bytes],
                                  *, source_run_ref: str) -> None:
    """Publish bounded records; update existing v0.5.0 control-plane fence.

    Not a Stage transition and not the PH-051-08 product apply transaction.
    Execution-result YAML is published LAST. A partial interruption is a
    quarantined conflict, never trusted as successful normalisation.
    """
    canonical = project_root.resolve(strict=True)
    state_path = canonical / ".harness/state/CURRENT_STATE.yaml"
    current = load_data(state_path).get("state")
    active = current.get("active_run") if isinstance(current, dict) else None
    if not isinstance(active, dict) or active.get("run_ref") != source_run_ref:
        raise ResultChannelError("RESULT_INVALID", "Run no longer active during kernel publication")
    agent_dir = _secure_control_dir(canonical, "AGENT_RESULTS")
    log_dir = _secure_control_dir(canonical, "EXECUTION_LOGS")
    execution_dir = _secure_control_dir(canonical, "EXECUTION_RESULTS")
    ids = _ref_ids(source_run_ref)
    paths = {
        "agent": agent_dir / (source_run_ref + ".json"),
        "stdout": log_dir / (ids["stdout"] + ".log"),
        "stderr": log_dir / (ids["stderr"] + ".log"),
        "execution": execution_dir / (ids["execution"] + ".yaml"),
    }
    blob = {"agent": agent_json, "stdout": logs["stdout"], "stderr": logs["stderr"],
            "execution": canonical_json_bytes({"execution_result": record})}
    if paths["execution"].exists():
        # Only exact immutable replay, with all supporting bytes intact.
        for key, path in paths.items():
            if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1 or path.read_bytes() != blob[key]:
                raise ResultChannelError("RESULT_INVALID", "conflicting immutable execution-result replay")
        return
    if any(p.exists() or p.is_symlink() for p in paths.values()):
        raise ResultChannelError("RESULT_INVALID", "partial/stale execution result; quarantine pending recovery")
    if check_control_plane(canonical, active)["status"] != "PASS":
        raise ResultChannelError("RESULT_INVALID", "control-plane boundary changed before result publication")
    created: list[Path] = []
    try:
        for key in ("stdout", "stderr", "agent", "execution"):
            _exclusive_bytes(paths[key], blob[key])
            created.append(paths[key])
        record_phase_boundary(canonical, active, phase="AGENT_RESULT_NORMALIZED_UNVERIFIED",
                              kernel_written_paths=[p.relative_to(canonical).as_posix() for p in created],
                              recorded_at=utc_now())
        if check_control_plane(canonical, active)["status"] != "PASS":
            raise ResultChannelError("RESULT_INVALID", "post-publication control-plane invariant FAILED")
    except Exception:
        # Only in-process recovery before any later phase transition. Crash
        # recovery of a partial record is PH-051-10; never infer a PASS from it.
        for path in reversed(created):
            try:
                path.unlink()
            except OSError:
                pass
        raise


def normalize_exact_execution_result(process_result: dict[str, Any], output_dir: Path, *,
                                     run_ref: str, task_ref: str, adapter_profile_ref: str,
                                     sandbox_profile_ref: str, execution_root_digest: str,
                                     project_root: Path | None = None,
                                     secret_values: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Bounded, non-optimistic normalized ART plus optional kernel persistence.

    `project_root` must be supplied by an exact, trusted current-Run caller.
    Normalization never marks a Task DONE or modifies canonical product bytes.
    """
    if not isinstance(process_result, dict):
        return _failure("RESULT_INVALID", None)
    secrets = secret_values or {}
    try:
        logs, leaked = _bounded_logs(process_result, secrets)
        if leaked:
            raise ResultChannelError("SECRET_LEAK_DETECTED", "secret appeared in process output")
        preliminary = classify_process_result(process_result, output_dir)
        if preliminary.get("reason_code"):
            return preliminary
        if (not _RUN_REF.fullmatch(run_ref or "") or not _TASK_REF.fullmatch(task_ref or "") or
            not _PROFILE_REF["adapter"].fullmatch(adapter_profile_ref or "") or
            not _PROFILE_REF["sandbox"].fullmatch(sandbox_profile_ref or "") or
            not isinstance(execution_root_digest, str) or
            re.fullmatch(r"sha256:[a-f0-9]{64}", execution_root_digest) is None):
            raise ResultChannelError("RESULT_INVALID", "execution context lacks exact trusted refs/digest")
        # Only trusted sandbox result; an arbitrary agent-authored dictionary is
        # never allowed to claim that it was an isolated Podman process.
        if (process_result.get("backend") != "ROOTLESS_PODMAN" or
            process_result.get("isolation_verified") is not True):
            raise ResultChannelError("SANDBOX_POLICY_FAILURE", "runner isolation attestation missing")
        started = _validate_timestamp(process_result.get("started_at"))
        finished = _validate_timestamp(process_result.get("finished_at"))
        if datetime.fromisoformat(finished.replace("Z", "+00:00")) < datetime.fromisoformat(started.replace("Z", "+00:00")):
            raise ResultChannelError("RESULT_INVALID", "runner timestamps out of order")
        result, canonical_agent_bytes = validate_exact_result_channel(
            output_dir, run_ref=run_ref, task_ref=task_ref, secret_values=secrets)
        ids = _ref_ids(run_ref)
        record = {
            "id": ids["execution"], "run_ref": run_ref if "@" in run_ref else run_ref + "@1",
            "adapter_profile_ref": adapter_profile_ref, "sandbox_profile_ref": sandbox_profile_ref,
            "started_at": started, "finished_at": finished,
            "exit_code": process_result["exit_code"], "termination_reason": process_result["termination_reason"],
            "stdout_artifact_ref": ids["stdout"] if logs["stdout"] else None,
            "stderr_artifact_ref": ids["stderr"] if logs["stderr"] else None,
            "agent_result_ref": ids["agent"],
            "execution_root_digest": execution_root_digest,
            "result_status": result["status"],
        }
        if project_root is not None:
            _publish_verified_schema_only(Path(project_root), record, canonical_agent_bytes, logs, source_run_ref=run_ref)
        return {"status": "PENDING_INDEPENDENT_VERIFICATION" if result["status"] == "COMPLETED" else "AGENT_REPORTED_" + result["status"],
                "reason_code": None, "result_validated": True, "independently_verified": False,
                "verification_eligible": result["status"] == "COMPLETED",
                "agent_result_status": result["status"], "execution_result_ref": ids["execution"],
                "agent_result_ref": ids["agent"], "run_ref": run_ref,
                "execution_result": {"execution_result": record}}
    except ResultChannelError as exc:
        return _failure(exc.reason_code, process_result.get("exit_code") if type(process_result.get("exit_code")) is int else None)
    except (OSError, ValueError, TypeError, KeyError):
        return _failure("RESULT_INVALID", None)

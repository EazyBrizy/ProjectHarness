from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import hashlib
import os
import stat
import tempfile
from pathlib import Path
import shlex
import subprocess
from typing import Any

from .operation_guard import guarded_mutation
from .errors import HarnessError, SafetyViolation, ValidationFailure
if os.name != "nt":
    # Linux-only automatic modules are optional for native Windows manual flows.
    from .apply import ApplyFailure, apply_verified_diff, recover_apply
    from .executors.codex_cli_local import CodexCliLocalAdapter, load_active_codex_profiles
    from .execution_roots import finalize_execution_root, quarantine_orphan_execution_roots
    from .executors.result import resolve_execution_environment, ResultChannelError
    from .sandbox.verification import verify_disposable
    from .sandbox.podman_rootless import RootlessPodmanRunner
from .evidence import normalized_evidence_body, write_normalized_evidence
from .hashing import sha256_file
from .maintenance import active_maintenance, execution_stage, finalize_maintenance, maintenance_for_task
from .prompting import ensure_current_project_contract, reserve_run
from .render import render_roadmap, render_status
from .serialization import append_jsonl, load_data, write_data
from .stages import _product_baseline_revision, load_current_target_level, load_stage_state, runtime_continuation
from .stage_gate_lifecycle import evaluate_stage_gate_readiness, materialize_preparation_task_evidence
from .util import resolve_inside, utc_now
from .platform_fs import ensure_native_path, _native_io_path, native_resolve, native_glob, native_iterdir
from .workspace import (
    load_phase_boundary,
    assert_agent_result_unchanged,
    check_control_plane,
    diff_snapshots,
    record_phase_boundary,
    secure_read_agent_result,
    snapshot_product,
    validate_scope,
)

RESULT_STATUSES = {"COMPLETED", "BLOCKED", "FAILED"}
SHELL_META = {"|", "||", "&&", ";", ">", ">>", "<", "2>", "&"}
SAFETY_RECOVERY_ROUTE = "RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN"


def _state(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / ".harness/state/CURRENT_STATE.yaml"
    if not _native_io_path(path).exists():
        raise ValidationFailure("Project Harness state is missing", str(path))
    value = load_data(path)
    if not isinstance(value, dict) or not isinstance(value.get("state"), dict):
        raise ValidationFailure("Project Harness state envelope is invalid", str(path))
    return path, value


def _task(root: Path, task_id: str) -> tuple[dict[str, Any], str]:
    index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
    rel = index["current"].get(task_id)
    if not rel:
        raise ValidationFailure("Unknown task", task_id)
    value = load_data(root / rel)
    task = value.get("task") if isinstance(value, dict) else None
    if not isinstance(task, dict):
        raise ValidationFailure("Task contract envelope is invalid", rel)
    return task, rel


def _write_task_revision(root: Path, task_id: str, **changes: Any) -> dict[str, Any]:
    index_path = root / ".harness/tasks/INDEX.yaml"
    index_doc = load_data(index_path)
    index = index_doc["task_index"]
    current_rel = index["current"][task_id]
    task = load_data(root / current_rel)["task"]
    previous_ref = f"{task['id']}@{task['revision']}"
    task.update(changes)
    task["revision"] = int(task["revision"]) + 1
    task["previous_revision_ref"] = previous_ref
    task["updated_at"] = utc_now()
    new_rel = f".harness/tasks/{task_id}@{task['revision']}.yaml"
    write_data(root / new_rel, {"task": task})
    index["current"][task_id] = new_rel
    write_data(index_path, index_doc)
    return task


def _write_trusted_task_revision(root: Path, trusted_task: dict[str, Any], **changes: Any) -> dict[str, Any]:
    """Create a blocked revision without trusting a possibly modified current task file."""
    task = deepcopy(trusted_task)
    task_id = str(task["id"])
    previous_ref = f"{task_id}@{task['revision']}"
    task.update(changes)
    revision = int(task["revision"]) + 1
    while (_native_io_path(root / f".harness/tasks/{task_id}@{revision}.yaml")).exists():
        revision += 1
    task["revision"] = revision
    task["previous_revision_ref"] = previous_ref
    task["updated_at"] = utc_now()
    new_rel = f".harness/tasks/{task_id}@{revision}.yaml"
    write_data(root / new_rel, {"task": task})

    index_path = root / ".harness/tasks/INDEX.yaml"
    try:
        index_doc = load_data(index_path)
        index = index_doc.get("task_index")
        if not isinstance(index, dict):
            raise ValueError("task_index envelope is missing")
        current = index.setdefault("current", {})
        current[task_id] = new_rel
        order = index.setdefault("order", [])
        if task_id not in order:
            order.append(task_id)
    except Exception:
        index_doc = {"task_index": {"order": [task_id], "current": {task_id: new_rel}, "aliases": {}}}
    write_data(index_path, index_doc)
    return task


def _write_work_package_revision(root: Path, wp_id: str, status: str) -> dict[str, Any]:
    index_path = root / ".harness/work-packages/INDEX.yaml"
    index_doc = load_data(index_path)
    index = index_doc["work_package_index"]
    current_rel = index["current"][wp_id]
    wp = load_data(root / current_rel)["work_package"]
    if wp.get("status") == status:
        return wp
    previous_ref = f"{wp['id']}@{wp['revision']}"
    wp["revision"] = int(wp["revision"]) + 1
    wp["previous_revision_ref"] = previous_ref
    wp["status"] = status
    wp["updated_at"] = utc_now()
    new_rel = f".harness/work-packages/{wp_id}@{wp['revision']}.yaml"
    write_data(root / new_rel, {"work_package": wp})
    index["current"][wp_id] = new_rel
    write_data(index_path, index_doc)
    return wp


def project_status(root: Path) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    _, state_doc = _state(root)
    state = state_doc["state"]
    implementation = load_stage_state(root)
    current_target = load_current_target_level(root, stage_state=implementation)
    task_summary = None
    if state.get("current_task_ref"):
        task, rel = _task(root, state["current_task_ref"])
        task_summary = {
            "task_ref": f"{task['id']}@{task['revision']}",
            "title": task["title"],
            "status": task["status"],
            "implementation_stage": task.get("implementation_stage"),
            "path": rel,
        }
    automatic_phase = automatic_run_phase(root, state.get("active_run"))
    continuation = runtime_continuation(root, state)
    return {
        "status": state.get("project_status"),
        "automatic_run": automatic_phase,
        "next_operator_route": continuation,
        "next_command": continuation.get("command"),
        "handoff_status": state.get("handoff_status"),
        "project_ref": state.get("project_ref"),
        "current_task": task_summary,
        "active_run": state.get("active_run"),
        "completed_task_refs": state.get("completed_task_refs") or [],
        "blocked_task_refs": state.get("blocked_task_refs") or [],
        "next_route": state.get("next_route"),
        "implementation": {
            "target_level": current_target,
            "claimed_current_level": implementation["claimed_current_level"],
            "observed_candidate_level": implementation["observed_candidate_level"],
            "highest_accepted_level": implementation["highest_accepted_level"],
            "active_stage": implementation["active_stage"],
            "permitted_use": implementation.get("permitted_use"),
        },
    }


@guarded_mutation
def next_task(root: Path) -> dict[str, Any]:
    """Advance only a reachable current-stage runtime route; never guess a boundary."""
    ensure_native_path(root, tree=True)
    root = native_resolve(root.expanduser())
    _, state_doc = _state(root)
    state = state_doc["state"]
    implementation = load_stage_state(root)
    current_target = load_current_target_level(root, stage_state=implementation)
    continuation = runtime_continuation(root, state)
    if continuation["route"] == "INVALID_RUNTIME_ROUTE":
        raise ValidationFailure("Persisted runtime has no executable continuation", {
            "project_status": state.get("project_status"), "next_route": state.get("next_route"),
            "current_task_ref": state.get("current_task_ref"), "reason": continuation["reason"],
        })
    operator = {"next_operator_route": continuation, "next_command": continuation["command"]}
    if state.get("project_status") == "TARGET_LEVEL_REACHED":
        return {
            "status": "TARGET_LEVEL_REACHED",
            "active_stage": implementation["active_stage"],
            "target_level": current_target,
            "highest_accepted_level": implementation["highest_accepted_level"],
            "next_route": state.get("next_route") or "TARGET_ALREADY_REACHED", **operator,
        }
    if state.get("project_status") == "BLOCKED":
        if continuation["route"] == "RESUME_STAGE_GATE":
            return {
                "status": "BLOCKED", "blocker_kind": "STAGE_GATE_BLOCKER",
                "blocker_refs": state.get("open_blocker_refs") or [],
                "active_stage": implementation["active_stage"], "target_level": current_target,
                "next_route": "RESOLVE_STAGE_GATE", **operator,
            }
        return {
            "status": "BLOCKED",
            "task_ref": state.get("current_task_ref"),
            "blocker_refs": state.get("open_blocker_refs") or [],
            "next_route": state.get("next_route"), **operator,
        }
    if state.get("current_task_ref") is None:
        route = state.get("next_route")
        if route == "EVALUATE_STAGE_GATE_READINESS":
            # This persisted post-completion boundary can survive interruption
            # between completion and the readiness transaction. `next` is its
            # public, idempotent continuation, never an implicit Stage acceptance.
            evaluation = evaluate_stage_gate_readiness(root, reserve_first=False)
            next_state = _state(root)[1]["state"]
            if next_state.get("next_route") == route and next_state.get("current_task_ref") is None:
                raise ValidationFailure("Gate readiness did not advance its persisted route", evaluation)
            result = next_task(root)
            result["readiness_recovery"] = evaluation.get("status")
            return result
        by_route = {
            "PLAN_ACTIVE_STAGE": "STAGE_PLANNING_REQUIRED",
            "STAGE_GATE_REVIEW": "STAGE_GATE_PENDING",
            "REVIEW_MATURITY_ASSESSMENT": "MATURITY_REVIEW_REQUIRED",
        }
        if route not in by_route:
            raise ValidationFailure("Unknown empty-task Stage boundary", route)
        return {
            "status": by_route[route], "active_stage": implementation["active_stage"],
            "target_level": current_target, "next_route": route,
            "stage_status": "VERIFYING" if route == "STAGE_GATE_REVIEW" else "ACTIVE", **operator,
        }
    if state.get("project_status") != "ACTIVE":
        raise ValidationFailure("Only an ACTIVE project may reserve a Run", state.get("project_status"))
    bundle = reserve_run(root, state["current_task_ref"])
    # Reservation may advance COMPILE_* to EXECUTE_CURRENT_TASK_WITH_CODEX.
    # Return the *post-reservation* executable operation, never stale `next`.
    # Replaying `next` is idempotent and observes the same persisted Run route.
    updated_state = _state(root)[1]["state"]
    updated_operator = runtime_continuation(root, updated_state)
    bundle["next_operator_route"] = updated_operator
    bundle["next_command"] = updated_operator["command"]
    return bundle


def _normalize_command(item: Any, default_timeout: int) -> tuple[list[str], Path | str, int]:
    if isinstance(item, str):
        argv = shlex.split(item)
        cwd: str = "."
        timeout = default_timeout
    elif isinstance(item, dict):
        raw = item.get("argv") or item.get("command")
        if isinstance(raw, str):
            argv = shlex.split(raw)
        elif isinstance(raw, list):
            argv = [str(part) for part in raw]
        else:
            raise ValidationFailure("Verification command requires argv or command", item)
        cwd = str(item.get("cwd", "."))
        timeout = int(item.get("timeout_seconds", default_timeout))
    else:
        raise ValidationFailure("Unsupported verification command", item)
    if not argv:
        raise ValidationFailure("Empty verification command")
    if any(token in SHELL_META for token in argv):
        raise SafetyViolation("Shell control operators are not allowed; commands run without a shell", argv)
    if timeout < 1 or timeout > 1800:
        raise ValidationFailure("Verification timeout must be between 1 and 1800 seconds", timeout)
    return argv, cwd, timeout


def _sanitized_env() -> dict[str, str]:
    allowed_exact = {
        "PATH", "HOME", "USER", "USERNAME", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP",
        "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "PYTHONPATH", "VIRTUAL_ENV",
    }
    env = {key: value for key, value in os.environ.items() if key in allowed_exact or key.startswith("LC_")}
    env.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "CI": "1",
            "NO_COLOR": "1",
        }
    )
    return env


def _run_command(root: Path, item: Any, default_timeout: int) -> dict[str, Any]:
    argv, cwd_value, timeout = _normalize_command(item, default_timeout)
    cwd = resolve_inside(root, cwd_value)
    if not _native_io_path(cwd).is_dir():
        raise ValidationFailure("Verification cwd does not exist", str(cwd_value))
    started = utc_now()
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=_sanitized_env(),
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "argv": argv,
            "cwd": cwd.relative_to(root).as_posix() or ".",
            "started_at": started,
            "completed_at": utc_now(),
            "returncode": completed.returncode,
            "stdout": completed.stdout[-20000:],
            "stderr": completed.stderr[-20000:],
            "status": "PASS" if completed.returncode == 0 else "FAIL",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "cwd": cwd.relative_to(root).as_posix() or ".",
            "started_at": started,
            "completed_at": utc_now(),
            "returncode": None,
            "stdout": (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-20000:] if isinstance(exc.stderr, str) else "",
            "status": "TIMEOUT",
        }
    except OSError as exc:
        return {
            "argv": argv,
            "cwd": cwd.relative_to(root).as_posix() or ".",
            "started_at": started,
            "completed_at": utc_now(),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "status": "ERROR",
        }


def _snapshot(root: Path, active: dict[str, Any]) -> dict[str, Any]:
    value = load_data(root / active["snapshot_path"])
    snapshot = value.get("snapshot") if isinstance(value, dict) else None
    if not isinstance(snapshot, dict):
        raise ValidationFailure("Run snapshot envelope is invalid", active.get("snapshot_path"))
    return snapshot


def _trusted_task(root: Path, active: dict[str, Any]) -> dict[str, Any]:
    snapshot = _snapshot(root, active)
    trusted = snapshot.get("trusted_task_contract")
    if isinstance(trusted, dict) and trusted.get("id"):
        return deepcopy(trusted)
    task_id = str(active["task_ref"]).split("@")[0]
    task, _ = _task(root, task_id)
    return deepcopy(task)


def _next_blocker_id(root: Path, task_id: str) -> str:
    token = task_id.removeprefix("TSK-").rsplit("-", 1)[0] or "PROJECT"
    sequence = len(list(native_glob(root / ".harness/blockers",'BLK-*@1.yaml'))) + 1
    return f"BLK-{token}-{sequence:03d}"


def _safety_block(
    root: Path,
    state_path: Path,
    state_doc: dict[str, Any],
    active: dict[str, Any],
    details: dict[str, Any],
    *,
    command_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Block a run using the trusted snapshot, never the modified Task Contract."""
    state = state_doc["state"]
    trusted_task = _trusted_task(root, active)
    task_id = str(trusted_task["id"])
    run_ref = str(active["run_ref"])
    suffix = run_ref.removeprefix("RUN-")
    evidence_id = f"EVD-{suffix}-SAFETY"
    report_id = f"VAL-{suffix}-SAFETY"
    blocker_id = _next_blocker_id(root, task_id)
    recorded_at = utc_now()
    command_results = list(command_results or [])
    commands_gate = "EXECUTED_BEFORE_DETECTION" if command_results else "NOT_RUN"
    reason = "Protected Project Harness control plane changed after Run reservation"
    recovery = [
        "Restore the project from the trusted handoff archive and start a new Run attempt",
        "Discard the modified control plane and re-run prepare from accepted input",
        "Cancel the route and inspect the safety evidence",
    ]

    report_path = f".harness/reports/{report_id}.yaml"
    write_data(
        root / report_path,
        {
            "validation_report": {
                "id": report_id,
                "kind": "CONTROL_PLANE_SAFETY",
                "task_ref": active["task_ref"],
                "run_ref": run_ref,
                "implementation_stage": trusted_task.get("implementation_stage"),
                **_maintenance_binding(trusted_task),
                "evidence_ref": evidence_id,
                "status": "BLOCKED",
                "gates": {"control_plane": "FAIL", "commands": commands_gate},
                "control_plane": details,
                "command_results": command_results,
                "created_at": recorded_at,
            }
        },
    )
    evidence_path = f".harness/evidence/{evidence_id}.yaml"
    evidence = normalized_evidence_body(
        evidence_id=evidence_id,
        kind="SECURITY_RECORD",
        status="BLOCKED",
        provenance={
            "source_type": "PROJECT_HARNESS_RUNTIME_SAFETY_REPORT",
            "source_ref": report_id,
            "producer": "PROJECT_HARNESS_RUNTIME",
        },
        base_revision=_product_baseline_revision(root),
        criterion_refs=[],
        outcome_refs=[],
        profile_control_refs=["CONTROL_PLANE_INTEGRITY"],
        source_bindings=[{
            "ref": report_id,
            "path": report_path,
            "sha256": f"sha256:{sha256_file(root / report_path)}",
        }],
        created_at=recorded_at,
        task_ref=str(active["task_ref"]),
        run_ref=run_ref,
        report_refs=[report_id],
        rationale=reason,
        validator="PROJECT_HARNESS_RUNTIME",
        details={
            "safety_violation": "CONTROL_PLANE_TAMPERING",
            "gates": {"control_plane": "FAIL", "commands": commands_gate},
            "control_plane": details,
            "commands": command_results,
        },
    )
    write_normalized_evidence(root, evidence)
    blocker = {
        "id": blocker_id,
        "revision": 1,
        "kind": "SAFETY_VIOLATION",
        "task_ref": active["task_ref"],
        "run_ref": run_ref,
        "implementation_stage": trusted_task.get("implementation_stage"),
        **_maintenance_binding(trusted_task),
        "reason": reason,
        "evidence_ref": evidence_id,
        "validation_report_ref": report_id,
        "recovery_options": recovery,
        "resume_condition": "Restore a trusted handoff/control plane and create a new Run attempt; in-place resume is prohibited.",
        "status": "OPEN",
        "created_at": recorded_at,
    }
    write_data(root / f".harness/blockers/{blocker_id}@1.yaml", {"blocker": blocker})
    run = {
        "id": run_ref,
        "task_ref": active["task_ref"],
        "implementation_stage": trusted_task.get("implementation_stage"),
        **_maintenance_binding(trusted_task),
        "attempt_no": active["attempt_no"],
        "run_plan_ref": active["run_plan_ref"],
        "status": "BLOCKED",
        "failure_class": "CONTROL_PLANE_TAMPERING",
        "blocker_ref": blocker_id,
        "evidence_refs": [evidence_id],
        "verification_report_ref": report_id,
        "compensation_status": "NOT_REQUIRED",
        "completed_at": recorded_at,
    }
    write_data(root / f".harness/runtime/RUNS/{run_ref}.yaml", {"run": run})
    blocked_task = _write_trusted_task_revision(
        root,
        trusted_task,
        status="BLOCKED",
        blocker_ref=blocker_id,
        blocked_at=recorded_at,
    )
    blocked_ref = f"{blocked_task['id']}@{blocked_task['revision']}"

    state["active_run"] = None
    state.setdefault("blocked_task_refs", []).append(blocked_ref)
    state.setdefault("open_blocker_refs", []).append(blocker_id)
    state["current_task_ref"] = task_id
    state["project_status"] = "BLOCKED"
    state["next_route"] = SAFETY_RECOVERY_ROUTE
    state["last_safety_violation_ref"] = report_id
    state["updated_at"] = recorded_at
    write_data(state_path, state_doc)
    write_data(
        root / ".harness/state/NEXT_TASK.yaml",
        {
            "next_task": {
                "status": "BLOCKED",
                "task_ref": blocked_ref,
                "run_ref": run_ref,
                "blocker_ref": blocker_id,
                "next_route": SAFETY_RECOVERY_ROUTE,
                "recovery_options": recovery,
            }
        },
    )
    append_jsonl(
        root / ".harness/events/EVENTS.jsonl",
        {
            "type": "SAFETY_VIOLATION",
            "task_ref": active["task_ref"],
            "run_ref": run_ref,
            "blocker_ref": blocker_id,
            "evidence_ref": evidence_id,
            "at": recorded_at,
        },
    )
    try:
        _update_wp_status(root, str(trusted_task["work_package_ref"]))
        render_roadmap(root)
    except Exception:
        # A safety transition must remain reportable even when a protected
        # aggregate/index was itself the tampering target.
        pass
    render_status(root)
    return {
        "status": "BLOCKED",
        "reason": "SAFETY_VIOLATION",
        "task_ref": blocked_ref,
        "run_ref": run_ref,
        "blocker_ref": blocker_id,
        "report_ref": report_id,
        "evidence_ref": evidence_id,
        "next_route": SAFETY_RECOVERY_ROUTE,
        "control_plane": details,
        "commands": command_results,
    }


@guarded_mutation
def verify_current(root: Path, *, allow_command_execution: bool = False) -> dict[str, Any]:
    ensure_native_path(root, tree=True)
    root = native_resolve(root.expanduser())
    state_path, state_doc = _state(root)
    state = state_doc["state"]
    active = state.get("active_run")
    if not isinstance(active, dict):
        raise ValidationFailure("No active run to verify")
    # An automatic Run may never fall back to host commands or fabricate a manual PASS.
    policy = load_data(root / '.harness/config/PROJECT_LOCK.yaml')['project_lock'].get('execution') or {}
    if policy.get('mode') == 'LOCAL_AUTOMATIC' or automatic_run_phase(root, active) is not None:
        raise ValidationFailure("Automatic Run verification is SANDBOXED-only; host verify is forbidden")

    control_plane = check_control_plane(root, active, allow_missing_agent_result=True)
    if control_plane.get("status") != "PASS":
        return _safety_block(root, state_path, state_doc, active, control_plane)

    task_id = str(active["task_ref"]).split("@")[0]
    task, _ = _task(root, task_id)
    snapshot_doc = _snapshot(root, active)
    before = snapshot_doc.get("product_files") or snapshot_doc.get("files") or {}
    verification = task.get("verification") or {}
    commands = verification.get("commands") or []
    command_results: list[dict[str, Any]] = []
    command_gate = "PASS"
    if commands and not allow_command_execution:
        command_gate = "BLOCKED"
    elif allow_command_execution:
        for command in commands:
            result = _run_command(root, command, int(verification.get("timeout_seconds", 300)))
            command_results.append(result)
        if any(item["status"] != "PASS" for item in command_results):
            command_gate = "FAIL"

    # Verification commands execute product code and can therefore attempt a
    # control-plane write. Re-check before the Kernel creates any evidence or
    # advances the phase boundary so such writes cannot be sealed as trusted.
    post_command_control_plane = check_control_plane(root, active, allow_missing_agent_result=True)
    if post_command_control_plane.get("status") != "PASS":
        post_command_control_plane["detected_after_verification_commands"] = bool(command_results)
        return _safety_block(
            root,
            state_path,
            state_doc,
            active,
            post_command_control_plane,
            command_results=command_results,
        )

    after = snapshot_product(root)
    diff = diff_snapshots(before, after)
    scope = validate_scope(diff, task["scope"])
    expected_paths = [str(item) for item in verification.get("expected_paths") or []]
    missing_paths: list[str] = []
    for relative in expected_paths:
        try:
            path = resolve_inside(root, relative)
        except HarnessError as exc:
            missing_paths.append(f"unsafe:{relative}:{exc.code}")
            continue
        if not _native_io_path(path).exists():
            missing_paths.append(relative)
    expected_gate = "PASS" if not missing_paths else "FAIL"
    manual_checks = verification.get("manual_checks") or []
    # Permission alone never proves a check. Intake binds explicit operator
    # observations to every check, the exact Run and current product bytes.
    from .task_manual_evidence import evaluate_manual_evidence
    manual_evidence = evaluate_manual_evidence(root, active)
    manual_gate = manual_evidence['status']
    gates = {
        "control_plane": "PASS",
        "scope": scope["status"],
        "commands": command_gate,
        "expected_paths": expected_gate,
        "manual_checks": manual_gate,
    }
    status = "PASS" if all(value == "PASS" for value in gates.values()) else ("BLOCKED" if "BLOCKED" in gates.values() else "FAIL")
    run_ref = active["run_ref"]
    report_id = f"VAL-{run_ref.removeprefix('RUN-')}"
    evidence_id = f"EVD-{run_ref.removeprefix('RUN-')}"
    # Re-verification (e.g. after a command-disabled BLOCKED check) must not
    # overwrite the report bound by immutable evidence from an earlier check.
    # Keep legacy first-attempt IDs; every later check gets fresh exact refs.
    report_base, evidence_base = report_id, evidence_id
    verification_attempt = 1
    while ((_native_io_path(root / f'.harness/reports/{report_id}.yaml')).exists() or
           (_native_io_path(root / f'.harness/evidence/{evidence_id}.yaml')).exists()):
        verification_attempt += 1
        if verification_attempt > 1000:
            raise ValidationFailure('Verification attempt limit reached; block/resume a new Run')
        report_id = f'{report_base}-V{verification_attempt:03d}'
        evidence_id = f'{evidence_base}-V{verification_attempt:03d}'
    recorded_at = utc_now()
    report = {
        "id": report_id,
        "kind": "TASK_VERIFICATION",
        "task_ref": active["task_ref"],
        "run_ref": run_ref,
        "implementation_stage": task.get("implementation_stage"),
        **_maintenance_binding(task),
        "evidence_ref": evidence_id,
        "status": status,
        "gates": gates,
        "control_plane": control_plane,
        "diff": diff,
        "scope_validation": scope,
        "command_results": command_results,
        "missing_expected_paths": missing_paths,
        "manual_evidence": manual_evidence,
        "created_at": recorded_at,
    }
    report_path = f".harness/reports/{report_id}.yaml"
    write_data(root / report_path, {"validation_report": report})
    evidence_kind = "TEST_REPORT"
    implementation_stage = str(task.get("implementation_stage") or load_stage_state(root).get("active_stage"))
    # A Task verification proves the exact Task/run check, not every Stage criterion
    # that happens to permit TEST_REPORT. A later governed Gate-preparation step may
    # create a criterion-mapped evidence record that source-binds this report.
    evidence = normalized_evidence_body(
        evidence_id=evidence_id,
        kind=evidence_kind,
        status=status,
        provenance={
            "source_type": "PROJECT_HARNESS_RUNTIME_VERIFICATION_REPORT",
            "source_ref": report_id,
            "producer": "PROJECT_HARNESS_RUNTIME",
        },
        base_revision=_product_baseline_revision(root),
        criterion_refs=[],
        outcome_refs=[],
        profile_control_refs=["RUNTIME_TASK_VERIFICATION"],
        source_bindings=[{
            "ref": report_id,
            "path": report_path,
            "sha256": f"sha256:{sha256_file(root / report_path)}",
        }],
        created_at=recorded_at,
        task_ref=str(active["task_ref"]),
        run_ref=str(run_ref),
        report_refs=[report_id],
        rationale="Runtime verification result for the exact post-command product snapshot.",
        validator="PROJECT_HARNESS_RUNTIME",
        details={
            "implementation_stage": implementation_stage,
            **_maintenance_binding(task),
            "gates": gates,
            "control_plane": control_plane,
            "scope_validation": scope,
            "diff": diff,
            "commands": command_results,
            "expected_paths": {"declared": expected_paths, "missing": missing_paths},
            "manual_checks": manual_checks,
            "manual_evidence": manual_evidence,
        },
    )
    evidence_path = f".harness/evidence/{evidence_id}.yaml"
    write_normalized_evidence(root, evidence)
    active["verification_report_ref"] = report_id
    active["verification_report_path"] = report_path
    active["verification_evidence_ref"] = evidence_id
    active["verification_evidence_path"] = evidence_path
    active["control_plane_phase"] = "VERIFIED"
    active["verified_product_diff"] = _actual_change_set(diff)
    # Preserve exact post-verification product digests, not only the path set.
    # A later edit to an already-modified path must force re-verification.
    active["verified_product_files"] = after
    state["next_route"] = "COMPLETE_TASK" if status == "PASS" else ("PROVIDE_MANUAL_VERIFICATION" if status == "BLOCKED" else "FIX_TASK_OR_BLOCK")
    state["updated_at"] = recorded_at
    write_data(state_path, state_doc)
    append_jsonl(root / ".harness/events/EVENTS.jsonl", {"type": "VERIFICATION_FINISHED", "run_ref": run_ref, "status": status, "at": recorded_at})
    render_status(root)
    boundary = record_phase_boundary(
        root,
        active,
        phase="VERIFIED",
        kernel_written_paths=[
            evidence_path,
            report_path,
            ".harness/state/CURRENT_STATE.yaml",
            ".harness/events/EVENTS.jsonl",
            "STATUS.md",
        ],
        recorded_at=recorded_at,
    )
    return {
        "status": status,
        "report_ref": report_id,
        "report_path": report_path,
        "gates": gates,
        "control_plane": control_plane,
        "phase_boundary_digest": boundary["boundary_digest"],
        "diff": diff,
        "commands": command_results,
        "missing_expected_paths": missing_paths,
    }


def _validate_agent_result(value: Any, active: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationFailure("Agent Task Result must be an object")
    required = ["schema_version", "task_ref", "run_ref", "status", "summary", "changes", "commands", "tests", "evidence", "blockers"]
    allowed = set(required) | {"notes", "stage_scope_violations"}
    missing = [field for field in required if field not in value]
    unknown = sorted(set(value) - allowed)
    if missing:
        raise ValidationFailure("Agent Task Result is missing fields", missing)
    if unknown:
        raise ValidationFailure("Agent Task Result contains unknown fields", unknown)
    if type(value.get("schema_version")) is not int or value.get("schema_version") != 1:
        raise ValidationFailure("Unsupported Agent Task Result schema", value.get("schema_version"))
    if value.get("task_ref") != active.get("task_ref") or value.get("run_ref") != active.get("run_ref"):
        raise ValidationFailure(
            "Agent Task Result references a different task/run",
            {
                "expected": {"task_ref": active.get("task_ref"), "run_ref": active.get("run_ref")},
                "actual": {"task_ref": value.get("task_ref"), "run_ref": value.get("run_ref")},
            },
        )
    if value.get("status") not in RESULT_STATUSES:
        raise ValidationFailure("Invalid Agent Task Result status", value.get("status"))
    if not isinstance(value.get("summary"), str) or not value["summary"].strip():
        raise ValidationFailure("Agent Task Result summary must be a non-empty string")
    changes = value.get("changes")
    if not isinstance(changes, dict) or set(changes) != {"added", "modified", "deleted"}:
        raise ValidationFailure("Agent Task Result changes must contain only added/modified/deleted")
    if any(not isinstance(changes.get(key), list) or any(not isinstance(item, str) for item in changes[key]) for key in ("added", "modified", "deleted")):
        raise ValidationFailure("Agent Task Result change lists must contain strings")
    for field in ("commands", "tests", "evidence", "blockers", "notes", "stage_scope_violations"):
        if field in value and not isinstance(value[field], list):
            raise ValidationFailure(f"Agent Task Result {field} must be an array")
    return value


def _actual_change_set(diff: dict[str, Any]) -> dict[str, list[str]]:
    return {key: sorted(str(item) for item in diff.get(key, [])) for key in ("added", "modified", "deleted")}


def _maintenance_binding(value: dict[str, Any]) -> dict[str, Any]:
    route = value.get("maintenance_route")
    if route is None:
        return {}
    return {
        "maintenance_route": route,
        "maintenance_plan_ref": value.get("maintenance_plan_ref"),
    }


def _next_runnable(state: dict[str, Any], root: Path) -> str | None:
    active_stage = execution_stage(root)
    maintenance = active_maintenance(root)
    maintenance_plan_ref = maintenance.get("plan_ref") if maintenance else None
    completed = {str(ref).split("@")[0] for ref in state.get("completed_task_refs") or []}
    for task_id in state.get("task_order") or []:
        if task_id in completed:
            continue
        task, _ = _task(root, task_id)
        if maintenance_plan_ref is not None and task.get("maintenance_plan_ref") != maintenance_plan_ref:
            continue
        if maintenance_plan_ref is None and task.get("maintenance_route") is not None:
            continue
        if task.get("implementation_stage") != active_stage:
            continue
        status = task.get("status")
        if status in {"DONE", "CANCELLED", "SUPERSEDED", "STALE"}:
            continue
        if status == "BLOCKED":
            return None
        deps = set(task.get("depends_on_tasks") or [])
        if deps.issubset(completed):
            return task_id
    return None


def _update_wp_status(root: Path, wp_id: str) -> None:
    wp_index = load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]
    wp = load_data(root / wp_index["current"][wp_id])["work_package"]
    statuses = []
    for task_id in wp.get("mandatory_task_refs") or []:
        task, _ = _task(root, task_id)
        statuses.append(task.get("status"))
    if statuses and all(status == "DONE" for status in statuses):
        target = "COMPLETED"
    elif any(status == "BLOCKED" for status in statuses):
        target = "BLOCKED"
    elif any(status in {"READY", "CLAIMED", "RUNNING", "VERIFYING", "DONE"} for status in statuses):
        target = "IN_PROGRESS"
    else:
        target = "PLANNED"
    _write_work_package_revision(root, wp_id, target)


def _assert_verified_product_unchanged(root: Path, active: dict[str, Any]) -> dict[str, dict[str, Any]]:
    verified = active.get("verified_product_files")
    if not isinstance(verified, dict):
        raise ValidationFailure("Verified product snapshot is missing; run verify again")
    current = snapshot_product(root)
    if current != verified:
        raise ValidationFailure(
            "Project files changed after verification; run verify again",
            {"delta_since_verification": diff_snapshots(verified, current)},
        )
    return current


def _exact_result_relative(root: Path, result_path: Path, active: dict[str, Any]) -> str:
    expected = str(active.get("allowed_agent_output_path") or f".harness/runtime/AGENT_RESULTS/{active['run_ref']}.json")
    supplied = result_path.expanduser()
    if not supplied.is_absolute():
        supplied = root / supplied
    supplied_abs = Path(os.path.abspath(supplied))
    expected_abs = Path(os.path.abspath(root / expected))
    if supplied_abs != expected_abs:
        raise SafetyViolation(
            "Agent Task Result must use the exact active Run output path",
            {"expected": expected, "supplied": str(result_path)},
        )
    return expected


@guarded_mutation
def complete_current(root: Path, result_path: Path) -> dict[str, Any]:
    ensure_native_path(root, tree=True)
    root = native_resolve(root.expanduser())
    state_path, state_doc = _state(root)
    state = state_doc["state"]
    active = state.get("active_run")
    if not isinstance(active, dict):
        raise ValidationFailure("No active run to complete")
    expected_result_path = _exact_result_relative(root, result_path, active)

    control_plane = check_control_plane(root, active, allow_missing_agent_result=False)
    if control_plane.get("status") != "PASS":
        return _safety_block(root, state_path, state_doc, active, control_plane)
    raw_result, result_digest, result_metadata = secure_read_agent_result(root, expected_result_path)
    result = _validate_agent_result(raw_result, active)
    result_metadata["sha256"] = result_digest

    stage_scope_violations = result.get("stage_scope_violations") or []
    if stage_scope_violations:
        assert_agent_result_unchanged(root, result_metadata)
        return block_current(
            root,
            "STAGE_SCOPE_VIOLATION: " + "; ".join(str(item) for item in stage_scope_violations),
            options=[
                "Remove future-stage-only work and retry the current Task",
                "Record the idea in the Next Stage Gap Backlog",
                "Revise the current Stage Plan through an explicit approval",
            ],
        )

    if result["status"] == "BLOCKED":
        assert_agent_result_unchanged(root, result_metadata)
        reason = (result.get("blockers") or ["Agent reported a blocker"])[0]
        return block_current(root, str(reason), options=["Resolve blocker and resume", "Change scope", "Defer task", "Cancel route"])
    if result["status"] == "FAILED":
        assert_agent_result_unchanged(root, result_metadata)
        return block_current(root, result.get("summary") or "Agent execution failed", options=["Fix and retry", "Change scope", "Use a different implementation route"])

    report_path = active.get("verification_report_path")
    if not report_path:
        raise ValidationFailure("Independent verification has not been run")
    report = load_data(root / report_path)["validation_report"]
    if automatic_run_phase(root, active) is not None:
        evidence_ref = active.get("automatic_apply_evidence_ref")
        proof_path = root / ".harness/evidence" / (str(evidence_ref) + ".yaml")
        if (report.get("verification_backend") != "SANDBOXED" or
                not isinstance(evidence_ref, str) or not _native_io_path(proof_path).is_file() or
                _native_io_path(proof_path).is_symlink() or
                load_data(proof_path).get("apply_evidence", {}).get("run_ref") != active["run_ref"] + "@1"):
            raise ValidationFailure("Automatic completion requires exact signed SANDBOXED verification and Apply Evidence")
    if report.get("status") != "PASS":
        raise ValidationFailure("Task cannot complete without PASS verification", report)
    from .task_manual_evidence import evaluate_manual_evidence
    manual_evidence = evaluate_manual_evidence(root, active)
    if manual_evidence['status'] != 'PASS' or (manual_evidence['evidence_ref'] and report.get('manual_evidence') != manual_evidence):
        raise ValidationFailure('Task manual evidence is missing/stale; run verify again')
    snapshot_doc = _snapshot(root, active)
    before = snapshot_doc.get("product_files") or snapshot_doc.get("files") or {}
    verified_product_files = _assert_verified_product_unchanged(root, active)
    current_diff = diff_snapshots(before, verified_product_files)
    verified_diff = _actual_change_set(report["diff"])
    if _actual_change_set(current_diff) != verified_diff:
        raise ValidationFailure("Project files changed after verification; run verify again", {"verified": verified_diff, "current": current_diff})
    declared = _actual_change_set(result["changes"])
    if declared != verified_diff:
        raise ValidationFailure("Agent-declared changes do not match independently observed changes", {"declared": declared, "observed": verified_diff})

    # Close the two TOCTOU windows immediately before kernel-owned completion writes.
    control_plane = check_control_plane(root, active, allow_missing_agent_result=False)
    if control_plane.get("status") != "PASS":
        return _safety_block(root, state_path, state_doc, active, control_plane)
    assert_agent_result_unchanged(root, result_metadata)
    _assert_verified_product_unchanged(root, active)

    task_id = str(active["task_ref"]).split("@")[0]
    task, _ = _task(root, task_id)
    completed_at = utc_now()
    preparation_evidence_bindings = materialize_preparation_task_evidence(
        root,
        task=task,
        active_run=active,
        verification_report=report,
    )
    completion_evidence_refs = [active["verification_evidence_ref"]] + ([manual_evidence['evidence_ref']] if manual_evidence['evidence_ref'] else []) + [
        item["ref"] for item in preparation_evidence_bindings
    ]
    run = {
        "id": active["run_ref"],
        "execution_origin": "LOCAL_AUTOMATIC" if automatic_run_phase(root, active) else "MANUAL_EXTERNAL",
        "task_ref": active["task_ref"],
        "implementation_stage": task["implementation_stage"],
        **_maintenance_binding(task),
        "attempt_no": active["attempt_no"],
        "run_plan_ref": active["run_plan_ref"],
        "status": "SUCCEEDED",
        "agent_result_path": expected_result_path,
        "agent_result_sha256": result_digest,
        "evidence_refs": completion_evidence_refs,
        "verification_report_ref": active["verification_report_ref"],
        "actual_changes": verified_diff,
        "compensation_status": "NOT_REQUIRED",
        "completed_at": completed_at,
    }
    run_path = f".harness/runtime/RUNS/{run['id']}.yaml"
    write_data(root / run_path, {"run": run})
    task_report_id = f"TRP-{run['id'].removeprefix('RUN-')}"
    task_report = {
        "id": task_report_id,
        "task_ref": active["task_ref"],
        "implementation_stage": task["implementation_stage"],
        **_maintenance_binding(task),
        "run_ref": run["id"],
        "status": "COMPLETED",
        "summary": result["summary"],
        "changes": verified_diff,
        "verification_report_ref": active["verification_report_ref"],
        "evidence_refs": completion_evidence_refs,
        "stage_acceptance_evidence_bindings": preparation_evidence_bindings,
        "documentation_impact": task.get("documentation"),
        "completed_at": completed_at,
    }
    task_report_path = f".harness/reports/{task_report_id}.yaml"
    write_data(root / task_report_path, {"task_report": task_report})
    completed_task = _write_task_revision(root, task_id, status="DONE", completion_report_ref=task_report_id, completed_at=completed_at)
    completed_ref = f"{completed_task['id']}@{completed_task['revision']}"
    if completed_ref not in state.setdefault("completed_task_refs", []):
        state["completed_task_refs"].append(completed_ref)
    if task_report_id not in state.setdefault("task_report_refs", []):
        state["task_report_refs"].append(task_report_id)
    state["active_run"] = None
    maintenance = maintenance_for_task(root, task)
    next_id = _next_runnable(state, root)
    maintenance_transition = None
    if maintenance is not None:
        if next_id:
            _update_wp_status(root, task["work_package_ref"])
            next_task_value, _ = _task(root, next_id)
            if next_task_value.get("status") == "PLANNED":
                _write_task_revision(root, next_id, status="READY", ready_at=completed_at)
            state["current_task_ref"] = next_id
            state["next_route"] = "COMPILE_NEXT_READY_TASK"
            state["project_status"] = "ACTIVE"
            state["handoff_status"] = "MAINTENANCE_ACTIVE"
            state["updated_at"] = completed_at
            write_data(state_path, state_doc)
        else:
            state["current_task_ref"] = None
            state["updated_at"] = completed_at
            maintenance_transition = finalize_maintenance(root, state_doc=state_doc)
            state_doc = load_data(state_path)
            state = state_doc["state"]
        stage_transition = None
    else:
        _update_wp_status(root, task["work_package_ref"])
        if next_id:
            next_task_value, _ = _task(root, next_id)
            if next_task_value.get("status") == "PLANNED":
                _write_task_revision(root, next_id, status="READY", ready_at=completed_at)
            state["current_task_ref"] = next_id
            state["next_route"] = "COMPILE_NEXT_READY_TASK"
            state["project_status"] = "ACTIVE"
            state["updated_at"] = completed_at
            write_data(state_path, state_doc)
            stage_transition = None
        else:
            # Persist the completed Task/WP facts before deterministic Gate-readiness
            # evaluation.  The readiness service then owns the atomic Stage/route
            # mutation and may create one bounded preparation Work Package.
            state["current_task_ref"] = None
            state["next_route"] = "EVALUATE_STAGE_GATE_READINESS"
            state["project_status"] = "ACTIVE"
            state["handoff_status"] = "GATE_READINESS_EVALUATION"
            state["updated_at"] = completed_at
            write_data(state_path, state_doc)
            stage_transition = evaluate_stage_gate_readiness(root, reserve_first=False)
            state_doc = load_data(state_path)
            state = state_doc["state"]
    append_jsonl(root / ".harness/events/EVENTS.jsonl", {"type": "TASK_COMPLETED", "task_ref": completed_ref, "run_ref": run["id"], "at": completed_at})
    render_roadmap(root)
    render_status(root)
    boundary = record_phase_boundary(
        root,
        active,
        phase="COMPLETED",
        kernel_written_paths=[
            run_path,
            task_report_path,
            f".harness/tasks/{completed_task['id']}@{completed_task['revision']}.yaml",
            ".harness/tasks/INDEX.yaml",
            ".harness/work-packages/INDEX.yaml",
            ".harness/state/CURRENT_STATE.yaml",
            ".harness/state/NEXT_TASK.yaml",
            ".harness/events/EVENTS.jsonl",
            "ROADMAP.md",
            "STATUS.md",
        ]
        + [item["path"] for item in preparation_evidence_bindings]
        + (stage_transition.get("kernel_written_paths", []) if stage_transition else [])
        + (maintenance_transition.get("kernel_written_paths", []) if maintenance_transition else []),
        recorded_at=completed_at,
    )
    if (
        not next_id
        and stage_transition
        and stage_transition.get("status") == "STAGE_ACCEPTANCE_PREPARATION"
        and not isinstance(stage_transition.get("next"), dict)
    ):
        preparation_task_id = str(stage_transition["task_ref"]).split("@", 1)[0]
        stage_transition["next"] = reserve_run(root, preparation_task_id)
        state_doc = load_data(state_path)
        state = state_doc["state"]
    response: dict[str, Any] = {
        "status": "COMPLETED",
        "task_ref": completed_ref,
        "run_ref": run["id"],
        "run_status": "SUCCEEDED",
        "task_status": "DONE",
        "task_report_ref": task_report_id,
        "project_status": state["project_status"],
        "implementation_stage": task["implementation_stage"],
        "next_route": state["next_route"],
        "phase_boundary_digest": boundary["boundary_digest"],
    }
    if next_id:
        next_bundle = reserve_run(root, next_id)
        response["next"] = next_bundle
    elif stage_transition:
        response["stage_gate"] = stage_transition
        if isinstance(stage_transition.get("next"), dict):
            response["next"] = stage_transition["next"]
    elif maintenance_transition:
        response["maintenance"] = maintenance_transition
    return response


@guarded_mutation
def block_current(root: Path, reason: str, *, options: list[str] | None = None,
                  run_status: str = "BLOCKED", reason_code: str | None = None,
                  execution_origin: str | None = None) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    state_path, state_doc = _state(root)
    state = state_doc["state"]
    active = state.get("active_run")
    if not isinstance(active, dict):
        raise ValidationFailure("No active run to block")
    if run_status not in {"BLOCKED", "FAILED_RETRYABLE", "TIMED_OUT"}:
        raise ValidationFailure("Unsupported terminal Run failure status", run_status)
    if execution_origin is not None and execution_origin not in {"MANUAL_EXTERNAL", "LOCAL_AUTOMATIC"}:
        raise ValidationFailure("Invalid execution origin", execution_origin)
    task_id = str(active["task_ref"]).split("@")[0]
    task, _ = _task(root, task_id)
    blocker_id = _next_blocker_id(root, task_id)
    recovery = options or ["Resolve missing input and resume", "Change task scope", "Defer task", "Cancel route"]
    recorded_at = utc_now()
    blocker = {
        "id": blocker_id,
        "revision": 1,
        "kind": "EXECUTION_BLOCKER",
        "task_ref": active["task_ref"],
        "run_ref": active["run_ref"],
        "implementation_stage": task.get("implementation_stage"),
        **_maintenance_binding(task),
        "reason": reason,
        **({"reason_code": reason_code} if reason_code else {}),
        "recovery_options": recovery,
        "resume_condition": "A resolution note is supplied and the affected task contract remains valid or is revised through an approved decision.",
        "status": "OPEN",
        "created_at": recorded_at,
    }
    write_data(root / f".harness/blockers/{blocker_id}@1.yaml", {"blocker": blocker})
    run = {
        "id": active["run_ref"],
        "execution_origin": execution_origin or ("LOCAL_AUTOMATIC" if automatic_run_phase(root, active) else "MANUAL_EXTERNAL"),
        "task_ref": active["task_ref"],
        "implementation_stage": task.get("implementation_stage"),
        **_maintenance_binding(task),
        "attempt_no": active["attempt_no"],
        "run_plan_ref": active["run_plan_ref"],
        "status": run_status,
        **({"reason_code": reason_code} if reason_code else {}),
        "blocker_ref": blocker_id,
        "evidence_refs": [active.get("verification_evidence_ref")] if active.get("verification_evidence_ref") else [],
        "compensation_status": "NOT_REQUIRED",
        "completed_at": recorded_at,
    }
    run_path = f".harness/runtime/RUNS/{run['id']}.yaml"
    write_data(root / run_path, {"run": run})
    blocked_task = _write_task_revision(root, task_id, status="BLOCKED", blocker_ref=blocker_id, blocked_at=recorded_at)
    blocked_ref = f"{blocked_task['id']}@{blocked_task['revision']}"
    state["active_run"] = None
    state.setdefault("blocked_task_refs", []).append(blocked_ref)
    state.setdefault("open_blocker_refs", []).append(blocker_id)
    state["current_task_ref"] = task_id
    state["project_status"] = "BLOCKED"
    state["next_route"] = "RESOLVE_BLOCKER_OR_CHANGE_SCOPE"
    state["updated_at"] = recorded_at
    write_data(state_path, state_doc)
    _update_wp_status(root, task["work_package_ref"])
    write_data(
        root / ".harness/state/NEXT_TASK.yaml",
        {
            "next_task": {
                "status": "BLOCKED",
                "task_ref": blocked_ref,
                "implementation_stage": task.get("implementation_stage"),
                **_maintenance_binding(task),
                "blocker_ref": blocker_id,
                "recovery_options": recovery,
            }
        },
    )
    append_jsonl(root / ".harness/events/EVENTS.jsonl", {"type": "TASK_BLOCKED", "task_ref": active["task_ref"], "run_ref": run["id"], "blocker_ref": blocker_id, "at": recorded_at})
    render_roadmap(root)
    render_status(root)
    record_phase_boundary(
        root,
        active,
        phase="BLOCKED",
        kernel_written_paths=[
            f".harness/blockers/{blocker_id}@1.yaml",
            run_path,
            f".harness/tasks/{blocked_task['id']}@{blocked_task['revision']}.yaml",
            ".harness/tasks/INDEX.yaml",
            ".harness/work-packages/INDEX.yaml",
            ".harness/state/CURRENT_STATE.yaml",
            ".harness/state/NEXT_TASK.yaml",
            ".harness/events/EVENTS.jsonl",
            "ROADMAP.md",
            "STATUS.md",
        ],
        recorded_at=recorded_at,
    )
    return {
        "status": "BLOCKED",
        "task_ref": blocked_ref,
        "run_ref": run["id"],
        "implementation_stage": task.get("implementation_stage"),
        **_maintenance_binding(task),
        "blocker_ref": blocker_id,
        **({"reason_code": reason_code, "run_status": run_status} if reason_code else {}),
        "recovery_options": recovery,
    }


@guarded_mutation
def resume_blocked(root: Path, *, resolution: str, blocker_ref: str | None = None) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    ensure_current_project_contract(root)
    state_path, state_doc = _state(root)
    state = state_doc["state"]
    if state.get("next_route") == "RESOLVE_STAGE_GATE":
        raise ValidationFailure(
            "Stage Gate blockers use the dedicated resume-stage-gate recovery route",
            {"next_route": "RESOLVE_STAGE_GATE"},
        )
    blocker_refs = state.get("open_blocker_refs") or []
    blocker_ref = blocker_ref or (blocker_refs[-1] if blocker_refs else None)
    if not blocker_ref:
        raise ValidationFailure("No open blocker to resume")
    blocker_path = root / f".harness/blockers/{blocker_ref}@1.yaml"
    if not _native_io_path(blocker_path).exists():
        raise ValidationFailure("Blocker record is missing", blocker_ref)
    blocker = load_data(blocker_path)["blocker"]
    if blocker.get("status") != "OPEN":
        raise ValidationFailure("Blocker is not OPEN", blocker_ref)
    if blocker.get("kind") == "SAFETY_VIOLATION" or state.get("next_route") == SAFETY_RECOVERY_ROUTE:
        raise SafetyViolation(
            "A control-plane safety blocker cannot be resumed in place",
            {"blocker_ref": blocker_ref, "next_route": SAFETY_RECOVERY_ROUTE},
        )
    task_id = str(blocker["task_ref"]).split("@")[0]
    blocker["revision"] = 2
    blocker["previous_revision_ref"] = f"{blocker_ref}@1"
    blocker["status"] = "RESOLVED"
    blocker["resolution"] = resolution
    blocker["resolved_at"] = utc_now()
    write_data(root / f".harness/blockers/{blocker_ref}@2.yaml", {"blocker": blocker})
    ready_task = _write_task_revision(root, task_id, status="READY", blocker_ref=None, resumed_at=utc_now())
    state["blocked_task_refs"] = [ref for ref in state.get("blocked_task_refs") or [] if str(ref).split("@")[0] != task_id]
    state["open_blocker_refs"] = [ref for ref in blocker_refs if ref != blocker_ref]
    state["current_task_ref"] = task_id
    state["project_status"] = "ACTIVE"
    state["next_route"] = "COMPILE_RESUMED_TASK"
    state["updated_at"] = utc_now()
    write_data(state_path, state_doc)
    append_jsonl(root / ".harness/events/EVENTS.jsonl", {"type": "BLOCKER_RESOLVED", "blocker_ref": blocker_ref, "task_ref": f"{ready_task['id']}@{ready_task['revision']}", "at": utc_now()})
    render_roadmap(root)
    render_status(root)
    bundle = reserve_run(root, task_id)
    return {"status": "RESUMED", "blocker_ref": f"{blocker_ref}@2", "task_ref": f"{ready_task['id']}@{ready_task['revision']}", "next": bundle}


# PH-051-09: governed automatic route. This composes the separately tested
# executor, sandbox verifier and apply service; it cannot dispatch a host agent.
_AUTOMATIC_PHASES = frozenset({
    "AUTO_RUNNING", "AGENT_RESULT_NORMALIZED_UNVERIFIED", "AUTO_VERIFYING",
    "AUTO_RECOVERY_QUARANTINED",
    "PRODUCT_APPLY_VERIFIED", "AUTO_VERIFIED",
})
_AUTOMATIC_REASON_CODES = frozenset({
    "EXECUTOR_UNAVAILABLE", "EXECUTOR_EXIT_NONZERO", "EXECUTOR_TIMEOUT",
    "SANDBOX_UNAVAILABLE", "SANDBOX_POLICY_FAILURE", "RESULT_MISSING",
    "RESULT_INVALID", "OUTPUT_LIMIT_EXCEEDED", "NETWORK_NOT_APPROVED",
    "SECRET_REFERENCE_MISSING", "SECRET_LEAK_DETECTED", "SCOPE_VIOLATION",
    "BASELINE_CHANGED", "VERIFICATION_FAILED", "APPLY_FAILED_RECOVERABLE",
})
_AUTOMATIC_BLOCKING = frozenset({
    "EXECUTOR_UNAVAILABLE", "SANDBOX_UNAVAILABLE", "SANDBOX_POLICY_FAILURE",
    "NETWORK_NOT_APPROVED", "SECRET_REFERENCE_MISSING", "SECRET_LEAK_DETECTED",
    "SCOPE_VIOLATION", "BASELINE_CHANGED", "APPLY_FAILED_RECOVERABLE",
})


def automatic_run_phase(root: Path, active: dict[str, Any] | None) -> dict[str, Any] | None:
    """Read a signed Run phase, including the uncompleted recovery boundary.

    Never adopt a partial result from an interrupted local process. Recovery
    is an explicit governed step within the project-scoped execute lock.
    """
    if (not isinstance(active, dict) or
            not all(isinstance(active.get(k), str) and active[k] for k in
                    ("run_ref", "snapshot_path", "operation_journal_path"))):
        # Older/manual state projections (and diagnostics of incomplete data)
        # do not have a signed automatic Run context. Preserve their public
        # continuation; normal project validation still detects invalid state.
        return None
    boundary = load_phase_boundary(root, active)  # validates the whole digest chain
    phase = boundary.get("phase")
    journal_path = root / str(active["operation_journal_path"])
    if not _native_io_path(journal_path).exists():
        return None
    raw = load_data(journal_path).get("operation_journal") or {}
    phases = [entry.get("phase") for entry in raw.get("boundaries") or []]
    if "AUTO_RUNNING" not in phases:
        return None
    if phase in {"AUTO_RUNNING"}:
        status = "RUNNING"
    elif phase in {"AGENT_RESULT_NORMALIZED_UNVERIFIED", "AUTO_VERIFYING", "PRODUCT_APPLY_VERIFIED"}:
        status = "VERIFYING"
    elif phase == "AUTO_VERIFIED":
        status = "SUCCEEDED"
    else:
        status = "VERIFYING"  # Fail closed for an unknown interrupted automatic phase.
    return {"run_ref": active["run_ref"], "status": status, "phase": phase,
            "replay_allowed": False}


def _automatic_response(reason: str, *, status: str = "BLOCKED", **extra: Any) -> dict[str, Any]:
    if reason not in _AUTOMATIC_REASON_CODES:
        reason = "SANDBOX_POLICY_FAILURE"
    return {"status": status, "reason_code": reason, **extra}


def _approved_execution_options(root: Path, policy: dict[str, Any], *,
                                adapter_profile: str | None, network: str | None,
                                approval: Path | None, keep_execution_root: bool) -> dict[str, Any] | None:
    """Bounded precedence: explicit command options can *only narrow* policy.

    The PH-051-03 Podman backend intentionally supports only NONE. Do not
    pretend an egress approval grants an unimplemented network boundary.
    """
    if keep_execution_root:
        return _automatic_response("SANDBOX_POLICY_FAILURE", message="No governed debug-retention policy is activated")
    desired = network or "NONE"
    if desired not in {"NONE", "EXPLICIT_APPROVED_EGRESS"}:
        return _automatic_response("NETWORK_NOT_APPROVED")
    if desired == "EXPLICIT_APPROVED_EGRESS":
        return _automatic_response("NETWORK_NOT_APPROVED", message=(
            "Explicit egress is not enforceable by the current pinned Podman runner; "
            "no host or unrestricted-network fallback is permitted"))
    if approval is not None:
        return _automatic_response("NETWORK_NOT_APPROVED", message="Per-Run approval cannot broaden a NONE-only execution")
    expected = policy.get("adapter_profile_ref")
    if adapter_profile is not None:
        # Neither a different active adapter nor an arbitrary path is an
        # allowed command-line override to an immutable project lock.
        exact_path = root / f".harness/config/ADAPTERS/{expected}.yaml"
        if (adapter_profile not in {expected, str(exact_path),
                                   f".harness/config/ADAPTERS/{expected}.yaml"}):
            return _automatic_response("SANDBOX_POLICY_FAILURE", message="Adapter override must match the exact pinned ADP")
    return None


def _automatic_supported_on_host() -> bool:
    """Native Windows is manual-only; Linux Podman doctor still gates activation."""
    return os.name == "posix" and hasattr(os, "geteuid")


def executor_doctor(root: Path, *, adapter_profile: str | None = None,
                    network: str | None = None, approval: Path | None = None,
                    keep_execution_root: bool = False) -> dict[str, Any]:
    """Public read-only project-scoped Podman doctor (not distribution doctor).

    UNKNOWN self-tests, missing profiles/secrets and manual opt-out all block.
    No current Task/Run or project state is changed by this API.
    """
    if not _automatic_supported_on_host():
        return _automatic_response("SANDBOX_UNAVAILABLE",
            execution_mode="UNSUPPORTED_ON_NATIVE_WINDOWS", isolation_verified=False,
            message="Rootless Podman automatic executor is Linux-only; Windows manual mode cannot run a host agent")
    root = native_resolve(Path(root).expanduser())
    try:
        lock = load_data(root / ".harness/config/PROJECT_LOCK.yaml")["project_lock"]
        policy = lock.get("execution") or {}
        if policy.get("mode") != "LOCAL_AUTOMATIC":
            return _automatic_response("EXECUTOR_UNAVAILABLE", execution_mode="MANUAL_HANDOFF",
                                       message="Automatic execution requires explicit project opt-in")
        options_failure = _approved_execution_options(root, policy, adapter_profile=adapter_profile,
                                                      network=network, approval=approval,
                                                      keep_execution_root=keep_execution_root)
        if options_failure:
            return {**options_failure, "execution_mode": "LOCAL_AUTOMATIC"}
        # Exact profile refs, digests and statuses are checked again by adapter.
        adapter = CodexCliLocalAdapter.from_project(root)
        response = adapter.doctor(adapter._bound["adapter_profile"])
        if response.get("status") != "PASS":
            reason = response.get("reason_code") or "SANDBOX_UNAVAILABLE"
            return {**_automatic_response(reason, message=response.get("message", "Podman self-test failed")),
                    "execution_mode": "LOCAL_AUTOMATIC", "doctor": response}
        return {"status": "PASS", "execution_mode": "LOCAL_AUTOMATIC",
                "adapter_profile_ref": adapter._bound["profile_bindings"]["adapter"]["ref"],
                "sandbox_profile_ref": adapter._bound["profile_bindings"]["sandbox"]["ref"],
                "network_mode": "NONE", "isolation_verified": True, "doctor": response}
    except (HarnessError, OSError, ValueError, TypeError, KeyError) as exc:
        # Contract errors are not a reason to execute an alternative provider.
        return _automatic_response("SANDBOX_POLICY_FAILURE", message=type(exc).__name__,
                                   execution_mode="LOCAL_AUTOMATIC")


def _execution_runtime_root() -> Path:
    # A stable per-UID host root outside canonical product and agent mounts.
    # This is not a user-controlled arbitrary mount-source override.
    return native_resolve(Path(tempfile.gettempdir())) / f"project-harness-v051-runtime-{os.geteuid()}"


@contextmanager
def _automatic_project_lock(root: Path, runtime_root: Path):
    """Host-only nonblocking per-project lock; not a .harness file/mount.

    Cross-process serialization covers Run reservation + dispatch + apply and
    prevents two execute-current invocations both claiming a READY task.
    """
    import fcntl  # Linux/rootless Podman target platform; fail-closed elsewhere.
    base = Path(runtime_root).absolute()
    if _native_io_path(base).is_symlink() or base == root or base in root.parents or root in base.parents:
        raise SafetyViolation("Unsafe automatic runtime lock location")
    _native_io_path(base).mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = base.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
        raise SafetyViolation("Automatic runtime lock root is not private")
    name = hashlib.sha256(str(root).encode("utf-8")).hexdigest() + ".lock"
    path = base / name
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags, 0o600)
    try:
        details = os.fstat(fd)
        if (not stat.S_ISREG(details.st_mode) or details.st_nlink != 1 or
                details.st_uid != os.geteuid() or details.st_mode & 0o077):
            raise SafetyViolation("Unsafe automatic project lock")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def _automatic_boundary(root: Path, active: dict[str, Any], phase: str) -> None:
    if check_control_plane(root, active)["status"] != "PASS":
        raise SafetyViolation("Control-plane integrity failed at automatic Run boundary")
    record_phase_boundary(root, active, phase=phase, kernel_written_paths=[], recorded_at=utc_now())



def _record_execution_cleanup(root: Path, active: dict[str, Any], outcome: dict[str, Any],
                              *, phase: str) -> dict[str, Any]:
    """Independent cleanup diagnostics; never changes verification truth.

    A receipt is bounded, contains no raw roots/logs/secrets and is sealed as
    a legitimate kernel-only change to the current Run control plane.
    """
    rel = f".harness/runtime/CLEANUP_REPORTS/{active['run_ref']}.yaml"
    path = root / rel
    if _native_io_path(path).is_symlink():
        raise SafetyViolation("Unsafe exact cleanup report path")
    if _native_io_path(path).exists():
        previous = load_data(path).get("execution_cleanup")
        if not isinstance(previous, dict) or previous.get("run_ref") != active["run_ref"]:
            raise SafetyViolation("Conflicting immutable cleanup status")
        return previous
    item = {
        "run_ref": active["run_ref"], "status": outcome.get("status", "CLEANUP_FAILED"),
        "quarantined": bool(outcome.get("quarantined", False)),
        "orphan_count": outcome.get("orphan_count", 0),
        "recorded_at": utc_now(),
    }
    write_data(path, {"execution_cleanup": item})
    record_phase_boundary(root, active, phase=phase,
                          kernel_written_paths=[rel], recorded_at=utc_now())
    return item


def _cleanup_automatic_attempt(root: Path, runtime_root: Path, active: dict[str, Any], *,
                               quarantine: bool, phase: str) -> dict[str, Any]:
    outcome = finalize_execution_root(root, runtime_root, run_ref=active["run_ref"],
                                      quarantine=quarantine)
    try:
        return _record_execution_cleanup(root, active, outcome, phase=phase)
    except (SafetyViolation, ValidationFailure, OSError) as exc:
        # Fail to report cleanup separately, but never falsify independent
        # verification / applied product bytes as a rollback.
        return {"status": "CLEANUP_FAILED", "diagnostic": type(exc).__name__}


def _recover_interrupted_automatic(root: Path, runtime_root: Path,
                                   active: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    """Never re-dispatch an orphan. Reap labeled containers, recover journal,
    quarantine old bytes, then persist one BLOCKED old Run for explicit retry.

    Called only under the nonblocking per-project host lock, so no legitimate
    active execute-current process can be mistaken for an orphan.
    """
    from .execution_roots import _runtime_run_root
    scanner = RootlessPodmanRunner().project_orphan_containers(root)
    if scanner.get("status") != "PASS":
        return _automatic_response(scanner.get("reason_code", "SANDBOX_UNAVAILABLE"),
                                   run_ref=active["run_ref"], phase=observed.get("phase"),
                                   run_status=observed.get("status"),
                                   message="Orphan container inspection is required before retry")
    _, run_root = _runtime_run_root(root, runtime_root, active["run_ref"])
    recovered = {"status": "NO_JOURNAL"}
    committed_evidence = (root / ".harness/evidence" /
                          ("EVD-APPLY-" + active["run_ref"].removeprefix("RUN-") + ".yaml"))
    # If journal staging or an old post-commit cleanup is incomplete, the
    # recovery primitive decides all-old / all-new before any new attempt.
    if _native_io_path(run_root).is_dir() and ((_native_io_path(run_root / ".apply-journal")).exists() or
                              (_native_io_path(run_root / ".apply-journal")).is_symlink()):
        try:
            recovered = recover_apply(root, run_root)
        except (SafetyViolation, ValidationFailure, ApplyFailure, OSError):
            return _automatic_response("APPLY_FAILED_RECOVERABLE", run_ref=active["run_ref"],
                                       message="Apply journal cannot be reconciled; original Run quarantined in place")
    if _native_io_path(run_root).is_dir() and ((_native_io_path(run_root / ".apply-cleanup")).exists() or
                              (_native_io_path(run_root / ".apply-cleanup")).is_symlink()):
        # A retired apply journal is never an authorization to reapply. A
        # lingering cleanup directory can be quarantined with the old Run.
        pass
    committed = recovered.get("status") == "APPLIED" or _native_io_path(committed_evidence).exists()
    if _native_io_path(committed_evidence).is_symlink():
        return _automatic_response("APPLY_FAILED_RECOVERABLE", message="Untrusted Apply Evidence")
    # Avoid old root reuse even if agent-result.json is syntactically valid.
    clean = _cleanup_automatic_attempt(root, runtime_root, active, quarantine=True,
                                       phase="AUTO_RECOVERY_QUARANTINED")
    if clean["status"] == "CLEANUP_FAILED":
        return _automatic_response("SANDBOX_POLICY_FAILURE", run_ref=active["run_ref"],
                                   message="Orphan bytes cannot be safely quarantined")
    reason = "APPLY_FAILED_RECOVERABLE" if committed else "EXECUTOR_UNAVAILABLE"
    blocked = block_current(root, "Interrupted local automatic Run; " + (
        "product commit is already present and requires governed inspection" if committed else
        "no untrusted partial output will be adopted"),
        options=["Inspect orphan cleanup and recovered apply result",
                 "Explicitly resume the Task as a new Run attempt after correction"],
        run_status="BLOCKED", reason_code=reason, execution_origin="LOCAL_AUTOMATIC")
    return {**blocked, "status": "BLOCKED", "reason_code": reason,
            "recovery": recovered["status"], "cleanup": clean["status"],
            "orphan_count": scanner.get("orphan_count", 0), "run_ref": active["run_ref"],
            "next_command": "project-harness resume --project <root> --resolution <reviewed-resolution>"}

def _recover_verified_cleanup(root: Path, runtime_root: Path,
                              active: dict[str, Any]) -> dict[str, Any]:
    """Complete an interrupted post-commit retirement without redispatch.

    AUTO_VERIFIED is already signed; its independent verification and Apply
    Evidence stay authoritative. The *missing* cleanup receipt is recovered
    only after checking all labeled Podman children have terminated. Any
    surviving apply journal is reconciled before its disposable tree moves.
    """
    inspected = RootlessPodmanRunner().project_orphan_containers(root)
    if inspected.get("status") != "PASS":
        return _automatic_response(inspected.get("reason_code", "SANDBOX_UNAVAILABLE"),
                                   run_ref=active["run_ref"], run_status="SUCCEEDED",
                                   message="Verified Run cleanup needs trusted Podman inspection")
    from .execution_roots import _runtime_run_root
    _, run_root = _runtime_run_root(root, runtime_root, active["run_ref"])
    if _native_io_path(run_root).is_dir() and ((_native_io_path(run_root / ".apply-journal")).exists() or
                              (_native_io_path(run_root / ".apply-journal")).is_symlink()):
        try:
            recover_apply(root, run_root)
        except (SafetyViolation, ValidationFailure, ApplyFailure, OSError):
            return _automatic_response("APPLY_FAILED_RECOVERABLE", run_ref=active["run_ref"],
                                       run_status="SUCCEEDED",
                                       message="Committed Apply journal cannot be reconciled")
    cleanup = _cleanup_automatic_attempt(root, runtime_root, active,
                                         quarantine=False, phase="AUTO_VERIFIED")
    return {"status": "PASS" if cleanup["status"] != "CLEANUP_FAILED" else "BLOCKED",
            "cleanup": cleanup["status"], "run_ref": active["run_ref"]}


def _automatic_failed(root: Path, reason: str, *, stage: str,
                      runtime_root: Path | None = None) -> dict[str, Any]:
    if reason not in _AUTOMATIC_REASON_CODES:
        reason = "SANDBOX_POLICY_FAILURE"
    active = _state(root)[1]["state"].get("active_run")
    if not isinstance(active, dict):
        return _automatic_response(reason, stage=stage)
    if check_control_plane(root, active)["status"] != "PASS":
        state_path, state_doc = _state(root)
        return _safety_block(root, state_path, state_doc, active,
                             check_control_plane(root, active))
    cleanup = None
    if runtime_root is not None:
        cleanup = _cleanup_automatic_attempt(root, runtime_root, active, quarantine=True,
                                             phase="AUTO_RECOVERY_QUARANTINED")
    run_status = ("TIMED_OUT" if reason == "EXECUTOR_TIMEOUT" else
                  "BLOCKED" if reason in _AUTOMATIC_BLOCKING else "FAILED_RETRYABLE")
    blocked = block_current(root, f"LOCAL_AUTOMATIC {stage}: {reason}",
                            options=["Inspect exact failure reason and resolve prerequisite",
                                     "Resume with a new Run attempt after correction",
                                     "Choose an explicitly governed manual route (never automatic fallback)"],
                            run_status=run_status, reason_code=reason,
                            execution_origin="LOCAL_AUTOMATIC")
    return {**blocked, **({"cleanup": cleanup["status"]} if cleanup else {}), "status": run_status, "project_status": "BLOCKED", "run_status": run_status,
            "reason_code": reason, "next_command": "project-harness resume --project <root> --resolution <documented-resolution>"}


def _record_sandboxed_verification(root: Path, active: dict[str, Any], verification: dict[str, Any],
                                   apply_result: dict[str, Any]) -> dict[str, Any]:
    """Record actual independent Podman PASS *after* committed safe apply.

    No host verification, generic Gate-proof promotion or human Stage approval.
    The existing complete_current requires this exact report and product digest.
    """
    if verification.get("status") != "PASS" or apply_result.get("status") != "APPLIED":
        raise ValidationFailure("Automatic verification and apply must both pass")
    task = _trusted_task(root, active)
    report_id = "VAL-" + active["run_ref"].removeprefix("RUN-")
    evidence_id = "EVD-" + active["run_ref"].removeprefix("RUN-")
    report_rel = f".harness/reports/{report_id}.yaml"
    evidence_rel = f".harness/evidence/{evidence_id}.yaml"
    for rel in (report_rel, evidence_rel):
        if (_native_io_path(root / rel)).exists() or (_native_io_path(root / rel)).is_symlink():
            raise ValidationFailure("Automatic verification record already exists; immutable replay refused", rel)
    after = snapshot_product(root)
    if after != verification.get("verified_product_files"):
        raise ValidationFailure("Canonical post-apply product is not the verified disposable product")
    before = _snapshot(root, active).get("product_files") or {}
    if diff_snapshots(before, after) != verification.get("diff"):
        raise ValidationFailure("Post-apply write set does not match independent sandbox verdict")
    control = check_control_plane(root, active)
    if control["status"] != "PASS":
        raise SafetyViolation("Control-plane integrity changed after apply")
    now = utc_now()
    commands = [{**r, "status": "PASS"} for r in verification["command_results"]]
    gates = {"control_plane": "PASS", "scope": "PASS", "commands": "PASS",
             "expected_paths": "PASS", "manual_checks": "PASS"}
    report = {
        "id": report_id, "kind": "TASK_VERIFICATION", "verification_backend": "SANDBOXED",
        "task_ref": active["task_ref"], "run_ref": active["run_ref"],
        "implementation_stage": task.get("implementation_stage"), **_maintenance_binding(task),
        "evidence_ref": evidence_id, "apply_evidence_ref": apply_result["evidence_ref"],
        "status": "PASS", "gates": gates, "control_plane": control,
        "diff": verification["diff"], "scope_validation": verification["scope"],
        "command_results": commands, "missing_expected_paths": [], "created_at": now,
    }
    write_data(root / report_rel, {"validation_report": report})
    body = normalized_evidence_body(
        evidence_id=evidence_id, kind="TEST_REPORT", status="PASS",
        provenance={"source_type": "PROJECT_HARNESS_RUNTIME_VERIFICATION_REPORT",
                    "source_ref": report_id, "producer": "PROJECT_HARNESS_RUNTIME"},
        base_revision=_product_baseline_revision(root),
        criterion_refs=[], outcome_refs=[], profile_control_refs=["RUNTIME_TASK_VERIFICATION"],
        source_bindings=[{"ref": report_id, "path": report_rel,
                          "sha256": "sha256:" + sha256_file(root / report_rel)}],
        created_at=now, task_ref=active["task_ref"], run_ref=active["run_ref"],
        report_refs=[report_id],
        rationale="Exact current Run independently verified in separate rootless sandbox process before controlled apply.",
        validator="PROJECT_HARNESS_RUNTIME",
        details={"implementation_stage": task.get("implementation_stage"),
                 **_maintenance_binding(task), "gates": gates,
                 "control_plane": control, "scope_validation": verification["scope"],
                 "diff": verification["diff"], "commands": commands,
                 "expected_paths": {"declared": task.get("verification", {}).get("expected_paths", []), "missing": []},
                 "manual_checks": task.get("verification", {}).get("manual_checks", [])},
    )
    write_normalized_evidence(root, body)
    state_path, state_doc = _state(root)
    persisted_active = state_doc["state"]["active_run"]
    if persisted_active["run_ref"] != active["run_ref"]:
        raise ValidationFailure("Another Run became active before verification publication")
    persisted_active.update({
        "verification_report_ref": report_id, "verification_report_path": report_rel,
        "verification_evidence_ref": evidence_id, "verification_evidence_path": evidence_rel,
        "automatic_apply_evidence_ref": apply_result["evidence_ref"],
        "control_plane_phase": "VERIFIED", "verified_product_diff": _actual_change_set(verification["diff"]),
        "verified_product_files": after,
    })
    state_doc["state"]["next_route"] = "COMPLETE_TASK"
    state_doc["state"]["updated_at"] = now
    write_data(state_path, state_doc)
    append_jsonl(root / ".harness/events/EVENTS.jsonl", {
        "type": "AUTOMATIC_SANDBOX_VERIFIED_AND_APPLIED", "run_ref": active["run_ref"],
        "apply_evidence_ref": apply_result["evidence_ref"], "at": now})
    render_status(root)
    boundary = record_phase_boundary(root, persisted_active, phase="AUTO_VERIFIED",
                                    kernel_written_paths=[report_rel, evidence_rel,
                                                          ".harness/state/CURRENT_STATE.yaml",
                                                          ".harness/events/EVENTS.jsonl", "STATUS.md"],
                                    recorded_at=now)
    return {"status": "PASS", "report_ref": report_id,
            "evidence_ref": evidence_id, "apply_evidence_ref": apply_result["evidence_ref"],
            "phase_boundary_digest": boundary["boundary_digest"]}


def execute_current(root: Path, *, adapter_profile: str | None = None,
                    network: str | None = None, approval: Path | None = None,
                    keep_execution_root: bool = False, runtime_root: Path | None = None) -> dict[str, Any]:
    """Public governed local execution of *only* the current READY Task/JIT.

    Never uses subprocess to run an agent on host. Every positive path requires
    real RootlessPodmanRunner doctor, a separately executed sandbox verifier,
    a bounded validated diff and signed Apply Evidence. The optional Python
    runtime_root is only a separate local storage location, not a mount override.
    """
    if not _automatic_supported_on_host():
        return _automatic_response("SANDBOX_UNAVAILABLE",
            execution_mode="UNSUPPORTED_ON_NATIVE_WINDOWS", isolation_verified=False,
            message="No rootless Podman automatic execution or host fallback on native Windows")
    root = native_resolve(Path(root).expanduser())
    runtime_dir = Path(runtime_root).absolute() if runtime_root is not None else _execution_runtime_root()
    try:
        with _automatic_project_lock(root, runtime_dir):
            state_path, state_doc = _state(root)
            state = state_doc["state"]
            if state.get("project_status") == "BLOCKED":
                return _automatic_response("EXECUTOR_UNAVAILABLE", project_status="BLOCKED",
                                           next_route=state.get("next_route"),
                                           next_command="project-harness resume --project <root> --resolution <documented-resolution>")
            task_id = state.get("current_task_ref")
            if state.get("project_status") != "ACTIVE" or not isinstance(task_id, str):
                return _automatic_response("EXECUTOR_UNAVAILABLE", message="No executable READY Task in active Stage")
            task, _ = _task(root, task_id)
            if task.get("status") != "READY" or task.get("implementation_stage") != execution_stage(root):
                return _automatic_response("EXECUTOR_UNAVAILABLE", message="Task is not current-stage READY")
            active = state.get("active_run")
            if active is not None:
                if not isinstance(active, dict) or active.get("task_ref", "").split("@")[0] != task_id:
                    return _automatic_response("SANDBOX_POLICY_FAILURE")
                previous = automatic_run_phase(root, active)
                if previous is not None:
                    if previous["phase"] == "AUTO_VERIFIED":
                        receipt = root / ".harness/runtime/CLEANUP_REPORTS" / (active["run_ref"] + ".yaml")
                        if _native_io_path(receipt).is_symlink():
                            raise SafetyViolation("Forged automatic cleanup receipt")
                        if not _native_io_path(receipt).is_file():
                            retirement = _recover_verified_cleanup(root, runtime_dir, active)
                            if retirement["status"] != "PASS":
                                return {**retirement, "run_ref": active["run_ref"],
                                        "completion_status": "CLEANUP_RECOVERY_REQUIRED"}
                        recorded = load_data(receipt)["execution_cleanup"]
                        if recorded.get("run_ref") != active["run_ref"]:
                            raise SafetyViolation("Cleanup receipt belongs to another Run")
                        return {"status": "SUCCEEDED", "run_status": "SUCCEEDED", "run_ref": active["run_ref"],
                                "completion_status": "WAITING_EXPLICIT_COMPLETION", "idempotent": True,
                                "cleanup": recorded.get("status", "UNKNOWN"),
                                "next_command": "project-harness complete --project <root> --result <exact-active-run-result-path>"}
                    return _recover_interrupted_automatic(root, runtime_dir, active, previous)
                if state.get("next_route") != "EXECUTE_CURRENT_TASK_WITH_CODEX":
                    return _automatic_response("SANDBOX_POLICY_FAILURE", message="Current Run is not awaiting execution")
            elif state.get("next_route") not in {
                "COMPILE_FIRST_READY_TASK", "COMPILE_NEXT_READY_TASK", "COMPILE_RESUMED_TASK",
                "STAGE_ACCEPTANCE_PREPARATION", "MAINTAIN_CURRENT_STAGE",
            }:
                return _automatic_response("SANDBOX_POLICY_FAILURE", message="No READY JIT continuation")

            # Doctor and project policy checks occur *before* Run reservation.
            # No failing doctor may fall through to an external host process.
            health = executor_doctor(root, adapter_profile=adapter_profile, network=network,
                                     approval=approval, keep_execution_root=keep_execution_root)
            if health["status"] != "PASS":
                # Doctor/policy rejection is strictly pre-dispatch and read-only,
                # even when manual `next` has already reserved this Run. A
                # denied automatic opt-in must never corrupt the manual route.
                return {**health, "project_status": "ACTIVE", "task_ref": task_id,
                        "next_command": "project-harness executor-doctor --project <root>"}
            # Existing orphan directories from a prior Run must never be
            # reused as inputs for this new attempt. Inspect any live labeled
            # containers before quarantine; without Podman, fail closed.
            from .execution_roots import _runtime_run_root
            _, current_root = _runtime_run_root(root, runtime_dir,
                                                active["run_ref"] if active else "RUN-RECOVERY")
            executions = current_root.parent
            stale = [entry for entry in native_iterdir(executions)
                     if _native_io_path(entry).is_dir() and entry.name != (active or {}).get("run_ref") ] if _native_io_path(executions).exists() else []
            if stale:
                orphan_check = RootlessPodmanRunner().project_orphan_containers(root)
                if orphan_check.get("status") != "PASS":
                    return _automatic_response(orphan_check.get("reason_code", "SANDBOX_UNAVAILABLE"),
                                               message="Cannot clear orphan execution roots")
                quarantined = quarantine_orphan_execution_roots(root, runtime_dir,
                    exclude={active["run_ref"]} if active else set())
                if quarantined.get("status") != "PASS":
                    return _automatic_response("SANDBOX_POLICY_FAILURE", message="Unsafe orphan execution root")
            if active is None:
                from .prompting import reserve_run
                reserve_run(root, task_id)
                state_path, state_doc = _state(root)
                active = state_doc["state"]["active_run"]
            if check_control_plane(root, active)["status"] != "PASS":
                raise SafetyViolation("Current Run control-plane differs from signed boundary")
            adapter = CodexCliLocalAdapter.from_project(root)
            try:
                prepared = adapter.prepare_current_run(runtime_dir, run_ref=active["run_ref"])
            except (SafetyViolation, ValidationFailure, OSError, ValueError):
                return _automatic_failed(root, "BASELINE_CHANGED", stage="PREPARATION", runtime_root=runtime_dir)
            execution_root = Path(prepared["sandbox_request"]["execution_root"])
            _, secrets = resolve_execution_environment(adapter._bound["adapter_profile"])
            _automatic_boundary(root, active, "AUTO_RUNNING")
            process = adapter.execute(prepared["invocation"], prepared["sandbox_request"])
            normalized = adapter.normalize_result(process, Path(prepared["sandbox_request"]["output_dir"]))
            if normalized.get("reason_code"):
                return _automatic_failed(root, normalized["reason_code"], stage="AGENT", runtime_root=runtime_dir)
            if normalized.get("status") != "PENDING_INDEPENDENT_VERIFICATION":
                return _automatic_failed(root, "RESULT_INVALID", stage="AGENT", runtime_root=runtime_dir)
            _automatic_boundary(root, active, "AUTO_VERIFYING")
            before = _snapshot(root, active).get("product_files") or {}
            verdict = verify_disposable(
                canonical_project_root=root, execution_root=execution_root,
                sandbox_profile=adapter._bound["sandbox_profile"],
                task_contract=_trusted_task(root, active), baseline_files=before)
            if verdict.get("status") != "PASS":
                reason = verdict.get("reason_code") or "VERIFICATION_FAILED"
                return _automatic_failed(root, reason, stage="INDEPENDENT_VERIFICATION", runtime_root=runtime_dir)
            try:
                applied = apply_verified_diff(root, execution_root, verification=verdict, secret_values=secrets)
            except ApplyFailure as exc:
                return _automatic_failed(root, exc.reason_code, stage="APPLY", runtime_root=runtime_dir)
            if applied.get("status") != "APPLIED":
                return _automatic_failed(root, "APPLY_FAILED_RECOVERABLE", stage="APPLY", runtime_root=runtime_dir)
            # Product has now committed; a failure publishing completion cannot
            # be mislabeled as a product rollback.
            proof = _record_sandboxed_verification(root, active, verdict, applied)
            cleanup = _cleanup_automatic_attempt(root, runtime_dir, active,
                                                  quarantine=False, phase="AUTO_VERIFIED")
            policy = load_data(root / ".harness/config/PROJECT_LOCK.yaml")["project_lock"]["execution"]
            if policy["completion_policy"] == "AUTO_AFTER_PASS":
                result = complete_current(root, root / active["allowed_agent_output_path"])
                return {**result, "automatic_execution": True, "apply_evidence_ref": applied["evidence_ref"],
                        "verification_backend": "SANDBOXED", "cleanup": cleanup["status"]}
            return {"status": "SUCCEEDED", "run_status": "SUCCEEDED", "run_ref": active["run_ref"],
                    "task_ref": active["task_ref"], "project_status": "ACTIVE", "completion_status": "WAITING_EXPLICIT_COMPLETION",
                    "verification_backend": "SANDBOXED", "verification_report_ref": proof["report_ref"],
                    "apply_evidence_ref": applied["evidence_ref"], "cleanup": cleanup["status"],
                    "next_command": "project-harness complete --project <root> --result " + active["allowed_agent_output_path"]}
    except BlockingIOError:
        return _automatic_response("EXECUTOR_UNAVAILABLE", message="Another execute-current operation holds the exact project lock")
    except ResultChannelError as exc:
        return _automatic_failed(root, exc.reason_code, stage="ENVIRONMENT")
    except (SafetyViolation, ValidationFailure, ApplyFailure) as exc:
        # Unexpected safety failures cannot be transformed into a new trusted
        # RUNNING/PASS state; surface them as bounded structured errors.
        return _automatic_response(getattr(exc, "reason_code", "SANDBOX_POLICY_FAILURE"),
                                   message=type(exc).__name__, project_status="BLOCKED")

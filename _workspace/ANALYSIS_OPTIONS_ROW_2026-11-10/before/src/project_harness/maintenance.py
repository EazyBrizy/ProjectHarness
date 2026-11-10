from __future__ import annotations

"""Governed same-level maintenance lifecycle for an accepted implementation stage."""

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .operation_guard import guarded_mutation
from .platform_fs import _native_io_path, native_resolve, native_glob
from .errors import ValidationFailure
from .hashing import sha256_bytes
from .project_input import _validate_schema_node
from .resources import distribution_root
from .serialization import canonical_json_bytes, load_data
from .stage_transactions import (
    committed_stage_transaction_result,
    digest_value as stage_transaction_digest,
    recover_stage_transactions,
)
from .stages import _transactional_write, canonical_levels, load_stage_state
from .util import ensure_relative_pattern, utc_now
from .workspace import snapshot_product

MAINTENANCE_ROUTE = "MAINTAIN_CURRENT_STAGE"
MAINTENANCE_PLAN_SCHEMA_ID = "SCHEMA-MAINTENANCE-PLAN@1"
MAINTENANCE_CANCEL_SCHEMA_ID = "SCHEMA-MAINTENANCE-CANCEL-APPROVAL@1"
MAINTENANCE_CURRENT_PATH = Path(".harness/maintenance/CURRENT.yaml")
MAINTENANCE_INDEX_PATH = Path(".harness/maintenance/INDEX.yaml")
OPEN_WP_STATUSES = {"PLANNED", "READY", "IN_PROGRESS", "BLOCKED"}
TERMINAL_TASK_STATUSES = {"DONE", "CANCELLED", "SUPERSEDED", "STALE"}
_ALLOWED_START_ROUTES = {
    "TARGET_ALREADY_REACHED",
    "PLAN_ACTIVE_STAGE",
    "STAGE_PLANNING_REQUIRED",
    "STAGE_GATE_REVIEW",
    "AWAIT_STAGE_APPROVAL",
}


def _schema(name: str, expected_id: str) -> dict[str, Any]:
    path = distribution_root() / "schemas" / name
    try:
        value = json.loads(_native_io_path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationFailure("Cannot load maintenance governance schema", {"path": str(path), "error": str(exc)}) from exc
    if value.get("$id") != expected_id:
        raise ValidationFailure("Unexpected maintenance governance schema id", {"expected": expected_id, "actual": value.get("$id")})
    return value


def validate_maintenance_plan_document(value: Any) -> dict[str, Any]:
    schema = _schema("maintenance_plan.schema.json", MAINTENANCE_PLAN_SCHEMA_ID)
    issues = _validate_schema_node(value, schema, schema)
    if issues:
        raise ValidationFailure("Maintenance plan schema validation failed", issues)
    body = value.get("maintenance_plan") if isinstance(value, dict) else None
    if not isinstance(body, dict):
        raise ValidationFailure("Maintenance plan envelope is invalid")
    return deepcopy(body)


def validate_maintenance_cancel_document(value: Any) -> dict[str, Any]:
    schema = _schema("maintenance_cancel_approval.schema.json", MAINTENANCE_CANCEL_SCHEMA_ID)
    issues = _validate_schema_node(value, schema, schema)
    if issues:
        raise ValidationFailure("Maintenance cancel approval schema validation failed", issues)
    body = value.get("maintenance_cancel_approval") if isinstance(value, dict) else None
    if not isinstance(body, dict):
        raise ValidationFailure("Maintenance cancel approval envelope is invalid")
    return deepcopy(body)


def _current_document(root: Path) -> dict[str, Any]:
    path = root / MAINTENANCE_CURRENT_PATH
    if not _native_io_path(path).exists():
        return {"maintenance_current": None}
    value = load_data(path)
    if not isinstance(value, dict) or "maintenance_current" not in value:
        raise ValidationFailure("Maintenance current-state envelope is invalid", str(path))
    body = value.get("maintenance_current")
    if body is not None and not isinstance(body, dict):
        raise ValidationFailure("Maintenance current-state body is invalid", str(path))
    return value


def active_maintenance(root: Path) -> dict[str, Any] | None:
    root = native_resolve(root.expanduser())
    body = _current_document(root).get("maintenance_current")
    if not isinstance(body, dict):
        return None
    if body.get("status") not in {"ACTIVE", "BLOCKED"}:
        return None
    if body.get("maintenance_route") != MAINTENANCE_ROUTE:
        raise ValidationFailure("Open maintenance state has an invalid route", body.get("maintenance_route"))
    return deepcopy(body)


def execution_stage(root: Path) -> str:
    """Return the stage fence for the current executable route.

    Same-level maintenance intentionally executes at the accepted level while the
    canonical Stage State may already point at a later active Stage.
    """
    current = active_maintenance(root)
    if current is not None:
        return str(current["implementation_stage"])
    return str(load_stage_state(root)["active_stage"])


def maintenance_for_task(root: Path, task: dict[str, Any]) -> dict[str, Any] | None:
    current = active_maintenance(root)
    if current is None or task.get("maintenance_route") != MAINTENANCE_ROUTE:
        return None
    if task.get("maintenance_plan_ref") != current.get("plan_ref"):
        raise ValidationFailure("Maintenance Task is bound to another plan", {"task": task.get("id"), "task_plan": task.get("maintenance_plan_ref"), "current_plan": current.get("plan_ref")})
    if str(task.get("work_package_ref")).split("@", 1)[0] != str(current.get("work_package_ref")).split("@", 1)[0]:
        raise ValidationFailure("Maintenance Task is bound to another Work Package", task.get("id"))
    return current


def _load_plan(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    value = load_data(native_resolve(path.expanduser()))
    return validate_maintenance_plan_document(value), value


def _load_cancel(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    value = load_data(native_resolve(path.expanduser()))
    return validate_maintenance_cancel_document(value), value


def _project_context(root: Path) -> dict[str, Any]:
    stage = load_stage_state(root)
    state_doc = load_data(root / ".harness/state/CURRENT_STATE.yaml")
    state = state_doc.get("state") if isinstance(state_doc, dict) else None
    if not isinstance(state, dict):
        raise ValidationFailure("Project current-state envelope is invalid")
    next_doc = load_data(root / ".harness/state/NEXT_TASK.yaml")
    project = load_data(root / ".harness/config/PROJECT.yaml").get("project") or {}
    entity_paths = state.get("entity_paths") or {}
    definition_rel = entity_paths.get("project_definition")
    if not isinstance(definition_rel, str):
        raise ValidationFailure("Accepted Project Definition path is absent")
    definition = load_data(root / definition_rel).get("project_definition") or {}
    return {
        "stage": stage,
        "state_doc": state_doc,
        "state": state,
        "next_doc": next_doc,
        "project": project,
        "definition": definition,
    }


def _canonical_ref(record: dict[str, Any]) -> str:
    return f"{record['id']}@{record['revision']}"


def _short_digest(value: Any, size: int = 12) -> str:
    return sha256_bytes(canonical_json_bytes(value)).upper()[:size]


def _transaction_id(decision_id: str, suffix: str | None = None) -> str:
    token = decision_id.removeprefix("DEC-")
    return f"STX-{token}{('-' + suffix) if suffix else ''}"


def _assert_unique(values: list[str], field: str) -> None:
    if len(values) != len(set(values)):
        raise ValidationFailure(f"{field} contains duplicate values", values)


def _assert_project_id(value: str, *, prefix: str, token: str, field: str) -> None:
    expected = f"{prefix}-{token}-"
    if not value.startswith(expected):
        raise ValidationFailure(f"{field} must be project-local and start with {expected}", value)


def _validate_scope(scope: dict[str, Any], *, field: str) -> None:
    for key in ("read", "write", "forbidden"):
        values = scope.get(key) or []
        _assert_unique([str(item) for item in values], f"{field}.{key}")
        for value in values:
            ensure_relative_pattern(str(value), field=f"{field}.{key}")


def _assert_acyclic(tasks: list[dict[str, Any]]) -> None:
    ids = [str(task["id"]) for task in tasks]
    _assert_unique(ids, "maintenance_plan.work_package.tasks[].id")
    known = set(ids)
    graph: dict[str, set[str]] = {}
    for task in tasks:
        task_id = str(task["id"])
        deps = [str(item) for item in task.get("depends_on_tasks") or []]
        _assert_unique(deps, f"{task_id}.depends_on_tasks")
        unknown = sorted(set(deps) - known)
        if unknown:
            raise ValidationFailure("Maintenance Task dependency is outside the plan", {"task": task_id, "unknown": unknown})
        if task_id in deps:
            raise ValidationFailure("Maintenance Task cannot depend on itself", task_id)
        graph[task_id] = set(deps)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            raise ValidationFailure("Maintenance Task DAG contains a cycle", node)
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for task_id in ids:
        visit(task_id)


def _semantic_plan_validation(root: Path, plan: dict[str, Any], context: dict[str, Any]) -> None:
    stage = context["stage"]
    accepted = str(stage.get("highest_accepted_level"))
    target = str(stage.get("target_level"))
    if accepted not in canonical_levels():
        raise ValidationFailure("Maintenance requires a formally accepted current level", accepted)
    exact = {
        "highest_accepted_level": accepted,
        "implementation_stage": accepted,
        "target_level": target,
        "last_acceptance_ref": stage.get("last_acceptance_ref"),
        "accepted_scope_ref": context["definition"].get("scope_ref"),
    }
    mismatches = {
        key: {"expected": expected, "actual": plan.get(key)}
        for key, expected in exact.items()
        if plan.get(key) != expected
    }
    if mismatches:
        raise ValidationFailure("Maintenance plan is not exact-bound to the accepted project context", mismatches)
    if plan.get("route") != MAINTENANCE_ROUTE:
        raise ValidationFailure("Maintenance plan route is invalid", plan.get("route"))
    if plan.get("status") != "APPROVED":
        raise ValidationFailure("Maintenance plan must be formally APPROVED", plan.get("status"))
    decision = plan["decision"]
    if decision.get("kind") != MAINTENANCE_ROUTE or decision.get("approved") is not True:
        raise ValidationFailure("Maintenance start Decision must approve MAINTAIN_CURRENT_STAGE", decision)
    boundary = plan["scope_boundary"]
    if boundary.get("future_stage_work") != "FORBIDDEN" or boundary.get("future_stage_refs") != []:
        raise ValidationFailure("Maintenance plan contains next-stage/future-stage scope", boundary)
    if plan["rollback_constraints"].get("automatic_rollback") is not False:
        raise ValidationFailure("Maintenance cannot invent automatic rollback", plan["rollback_constraints"])
    if plan["cancel_constraints"].get("before_product_change_only") is not True:
        raise ValidationFailure("Maintenance cancel boundary must be pre-product-change only", plan["cancel_constraints"])

    token = str(context["project"].get("id_token") or "")
    _assert_project_id(str(plan["id"]), prefix="RQP", token=token, field="maintenance_plan.id")
    _assert_project_id(str(decision["id"]), prefix="DEC", token=token, field="maintenance_plan.decision.id")
    wp = plan["work_package"]
    _assert_project_id(str(wp["id"]), prefix="WP", token=token, field="maintenance_plan.work_package.id")
    if wp.get("implementation_stage") != accepted:
        raise ValidationFailure("Maintenance Work Package must remain at highest_accepted_level", wp.get("implementation_stage"))
    tasks = wp["tasks"]
    _assert_acyclic(tasks)
    for index, task in enumerate(tasks):
        _assert_project_id(str(task["id"]), prefix="TSK", token=token, field=f"tasks[{index}].id")
        if task.get("implementation_stage") != accepted:
            raise ValidationFailure("Maintenance Task contains wrong/future implementation stage", {"task": task.get("id"), "stage": task.get("implementation_stage"), "accepted": accepted})
        if task.get("future_stage_work") != "FORBIDDEN":
            raise ValidationFailure("Maintenance Task permits future-stage work", task.get("id"))
        _validate_scope(task["scope"], field=f"tasks[{index}].scope")
        commands = task["verification"].get("commands") or []
        for command_index, command in enumerate(commands):
            if not isinstance(command.get("argv"), list) or not command["argv"]:
                raise ValidationFailure("Maintenance verification command argv is empty", {"task": task.get("id"), "index": command_index})


def _open_maintenance_wps(root: Path) -> list[str]:
    index_path = root / ".harness/work-packages/INDEX.yaml"
    if not _native_io_path(index_path).exists():
        return []
    index = load_data(index_path).get("work_package_index") or {}
    result: list[str] = []
    for wp_id, rel in (index.get("current") or {}).items():
        try:
            wp = load_data(root / str(rel)).get("work_package") or {}
        except Exception:
            continue
        if wp.get("maintenance_route") == MAINTENANCE_ROUTE and wp.get("status") in OPEN_WP_STATUSES:
            result.append(str(wp_id))
    return sorted(result)


def _assert_start_idle(root: Path, context: dict[str, Any]) -> None:
    state = context["state"]
    if isinstance(state.get("active_run"), dict):
        raise ValidationFailure("Maintenance cannot start while a Run is active", state["active_run"].get("run_ref"))
    if state.get("current_task_ref") is not None:
        raise ValidationFailure("Maintenance cannot start while another Task route is open", state.get("current_task_ref"))
    if state.get("project_status") == "BLOCKED":
        raise ValidationFailure("Maintenance cannot start while the project is BLOCKED", state.get("next_route"))
    if active_maintenance(root) is not None or _open_maintenance_wps(root):
        raise ValidationFailure("Another maintenance route is already open", _open_maintenance_wps(root))
    route = str(state.get("next_route") or "")
    if route not in _ALLOWED_START_ROUTES:
        raise ValidationFailure("Maintenance cannot start during an active planning/Gate transition", {"next_route": route, "allowed_idle_routes": sorted(_ALLOWED_START_ROUTES)})
    handoff = str(state.get("handoff_status") or "")
    if handoff in {"GATE_READINESS_EVALUATION", "STAGE_ACCEPTANCE_PREPARATION", "GATE_RECOVERY_REQUIRED", "STAGE_PLANNING_APPLICATION"}:
        raise ValidationFailure("Maintenance cannot start during an active Stage/Gate application", handoff)


def _next_sequence(root: Path) -> int:
    index = load_data(root / ".harness/tasks/INDEX.yaml").get("task_index") or {}
    highest = 0
    for rel in (index.get("current") or {}).values():
        try:
            task = load_data(root / str(rel)).get("task") or {}
            highest = max(highest, int(task.get("sequence", 0)))
        except Exception:
            continue
    return ((highest // 10) + 1) * 10


def _index_document(root: Path, rel: str, envelope: str, default: dict[str, Any]) -> dict[str, Any]:
    path = root / rel
    if not _native_io_path(path).exists():
        return {envelope: deepcopy(default)}
    value = load_data(path)
    if not isinstance(value, dict) or not isinstance(value.get(envelope), dict):
        raise ValidationFailure(f"{envelope} envelope is invalid", rel)
    return value


def _build_start_writes(root: Path, plan: dict[str, Any], context: dict[str, Any]) -> tuple[dict[Path, Any], dict[str, Any]]:
    now = utc_now()
    plan_ref = _canonical_ref(plan)
    decision = plan["decision"]
    decision_ref = f"{decision['id']}@1"
    wp_in = plan["work_package"]
    wp_id = str(wp_in["id"])
    tasks_in = wp_in["tasks"]
    token = str(context["project"]["id_token"])
    fingerprint = _short_digest({"plan_ref": plan_ref, "decision_ref": decision_ref}, 10)

    task_index_doc = deepcopy(load_data(root / ".harness/tasks/INDEX.yaml"))
    wp_index_doc = deepcopy(load_data(root / ".harness/work-packages/INDEX.yaml"))
    task_index = task_index_doc["task_index"]
    wp_index = wp_index_doc["work_package_index"]
    collisions = [task["id"] for task in tasks_in if task["id"] in (task_index.get("current") or {})]
    if collisions:
        raise ValidationFailure("Maintenance plan reuses existing Task ids", collisions)
    if wp_id in (wp_index.get("current") or {}):
        raise ValidationFailure("Maintenance plan reuses an existing Work Package id", wp_id)

    maintenance_index_doc = _index_document(
        root,
        MAINTENANCE_INDEX_PATH.as_posix(),
        "maintenance_index",
        {"order": [], "current": {}, "reports": {}},
    )
    maintenance_index = maintenance_index_doc["maintenance_index"]
    if plan["id"] in (maintenance_index.get("current") or {}):
        raise ValidationFailure("Maintenance plan id already exists", plan["id"])

    writes: dict[Path, Any] = {}
    plan_rel = Path(f".harness/maintenance/PLANS/{plan_ref}.yaml")
    decision_rel = Path(f".harness/canonical/DECISIONS/{decision['id']}@1.yaml")
    if (_native_io_path(root / plan_rel)).exists() or (_native_io_path(root / decision_rel)).exists():
        raise ValidationFailure("Maintenance plan or Decision immutable path already exists", {"plan": plan_rel.as_posix(), "decision": decision_rel.as_posix()})
    writes[plan_rel] = {"maintenance_plan": deepcopy(plan)}
    writes[decision_rel] = {
        "decision": {
            "id": decision["id"],
            "revision": 1,
            "kind": MAINTENANCE_ROUTE,
            "subject_ref": plan_ref,
            "approved": True,
            "actor": decision["actor"],
            "approved_at": decision["approved_at"],
            "notes": plan["rationale"],
            "status": "ACCEPTED",
        }
    }

    base_sequence = _next_sequence(root)
    task_ids = [str(task["id"]) for task in tasks_in]
    completed_ids = {str(ref).split("@", 1)[0] for ref in context["state"].get("completed_task_refs") or []}
    first_ready: str | None = None
    task_paths: dict[str, str] = {}
    for ordinal, task_in in enumerate(tasks_in, 1):
        task_id = str(task_in["id"])
        sequence = base_sequence + (ordinal - 1) * 10
        deps = [str(item) for item in task_in.get("depends_on_tasks") or []]
        if first_ready is None and set(deps).issubset(completed_ids):
            first_ready = task_id
        status = "READY" if task_id == first_ready else "PLANNED"
        artifact_token = f"{token}-MNT-{fingerprint}-{ordinal:03d}"
        verification_id = f"VFP-{artifact_token}"
        prompt_plan_id = f"PPL-{artifact_token}"
        context_plan_id = f"CTX-{artifact_token}"
        verification = deepcopy(task_in["verification"])
        verification_profile = {
            "id": verification_id,
            "revision": 1,
            "task_ref": f"{task_id}@1",
            "implementation_stage": plan["implementation_stage"],
            "maintenance_route": MAINTENANCE_ROUTE,
            "maintenance_plan_ref": plan_ref,
            "commands": verification.get("commands") or [],
            "expected_paths": verification.get("expected_paths") or [],
            "manual_checks": verification.get("manual_checks") or [],
            "timeout_seconds": int(verification.get("timeout_seconds", 300)),
            "allow_manual": bool(verification.get("allow_manual", False)),
            "status": "ACTIVE",
        }
        prompt_plan = {
            "id": prompt_plan_id,
            "revision": 1,
            "task_ref": f"{task_id}@1",
            "implementation_stage": plan["implementation_stage"],
            "maintenance_route": MAINTENANCE_ROUTE,
            "maintenance_plan_ref": plan_ref,
            "prompt_spec_ref": task_in["prompt_spec_ref"],
            "module_refs": ["PMD-CORE-ROLE@1", "PMD-TASK-CONTRACT@1", "PMD-RESULT-SCHEMA@1"],
            "resolved_inputs": {
                "task_hash": f"sha256:{sha256_bytes(canonical_json_bytes(task_in))}",
                "skill_ref": task_in["route"]["primary_skill_ref"],
                "context_plan_ref": f"{context_plan_id}@1",
            },
            "output_schema_ref": "SCHEMA-AGENT-TASK-RESULT@1",
            "status": "RESOLVED",
        }
        context_plan = {
            "id": context_plan_id,
            "revision": 1,
            "task_ref": f"{task_id}@1",
            "implementation_stage": plan["implementation_stage"],
            "maintenance_route": MAINTENANCE_ROUTE,
            "maintenance_plan_ref": plan_ref,
            "include": {
                "project_definition": True,
                "architecture_baseline": True,
                "technology_baseline": True,
                "task_dependencies": deps,
                "read_paths": task_in["scope"].get("read") or [],
            },
            "exclude": ["secrets", "unrelated tasks", "future-stage work", "provider accounting"],
            "status": "READY",
        }
        task = {
            "id": task_id,
            "revision": 1,
            "work_package_ref": wp_id,
            "implementation_stage": plan["implementation_stage"],
            "maintenance_route": MAINTENANCE_ROUTE,
            "maintenance_plan_ref": plan_ref,
            "maintenance_decision_ref": decision_ref,
            "maintenance_product_changing": bool(task_in["product_changing"]),
            "future_stage_work": "FORBIDDEN",
            "title": task_in["title"],
            "type": task_in["type"],
            "track": "MAINTENANCE",
            "priority": task_in["priority"],
            "sequence": sequence,
            "purpose": task_in["purpose"],
            "expected_result": task_in["expected_result"],
            "requirement_refs": task_in.get("requirement_refs") or [],
            "constraint_refs": task_in.get("constraint_refs") or [],
            "architecture_refs": task_in.get("architecture_refs") or [],
            "documentation": deepcopy(task_in["documentation"]),
            "depends_on_tasks": deps,
            "requires_artifacts": [plan["last_acceptance_ref"], plan["accepted_scope_ref"]],
            "produces_artifacts": task_in.get("produces_artifacts") or [],
            "scope": deepcopy(task_in["scope"]),
            "route": deepcopy(task_in["route"]),
            "prompt_spec_ref": task_in["prompt_spec_ref"],
            "prompt_plan_ref": f"{prompt_plan_id}@1",
            "context_policy_ref": "CTP-TASK-STANDARD@1",
            "context_plan_ref": f"{context_plan_id}@1",
            "verification_profile_ref": f"{verification_id}@1",
            "verification": verification,
            "acceptance_criteria": deepcopy(task_in["acceptance_criteria"]),
            "rollback": deepcopy(task_in["rollback"]),
            "status": status,
            "created_at": now,
        }
        task_rel = f".harness/tasks/{task_id}@1.yaml"
        writes[Path(task_rel)] = {"task": task}
        writes[Path(f".harness/verification/PROFILES/{verification_id}@1.yaml")] = {"verification_profile": verification_profile}
        writes[Path(f".harness/prompts/PLANS/{prompt_plan_id}@1.yaml")] = {"prompt_plan": prompt_plan}
        writes[Path(f".harness/context/PLANS/{context_plan_id}@1.yaml")] = {"context_plan": context_plan}
        task_paths[task_id] = task_rel
        task_index.setdefault("order", []).append(task_id)
        task_index.setdefault("current", {})[task_id] = task_rel
        task_index.setdefault("aliases", {})[task_id] = task_id

    if first_ready is None:
        raise ValidationFailure("Maintenance plan has no deterministic first runnable Task")

    dag_id = f"DAG-{token}-MNT-{fingerprint}"
    dag = {
        "id": dag_id,
        "revision": 1,
        "nodes": task_ids,
        "edges": [
            {"from": dependency, "to": str(task["id"])}
            for task in tasks_in
            for dependency in task.get("depends_on_tasks") or []
        ],
        "scheduler_policy": "SINGLE_ACTIVE_TASK",
        "implementation_stage": plan["implementation_stage"],
        "maintenance_route": MAINTENANCE_ROUTE,
        "maintenance_plan_ref": plan_ref,
        "status": "ACTIVE",
    }
    writes[Path(f".harness/dags/{dag_id}@1.yaml")] = {"dependency_graph": dag}
    wp = {
        "id": wp_id,
        "revision": 1,
        "request_refs": [plan_ref],
        "title": wp_in["title"],
        "objective": wp_in["objective"],
        "implementation_stage": plan["implementation_stage"],
        "maintenance_route": MAINTENANCE_ROUTE,
        "maintenance_plan_ref": plan_ref,
        "maintenance_decision_ref": decision_ref,
        "accepted_scope_ref": plan["accepted_scope_ref"],
        "last_acceptance_ref": plan["last_acceptance_ref"],
        "requirement_refs": [],
        "architecture_refs": [],
        "documentation_refs": [],
        "mandatory_task_refs": task_ids,
        "dependency_graph_ref": f"{dag_id}@1",
        "aggregation_rule": "ALL_MANDATORY_PASS",
        "verification_constraints": deepcopy(plan["verification_constraints"]),
        "rollback_constraints": deepcopy(plan["rollback_constraints"]),
        "cancel_constraints": deepcopy(plan["cancel_constraints"]),
        "status": "READY",
        "created_at": now,
    }
    wp_rel = f".harness/work-packages/{wp_id}@1.yaml"
    writes[Path(wp_rel)] = {"work_package": wp}
    wp_index.setdefault("order", []).append(wp_id)
    wp_index.setdefault("current", {})[wp_id] = wp_rel

    previous_route = {
        "project_status": context["state"].get("project_status"),
        "handoff_status": context["state"].get("handoff_status"),
        "current_task_ref": context["state"].get("current_task_ref"),
        "next_route": context["state"].get("next_route"),
        "active_stage": context["state"].get("active_stage"),
        "blocked_task_refs": deepcopy(context["state"].get("blocked_task_refs") or []),
        "open_blocker_refs": deepcopy(context["state"].get("open_blocker_refs") or []),
        "next_task_document": deepcopy(context["next_doc"]),
    }
    maintenance_current = {
        "schema_version": 1,
        "maintenance_route": MAINTENANCE_ROUTE,
        "status": "ACTIVE",
        "plan_ref": plan_ref,
        "plan_path": plan_rel.as_posix(),
        "decision_ref": decision_ref,
        "work_package_ref": f"{wp_id}@1",
        "task_refs": [f"{task_id}@1" for task_id in task_ids],
        "implementation_stage": plan["implementation_stage"],
        "highest_accepted_level": plan["highest_accepted_level"],
        "target_level": plan["target_level"],
        "last_acceptance_ref": plan["last_acceptance_ref"],
        "accepted_scope_ref": plan["accepted_scope_ref"],
        "previous_route": previous_route,
        "started_at": now,
        "updated_at": now,
    }
    writes[MAINTENANCE_CURRENT_PATH] = {"maintenance_current": maintenance_current}
    maintenance_index.setdefault("order", []).append(plan["id"])
    maintenance_index.setdefault("current", {})[plan["id"]] = {
        "plan_ref": plan_ref,
        "plan_path": plan_rel.as_posix(),
        "decision_ref": decision_ref,
        "work_package_ref": f"{wp_id}@1",
        "status": "ACTIVE",
    }
    maintenance_index.setdefault("reports", {})[plan["id"]] = []
    writes[MAINTENANCE_INDEX_PATH] = maintenance_index_doc

    state_doc = deepcopy(context["state_doc"])
    state = state_doc["state"]
    state.setdefault("task_order", []).extend(task_ids)
    state["project_status"] = "ACTIVE"
    state["handoff_status"] = "MAINTENANCE_ACTIVE"
    state["current_task_ref"] = first_ready
    state["active_run"] = None
    state["next_route"] = MAINTENANCE_ROUTE
    state["maintenance_route"] = MAINTENANCE_ROUTE
    state["maintenance_plan_ref"] = plan_ref
    state["maintenance_work_package_ref"] = f"{wp_id}@1"
    state["updated_at"] = now
    writes[Path(".harness/state/CURRENT_STATE.yaml")] = state_doc
    writes[Path(".harness/state/NEXT_TASK.yaml")] = {
        "next_task": {
            "status": "READY",
            "task_ref": f"{first_ready}@1",
            "run_ref": None,
            "implementation_stage": plan["implementation_stage"],
            "target_implementation_level": plan["target_level"],
            "maintenance_route": MAINTENANCE_ROUTE,
            "maintenance_plan_ref": plan_ref,
            "next_route": MAINTENANCE_ROUTE,
        }
    }
    writes[Path(".harness/tasks/INDEX.yaml")] = task_index_doc
    writes[Path(".harness/work-packages/INDEX.yaml")] = wp_index_doc

    result = {
        "status": "MAINTENANCE_ACTIVE",
        "route": MAINTENANCE_ROUTE,
        "maintenance_plan_ref": plan_ref,
        "decision_ref": decision_ref,
        "work_package_ref": f"{wp_id}@1",
        "task_refs": [f"{task_id}@1" for task_id in task_ids],
        "first_task_ref": f"{first_ready}@1",
        "implementation_stage": plan["implementation_stage"],
        "target_level": plan["target_level"],
        "highest_accepted_level": plan["highest_accepted_level"],
        "last_acceptance_ref": plan["last_acceptance_ref"],
        "kernel_written_paths": sorted(path.as_posix() for path in writes),
    }
    return writes, result


def _reserve_first_if_required(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    current = active_maintenance(root)
    if current is None or current.get("plan_ref") != result.get("maintenance_plan_ref"):
        return result
    state = load_data(root / ".harness/state/CURRENT_STATE.yaml").get("state") or {}
    first_id = str(result["first_task_ref"]).split("@", 1)[0]
    completed = {str(ref).split("@", 1)[0] for ref in state.get("completed_task_refs") or []}
    if first_id in completed or state.get("current_task_ref") != first_id:
        return result
    from .prompting import reserve_run

    output = deepcopy(result)
    output["next"] = reserve_run(root, first_id)
    return output


@guarded_mutation
def start_maintenance(root: Path, plan_path: Path) -> dict[str, Any]:
    """Start an exact-bound, governed same-level maintenance Work Package."""
    root = native_resolve(root.expanduser())
    recover_stage_transactions(root)
    plan, source_document = _load_plan(plan_path)
    context = _project_context(root)
    _semantic_plan_validation(root, plan, context)
    transaction_id = _transaction_id(plan["decision"]["id"])
    request_digest = stage_transaction_digest(source_document)
    replay = committed_stage_transaction_result(
        root,
        transaction_id=transaction_id,
        operation_kind="START_MAINTENANCE",
        request_digest=request_digest,
    )
    if replay is not None:
        return _reserve_first_if_required(root, replay)
    _assert_start_idle(root, context)
    writes, result = _build_start_writes(root, plan, context)
    committed = _transactional_write(
        root,
        writes,
        transaction_id=transaction_id,
        operation_kind="START_MAINTENANCE",
        request_digest=request_digest,
        result=result,
    )
    return _reserve_first_if_required(root, committed)


def _load_current_task(root: Path, task_id: str) -> tuple[dict[str, Any], str]:
    index = load_data(root / ".harness/tasks/INDEX.yaml").get("task_index") or {}
    rel = (index.get("current") or {}).get(task_id)
    if not isinstance(rel, str):
        raise ValidationFailure("Maintenance Task is absent from the current index", task_id)
    task = load_data(root / rel).get("task") or {}
    if not isinstance(task, dict):
        raise ValidationFailure("Maintenance Task envelope is invalid", rel)
    return task, rel


def _load_current_wp(root: Path, wp_ref: str) -> tuple[dict[str, Any], str]:
    wp_id = str(wp_ref).split("@", 1)[0]
    index = load_data(root / ".harness/work-packages/INDEX.yaml").get("work_package_index") or {}
    rel = (index.get("current") or {}).get(wp_id)
    if not isinstance(rel, str):
        raise ValidationFailure("Maintenance Work Package is absent from the current index", wp_id)
    wp = load_data(root / rel).get("work_package") or {}
    if not isinstance(wp, dict):
        raise ValidationFailure("Maintenance Work Package envelope is invalid", rel)
    return wp, rel


def _revision(value: dict[str, Any], *, status: str, now: str, **changes: Any) -> dict[str, Any]:
    revised = deepcopy(value)
    revised["previous_revision_ref"] = f"{value['id']}@{value['revision']}"
    revised["revision"] = int(value["revision"]) + 1
    revised["status"] = status
    revised.update(changes)
    revised["updated_at"] = now
    return revised


def _restore_state(current_state_doc: dict[str, Any], maintenance: dict[str, Any], *, now: str) -> tuple[dict[str, Any], dict[str, Any]]:
    restored_doc = deepcopy(current_state_doc)
    restored = restored_doc["state"]
    previous = maintenance["previous_route"]
    restored["project_status"] = previous["project_status"]
    restored["handoff_status"] = previous["handoff_status"]
    restored["current_task_ref"] = previous["current_task_ref"]
    restored["active_run"] = None
    restored["next_route"] = previous["next_route"]
    restored["active_stage"] = previous["active_stage"]
    restored["blocked_task_refs"] = deepcopy(previous.get("blocked_task_refs") or [])
    restored["open_blocker_refs"] = deepcopy(previous.get("open_blocker_refs") or [])
    restored.pop("maintenance_route", None)
    restored.pop("maintenance_plan_ref", None)
    restored.pop("maintenance_work_package_ref", None)
    restored["updated_at"] = now
    return restored_doc, deepcopy(previous["next_task_document"])


def _maintenance_reports(root: Path, maintenance: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    task_ids = {str(ref).split("@", 1)[0] for ref in maintenance.get("task_refs") or []}
    reports: list[dict[str, Any]] = []
    for ref in state.get("task_report_refs") or []:
        path = root / f".harness/reports/{ref}.yaml"
        if not _native_io_path(path).exists():
            continue
        report = load_data(path).get("task_report") or {}
        task_id = str(report.get("task_ref") or "").split("@", 1)[0]
        if task_id in task_ids:
            reports.append(report)
    return reports


def _completed_product_changes(root: Path, maintenance: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for ref in maintenance.get("task_refs") or []:
        task_id = str(ref).split("@", 1)[0]
        task, _ = _load_current_task(root, task_id)
        if task.get("status") == "DONE" and task.get("maintenance_product_changing") is True:
            findings.append({"task_ref": f"{task_id}@{task['revision']}", "reason": "plan marks the completed Task as product-changing"})
    for report in _maintenance_reports(root, maintenance, state):
        changes = report.get("changes") or {}
        observed = sorted({str(item) for key in ("added", "modified", "deleted") for item in changes.get(key) or []})
        if observed:
            findings.append({"task_ref": report.get("task_ref"), "task_report_ref": report.get("id"), "reason": "completed Task Report contains product changes", "paths": observed})
    return findings


def _update_maintenance_index(root: Path, plan_id: str, *, status: str, work_package_ref: str, report_ref: str | None = None) -> dict[str, Any]:
    value = _index_document(root, MAINTENANCE_INDEX_PATH.as_posix(), "maintenance_index", {"order": [], "current": {}, "reports": {}})
    index = value["maintenance_index"]
    current = index.setdefault("current", {}).get(plan_id)
    if not isinstance(current, dict):
        raise ValidationFailure("Maintenance plan is absent from the maintenance index", plan_id)
    current["status"] = status
    current["work_package_ref"] = work_package_ref
    if report_ref is not None:
        current["report_ref"] = report_ref
        reports = index.setdefault("reports", {}).setdefault(plan_id, [])
        if report_ref not in reports:
            reports.append(report_ref)
    return value


def _cancel_safe_active_run(root: Path, state: dict[str, Any], *, decision_ref: str, now: str) -> tuple[dict[Path, Any], str | None]:
    active = state.get("active_run")
    if not isinstance(active, dict):
        return {}, None
    result_rel = str(active.get("allowed_agent_output_path") or "")
    if result_rel and (_native_io_path(root / result_rel)).exists():
        raise ValidationFailure(
            "Maintenance cancel is not permitted after an Agent Task Result was submitted; finish verification/completion or use an existing governed compensation route",
            {"run_ref": active.get("run_ref"), "result_path": result_rel},
        )
    snapshot_rel = active.get("snapshot_path")
    if not isinstance(snapshot_rel, str):
        raise ValidationFailure("Active maintenance Run has no trusted product snapshot", active.get("run_ref"))
    snapshot = load_data(root / snapshot_rel).get("snapshot") or {}
    before = snapshot.get("product_files")
    if not isinstance(before, dict):
        raise ValidationFailure("Active maintenance Run product snapshot is invalid", snapshot_rel)
    current = snapshot_product(root)
    if current != before:
        changed = sorted(set(before) ^ set(current) | {path for path in set(before) & set(current) if before[path] != current[path]})
        raise ValidationFailure(
            "Maintenance cancel is not permitted after uncommitted product changes; no automatic rollback is invented",
            {"run_ref": active.get("run_ref"), "changed_paths": changed},
        )
    run_ref = str(active["run_ref"])
    run_path = Path(f".harness/runtime/RUNS/{run_ref}.yaml")
    if (_native_io_path(root / run_path)).exists():
        raise ValidationFailure("Active maintenance Run immutable record already exists", run_ref)
    run = {
        "id": run_ref,
        "task_ref": active["task_ref"],
        "implementation_stage": active["implementation_stage"],
        "maintenance_route": MAINTENANCE_ROUTE,
        "maintenance_plan_ref": active.get("maintenance_plan_ref"),
        "attempt_no": active["attempt_no"],
        "run_plan_ref": active["run_plan_ref"],
        "status": "CANCELLED",
        "evidence_refs": [],
        "actual_changes": {"added": [], "modified": [], "deleted": []},
        "cancel_decision_ref": decision_ref,
        "compensation_status": "NOT_REQUIRED",
        "completed_at": now,
    }
    return {run_path: {"run": run}}, run_ref


def _assert_no_blocked_run_product_drift(root: Path, maintenance: dict[str, Any]) -> None:
    """Reject cancellation when an inactive blocked attempt left product changes.

    ``block`` closes the active Run record before cancellation is requested.  The
    trusted pre-Run snapshot therefore has to be resolved through the immutable
    Run Plan instead of ``CURRENT_STATE.active_run``.
    """
    task_ids = {str(ref).split("@", 1)[0] for ref in maintenance.get("task_refs") or []}
    blocked_runs: list[dict[str, Any]] = []
    run_dir = root / ".harness/runtime/RUNS"
    if _native_io_path(run_dir).exists():
        for path in sorted(native_glob(run_dir,'RUN-*.yaml')):
            run = load_data(path).get("run") or {}
            task_id = str(run.get("task_ref") or "").split("@", 1)[0]
            if task_id in task_ids and run.get("status") == "BLOCKED":
                blocked_runs.append(run)
    if not blocked_runs:
        return
    latest = max(blocked_runs, key=lambda item: int(item.get("attempt_no", 0)))
    run_plan_ref = latest.get("run_plan_ref")
    if not isinstance(run_plan_ref, str):
        raise ValidationFailure("Blocked maintenance Run has no immutable Run Plan reference", latest.get("id"))
    run_plan_path = root / f".harness/runtime/RUN_PLANS/{run_plan_ref}@1.yaml"
    run_plan = load_data(run_plan_path).get("run_plan") or {}
    snapshot_ref = (run_plan.get("base_revisions") or {}).get("repository_snapshot")
    if not isinstance(snapshot_ref, str):
        raise ValidationFailure("Blocked maintenance Run Plan has no trusted repository snapshot", run_plan_ref)
    snapshot_path = root / f".harness/runtime/SNAPSHOTS/{snapshot_ref}.yaml"
    snapshot = load_data(snapshot_path).get("snapshot") or {}
    before = snapshot.get("product_files")
    if not isinstance(before, dict):
        raise ValidationFailure("Blocked maintenance Run product snapshot is invalid", snapshot_ref)
    current = snapshot_product(root)
    if current != before:
        changed = sorted(set(before) ^ set(current) | {path for path in set(before) & set(current) if before[path] != current[path]})
        raise ValidationFailure(
            "Maintenance cancel is not permitted while a blocked attempt has uncommitted product changes; no automatic rollback is invented",
            {"run_ref": latest.get("id"), "changed_paths": changed},
        )


@guarded_mutation
def cancel_maintenance(root: Path, approval_path: Path) -> dict[str, Any]:
    """Cancel an open maintenance route only before product-changing completion."""
    root = native_resolve(root.expanduser())
    recover_stage_transactions(root)
    approval, source_document = _load_cancel(approval_path)
    transaction_id = _transaction_id(approval["id"])
    request_digest = stage_transaction_digest(source_document)
    replay = committed_stage_transaction_result(
        root,
        transaction_id=transaction_id,
        operation_kind="CANCEL_MAINTENANCE",
        request_digest=request_digest,
    )
    if replay is not None:
        return replay
    maintenance = active_maintenance(root)
    if maintenance is None:
        raise ValidationFailure("No open maintenance route is available to cancel")
    context = _project_context(root)
    stage = context["stage"]
    exact = {
        "maintenance_plan_ref": maintenance["plan_ref"],
        "work_package_ref": maintenance["work_package_ref"],
        "highest_accepted_level": stage["highest_accepted_level"],
        "target_level": stage["target_level"],
        "last_acceptance_ref": stage["last_acceptance_ref"],
    }
    mismatches = {key: {"expected": expected, "actual": approval.get(key)} for key, expected in exact.items() if approval.get(key) != expected}
    if mismatches:
        raise ValidationFailure("Maintenance cancel approval is not exact-bound to the open route", mismatches)
    if approval.get("kind") != "CANCEL_MAINTENANCE" or approval.get("approved") is not True:
        raise ValidationFailure("Formal CANCEL_MAINTENANCE Decision is required")
    changed = _completed_product_changes(root, maintenance, context["state"])
    if changed:
        raise ValidationFailure(
            "Silent maintenance cancel is forbidden after a completed product-changing Task; complete the route or use an existing governed compensation/rollback route",
            changed,
        )
    _assert_no_blocked_run_product_drift(root, maintenance)

    now = utc_now()
    decision_ref = f"{approval['id']}@1"
    writes, cancelled_run_ref = _cancel_safe_active_run(root, context["state"], decision_ref=decision_ref, now=now)
    task_index_doc = deepcopy(load_data(root / ".harness/tasks/INDEX.yaml"))
    task_index = task_index_doc["task_index"]
    cancelled_task_refs: list[str] = []
    for ref in maintenance.get("task_refs") or []:
        task_id = str(ref).split("@", 1)[0]
        task, _ = _load_current_task(root, task_id)
        if task.get("status") in TERMINAL_TASK_STATUSES:
            continue
        revised = _revision(task, status="CANCELLED", now=now, cancelled_by=f"{approval['id']}@1", cancelled_at=now)
        rel = f".harness/tasks/{task_id}@{revised['revision']}.yaml"
        writes[Path(rel)] = {"task": revised}
        task_index["current"][task_id] = rel
        cancelled_task_refs.append(f"{task_id}@{revised['revision']}")
    writes[Path(".harness/tasks/INDEX.yaml")] = task_index_doc

    wp, _ = _load_current_wp(root, maintenance["work_package_ref"])
    revised_wp = _revision(wp, status="CANCELLED", now=now, cancelled_by=f"{approval['id']}@1", cancelled_at=now)
    wp_rel = f".harness/work-packages/{wp['id']}@{revised_wp['revision']}.yaml"
    wp_index_doc = deepcopy(load_data(root / ".harness/work-packages/INDEX.yaml"))
    wp_index_doc["work_package_index"]["current"][wp["id"]] = wp_rel
    writes[Path(wp_rel)] = {"work_package": revised_wp}
    writes[Path(".harness/work-packages/INDEX.yaml")] = wp_index_doc

    decision_rel = Path(f".harness/canonical/DECISIONS/{approval['id']}@1.yaml")
    if (_native_io_path(root / decision_rel)).exists():
        raise ValidationFailure("Maintenance cancel Decision already exists", approval["id"])
    writes[decision_rel] = {
        "decision": {
            "id": approval["id"],
            "revision": 1,
            "kind": "CANCEL_MAINTENANCE",
            "subject_ref": maintenance["plan_ref"],
            "approved": True,
            "actor": approval["actor"],
            "approved_at": approval["approved_at"],
            "notes": approval["rationale"],
            "status": "ACCEPTED",
        }
    }
    report_id = f"VAL-{str(context['project']['id_token'])}-MAINT-CANCEL-{_short_digest({'plan': maintenance['plan_ref'], 'decision': decision_ref}, 10)}"
    report_ref = f"{report_id}@1"
    report_rel = Path(f".harness/maintenance/REPORTS/{report_ref}.yaml")
    writes[report_rel] = {
        "maintenance_report": {
            "id": report_id,
            "revision": 1,
            "kind": "MAINTENANCE_CANCELLATION",
            "status": "CANCELLED",
            "maintenance_route": MAINTENANCE_ROUTE,
            "maintenance_plan_ref": maintenance["plan_ref"],
            "start_decision_ref": maintenance["decision_ref"],
            "cancel_decision_ref": decision_ref,
            "work_package_ref": f"{wp['id']}@{revised_wp['revision']}",
            "implementation_stage": maintenance["implementation_stage"],
            "cancelled_task_refs": cancelled_task_refs,
            "cancelled_run_ref": cancelled_run_ref,
            "completed_non_product_changing_task_refs": [
                f"{task['id']}@{task['revision']}"
                for task_id in [str(ref).split("@", 1)[0] for ref in maintenance.get("task_refs") or []]
                for task, _ in [_load_current_task(root, task_id)]
                if task.get("status") == "DONE"
            ],
            "rationale": approval["rationale"],
            "recorded_at": now,
        }
    }
    restored_state_doc, restored_next_doc = _restore_state(context["state_doc"], maintenance, now=now)
    writes[Path(".harness/state/CURRENT_STATE.yaml")] = restored_state_doc
    writes[Path(".harness/state/NEXT_TASK.yaml")] = restored_next_doc
    writes[MAINTENANCE_CURRENT_PATH] = {"maintenance_current": None}
    plan_id = str(maintenance["plan_ref"]).split("@", 1)[0]
    writes[MAINTENANCE_INDEX_PATH] = _update_maintenance_index(
        root,
        plan_id,
        status="CANCELLED",
        work_package_ref=f"{wp['id']}@{revised_wp['revision']}",
        report_ref=report_ref,
    )
    result = {
        "status": "MAINTENANCE_CANCELLED",
        "route": MAINTENANCE_ROUTE,
        "maintenance_plan_ref": maintenance["plan_ref"],
        "decision_ref": decision_ref,
        "work_package_ref": f"{wp['id']}@{revised_wp['revision']}",
        "report_ref": report_ref,
        "cancelled_task_refs": cancelled_task_refs,
        "cancelled_run_ref": cancelled_run_ref,
        "implementation_stage": maintenance["implementation_stage"],
        "target_level": stage["target_level"],
        "highest_accepted_level": stage["highest_accepted_level"],
        "active_stage": stage["active_stage"],
        "next_route": restored_state_doc["state"]["next_route"],
        "kernel_written_paths": sorted(path.as_posix() for path in writes),
    }
    return _transactional_write(
        root,
        writes,
        transaction_id=transaction_id,
        operation_kind="CANCEL_MAINTENANCE",
        request_digest=request_digest,
        result=result,
    )


def finalize_maintenance(root: Path, *, state_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    """Atomically close the open maintenance WP after all mandatory Tasks are DONE."""
    root = native_resolve(root.expanduser())
    recover_stage_transactions(root)
    maintenance = active_maintenance(root)
    if maintenance is None:
        raise ValidationFailure("No open maintenance route is available to complete")
    context = _project_context(root)
    if state_doc is not None:
        supplied_state = state_doc.get("state") if isinstance(state_doc, dict) else None
        if not isinstance(supplied_state, dict):
            raise ValidationFailure("Supplied maintenance completion state envelope is invalid")
        context["state_doc"] = deepcopy(state_doc)
        context["state"] = context["state_doc"]["state"]
    if isinstance(context["state"].get("active_run"), dict):
        raise ValidationFailure("Maintenance finalization requires no active Run")
    wp, _ = _load_current_wp(root, maintenance["work_package_ref"])
    tasks: list[dict[str, Any]] = []
    for task_id in wp.get("mandatory_task_refs") or []:
        task, _ = _load_current_task(root, str(task_id))
        tasks.append(task)
    incomplete = [f"{task['id']}@{task['revision']}:{task.get('status')}" for task in tasks if task.get("status") != "DONE"]
    if incomplete:
        raise ValidationFailure("Maintenance cannot complete before every mandatory Task is DONE", incomplete)

    plan_id = str(maintenance["plan_ref"]).split("@", 1)[0]
    transaction_id = _transaction_id(str(maintenance["decision_ref"]).split("@", 1)[0], "COMPLETE")
    reports = _maintenance_reports(root, maintenance, context["state"])
    request_contract = {
        "maintenance_plan_ref": maintenance["plan_ref"],
        "work_package_ref": f"{wp['id']}@{wp['revision']}",
        "task_refs": [f"{task['id']}@{task['revision']}" for task in tasks],
        "task_report_refs": [report.get("id") for report in reports],
    }
    request_digest = stage_transaction_digest(request_contract)
    replay = committed_stage_transaction_result(
        root,
        transaction_id=transaction_id,
        operation_kind="COMPLETE_MAINTENANCE",
        request_digest=request_digest,
    )
    if replay is not None:
        return replay

    now = utc_now()
    revised_wp = _revision(wp, status="COMPLETED", now=now, completed_at=now)
    wp_rel = f".harness/work-packages/{wp['id']}@{revised_wp['revision']}.yaml"
    wp_index_doc = deepcopy(load_data(root / ".harness/work-packages/INDEX.yaml"))
    wp_index_doc["work_package_index"]["current"][wp["id"]] = wp_rel
    report_id = f"VAL-{str(context['project']['id_token'])}-MAINT-COMPLETE-{_short_digest({'plan': maintenance['plan_ref'], 'tasks': request_contract['task_refs']}, 10)}"
    report_ref = f"{report_id}@1"
    evidence_refs = sorted({str(ref) for report in reports for ref in report.get("evidence_refs") or []})
    task_report_refs = [str(report["id"]) for report in reports]
    run_refs = [str(report["run_ref"]) for report in reports if report.get("run_ref")]
    summary = {
        "id": report_id,
        "revision": 1,
        "kind": "MAINTENANCE_COMPLETION",
        "status": "COMPLETED",
        "maintenance_route": MAINTENANCE_ROUTE,
        "maintenance_plan_ref": maintenance["plan_ref"],
        "start_decision_ref": maintenance["decision_ref"],
        "work_package_ref": f"{wp['id']}@{revised_wp['revision']}",
        "implementation_stage": maintenance["implementation_stage"],
        "highest_accepted_level": maintenance["highest_accepted_level"],
        "target_level": maintenance["target_level"],
        "last_acceptance_ref": maintenance["last_acceptance_ref"],
        "task_refs": request_contract["task_refs"],
        "task_report_refs": task_report_refs,
        "run_refs": run_refs,
        "evidence_refs": evidence_refs,
        "completion_rule": "ALL_MANDATORY_PASS",
        "completed_at": now,
    }
    restored_state_doc, restored_next_doc = _restore_state(context["state_doc"], maintenance, now=now)
    writes: dict[Path, Any] = {
        Path(wp_rel): {"work_package": revised_wp},
        Path(".harness/work-packages/INDEX.yaml"): wp_index_doc,
        Path(f".harness/maintenance/REPORTS/{report_ref}.yaml"): {"maintenance_report": summary},
        Path(".harness/state/CURRENT_STATE.yaml"): restored_state_doc,
        Path(".harness/state/NEXT_TASK.yaml"): restored_next_doc,
        MAINTENANCE_CURRENT_PATH: {"maintenance_current": None},
        MAINTENANCE_INDEX_PATH: _update_maintenance_index(
            root,
            plan_id,
            status="COMPLETED",
            work_package_ref=f"{wp['id']}@{revised_wp['revision']}",
            report_ref=report_ref,
        ),
    }
    stage = context["stage"]
    result = {
        "status": "MAINTENANCE_COMPLETED",
        "route": MAINTENANCE_ROUTE,
        "maintenance_plan_ref": maintenance["plan_ref"],
        "decision_ref": maintenance["decision_ref"],
        "work_package_ref": f"{wp['id']}@{revised_wp['revision']}",
        "report_ref": report_ref,
        "task_refs": request_contract["task_refs"],
        "task_report_refs": task_report_refs,
        "run_refs": run_refs,
        "evidence_refs": evidence_refs,
        "implementation_stage": maintenance["implementation_stage"],
        "target_level": stage["target_level"],
        "highest_accepted_level": stage["highest_accepted_level"],
        "active_stage": stage["active_stage"],
        "next_route": restored_state_doc["state"]["next_route"],
        "kernel_written_paths": sorted(path.as_posix() for path in writes),
    }
    return _transactional_write(
        root,
        writes,
        transaction_id=transaction_id,
        operation_kind="COMPLETE_MAINTENANCE",
        request_digest=request_digest,
        result=result,
    )


def validate_maintenance_artifacts(root: Path) -> dict[str, Any]:
    """Validate stored plans and the single open maintenance route, if present."""
    root = native_resolve(root.expanduser())
    errors: list[str] = []
    plan_dir = root / ".harness/maintenance/PLANS"
    plans: dict[str, dict[str, Any]] = {}
    if _native_io_path(plan_dir).exists():
        for path in sorted(native_glob(plan_dir,'*.yaml')):
            try:
                plan = validate_maintenance_plan_document(load_data(path))
                ref = _canonical_ref(plan)
                if path.name != f"{ref}.yaml":
                    errors.append(f"{path.relative_to(root)}: filename does not match {ref}")
                plans[ref] = plan
            except Exception as exc:
                errors.append(f"{path.relative_to(root)}: {exc}")
    try:
        current = active_maintenance(root)
    except Exception as exc:
        current = None
        errors.append(f"{MAINTENANCE_CURRENT_PATH}: {exc}")
    open_wps = _open_maintenance_wps(root)
    if len(open_wps) > 1:
        errors.append(f"multiple open maintenance Work Packages: {open_wps}")
    if current is None and open_wps:
        errors.append(f"open maintenance Work Package has no maintenance current state: {open_wps}")
    if current is not None:
        plan = plans.get(str(current.get("plan_ref")))
        if plan is None:
            errors.append(f"open maintenance plan is absent: {current.get('plan_ref')}")
        elif plan.get("implementation_stage") != current.get("implementation_stage"):
            errors.append("maintenance current stage differs from stored plan")
        try:
            wp, _ = _load_current_wp(root, str(current["work_package_ref"]))
            if wp.get("maintenance_route") != MAINTENANCE_ROUTE:
                errors.append(f"{wp.get('id')}: missing maintenance_route")
            if wp.get("implementation_stage") != current.get("implementation_stage"):
                errors.append(f"{wp.get('id')}: implementation_stage differs from maintenance current")
            for task_id in wp.get("mandatory_task_refs") or []:
                task, _ = _load_current_task(root, str(task_id))
                if task.get("maintenance_route") != MAINTENANCE_ROUTE:
                    errors.append(f"{task_id}: missing maintenance_route")
                if task.get("implementation_stage") != current.get("implementation_stage"):
                    errors.append(f"{task_id}: implementation_stage differs from maintenance current")
        except Exception as exc:
            errors.append(f"open maintenance artifact resolution failed: {exc}")
    return {
        "status": "PASS" if not errors else "FAIL",
        "plans": len(plans),
        "open_work_packages": open_wps,
        "active_plan_ref": current.get("plan_ref") if current else None,
        "errors": errors,
    }

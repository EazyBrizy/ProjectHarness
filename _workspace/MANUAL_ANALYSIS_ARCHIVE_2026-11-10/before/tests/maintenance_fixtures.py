from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from project_harness.serialization import load_data, write_data
from project_harness.stages import load_stage_state


APPROVED_AT = "2026-08-20T02:00:00Z"
ACTOR = "ACT-MAINTENANCE-APPROVER-001"


def accepted_scope_ref(root: Path) -> str:
    state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
    definition = load_data(root / state["entity_paths"]["project_definition"])["project_definition"]
    return str(definition["scope_ref"])


def maintenance_plan_document(
    root: Path,
    *,
    suffix: str = "001",
    task_count: int = 1,
    product_changing: bool | list[bool] = True,
    level: str | None = None,
    target: str | None = None,
    future_stage_refs: list[str] | None = None,
    task_stage: str | None = None,
) -> dict[str, Any]:
    stage = load_stage_state(root)
    project = load_data(root / ".harness/config/PROJECT.yaml")["project"]
    token = project["id_token"]
    accepted = level or stage["highest_accepted_level"]
    target_level = target or stage["target_level"]
    plan_id = f"RQP-{token}-MAINT-{suffix}"
    wp_id = f"WP-{token}-MAINT-{suffix}"
    flags = [product_changing] * task_count if isinstance(product_changing, bool) else list(product_changing)
    if len(flags) != task_count:
        raise ValueError("product_changing must match task_count")
    tasks: list[dict[str, Any]] = []
    for index in range(1, task_count + 1):
        task_id = f"TSK-{token}-MAINT-{suffix}-{index:03d}"
        dependencies = [] if index == 1 else [f"TSK-{token}-MAINT-{suffix}-{index - 1:03d}"]
        tasks.append(
            {
                "id": task_id,
                "title": f"Maintenance task {index}",
                "type": "DOCUMENT",
                "priority": "NORMAL",
                "purpose": f"Apply bounded accepted-scope maintenance step {index}.",
                "expected_result": f"Maintenance step {index} is documented and verified.",
                "implementation_stage": task_stage or accepted,
                "product_changing": bool(flags[index - 1]),
                "future_stage_work": "FORBIDDEN",
                "depends_on_tasks": dependencies,
                "requirement_refs": [],
                "constraint_refs": [],
                "architecture_refs": [],
                "produces_artifacts": ["README.md"],
                "scope": {
                    "read": ["README.md"],
                    "write": ["README.md"],
                    "forbidden": ["CODEX_START.md", "PROJECT.md", "ARCHITECTURE.md", "TECHNOLOGY.md"],
                },
                "route": {
                    "primary_skill_ref": "SKL-UNIVERSAL-DOCUMENT@1",
                    "supporting_skill_refs": [],
                    "required_capabilities": ["FILESYSTEM_READ", "FILESYSTEM_WRITE", "COMMAND_EXECUTE"],
                },
                "prompt_spec_ref": "PSP-IMPLEMENT@1",
                "verification": {
                    "commands": [
                        {
                            "argv": ["python", "-m", "unittest", "discover", "-s", "tests", "-v"],
                            "cwd": ".",
                            "timeout_seconds": 120,
                        }
                    ],
                    "expected_paths": ["README.md"],
                    "manual_checks": [],
                    "timeout_seconds": 120,
                    "allow_manual": False,
                },
                "documentation": {
                    "source_refs": [],
                    "impact": "UPDATE_EXISTING",
                    "required_updates": ["README.md"],
                },
                "acceptance_criteria": [f"Maintenance step {index} is present in README.md", "Existing tests pass"],
                "rollback": {"strategy": "RESTORE_PRE_RUN_SNAPSHOT"},
            }
        )
    return {
        "maintenance_plan": {
            "schema_version": 1,
            "schema_ref": "SCHEMA-MAINTENANCE-PLAN@1",
            "record_kind": "MAINTENANCE_PLAN",
            "id": plan_id,
            "revision": 1,
            "status": "APPROVED",
            "route": "MAINTAIN_CURRENT_STAGE",
            "highest_accepted_level": accepted,
            "implementation_stage": accepted,
            "target_level": target_level,
            "last_acceptance_ref": stage["last_acceptance_ref"],
            "accepted_scope_ref": accepted_scope_ref(root),
            "objective": "Maintain accepted product behavior without changing implementation maturity.",
            "rationale": "A bounded accepted-scope maintenance change is formally approved.",
            "decision": {
                "id": f"DEC-{token}-MAINT-{suffix}",
                "kind": "MAINTAIN_CURRENT_STAGE",
                "approved": True,
                "actor": ACTOR,
                "approved_at": APPROVED_AT,
            },
            "scope_boundary": {
                "future_stage_work": "FORBIDDEN",
                "future_stage_refs": list(future_stage_refs or []),
            },
            "work_package": {
                "id": wp_id,
                "title": "Governed same-level maintenance",
                "objective": "Complete only the approved bounded maintenance Tasks.",
                "implementation_stage": accepted,
                "tasks": tasks,
            },
            "verification_constraints": {
                "independent_verification_required": True,
                "completion_requires_pass": True,
            },
            "rollback_constraints": {
                "automatic_rollback": False,
                "strategy": "RESTORE_PRE_RUN_SNAPSHOT",
            },
            "cancel_constraints": {
                "before_product_change_only": True,
                "completed_product_change_action": "REQUIRE_COMPLETION_OR_GOVERNED_COMPENSATION",
            },
        }
    }


def maintenance_cancel_document(root: Path, *, suffix: str = "001") -> dict[str, Any]:
    stage = load_stage_state(root)
    current = load_data(root / ".harness/maintenance/CURRENT.yaml")["maintenance_current"]
    project = load_data(root / ".harness/config/PROJECT.yaml")["project"]
    token = project["id_token"]
    return {
        "maintenance_cancel_approval": {
            "schema_version": 1,
            "schema_ref": "SCHEMA-MAINTENANCE-CANCEL-APPROVAL@1",
            "record_kind": "MAINTENANCE_CANCEL_APPROVAL",
            "id": f"DEC-{token}-MAINT-CANCEL-{suffix}",
            "revision": 1,
            "kind": "CANCEL_MAINTENANCE",
            "approved": True,
            "actor": ACTOR,
            "approved_at": APPROVED_AT,
            "maintenance_plan_ref": current["plan_ref"],
            "work_package_ref": current["work_package_ref"],
            "highest_accepted_level": stage["highest_accepted_level"],
            "target_level": stage["target_level"],
            "last_acceptance_ref": stage["last_acceptance_ref"],
            "rationale": "Cancel the open route before any product-changing Task is completed.",
            "cancel_mode": "PRE_PRODUCT_CHANGE_ONLY",
        }
    }


def write_record(base: Path, name: str, value: dict[str, Any]) -> Path:
    path = base / name
    write_data(path, value)
    return path


def with_new_decision(plan: dict[str, Any], decision_suffix: str) -> dict[str, Any]:
    value = deepcopy(plan)
    body = value["maintenance_plan"]
    token = body["id"].split("-MAINT-", 1)[0].removeprefix("RQP-")
    body["decision"]["id"] = f"DEC-{token}-MAINT-{decision_suffix}"
    return value

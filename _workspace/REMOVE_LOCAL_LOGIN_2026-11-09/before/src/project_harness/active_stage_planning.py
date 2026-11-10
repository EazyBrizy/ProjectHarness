from __future__ import annotations

"""PH-F03: exact-bound next active Stage planner. No future-stage Tasks are compiled."""

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .operation_guard import guarded_mutation
from .errors import ValidationFailure
from .hashing import sha256_file
from .maintenance import active_maintenance
from .project_input import _validate_schema_node
from .registry import implementation_level_model
from .resources import distribution_root
from .serialization import load_data, write_data
from .stage_transactions import (
    committed_stage_transaction_result,
    digest_value,
    recover_stage_transactions,
    validate_stage_transaction_journals,
)
from .stages import (
    STAGE_GATE_INDEX_PATH, STAGE_PLAN_INDEX_PATH, STAGE_STATE_PATH,
    _current_stage_gate_context, _last_acceptance_context, _transactional_write,
    _render_committed_stage_transition, canonical_levels, next_level,
    validate_stage_gate, validate_stage_plan, validate_stage_state,
)
from .util import ensure_relative_pattern, utc_now
from .workspace import PROTECTED_ROOT_FILES, snapshot_product

SCHEMA_REF = "SCHEMA-ACTIVE-STAGE-PLAN-REVIEW@1"
ROUTE = "PLAN_ACTIVE_STAGE"
PLAN_RECORDS = Path(".harness/stages/PLANNING/RECORDS")
_PROTECTED = set(PROTECTED_ROOT_FILES) | {".harness", ".git"}


def validate_active_stage_plan_document(value: Any) -> dict[str, Any]:
    path = distribution_root() / "schemas/active_stage_plan_review.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    if schema.get("$id") != SCHEMA_REF:
        raise ValidationFailure("Unexpected active-stage planner schema", str(path))
    errors = _validate_schema_node(value, schema, schema)
    if errors:
        raise ValidationFailure("Active-stage reviewed plan schema validation failed", errors)
    return deepcopy(value["active_stage_plan_review"])


def _canonical_ref(body: dict[str, Any]) -> str:
    return f"{body['id']}@{body['revision']}"


def _sha(path: Path) -> str:
    return f"sha256:{sha256_file(path)}"


def _load_exact(root: Path, ref: str, folder: str, envelope: str) -> tuple[dict[str, Any], Path]:
    # The canonical storage path is computed from the exact ref, never a glob.
    if not isinstance(ref, str) or ref.count("@") != 1 or ".." in ref or "/" in ref or "\\" in ref:
        raise ValidationFailure("Invalid canonical planner context ref", ref)
    path = Path(folder) / f"{ref}.yaml"
    doc = load_data(root / path)
    body = doc.get(envelope) if isinstance(doc, dict) else None
    if not isinstance(body, dict) or _canonical_ref(body) != ref:
        raise ValidationFailure("Planner context artifact ref/envelope mismatch", ref)
    return body, path


def _last_completed_maintenance(root: Path, *, acceptance_ref: str, product_revision: str, accepted_revision: str) -> tuple[str | None, str | None]:
    """Require a governed completed maintenance record when product differs from acceptance."""
    if product_revision == accepted_revision:
        return None, None
    reports = sorted((root / ".harness/maintenance/REPORTS").glob("*.yaml"))
    matching: list[tuple[str, str]] = []
    for path in reports:
        doc = load_data(path)
        body = doc.get("maintenance_report") if isinstance(doc, dict) else None
        if isinstance(body, dict) and body.get("status") == "COMPLETED" and body.get("last_acceptance_ref") == acceptance_ref:
            matching.append((_canonical_ref(body), _sha(path)))
    if not matching:
        raise ValidationFailure(
            "Product changed after accepted Stage baseline without a completed governed maintenance report",
            {"accepted": accepted_revision, "observed": product_revision},
        )
    # Product baseline still binds to this exact draft; no maintenance report is accepted as
    # a substitute for the current product digest or an approval of an enlarged product scope.
    return matching[-1]


def _context(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not (root / STAGE_STATE_PATH).is_file():
        raise ValidationFailure("Active-stage planning requires a prepared Project Instance")
    current = _current_stage_gate_context(root)
    state = current["state"]
    project_doc = load_data(root / ".harness/config/PROJECT.yaml")
    project = project_doc.get("project") or {}
    project_state_doc = load_data(root / ".harness/state/CURRENT_STATE.yaml")
    project_state = project_state_doc.get("state") or {}
    if state["highest_accepted_level"] not in canonical_levels() or next_level(state["highest_accepted_level"]) != state["active_stage"]:
        raise ValidationFailure("Active Stage is not the immediate successor of highest accepted level", state)
    if state["active_stage"] not in state["stage_path"] or state["stage_path"][-1] != state["target_level"]:
        raise ValidationFailure("Active Stage/target is inconsistent with sequential path")
    if project.get("target_implementation_level") != state["target_level"] or project_state.get("target_implementation_level") != state["target_level"]:
        raise ValidationFailure("Canonical target and project projections differ")
    if project_state.get("active_stage") != state["active_stage"]:
        raise ValidationFailure("CURRENT_STATE active_stage differs from Stage State")
    if project_state.get("next_route") != ROUTE or project_state.get("project_status") != "ACTIVE":
        raise ValidationFailure("Active Stage is not waiting for a planning route", project_state.get("next_route"))
    if project_state.get("current_task_ref") is not None or project_state.get("active_run") is not None:
        raise ValidationFailure("Active Stage planning is forbidden during an active Task/Run")
    if project_state.get("blocked_task_refs") or project_state.get("open_blocker_refs"):
        raise ValidationFailure("Active Stage planning requires resolved Task/Gate blockers")
    if active_maintenance(root) is not None:
        raise ValidationFailure("Active Stage planning is forbidden while maintenance is open")
    if current["plan"].get("status") != "ACTIVE" or current["gate"].get("status") != "ACTIVE":
        raise ValidationFailure("Active Stage Plan and Gate must both be ACTIVE and unclosed")
    if not current["plan"].get("review_required") or current["plan"].get("detailed_work_package_refs"):
        raise ValidationFailure("Current Stage Plan has already been detailed")
    if current["gate"].get("required_work_package_refs") or current["gate"].get("critical_blocker_refs"):
        raise ValidationFailure("Current Stage Gate has unfinished acceptance or blocked work")
    task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
    wp_index = load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]
    for task_id, rel in (task_index.get("current") or {}).items():
        task = load_data(root / str(rel)).get("task") or {}
        if task.get("implementation_stage") == state["active_stage"] and task.get("status") not in {"DONE", "SUPERSEDED", "STALE", "CANCELLED"}:
            raise ValidationFailure("An active Stage Task already exists", task_id)
    for wp_id, rel in (wp_index.get("current") or {}).items():
        wp = load_data(root / str(rel)).get("work_package") or {}
        if wp.get("implementation_stage") == state["active_stage"] and wp.get("status") in {"PLANNED", "READY", "IN_PROGRESS", "BLOCKED"}:
            raise ValidationFailure("An active Stage Work Package already exists", wp_id)
    last = _last_acceptance_context(root, state)
    if not last["ref"]:
        raise ValidationFailure("Next Stage requires an exact last Stage Acceptance Report")
    accepted_report, acceptance_path = _load_exact(root, last["ref"], ".harness/stages/ACCEPTANCE", "stage_acceptance")
    if accepted_report["level"] != state["highest_accepted_level"] or accepted_report.get("status") != "PASS":
        raise ValidationFailure("Last acceptance report is not the accepted predecessor Stage", last["ref"])
    product_revision = current["baseline_revision"]
    maintenance_ref, maintenance_digest = _last_completed_maintenance(
        root, acceptance_ref=last["ref"], product_revision=product_revision, accepted_revision=accepted_report["baseline_revision"],
    )
    project_definition = _load_exact(root, project["project_definition_ref"], ".harness/canonical/DEFINITION", "project_definition")[0]
    scope_ref = project_definition["scope_ref"]
    scope, scope_path = _load_exact(root, scope_ref, ".harness/canonical/DEFINITION", "scope")
    accepted_input_path = root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml"
    accepted_input = load_data(accepted_input_path)
    if accepted_input["project"]["scope"]["in"] != scope["in"] or accepted_input["project"]["scope"]["out"] != scope["out"]:
        raise ValidationFailure("Accepted scope differs between project definition and immutable input")
    model = implementation_level_model()
    level = state["active_stage"]
    criteria = list(model["profiles"][level]["criteria_refs"])
    expected_results = [item["criterion_ref"] for item in current["gate"].get("criteria_results") or []]
    overrides = [item["key"] for item in current["plan"].get("hard_constraint_overrides") or []]
    if expected_results != criteria + overrides:
        raise ValidationFailure("Active Gate does not match canonical criteria/constraint bindings", expected_results)
    requirement_refs = list(current["plan"].get("scope_refs") or [])
    if not requirement_refs:
        raise ValidationFailure("Accepted requirements are missing from Stage Plan")
    for ref in requirement_refs:
        _load_exact(root, ref, ".harness/canonical/REQUIREMENTS", "requirement")
    constraint_refs = [f"{body['id']}@{body['revision']}" for path in sorted((root / ".harness/canonical/CONSTRAINTS").glob("CST-*@*.yaml")) if (body := load_data(path).get("constraint"))]
    for ref in constraint_refs:
        _load_exact(root, ref, ".harness/canonical/CONSTRAINTS", "constraint")
    token = project.get("id_token")
    if not isinstance(token, str) or not token:
        raise ValidationFailure("Project token missing")
    return {
        **current, "root": root, "project": project, "project_state_doc": project_state_doc,
        "task_index": task_index, "wp_index": wp_index, "token": token,
        "scope": scope, "scope_ref": scope_ref, "scope_path": scope_path,
        "last_report": accepted_report, "last_report_path": acceptance_path,
        "accepted_input_path": accepted_input_path, "accepted_input": accepted_input,
        "maintenance_report_ref": maintenance_ref, "maintenance_report_digest": maintenance_digest,
        "criteria_refs": criteria, "constraint_refs": constraint_refs, "requirement_refs": requirement_refs,
        "criteria_model": model["criteria"], "overrides": overrides,
    }


def _scope_for_stage(ctx: dict[str, Any]) -> dict[str, list[str]]:
    # Reuse paths that the accepted initial planning contract already allowed.
    # New write locations require an explicitly reviewed plan; no future features are inferred.
    original_wps = ctx["accepted_input"]["planning"]["work_packages"]
    scopes = [task.get("scope") or {} for wp in original_wps for task in wp.get("tasks") or []]
    values = {name: sorted({str(p) for item in scopes for p in (item.get(name) or [])}) for name in ("read", "write", "forbidden")}
    values["read"] = sorted(set(values["read"]) | {"PROJECT.md", "ARCHITECTURE.md", "TECHNOLOGY.md"})
    values["forbidden"] = sorted((set(values["forbidden"]) | _PROTECTED) - {".harness", ".git"})
    values["write"] = [value for value in values["write"] if value not in _PROTECTED and not value.startswith(".harness")]
    if not values["write"]:
        raise ValidationFailure("Accepted project plan has no safe writable product paths")
    return values


def _new_plan_record_id(root: Path, token: str, level: str, revision: int) -> str:
    """Retired transaction IDs are never reused after crash recovery/rollback.

    A fresh operator draft gets a distinct ID without changing accepted history
    or the canonical Stage revision; committed operations are replayed separately.
    """
    base = f"RQP-{token}-{level}-{revision:04d}"
    candidate = base
    for attempt in range(1, 101):
        tx = f"STX-PLAN-{candidate.removeprefix('RQP-')}"
        journal_path = root / ".harness/stages/TRANSACTIONS" / tx / "TRANSACTION.yaml"
        if not journal_path.exists():
            return candidate
        journal = load_data(journal_path).get("stage_transaction") or {}
        if journal.get("status") != "ROLLED_BACK":
            raise ValidationFailure("Planner cannot issue a conflicting transaction ID", {"id": tx, "status": journal.get("status")})
        candidate = f"{base}-RETRY-{attempt + 1:02d}"
    raise ValidationFailure("Active Stage exceeded bounded transaction retry attempts")


def _draft(root: Path) -> dict[str, Any]:
    ctx = _context(root)
    state = ctx["state"]
    level, token = state["active_stage"], ctx["token"]
    binding = {
        "stage_state_revision": state["revision"],
        "stage_state_digest": _sha(root / STAGE_STATE_PATH),
        "highest_accepted_level": state["highest_accepted_level"],
        "active_stage": level,
        "target_level": state["target_level"],
        "stage_plan_ref": ctx["plan_ref"], "stage_plan_digest": ctx["plan_digest"],
        "gate_ref": ctx["gate_ref"], "gate_digest": ctx["gate_digest"],
        "last_acceptance_ref": ctx["last_report"]["id"] + "@" + str(ctx["last_report"]["revision"]),
        "last_acceptance_digest": _sha(root / ctx["last_report_path"]),
        "accepted_baseline_revision": ctx["last_report"]["baseline_revision"],
        "product_baseline_revision": ctx["baseline_revision"],
        "accepted_scope_ref": ctx["scope_ref"], "accepted_scope_digest": _sha(root / ctx["scope_path"]),
        "accepted_input_digest": _sha(ctx["accepted_input_path"]),
        "maintenance_report_ref": ctx["maintenance_report_ref"],
        "maintenance_report_digest": ctx["maintenance_report_digest"],
    }
    basis = {
        "required_outcomes": list(ctx["plan"]["required_outcomes"]),
        "criteria_refs": ctx["criteria_refs"] + ctx["overrides"],
        "profile_control_refs": list(ctx["gate"].get("profile_control_refs") or []),
        "hard_constraint_refs": list(ctx["overrides"]),
        "requirement_refs": ctx["requirement_refs"],
        "constraint_refs": ctx["constraint_refs"],
        "accepted_scope_in": [str(x) for x in ctx["scope"]["in"]],
        "accepted_scope_out": [str(x) for x in ctx["scope"]["out"]],
        "next_stage_gaps": [str(x) for x in ctx["last_report"].get("next_stage_gaps") or []],
        "known_limitations": [str(x) for x in ctx["last_report"].get("known_limitations") or []],
        "permitted_use": deepcopy(ctx["last_report"].get("permitted_use") or {}),
        "product_files": sorted(snapshot_product(root)),
    }
    scope = _scope_for_stage(ctx)
    revision = state["revision"]
    wp_id = f"WP-{token}-{level}-{revision:04d}"
    tasks = []
    for ordinal, criterion in enumerate(basis["criteria_refs"], 1):
        record = ctx["criteria_model"].get(criterion) or next((i for i in ctx["plan"].get("hard_constraint_overrides") or [] if i.get("key") == criterion), {})
        desc = str(record.get("description") or record.get("statement") or criterion)
        dimension = record.get("dimension")
        typ = "DOCUMENT" if dimension in {"DOCUMENTATION_SUPPORT", "RELEASE_EVIDENCE"} else ("TEST" if dimension == "TESTING_VERIFICATION" else "IMPLEMENT")
        skill = "SKL-UNIVERSAL-DOCUMENT@1" if typ == "DOCUMENT" else "SKL-UNIVERSAL-IMPLEMENT@3"
        caps = ["FILESYSTEM_READ", "FILESYSTEM_WRITE"] if typ == "DOCUMENT" else ["FILESYSTEM_READ", "FILESYSTEM_WRITE", "COMMAND_EXECUTE"]
        task_id = f"TSK-{token}-{level}-{revision:04d}-{ordinal:03d}"
        tasks.append({
            "id": task_id, "criterion_ref": criterion, "title": f"{level}: {criterion}",
            "type": typ, "priority": "NORMAL", "purpose": desc,
            "expected_result": f"Address {criterion} within the accepted project scope; preserve evidence needed for the Stage Gate.",
            "implementation_stage": level, "future_stage_work": "FORBIDDEN",
            "depends_on_tasks": [tasks[-1]["id"]] if tasks else [],
            "requirement_refs": ctx["requirement_refs"], "constraint_refs": ctx["constraint_refs"],
            "scope": deepcopy(scope),
            "route": {"primary_skill_ref": skill, "supporting_skill_refs": [], "required_capabilities": caps},
            "verification": {
                "commands": [], "expected_paths": [],
                "manual_checks": [f"Independently check {criterion}: {desc}; do not treat a generic PASS report as Gate evidence."],
                "timeout_seconds": 300, "allow_manual": True,
            },
            "documentation": {"source_refs": [], "impact": "REVIEW_REQUIRED", "required_updates": []},
            "acceptance_criteria": [desc, "Preserve accepted project scope and demonstrate criterion-specific checks or document inapplicability."],
            "rollback": {"strategy": "RESTORE_PRE_RUN_SNAPSHOT"},
        })
    if not tasks:
        raise ValidationFailure("Canonical active Stage has no planning criteria")
    wps = [{"id": wp_id, "title": f"{level} accepted-scope delta", "objective": "Close current Stage criteria only; accepted gaps are review inputs, not authorization to expand scope.", "implementation_stage": level, "tasks": tasks}]
    candidate_digest = digest_value({"work_packages": wps, "planning_basis": basis})
    draft = {
        "schema_version": 1, "schema_ref": SCHEMA_REF, "record_kind": "ACTIVE_STAGE_PLAN_REVIEW",
        "id": _new_plan_record_id(root, token, level, revision), "revision": 1, "route": ROUTE,
        "binding": binding, "planning_basis": basis,
        "review": {"material_change": False, "scope_confirmed": True, "decision": None},
        "work_packages": wps, "candidate_work_digest": candidate_digest,
        "future_stage_work": "FORBIDDEN",
    }
    validate_active_stage_plan_document({"active_stage_plan_review": draft})
    return draft


def _safe_output(root: Path, output: Path) -> Path:
    path = output.expanduser().resolve()
    if path.is_dir():
        raise ValidationFailure("Operator plan output must be a file")
    try:
        inside = path.relative_to(root)
    except ValueError:
        return path
    if not inside.as_posix().startswith(".harness/operator/"):
        raise ValidationFailure("Read-only planner draft must be stored outside the product tree or in .harness/operator/", inside.as_posix())
    return path


@guarded_mutation
def prepare_active_stage_plan(root: Path, output_path: Path, *, force: bool = False) -> dict[str, Any]:
    """Read-only Stage compilation: only the separately requested draft is written."""
    root = root.expanduser().resolve()
    pending = [p.as_posix() for p in (root / ".harness/stages/TRANSACTIONS").glob("*/TRANSACTION.yaml") if (load_data(p).get("stage_transaction") or {}).get("status") not in {"COMMITTED", "ROLLED_BACK"}]
    if pending:
        raise ValidationFailure("Pending Stage transaction must be recovered before read-only planning", pending)
    draft = _draft(root)
    destination = _safe_output(root, output_path)
    if destination.exists() and not force:
        if load_data(destination) != {"active_stage_plan_review": draft}:
            raise ValidationFailure("Planner output file exists; choose another --output or use --force", str(destination))
    else:
        write_data(destination, {"active_stage_plan_review": draft})
    return {
        "status": "DRAFT_PREPARED", "output_path": str(destination), "active_stage": draft["binding"]["active_stage"],
        "target_level": draft["binding"]["target_level"], "stage_plan_ref": draft["binding"]["stage_plan_ref"],
        "gate_ref": draft["binding"]["gate_ref"], "last_acceptance_ref": draft["binding"]["last_acceptance_ref"],
        "candidate_task_count": sum(len(wp["tasks"]) for wp in draft["work_packages"]),
        "next_command": "project-harness plan-active-stage --project <root> --plan <reviewed-record>",
        "control_plane_mutated": False,
    }


def _reviewed_work(root: Path, reviewed: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any] | None:
    if reviewed["id"] != draft["id"] or reviewed["binding"] != draft["binding"] or reviewed["planning_basis"] != draft["planning_basis"] or reviewed["candidate_work_digest"] != draft["candidate_work_digest"]:
        raise ValidationFailure("Reviewed plan is stale, not exact-bound, or its immutable planning basis was changed")
    if reviewed["review"]["material_change"] is not False or reviewed["review"]["scope_confirmed"] is not True:
        raise ValidationFailure("Material scope divergence requires a separate governed scope-change decision, not active-stage planning")
    if reviewed["future_stage_work"] != "FORBIDDEN":
        raise ValidationFailure("Next/future-stage work is prohibited")
    decision = reviewed["review"]["decision"]
    modified = digest_value({"work_packages": reviewed["work_packages"], "planning_basis": reviewed["planning_basis"]}) != draft["candidate_work_digest"]
    if modified and not decision:
        raise ValidationFailure("Edited Stage work plan requires explicit formal review/approval, even without a scope change")
    if decision:
        if decision["id"] != f"DEC-{draft['id'].removeprefix('RQP-')}-REVIEW":
            raise ValidationFailure("Stage planning review Decision id is not deterministic/project-local")
        if not decision["actor"].startswith("ACT-"):
            raise ValidationFailure("Stage planning review Decision requires canonical actor ref")
    ctx = _context(root)
    expected_refs = draft["planning_basis"]["criteria_refs"]
    actual_refs = [task["criterion_ref"] for wp in reviewed["work_packages"] for task in wp["tasks"]]
    if sorted(actual_refs) != sorted(expected_refs) or len(actual_refs) != len(set(actual_refs)):
        raise ValidationFailure("Reviewed Tasks must cover current Stage criteria exactly once", {"expected": expected_refs, "actual": actual_refs})
    task_ids = [task["id"] for wp in reviewed["work_packages"] for task in wp["tasks"]]
    wp_ids = [wp["id"] for wp in reviewed["work_packages"]]
    if len(set(task_ids)) != len(task_ids) or len(set(wp_ids)) != len(wp_ids):
        raise ValidationFailure("Reviewed Stage Task/WP ids must be unique")
    for wp in reviewed["work_packages"]:
        if not str(wp["id"]).startswith(f"WP-{ctx['token']}-{ctx['active_stage']}-") or wp["implementation_stage"] != ctx["active_stage"]:
            raise ValidationFailure("Reviewed WP is not project-local/current-stage", wp["id"])
        for task in wp["tasks"]:
            if not str(task["id"]).startswith(f"TSK-{ctx['token']}-{ctx['active_stage']}-") or task["implementation_stage"] != ctx["active_stage"]:
                raise ValidationFailure("Reviewed Task is not project-local/current-stage", task["id"])
            if task["criterion_ref"] not in expected_refs or task["future_stage_work"] != "FORBIDDEN":
                raise ValidationFailure("Task references future/out-of-contract Stage work", task["id"])
            if any(ref not in ctx["requirement_refs"] for ref in task["requirement_refs"]):
                raise ValidationFailure("Task references requirements outside accepted scope", task["id"])
            if any(ref not in ctx["constraint_refs"] for ref in task["constraint_refs"]):
                raise ValidationFailure("Task references constraints outside accepted scope", task["id"])
            for key, paths in task["scope"].items():
                for path in paths:
                    ensure_relative_pattern(str(path), field=f"{task['id']}.scope.{key}")
                    if key == "write" and (str(path).startswith((".harness", ".git")) or path in _PROTECTED):
                        raise ValidationFailure("Task write scope touches protected project control-plane", {"task": task["id"], "path": path})
            if any(dep not in task_ids or dep == task["id"] for dep in task["depends_on_tasks"]):
                raise ValidationFailure("Task dependency references missing/self Task", task["id"])
    # Validate DAG using the existing planner algorithm, keeping the reviewed ordering.
    from .planner import topological_order
    ordered = [dict(item, original_index=i) for i, item in enumerate((task for wp in reviewed["work_packages"] for task in wp["tasks"]), 1)]
    ordered_ids = topological_order(ordered)
    if ordered_ids[0] != task_ids[0]:
        raise ValidationFailure("First reviewed Task must be the first executable DAG node")
    # Changing field-level plan semantics cannot bypass the accepted scope: only
    # an authorized operator can assert that edited work stays within it.
    return decision


def _writes(root: Path, reviewed: dict[str, Any], decision: dict[str, Any] | None) -> tuple[dict[Path, Any], dict[str, Any]]:
    ctx = _context(root)
    now, token, level = utc_now(), ctx["token"], ctx["active_stage"]
    sequence = max((int((load_data(root / path).get("task") or {}).get("sequence") or 0) for path in (ctx["task_index"].get("current") or {}).values()), default=0)
    base_sequence = ((sequence // 10) + 1) * 10
    plan_ref = f"{reviewed['id']}@1"
    writes: dict[Path, Any] = {PLAN_RECORDS / f"{plan_ref}.yaml": {"active_stage_plan_review": deepcopy(reviewed)}}
    if decision:
        writes[Path(f".harness/canonical/DECISIONS/{decision['id']}@1.yaml")] = {
            "decision": {"id": decision["id"], "revision": 1, "kind": "ACTIVE_STAGE_PLAN_REVIEW", "subject_ref": plan_ref,
                         "approved": True, "actor": decision["actor"], "approved_at": decision["approved_at"],
                         "notes": decision["rationale"], "status": "ACCEPTED"},
        }
    task_index = deepcopy(ctx["task_index"])
    wp_index = deepcopy(ctx["wp_index"])
    task_ids = [t["id"] for wp in reviewed["work_packages"] for t in wp["tasks"]]
    wp_ids = [wp["id"] for wp in reviewed["work_packages"]]
    all_new_paths: set[Path] = set(writes)
    for entity_id in task_ids:
        if entity_id in (task_index.get("current") or {}):
            raise ValidationFailure("Planning collides with historical Task id", entity_id)
    for entity_id in wp_ids:
        if entity_id in (wp_index.get("current") or {}):
            raise ValidationFailure("Planning collides with historical WP id", entity_id)
    dag_id = f"DAG-{token}-{level}-{ctx['state']['revision']:04d}"
    dag = {"id": dag_id, "revision": 1, "nodes": task_ids, "edges": [
        {"from": dep, "to": task["id"]} for wp in reviewed["work_packages"] for task in wp["tasks"] for dep in task["depends_on_tasks"]
    ], "scheduler_policy": "SINGLE_ACTIVE_TASK", "implementation_stage": level, "status": "ACTIVE"}
    writes[Path(f".harness/dags/{dag_id}@1.yaml")] = {"dependency_graph": dag}
    ordinal = 0
    for wp in reviewed["work_packages"]:
        for task_in in wp["tasks"]:
            ordinal += 1
            task_id = task_in["id"]
            art = f"{token}-{level}-{ctx['state']['revision']:04d}-{ordinal:03d}"
            verification_id, prompt_id, context_id = f"VFP-{art}", f"PPL-{art}", f"CTX-{art}"
            status = "READY" if ordinal == 1 else "PLANNED"
            task = {
                "id": task_id, "revision": 1, "work_package_ref": wp["id"], "implementation_stage": level,
                "title": task_in["title"], "type": task_in["type"], "track": "PRIMARY",
                "priority": task_in["priority"], "sequence": base_sequence + (ordinal - 1) * 10,
                "purpose": task_in["purpose"], "expected_result": task_in["expected_result"],
                "requirement_refs": task_in["requirement_refs"], "constraint_refs": task_in["constraint_refs"],
                "architecture_refs": [ctx["project"]["architecture_baseline_ref"]],
                "documentation": task_in["documentation"], "depends_on_tasks": task_in["depends_on_tasks"],
                "requires_artifacts": [ctx["state"]["last_acceptance_ref"]], "produces_artifacts": [],
                "scope": task_in["scope"], "route": task_in["route"], "prompt_spec_ref": "PSP-IMPLEMENT@1",
                "prompt_plan_ref": f"{prompt_id}@1", "context_policy_ref": "CTP-TASK-STANDARD@1",
                "context_plan_ref": f"{context_id}@1", "verification_profile_ref": f"{verification_id}@1",
                "verification": task_in["verification"], "acceptance_criteria": task_in["acceptance_criteria"],
                "rollback": task_in["rollback"], "stage_criterion_ref": task_in["criterion_ref"],
                "future_stage_work": "FORBIDDEN", "status": status, "created_at": now,
            }
            rel = f".harness/tasks/{task_id}@1.yaml"
            writes[Path(rel)] = {"task": task}
            task_index.setdefault("order", []).append(task_id)
            task_index.setdefault("current", {})[task_id] = rel
            task_index.setdefault("aliases", {})[task_id] = task_id
            writes[Path(f".harness/verification/PROFILES/{verification_id}@1.yaml")] = {"verification_profile": {
                "id": verification_id, "revision": 1, "task_ref": f"{task_id}@1", "implementation_stage": level,
                **task_in["verification"], "status": "ACTIVE",
            }}
            writes[Path(f".harness/prompts/PLANS/{prompt_id}@1.yaml")] = {"prompt_plan": {
                "id": prompt_id, "revision": 1, "task_ref": f"{task_id}@1", "implementation_stage": level,
                "prompt_spec_ref": "PSP-IMPLEMENT@1", "module_refs": ["PMD-CORE-ROLE@1", "PMD-TASK-CONTRACT@1", "PMD-RESULT-SCHEMA@1"],
                "resolved_inputs": {"task_hash": digest_value(task), "skill_ref": task_in["route"]["primary_skill_ref"], "context_plan_ref": f"{context_id}@1"},
                "output_schema_ref": "SCHEMA-AGENT-TASK-RESULT@1", "status": "RESOLVED",
            }}
            writes[Path(f".harness/context/PLANS/{context_id}@1.yaml")] = {"context_plan": {
                "id": context_id, "revision": 1, "task_ref": f"{task_id}@1", "implementation_stage": level,
                "include": {"project_definition": True, "architecture_baseline": True, "technology_baseline": True,
                            "task_dependencies": task_in["depends_on_tasks"], "read_paths": task_in["scope"]["read"]},
                "exclude": ["secrets", "unrelated tasks", "future-stage work", "provider accounting"], "status": "READY",
            }}
        wp_rel = f".harness/work-packages/{wp['id']}@1.yaml"
        wp_status = "READY" if task_ids[0] in [t["id"] for t in wp["tasks"]] else "PLANNED"
        writes[Path(wp_rel)] = {"work_package": {
            "id": wp["id"], "revision": 1, "request_refs": [plan_ref], "title": wp["title"], "objective": wp["objective"],
            "implementation_stage": level, "requirement_refs": ctx["requirement_refs"], "architecture_refs": [ctx["project"]["architecture_baseline_ref"]],
            "documentation_refs": [], "mandatory_task_refs": [t["id"] for t in wp["tasks"]],
            "dependency_graph_ref": f"{dag_id}@1", "aggregation_rule": "ALL_MANDATORY_PASS", "status": wp_status,
        }}
        wp_index.setdefault("order", []).append(wp["id"])
        wp_index.setdefault("current", {})[wp["id"]] = wp_rel
    plan = deepcopy(ctx["plan"])
    plan["revision"] += 1
    plan["previous_revision_ref"] = ctx["plan_ref"]
    plan["status"] = "ACTIVE"
    plan["review_required"] = False
    plan["baseline_ref"] = ctx["state"]["last_acceptance_ref"]
    plan["accepted_baseline_revision"] = ctx["last_report"]["baseline_revision"]
    plan["planning_product_baseline_revision"] = ctx["baseline_revision"]
    plan["planning_record_ref"] = plan_ref
    plan["work_package_outlines"] = [{"title": wp["title"], "outcome": wp["objective"]} for wp in reviewed["work_packages"]]
    plan["detailed_work_package_refs"] = [f"{wp_id}@1" for wp_id in wp_ids]
    plan["updated_at"] = now
    gate = deepcopy(ctx["gate"])
    gate["revision"] += 1
    gate["previous_revision_ref"] = ctx["gate_ref"]
    gate["stage_plan_ref"] = _canonical_ref(plan)
    gate["status"] = "ACTIVE"
    gate["required_work_package_refs"] = [f"{wp_id}@1" for wp_id in wp_ids]
    gate["base_revision"] = ctx["baseline_revision"]
    gate["updated_at"] = now
    plan["gate_ref"] = _canonical_ref(gate)
    validate_stage_plan({"stage_plan": plan})
    validate_stage_gate({"stage_gate": gate})
    plan_rel = Path(f".harness/stages/PLANS/{_canonical_ref(plan)}.yaml")
    gate_rel = Path(f".harness/stages/GATES/{_canonical_ref(gate)}.yaml")
    writes[plan_rel] = {"stage_plan": plan}
    writes[gate_rel] = {"stage_gate": gate}
    plan_index_doc = deepcopy(load_data(root / STAGE_PLAN_INDEX_PATH))
    gate_index_doc = deepcopy(load_data(root / STAGE_GATE_INDEX_PATH))
    plan_index_doc["stage_plan_index"]["current"][plan["id"]] = plan_rel.as_posix()
    gate_index_doc["stage_gate_index"]["current"][gate["id"]] = gate_rel.as_posix()
    writes[STAGE_PLAN_INDEX_PATH] = plan_index_doc
    writes[STAGE_GATE_INDEX_PATH] = gate_index_doc
    stage_doc = deepcopy(load_data(root / STAGE_STATE_PATH))
    stage_doc["implementation"]["revision"] += 1
    stage_doc["implementation"]["updated_at"] = now
    stage_doc["implementation"]["active_stage_plan_ref"] = _canonical_ref(plan)
    validate_stage_state(stage_doc)
    writes[STAGE_STATE_PATH] = stage_doc
    writes[Path(f".harness/stages/STATE_HISTORY/STAGE_STATE@{stage_doc['implementation']['revision']}.yaml")] = stage_doc
    project_state_doc = deepcopy(ctx["project_state_doc"])
    st = project_state_doc["state"]
    st.setdefault("task_order", []).extend(task_ids)
    st["active_stage"] = level
    st["target_implementation_level"] = ctx["state"]["target_level"]
    st["current_task_ref"] = task_ids[0]
    st["active_run"] = None
    st["project_status"] = "ACTIVE"
    st["handoff_status"] = "STAGE_PLANNED"
    st["next_route"] = "COMPILE_FIRST_READY_TASK"
    st["updated_at"] = now
    writes[Path(".harness/state/CURRENT_STATE.yaml")] = project_state_doc
    writes[Path(".harness/state/NEXT_TASK.yaml")] = {"next_task": {
        "status": "READY", "task_ref": f"{task_ids[0]}@1", "run_ref": None,
        "active_stage": level, "target_implementation_level": ctx["state"]["target_level"],
        "next_route": "COMPILE_FIRST_READY_TASK",
    }}
    writes[Path(".harness/tasks/INDEX.yaml")] = {"task_index": task_index}
    writes[Path(".harness/work-packages/INDEX.yaml")] = {"work_package_index": wp_index}
    for path in writes:
        if path in all_new_paths or path.as_posix().startswith((".harness/tasks/TSK-", ".harness/work-packages/WP-", ".harness/prompts/PLANS/PPL-", ".harness/verification/PROFILES/VFP-", ".harness/context/PLANS/CTX-", ".harness/dags/DAG-", ".harness/stages/PLANS/STG-", ".harness/stages/GATES/GATE-", ".harness/stages/STATE_HISTORY/STAGE_STATE@")):
            # Revisioned paths are append-only, including the operator-approved record.
            if (root / path).exists():
                raise ValidationFailure("Planning would overwrite immutable artifact", path.as_posix())
    result = {
        "status": "STAGE_PLANNED", "active_stage": level, "target_level": ctx["state"]["target_level"],
        "highest_accepted_level": ctx["state"]["highest_accepted_level"],
        "stage_plan_ref": _canonical_ref(plan), "gate_ref": _canonical_ref(gate),
        "planning_record_ref": plan_ref, "first_task_ref": f"{task_ids[0]}@1",
        "work_package_refs": [f"{wp_id}@1" for wp_id in wp_ids], "task_count": len(task_ids),
        "continuation_command": "project-harness next --project <root>",
    }
    return writes, result


def _first_jit_if_needed(root: Path, result: dict[str, Any]) -> dict[str, Any]:
    state = load_data(root / ".harness/state/CURRENT_STATE.yaml").get("state") or {}
    output = deepcopy(result)
    output["next_route"] = state.get("next_route")
    first = str(result["first_task_ref"]).split("@", 1)[0]
    if state.get("current_task_ref") == first and not state.get("completed_task_refs", [])[-1:] == [first]:
        from .prompting import reserve_run
        output["first_jit"] = reserve_run(root, first)
        output["next_route"] = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"].get("next_route")
    return output


@guarded_mutation
def plan_active_stage(root: Path, plan_path: Path) -> dict[str, Any]:
    """Apply one reviewed current-stage work plan transaction; retry is idempotent."""
    root = root.expanduser().resolve()
    recover_stage_transactions(root)
    reviewed_document = load_data(plan_path.expanduser().resolve())
    reviewed = validate_active_stage_plan_document(reviewed_document)
    transaction_id = f"STX-PLAN-{reviewed['id'].removeprefix('RQP-')}"
    request_digest = digest_value(reviewed_document)
    replay = committed_stage_transaction_result(
        root, transaction_id=transaction_id, operation_kind="PLAN_ACTIVE_STAGE", request_digest=request_digest,
    )
    if replay is not None:
        return _first_jit_if_needed(root, replay)
    draft = _draft(root)  # Reject stale stage state, Gate, scope, acceptance, product tree before mutation.
    decision = _reviewed_work(root, reviewed, draft)
    writes, result = _writes(root, reviewed, decision)
    committed = _transactional_write(
        root, writes, transaction_id=transaction_id, operation_kind="PLAN_ACTIVE_STAGE",
        request_digest=request_digest, result=result,
    )
    rendered = _render_committed_stage_transition(root, committed, regeneration_route="repeat the identical plan-active-stage command")
    try:
        return _first_jit_if_needed(root, rendered)
    except Exception as exc:
        # Canonical planning committed; Run/JIT reservation may be retried without
        # pretending the previous transaction rolled back.
        rendered["jit_status"] = "FAILED_RECOVERABLE"
        rendered["jit_error"] = str(exc)
        rendered["continuation_command"] = "project-harness next --project <root>"
        return rendered

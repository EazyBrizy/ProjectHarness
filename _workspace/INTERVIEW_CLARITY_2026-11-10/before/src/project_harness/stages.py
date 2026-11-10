from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import fnmatch
import hashlib
import os
import re
from typing import Any, Iterable

from .operation_guard import guarded_mutation
from .errors import SafetyViolation, ValidationFailure, WaitingDecision, WaitingInput
from .evidence import (
    EVIDENCE_STATUSES,
    allowed_evidence_kinds,
    gate_subject_requirements,
    normalize_evidence_bindings,
    resolve_evidence_artifact,
    normalized_evidence_body,
    validate_gate_evidence_closure,
    validate_normalized_evidence_document,
    validate_semantic_gate_proof,
    write_normalized_evidence,
)
from .hashing import sha256_file, tree_entries, tree_hash
from .platform_fs import _native_io_path, native_resolve, native_glob, native_iterdir
from .registry import implementation_level_model, load_registries
from .serialization import canonical_json_bytes, load_data, write_data
from .stage_approvals import is_strict_stage_approval, validate_stage_approval_document
from .stage_transactions import (
    apply_stage_transaction,
    committed_stage_transaction_result,
    digest_value as stage_transaction_digest,
    recover_stage_transactions,
)
from .util import deep_get, id_token, nonempty, utc_now
from .workspace import check_control_plane, record_phase_boundary, snapshot_product

STAGE_STATE_PATH = Path(".harness/stages/STAGE_STATE.yaml")
STAGE_PLAN_INDEX_PATH = Path(".harness/stages/PLANS/INDEX.yaml")
STAGE_GATE_INDEX_PATH = Path(".harness/stages/GATES/INDEX.yaml")
STAGE_TRANSITIONS = {
    "PLANNED": {"ACTIVE", "SUPERSEDED"},
    "ACTIVE": {"VERIFYING", "SUPERSEDED"},
    "VERIFYING": {"ACCEPTED", "BLOCKED"},
    "BLOCKED": {"ACTIVE"},
    "ACCEPTED": set(),
    "SUPERSEDED": set(),
}
CRITERION_STATUSES = {"PASS", "PARTIAL", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}
PROJECT_EXECUTION_STATUSES = {"ACTIVE", "BLOCKED", "TARGET_LEVEL_REACHED", "CANCELLED"}
ASSESSMENT_ROUTES = {
    "COMPLETE_CURRENT_STAGE",
    "MAINTAIN_CURRENT_STAGE",
    "ADVANCE_TO_NEXT_STAGE",
    "TARGET_ALREADY_REACHED",
    "STABILIZE_CURRENT_STAGE",
}
ASSESSMENT_REF_PATTERN = re.compile(
    r"^(?P<assessment_id>VAL-[A-Z0-9](?:[A-Z0-9._:-]*[A-Z0-9])?)@(?P<revision>[1-9][0-9]*)$"
)
ASSESSMENT_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


def _parse_exact_assessment_ref(value: Any) -> tuple[str, int, str]:
    """Parse one canonical immutable maturity-assessment revision reference."""
    if not isinstance(value, str):
        raise ValidationFailure(
            "assessment_ref must be an exact canonical revisioned reference",
            value,
        )
    match = ASSESSMENT_REF_PATTERN.fullmatch(value)
    if match is None:
        raise ValidationFailure(
            "assessment_ref must match <assessment-id>@<positive-integer-revision>",
            value,
        )
    assessment_id = match.group("assessment_id")
    revision = int(match.group("revision"))
    canonical_ref = f"{assessment_id}@{revision}"
    if value != canonical_ref:
        raise ValidationFailure("assessment_ref is not canonical", value)
    return assessment_id, revision, canonical_ref


def _resolve_exact_maturity_assessment(
    root: Path,
    assessment_ref: Any,
    assessment_digest: Any,
) -> dict[str, Any]:
    """Resolve and verify exactly one immutable maturity-assessment revision."""
    assessment_id, requested_revision, canonical_ref = _parse_exact_assessment_ref(assessment_ref)
    if not isinstance(assessment_digest, str) or ASSESSMENT_DIGEST_PATTERN.fullmatch(assessment_digest) is None:
        raise ValidationFailure(
            "assessment_digest must use canonical sha256:<64 lowercase hex> form",
            assessment_digest,
        )

    assessment_dir = root / ".harness/stages/ASSESSMENTS"
    expected_filename = f"{canonical_ref}.yaml"
    assessment_file = assessment_dir / expected_filename
    if assessment_file.name != expected_filename or assessment_file.parent != assessment_dir:
        raise ValidationFailure("Resolved maturity assessment path is not exact", canonical_ref)
    if not _native_io_path(assessment_file).is_file():
        raise ValidationFailure("Referenced maturity assessment is absent", canonical_ref)

    actual_digest = f"sha256:{sha256_file(assessment_file)}"
    if actual_digest != assessment_digest:
        raise ValidationFailure(
            "Maturity assessment digest mismatch",
            {"assessment_ref": canonical_ref, "expected": assessment_digest, "actual": actual_digest},
        )

    document = load_data(assessment_file)
    if not isinstance(document, dict) or set(document) != {"maturity_assessment"}:
        raise ValidationFailure(
            "Maturity assessment envelope must be exactly maturity_assessment",
            canonical_ref,
        )
    assessment = document["maturity_assessment"]
    if not isinstance(assessment, dict):
        raise ValidationFailure("Maturity assessment body is invalid", canonical_ref)
    if assessment.get("id") != assessment_id:
        raise ValidationFailure(
            "Maturity assessment internal id does not match assessment_ref",
            {"assessment_ref": canonical_ref, "internal_id": assessment.get("id")},
        )
    internal_revision = assessment.get("revision")
    if type(internal_revision) is not int or internal_revision != requested_revision:
        raise ValidationFailure(
            "Maturity assessment internal revision does not match assessment_ref",
            {"assessment_ref": canonical_ref, "internal_revision": internal_revision},
        )

    return {
        "assessment_ref": canonical_ref,
        "assessment_id": assessment_id,
        "revision": requested_revision,
        "path": assessment_file,
        "assessment_digest": actual_digest,
        "assessment": assessment,
    }


def _model() -> dict[str, Any]:
    return implementation_level_model(load_registries())


def canonical_levels() -> tuple[str, ...]:
    return tuple(_model()["order"])


def level_ordinal(level: str) -> int:
    model = _model()
    if level == "NONE":
        return 0
    if level not in model["ordinals"]:
        raise ValidationFailure("Unknown implementation level", level)
    return int(model["ordinals"][level])


def stage_path(target_level: str, *, initial_level: str = "PROTOTYPE") -> list[str]:
    model = _model()
    if target_level not in model["levels"]:
        raise ValidationFailure("Target implementation level is not canonical", target_level)
    if initial_level not in model["levels"]:
        raise ValidationFailure("Initial implementation level is not canonical", initial_level)
    order = model["order"]
    start = order.index(initial_level)
    end = order.index(target_level)
    if end < start:
        raise ValidationFailure("Stage path cannot move backwards", {"initial": initial_level, "target": target_level})
    return list(order[start : end + 1])


def next_level(level: str) -> str | None:
    model = _model()
    if level == "NONE":
        return str(model["initial"])
    item = model["levels"].get(level)
    if not item:
        raise ValidationFailure("Unknown implementation level", level)
    value = item.get("next")
    return str(value) if value else None


def previous_level(level: str) -> str | None:
    model = _model()
    if level not in model["levels"]:
        raise ValidationFailure("Unknown implementation level", level)
    value = model["levels"][level].get("previous")
    return str(value) if value else None


def _outcomes_for_level(level: str) -> list[str]:
    outcomes = {
        "PROTOTYPE": ["working_primary_flow", "documented_local_start", "prototype_permitted_use_boundary"],
        "ALPHA": ["internal_user_core_operations", "reproducible_dev_test_environment", "critical_logic_verification"],
        "BETA": ["pilot_user_core_operations", "safe_update_and_rollback", "pilot_operability_and_recovery"],
        "MVP": ["production_business_value", "production_operability", "support_and_recovery_boundary"],
        "RELEASE": ["approved_release_commitments", "release_regression_and_review", "reproducible_release_publication"],
    }
    return list(outcomes[level])


def _default_permitted_use(level: str) -> dict[str, Any]:
    # These are conservative defaults and remain UNCONFIRMED until the Gate approval.
    if level == "PROTOTYPE":
        return {
            "status": "UNCONFIRMED",
            "users": ["DEVELOPER"],
            "environments": ["LOCAL"],
            "data_classes": ["PUBLIC"],
            "data_constraints": ["SYNTHETIC_ONLY"],
        }
    return {
        "status": "UNCONFIRMED",
        "users": [],
        "environments": [],
        "data_classes": [],
        "data_constraints": [],
    }


def _hard_constraint_overrides(project_input: dict[str, Any]) -> list[dict[str, Any]]:
    values = deep_get(project_input, "project.constraints.mandatory", []) or []
    overrides: list[dict[str, Any]] = []
    for index, value in enumerate(values, 1):
        if isinstance(value, dict):
            statement = value.get("statement") or value.get("title") or str(value)
            source_ref = value.get("source_ref")
        else:
            statement = str(value)
            source_ref = None
        overrides.append(
            {
                "key": f"HARD_CONSTRAINT_{index:03d}",
                "statement": statement,
                "source_ref": source_ref,
                "mandatory": True,
                "required_evidence_kinds": ["EXTERNAL_EVIDENCE"],
            }
        )
    return overrides


def _criteria_for_level(level: str) -> list[str]:
    model = _model()
    profile = model["profiles"].get(level)
    if not isinstance(profile, dict):
        raise ValidationFailure("Missing criteria profile", level)
    return [str(item) for item in profile.get("criteria_refs") or []]


def _criterion_result_template(criterion_ref: str) -> dict[str, Any]:
    return {
        "criterion_ref": criterion_ref,
        "status": "UNKNOWN",
        "evidence_refs": [],
        "rationale": "Evidence has not yet been accepted for this Gate.",
        "validator": None,
    }


def _plan_id(token: str, level: str) -> str:
    return f"STG-{token}-{level}-001"


def _gate_id(token: str, level: str) -> str:
    return f"GATE-{token}-{level}-001"


def _acceptance_id(token: str, level: str) -> str:
    return f"VAL-{token}-{level}-001"


def _load_index(root: Path, path: Path, key: str) -> dict[str, Any]:
    full = root / path
    if not _native_io_path(full).exists():
        return {"order": [], "current": {}}
    value = load_data(full)
    index = value.get(key) if isinstance(value, dict) else None
    if not isinstance(index, dict):
        raise ValidationFailure("Stage index envelope is invalid", str(path))
    return index


def _write_index(root: Path, path: Path, key: str, value: dict[str, Any]) -> None:
    write_data(root / path, {key: value})


def _load_stage_state(root: Path) -> tuple[Path, dict[str, Any]]:
    path = root / STAGE_STATE_PATH
    value = load_data(path)
    implementation = value.get("implementation") if isinstance(value, dict) else None
    if not isinstance(implementation, dict):
        raise ValidationFailure("Stage State envelope is invalid", str(path))
    validate_stage_state(value)
    return path, value


def load_stage_state(root: Path) -> dict[str, Any]:
    return deepcopy(_load_stage_state(native_resolve(root.expanduser()))[1]["implementation"])


def load_current_target_level(
    workspace: Path,
    *,
    stage_state: dict[str, Any] | None = None,
) -> str:
    """Load the canonical target for either a prepared project or external intake.

    A prepared Project Instance is identified by its canonical Stage State and must
    never fall back to the immutable accepted intake record. Before preparation,
    the current intake target remains the value in PROJECT_INPUT.yaml.
    """
    workspace = native_resolve(workspace.expanduser())
    stage_state_path = workspace / STAGE_STATE_PATH
    if _native_io_path(stage_state_path).is_file():
        implementation = stage_state if stage_state is not None else load_stage_state(workspace)
        target = implementation.get("target_level") if isinstance(implementation, dict) else None
        source = STAGE_STATE_PATH.as_posix()
    else:
        input_path = workspace / "PROJECT_INPUT.yaml"
        if not _native_io_path(input_path).is_file():
            raise ValidationFailure(
                "Current target source is missing",
                {
                    "workspace": str(workspace),
                    "prepared_project_source": STAGE_STATE_PATH.as_posix(),
                    "intake_source": "PROJECT_INPUT.yaml",
                },
            )
        project_input = load_data(input_path)
        target = deep_get(project_input, "implementation.target_level")
        source = "PROJECT_INPUT.yaml"

    if target == "UNSURE":
        raise WaitingDecision("Current target implementation level requires confirmation", {"source": source})
    if target not in canonical_levels():
        raise WaitingInput(
            "Canonical current target implementation level is required",
            {"source": source, "value": target},
        )
    return str(target)


def validate_stage_state(value: Any) -> None:
    implementation = value.get("implementation") if isinstance(value, dict) else None
    if not isinstance(implementation, dict):
        raise ValidationFailure("Stage State must contain implementation object")
    required = [
        "scale_version",
        "target_level",
        "claimed_current_level",
        "observed_candidate_level",
        "highest_accepted_level",
        "active_stage",
        "progression_policy",
        "future_stage_work",
        "stage_path",
        "revision",
    ]
    missing = [field for field in required if field not in implementation]
    if missing:
        raise ValidationFailure("Stage State is missing required fields", missing)
    canonical = set(canonical_levels())
    target = implementation.get("target_level")
    active = implementation.get("active_stage")
    accepted = implementation.get("highest_accepted_level")
    observed = implementation.get("observed_candidate_level")
    claimed = implementation.get("claimed_current_level")
    if target not in canonical:
        raise ValidationFailure("Stage State target_level is not canonical", target)
    if active not in canonical:
        raise ValidationFailure("Stage State active_stage is not canonical", active)
    for field, actual in (
        ("highest_accepted_level", accepted),
        ("observed_candidate_level", observed),
        ("claimed_current_level", claimed),
    ):
        if actual not in canonical | {"NONE", "UNKNOWN"}:
            raise ValidationFailure(f"Stage State {field} is invalid", actual)
    path = implementation.get("stage_path")
    if path != stage_path(str(target)):
        raise ValidationFailure("Stage State stage_path does not match target", {"target": target, "path": path})
    if active not in path:
        raise ValidationFailure("Active stage is outside stage_path", active)
    if implementation.get("progression_policy") != "SEQUENTIAL":
        raise ValidationFailure("Stage State progression_policy must be SEQUENTIAL")
    if implementation.get("future_stage_work") != "FORBIDDEN":
        raise ValidationFailure("Stage State future_stage_work must be FORBIDDEN")
    if not isinstance(implementation.get("revision"), int) or implementation["revision"] < 1:
        raise ValidationFailure("Stage State revision must be a positive integer")
    if accepted not in {"NONE", "UNKNOWN"} and level_ordinal(str(accepted)) > level_ordinal(str(target)):
        # A lower target is represented as already reached, never by destructive downgrade.
        pass


def validate_stage_plan(value: Any) -> None:
    plan = value.get("stage_plan") if isinstance(value, dict) else None
    if not isinstance(plan, dict):
        raise ValidationFailure("Stage Plan envelope is invalid")
    required = [
        "id", "revision", "level", "status", "target_level", "baseline_ref", "scope_refs",
        "required_outcomes", "criteria_profile_ref", "hard_constraint_overrides",
        "work_package_outlines", "deferred_to_next_stage",
    ]
    missing = [field for field in required if field not in plan]
    if missing:
        raise ValidationFailure("Stage Plan is missing required fields", missing)
    if plan.get("level") not in canonical_levels() or plan.get("target_level") not in canonical_levels():
        raise ValidationFailure("Stage Plan level/target is not canonical")
    if plan.get("status") not in STAGE_TRANSITIONS:
        raise ValidationFailure("Stage Plan status is invalid", plan.get("status"))
    expected_ref = f"REG-IMPLEMENTATION-LEVELS#{plan['level']}"
    if plan.get("criteria_profile_ref") != expected_ref:
        raise ValidationFailure("Stage Plan criteria profile ref is invalid", plan.get("criteria_profile_ref"))
    if plan.get("level") != "PROTOTYPE" and plan.get("detailed_work_package_refs"):
        # This is only valid once that stage is active; cross-state validation handles it.
        pass


def validate_stage_gate(value: Any, *, require_closure: bool = False) -> None:
    gate = value.get("stage_gate") if isinstance(value, dict) else None
    if not isinstance(gate, dict):
        raise ValidationFailure("Stage Gate envelope is invalid")
    required = [
        "id", "revision", "type", "level", "stage_plan_ref", "status", "criteria_results",
        "required_work_package_refs", "critical_blocker_refs", "permitted_use",
    ]
    missing = [field for field in required if field not in gate]
    if missing:
        raise ValidationFailure("Stage Gate is missing required fields", missing)
    if gate.get("type") != "STAGE_ACCEPTANCE":
        raise ValidationFailure("Stage Gate type must be STAGE_ACCEPTANCE")
    if gate.get("level") not in canonical_levels():
        raise ValidationFailure("Stage Gate level is not canonical", gate.get("level"))
    results = gate.get("criteria_results")
    if not isinstance(results, list):
        raise ValidationFailure("Stage Gate criteria_results must be an array")
    unresolved: list[str] = []
    for item in results:
        if not isinstance(item, dict):
            raise ValidationFailure("Stage Gate criterion result must be an object")
        status = item.get("status")
        if status not in CRITERION_STATUSES:
            raise ValidationFailure("Stage Gate criterion status is invalid", status)
        ref = str(item.get("criterion_ref") or "")
        if status == "NOT_APPLICABLE":
            if not nonempty(item.get("rationale")) or not nonempty(item.get("validator")):
                raise ValidationFailure("NOT_APPLICABLE requires rationale and validator", ref)
        if status == "PASS" and not (item.get("evidence_refs") or []):
            raise ValidationFailure("PASS criterion requires evidence_refs", ref)
        if require_closure and status not in {"PASS", "NOT_APPLICABLE"}:
            unresolved.append(ref)
    if require_closure and unresolved:
        raise ValidationFailure("Stage Gate has unresolved mandatory criteria", unresolved)
    if require_closure and (gate.get("critical_blocker_refs") or []):
        raise ValidationFailure("Stage Gate has OPEN critical blockers", gate.get("critical_blocker_refs"))
    if require_closure:
        permitted = gate.get("permitted_use")
        if not isinstance(permitted, dict) or permitted.get("status") in {None, "UNCONFIRMED"}:
            raise ValidationFailure("Stage Gate requires confirmed permitted_use")
        evidence_refs = gate.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ValidationFailure("Accepted Stage Gate requires evidence_refs")
        bindings = normalize_evidence_bindings(gate.get("evidence_bindings"))
        if sorted(str(ref) for ref in evidence_refs) != [item["ref"] for item in bindings]:
            raise ValidationFailure("Accepted Stage Gate evidence_refs differ from evidence_bindings")
        if not isinstance(gate.get("base_revision"), str) or not str(gate["base_revision"]).startswith("tree:sha256:"):
            raise ValidationFailure("Accepted Stage Gate requires an immutable tree baseline revision")


def validate_stage_acceptance(value: Any) -> None:
    report = value.get("stage_acceptance") if isinstance(value, dict) else None
    if not isinstance(report, dict):
        raise ValidationFailure("Stage Acceptance Report envelope is invalid")
    required = [
        "id", "revision", "level", "status", "acceptance_method", "baseline_revision",
        "accepted_at", "decision_ref", "evidence_refs", "evidence_bindings", "permitted_use",
        "known_limitations", "next_stage_gaps",
    ]
    missing = [field for field in required if field not in report]
    if missing:
        raise ValidationFailure("Stage Acceptance Report is missing required fields", missing)
    if not str(report.get("id", "")).startswith("VAL-"):
        raise ValidationFailure("Stage Acceptance Report id must use VAL prefix", report.get("id"))
    if report.get("revision") != 1:
        raise ValidationFailure("Stage Acceptance Report is immutable at revision 1", report.get("revision"))
    if report.get("level") not in canonical_levels():
        raise ValidationFailure("Stage Acceptance Report level is not canonical", report.get("level"))
    if report.get("status") != "PASS":
        raise ValidationFailure("Stage Acceptance Report status must be PASS", report.get("status"))
    method = report.get("acceptance_method")
    if method not in {"EXECUTED_STAGE_WORK", "SATISFIED_BY_BASELINE"}:
        raise ValidationFailure("Stage Acceptance Report acceptance_method is invalid", method)
    assessment_ref = report.get("assessment_ref")
    if method == "SATISFIED_BY_BASELINE":
        _parse_exact_assessment_ref(assessment_ref)
    elif assessment_ref is not None:
        _parse_exact_assessment_ref(assessment_ref)
    if not str(report.get("baseline_revision", "")).startswith("tree:sha256:"):
        raise ValidationFailure("Stage Acceptance Report requires an immutable tree baseline revision")
    if not str(report.get("decision_ref", "")).startswith("DEC-"):
        raise ValidationFailure("Stage Acceptance Report requires a Decision reference")
    if not report.get("evidence_refs"):
        raise ValidationFailure("Stage Acceptance Report requires evidence_refs")
    bindings = normalize_evidence_bindings(report.get("evidence_bindings"))
    if sorted(str(ref) for ref in report.get("evidence_refs") or []) != [item["ref"] for item in bindings]:
        raise ValidationFailure("Stage Acceptance Report evidence_refs differ from evidence_bindings")
    permitted = report.get("permitted_use")
    if not isinstance(permitted, dict) or permitted.get("status") not in {None, "CONFIRMED"}:
        raise ValidationFailure("Stage Acceptance Report permitted_use must be confirmed")
    if not isinstance(report.get("known_limitations"), list) or not isinstance(report.get("next_stage_gaps"), list):
        raise ValidationFailure("Stage Acceptance Report limitations and gaps must be arrays")


def _current_entity(root: Path, index_path: Path, index_key: str, entity_id: str, envelope: str) -> tuple[dict[str, Any], str]:
    index = _load_index(root, index_path, index_key)
    rel = (index.get("current") or {}).get(entity_id)
    if not rel:
        raise ValidationFailure(f"{envelope} is not indexed", entity_id)
    value = load_data(root / rel)
    entity = value.get(envelope) if isinstance(value, dict) else None
    if not isinstance(entity, dict):
        raise ValidationFailure(f"{envelope} envelope is invalid", rel)
    return entity, str(rel)


def _next_revision_path(base_dir: str, entity_id: str, revision: int) -> str:
    return f"{base_dir}/{entity_id}@{revision}.yaml"


def _write_stage_plan_revision(root: Path, plan: dict[str, Any], **changes: Any) -> tuple[dict[str, Any], str]:
    current = deepcopy(plan)
    previous_ref = f"{current['id']}@{current['revision']}"
    new_revision = int(current["revision"]) + 1
    current.update(changes)
    current["revision"] = new_revision
    current["previous_revision_ref"] = previous_ref
    current["updated_at"] = utc_now()
    rel = _next_revision_path(".harness/stages/PLANS", current["id"], new_revision)
    write_data(root / rel, {"stage_plan": current})
    index = _load_index(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index")
    index.setdefault("current", {})[current["id"]] = rel
    _write_index(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index", index)
    return current, rel


def _write_stage_gate_revision(root: Path, gate: dict[str, Any], **changes: Any) -> tuple[dict[str, Any], str]:
    current = deepcopy(gate)
    previous_ref = f"{current['id']}@{current['revision']}"
    new_revision = int(current["revision"]) + 1
    current.update(changes)
    current["revision"] = new_revision
    current["previous_revision_ref"] = previous_ref
    current["updated_at"] = utc_now()
    rel = _next_revision_path(".harness/stages/GATES", current["id"], new_revision)
    write_data(root / rel, {"stage_gate": current})
    index = _load_index(root, STAGE_GATE_INDEX_PATH, "stage_gate_index")
    index.setdefault("current", {})[current["id"]] = rel
    _write_index(root, STAGE_GATE_INDEX_PATH, "stage_gate_index", index)
    return current, rel


def create_initial_stage_artifacts(
    root: Path,
    project_input: dict[str, Any],
    *,
    token: str,
    baseline_ref: str,
    scope_refs: list[str],
    work_package_refs: list[str],
) -> dict[str, Any]:
    root = native_resolve(root)
    target = deep_get(project_input, "implementation.target_level")
    claimed = deep_get(project_input, "implementation.claimed_current_level")
    if target not in canonical_levels():
        if target == "UNSURE":
            raise WaitingDecision("Target implementation level requires confirmation")
        raise WaitingInput("Target implementation level is required")
    project_mode = str(deep_get(project_input, "project.mode", "")).upper()
    if project_mode == "GREENFIELD" and claimed != "NONE":
        raise ValidationFailure("Greenfield claimed_current_level must be NONE", claimed)
    if project_mode in {"BROWNFIELD", "HYBRID"} and claimed not in set(canonical_levels()) | {"UNKNOWN"}:
        raise ValidationFailure("Brownfield/Hybrid claimed_current_level is invalid", claimed)

    path = stage_path(str(target))
    active = path[0]
    model = _model()
    overrides = _hard_constraint_overrides(project_input)
    plans_index = {"order": [], "by_level": {}, "current": {}}
    gates_index = {"order": [], "by_level": {}, "current": {}}
    planning_wps = deep_get(project_input, "planning.work_packages", []) or []

    for level in path:
        plan_id = _plan_id(token, level)
        gate_id = _gate_id(token, level)
        is_active = level == active
        if is_active:
            outlines = [
                {
                    "title": str(item.get("title") or f"Active {level} work"),
                    "outcome": str(item.get("objective") or "Deliver the accepted active-stage outcome"),
                }
                for item in planning_wps
            ]
        else:
            previous = previous_level(level)
            outlines = [
                {
                    "title": f"{level} delta review",
                    "outcome": f"Recompute the {level} delta only after acceptance of {previous}",
                }
            ]
        nxt = next_level(level)
        deferred = []
        if nxt and nxt in path:
            deferred = [
                f"Recompute {nxt} criteria delta after {level} acceptance; do not precompile atomic work."
            ]
        plan = {
            "id": plan_id,
            "revision": 1,
            "level": level,
            "status": "ACTIVE" if is_active else "PLANNED",
            "target_level": target,
            "baseline_ref": baseline_ref,
            "scope_refs": list(scope_refs),
            "required_outcomes": _outcomes_for_level(level),
            "criteria_profile_ref": f"REG-IMPLEMENTATION-LEVELS#{level}",
            "hard_constraint_overrides": deepcopy(overrides),
            "work_package_outlines": outlines,
            "deferred_to_next_stage": deferred,
            "detailed_work_package_refs": list(work_package_refs) if is_active else [],
            "gate_ref": f"{gate_id}@1",
            "review_required": not is_active,
            "created_at": utc_now(),
        }
        validate_stage_plan({"stage_plan": plan})
        plan_rel = f".harness/stages/PLANS/{plan_id}@1.yaml"
        write_data(root / plan_rel, {"stage_plan": plan})
        plans_index["order"].append(plan_id)
        plans_index["by_level"][level] = plan_id
        plans_index["current"][plan_id] = plan_rel

        results = [_criterion_result_template(ref) for ref in _criteria_for_level(level)]
        results.extend(_criterion_result_template(item["key"]) for item in overrides)
        gate = {
            "id": gate_id,
            "revision": 1,
            "type": "STAGE_ACCEPTANCE",
            "level": level,
            "stage_plan_ref": f"{plan_id}@1",
            "status": "ACTIVE" if is_active else "PLANNED",
            "criteria_results": results,
            "required_work_package_refs": list(work_package_refs) if is_active else [],
            "critical_blocker_refs": [],
            "hard_constraint_overrides": deepcopy(overrides),
            "profile_control_refs": [deep_get(project_input, "profile.ref")],
            "evidence_refs": [],
            "base_revision": baseline_ref,
            "permitted_use": _default_permitted_use(level),
            "created_at": utc_now(),
        }
        validate_stage_gate({"stage_gate": gate})
        gate_rel = f".harness/stages/GATES/{gate_id}@1.yaml"
        write_data(root / gate_rel, {"stage_gate": gate})
        gates_index["order"].append(gate_id)
        gates_index["by_level"][level] = gate_id
        gates_index["current"][gate_id] = gate_rel

    _write_index(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index", plans_index)
    _write_index(root, STAGE_GATE_INDEX_PATH, "stage_gate_index", gates_index)
    now = utc_now()
    state = {
        "schema_version": 1,
        "implementation": {
            "scale_version": 1,
            "target_level": target,
            "claimed_current_level": claimed,
            "observed_candidate_level": "NONE",
            "highest_accepted_level": "NONE",
            "active_stage": active,
            "progression_policy": "SEQUENTIAL",
            "future_stage_work": "FORBIDDEN",
            "stage_path": path,
            "revision": 1,
            "permitted_use": _default_permitted_use(active),
            "last_acceptance_ref": None,
            "last_assessment_ref": None,
            "updated_at": now,
        },
    }
    validate_stage_state(state)
    write_data(root / STAGE_STATE_PATH, state)
    history = root / ".harness/stages/STATE_HISTORY/STAGE_STATE@1.yaml"
    write_data(history, state)
    return {
        "target_level": target,
        "active_stage": active,
        "stage_path": path,
        "stage_plan_refs": [f"{plans_index['by_level'][level]}@1" for level in path],
        "gate_refs": [f"{gates_index['by_level'][level]}@1" for level in path],
    }


def validate_stage_cross_references(root: Path) -> dict[str, Any]:
    root = native_resolve(root)
    state = load_stage_state(root)
    plan_index = _load_index(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index")
    gate_index = _load_index(root, STAGE_GATE_INDEX_PATH, "stage_gate_index")
    errors: list[str] = []
    active = state["active_stage"]
    path = state["stage_path"]
    active_count = 0
    for level in path:
        plan_id = (plan_index.get("by_level") or {}).get(level)
        gate_id = (gate_index.get("by_level") or {}).get(level)
        if not plan_id or not gate_id:
            errors.append(f"{level}: missing Stage Plan/Gate index entry")
            continue
        plan, _ = _current_entity(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index", plan_id, "stage_plan")
        gate, _ = _current_entity(root, STAGE_GATE_INDEX_PATH, "stage_gate_index", gate_id, "stage_gate")
        try:
            validate_stage_plan({"stage_plan": plan})
            validate_stage_gate({"stage_gate": gate})
        except ValidationFailure as exc:
            errors.append(f"{level}: {exc.message}: {exc.details}")
        if plan.get("level") != level or gate.get("level") != level:
            errors.append(f"{level}: indexed artifact level mismatch")
        if str(gate.get("stage_plan_ref", "")).split("@")[0] != plan_id:
            errors.append(f"{level}: Gate does not reference current Stage Plan identity")
        if plan.get("status") in {"ACTIVE", "VERIFYING", "BLOCKED"}:
            active_count += 1
            if level != active:
                errors.append(f"{level}: future/non-active Stage Plan is {plan.get('status')}")
        # Accepted stages retain their detailed Work Package references as immutable
        # execution history. Only future stages are prohibited from having detailed
        # atomic work before they become active.
        if level_ordinal(level) > level_ordinal(active) and plan.get("detailed_work_package_refs"):
            errors.append(f"{level}: future stage has detailed Work Packages")
    if active_count != 1 and state.get("highest_accepted_level") != state.get("target_level"):
        errors.append(f"expected exactly one active/transitioning stage, found {active_count}")

    # Nonterminal ordinary work belongs to the canonical active Stage.
    # Governed maintenance is the single exception: it may run at the last
    # accepted level while a separately planned next Stage remains dormant.
    # Its task/WP must be bound to the exact ACTIVE maintenance plan.
    from .maintenance import active_maintenance
    maintenance = active_maintenance(root)

    def executable_binding(entity: dict[str, Any]) -> bool:
        if entity.get("maintenance_route") == "MAINTAIN_CURRENT_STAGE":
            return bool(maintenance and entity.get("maintenance_plan_ref") == maintenance.get("plan_ref")
                        and entity.get("implementation_stage") == maintenance.get("implementation_stage"))
        return entity.get("maintenance_route") is None and entity.get("implementation_stage") == active

    task_index_path = root / ".harness/tasks/INDEX.yaml"
    if _native_io_path(task_index_path).exists():
        task_index = load_data(task_index_path).get("task_index") or {}
        for task_id, rel in (task_index.get("current") or {}).items():
            task = load_data(root / rel).get("task") or {}
            if task.get("status") not in {"DONE", "SUPERSEDED", "CANCELLED", "STALE"} and not executable_binding(task):
                errors.append(
                    f"{task_id}: task is not bound to the current executable Stage/maintenance route"
                )
    wp_index_path = root / ".harness/work-packages/INDEX.yaml"
    if _native_io_path(wp_index_path).exists():
        wp_index = load_data(wp_index_path).get("work_package_index") or {}
        for wp_id, rel in (wp_index.get("current") or {}).items():
            wp = load_data(root / rel).get("work_package") or {}
            if wp.get("status") not in {"COMPLETED", "SUPERSEDED", "CANCELLED"} and not executable_binding(wp):
                errors.append(
                    f"{wp_id}: Work Package is not bound to the current executable Stage/maintenance route"
                )
    return {"status": "PASS" if not errors else "FAIL", "active_stage": active, "target_level": state["target_level"], "errors": errors}


def mark_active_stage_verifying(root: Path) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    recover_stage_transactions(root)
    state_path, state_doc = _load_stage_state(root)
    state = state_doc["implementation"]
    active = state["active_stage"]
    plan_index = _load_index(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index")
    gate_index = _load_index(root, STAGE_GATE_INDEX_PATH, "stage_gate_index")
    plan_id = plan_index["by_level"][active]
    gate_id = gate_index["by_level"][active]
    plan, _ = _current_entity(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index", plan_id, "stage_plan")
    gate, _ = _current_entity(root, STAGE_GATE_INDEX_PATH, "stage_gate_index", gate_id, "stage_gate")
    if plan.get("status") == "VERIFYING":
        return {"status": "VERIFYING", "active_stage": active, "gate_ref": f"{gate['id']}@{gate['revision']}", "idempotent": True}
    if plan.get("status") != "ACTIVE":
        raise ValidationFailure("Active Stage Plan cannot enter VERIFYING", {"status": plan.get("status"), "level": active})
    new_plan, plan_rel = _write_stage_plan_revision(root, plan, status="VERIFYING")
    new_gate, gate_rel = _write_stage_gate_revision(root, gate, status="VERIFYING", stage_plan_ref=f"{new_plan['id']}@{new_plan['revision']}")
    state["revision"] = int(state["revision"]) + 1
    state["updated_at"] = utc_now()
    write_data(state_path, state_doc)
    write_data(root / f".harness/stages/STATE_HISTORY/STAGE_STATE@{state['revision']}.yaml", state_doc)
    return {
        "status": "VERIFYING",
        "active_stage": active,
        "gate_ref": f"{new_gate['id']}@{new_gate['revision']}",
        "idempotent": False,
        "kernel_written_paths": [
            plan_rel,
            STAGE_PLAN_INDEX_PATH.as_posix(),
            gate_rel,
            STAGE_GATE_INDEX_PATH.as_posix(),
            STAGE_STATE_PATH.as_posix(),
            f".harness/stages/STATE_HISTORY/STAGE_STATE@{state['revision']}.yaml",
        ],
    }


def _all_required_work_packages_complete(root: Path, refs: Iterable[str]) -> tuple[bool, list[str]]:
    index_path = root / ".harness/work-packages/INDEX.yaml"
    index = load_data(index_path).get("work_package_index") if _native_io_path(index_path).exists() else None
    current = index.get("current") if isinstance(index, dict) else {}
    incomplete: list[str] = []
    for ref in refs:
        wp_id = str(ref).split("@")[0]
        rel = (current or {}).get(wp_id)
        if not rel:
            incomplete.append(f"{wp_id}:missing")
            continue
        wp = load_data(root / rel).get("work_package") or {}
        if wp.get("status") != "COMPLETED":
            incomplete.append(f"{wp_id}:{wp.get('status')}")
    return (not incomplete, incomplete)


def product_baseline_revision(root: Path) -> str:
    """Return the canonical public product-tree baseline without repository commands.

    The helper hashes the same file set used by runtime snapshots. Generated root
    views and the ``.harness`` control plane are excluded, so operator drafts and
    governed evidence do not invalidate the product baseline by themselves.
    """
    root = native_resolve(root.expanduser())
    files = [root / relative for relative in snapshot_product(root)]
    return f"tree:sha256:{tree_hash(root, files)}"


# Backward-compatible private import retained for existing v0.5.0 integrations.
_product_baseline_revision = product_baseline_revision


def _context_issue(
    code: str,
    field: str,
    *,
    actual: Any,
    expected: Any,
    message: str,
) -> dict[str, Any]:
    """Build one stable, machine-readable freshness/context issue."""
    return {
        "code": code,
        "field": field,
        "message": message,
        "actual": deepcopy(actual),
        "expected": deepcopy(expected),
    }


def _assessment_criteria_context(
    assessment: dict[str, Any],
) -> tuple[str | None, dict[str, dict[str, dict[str, Any]]], list[dict[str, Any]]]:
    """Recompute sequential maturity from mandatory registry criteria.

    The declared highest candidate is never trusted on its own.  This helper is
    intentionally read-only and accepts no approval/Gate evidence extensions.
    """
    criteria_results = assessment.get("criteria_results")
    issues: list[dict[str, Any]] = []
    mapped: dict[str, dict[str, dict[str, Any]]] = {}
    if not isinstance(criteria_results, dict):
        issues.append(
            _context_issue(
                "ASSESSMENT_CRITERIA_RESULTS_INVALID",
                "criteria_results",
                actual=type(criteria_results).__name__,
                expected="object keyed by every canonical level",
                message="Assessment criteria_results cannot be used to verify the declared candidate.",
            )
        )
        return None, mapped, issues

    highest = "NONE"
    sequentially_closed = True
    for candidate_level in canonical_levels():
        raw_results = criteria_results.get(candidate_level)
        if not isinstance(raw_results, list):
            issues.append(
                _context_issue(
                    "ASSESSMENT_LEVEL_CRITERIA_INVALID",
                    f"criteria_results.{candidate_level}",
                    actual=type(raw_results).__name__,
                    expected="array",
                    message=f"Assessment criteria for {candidate_level} are not an array.",
                )
            )
            mapped[candidate_level] = {}
            sequentially_closed = False
            continue

        level_map: dict[str, dict[str, Any]] = {}
        duplicates: list[str] = []
        for item in raw_results:
            if not isinstance(item, dict) or not nonempty(item.get("criterion_ref")):
                issues.append(
                    _context_issue(
                        "ASSESSMENT_CRITERION_RECORD_INVALID",
                        f"criteria_results.{candidate_level}",
                        actual=item,
                        expected="criterion result object with criterion_ref",
                        message=f"Assessment contains an invalid criterion result for {candidate_level}.",
                    )
                )
                sequentially_closed = False
                continue
            ref = str(item["criterion_ref"])
            if ref in level_map:
                duplicates.append(ref)
            level_map[ref] = item
        mapped[candidate_level] = level_map
        if duplicates:
            issues.append(
                _context_issue(
                    "ASSESSMENT_DUPLICATE_CRITERIA",
                    f"criteria_results.{candidate_level}",
                    actual=sorted(set(duplicates)),
                    expected="one record per mandatory criterion",
                    message=f"Assessment duplicates mandatory criterion results for {candidate_level}.",
                )
            )
            sequentially_closed = False

        required_refs = _criteria_for_level(candidate_level)
        missing = [ref for ref in required_refs if ref not in level_map]
        if missing:
            issues.append(
                _context_issue(
                    "ASSESSMENT_MANDATORY_CRITERIA_MISSING",
                    f"criteria_results.{candidate_level}",
                    actual=missing,
                    expected=required_refs,
                    message=f"Assessment is missing mandatory criteria for {candidate_level}.",
                )
            )
            sequentially_closed = False

        level_closed = not missing and not duplicates
        for ref in required_refs:
            item = level_map.get(ref)
            if item is None:
                level_closed = False
                continue
            status = item.get("status")
            if status not in {"PASS", "NOT_APPLICABLE"}:
                level_closed = False
            if status == "PASS" and not (item.get("evidence_refs") or []):
                issues.append(
                    _context_issue(
                        "ASSESSMENT_PASS_WITHOUT_EVIDENCE",
                        f"criteria_results.{candidate_level}.{ref}.evidence_refs",
                        actual=item.get("evidence_refs"),
                        expected="one or more exact evidence refs",
                        message=f"PASS assessment criterion {ref} has no evidence refs.",
                    )
                )
                level_closed = False
            if status == "NOT_APPLICABLE" and (
                not nonempty(item.get("rationale")) or not nonempty(item.get("validator"))
            ):
                issues.append(
                    _context_issue(
                        "ASSESSMENT_NOT_APPLICABLE_UNJUSTIFIED",
                        f"criteria_results.{candidate_level}.{ref}",
                        actual={"rationale": item.get("rationale"), "validator": item.get("validator")},
                        expected="non-empty rationale and validator",
                        message=f"NOT_APPLICABLE assessment criterion {ref} is not justified.",
                    )
                )
                level_closed = False

        if sequentially_closed and level_closed:
            highest = candidate_level
        else:
            sequentially_closed = False

    return highest, mapped, issues


def _assessment_stale_evidence_context(
    assessment: dict[str, Any],
) -> tuple[set[str], list[tuple[str, str | None]]]:
    """Return stale evidence refs and stale/base-revision warning records."""
    repository_revision = assessment.get("repository_revision")
    stale_refs: set[str] = set()
    for item in assessment.get("evidence_inventory") or []:
        if not isinstance(item, dict):
            continue
        refs = item.get("refs") or ([] if item.get("id") is None else [item.get("id")])
        base_revision = item.get("base_revision")
        stale = item.get("stale") is True or (
            nonempty(base_revision) and base_revision != repository_revision
        )
        if stale:
            stale_refs.update(str(ref) for ref in refs if nonempty(ref))

    stale_warnings: list[tuple[str, str | None]] = []
    for raw in assessment.get("warnings") or []:
        text = str(raw)
        normalized = text.upper().replace("-", "_").replace(" ", "_")
        if "STALE" not in normalized and "BASE_REVISION" not in normalized:
            continue
        prefix = text.split(":", 1)[0].strip()
        evidence_ref = prefix if prefix.startswith("EVD-") else None
        if evidence_ref:
            stale_refs.add(evidence_ref)
        stale_warnings.append((text, evidence_ref))
    return stale_refs, stale_warnings


def _baseline_assessment_context_issues(
    assessment: dict[str, Any],
    approval: dict[str, Any],
    *,
    current_repository_revision: str,
    state: dict[str, Any],
    accepted_claimed_level: Any,
    requested_level: str,
    levels_to_accept: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Validate exact current-context binding before baseline acceptance."""
    accepted_level = state.get("highest_accepted_level")
    target_level = state.get("target_level")
    active_stage = state.get("active_stage")
    expected_next = (
        next_level(str(accepted_level))
        if accepted_level not in {None, "NONE", "UNKNOWN"}
        else "PROTOTYPE"
    )
    if expected_next is None:
        expected_next = accepted_level

    assessment_context = {
        "status": assessment.get("status"),
        "repository_revision": assessment.get("repository_revision"),
        "target_level": assessment.get("target_level"),
        "previous_highest_accepted_level": assessment.get("previous_highest_accepted_level"),
        "claimed_current_level": assessment.get("claimed_current_level"),
        "proposed_active_stage": assessment.get("proposed_active_stage"),
        "highest_satisfied_candidate_level": assessment.get("highest_satisfied_candidate_level"),
        "warnings": deepcopy(assessment.get("warnings") or []),
    }
    current_context = {
        "repository_revision": current_repository_revision,
        "approval_baseline_revision": approval.get("baseline_revision"),
        "target_level": target_level,
        "highest_accepted_level": accepted_level,
        "claimed_current_level": accepted_claimed_level,
        "active_stage": active_stage,
        "expected_sequential_stage": expected_next,
        "requested_accepted_level": requested_level,
        "levels_to_accept": deepcopy(levels_to_accept),
    }
    issues: list[dict[str, Any]] = []

    if assessment.get("status") != "COMPLETED":
        issues.append(
            _context_issue(
                "ASSESSMENT_NOT_COMPLETED",
                "status",
                actual=assessment.get("status"),
                expected="COMPLETED",
                message="Only a COMPLETED maturity assessment may authorize baseline acceptance.",
            )
        )
    if assessment.get("repository_revision") != current_repository_revision:
        issues.append(
            _context_issue(
                "ASSESSMENT_REPOSITORY_REVISION_MISMATCH",
                "repository_revision",
                actual=assessment.get("repository_revision"),
                expected=current_repository_revision,
                message="Assessment was created for a different canonical product tree.",
            )
        )
    if approval.get("baseline_revision") != current_repository_revision:
        issues.append(
            _context_issue(
                "APPROVAL_BASELINE_REVISION_MISMATCH",
                "approval.baseline_revision",
                actual=approval.get("baseline_revision"),
                expected=current_repository_revision,
                message="Approval baseline revision does not equal the current canonical product tree.",
            )
        )
    if assessment.get("target_level") != target_level:
        issues.append(
            _context_issue(
                "ASSESSMENT_TARGET_LEVEL_MISMATCH",
                "target_level",
                actual=assessment.get("target_level"),
                expected=target_level,
                message="Assessment target level is not the current canonical Stage State target.",
            )
        )
    if assessment.get("previous_highest_accepted_level") != accepted_level:
        issues.append(
            _context_issue(
                "ASSESSMENT_PREVIOUS_ACCEPTED_LEVEL_MISMATCH",
                "previous_highest_accepted_level",
                actual=assessment.get("previous_highest_accepted_level"),
                expected=accepted_level,
                message="Assessment was created before the current accepted maturity context.",
            )
        )
    if assessment.get("claimed_current_level") != accepted_claimed_level:
        issues.append(
            _context_issue(
                "ASSESSMENT_CLAIMED_LEVEL_MISMATCH",
                "claimed_current_level",
                actual=assessment.get("claimed_current_level"),
                expected=accepted_claimed_level,
                message="Assessment user-claim context differs from the immutable accepted project input.",
            )
        )
    if assessment.get("proposed_active_stage") != expected_next:
        issues.append(
            _context_issue(
                "ASSESSMENT_PROPOSED_STAGE_MISMATCH",
                "proposed_active_stage",
                actual=assessment.get("proposed_active_stage"),
                expected=expected_next,
                message="Assessment proposed stage contradicts sequential progression from current Stage State.",
            )
        )
    if active_stage != expected_next:
        issues.append(
            _context_issue(
                "CURRENT_STAGE_SEQUENCE_MISMATCH",
                "STAGE_STATE.active_stage",
                actual=active_stage,
                expected=expected_next,
                message="Current Stage State is not positioned at the sequential baseline candidate.",
            )
        )
    expected_levels = []
    path = state.get("stage_path")
    if isinstance(path, list) and expected_next in path and requested_level in path:
        start = path.index(expected_next)
        end = path.index(requested_level)
        if end >= start:
            expected_levels = path[start : end + 1]
    if levels_to_accept != expected_levels or not levels_to_accept:
        issues.append(
            _context_issue(
                "ASSESSMENT_SEQUENTIAL_CANDIDATE_CONTEXT_INVALID",
                "levels_to_accept",
                actual=levels_to_accept,
                expected=expected_levels or "non-empty canonical sequential prefix",
                message="Requested baseline levels are not a contiguous sequential slice of current Stage State.",
            )
        )

    declared_candidate = assessment.get("highest_satisfied_candidate_level")
    if declared_candidate not in set(canonical_levels()) | {"NONE"}:
        issues.append(
            _context_issue(
                "ASSESSMENT_HIGHEST_CANDIDATE_INVALID",
                "highest_satisfied_candidate_level",
                actual=declared_candidate,
                expected=["NONE", *canonical_levels()],
                message="Assessment highest satisfied candidate is not canonical.",
            )
        )
    elif declared_candidate == "NONE" or level_ordinal(requested_level) > level_ordinal(str(declared_candidate)):
        issues.append(
            _context_issue(
                "REQUESTED_LEVEL_EXCEEDS_ASSESSMENT_CANDIDATE",
                "requested_accepted_level",
                actual=requested_level,
                expected=f"<= {declared_candidate}",
                message="Requested baseline acceptance exceeds the assessment's highest satisfied candidate.",
            )
        )

    recomputed_candidate, criteria_by_level, criteria_issues = _assessment_criteria_context(assessment)
    issues.extend(criteria_issues)
    if recomputed_candidate is not None and declared_candidate != recomputed_candidate:
        issues.append(
            _context_issue(
                "ASSESSMENT_HIGHEST_CANDIDATE_INCONSISTENT",
                "highest_satisfied_candidate_level",
                actual=declared_candidate,
                expected=recomputed_candidate,
                message="Declared highest candidate does not match mandatory criterion closure.",
            )
        )

    stale_refs, stale_warnings = _assessment_stale_evidence_context(assessment)
    used_refs: set[str] = set()
    for accepted_candidate in levels_to_accept:
        level_map = criteria_by_level.get(accepted_candidate) or {}
        for ref in _criteria_for_level(accepted_candidate):
            item = level_map.get(ref) or {}
            used_refs.update(str(value) for value in (item.get("evidence_refs") or []) if nonempty(value))
    stale_used = sorted(stale_refs & used_refs)
    if stale_used:
        issues.append(
            _context_issue(
                "STALE_EVIDENCE_USED_FOR_MANDATORY_CRITERIA",
                "criteria_results[*].evidence_refs",
                actual=stale_used,
                expected="evidence bound to assessment.repository_revision",
                message="Stale or other-base evidence is referenced by mandatory criteria being accepted.",
            )
        )
    for warning, evidence_ref in stale_warnings:
        if evidence_ref is not None and evidence_ref not in used_refs:
            continue
        issues.append(
            _context_issue(
                "ASSESSMENT_STALE_EVIDENCE_WARNING",
                "warnings",
                actual=warning,
                expected="no stale/base-revision warning for evidence used by accepted mandatory criteria",
                message="Assessment warning marks evidence in the accepted baseline context as stale.",
            )
        )

    return issues, assessment_context, current_context


def _next_assessment_revision(root: Path, assessment_id: str) -> int:
    directory = root / ".harness/stages/ASSESSMENTS"
    pattern = re.compile(rf"^{re.escape(assessment_id)}@(?P<revision>[1-9][0-9]*)\.yaml$")
    revisions = [
        int(match.group("revision"))
        for path in native_iterdir(directory)
        if _native_io_path(path).is_file() and (match := pattern.fullmatch(path.name)) is not None
    ] if _native_io_path(directory).is_dir() else []
    return max(revisions, default=0) + 1


def _record_assessment_staleness(
    root: Path,
    resolved_assessment: dict[str, Any],
    *,
    issues: list[dict[str, Any]],
    assessment_context: dict[str, Any],
    current_context: dict[str, Any],
) -> dict[str, Any]:
    """Persist one immutable validation revision without mutating Stage State."""
    source = resolved_assessment["assessment"]
    stale = deepcopy(source)
    revision = _next_assessment_revision(root, str(source["id"]))
    detected_at = utc_now()
    stale["revision"] = revision
    stale["status"] = "STALE"
    stale["validation_kind"] = "BROWNFIELD_BASELINE_FRESHNESS"
    stale["source_assessment_ref"] = resolved_assessment["assessment_ref"]
    stale["source_assessment_digest"] = resolved_assessment["assessment_digest"]
    stale["staleness"] = {
        "detected_at": detected_at,
        "reason_codes": list(dict.fromkeys(str(item["code"]) for item in issues)),
        "issues": deepcopy(issues),
        "original_repository_revision": source.get("repository_revision"),
        "detected_current_repository_revision": current_context.get("repository_revision"),
        "assessment_context": deepcopy(assessment_context),
        "current_context": deepcopy(current_context),
    }
    existing_warnings = [str(item) for item in (source.get("warnings") or [])]
    stale["warnings"] = existing_warnings + [
        f"{item['code']}: {item['message']}" for item in issues
    ]
    stale["created_at"] = detected_at

    stale_ref = f"{source['id']}@{revision}"
    output = root / f".harness/stages/ASSESSMENTS/{stale_ref}.yaml"
    if _native_io_path(output).exists():
        raise ValidationFailure("Immutable assessment staleness revision already exists", stale_ref)
    write_data(output, {"maturity_assessment": stale})
    return {
        "assessment_ref": stale_ref,
        "assessment_path": output,
        "assessment_digest": f"sha256:{sha256_file(output)}",
    }


def _normalize_criterion_results(
    level: str,
    supplied: Any,
    *,
    overrides: list[dict[str, Any]],
    require_closure: bool = True,
) -> list[dict[str, Any]]:
    required_refs = _criteria_for_level(level) + [str(item["key"]) for item in overrides]
    if isinstance(supplied, list):
        mapping = {str(item.get("criterion_ref")): item for item in supplied if isinstance(item, dict)}
    elif isinstance(supplied, dict):
        mapping = {}
        for ref, raw in supplied.items():
            item = deepcopy(raw) if isinstance(raw, dict) else {"status": raw}
            item["criterion_ref"] = str(ref)
            mapping[str(ref)] = item
    else:
        raise ValidationFailure("Approval criteria_results must be an object or array")
    extra = sorted(set(mapping) - set(required_refs))
    missing = [ref for ref in required_refs if ref not in mapping]
    if extra or missing:
        raise ValidationFailure("Approval criteria_results do not match the exact Gate criteria", {"missing": missing, "extra": extra})
    results: list[dict[str, Any]] = []
    for ref in required_refs:
        item = deepcopy(mapping[ref])
        item["criterion_ref"] = ref
        status = item.get("status")
        if status not in CRITERION_STATUSES:
            raise ValidationFailure("Invalid criterion status", {"criterion": ref, "status": status})
        if require_closure and status not in {"PASS", "NOT_APPLICABLE"}:
            raise ValidationFailure("Mandatory criterion does not close the Stage Gate", {"criterion": ref, "status": status})
        evidence_refs = item.get("evidence_refs") or []
        if not isinstance(evidence_refs, list) or len(evidence_refs) != len(set(str(value) for value in evidence_refs)):
            raise ValidationFailure("Criterion evidence_refs must be a unique array", ref)
        if status == "PASS" and not evidence_refs:
            raise ValidationFailure("PASS criterion requires evidence_refs", ref)
        if status == "NOT_APPLICABLE":
            if evidence_refs:
                raise ValidationFailure("NOT_APPLICABLE criterion must not claim closing evidence", ref)
            if not nonempty(item.get("rationale")) or not nonempty(item.get("validator")):
                raise ValidationFailure("NOT_APPLICABLE requires rationale and validator", ref)
        item["evidence_refs"] = [str(value) for value in evidence_refs]
        item.setdefault("rationale", None)
        item.setdefault("validator", None)
        results.append(item)
    return results


def _approval_payload(path: Path, *, envelope_candidates: tuple[str, ...]) -> tuple[dict[str, Any], str]:
    value = load_data(native_resolve(path.expanduser()))
    if not isinstance(value, dict):
        raise ValidationFailure("Approval record must be an object", str(path))
    for envelope in envelope_candidates:
        candidate = value.get(envelope)
        if isinstance(candidate, dict):
            return candidate, envelope
    return value, "ROOT"


def _formal_approval(record: dict[str, Any], *, expected_level: str | None = None, expected_target: str | None = None) -> None:
    if record.get("approved") is not True:
        raise WaitingDecision("Formal approval record is not approved")
    required = ["id", "actor", "approved_at"]
    missing = [field for field in required if not nonempty(record.get(field))]
    if missing:
        raise ValidationFailure("Formal approval record is incomplete", missing)
    if not str(record["id"]).startswith("DEC-"):
        raise ValidationFailure("Formal approval id must use DEC prefix", record["id"])
    if expected_level is not None and record.get("level") != expected_level:
        raise ValidationFailure("Approval level does not match command", {"expected": expected_level, "actual": record.get("level")})
    if expected_target is not None and record.get("target_level") != expected_target:
        raise ValidationFailure("Level-up approval target does not match command", {"expected": expected_target, "actual": record.get("target_level")})


def _transactional_write(
    root: Path,
    writes: dict[Path, Any],
    *,
    transaction_id: str,
    operation_kind: str,
    request_digest: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Apply one governed Stage mutation through the crash-recovery service."""
    outcome = apply_stage_transaction(
        root,
        writes,
        transaction_id=transaction_id,
        operation_kind=operation_kind,
        request_digest=request_digest,
        result=result,
        # Keep the narrow replacement hook in this module for compatibility with
        # existing focused fault-injection tests. Recovery itself uses the
        # transaction service's verified replacement path.
        replace_canonical=lambda source, target: os.replace(source, target),
    )
    return deepcopy(outcome["result"])


def _render_committed_stage_transition(
    root: Path,
    result: dict[str, Any],
    *,
    regeneration_route: str,
) -> dict[str, Any]:
    """Render derived views without converting a committed fact into failure."""
    output = deepcopy(result)
    try:
        from .render import render_project_summary, render_roadmap, render_status

        render_project_summary(root)
        render_roadmap(root)
        render_status(root)
        output["render_status"] = "PASS"
    except Exception as exc:
        output["render_status"] = "FAILED_RECOVERABLE"
        output["render_regeneration_route"] = regeneration_route
        output.setdefault("warnings", []).append(
            {
                "code": "DERIVED_VIEW_RENDER_FAILED",
                "message": "Canonical Stage transition is COMMITTED; PROJECT.md/ROADMAP.md/STATUS.md regeneration remains recoverable.",
                "error": str(exc),
                "regeneration_route": regeneration_route,
            }
        )
    return output


def _approval_gate_data(record: dict[str, Any], level: str) -> dict[str, Any]:
    per_level = record.get("levels")
    if isinstance(per_level, dict) and isinstance(per_level.get(level), dict):
        merged = deepcopy(record)
        merged.update(deepcopy(per_level[level]))
        merged.pop("levels", None)
        return merged
    return record



def _strict_result_refs(record: dict[str, Any], field: str, ref_field: str) -> list[str]:
    value = record.get(field)
    if not isinstance(value, list):
        raise ValidationFailure(f"Strict Stage approval {field} must be an array")
    refs: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or not nonempty(item.get(ref_field)):
            raise ValidationFailure(f"Strict Stage approval {field} item is invalid", {"index": index, "ref_field": ref_field})
        refs.append(str(item[ref_field]))
    if len(refs) != len(set(refs)):
        raise ValidationFailure(f"Strict Stage approval {field} contains duplicate refs", refs)
    return refs


def _validate_strict_stage_approval_binding(root: Path, approval: dict[str, Any]) -> dict[str, Any]:
    expected_doc, details = _build_stage_approval_draft(root, require_preparable=True)
    expected = expected_doc["stage_approval"]
    fields = ["level","target_level","acceptance_method","stage_plan_ref","stage_plan_path","stage_plan_revision","stage_plan_digest",
        "prepared_from_stage_plan_status","gate_ref","gate_path","gate_revision","gate_digest","prepared_from_gate_status","gate_base_revision",
        "baseline_revision","last_acceptance_ref","last_acceptance_path","last_accepted_baseline_revision","assessment_ref","assessment_digest",
        "required_outcomes","level_criteria","hard_constraints","profile_controls","required_work_packages","critical_blockers","preparation_fingerprint"]
    mismatches: dict[str, Any] = {}
    for field in fields:
        if canonical_json_bytes(approval.get(field)) != canonical_json_bytes(expected.get(field)):
            mismatches[field] = {"expected": expected.get(field), "actual": approval.get(field)}
    contracts=[
        ("outcome_results","outcome_ref",[item["outcome_ref"] for item in expected["required_outcomes"]]),
        ("criteria_results","criterion_ref",[item["criterion_ref"] for item in expected["level_criteria"]]),
        ("hard_constraint_results","constraint_ref",[item["constraint_ref"] for item in expected["hard_constraints"]]),
        ("profile_control_results","control_ref",[item["control_ref"] for item in expected["profile_controls"]]),
    ]
    for field,ref_field,expected_refs in contracts:
        actual=_strict_result_refs(approval,field,ref_field)
        if actual != expected_refs:
            mismatches[field]={"expected_refs":expected_refs,"actual_refs":actual}
    if mismatches:
        raise ValidationFailure("Stage approval is stale or is not exact-bound to the current Stage Plan/Gate/baseline contract",mismatches)
    return details


def _validate_strict_formal_result_set(record: dict[str, Any], *, field: str, ref_field: str, expected_refs: list[str]) -> list[dict[str, Any]]:
    value=record.get(field)
    if not isinstance(value,list):
        raise ValidationFailure(f"Strict Stage approval {field} must be an array")
    mapping={str(item.get(ref_field)):item for item in value if isinstance(item,dict)}
    missing=[ref for ref in expected_refs if ref not in mapping]; extra=sorted(set(mapping)-set(expected_refs))
    if missing or extra or len(mapping)!=len(value):
        raise ValidationFailure(f"Strict Stage approval {field} does not match the exact mandatory result set",{"missing":missing,"extra":extra})
    normalized=[]
    for ref in expected_refs:
        item=deepcopy(mapping[ref]); status=item.get("status"); evidence=item.get("evidence_refs") or []
        if status not in CRITERION_STATUSES:
            raise ValidationFailure("Mandatory strict Stage approval result has an invalid status",{"field":field,"ref":ref,"status":status})
        if not isinstance(evidence,list) or len(evidence)!=len(set(str(x) for x in evidence)):
            raise ValidationFailure("Formal result evidence_refs must be a unique array",{"field":field,"ref":ref})
        if status=="PASS" and not evidence:
            raise ValidationFailure("PASS formal result requires evidence_refs",{"field":field,"ref":ref})
        if status=="NOT_APPLICABLE":
            if evidence:
                raise ValidationFailure("NOT_APPLICABLE formal result must not claim closing evidence",{"field":field,"ref":ref})
            if not nonempty(item.get("rationale")) or not nonempty(item.get("validator")):
                raise ValidationFailure("NOT_APPLICABLE formal result requires rationale and validator",{"field":field,"ref":ref})
        normalized.append(item)
    return normalized


def _validate_strict_auxiliary_result_evidence(root: Path, *, approval: dict[str, Any], details: dict[str, Any], baseline_revision: str) -> list[dict[str,str]]:
    definitions=details["definitions"]
    outcomes=_validate_strict_formal_result_set(approval,field="outcome_results",ref_field="outcome_ref",expected_refs=[x["outcome_ref"] for x in definitions["required_outcomes"]])
    _validate_strict_formal_result_set(approval,field="criteria_results",ref_field="criterion_ref",expected_refs=[x["criterion_ref"] for x in definitions["level_criteria"]])
    _validate_strict_formal_result_set(approval,field="hard_constraint_results",ref_field="constraint_ref",expected_refs=[x["constraint_ref"] for x in definitions["hard_constraints"]])
    controls=_validate_strict_formal_result_set(approval,field="profile_control_results",ref_field="control_ref",expected_refs=[x["control_ref"] for x in definitions["profile_controls"]])
    resolved: dict[str,dict[str,Any]]={}
    def check(item: dict[str,Any], ref_field: str, mapping_field: str) -> None:
        if item.get("status")!="PASS": return
        subject=str(item[ref_field])
        for raw in item.get("evidence_refs") or []:
            ref=str(raw); artifact=resolved.get(ref)
            if artifact is None:
                artifact=resolve_evidence_artifact(root,ref,verify_sources=True); resolved[ref]=artifact
            body=artifact["body"]
            if body.get("status")!="PASS":
                raise ValidationFailure("Auxiliary Stage result evidence does not have PASS status",{"subject_ref":subject,"evidence_ref":ref})
            if body.get("kind")=="USER_CLAIM":
                raise ValidationFailure("USER_CLAIM cannot close a mandatory Stage result without corroboration",{"subject_ref":subject,"evidence_ref":ref})
            if body.get("base_revision")!=baseline_revision:
                raise ValidationFailure("Auxiliary Stage result evidence is stale for the current baseline",{"subject_ref":subject,"evidence_ref":ref,"expected":baseline_revision,"actual":body.get("base_revision")})
            validate_semantic_gate_proof(root, body, subject_ref=subject)
            if subject not in (body.get(mapping_field) or []):
                raise ValidationFailure("Evidence does not map the mandatory Stage result",{"subject_ref":subject,"evidence_ref":ref,"mapping_field":mapping_field})
    for item in outcomes: check(item,"outcome_ref","outcome_refs")
    for item in controls: check(item,"control_ref","profile_control_refs")
    return sorted([{"ref":ref,"path":str(a["path"]),"sha256":str(a["sha256"])} for ref,a in resolved.items()],key=lambda x:x["ref"])


def _strict_combined_criterion_results(approval: dict[str, Any]) -> list[dict[str, Any]]:
    combined=deepcopy(approval.get("criteria_results") or [])
    for raw in approval.get("hard_constraint_results") or []:
        item=deepcopy(raw); item["criterion_ref"]=item.pop("constraint_ref",None); combined.append(item)
    return combined


def _validate_open_review_evidence(
    root: Path,
    *,
    level: str,
    criteria_results: list[dict[str, Any]],
    global_evidence_refs: Any,
    baseline_revision: str,
    overrides: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Validate every evidence claim in an honestly open formal Gate review.

    UNKNOWN/PARTIAL/FAIL are legitimate review conclusions and therefore do not
    close their subjects.  PASS claims and global evidence refs must nevertheless
    satisfy the same strict resolver/kind/provenance/baseline contract before a
    persisted BLOCKED mutation is allowed.  This keeps dangling or wrong refs in
    the no-mutation validation-failure class.
    """
    has_pass = any(item.get("status") == "PASS" for item in criteria_results)
    global_refs = global_evidence_refs or []
    if not has_pass and not global_refs:
        return []
    validation_results: list[dict[str, Any]] = []
    for item in criteria_results:
        if item.get("status") in {"PASS", "NOT_APPLICABLE"}:
            validation_results.append(deepcopy(item))
        else:
            validation_results.append(
                {
                    "criterion_ref": item["criterion_ref"],
                    "status": "NOT_APPLICABLE",
                    "evidence_refs": [],
                    "rationale": "Internal open-review evidence validation placeholder; not persisted as a Gate conclusion.",
                    "validator": "PROJECT_HARNESS_GATE_REVIEW",
                }
            )
    return validate_gate_evidence_closure(
        root,
        level=level,
        criteria_results=validation_results,
        global_evidence_refs=global_refs,
        base_revision=baseline_revision,
        overrides=overrides,
    )


def _unclosed_review_items(
    *,
    approval: dict[str, Any],
    criteria_results: list[dict[str, Any]],
    strict_approval: bool,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    def collect(field: str, ref_field: str, result_kind: str, values: Any) -> None:
        for raw in values or []:
            if not isinstance(raw, dict):
                continue
            status = str(raw.get("status") or "UNKNOWN")
            if status in {"PASS", "NOT_APPLICABLE"}:
                continue
            items.append(
                {
                    "result_kind": result_kind,
                    "result_field": field,
                    "subject_ref": str(raw.get(ref_field)),
                    "status": status,
                    "evidence_refs": [str(ref) for ref in (raw.get("evidence_refs") or [])],
                    "rationale": raw.get("rationale"),
                    "validator": raw.get("validator"),
                    "diagnostic": "Mandatory formal Gate result is not PASS or justified NOT_APPLICABLE.",
                }
            )

    collect("criteria_results", "criterion_ref", "LEVEL_OR_HARD_CONSTRAINT", criteria_results)
    if strict_approval:
        collect("outcome_results", "outcome_ref", "OUTCOME", approval.get("outcome_results"))
        collect("profile_control_results", "control_ref", "PROFILE_CONTROL", approval.get("profile_control_results"))
        permitted = approval.get("permitted_use")
        if isinstance(permitted, dict) and permitted.get("status") != "CONFIRMED":
            items.append(
                {
                    "result_kind": "PERMITTED_USE",
                    "result_field": "permitted_use",
                    "subject_ref": "PERMITTED_USE",
                    "status": str(permitted.get("status") or "UNCONFIRMED"),
                    "evidence_refs": [],
                    "rationale": None,
                    "validator": None,
                    "diagnostic": "Permitted-use boundary is not formally CONFIRMED.",
                }
            )
    return items


def _persist_stage_gate_blocked(
    root: Path,
    *,
    level: str,
    approval: dict[str, Any],
    transaction_id: str,
    request_digest: str,
    baseline_revision: str,
    plan: dict[str, Any],
    gate: dict[str, Any],
    criteria_results: list[dict[str, Any]],
    unclosed_items: list[dict[str, Any]],
    strict_approval: bool,
    strict_details: dict[str, Any] | None,
) -> dict[str, Any]:
    """Atomically persist an honest, structurally valid failed Gate review."""
    if not unclosed_items:
        raise ValidationFailure("Gate BLOCKED persistence requires at least one unclosed mandatory result")
    if plan.get("status") != "VERIFYING" or gate.get("status") != "VERIFYING":
        raise ValidationFailure(
            "Persisted Gate BLOCKED review requires current VERIFYING Stage Plan and Gate",
            {"plan_status": plan.get("status"), "gate_status": gate.get("status")},
        )
    context = _current_stage_gate_context(root)
    definitions = strict_details["definitions"] if strict_details is not None else _stage_contract_definitions(context)
    candidates = _evidence_candidate_views(context, definitions)
    by_subject: dict[str, list[str]] = {}
    for candidate in candidates:
        for subject in candidate.get("compatible_subject_refs") or []:
            by_subject.setdefault(str(subject), []).append(str(candidate["ref"]))
    diagnostics = deepcopy(unclosed_items)
    for item in diagnostics:
        item["candidate_refs"] = sorted(set(by_subject.get(str(item["subject_ref"])) or []))

    token = id_token(load_data(root / ".harness/config/PROJECT.yaml")["project"]["id_token"])
    blocker_suffix = hashlib.sha256(
        canonical_json_bytes(
            {
                "approval_id": approval["id"],
                "gate_ref": context["gate_ref"],
                "baseline_revision": baseline_revision,
                "items": diagnostics,
            }
        )
    ).hexdigest()[:12].upper()
    blocker_id = f"BLK-{token}-{level}-GATE-{blocker_suffix}"
    blocker_ref = f"{blocker_id}@1"
    blocker_rel = Path(f".harness/blockers/{blocker_ref}.yaml")
    now = utc_now()
    blocker = {
        "id": blocker_id,
        "revision": 1,
        "kind": "STAGE_GATE_BLOCKER",
        "level": level,
        "stage_plan_ref": context["plan_ref"],
        "gate_ref": context["gate_ref"],
        "baseline_revision": baseline_revision,
        "formal_review_ref": f"{approval['id']}@1",
        "formal_review_digest": f"sha256:{hashlib.sha256(canonical_json_bytes(approval)).hexdigest()}",
        "reason": "A structurally valid formal Stage review reported one or more unclosed mandatory Gate results.",
        "failed_or_missing_items": diagnostics,
        "evidence_diagnostics": {
            "candidate_evidence_refs": [str(item["ref"]) for item in candidates],
            "candidate_count": len(candidates),
            "evaluated_baseline_revision": baseline_revision,
        },
        "recovery_options": [
            "Add or prepare exact current-baseline evidence through the governed Stage acceptance preparation route.",
            "Correct an honest formal conclusion only after revalidation, then generate a fresh exact-bound approval draft.",
        ],
        "resume_condition": "Run resume-stage-gate after evidence or the final product baseline changes; recovery revalidates the exact current Gate contract.",
        "status": "OPEN",
        "created_at": now,
    }

    plan_index_doc = load_data(root / STAGE_PLAN_INDEX_PATH)
    gate_index_doc = load_data(root / STAGE_GATE_INDEX_PATH)
    plan_index = plan_index_doc["stage_plan_index"]
    gate_index = gate_index_doc["stage_gate_index"]
    new_plan = deepcopy(plan)
    new_plan["revision"] = int(plan["revision"]) + 1
    new_plan["previous_revision_ref"] = context["plan_ref"]
    new_plan["status"] = "BLOCKED"
    new_plan["gate_blocker_ref"] = blocker_ref
    new_plan["gate_diagnostics"] = {
        "formal_review_ref": blocker["formal_review_ref"],
        "baseline_revision": baseline_revision,
        "failed_or_missing_items": diagnostics,
    }
    new_plan["updated_at"] = now
    validate_stage_plan({"stage_plan": new_plan})
    plan_rel = Path(_next_revision_path(".harness/stages/PLANS", str(plan["id"]), int(new_plan["revision"])))

    new_gate = deepcopy(gate)
    new_gate["revision"] = int(gate["revision"]) + 1
    new_gate["previous_revision_ref"] = context["gate_ref"]
    new_gate["stage_plan_ref"] = f"{new_plan['id']}@{new_plan['revision']}"
    new_gate["status"] = "BLOCKED"
    new_gate["criteria_results"] = deepcopy(criteria_results)
    if strict_approval:
        new_gate["outcome_results"] = deepcopy(approval.get("outcome_results") or [])
        new_gate["hard_constraint_results"] = deepcopy(approval.get("hard_constraint_results") or [])
        new_gate["profile_control_results"] = deepcopy(approval.get("profile_control_results") or [])
        new_gate["permitted_use"] = deepcopy(approval.get("permitted_use") or new_gate.get("permitted_use") or {})
    new_gate["critical_blocker_refs"] = list(dict.fromkeys([str(ref) for ref in (gate.get("critical_blocker_refs") or [])] + [blocker_ref]))
    new_gate["base_revision"] = baseline_revision
    new_gate["evidence_diagnostics"] = {
        "formal_review_ref": blocker["formal_review_ref"],
        "failed_or_missing_items": diagnostics,
        "candidate_evidence_refs": [str(item["ref"]) for item in candidates],
    }
    new_gate["updated_at"] = now
    validate_stage_gate({"stage_gate": new_gate})
    gate_rel = Path(_next_revision_path(".harness/stages/GATES", str(gate["id"]), int(new_gate["revision"])))
    plan_index["current"][str(plan["id"])] = plan_rel.as_posix()
    gate_index["current"][str(gate["id"])] = gate_rel.as_posix()

    state_doc = load_data(root / STAGE_STATE_PATH)
    implementation = state_doc["implementation"]
    implementation["revision"] = int(implementation["revision"]) + 1
    implementation["updated_at"] = now
    validate_stage_state(state_doc)

    project_state_path = Path(".harness/state/CURRENT_STATE.yaml")
    project_state_doc = load_data(root / project_state_path)
    project_state = project_state_doc["state"]
    project_state["project_status"] = "BLOCKED"
    project_state["current_task_ref"] = None
    project_state["active_run"] = None
    project_state["next_route"] = "RESOLVE_STAGE_GATE"
    project_state["handoff_status"] = "STAGE_GATE_BLOCKED"
    project_state.setdefault("open_blocker_refs", [])
    if blocker_ref not in project_state["open_blocker_refs"]:
        project_state["open_blocker_refs"].append(blocker_ref)
    project_state["updated_at"] = now

    writes: dict[Path, Any] = {
        plan_rel: {"stage_plan": new_plan},
        gate_rel: {"stage_gate": new_gate},
        STAGE_PLAN_INDEX_PATH: plan_index_doc,
        STAGE_GATE_INDEX_PATH: gate_index_doc,
        STAGE_STATE_PATH: state_doc,
        Path(f".harness/stages/STATE_HISTORY/STAGE_STATE@{implementation['revision']}.yaml"): state_doc,
        blocker_rel: {"blocker": blocker},
        project_state_path: project_state_doc,
        Path(".harness/state/NEXT_TASK.yaml"): {
            "next_task": {
                "status": "BLOCKED",
                "task_ref": None,
                "run_ref": None,
                "active_stage": level,
                "stage_plan_ref": f"{new_plan['id']}@{new_plan['revision']}",
                "gate_ref": f"{new_gate['id']}@{new_gate['revision']}",
                "blocker_ref": blocker_ref,
                "blocker_kind": "STAGE_GATE_BLOCKER",
                "next_route": "RESOLVE_STAGE_GATE",
            }
        },
    }
    planned_result = {
        "status": "BLOCKED",
        "accepted_levels": [],
        "acceptance_refs": [],
        "highest_accepted_level": implementation.get("highest_accepted_level"),
        "active_stage": level,
        "target_level": implementation.get("target_level"),
        "next_route": "RESOLVE_STAGE_GATE",
        "stage_plan_ref": f"{new_plan['id']}@{new_plan['revision']}",
        "gate_ref": f"{new_gate['id']}@{new_gate['revision']}",
        "blocker_ref": blocker_ref,
        "failed_or_missing_items": diagnostics,
        "acceptance_created": False,
        "transaction_ref": transaction_id,
    }
    committed = _transactional_write(
        root,
        writes,
        transaction_id=transaction_id,
        operation_kind="ACCEPT_STAGE",
        request_digest=request_digest,
        result=planned_result,
    )
    return _render_committed_stage_transition(
        root,
        committed,
        regeneration_route="run resume-stage-gate after resolving the exact Gate evidence gaps",
    )


@guarded_mutation
def accept_stage(root: Path, level: str, approval_path: Path) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    if level not in canonical_levels():
        raise ValidationFailure("Stage level is not canonical", level)
    approval, approval_envelope = _approval_payload(approval_path, envelope_candidates=("stage_approval", "approval"))
    strict_markers = {"schema_version", "schema_ref", "record_kind", "record_state"}
    strict_approval = is_strict_stage_approval(approval)
    if strict_markers.intersection(approval) and not strict_approval:
        raise ValidationFailure("Stage approval contains strict-schema markers but does not identify the supported schema", {"schema_version": approval.get("schema_version"), "schema_ref": approval.get("schema_ref")})
    if strict_approval:
        raw_document = load_data(native_resolve(approval_path.expanduser()))
        if approval_envelope != "stage_approval":
            raise ValidationFailure("Strict Stage approval requires the exact stage_approval envelope")
        approval = validate_stage_approval_document(raw_document)
    _formal_approval(approval, expected_level=level)
    method = str(approval.get("acceptance_method") or "EXECUTED_STAGE_WORK")
    if method not in {"EXECUTED_STAGE_WORK", "SATISFIED_BY_BASELINE"}:
        raise ValidationFailure("Unknown stage acceptance_method", method)

    resolved_assessment: dict[str, Any] | None = None
    if method == "SATISFIED_BY_BASELINE":
        resolved_assessment = _resolve_exact_maturity_assessment(
            root,
            approval.get("assessment_ref"),
            approval.get("assessment_digest"),
        )

    transaction_id = f"STX-{approval['id'].removeprefix('DEC-')}"
    request_digest = stage_transaction_digest(
        {"operation_kind": "ACCEPT_STAGE", "level": level, "approval": approval}
    )
    recover_stage_transactions(root)
    existing = committed_stage_transaction_result(
        root,
        transaction_id=transaction_id,
        operation_kind="ACCEPT_STAGE",
        request_digest=request_digest,
    )
    if existing is not None:
        return _render_committed_stage_transition(
            root,
            existing,
            regeneration_route="repeat the identical accept-stage command",
        )
    state_path, state_doc = _load_stage_state(root)
    state = state_doc["implementation"]
    # PH-F06: a baseline disposition is a Stage transition too. It must not
    # supersede Tasks or clear the Run pointer of an open maintenance route.
    from .maintenance import active_maintenance
    if active_maintenance(root) is not None:
        raise ValidationFailure("Stage acceptance is blocked while same-level maintenance work remains open")
    current_active = state["active_stage"]
    strict_details: dict[str, Any] | None = None
    if strict_approval:
        strict_details = _validate_strict_stage_approval_binding(root, approval)

    if method == "EXECUTED_STAGE_WORK" and level != current_active:
        raise ValidationFailure("Executed-stage acceptance must target active_stage", {"active": current_active, "requested": level})
    accepted_input: dict[str, Any] | None = None
    if method == "SATISFIED_BY_BASELINE":
        accepted_input = load_data(root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml")
        project_mode = str(deep_get(accepted_input, "project.mode", "")).upper()
        if project_mode not in {"BROWNFIELD", "HYBRID"}:
            raise ValidationFailure(
                "SATISFIED_BY_BASELINE is restricted to Brownfield/Hybrid assessment",
                project_mode or None,
            )
    accepted = state["highest_accepted_level"]
    expected_next = next_level(str(accepted)) if accepted not in {"NONE", "UNKNOWN"} else "PROTOTYPE"
    if method == "SATISFIED_BY_BASELINE":
        if expected_next is None:
            return {"status": "NO_ACTION", "highest_accepted_level": accepted, "requested_level": level}
        if level_ordinal(level) < level_ordinal(str(expected_next)):
            return {"status": "NO_ACTION", "highest_accepted_level": accepted, "requested_level": level}
        if resolved_assessment is None:  # Defensive: baseline requests are resolved before recovery/mutation.
            raise ValidationFailure("Baseline acceptance requires exact assessment_ref and assessment_digest")

    path = state["stage_path"]
    start_level = expected_next
    if start_level not in path or level not in path:
        raise ValidationFailure(
            "Requested Stage is outside the current sequential Stage path",
            {"start": start_level, "requested": level, "stage_path": path},
        )
    start_index = path.index(start_level)
    end_index = path.index(level)
    if end_index < start_index:
        return {"status": "NO_ACTION", "highest_accepted_level": accepted, "requested_level": level}
    levels_to_accept = path[start_index : end_index + 1]
    if method == "EXECUTED_STAGE_WORK" and levels_to_accept != [level]:
        raise ValidationFailure("Executed stage acceptance cannot skip levels", levels_to_accept)

    baseline_revision = _product_baseline_revision(root)
    supplied_baseline = approval.get("baseline_revision")
    if method == "SATISFIED_BY_BASELINE":
        assert resolved_assessment is not None
        assert accepted_input is not None
        issues, assessment_context, current_context = _baseline_assessment_context_issues(
            resolved_assessment["assessment"],
            approval,
            current_repository_revision=baseline_revision,
            state=state,
            accepted_claimed_level=deep_get(accepted_input, "implementation.claimed_current_level"),
            requested_level=level,
            levels_to_accept=levels_to_accept,
        )
        if issues:
            stale_record = _record_assessment_staleness(
                root,
                resolved_assessment,
                issues=issues,
                assessment_context=assessment_context,
                current_context=current_context,
            )
            return {
                "status": "STALE",
                "message": "Brownfield baseline assessment is not bound to the current acceptance context.",
                "reason_codes": list(dict.fromkeys(str(item["code"]) for item in issues)),
                "issues": issues,
                "assessment_ref": resolved_assessment["assessment_ref"],
                "assessment_digest": resolved_assessment["assessment_digest"],
                "assessment_context": assessment_context,
                "current_context": current_context,
                "staleness_record_ref": stale_record["assessment_ref"],
                "staleness_record_path": str(stale_record["assessment_path"]),
                "staleness_record_digest": stale_record["assessment_digest"],
                "acceptance_mutation": {
                    "decision_created": False,
                    "acceptance_reports_created": [],
                    "stage_revisions_created": [],
                    "highest_accepted_level_changed": False,
                    "active_stage_changed": False,
                },
            }
    elif supplied_baseline != baseline_revision:
        raise ValidationFailure("Approval baseline_revision does not match current product tree", {"expected": baseline_revision, "supplied": supplied_baseline})

    plan_index = _load_index(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index")
    gate_index = _load_index(root, STAGE_GATE_INDEX_PATH, "stage_gate_index")
    writes: dict[Path, Any] = {}
    created_acceptance_refs: list[str] = []
    now = utc_now()
    last_level = accepted
    plan_index_new = deepcopy(plan_index)
    gate_index_new = deepcopy(gate_index)

    # A Brownfield baseline disposition replaces any prepared-but-unexecuted atomic
    # route for the stages being accepted. Preserve the old revisions as history,
    # but make their current revisions explicitly SUPERSEDED so future-stage fences
    # cannot mistake them for executable work after the atomic Stage transition.
    if method == "SATISFIED_BY_BASELINE":
        accepted_stage_set = set(levels_to_accept)
        task_index_path = Path(".harness/tasks/INDEX.yaml")
        if (_native_io_path(root / task_index_path)).exists():
            task_index_doc = load_data(root / task_index_path)
            task_index = task_index_doc.get("task_index") or {}
            task_index_changed = False
            for task_id, rel in list((task_index.get("current") or {}).items()):
                task = load_data(root / rel).get("task") or {}
                if task.get("implementation_stage") not in accepted_stage_set:
                    continue
                if task.get("status") in {"DONE", "SUPERSEDED", "CANCELLED"}:
                    continue
                revised = deepcopy(task)
                revised["revision"] = int(task.get("revision", 1)) + 1
                revised["previous_revision_ref"] = f"{task_id}@{task.get('revision', 1)}"
                revised["status"] = "SUPERSEDED"
                revised["superseded_reason"] = "SATISFIED_BY_BASELINE"
                revised["updated_at"] = now
                new_rel = Path(f".harness/tasks/{task_id}@{revised['revision']}.yaml")
                writes[new_rel] = {"task": revised}
                task_index.setdefault("current", {})[task_id] = new_rel.as_posix()
                task_index_changed = True
            if task_index_changed:
                writes[task_index_path] = task_index_doc

        wp_index_path = Path(".harness/work-packages/INDEX.yaml")
        if (_native_io_path(root / wp_index_path)).exists():
            wp_index_doc = load_data(root / wp_index_path)
            wp_index = wp_index_doc.get("work_package_index") or {}
            wp_index_changed = False
            for wp_id, rel in list((wp_index.get("current") or {}).items()):
                wp = load_data(root / rel).get("work_package") or {}
                if wp.get("implementation_stage") not in accepted_stage_set:
                    continue
                if wp.get("status") in {"COMPLETED", "SUPERSEDED", "CANCELLED"}:
                    continue
                revised = deepcopy(wp)
                revised["revision"] = int(wp.get("revision", 1)) + 1
                revised["previous_revision_ref"] = f"{wp_id}@{wp.get('revision', 1)}"
                revised["status"] = "SUPERSEDED"
                revised["superseded_reason"] = "SATISFIED_BY_BASELINE"
                revised["updated_at"] = now
                new_rel = Path(f".harness/work-packages/{wp_id}@{revised['revision']}.yaml")
                writes[new_rel] = {"work_package": revised}
                wp_index.setdefault("current", {})[wp_id] = new_rel.as_posix()
                wp_index_changed = True
            if wp_index_changed:
                writes[wp_index_path] = wp_index_doc

    for accepted_level in levels_to_accept:
        level_record = _approval_gate_data(approval, accepted_level)
        plan_id = plan_index["by_level"][accepted_level]
        gate_id = gate_index["by_level"][accepted_level]
        plan, _ = _current_entity(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index", plan_id, "stage_plan")
        gate, _ = _current_entity(root, STAGE_GATE_INDEX_PATH, "stage_gate_index", gate_id, "stage_gate")
        if method == "EXECUTED_STAGE_WORK":
            if plan.get("status") != "VERIFYING" or gate.get("status") != "VERIFYING":
                raise ValidationFailure(
                    "Executed-stage acceptance requires a VERIFYING Stage Plan and Gate",
                    {"level": accepted_level, "plan_status": plan.get("status"), "gate_status": gate.get("status")},
                )
            complete, incomplete = _all_required_work_packages_complete(root, gate.get("required_work_package_refs") or [])
            if not complete:
                raise ValidationFailure("Required Work Packages are incomplete", incomplete)
        if gate.get("critical_blocker_refs"):
            raise ValidationFailure("Stage Gate has critical blockers", gate.get("critical_blocker_refs"))
        supplied_results = _strict_combined_criterion_results(level_record) if strict_approval else level_record.get("criteria_results")
        criteria_results = _normalize_criterion_results(
            accepted_level,
            supplied_results,
            overrides=gate.get("hard_constraint_overrides") or [],
            require_closure=False,
        )
        permitted_use = level_record.get("permitted_use")
        if not isinstance(permitted_use, dict) or not all(
            key in permitted_use for key in ("users", "environments", "data_classes", "data_constraints")
        ):
            raise ValidationFailure("Approval permitted_use boundary is incomplete", accepted_level)
        permitted_use = deepcopy(permitted_use)
        known_limitations = level_record.get("known_limitations")
        next_stage_gaps = level_record.get("next_stage_gaps")
        if not isinstance(known_limitations, list) or not isinstance(next_stage_gaps, list):
            raise ValidationFailure("Approval requires known_limitations and next_stage_gaps arrays", accepted_level)
        # Validate every claimed PASS/global evidence binding before deciding
        # whether this review accepts or honestly blocks the Gate.  Dangling,
        # stale, wrong-kind, or wrong-subject refs remain validation failures
        # with no state mutation.
        _validate_open_review_evidence(
            root,
            level=accepted_level,
            criteria_results=criteria_results,
            global_evidence_refs=level_record.get("evidence_refs") or [],
            baseline_revision=baseline_revision,
            overrides=gate.get("hard_constraint_overrides") or [],
        )
        if strict_approval:
            if strict_details is None:
                raise ValidationFailure("Strict Stage approval context was not validated")
            # Outcome/profile-control evidence is validated against the strict
            # approval contract before mutation. The v0.5.0 Gate persistence
            # contract records only criterion/hard-constraint closing evidence;
            # treating auxiliary refs as global Gate evidence would make the
            # accepted Gate fail its own recorded-evidence validator.
            _validate_strict_auxiliary_result_evidence(
                root,
                approval=level_record,
                details=strict_details,
                baseline_revision=baseline_revision,
            )
        unclosed_items = _unclosed_review_items(
            approval=level_record,
            criteria_results=criteria_results,
            strict_approval=strict_approval,
        )
        if unclosed_items:
            if method != "EXECUTED_STAGE_WORK" or levels_to_accept != [accepted_level]:
                raise ValidationFailure(
                    "Only the current executed Stage Gate can persist an honest BLOCKED formal review",
                    {"method": method, "levels": levels_to_accept, "unclosed_items": unclosed_items},
                )
            return _persist_stage_gate_blocked(
                root,
                level=accepted_level,
                approval=level_record,
                transaction_id=transaction_id,
                request_digest=request_digest,
                baseline_revision=baseline_revision,
                plan=plan,
                gate=gate,
                criteria_results=criteria_results,
                unclosed_items=unclosed_items,
                strict_approval=strict_approval,
                strict_details=strict_details,
            )

        permitted_use["status"] = "CONFIRMED"
        evidence_bindings = validate_gate_evidence_closure(
            root,
            level=accepted_level,
            criteria_results=criteria_results,
            global_evidence_refs=level_record.get("evidence_refs") or [],
            base_revision=baseline_revision,
            overrides=gate.get("hard_constraint_overrides") or [],
        )
        evidence_refs = [item["ref"] for item in evidence_bindings]

        new_plan = deepcopy(plan)
        new_plan["revision"] = int(plan["revision"]) + 1
        new_plan["previous_revision_ref"] = f"{plan['id']}@{plan['revision']}"
        new_plan["status"] = "ACCEPTED"
        new_plan["updated_at"] = now
        plan_rel = Path(_next_revision_path(".harness/stages/PLANS", plan_id, new_plan["revision"]))
        writes[plan_rel] = {"stage_plan": new_plan}
        plan_index_new["current"][plan_id] = plan_rel.as_posix()

        new_gate = deepcopy(gate)
        new_gate["revision"] = int(gate["revision"]) + 1
        new_gate["previous_revision_ref"] = f"{gate['id']}@{gate['revision']}"
        new_gate["stage_plan_ref"] = f"{new_plan['id']}@{new_plan['revision']}"
        new_gate["status"] = "ACCEPTED"
        new_gate["criteria_results"] = criteria_results
        if strict_approval:
            new_gate["outcome_results"] = deepcopy(level_record.get("outcome_results") or [])
            new_gate["hard_constraint_results"] = deepcopy(level_record.get("hard_constraint_results") or [])
            new_gate["profile_control_results"] = deepcopy(level_record.get("profile_control_results") or [])
        new_gate["permitted_use"] = permitted_use
        new_gate["evidence_refs"] = evidence_refs
        new_gate["evidence_bindings"] = deepcopy(evidence_bindings)
        new_gate["base_revision"] = baseline_revision
        new_gate["updated_at"] = now
        validate_stage_gate({"stage_gate": new_gate}, require_closure=True)
        gate_rel = Path(_next_revision_path(".harness/stages/GATES", gate_id, new_gate["revision"]))
        writes[gate_rel] = {"stage_gate": new_gate}
        gate_index_new["current"][gate_id] = gate_rel.as_posix()

        acceptance_id = _acceptance_id(id_token(load_data(root / ".harness/config/PROJECT.yaml")["project"]["id_token"]), accepted_level)
        # id_token is idempotent for an already-normalized project token.
        acceptance_rel = Path(f".harness/stages/ACCEPTANCE/{acceptance_id}@1.yaml")
        if (_native_io_path(root / acceptance_rel)).exists() or acceptance_rel in writes:
            raise ValidationFailure("Stage Acceptance Report already exists", acceptance_id)
        report = {
            "id": acceptance_id,
            "revision": 1,
            "level": accepted_level,
            "status": "PASS",
            "acceptance_method": method,
            "baseline_revision": baseline_revision,
            "accepted_at": approval["approved_at"],
            "accepted_by": approval["actor"],
            "decision_ref": f"{approval['id']}@1",
            "stage_plan_ref": f"{new_plan['id']}@{new_plan['revision']}",
            "gate_ref": f"{new_gate['id']}@{new_gate['revision']}",
            "assessment_ref": resolved_assessment["assessment_ref"] if resolved_assessment is not None else None,
            "evidence_refs": evidence_refs,
            "evidence_bindings": deepcopy(evidence_bindings),
            "permitted_use": permitted_use,
            "known_limitations": deepcopy(known_limitations),
            "next_stage_gaps": deepcopy(next_stage_gaps),
        }
        validate_stage_acceptance({"stage_acceptance": report})
        writes[acceptance_rel] = {"stage_acceptance": report}
        created_acceptance_refs.append(f"{acceptance_id}@1")
        last_level = accepted_level

    target = state["target_level"]
    reached = level_ordinal(str(last_level)) >= level_ordinal(str(target))
    next_active = str(last_level) if reached else str(next_level(str(last_level)))
    if not reached:
        next_plan_id = plan_index["by_level"][next_active]
        next_gate_id = gate_index["by_level"][next_active]
        next_plan, _ = _current_entity(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index", next_plan_id, "stage_plan")
        next_gate, _ = _current_entity(root, STAGE_GATE_INDEX_PATH, "stage_gate_index", next_gate_id, "stage_gate")
        activated_plan = deepcopy(next_plan)
        activated_plan["revision"] = int(next_plan["revision"]) + 1
        activated_plan["previous_revision_ref"] = f"{next_plan['id']}@{next_plan['revision']}"
        activated_plan["status"] = "ACTIVE"
        activated_plan["review_required"] = True
        activated_plan["detailed_work_package_refs"] = []
        activated_plan["updated_at"] = now
        next_plan_rel = Path(_next_revision_path(".harness/stages/PLANS", next_plan_id, activated_plan["revision"]))
        writes[next_plan_rel] = {"stage_plan": activated_plan}
        plan_index_new["current"][next_plan_id] = next_plan_rel.as_posix()

        activated_gate = deepcopy(next_gate)
        activated_gate["revision"] = int(next_gate["revision"]) + 1
        activated_gate["previous_revision_ref"] = f"{next_gate['id']}@{next_gate['revision']}"
        activated_gate["stage_plan_ref"] = f"{activated_plan['id']}@{activated_plan['revision']}"
        activated_gate["status"] = "ACTIVE"
        activated_gate["updated_at"] = now
        next_gate_rel = Path(_next_revision_path(".harness/stages/GATES", next_gate_id, activated_gate["revision"]))
        writes[next_gate_rel] = {"stage_gate": activated_gate}
        gate_index_new["current"][next_gate_id] = next_gate_rel.as_posix()

    new_state_doc = deepcopy(state_doc)
    new_state = new_state_doc["implementation"]
    new_state["highest_accepted_level"] = last_level
    new_state["active_stage"] = next_active
    new_state["last_acceptance_ref"] = created_acceptance_refs[-1]
    new_state["permitted_use"] = deepcopy(_approval_gate_data(approval, str(last_level))["permitted_use"])
    new_state["permitted_use"]["status"] = "CONFIRMED"
    new_state["revision"] = int(state["revision"]) + 1
    new_state["updated_at"] = now
    validate_stage_state(new_state_doc)
    writes[STAGE_STATE_PATH] = new_state_doc
    writes[Path(f".harness/stages/STATE_HISTORY/STAGE_STATE@{new_state['revision']}.yaml")] = new_state_doc
    writes[STAGE_PLAN_INDEX_PATH] = {"stage_plan_index": plan_index_new}
    writes[STAGE_GATE_INDEX_PATH] = {"stage_gate_index": gate_index_new}
    decision_rel = Path(f".harness/canonical/DECISIONS/{approval['id']}@1.yaml")
    if (_native_io_path(root / decision_rel)).exists():
        raise ValidationFailure("Approval decision already exists", approval["id"])
    writes[decision_rel] = {
        "decision": {
            "id": approval["id"],
            "revision": 1,
            "kind": "STAGE_ACCEPTANCE",
            "subject_ref": created_acceptance_refs[-1],
            "approved": True,
            "actor": approval["actor"],
            "approved_at": approval["approved_at"],
            "notes": approval.get("notes"),
            "status": "ACCEPTED",
        }
    }

    project_state_path = Path(".harness/state/CURRENT_STATE.yaml")
    project_state_doc = load_data(root / project_state_path)
    project_state = project_state_doc.get("state") or {}
    project_state["project_status"] = "TARGET_LEVEL_REACHED" if reached else "ACTIVE"
    project_state["active_stage"] = next_active
    project_state["target_implementation_level"] = target
    project_state["current_task_ref"] = None
    project_state["active_run"] = None
    project_state["next_route"] = "TARGET_ALREADY_REACHED" if reached else "PLAN_ACTIVE_STAGE"
    project_state["handoff_status"] = "TARGET_LEVEL_REACHED" if reached else "STAGE_TRANSITION_REVIEW"
    project_state["updated_at"] = now
    writes[project_state_path] = project_state_doc
    writes[Path(".harness/state/NEXT_TASK.yaml")] = {
        "next_task": {
            "status": "TARGET_LEVEL_REACHED" if reached else "STAGE_PLANNING_REQUIRED",
            "task_ref": None,
            "run_ref": None,
            "active_stage": next_active,
            "next_route": project_state["next_route"],
        }
    }
    planned_result = {
        "status": "TARGET_LEVEL_REACHED" if reached else "ACCEPTED",
        "accepted_levels": levels_to_accept,
        "acceptance_refs": created_acceptance_refs,
        "highest_accepted_level": last_level,
        "active_stage": next_active,
        "target_level": target,
        "next_route": project_state["next_route"],
        "transaction_ref": transaction_id,
    }
    committed_result = _transactional_write(
        root,
        writes,
        transaction_id=transaction_id,
        operation_kind="ACCEPT_STAGE",
        request_digest=request_digest,
        result=planned_result,
    )
    return _render_committed_stage_transition(
        root,
        committed_result,
        regeneration_route="repeat the identical accept-stage command",
    )



def _current_stage_gate_context(root: Path) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    state = load_stage_state(root)
    target = load_current_target_level(root, stage_state=state)
    active = str(state["active_stage"])
    plan_index = _load_index(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index")
    gate_index = _load_index(root, STAGE_GATE_INDEX_PATH, "stage_gate_index")
    plan_id = (plan_index.get("by_level") or {}).get(active)
    gate_id = (gate_index.get("by_level") or {}).get(active)
    if not plan_id or not gate_id:
        raise ValidationFailure("Active Stage Plan/Gate is not indexed", {"active_stage": active})
    plan, plan_rel = _current_entity(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index", str(plan_id), "stage_plan")
    gate, gate_rel = _current_entity(root, STAGE_GATE_INDEX_PATH, "stage_gate_index", str(gate_id), "stage_gate")
    plan_ref = f"{plan['id']}@{plan['revision']}"
    gate_ref = f"{gate['id']}@{gate['revision']}"
    if gate.get("stage_plan_ref") != plan_ref:
        raise ValidationFailure("Current Stage Gate is not bound to the exact current Stage Plan revision", {"expected": plan_ref, "actual": gate.get("stage_plan_ref")})
    raw_plan_gate = str(plan.get("gate_ref") or "")
    if raw_plan_gate.split("@", 1)[0] != str(gate["id"]):
        raise ValidationFailure("Current Stage Plan points to another Gate id", {"stage_plan_ref": plan_ref, "gate_ref": raw_plan_gate})
    return {
        "root": root, "state": state, "target_level": target, "active_stage": active,
        "plan": plan, "plan_path": plan_rel, "plan_ref": plan_ref,
        "plan_digest": f"sha256:{sha256_file(root / plan_rel)}",
        "gate": gate, "gate_path": gate_rel, "gate_ref": gate_ref,
        "gate_digest": f"sha256:{sha256_file(root / gate_rel)}",
        "baseline_revision": product_baseline_revision(root),
    }


def _last_acceptance_context(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    ref = state.get("last_acceptance_ref")
    if not ref:
        return {"ref": None, "path": None, "baseline_revision": None}
    relative = f".harness/stages/ACCEPTANCE/{ref}.yaml"
    path = root / relative
    if not _native_io_path(path).is_file():
        raise ValidationFailure("Last Stage Acceptance Report is missing", {"ref": ref, "path": relative})
    value = load_data(path)
    report = value.get("stage_acceptance") if isinstance(value, dict) else None
    if not isinstance(report, dict):
        raise ValidationFailure("Last Stage Acceptance Report envelope is invalid", relative)
    internal_ref = f"{report.get('id')}@{report.get('revision')}"
    if internal_ref != ref:
        raise ValidationFailure("Last Stage Acceptance Report ref does not match Stage State", {"expected": ref, "actual": internal_ref})
    return {"ref": str(ref), "path": relative, "baseline_revision": report.get("baseline_revision")}


def _current_work_package_views(root: Path, refs: Iterable[Any]) -> list[dict[str, Any]]:
    index: dict[str, Any] = {}
    index_path = root / ".harness/work-packages/INDEX.yaml"
    if _native_io_path(index_path).is_file():
        value = load_data(index_path)
        index = value.get("work_package_index") if isinstance(value, dict) else {}
        if not isinstance(index, dict):
            index = {}
    current = index.get("current") or {}
    views: list[dict[str, Any]] = []
    for raw_ref in refs:
        requested_ref = str(raw_ref)
        entity_id = requested_ref.split("@", 1)[0]
        relative = current.get(entity_id)
        if not relative or not (_native_io_path(root / str(relative))).is_file():
            views.append({"requested_ref": requested_ref, "current_ref": None, "path": None, "status": "MISSING"})
            continue
        value = load_data(root / str(relative))
        body = value.get("work_package") if isinstance(value, dict) else None
        if not isinstance(body, dict):
            views.append({"requested_ref": requested_ref, "current_ref": None, "path": str(relative), "status": "INVALID"})
            continue
        views.append({"requested_ref": requested_ref, "current_ref": f"{body.get('id')}@{body.get('revision')}", "path": str(relative), "status": str(body.get("status") or "UNKNOWN")})
    return views


def _current_blocker_views(root: Path, refs: Iterable[Any]) -> list[dict[str, Any]]:
    blocker_dir = root / ".harness/blockers"
    views: list[dict[str, Any]] = []
    for raw_ref in refs:
        requested_ref = str(raw_ref)
        entity_id = requested_ref.split("@", 1)[0]
        candidates: list[tuple[int, Path]] = []
        if _native_io_path(blocker_dir).is_dir():
            for path in native_glob(blocker_dir,f'{entity_id}@*.yaml'):
                match = re.fullmatch(re.escape(entity_id) + r"@([1-9][0-9]*)\.yaml", path.name)
                if match and _native_io_path(path).is_file() and not _native_io_path(path).is_symlink():
                    candidates.append((int(match.group(1)), path))
        if not candidates:
            views.append({"requested_ref": requested_ref, "current_ref": None, "path": None, "status": "MISSING", "kind": None, "reason": None})
            continue
        _, path = max(candidates, key=lambda item: item[0])
        value = load_data(path)
        body = value.get("blocker") if isinstance(value, dict) else None
        if not isinstance(body, dict):
            views.append({"requested_ref": requested_ref, "current_ref": None, "path": path.relative_to(root).as_posix(), "status": "INVALID", "kind": None, "reason": None})
            continue
        views.append({
            "requested_ref": requested_ref, "current_ref": f"{body.get('id')}@{body.get('revision')}",
            "path": path.relative_to(root).as_posix(), "status": str(body.get("status") or "UNKNOWN"),
            "kind": str(body.get("kind")) if body.get("kind") is not None else None,
            "reason": str(body.get("reason")) if body.get("reason") is not None else None,
        })
    return views


def _stage_contract_definitions(context: dict[str, Any]) -> dict[str, Any]:
    level = str(context["active_stage"])
    plan = context["plan"]
    gate = context["gate"]
    model = _model()
    outcomes = [{"outcome_ref": str(ref), "mandatory": True, "applicability": "ALWAYS"} for ref in (plan.get("required_outcomes") or [])]
    criteria: list[dict[str, Any]] = []
    for ref in _criteria_for_level(level):
        raw = (model.get("criteria") or {}).get(ref)
        if not isinstance(raw, dict):
            raise ValidationFailure("Implementation level criterion is missing", ref)
        criteria.append({
            "criterion_ref": ref, "dimension": str(raw.get("dimension")), "description": str(raw.get("description")),
            "mandatory": bool(raw.get("mandatory")), "applicability": str(raw.get("applicability")),
            "required_evidence_kinds": [str(item) for item in (raw.get("required_evidence_kinds") or [])],
            "execution_evidence_required": bool(raw.get("execution_evidence_required")),
        })
    hard_constraints = [{
        "constraint_ref": str(item.get("key")), "statement": str(item.get("statement")),
        "source_ref": str(item.get("source_ref")) if item.get("source_ref") is not None else None,
        "mandatory": bool(item.get("mandatory", True)),
        "required_evidence_kinds": [str(kind) for kind in (item.get("required_evidence_kinds") or [])],
    } for item in (gate.get("hard_constraint_overrides") or []) if isinstance(item, dict)]
    controls = [{"control_ref": str(ref), "mandatory": True, "applicability": "ALWAYS", "source": "stage_gate.profile_control_refs"}
                for ref in (gate.get("profile_control_refs") or []) if nonempty(ref)]
    expected = [item["criterion_ref"] for item in criteria] + [item["constraint_ref"] for item in hard_constraints]
    actual = [str(item.get("criterion_ref")) for item in (gate.get("criteria_results") or []) if isinstance(item, dict)]
    if actual != expected:
        raise ValidationFailure("Current Gate result set differs from the exact level/hard-constraint contract", {"expected": expected, "actual": actual, "gate_ref": context["gate_ref"]})
    return {"required_outcomes": outcomes, "level_criteria": criteria, "hard_constraints": hard_constraints, "profile_controls": controls}


def _unknown_result(ref_field: str, ref: str) -> dict[str, Any]:
    return {ref_field: ref, "status": "UNKNOWN", "evidence_refs": [], "rationale": None, "validator": None}


def _semantic_candidate_ok(root: Path, body: dict[str, Any], subject: str) -> bool:
    try:
        validate_semantic_gate_proof(root, body, subject_ref=subject)
        return True
    except ValidationFailure:
        return False


def _evidence_candidate_views(context: dict[str, Any], definitions: dict[str, Any]) -> list[dict[str, Any]]:
    root = context["root"]
    requirements = gate_subject_requirements(root, str(context["active_stage"]), context["gate"].get("hard_constraint_overrides") or [])
    outcomes = {item["outcome_ref"] for item in definitions["required_outcomes"]}
    controls = {item["control_ref"] for item in definitions["profile_controls"]}
    baseline = str(context["baseline_revision"])
    directory = root / ".harness/evidence"
    result: list[dict[str, Any]] = []
    if not _native_io_path(directory).is_dir():
        return result
    for path in sorted(native_glob(directory,'EVD-*.yaml'), key=lambda item: item.name):
        try:
            resolved = resolve_evidence_artifact(root, path.stem, verify_sources=True)
        except ValidationFailure:
            continue
        body = resolved["body"]
        if body.get("status") != "PASS" or body.get("base_revision") != baseline or body.get("kind") == "USER_CLAIM":
            continue
        compatible: set[str] = set()
        for subject, kinds in requirements.items():
            if subject in (body.get("criterion_refs") or []) and body.get("kind") in kinds:
                compatible.add(subject)
        compatible.update(outcomes.intersection(str(item) for item in (body.get("outcome_refs") or [])))
        compatible.update(controls.intersection(str(item) for item in (body.get("profile_control_refs") or [])))
        compatible = {subject for subject in compatible if _semantic_candidate_ok(root, body, subject)}
        if not compatible:
            continue
        provenance = body.get("provenance") or {}
        source_bindings = [{
            "ref": str(binding.get("ref")), "sha256": str(binding.get("sha256")),
            "path": str(binding.get("path")) if binding.get("path") is not None else None,
            "media_type": str(binding.get("media_type")) if binding.get("media_type") is not None else None,
        } for binding in (body.get("source_bindings") or [])]
        result.append({
            "ref": str(resolved["ref"]), "path": str(resolved["path"]), "sha256": str(resolved["sha256"]),
            "kind": str(body.get("kind")), "status": str(body.get("status")), "base_revision": str(body.get("base_revision")),
            "provenance": {"source_type": str(provenance.get("source_type")), "source_ref": str(provenance.get("source_ref")),
                "producer": str(provenance.get("producer")), "actor": str(provenance.get("actor")) if provenance.get("actor") is not None else None,
                "tool_version": str(provenance.get("tool_version")) if provenance.get("tool_version") is not None else None},
            "source_bindings": source_bindings, "criterion_refs": [str(item) for item in (body.get("criterion_refs") or [])],
            "outcome_refs": [str(item) for item in (body.get("outcome_refs") or [])],
            "profile_control_refs": [str(item) for item in (body.get("profile_control_refs") or [])],
            "compatible_subject_refs": sorted(compatible),
        })
    return sorted(result, key=lambda item: item["ref"])


def _unresolved_stage_gaps(definitions: dict[str, Any], candidates: list[dict[str, Any]], work_packages: list[dict[str, Any]], blockers: list[dict[str, Any]], permitted_use: dict[str, Any]) -> list[dict[str, Any]]:
    by_subject: dict[str, list[str]] = {}
    for candidate in candidates:
        for subject in candidate["compatible_subject_refs"]:
            by_subject.setdefault(subject, []).append(candidate["ref"])
    gaps: list[dict[str, Any]] = []
    def add(kind: str, ref: str, required: list[str]) -> None:
        refs = sorted(by_subject.get(ref) or [])
        gaps.append({"gap_kind": kind, "subject_ref": ref, "status": "UNKNOWN", "required_evidence_kinds": list(required), "candidate_refs": refs,
            "message": "Formal result is UNKNOWN; review compatible evidence and record an explicit conclusion." if refs else "Formal result is UNKNOWN and no compatible current-baseline evidence candidate was found."})
    for item in definitions["required_outcomes"]: add("OUTCOME", item["outcome_ref"], [])
    for item in definitions["level_criteria"]: add("LEVEL_CRITERION", item["criterion_ref"], item["required_evidence_kinds"])
    for item in definitions["hard_constraints"]: add("HARD_CONSTRAINT", item["constraint_ref"], item["required_evidence_kinds"])
    for item in definitions["profile_controls"]: add("PROFILE_CONTROL", item["control_ref"], [])
    for item in work_packages:
        if item["status"] != "COMPLETED":
            gaps.append({"gap_kind": "WORK_PACKAGE", "subject_ref": item["requested_ref"], "status": item["status"], "required_evidence_kinds": [], "candidate_refs": [], "message": "Required Work Package is not currently COMPLETED."})
    for item in blockers:
        if item["status"] not in {"RESOLVED", "CLOSED", "SUPERSEDED"}:
            gaps.append({"gap_kind": "CRITICAL_BLOCKER", "subject_ref": item["requested_ref"], "status": item["status"], "required_evidence_kinds": [], "candidate_refs": [], "message": "Critical blocker is not resolved."})
    if permitted_use.get("status") != "CONFIRMED":
        gaps.append({"gap_kind": "PERMITTED_USE", "subject_ref": "PERMITTED_USE", "status": str(permitted_use.get("status") or "UNKNOWN"), "required_evidence_kinds": ["PERMITTED_USE_RECORD"], "candidate_refs": [], "message": "Permitted-use boundary requires explicit formal confirmation."})
    return gaps


def _preparation_binding_payload(context: dict[str, Any], definitions: dict[str, Any], work_packages: list[dict[str, Any]], blockers: list[dict[str, Any]], last_acceptance: dict[str, Any]) -> dict[str, Any]:
    return {
        "level": context["active_stage"], "target_level": context["target_level"],
        "stage_plan_ref": context["plan_ref"], "stage_plan_path": context["plan_path"], "stage_plan_revision": context["plan"]["revision"],
        "stage_plan_digest": context["plan_digest"], "stage_plan_status": context["plan"].get("status"),
        "gate_ref": context["gate_ref"], "gate_path": context["gate_path"], "gate_revision": context["gate"]["revision"],
        "gate_digest": context["gate_digest"], "gate_status": context["gate"].get("status"), "gate_base_revision": context["gate"].get("base_revision"),
        "baseline_revision": context["baseline_revision"], "last_acceptance": last_acceptance,
        "required_outcomes": definitions["required_outcomes"], "level_criteria": definitions["level_criteria"],
        "hard_constraints": definitions["hard_constraints"], "profile_controls": definitions["profile_controls"],
        "required_work_packages": work_packages, "critical_blockers": blockers,
    }


def _preparation_fingerprint(payload: dict[str, Any]) -> str:
    return f"sha256:{hashlib.sha256(canonical_json_bytes(payload)).hexdigest()}"


def _build_stage_approval_draft(root: Path, *, require_preparable: bool = True) -> tuple[dict[str, Any], dict[str, Any]]:
    context = _current_stage_gate_context(root)
    plan_status = str(context["plan"].get("status")); gate_status = str(context["gate"].get("status"))
    if require_preparable and not (plan_status in {"VERIFYING", "BLOCKED"} and gate_status in {"VERIFYING", "BLOCKED"}):
        raise ValidationFailure("Stage approval preparation requires the current active Stage to be VERIFYING or Gate-related BLOCKED", {"active_stage": context["active_stage"], "stage_plan_status": plan_status, "gate_status": gate_status})
    definitions = _stage_contract_definitions(context)
    work_packages = _current_work_package_views(context["root"], context["gate"].get("required_work_package_refs") or [])
    blockers = _current_blocker_views(context["root"], context["gate"].get("critical_blocker_refs") or [])
    last_acceptance = _last_acceptance_context(context["root"], context["state"])
    candidates = _evidence_candidate_views(context, definitions)
    permitted_use = deepcopy(context["gate"].get("permitted_use") or {})
    fingerprint_payload = _preparation_binding_payload(context, definitions, work_packages, blockers, last_acceptance)
    body = {
        "schema_version": 1, "schema_ref": "SCHEMA-STAGE-APPROVAL@1", "record_kind": "STAGE_APPROVAL", "record_state": "DRAFT",
        "id": None, "approved": False, "actor": None, "approved_at": None,
        "level": context["active_stage"], "target_level": context["target_level"], "acceptance_method": "EXECUTED_STAGE_WORK",
        "stage_plan_ref": context["plan_ref"], "stage_plan_path": context["plan_path"], "stage_plan_revision": int(context["plan"]["revision"]),
        "stage_plan_digest": context["plan_digest"], "prepared_from_stage_plan_status": plan_status,
        "gate_ref": context["gate_ref"], "gate_path": context["gate_path"], "gate_revision": int(context["gate"]["revision"]),
        "gate_digest": context["gate_digest"], "prepared_from_gate_status": gate_status, "gate_base_revision": str(context["gate"].get("base_revision")),
        "baseline_revision": context["baseline_revision"], "last_acceptance_ref": last_acceptance["ref"], "last_acceptance_path": last_acceptance["path"],
        "last_accepted_baseline_revision": last_acceptance["baseline_revision"], "assessment_ref": None, "assessment_digest": None,
        "required_outcomes": definitions["required_outcomes"],
        "outcome_results": [_unknown_result("outcome_ref", item["outcome_ref"]) for item in definitions["required_outcomes"]],
        "level_criteria": definitions["level_criteria"],
        "criteria_results": [_unknown_result("criterion_ref", item["criterion_ref"]) for item in definitions["level_criteria"]],
        "hard_constraints": definitions["hard_constraints"],
        "hard_constraint_results": [_unknown_result("constraint_ref", item["constraint_ref"]) for item in definitions["hard_constraints"]],
        "profile_controls": definitions["profile_controls"],
        "profile_control_results": [_unknown_result("control_ref", item["control_ref"]) for item in definitions["profile_controls"]],
        "required_work_packages": work_packages, "critical_blockers": blockers, "permitted_use": permitted_use,
        "evidence_candidates": candidates, "unresolved_gaps": _unresolved_stage_gaps(definitions, candidates, work_packages, blockers, permitted_use),
        "evidence_refs": [], "known_limitations": [], "next_stage_gaps": [], "notes": None,
        "preparation_fingerprint": _preparation_fingerprint(fingerprint_payload),
    }
    document = {"stage_approval": body}
    validate_stage_approval_document(document)
    return document, {"context": context, "definitions": definitions, "work_packages": work_packages, "blockers": blockers, "last_acceptance": last_acceptance, "fingerprint_payload": fingerprint_payload}


def _safe_stage_approval_output(root: Path, output_path: Path) -> Path:
    root = native_resolve(root.expanduser())
    raw = output_path.expanduser()
    if not raw.is_absolute(): raw = Path.cwd() / raw
    output = native_resolve(raw.parent) / raw.name
    if output == root or not output.name:
        raise ValidationFailure("Stage approval output must be a file path", str(output))
    try: relative = output.relative_to(root)
    except ValueError: return output
    allowed = Path(".harness/operator/APPROVALS")
    if relative == allowed or allowed not in relative.parents:
        raise ValidationFailure("Stage approval output inside the project is restricted to .harness/operator/APPROVALS", {"output": str(output), "allowed_root": str(root / allowed)})
    return output


@guarded_mutation
def prepare_stage_approval(root: Path, output_path: Path, *, force: bool = False) -> dict[str, Any]:
    """Write one deterministic, not-approved exact-bound operator draft."""
    root = native_resolve(root.expanduser()); output = _safe_stage_approval_output(root, output_path)
    if _native_io_path(output).is_symlink() or _native_io_path(output).is_dir():
        raise ValidationFailure("Stage approval output is not a replaceable regular file", str(output))
    if _native_io_path(output).exists() and not force:
        raise ValidationFailure("Stage approval output already exists; use --force to replace it explicitly", str(output))
    document, _ = _build_stage_approval_draft(root, require_preparable=True)
    write_data(output, document)
    body = document["stage_approval"]
    return {"status": "DRAFT_PREPARED", "approval_path": str(output), "approved": False,
        "level": body["level"], "target_level": body["target_level"], "stage_plan_ref": body["stage_plan_ref"],
        "gate_ref": body["gate_ref"], "gate_digest": body["gate_digest"], "baseline_revision": body["baseline_revision"],
        "result_counts": {"outcomes": len(body["outcome_results"]), "level_criteria": len(body["criteria_results"]), "hard_constraints": len(body["hard_constraint_results"]), "profile_controls": len(body["profile_control_results"])},
        "evidence_candidate_count": len(body["evidence_candidates"]), "unresolved_gap_count": len(body["unresolved_gaps"]),
        "preparation_fingerprint": body["preparation_fingerprint"],
        "next_route": "complete formal fields/results/evidence, set record_state=APPROVED and approved=true, then run accept-stage"}


def _status_counts(values: Iterable[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in values:
        status = str(item.get("status") if isinstance(item, dict) else "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def runtime_continuation(
    root: Path,
    project_state: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Describe a *real* v0.5.0 CLI continuation for the persisted route.

    This is read-only and shared by `next`, `stage-status`, and the project
    validator.  It must never promote an arbitrary empty-task boundary into
    STAGE_PLANNING_REQUIRED (that would conceal an unreachable runtime state).
    """
    route = project_state.get("next_route")
    status = project_state.get("project_status")
    task_ref = project_state.get("current_task_ref")
    run = project_state.get("active_run")
    from .maintenance import active_maintenance
    maintenance = active_maintenance(root)

    def operation(name: str, command: str | None, reason: str, **extra: Any) -> dict[str, Any]:
        return {"route": name, "command": command, "reason": reason, **extra}

    if status == "BLOCKED":
        if route == "RESOLVE_STAGE_GATE":
            return operation("RESUME_STAGE_GATE", "project-harness resume-stage-gate --project <root>",
                             "Revalidate the persisted Stage Gate blocker; missing semantic evidence still requires real proof.")
        if route == "RESOLVE_BLOCKER_OR_CHANGE_SCOPE":
            return operation("RESUME_BLOCKED_TASK", "project-harness resume --project <root> --resolution <recorded-resolution>",
                             "An OPEN ordinary Task blocker requires an operator's documented resolution before resuming.",
                             external_prerequisite="Resolve the recorded Task blocker without changing accepted scope.")
        if route == "RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN":
            return operation("EXTERNAL_SAFETY_RECOVERY", None,
                             "No in-place resume is permitted after a protected control-plane safety violation.",
                             external_prerequisite="Operator restores a trusted handoff/backup or restarts the Run under a trusted state; validate-project is diagnostic only.")
        return operation("INVALID_RUNTIME_ROUTE", None, "BLOCKED has no supported Task/Gate/safety recovery route.")

    if status == "TARGET_LEVEL_REACHED":
        current = context or _current_stage_gate_context(root)
        if (route != "TARGET_ALREADY_REACHED" or
                current["state"]["highest_accepted_level"] != current["target_level"] or
                current["plan"].get("status") != "ACCEPTED" or current["gate"].get("status") != "ACCEPTED"):
            return operation("INVALID_RUNTIME_ROUTE", None, "Target-reached Stage/Gate/accepted level/route are inconsistent.")
        if next_level(current["state"]["highest_accepted_level"]) is None:
            return operation("TARGET_ALREADY_REACHED", None,
                             "RELEASE is the highest canonical implementation level. No level-up is possible; same-level maintenance remains optional.",
                             optional_command="project-harness start-maintenance --project <root> --plan <approved-record>")
        return operation("TARGET_ALREADY_REACHED",
                         "project-harness level-up --project <root> --target <higher-level> --approval <formal-record>",
                         "Current target has been formally accepted. Further implementation requires a new formal level-up; same-level maintenance is separate.",
                         optional_command="project-harness start-maintenance --project <root> --plan <approved-record>")

    if status != "ACTIVE":
        return operation("INVALID_RUNTIME_ROUTE", None, "Project execution status has no runnable v0.5.0 route.")

    if task_ref is not None:
        if isinstance(run, dict):
            # The existing signed Run journal distinguishes an automatic Run
            # from the manual external Codex continuation. Never direct an
            # in-flight automatic Run to host-based `verify`.
            from .runtime import automatic_run_phase
            automatic = automatic_run_phase(root, run)
            if automatic is not None and automatic["phase"] != "AUTO_VERIFIED":
                return operation("AUTOMATIC_RUN_IN_PROGRESS", "project-harness status --project <root>",
                                 "Existing automatic Run must not be executed or host-verified twice.",
                                 external_prerequisite="In-flight process or PH-051-10 orphan/recovery inspection after host interruption.",
                                 run_status=automatic["status"])
            if route == "COMPLETE_TASK":
                return operation("COMPLETE_VERIFIED_TASK", "project-harness complete --project <root> --result <exact-active-run-result-path>",
                                 "Only a PASS-verified active Run can be completed; supply its exact Agent Task Result.")
            if route in {"EXECUTE_CURRENT_TASK_WITH_CODEX", "PROVIDE_MANUAL_VERIFICATION", "FIX_TASK_OR_BLOCK"}:
                if route == "EXECUTE_CURRENT_TASK_WITH_CODEX":
                    try:
                        policy = load_data(root / ".harness/config/PROJECT_LOCK.yaml")["project_lock"].get("execution") or {}
                    except (OSError, ValueError, KeyError, TypeError):
                        policy = {}
                    if policy.get("mode") == "LOCAL_AUTOMATIC":
                        return operation("EXECUTE_LOCAL_AUTOMATIC", "project-harness execute-current --project <root>",
                                         "Current READY JIT may execute only through a successful project rootless Podman doctor; manual execution is never an automatic fallback.",
                                         prerequisite_command="project-harness executor-doctor --project <root>")
                    reason = "Execute the current JIT with external Codex, then run independent verification."
                else:
                    reason = "Supply the required manual proof or correct the Task, then re-run independent verification; use block if a safe resolution is unavailable."
                return operation("VERIFY_CURRENT_TASK", "project-harness verify --project <root> --allow-command-execution", reason,
                                 external_prerequisite="External agent implementation / documented manual verification" if route != "EXECUTE_CURRENT_TASK_WITH_CODEX" else "External agent implementation")
            return operation("INVALID_RUNTIME_ROUTE", None, "Active Run has no supported verification/completion route.")
        if route in {"COMPILE_FIRST_READY_TASK", "COMPILE_NEXT_READY_TASK", "COMPILE_RESUMED_TASK", "STAGE_ACCEPTANCE_PREPARATION", "MAINTAIN_CURRENT_STAGE"}:
            return operation("RESERVE_READY_TASK", "project-harness next --project <root>",
                             "Compile or replay only the current executable-stage READY Task/JIT.",
                             maintenance_route="MAINTAIN_CURRENT_STAGE" if maintenance else None)
        return operation("INVALID_RUNTIME_ROUTE", None, "Current Task has no supported READY/JIT continuation route.")

    if run is not None:
        return operation("INVALID_RUNTIME_ROUTE", None, "An active Run cannot exist without the current Task.")
    if maintenance is not None:
        return operation("INVALID_RUNTIME_ROUTE", None, "Open maintenance requires a current executable Task.")

    if route == "PLAN_ACTIVE_STAGE":
        current = context or _current_stage_gate_context(root)
        if (current["plan"].get("status") != "ACTIVE" or current["gate"].get("status") != "ACTIVE" or
                not current["plan"].get("review_required") or current["plan"].get("detailed_work_package_refs") or
                current["gate"].get("required_work_package_refs") or
                current["gate"].get("critical_blocker_refs") or
                next_level(current["state"]["highest_accepted_level"]) != current["active_stage"]):
            return operation("INVALID_RUNTIME_ROUTE", None, "Active Stage planning boundary is inconsistent with its Plan/Gate/accepted predecessor.")
        return operation("PREPARE_ACTIVE_STAGE_PLAN",
                         "project-harness prepare-active-stage-plan --project <root> --output <reviewed-record-path>",
                         "Prepare an exact-bound read-only draft, review the current-stage work, then apply it using plan-active-stage --project <root> --plan <reviewed-record-path>.",
                         follow_up_command="project-harness plan-active-stage --project <root> --plan <reviewed-record-path>")
    if route == "STAGE_GATE_REVIEW":
        current = context or _current_stage_gate_context(root)
        if current["plan"].get("status") != "VERIFYING" or current["gate"].get("status") != "VERIFYING":
            return operation("INVALID_RUNTIME_ROUTE", None, "Formal Stage review requires matching VERIFYING Plan/Gate.")
        return operation("PREPARE_STAGE_APPROVAL",
                         "project-harness prepare-stage-approval --project <root> --output <outside-root-or-.harness/operator/APPROVALS/file.yaml>",
                         "Gate is VERIFYING; operator must supply semantic proof and a separate formal acceptance decision.",
                         follow_up_command="project-harness accept-stage --project <root> --level <active-stage> --approval <approved-record>")
    if route == "EVALUATE_STAGE_GATE_READINESS":
        current = context or _current_stage_gate_context(root)
        if current["plan"].get("status") != "ACTIVE" or current["gate"].get("status") != "ACTIVE":
            return operation("INVALID_RUNTIME_ROUTE", None, "Interrupted Gate-readiness evaluation requires an ACTIVE Plan/Gate.")
        return operation("RESUME_GATE_READINESS", "project-harness next --project <root>",
                         "Recover the persisted post-Task Gate-readiness evaluation; do not fabricate approval or evidence.")
    if route == "REVIEW_MATURITY_ASSESSMENT":
        current = context or _current_stage_gate_context(root)
        if current["plan"].get("status") != "ACTIVE" or current["gate"].get("status") != "ACTIVE":
            return operation("INVALID_RUNTIME_ROUTE", None, "Maturity review requires an unchanged ACTIVE Stage Plan/Gate.")
        return operation("REVIEW_MATURITY_ASSESSMENT", "project-harness assess-maturity --workspace <root>",
                         "A migrated completed baseline requires a read-only assessment and explicit governed review, not automatic maturity acceptance.",
                         external_prerequisite="Operator reviews observed execution evidence and supplies the applicable formal Stage/baseline acceptance or new executable work; assessment alone does not advance the runtime.")
    return operation("INVALID_RUNTIME_ROUTE", None, "Empty current Task has no supported nonterminal Stage boundary route.")


def stage_status(root: Path) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    state = load_stage_state(root)
    current_target = load_current_target_level(root, stage_state=state)
    project_state = load_data(root / ".harness/state/CURRENT_STATE.yaml").get("state") or {}
    plan_index = _load_index(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index")
    stages: list[dict[str, Any]] = []
    for level in state["stage_path"]:
        plan_id = (plan_index.get("by_level") or {}).get(level)
        if not plan_id:
            stages.append({"level": level, "status": "MISSING"}); continue
        plan, rel = _current_entity(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index", plan_id, "stage_plan")
        stages.append({"level": level, "status": plan.get("status"), "stage_plan_ref": f"{plan['id']}@{plan['revision']}", "stage_plan_path": rel,
            "detailed_work_package_count": len(plan.get("detailed_work_package_refs") or []), "review_required": bool(plan.get("review_required"))})
    current = _current_stage_gate_context(root)
    definitions = _stage_contract_definitions(current)
    work_packages = _current_work_package_views(root, current["gate"].get("required_work_package_refs") or [])
    blockers = _current_blocker_views(root, current["gate"].get("critical_blocker_refs") or [])
    gate_results = [item for item in (current["gate"].get("criteria_results") or []) if isinstance(item, dict)]
    level_refs = {item["criterion_ref"] for item in definitions["level_criteria"]}; hard_refs = {item["constraint_ref"] for item in definitions["hard_constraints"]}
    level_results = [item for item in gate_results if item.get("criterion_ref") in level_refs]
    hard_results = [item for item in gate_results if item.get("criterion_ref") in hard_refs]
    outcome_results = [item for item in (current["gate"].get("outcome_results") or []) if isinstance(item, dict)]
    if not outcome_results:
        outcome_results = [{"status": "UNKNOWN"} for _ in definitions["required_outcomes"]]
    profile_results = [item for item in (current["gate"].get("profile_control_results") or []) if isinstance(item, dict)]
    if not profile_results:
        profile_results = [{"status": "UNKNOWN"} for _ in definitions["profile_controls"]]
    plan_status = str(current["plan"].get("status")); gate_status = str(current["gate"].get("status"))
    route = runtime_continuation(root, project_state, context=current)
    from .maintenance import active_maintenance
    maintenance = active_maintenance(root)
    project_execution = project_state.get("project_status")
    persisted_route = project_state.get("next_route")
    if project_execution == "TARGET_LEVEL_REACHED":
        runtime_phase = "TARGET_LEVEL_REACHED"
    elif project_execution == "BLOCKED":
        runtime_phase = "STAGE_GATE_BLOCKED" if persisted_route == "RESOLVE_STAGE_GATE" else "TASK_BLOCKED"
    elif maintenance is not None:
        runtime_phase = "MAINTENANCE"
    elif persisted_route == "PLAN_ACTIVE_STAGE":
        runtime_phase = "STAGE_PLANNING_REQUIRED"
    elif persisted_route == "STAGE_GATE_REVIEW":
        runtime_phase = "VERIFYING"
    elif project_state.get("active_run"):
        runtime_phase = "READY_FOR_CODEX" if persisted_route == "EXECUTE_CURRENT_TASK_WITH_CODEX" else "TASK_VERIFICATION"
    elif project_state.get("current_task_ref"):
        runtime_phase = "READY"
    elif persisted_route == "REVIEW_MATURITY_ASSESSMENT":
        runtime_phase = "MATURITY_REVIEW_REQUIRED"
    else:
        runtime_phase = str(persisted_route or "INVALID_RUNTIME_ROUTE")
    return {
        "status": project_state.get("project_status"), "runtime_phase": runtime_phase,
        "maintenance_route": maintenance.get("maintenance_route") if maintenance else None, "target_level": current_target, "claimed_current_level": state["claimed_current_level"],
        "observed_candidate_level": state["observed_candidate_level"], "highest_accepted_level": state["highest_accepted_level"],
        "active_stage": state["active_stage"], "permitted_use": state.get("permitted_use"), "next_route": project_state.get("next_route"),
        "next_operator_route": route, "stage_plan_ref": current["plan_ref"], "stage_plan_path": current["plan_path"],
        "stage_plan_revision": current["plan"]["revision"], "stage_plan_status": plan_status, "gate_ref": current["gate_ref"],
        "gate_path": current["gate_path"], "gate_revision": current["gate"]["revision"], "gate_digest": current["gate_digest"],
        "gate_status": gate_status, "baseline_revision": current["baseline_revision"], "baseline_digest": current["baseline_revision"],
        "gate_counts": {
            "required_outcomes": {"total": len(definitions["required_outcomes"]), "by_status": _status_counts(outcome_results)},
            "level_criteria": {"total": len(level_results), "by_status": _status_counts(level_results)},
            "hard_constraints": {"total": len(hard_results), "by_status": _status_counts(hard_results)},
            "profile_controls": {"total": len(definitions["profile_controls"]), "by_status": _status_counts(profile_results)},
            "required_work_packages": {"total": len(work_packages), "by_status": _status_counts(work_packages)},
            "critical_blockers": {"total": len(blockers), "by_status": _status_counts(blockers)}},
        "required_work_packages": work_packages, "critical_blockers": blockers, "stages": stages,
        "validation": validate_stage_cross_references(root),
    }

def _repository_paths(repository: Path) -> list[str]:
    if not _native_io_path(repository).is_dir():
        return []
    paths: list[str] = []
    for path in tree_entries(
        repository,
        exclude_dirs={".git", ".harness", "node_modules", ".venv", "__pycache__", ".pytest_cache"},
    ):
        paths.append(path.relative_to(repository).as_posix())
    return paths


def _static_evidence_inventory(inventory: dict[str, Any], repository_paths: list[str]) -> dict[str, list[str]]:
    evidence: dict[str, list[str]] = {}

    def add(kind: str, path: str) -> None:
        evidence.setdefault(kind, [])
        if path not in evidence[kind]:
            evidence[kind].append(path)

    for path in repository_paths:
        lower = path.lower()
        name = Path(path).name.lower()
        suffix = Path(path).suffix.lower()
        if suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".swift", ".kt"}:
            add("REPOSITORY_ARTIFACT", path)
        if name in {"readme.md", "readme.rst", "readme.txt", "getting-started.md", "quickstart.md"}:
            add("START_INSTRUCTIONS", path)
            add("USER_DOCUMENTATION", path)
        if any(token in lower for token in ("architecture", "design", "adr/", "decisions/")):
            add("ARCHITECTURE_RECORD", path)
        if any(part in {"test", "tests", "spec", "specs", "__tests__"} for part in Path(lower).parts):
            add("TEST_SOURCE", path)
        if any(token in lower for token in ("junit", "test-report", "test_results", "coverage.xml", "coverage.json")):
            add("TEST_REPORT", path)
        if any(token in lower for token in ("migration", "migrations", "upgrade")):
            add("MIGRATION_RECORD", path)
        if any(token in lower for token in ("openapi", "swagger", "api-contract", "contracts/")):
            add("CONTRACT_RECORD", path)
        if any(token in lower for token in ("security", "threat-model", "privacy")):
            add("SECURITY_RECORD", path)
        if any(token in lower for token in ("deploy", "deployment", "helm", "compose", "dockerfile", "infra/", "terraform")):
            add("DEPLOYMENT_RECORD", path)
            add("CONFIGURATION", path)
        if any(token in lower for token in ("runbook", "operations", "operating")):
            add("OPERATIONS_RECORD", path)
        if any(token in lower for token in ("monitor", "observability", "alert")):
            add("MONITORING_EVIDENCE", path)
        if any(token in lower for token in ("backup", "restore", "recovery", "disaster")):
            add("RECOVERY_RECORD", path)
        if "rollback" in lower:
            add("ROLLBACK_RECORD", path)
        if any(token in lower for token in ("limitations", "known-issues", "known_issues")):
            add("LIMITATIONS_RECORD", path)
        if any(token in lower for token in ("permitted-use", "operating-boundary", "usage-boundary")):
            add("PERMITTED_USE_RECORD", path)
        if any(token in lower for token in ("support", "oncall", "escalation")):
            add("SUPPORT_RECORD", path)
        if any(token in lower for token in ("owners", "ownership", "codeowners")):
            add("OWNERSHIP_RECORD", path)
        if any(token in lower for token in ("retention", "data-lifecycle", "deletion-policy")):
            add("DATA_LIFECYCLE_RECORD", path)
        if any(token in lower for token in ("compatibility", "backward-compat")):
            add("COMPATIBILITY_RECORD", path)
        if any(token in lower for token in ("release-notes", "changelog", "release/")):
            add("RELEASE_RECORD", path)
        if name in {
            "pyproject.toml", "package.json", "go.mod", "cargo.toml", "pom.xml", "build.gradle",
            "makefile", "dockerfile", "requirements.txt",
        } or suffix in {".yaml", ".yml", ".toml", ".ini", ".cfg"}:
            add("CONFIGURATION", path)
    for marker in inventory.get("build_markers") or []:
        add("CONFIGURATION", str(marker))
        add("REPOSITORY_ARTIFACT", str(marker))
    for path in inventory.get("test_paths") or []:
        add("TEST_SOURCE", str(path))
    for path in inventory.get("documentation_paths") or []:
        add("USER_DOCUMENTATION", str(path))
    return {key: sorted(values) for key, values in evidence.items()}


def _external_evidence(
    path: Path | None,
    *,
    repository_revision: str,
    project_root: Path | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if path is None:
        return [], []
    source_path = native_resolve(path.expanduser())
    value = load_data(source_path)
    records = value.get("evidence") if isinstance(value, dict) else None
    if not isinstance(records, list):
        raise ValidationFailure("External maturity evidence must contain evidence array", str(path))
    registry_root = project_root if project_root is not None else source_path.parent
    registered_kinds = allowed_evidence_kinds(registry_root)
    source_digest = f"sha256:{sha256_file(source_path)}"
    source_ref = f"EXTERNAL-EVIDENCE-FILE:{source_digest}"
    # Check normalized records and all source proofs before the first import.
    # The compatibility path for legacy assessment records is unchanged; such
    # records are still not sufficient semantic proof for a positive Gate.
    preflight_ids: set[str] = set()
    for raw in records:
        if not isinstance(raw, dict):
            raise ValidationFailure("Evidence entry must be an object")
        evidence_id = str(raw.get("id"))
        if evidence_id in preflight_ids:
            raise ValidationFailure("External evidence file contains duplicate ids", evidence_id)
        preflight_ids.add(evidence_id)
        if "schema_version" in raw:
            if project_root is None:
                raise ValidationFailure("Normalized maturity evidence requires a prepared Project Instance for source resolution")
            body = validate_normalized_evidence_document(project_root, {"verification_evidence": raw}, verify_sources=True)
            if body["status"] == "NOT_APPLICABLE" and (
                not nonempty(body.get("rationale")) or not nonempty(body.get("validator"))
            ):
                raise ValidationFailure("NOT_APPLICABLE evidence requires rationale and validator", body["id"])
            if body["status"] == "PASS" and body["kind"] != "USER_CLAIM":
                for subject in body["criterion_refs"] + body["outcome_refs"] + body["profile_control_refs"]:
                    validate_semantic_gate_proof(project_root, body, subject_ref=subject)
            existing_path = project_root / f".harness/evidence/{body['id']}.yaml"
            if _native_io_path(existing_path).exists():
                existing = resolve_evidence_artifact(project_root, body["id"], verify_sources=True)
                if canonical_json_bytes(existing["body"]) != canonical_json_bytes(body):
                    raise ValidationFailure("Immutable evidence artifact already exists with different content", body["id"])
    normalized: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(records, 1):
        if not isinstance(raw, dict):
            raise ValidationFailure("Evidence entry must be an object", index)
        if "schema_version" in raw:
            if project_root is None:
                raise ValidationFailure("Normalized maturity evidence requires a prepared Project Instance for source resolution")
            body = validate_normalized_evidence_document(
                project_root, {"verification_evidence": raw}, verify_sources=True,
            )
            evidence_id = str(body["id"])
            if evidence_id in seen_ids:
                raise ValidationFailure("External evidence file contains duplicate ids", evidence_id)
            seen_ids.add(evidence_id)
            if body["status"] == "PASS" and body["kind"] != "USER_CLAIM":
                subjects = body["criterion_refs"] + body["outcome_refs"] + body["profile_control_refs"]
                for subject in subjects:
                    validate_semantic_gate_proof(project_root, body, subject_ref=subject)
            written = write_normalized_evidence(project_root, body)
            item = deepcopy(written["body"])
            if item["base_revision"] != repository_revision:
                warnings.append(f"{evidence_id}: STALE base_revision")
                item.update(status="UNKNOWN", stale=True)
            if item["kind"] == "USER_CLAIM" and item["status"] == "PASS":
                item.update(status="PARTIAL", rationale="USER_CLAIM cannot satisfy a mandatory maturity criterion.")
            normalized.append(item)
            continue
        required = ["id", "kind", "criterion_refs", "status", "provenance", "base_revision"]
        missing = [field for field in required if not nonempty(raw.get(field))]
        if missing:
            raise ValidationFailure("External evidence entry is incomplete", {"index": index, "missing": missing})
        evidence_id = str(raw["id"])
        if evidence_id in seen_ids:
            raise ValidationFailure("External evidence file contains duplicate ids", evidence_id)
        seen_ids.add(evidence_id)
        if raw.get("kind") not in registered_kinds:
            raise ValidationFailure("External evidence kind is not registered", raw.get("kind"))
        if raw.get("status") not in EVIDENCE_STATUSES:
            raise ValidationFailure("External evidence has invalid status", raw.get("status"))
        if not isinstance(raw.get("criterion_refs"), list) or not raw.get("criterion_refs"):
            raise ValidationFailure("External maturity evidence requires non-empty criterion_refs", evidence_id)

        item = deepcopy(raw)
        item.setdefault("outcome_refs", [])
        item.setdefault("profile_control_refs", [])
        item["ref"] = evidence_id
        if item.get("base_revision") != repository_revision:
            warnings.append(f"{evidence_id}: STALE base_revision")
            item["status"] = "UNKNOWN"
            item["stale"] = True
            item.setdefault("rationale", "Evidence base_revision does not match the assessed product tree.")
        if item.get("kind") == "USER_CLAIM" and item.get("status") == "PASS":
            item["status"] = "PARTIAL"
            item["rationale"] = "USER_CLAIM cannot satisfy a mandatory maturity criterion without corroborating evidence."
        if item.get("status") == "NOT_APPLICABLE" and (
            not nonempty(item.get("rationale")) or not nonempty(item.get("validator"))
        ):
            raise ValidationFailure("NOT_APPLICABLE evidence requires rationale and validator", evidence_id)

        if project_root is not None:
            existing_created_at: str | None = None
            existing_path = project_root / f".harness/evidence/{evidence_id}.yaml"
            if _native_io_path(existing_path).is_file():
                try:
                    existing_body = load_data(existing_path).get("verification_evidence") or {}
                    if existing_body.get("schema_version") == 1:
                        existing_created_at = existing_body.get("created_at")
                except Exception:
                    existing_created_at = None
            declared_provenance = deepcopy(raw.get("provenance"))
            provenance = {
                "source_type": "EXTERNAL_EVIDENCE_IMPORT",
                "source_ref": source_ref,
                "producer": "PROJECT_HARNESS_READ_ONLY_ASSESSOR",
                "details": {"declared_provenance": declared_provenance, "record_index": index},
            }
            body = normalized_evidence_body(
                evidence_id=evidence_id,
                kind=str(item["kind"]),
                status=str(item["status"]),
                provenance=provenance,
                base_revision=str(item["base_revision"]),
                criterion_refs=[str(ref) for ref in item.get("criterion_refs") or []],
                outcome_refs=[str(ref) for ref in item.get("outcome_refs") or []],
                profile_control_refs=[str(ref) for ref in item.get("profile_control_refs") or []],
                source_bindings=[{"ref": source_ref, "sha256": source_digest}],
                created_at=str(item.get("created_at") or existing_created_at or utc_now()),
                rationale=item.get("rationale"),
                validator=item.get("validator"),
                details={"imported_record_index": index, "stale": bool(item.get("stale"))},
            )
            written = write_normalized_evidence(project_root, body)
            item = deepcopy(written["body"])
            if body.get("details", {}).get("stale"):
                item["stale"] = True
        normalized.append(item)
    return normalized, warnings


def _criterion_assessment(
    criterion_ref: str,
    criterion: dict[str, Any],
    static_evidence: dict[str, list[str]],
    external: list[dict[str, Any]],
) -> dict[str, Any]:
    required = {str(item) for item in criterion.get("required_evidence_kinds") or []}
    subject_matches = [item for item in external if criterion_ref in (item.get("criterion_refs") or [])]
    matching_external = [item for item in subject_matches if item.get("kind") in required]
    wrong_kind = [item for item in subject_matches if item.get("kind") not in required]
    precedence = {"BLOCKED": 6, "FAIL": 5, "UNKNOWN": 4, "PARTIAL": 3, "NOT_APPLICABLE": 2, "PASS": 1}
    if matching_external:
        # A negative or uncertain exact-base record is never averaged away by positive records.
        selected = sorted(
            matching_external,
            key=lambda item: precedence.get(str(item.get("status")), 99),
            reverse=True,
        )[0]
        selected_status = "FAIL" if selected.get("status") == "BLOCKED" else selected.get("status")
        return {
            "criterion_ref": criterion_ref,
            "status": selected_status,
            "evidence_refs": sorted(str(item["id"]) for item in matching_external),
            "rationale": selected.get("rationale") or "External evidence with exact provenance, kind and baseline was supplied.",
            "validator": selected.get("validator"),
        }
    if wrong_kind:
        return {
            "criterion_ref": criterion_ref,
            "status": "UNKNOWN",
            "evidence_refs": [],
            "rationale": (
                "Supplied evidence maps this criterion but its semantic kind does not satisfy "
                f"required_evidence_kinds: {', '.join(sorted(required))}."
            ),
            "validator": "PROJECT_HARNESS_READ_ONLY_ASSESSOR",
            "rejected_evidence_refs": sorted(str(item["id"]) for item in wrong_kind),
        }
    available_refs: list[str] = []
    available_kinds: list[str] = []
    for kind in sorted(required):
        if static_evidence.get(kind):
            available_kinds.append(kind)
            available_refs.extend(static_evidence[kind][:20])
    if criterion.get("execution_evidence_required"):
        return {
            "criterion_ref": criterion_ref,
            "status": "UNKNOWN",
            "evidence_refs": sorted(set(available_refs)),
            "rationale": "Execution evidence is required, and v0.5.0 maturity assessment does not run commands automatically.",
            "validator": "PROJECT_HARNESS_READ_ONLY_ASSESSOR",
            "available_static_evidence_kinds": available_kinds,
        }
    if criterion.get("applicability") != "ALWAYS" and not available_refs:
        return {
            "criterion_ref": criterion_ref,
            "status": "UNKNOWN",
            "evidence_refs": [],
            "rationale": f"Applicability {criterion.get('applicability')} requires explicit project evidence or justified NOT_APPLICABLE.",
            "validator": "PROJECT_HARNESS_READ_ONLY_ASSESSOR",
        }
    if available_refs:
        return {
            "criterion_ref": criterion_ref,
            "status": "PASS",
            "evidence_refs": sorted(set(available_refs)),
            "rationale": f"Read-only repository evidence matches required kinds: {', '.join(available_kinds)}.",
            "validator": "PROJECT_HARNESS_READ_ONLY_ASSESSOR",
        }
    return {
        "criterion_ref": criterion_ref,
        "status": "UNKNOWN",
        "evidence_refs": [],
        "rationale": "Required evidence was not found in the read-only inventory or supplied evidence.",
        "validator": "PROJECT_HARNESS_READ_ONLY_ASSESSOR",
    }


def _observed_candidate(static: dict[str, list[str]], external: list[dict[str, Any]]) -> str:
    passed_refs = {
        ref
        for item in external
        if item.get("status") == "PASS"
        for ref in (item.get("criterion_refs") or [])
    }
    if static.get("RELEASE_RECORD") and static.get("OPERATIONS_RECORD") and any(ref.startswith("RELEASE_") for ref in passed_refs):
        return "RELEASE"
    if static.get("DEPLOYMENT_RECORD") and static.get("OPERATIONS_RECORD") and (
        static.get("SUPPORT_RECORD") or static.get("OWNERSHIP_RECORD")
    ):
        return "MVP"
    if static.get("TEST_SOURCE") and static.get("DEPLOYMENT_RECORD") and (
        static.get("MIGRATION_RECORD") or static.get("RECOVERY_RECORD")
    ):
        return "BETA"
    if static.get("TEST_SOURCE") and static.get("CONFIGURATION") and static.get("USER_DOCUMENTATION"):
        return "ALPHA"
    if static.get("REPOSITORY_ARTIFACT") or static.get("CONFIGURATION") or static.get("USER_DOCUMENTATION"):
        return "PROTOTYPE"
    return "NONE"


def _highest_satisfied(criteria_results: dict[str, list[dict[str, Any]]]) -> str:
    highest = "NONE"
    for level in canonical_levels():
        results = criteria_results[level]
        if all(item.get("status") in {"PASS", "NOT_APPLICABLE"} for item in results):
            highest = level
        else:
            break
    return highest


def _dimension_levels(criteria_results: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    model = _model()
    result = {dimension: "NONE" for dimension in model["dimensions"]}
    for level in canonical_levels():
        for item in criteria_results[level]:
            criterion = model["criteria"][item["criterion_ref"]]
            if item.get("status") in {"PASS", "NOT_APPLICABLE"}:
                result[criterion["dimension"]] = level
    return result


def _assessment_route(
    previous_accepted: str,
    target: str,
    observed: str,
    criteria_results: dict[str, list[dict[str, Any]]],
) -> str:
    if previous_accepted not in set(canonical_levels()):
        return "COMPLETE_CURRENT_STAGE"
    if level_ordinal(previous_accepted) >= level_ordinal(target):
        return "TARGET_ALREADY_REACHED"
    accepted_results = criteria_results.get(previous_accepted) or []
    if any(item.get("status") == "FAIL" for item in accepted_results):
        return "STABILIZE_CURRENT_STAGE"
    if any(item.get("status") in {"PARTIAL", "UNKNOWN"} for item in accepted_results) and level_ordinal(observed) <= level_ordinal(previous_accepted):
        return "MAINTAIN_CURRENT_STAGE"
    return "ADVANCE_TO_NEXT_STAGE"


@guarded_mutation
def assess_maturity(workspace: Path, *, evidence_path: Path | None = None) -> dict[str, Any]:
    workspace = native_resolve(workspace.expanduser())
    is_project = (_native_io_path(workspace / STAGE_STATE_PATH)).exists()
    stage_state: dict[str, Any] | None = None
    assessment_run: dict[str, Any] | None = None
    if is_project:
        recover_stage_transactions(workspace)
        from .maintenance import active_maintenance
        if active_maintenance(workspace) is not None:
            raise ValidationFailure("Maturity assessment is blocked while same-level maintenance work remains open")
        runtime = load_data(workspace / ".harness/state/CURRENT_STATE.yaml")["state"]
        active_run = runtime.get("active_run")
        # A clean, already reserved Run must remain usable after read-only
        # assessment. Never bless a pre-existing control-plane violation: only
        # a PASS preflight can receive the narrow trusted phase below.
        if isinstance(active_run, dict) and check_control_plane(workspace, active_run).get("status") == "PASS":
            assessment_run = deepcopy(active_run)
        accepted_input_path = workspace / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml"
        project_input = load_data(accepted_input_path)
        stage_state = load_stage_state(workspace)
        previous_accepted = stage_state["highest_accepted_level"]
        repository_revision = _product_baseline_revision(workspace)
        inventory = {
            "repository_revision": repository_revision,
            "tree_digest": repository_revision.removeprefix("tree:"),
            "build_markers": [],
            "test_paths": [],
            "documentation_paths": [],
        }
        repository = workspace
        token = load_data(workspace / ".harness/config/PROJECT.yaml")["project"]["id_token"]
    else:
        input_path = workspace / "PROJECT_INPUT.yaml"
        inventory_path = workspace / "REPOSITORY_INVENTORY.yaml"
        if not _native_io_path(input_path).exists() or not _native_io_path(inventory_path).exists():
            raise ValidationFailure("Maturity assessment requires a Brownfield/Hybrid intake workspace or prepared project")
        project_input = load_data(input_path)
        inventory_doc = load_data(inventory_path)
        inventory = inventory_doc.get("repository_inventory") or {}
        repository_revision = str(inventory.get("repository_revision") or inventory.get("tree_digest") or "UNKNOWN")
        state_doc = load_data(workspace / "STATE.yaml").get("state") or {}
        repository = Path(state_doc.get("effective_repository_path") or inventory.get("repository_path") or "")
        previous_accepted = "NONE"
        token = id_token(str(deep_get(project_input, "project.slug") or deep_get(project_input, "project.name") or "PROJECT"))

    mode = str(deep_get(project_input, "project.mode", "")).upper()
    if mode not in {"BROWNFIELD", "HYBRID"} and not is_project:
        raise ValidationFailure("Brownfield maturity assessment is only valid for BROWNFIELD/HYBRID intake")
    target = load_current_target_level(workspace, stage_state=stage_state)
    claimed = deep_get(project_input, "implementation.claimed_current_level")
    if claimed not in set(canonical_levels()) | {"UNKNOWN", "NONE"}:
        raise WaitingInput("claimed_current_level is required before maturity assessment")

    repository_paths = _repository_paths(repository)
    static = _static_evidence_inventory(inventory, repository_paths)
    external, warnings = _external_evidence(
        evidence_path,
        repository_revision=repository_revision,
        project_root=workspace if is_project else None,
    )
    model = _model()
    criteria_results: dict[str, list[dict[str, Any]]] = {}
    blocking_gaps: list[str] = []
    evidence_inventory = [
        {"kind": kind, "refs": refs[:100], "count": len(refs)}
        for kind, refs in sorted(static.items())
    ]
    evidence_inventory.extend(
        {
            "kind": str(item.get("kind")),
            "refs": [str(item.get("id"))],
            "count": 1,
            "provenance": item.get("provenance"),
            "status": item.get("status"),
            "base_revision": item.get("base_revision"),
            "criterion_refs": [str(ref) for ref in (item.get("criterion_refs") or [])],
            "stale": bool(item.get("stale")),
        }
        for item in external
    )
    for level in canonical_levels():
        results: list[dict[str, Any]] = []
        for ref in _criteria_for_level(level):
            item = _criterion_assessment(ref, model["criteria"][ref], static, external)
            results.append(item)
            if item["status"] not in {"PASS", "NOT_APPLICABLE"}:
                blocking_gaps.append(f"{ref}: {item['status']} — {item['rationale']}")
        criteria_results[level] = results
    observed = _observed_candidate(static, external)
    highest = _highest_satisfied(criteria_results)
    proposed_active = next_level(previous_accepted) if previous_accepted not in {"NONE", "UNKNOWN"} else "PROTOTYPE"
    if proposed_active is None:
        proposed_active = previous_accepted
    route = _assessment_route(str(previous_accepted), str(target), observed, criteria_results)
    confidence = "HIGH" if external and not warnings else ("MEDIUM" if static else "LOW")
    assessment_id = f"VAL-{token}-MATURITY-001"
    assessment = {
        "id": assessment_id,
        "revision": 1,
        "repository_revision": repository_revision,
        "base_tree_digest": inventory.get("tree_digest"),
        "claimed_current_level": claimed,
        "observed_candidate_level": observed,
        "highest_satisfied_candidate_level": highest,
        "previous_highest_accepted_level": previous_accepted,
        "proposed_active_stage": proposed_active,
        "target_level": target,
        "confidence": confidence,
        "criteria_results": criteria_results,
        "dimensions": _dimension_levels(criteria_results),
        "blocking_gaps": blocking_gaps,
        "recommended_route": route,
        "evidence_inventory": evidence_inventory,
        "automatic_command_execution": "FORBIDDEN",
        "status": "STALE" if warnings else "COMPLETED",
        "warnings": warnings,
        "created_at": utc_now(),
    }
    if route not in ASSESSMENT_ROUTES:
        raise ValidationFailure("Assessment route is invalid", route)
    if is_project:
        output = workspace / f".harness/stages/ASSESSMENTS/{assessment_id}@1.yaml"
        if _native_io_path(output).exists():
            # Immutable revision: allocate the next revision instead of overwriting.
            revisions = [
                int(path.stem.rsplit("@", 1)[1])
                for path in native_glob(output.parent,f'{assessment_id}@*.yaml')
                if "@" in path.stem and path.stem.rsplit("@", 1)[1].isdigit()
            ]
            assessment["revision"] = max(revisions, default=0) + 1
            output = workspace / f".harness/stages/ASSESSMENTS/{assessment_id}@{assessment['revision']}.yaml"
        write_data(output, {"maturity_assessment": assessment})
        state_path, stage_doc = _load_stage_state(workspace)
        stage_doc["implementation"]["observed_candidate_level"] = observed
        stage_doc["implementation"]["last_assessment_ref"] = f"{assessment_id}@{assessment['revision']}"
        stage_doc["implementation"]["revision"] += 1
        stage_doc["implementation"]["updated_at"] = utc_now()
        write_data(state_path, stage_doc)
        write_data(
            workspace / f".harness/stages/STATE_HISTORY/STAGE_STATE@{stage_doc['implementation']['revision']}.yaml",
            stage_doc,
        )
    else:
        output = workspace / "MATURITY_ASSESSMENT.yaml"
        write_data(output, {"maturity_assessment": assessment})
    if assessment_run is not None:
        expected_writes = {
            output.relative_to(workspace).as_posix(), STAGE_STATE_PATH.as_posix(),
            f".harness/stages/STATE_HISTORY/STAGE_STATE@{stage_doc['implementation']['revision']}.yaml",
            *(f".harness/evidence/{item['id']}.yaml" for item in external),
        }
        control = check_control_plane(workspace, assessment_run)
        unexpected = (set(control.get("changed") or []) | set(control.get("unexpected") or [])) - expected_writes
        if unexpected or control.get("deleted") or control.get("unsafe") or control.get("agent_result", {}).get("status") == "FAIL":
            raise SafetyViolation("Read-only assessment cannot seal unrelated control-plane changes", control)
        if _product_baseline_revision(workspace) != repository_revision:
            raise SafetyViolation("Product changed during read-only assessment; the assessment cannot refresh Run integrity")
        record_phase_boundary(
            workspace, assessment_run, phase="READ_ONLY_ASSESSMENT",
            kernel_written_paths=sorted(expected_writes), recorded_at=utc_now(),
        )
    return {
        "status": assessment["status"],
        "assessment_ref": f"{assessment_id}@{assessment['revision']}",
        "assessment_path": str(output),
        "assessment_digest": f"sha256:{sha256_file(output)}",
        "claimed_current_level": claimed,
        "observed_candidate_level": observed,
        "highest_satisfied_candidate_level": highest,
        "previous_highest_accepted_level": previous_accepted,
        "proposed_active_stage": proposed_active,
        "target_level": target,
        "confidence": confidence,
        "blocking_gaps": blocking_gaps,
        "recommended_route": route,
        "automatic_command_execution": False,
        "warnings": warnings,
    }


@guarded_mutation
def level_up(root: Path, target_level: str, approval_path: Path) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    if target_level not in canonical_levels():
        raise ValidationFailure("Level-up target is not canonical", target_level)
    approval, _ = _approval_payload(approval_path, envelope_candidates=("level_up_approval", "approval"))
    _formal_approval(approval, expected_target=target_level)
    transaction_id = f"STX-{approval['id'].removeprefix('DEC-')}"
    request_digest = stage_transaction_digest(
        {"operation_kind": "LEVEL_UP", "target_level": target_level, "approval": approval}
    )
    recover_stage_transactions(root)
    existing = committed_stage_transaction_result(
        root,
        transaction_id=transaction_id,
        operation_kind="LEVEL_UP",
        request_digest=request_digest,
    )
    if existing is not None:
        return _render_committed_stage_transition(
            root,
            existing,
            regeneration_route="repeat the identical level-up command",
        )
    state_path, state_doc = _load_stage_state(root)
    state = state_doc["implementation"]
    accepted = state["highest_accepted_level"]
    if accepted not in canonical_levels():
        raise ValidationFailure("Level-up requires an accepted implementation stage", accepted)
    if level_ordinal(target_level) > level_ordinal(accepted):
        wp_index_path = root / ".harness/work-packages/INDEX.yaml"
        if _native_io_path(wp_index_path).exists():
            wp_index = load_data(wp_index_path).get("work_package_index") or {}
            open_maintenance: list[str] = []
            for wp_id, rel in (wp_index.get("current") or {}).items():
                wp = load_data(root / rel).get("work_package") or {}
                if (
                    wp.get("maintenance_route") == "MAINTAIN_CURRENT_STAGE"
                    and wp.get("implementation_stage") == accepted
                    and wp.get("status") not in {"COMPLETED", "CANCELLED", "SUPERSEDED"}
                ):
                    open_maintenance.append(f"{wp_id}:{wp.get('status')}")
            if open_maintenance:
                raise ValidationFailure(
                    "Level-up is blocked while same-level maintenance work remains open",
                    open_maintenance,
                )
    if level_ordinal(target_level) <= level_ordinal(accepted):
        return {
            "status": "TARGET_ALREADY_REACHED",
            "highest_accepted_level": accepted,
            "requested_target": target_level,
            "changed": False,
        }
    old_target = state["target_level"]
    # A new target cycle starts only at an accepted target boundary. A second
    # decision must not reset an in-flight Stage/Gate/Run; exact replay returned
    # above and lower/equal targets already returned without mutation.
    project_runtime = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
    if (
        level_ordinal(accepted) < level_ordinal(old_target)
        or project_runtime.get("project_status") != "TARGET_LEVEL_REACHED"
        or project_runtime.get("next_route") != "TARGET_ALREADY_REACHED"
        or project_runtime.get("active_run") is not None
        or project_runtime.get("current_task_ref") is not None
    ):
        raise ValidationFailure(
            "Level-up requires the current target cycle to be fully accepted and idle",
            {"highest_accepted_level": accepted, "current_target": old_target,
             "project_status": project_runtime.get("project_status"),
             "next_route": project_runtime.get("next_route")},
        )
    old_path = list(state["stage_path"])
    new_path = stage_path(target_level)
    next_active = str(next_level(accepted))
    if not next_active:
        raise ValidationFailure("No next implementation stage exists", accepted)
    plan_index = _load_index(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index")
    gate_index = _load_index(root, STAGE_GATE_INDEX_PATH, "stage_gate_index")
    token = load_data(root / ".harness/config/PROJECT.yaml")["project"]["id_token"]
    accepted_input = load_data(root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml")
    baseline_ref = load_data(root / ".harness/config/PROJECT.yaml")["project"]["project_definition_ref"]
    scope_refs: list[str] = []
    requirements_dir = root / ".harness/canonical/REQUIREMENTS"
    for path in sorted(native_glob(requirements_dir,'REQ-*@*.yaml')):
        req = load_data(path).get("requirement") or {}
        if req.get("id") and req.get("revision"):
            scope_refs.append(f"{req['id']}@{req['revision']}")
    overrides = _hard_constraint_overrides(accepted_input)
    now = utc_now()
    writes: dict[Path, Any] = {}
    plan_index_new = deepcopy(plan_index)
    gate_index_new = deepcopy(gate_index)

    for level in new_path:
        plan_id = (plan_index_new.get("by_level") or {}).get(level)
        gate_id = (gate_index_new.get("by_level") or {}).get(level)
        desired_status = "ACTIVE" if level == next_active else ("ACCEPTED" if level_ordinal(level) <= level_ordinal(accepted) else "PLANNED")
        if plan_id:
            plan, _ = _current_entity(root, STAGE_PLAN_INDEX_PATH, "stage_plan_index", plan_id, "stage_plan")
            if level_ordinal(level) > level_ordinal(accepted):
                new_plan = deepcopy(plan)
                new_plan["revision"] = int(plan["revision"]) + 1
                new_plan["previous_revision_ref"] = f"{plan['id']}@{plan['revision']}"
                new_plan["status"] = desired_status
                new_plan["target_level"] = target_level
                new_plan["review_required"] = True
                new_plan["detailed_work_package_refs"] = []
                new_plan["deferred_to_next_stage"] = [
                    f"Recompute {next_level(level)} delta after {level} acceptance; do not precompile atomic work."
                ] if next_level(level) and next_level(level) in new_path else []
                new_plan["updated_at"] = now
                rel = Path(_next_revision_path(".harness/stages/PLANS", plan_id, new_plan["revision"]))
                writes[rel] = {"stage_plan": new_plan}
                plan_index_new["current"][plan_id] = rel.as_posix()
                gate, _ = _current_entity(root, STAGE_GATE_INDEX_PATH, "stage_gate_index", gate_id, "stage_gate")
                new_gate = deepcopy(gate)
                new_gate["revision"] = int(gate["revision"]) + 1
                new_gate["previous_revision_ref"] = f"{gate['id']}@{gate['revision']}"
                new_gate["stage_plan_ref"] = f"{new_plan['id']}@{new_plan['revision']}"
                new_gate["status"] = desired_status
                new_gate["updated_at"] = now
                grel = Path(_next_revision_path(".harness/stages/GATES", gate_id, new_gate["revision"]))
                writes[grel] = {"stage_gate": new_gate}
                gate_index_new["current"][gate_id] = grel.as_posix()
            continue

        plan_id = _plan_id(str(token), level)
        gate_id = _gate_id(str(token), level)
        plan = {
            "id": plan_id,
            "revision": 1,
            "level": level,
            "status": desired_status,
            "target_level": target_level,
            "baseline_ref": baseline_ref,
            "scope_refs": scope_refs,
            "required_outcomes": _outcomes_for_level(level),
            "criteria_profile_ref": f"REG-IMPLEMENTATION-LEVELS#{level}",
            "hard_constraint_overrides": deepcopy(overrides),
            "work_package_outlines": [{"title": f"{level} delta review", "outcome": f"Plan {level} from accepted {accepted} baseline"}],
            "deferred_to_next_stage": [
                f"Recompute {next_level(level)} delta after {level} acceptance; do not precompile atomic work."
            ] if next_level(level) and next_level(level) in new_path else [],
            "detailed_work_package_refs": [],
            "gate_ref": f"{gate_id}@1",
            "review_required": True,
            "created_at": now,
        }
        gate = {
            "id": gate_id,
            "revision": 1,
            "type": "STAGE_ACCEPTANCE",
            "level": level,
            "stage_plan_ref": f"{plan_id}@1",
            "status": desired_status,
            "criteria_results": [_criterion_result_template(ref) for ref in _criteria_for_level(level)]
                + [_criterion_result_template(item["key"]) for item in overrides],
            "required_work_package_refs": [],
            "critical_blocker_refs": [],
            "hard_constraint_overrides": deepcopy(overrides),
            "profile_control_refs": [deep_get(accepted_input, "profile.ref")],
            "evidence_refs": [],
            "base_revision": baseline_ref,
            "permitted_use": _default_permitted_use(level),
            "created_at": now,
        }
        prel = Path(f".harness/stages/PLANS/{plan_id}@1.yaml")
        grel = Path(f".harness/stages/GATES/{gate_id}@1.yaml")
        writes[prel] = {"stage_plan": plan}
        writes[grel] = {"stage_gate": gate}
        plan_index_new.setdefault("order", []).append(plan_id)
        plan_index_new.setdefault("by_level", {})[level] = plan_id
        plan_index_new.setdefault("current", {})[plan_id] = prel.as_posix()
        gate_index_new.setdefault("order", []).append(gate_id)
        gate_index_new.setdefault("by_level", {})[level] = gate_id
        gate_index_new.setdefault("current", {})[gate_id] = grel.as_posix()

    # Future prompt plans should normally be absent. Any present stale assumptions are superseded safely.
    prompt_index_updates: list[str] = []
    for path in sorted(native_glob(root / ".harness/prompts/PLANS",'PPL-*@*.yaml')):
        value = load_data(path)
        prompt = value.get("prompt_plan") if isinstance(value, dict) else None
        if not isinstance(prompt, dict):
            continue
        stage = prompt.get("implementation_stage")
        if stage and stage != next_active and prompt.get("status") != "STALE":
            revised = deepcopy(prompt)
            revised["revision"] = int(prompt.get("revision", 1)) + 1
            revised["status"] = "STALE"
            revised["stale_reason"] = "LEVEL_UP_REPLANNING"
            revised["previous_revision_ref"] = f"{prompt['id']}@{prompt.get('revision', 1)}"
            rel = Path(f".harness/prompts/PLANS/{prompt['id']}@{revised['revision']}.yaml")
            writes[rel] = {"prompt_plan": revised}
            prompt_index_updates.append(rel.as_posix())

    new_state_doc = deepcopy(state_doc)
    new_state = new_state_doc["implementation"]
    new_state["target_level"] = target_level
    new_state["active_stage"] = next_active
    new_state["stage_path"] = new_path
    new_state["revision"] = int(state["revision"]) + 1
    new_state["updated_at"] = now
    new_state["level_up_decision_ref"] = f"{approval['id']}@1"
    validate_stage_state(new_state_doc)
    writes[STAGE_STATE_PATH] = new_state_doc
    writes[Path(f".harness/stages/STATE_HISTORY/STAGE_STATE@{new_state['revision']}.yaml")] = new_state_doc
    writes[STAGE_PLAN_INDEX_PATH] = {"stage_plan_index": plan_index_new}
    writes[STAGE_GATE_INDEX_PATH] = {"stage_gate_index": gate_index_new}
    decision_rel = Path(f".harness/canonical/DECISIONS/{approval['id']}@1.yaml")
    if (_native_io_path(root / decision_rel)).exists():
        raise ValidationFailure("Level-up decision already exists", approval["id"])
    writes[decision_rel] = {
        "decision": {
            "id": approval["id"],
            "revision": 1,
            "kind": "IMPLEMENTATION_LEVEL_UP",
            "subject_ref": f"{accepted}->{target_level}",
            "approved": True,
            "actor": approval["actor"],
            "approved_at": approval["approved_at"],
            "notes": approval.get("rationale") or approval.get("notes"),
            "status": "ACCEPTED",
        }
    }
    project_config_path = Path(".harness/config/PROJECT.yaml")
    project_config_doc = load_data(root / project_config_path)
    project_config = project_config_doc.get("project") or {}
    project_config["target_implementation_level"] = target_level
    project_config["implementation_level_change_decision_ref"] = f"{approval['id']}@1"
    project_config["updated_at"] = now
    writes[project_config_path] = project_config_doc

    project_state_path = Path(".harness/state/CURRENT_STATE.yaml")
    project_state_doc = load_data(root / project_state_path)
    project_state = project_state_doc.get("state") or {}
    project_state["project_status"] = "ACTIVE"
    project_state["active_stage"] = next_active
    project_state["target_implementation_level"] = target_level
    project_state["current_task_ref"] = None
    project_state["active_run"] = None
    project_state["next_route"] = "PLAN_ACTIVE_STAGE"
    project_state["handoff_status"] = "LEVEL_UP_APPROVED"
    project_state["updated_at"] = now
    writes[project_state_path] = project_state_doc
    writes[Path(".harness/state/NEXT_TASK.yaml")] = {
        "next_task": {
            "status": "STAGE_PLANNING_REQUIRED",
            "task_ref": None,
            "run_ref": None,
            "active_stage": next_active,
            "next_route": "PLAN_ACTIVE_STAGE",
        }
    }
    planned_result = {
        "status": "ACTIVE",
        "old_target_level": old_target,
        "target_level": target_level,
        "highest_accepted_level": accepted,
        "active_stage": next_active,
        "stage_path": new_path,
        "historical_stage_path": old_path,
        "stale_prompt_plan_paths": prompt_index_updates,
        "next_route": "PLAN_ACTIVE_STAGE",
        "transaction_ref": transaction_id,
    }
    committed_result = _transactional_write(
        root,
        writes,
        transaction_id=transaction_id,
        operation_kind="LEVEL_UP",
        request_digest=request_digest,
        result=planned_result,
    )
    return _render_committed_stage_transition(
        root,
        committed_result,
        regeneration_route="repeat the identical level-up command",
    )


# Public Stage-planning Python API. Lazy delegation preserves maintenance/stage imports.
def prepare_active_stage_plan(root: Path, output_path: Path, *, force: bool = False) -> dict[str, Any]:
    from .active_stage_planning import prepare_active_stage_plan as prepare
    return prepare(root, output_path, force=force)


def plan_active_stage(root: Path, plan_path: Path) -> dict[str, Any]:
    from .active_stage_planning import plan_active_stage as apply
    return apply(root, plan_path)

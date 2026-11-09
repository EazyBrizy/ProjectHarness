from __future__ import annotations

"""Governed Stage-Gate readiness, evidence-preparation, and recovery routes.

This module deliberately stays inside the v0.5.0 Stage lifecycle.  It does not
plan same-level maintenance or future-stage product features.  Its only
executable route is the bounded ``STAGE_ACCEPTANCE_PREPARATION`` Work Package
used to close exact final-baseline Gate evidence gaps.
"""

from copy import deepcopy
from pathlib import Path
import hashlib
from typing import Any, Iterable

from .operation_guard import guarded_mutation
from .errors import ValidationFailure
from .evidence import gate_proof_methods, evidence_binding_view
from .hashing import sha256_bytes, sha256_file
from .prompting import reserve_run
from .serialization import canonical_json_bytes, load_data
from .stage_transactions import digest_value as stage_transaction_digest, recover_stage_transactions
from .stages import (
    STAGE_GATE_INDEX_PATH,
    STAGE_PLAN_INDEX_PATH,
    STAGE_STATE_PATH,
    _current_blocker_views,
    _current_stage_gate_context,
    _current_work_package_views,
    _evidence_candidate_views,
    _next_revision_path,
    _stage_contract_definitions,
    _transactional_write,
    product_baseline_revision,
    validate_stage_gate,
    validate_stage_plan,
    validate_stage_state,
)
from .util import utc_now

PREPARATION_KIND = "STAGE_ACCEPTANCE_PREPARATION"
GATE_BLOCKER_KIND = "STAGE_GATE_BLOCKER"
PREPARATION_ROUTE = "STAGE_ACCEPTANCE_PREPARATION"
GATE_REVIEW_ROUTE = "STAGE_GATE_REVIEW"
GATE_RECOVERY_ROUTE = "RESOLVE_STAGE_GATE"


def _short_digest(value: Any, length: int = 12) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()[:length].upper()


def _project_token(root: Path) -> str:
    value = load_data(root / ".harness/config/PROJECT.yaml")
    project = value.get("project") if isinstance(value, dict) else None
    token = project.get("id_token") if isinstance(project, dict) else None
    if not isinstance(token, str) or not token:
        raise ValidationFailure("Project id_token is missing")
    return token


def _current_entity_doc(root: Path, index_path: Path, envelope: str, entity_id: str) -> tuple[dict[str, Any], str]:
    value = load_data(root / index_path)
    index = value.get(envelope + "_index") if isinstance(value, dict) else None
    if not isinstance(index, dict):
        raise ValidationFailure(f"{envelope} index envelope is invalid", str(index_path))
    relative = (index.get("current") or {}).get(entity_id)
    if not isinstance(relative, str):
        raise ValidationFailure(f"Current {envelope} path is absent", entity_id)
    document = load_data(root / relative)
    body = document.get(envelope) if isinstance(document, dict) else None
    if not isinstance(body, dict):
        raise ValidationFailure(f"Current {envelope} envelope is invalid", relative)
    return body, relative


def _subject_candidates(candidates: Iterable[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for candidate in candidates:
        ref = str(candidate.get("ref") or "")
        for subject in candidate.get("compatible_subject_refs") or []:
            result.setdefault(str(subject), []).append(ref)
    return {key: sorted(set(value)) for key, value in result.items()}


def missing_gate_evidence_items(root: Path) -> dict[str, Any]:
    """Return exact mandatory Gate subjects lacking compatible final-baseline evidence."""
    context = _current_stage_gate_context(root)
    definitions = _stage_contract_definitions(context)
    candidates = _evidence_candidate_views(context, definitions)
    by_subject = _subject_candidates(candidates)
    items: list[dict[str, Any]] = []

    def add(kind: str, subject_ref: str, required_kinds: list[str], *, preferred_kind: str) -> None:
        refs = by_subject.get(subject_ref) or []
        if refs:
            return
        selected_kind = str(required_kinds[0]) if required_kinds else preferred_kind
        items.append(
            {
                "item_kind": kind,
                "subject_ref": subject_ref,
                "required_evidence_kinds": list(required_kinds),
                "selected_evidence_kind": selected_kind,
                "proof_methods": list(gate_proof_methods(selected_kind)),
                "source_requirement": "EXACT_SUBJECT_REVIEWABLE_SOURCE_WITH_DIGEST_AND_PROVENANCE",
                "baseline_revision": context["baseline_revision"],
                "reason": "No compatible PASS evidence is bound to the exact current product baseline.",
            }
        )

    for item in definitions["required_outcomes"]:
        if bool(item.get("mandatory", True)):
            add("OUTCOME", str(item["outcome_ref"]), [], preferred_kind="REVIEW_RECORD")
    for item in definitions["level_criteria"]:
        if bool(item.get("mandatory", True)):
            add(
                "LEVEL_CRITERION",
                str(item["criterion_ref"]),
                [str(kind) for kind in item.get("required_evidence_kinds") or []],
                preferred_kind="TEST_REPORT",
            )
    for item in definitions["hard_constraints"]:
        if bool(item.get("mandatory", True)):
            add(
                "HARD_CONSTRAINT",
                str(item["constraint_ref"]),
                [str(kind) for kind in item.get("required_evidence_kinds") or []],
                preferred_kind="EXTERNAL_EVIDENCE",
            )
    for item in definitions["profile_controls"]:
        if bool(item.get("mandatory", True)):
            add("PROFILE_CONTROL", str(item["control_ref"]), [], preferred_kind="REVIEW_RECORD")

    fingerprint_payload = {
        "level": context["active_stage"],
        "stage_plan_ref": context["plan_ref"],
        "gate_ref": context["gate_ref"],
        "baseline_revision": context["baseline_revision"],
        "missing_items": items,
    }
    return {
        "context": context,
        "definitions": definitions,
        "candidates": candidates,
        "missing_items": items,
        "readiness_fingerprint": f"sha256:{hashlib.sha256(canonical_json_bytes(fingerprint_payload)).hexdigest()}",
    }


def _verification_commands(root: Path, project_state: dict[str, Any]) -> list[dict[str, Any]]:
    entity_paths = project_state.get("entity_paths") or {}
    relative = entity_paths.get("technology_baseline")
    if not isinstance(relative, str):
        raise ValidationFailure("Technology Baseline path is missing from CURRENT_STATE")
    value = load_data(root / relative)
    body = value.get("technology_baseline") if isinstance(value, dict) else None
    if not isinstance(body, dict) or body.get("status") not in {"ACCEPTED", "ACTIVE"}:
        raise ValidationFailure("Accepted Technology Baseline is unavailable", relative)
    commands: list[dict[str, Any]] = []
    for raw in body.get("verification_commands") or []:
        if isinstance(raw, dict):
            argv = raw.get("argv")
            cwd = raw.get("cwd", ".")
            timeout = int(raw.get("timeout_seconds", 300))
        else:
            argv = raw
            cwd = "."
            timeout = 300
        if not isinstance(argv, list) or not argv or any(not isinstance(item, str) or not item for item in argv):
            raise ValidationFailure("Technology Baseline verification command is invalid", raw)
        commands.append({"argv": list(argv), "cwd": str(cwd), "timeout_seconds": timeout})
    return commands


def _latest_sequence(task_index: dict[str, Any], root: Path) -> int:
    maximum = 0
    for relative in (task_index.get("current") or {}).values():
        if not isinstance(relative, str) or not (root / relative).is_file():
            continue
        body = load_data(root / relative).get("task") or {}
        try:
            maximum = max(maximum, int(body.get("sequence", 0)))
        except (TypeError, ValueError):
            continue
    return ((maximum // 10) + 1) * 10


def _current_ref_for_index(root: Path, index_path: str, envelope: str, entity_id: str) -> str | None:
    path = root / index_path
    if not path.is_file():
        return None
    index_doc = load_data(path)
    index = index_doc.get(envelope + "_index") if isinstance(index_doc, dict) else None
    relative = (index.get("current") or {}).get(entity_id) if isinstance(index, dict) else None
    if not isinstance(relative, str) or not (root / relative).is_file():
        return None
    body = load_data(root / relative).get(envelope) or {}
    if body.get("id") != entity_id or not isinstance(body.get("revision"), int):
        return None
    return f"{entity_id}@{body['revision']}"


def _refresh_wp_refs(root: Path, refs: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for raw in refs:
        entity_id = str(raw).split("@", 1)[0]
        current = _current_ref_for_index(root, ".harness/work-packages/INDEX.yaml", "work_package", entity_id)
        value = current or str(raw)
        if value not in result:
            result.append(value)
    return result


def _preparation_scope() -> dict[str, list[str]]:
    # Product implementation paths are intentionally absent.  Preparation may
    # add or update verification/tests and bounded operating documentation only.
    return {
        "read": ["**/*"],
        "write": [
            "tests/**",
            "test/**",
            "docs/**",
            "README.md",
            "README.rst",
            "LIMITATIONS.md",
            "KNOWN_ISSUES.md",
            "PERMITTED_USE.md",
            "OPERATING_BOUNDARY.md",
        ],
        "forbidden": [
            ".harness/**",
            "CODEX_START.md",
            "AGENTS.md",
            "PROJECT.md",
            "ARCHITECTURE.md",
            "TECHNOLOGY.md",
        ],
    }


def _preparation_artifacts(
    root: Path,
    *,
    context: dict[str, Any],
    missing_items: list[dict[str, Any]],
    readiness_fingerprint: str,
    project_state_doc: dict[str, Any],
    task_index_doc: dict[str, Any],
    wp_index_doc: dict[str, Any],
) -> tuple[dict[Path, Any], dict[str, Any]]:
    token = _project_token(root)
    level = str(context["active_stage"])
    task_index = task_index_doc["task_index"]
    wp_index = wp_index_doc["work_package_index"]
    sequence = _latest_sequence(task_index, root)
    fingerprint_token = _short_digest(
        {
            "level": level,
            "baseline_revision": context["baseline_revision"],
            "missing_items": missing_items,
        },
        12,
    )
    wp_id = f"WP-{token}-{level}-STAGE-ACCEPTANCE-PREPARATION"
    task_id = f"TSK-{token}-GATE-PREP-{fingerprint_token}"
    existing_task_rel = (task_index.get("current") or {}).get(task_id)
    if isinstance(existing_task_rel, str) and (root / existing_task_rel).is_file():
        task = load_data(root / existing_task_rel).get("task") or {}
        if task.get("status") not in {"DONE", "SUPERSEDED", "CANCELLED"}:
            return {}, {
                "work_package_id": wp_id,
                "task_id": task_id,
                "task_ref": f"{task_id}@{task.get('revision')}",
                "existing": True,
                "sequence": int(task.get("sequence", sequence)),
            }
        raise ValidationFailure(
            "Completed preparation Task exists for an unresolved identical readiness fingerprint",
            {"task_ref": f"{task_id}@{task.get('revision')}", "readiness_fingerprint": readiness_fingerprint},
        )

    project_state = project_state_doc["state"]
    commands = _verification_commands(root, project_state)
    verification_id = f"VFP-{token}-{sequence // 10:03d}"
    prompt_plan_id = f"PPL-{token}-{sequence // 10:03d}"
    context_plan_id = f"CTX-{token}-{sequence // 10:03d}"
    dag_id = f"DAG-{token}-GATE-PREP-{fingerprint_token}"
    gap_refs = [str(item["subject_ref"]) for item in missing_items]
    completed_ids = [str(ref).split("@", 1)[0] for ref in project_state.get("completed_task_refs") or []]
    dependencies = [task for task in task_index.get("order") or [] if task in completed_ids]
    scope = _preparation_scope()
    now = utc_now()
    verification = {
        "commands": commands,
        "expected_paths": [],
        "manual_checks": [],
        "timeout_seconds": max([int(item.get("timeout_seconds", 300)) for item in commands] or [300]),
        "allow_manual": False,
    }
    metadata = {
        "kind": PREPARATION_KIND,
        "implementation_stage": level,
        "stage_plan_ref": context["plan_ref"],
        "gate_ref": context["gate_ref"],
        "evaluated_baseline_revision": context["baseline_revision"],
        "readiness_fingerprint": readiness_fingerprint,
        "missing_gate_items": deepcopy(missing_items),
        "future_stage_work": "FORBIDDEN",
        "accepted_scope_change": "NONE",
        "kernel_materialization": "ONLY_VALIDATED_PER_SUBJECT_PROOF_BINDINGS",
    }
    task = {
        "id": task_id,
        "revision": 1,
        "work_package_ref": wp_id,
        "implementation_stage": level,
        "title": f"Prepare exact final-baseline evidence for {level} Stage acceptance",
        "type": "VERIFICATION",
        "track": PREPARATION_KIND,
        "priority": "CRITICAL",
        "sequence": sequence,
        "purpose": "Collect and review real subject-specific proof artifacts for the exact unresolved Gate items; verification PASS alone cannot close them.",
        "expected_result": "All listed current-stage Gate subjects have immutable PASS evidence bound to the final product-tree baseline; no future-stage feature work is introduced.",
        "requirement_refs": [],
        "constraint_refs": [],
        "architecture_refs": [],
        "documentation": {
            "source_refs": [],
            "impact": "CONDITIONAL_CURRENT_STAGE_ONLY",
            "required_updates": [
                "Only tests, limitations, permitted-use, or operating documentation required by the exact missing Gate items may change."
            ],
        },
        "depends_on_tasks": dependencies,
        "requires_artifacts": [context["plan_ref"], context["gate_ref"]],
        "produces_artifacts": ["IMMUTABLE_GATE_EVIDENCE_BINDINGS"],
        "scope": scope,
        "route": {
            "primary_skill_ref": "SKL-UNIVERSAL-VERIFY@1",
            "supporting_skill_refs": ["SKL-UNIVERSAL-DOCUMENT@1"],
            "required_capabilities": ["FILESYSTEM_READ", "FILESYSTEM_WRITE", "COMMAND_EXECUTE"],
        },
        "prompt_spec_ref": "PSP-IMPLEMENT@1",
        "prompt_plan_ref": f"{prompt_plan_id}@1",
        "context_policy_ref": "CTP-TASK-STANDARD@1",
        "context_plan_ref": f"{context_plan_id}@1",
        "verification_profile_ref": f"{verification_id}@1",
        "verification": verification,
        "acceptance_criteria": [
            "Accepted Technology/Verification Baseline commands pass on the exact final product tree.",
            "Every missing_gate_item is addressed without adding future-stage functionality.",
            "Any product changes are limited to current-stage tests or bounded documentation allowed by scope.",
            "Every subject-specific proof identifies its checks, semantic method, accountable source and exact baseline; no generic PASS report is promoted.",
        ],
        "rollback": {"strategy": "RESTORE_PRE_RUN_SNAPSHOT"},
        "stage_acceptance_preparation": metadata,
        "status": "READY",
        "created_at": now,
    }
    verification_profile = {
        "id": verification_id,
        "revision": 1,
        "task_ref": f"{task_id}@1",
        "implementation_stage": level,
        "commands": commands,
        "expected_paths": [],
        "manual_checks": [],
        "timeout_seconds": verification["timeout_seconds"],
        "allow_manual": False,
        "status": "ACTIVE",
    }
    prompt_plan = {
        "id": prompt_plan_id,
        "revision": 1,
        "task_ref": f"{task_id}@1",
        "implementation_stage": level,
        "prompt_spec_ref": "PSP-IMPLEMENT@1",
        "module_refs": ["PMD-CORE-ROLE@1", "PMD-TASK-CONTRACT@1", "PMD-RESULT-SCHEMA@1"],
        "resolved_inputs": {
            "task_hash": f"sha256:{sha256_bytes(canonical_json_bytes(task))}",
            "skill_ref": "SKL-UNIVERSAL-VERIFY@1",
            "context_plan_ref": f"{context_plan_id}@1",
        },
        "output_schema_ref": "SCHEMA-AGENT-TASK-RESULT@1",
        "status": "RESOLVED",
    }
    context_plan = {
        "id": context_plan_id,
        "revision": 1,
        "task_ref": f"{task_id}@1",
        "implementation_stage": level,
        "include": {
            "project_definition": True,
            "architecture_baseline": True,
            "technology_baseline": True,
            "task_dependencies": dependencies,
            "read_paths": scope["read"],
            "stage_plan_ref": context["plan_ref"],
            "gate_ref": context["gate_ref"],
            "missing_gate_items": gap_refs,
        },
        "exclude": ["secrets", "unrelated tasks", "future-stage features", "provider accounting"],
        "status": "READY",
    }
    dag = {
        "id": dag_id,
        "revision": 1,
        "nodes": [task_id],
        "edges": [],
        "external_dependencies": dependencies,
        "scheduler_policy": "SINGLE_ACTIVE_TASK",
        "implementation_stage": level,
        "route_kind": PREPARATION_KIND,
        "status": "ACTIVE",
    }

    existing_wp_rel = (wp_index.get("current") or {}).get(wp_id)
    if isinstance(existing_wp_rel, str) and (root / existing_wp_rel).is_file():
        old_wp = load_data(root / existing_wp_rel).get("work_package") or {}
        wp_revision = int(old_wp.get("revision", 0)) + 1
        mandatory = [str(item) for item in old_wp.get("mandatory_task_refs") or []]
        if task_id not in mandatory:
            mandatory.append(task_id)
        wp = deepcopy(old_wp)
        wp.update(
            {
                "revision": wp_revision,
                "previous_revision_ref": f"{wp_id}@{old_wp.get('revision')}",
                "mandatory_task_refs": mandatory,
                "dependency_graph_ref": f"{dag_id}@1",
                "status": "READY",
                "readiness_fingerprint": readiness_fingerprint,
                "missing_gate_items": deepcopy(missing_items),
                "updated_at": now,
            }
        )
    else:
        wp_revision = 1
        wp = {
            "id": wp_id,
            "revision": 1,
            "kind": PREPARATION_KIND,
            "request_refs": [],
            "title": f"{level} Stage acceptance evidence preparation",
            "objective": "Close only exact final-baseline evidence gaps for the current active Stage Gate.",
            "implementation_stage": level,
            "requirement_refs": [],
            "architecture_refs": [],
            "documentation_refs": [],
            "mandatory_task_refs": [task_id],
            "dependency_graph_ref": f"{dag_id}@1",
            "aggregation_rule": "ALL_MANDATORY_PASS",
            "readiness_fingerprint": readiness_fingerprint,
            "missing_gate_items": deepcopy(missing_items),
            "future_stage_work": "FORBIDDEN",
            "status": "READY",
            "created_at": now,
        }

    task_rel = Path(f".harness/tasks/{task_id}@1.yaml")
    wp_rel = Path(f".harness/work-packages/{wp_id}@{wp_revision}.yaml")
    writes: dict[Path, Any] = {
        task_rel: {"task": task},
        Path(f".harness/verification/PROFILES/{verification_id}@1.yaml"): {"verification_profile": verification_profile},
        Path(f".harness/prompts/PLANS/{prompt_plan_id}@1.yaml"): {"prompt_plan": prompt_plan},
        Path(f".harness/context/PLANS/{context_plan_id}@1.yaml"): {"context_plan": context_plan},
        Path(f".harness/dags/{dag_id}@1.yaml"): {"dependency_graph": dag},
        wp_rel: {"work_package": wp},
    }
    task_index.setdefault("order", []).append(task_id)
    task_index.setdefault("current", {})[task_id] = task_rel.as_posix()
    task_index.setdefault("aliases", {})[task_id] = task_id
    task_index["aliases"]["stage-acceptance-preparation"] = task_id
    wp_index.setdefault("order", [])
    if wp_id not in wp_index["order"]:
        wp_index["order"].append(wp_id)
    wp_index.setdefault("current", {})[wp_id] = wp_rel.as_posix()
    writes[Path(".harness/tasks/INDEX.yaml")] = task_index_doc
    writes[Path(".harness/work-packages/INDEX.yaml")] = wp_index_doc
    return writes, {
        "work_package_id": wp_id,
        "work_package_ref": f"{wp_id}@{wp_revision}",
        "task_id": task_id,
        "task_ref": f"{task_id}@1",
        "sequence": sequence,
        "existing": False,
    }


def _stage_revision_writes(
    root: Path,
    *,
    context: dict[str, Any],
    plan_status: str,
    gate_status: str,
    baseline_revision: str,
    readiness_fingerprint: str,
    required_wp_refs: list[str],
    detailed_wp_refs: list[str],
    critical_blocker_refs: list[str] | None = None,
    diagnostics: dict[str, Any] | None = None,
) -> tuple[dict[Path, Any], dict[str, Any]]:
    now = utc_now()
    plan_index_doc = load_data(root / STAGE_PLAN_INDEX_PATH)
    gate_index_doc = load_data(root / STAGE_GATE_INDEX_PATH)
    plan_index = plan_index_doc["stage_plan_index"]
    gate_index = gate_index_doc["stage_gate_index"]
    plan = context["plan"]
    gate = context["gate"]

    new_plan = deepcopy(plan)
    new_plan["revision"] = int(plan["revision"]) + 1
    new_plan["previous_revision_ref"] = context["plan_ref"]
    new_plan["status"] = plan_status
    if plan_status != "BLOCKED":
        # The immutable BLOCKED revision retains the exact blocker binding.
        # A recovery revision is a new active/review state and must not still
        # present itself as bound to the resolved blocker.
        new_plan.pop("gate_blocker_ref", None)
    new_plan["detailed_work_package_refs"] = detailed_wp_refs
    new_plan["gate_readiness"] = {
        "status": "READY_FOR_FORMAL_REVIEW" if plan_status == "VERIFYING" else "EVIDENCE_PREPARATION_REQUIRED",
        "baseline_revision": baseline_revision,
        "readiness_fingerprint": readiness_fingerprint,
        "evaluated_at": now,
    }
    if diagnostics is not None:
        new_plan["gate_diagnostics"] = deepcopy(diagnostics)
    new_plan["updated_at"] = now
    validate_stage_plan({"stage_plan": new_plan})
    plan_rel = Path(_next_revision_path(".harness/stages/PLANS", str(plan["id"]), int(new_plan["revision"])))

    new_gate = deepcopy(gate)
    new_gate["revision"] = int(gate["revision"]) + 1
    new_gate["previous_revision_ref"] = context["gate_ref"]
    new_gate["stage_plan_ref"] = f"{new_plan['id']}@{new_plan['revision']}"
    new_gate["status"] = gate_status
    if gate.get("status") == "BLOCKED" and gate_status in {"ACTIVE", "VERIFYING"}:
        # Formal conclusions belong to the immutable BLOCKED Gate revision.
        # Recovery creates a fresh review revision, so all conclusions are
        # reopened instead of leaking UNKNOWN/FAIL values into a later accepted
        # Gate. Exact evidence candidates remain discoverable from artifacts.
        new_gate["criteria_results"] = [
            {
                "criterion_ref": str(item.get("criterion_ref")),
                "status": "UNKNOWN",
                "evidence_refs": [],
                "rationale": None,
                "validator": None,
            }
            for item in (gate.get("criteria_results") or [])
            if isinstance(item, dict) and item.get("criterion_ref")
        ]
        for field, ref_field in (
            ("outcome_results", "outcome_ref"),
            ("hard_constraint_results", "constraint_ref"),
            ("profile_control_results", "control_ref"),
        ):
            values = gate.get(field)
            if isinstance(values, list):
                new_gate[field] = [
                    {
                        ref_field: str(item.get(ref_field)),
                        "status": "UNKNOWN",
                        "evidence_refs": [],
                        "rationale": None,
                        "validator": None,
                    }
                    for item in values
                    if isinstance(item, dict) and item.get(ref_field)
                ]
        permitted_use = deepcopy(new_gate.get("permitted_use") or {})
        if permitted_use:
            permitted_use["status"] = "UNCONFIRMED"
            new_gate["permitted_use"] = permitted_use
        new_gate.pop("evidence_bindings", None)
        new_gate["evidence_refs"] = []
    new_gate["required_work_package_refs"] = required_wp_refs
    new_gate["critical_blocker_refs"] = list(critical_blocker_refs if critical_blocker_refs is not None else gate.get("critical_blocker_refs") or [])
    new_gate["base_revision"] = baseline_revision
    new_gate["readiness"] = {
        "status": "READY_FOR_FORMAL_REVIEW" if gate_status == "VERIFYING" else "EVIDENCE_PREPARATION_REQUIRED",
        "baseline_revision": baseline_revision,
        "readiness_fingerprint": readiness_fingerprint,
        "evaluated_at": now,
    }
    if diagnostics is not None:
        new_gate["evidence_diagnostics"] = deepcopy(diagnostics)
    new_gate["updated_at"] = now
    validate_stage_gate({"stage_gate": new_gate})
    gate_rel = Path(_next_revision_path(".harness/stages/GATES", str(gate["id"]), int(new_gate["revision"])))

    plan_index["current"][str(plan["id"])] = plan_rel.as_posix()
    gate_index["current"][str(gate["id"])] = gate_rel.as_posix()
    return {
        plan_rel: {"stage_plan": new_plan},
        gate_rel: {"stage_gate": new_gate},
        STAGE_PLAN_INDEX_PATH: plan_index_doc,
        STAGE_GATE_INDEX_PATH: gate_index_doc,
    }, {
        "plan": new_plan,
        "plan_ref": f"{new_plan['id']}@{new_plan['revision']}",
        "plan_path": plan_rel.as_posix(),
        "gate": new_gate,
        "gate_ref": f"{new_gate['id']}@{new_gate['revision']}",
        "gate_path": gate_rel.as_posix(),
    }


def _stage_state_revision(root: Path, *, now: str) -> tuple[dict[Path, Any], dict[str, Any]]:
    current = load_data(root / STAGE_STATE_PATH)
    updated = deepcopy(current)
    implementation = updated["implementation"]
    implementation["revision"] = int(implementation["revision"]) + 1
    implementation["updated_at"] = now
    validate_stage_state(updated)
    return {
        STAGE_STATE_PATH: updated,
        Path(f".harness/stages/STATE_HISTORY/STAGE_STATE@{implementation['revision']}.yaml"): updated,
    }, updated


def _persist_readiness_route(
    root: Path,
    readiness: dict[str, Any],
    *,
    from_gate_blocker: dict[str, Any] | None = None,
    reserve_first: bool = True,
) -> dict[str, Any]:
    context = readiness["context"]
    missing_items = readiness["missing_items"]
    fingerprint = str(readiness["readiness_fingerprint"])
    project_state_path = Path(".harness/state/CURRENT_STATE.yaml")
    next_task_path = Path(".harness/state/NEXT_TASK.yaml")
    project_state_doc = load_data(root / project_state_path)
    task_index_doc = load_data(root / ".harness/tasks/INDEX.yaml")
    wp_index_doc = load_data(root / ".harness/work-packages/INDEX.yaml")
    now = utc_now()
    writes: dict[Path, Any] = {}

    existing_required = _refresh_wp_refs(root, context["gate"].get("required_work_package_refs") or [])
    existing_detailed = _refresh_wp_refs(root, context["plan"].get("detailed_work_package_refs") or [])

    if missing_items:
        # A completed attempt with exactly the same missing subjects/baseline
        # must not spin up another identical preparation Task.
        token = _short_digest({"level": context["active_stage"], "baseline_revision": context["baseline_revision"], "missing_items": missing_items}, 12)
        previous_task_id = f"TSK-{_project_token(root)}-GATE-PREP-{token}"
        previous_path = (task_index_doc.get("task_index") or {}).get("current", {}).get(previous_task_id)
        if previous_path and (root / previous_path).is_file():
            previous = load_data(root / previous_path).get("task") or {}
            if previous.get("status") == "DONE":
                diagnostics = {"baseline_revision": context["baseline_revision"], "missing_items": deepcopy(missing_items),
                               "reason": "Preparation completed but did not provide sufficient semantic Gate evidence"}
                stage_writes, refs = _stage_revision_writes(
                    root, context=context, plan_status="BLOCKED", gate_status="BLOCKED",
                    baseline_revision=str(context["baseline_revision"]), readiness_fingerprint=fingerprint,
                    required_wp_refs=existing_required, detailed_wp_refs=existing_detailed,
                    critical_blocker_refs=[], diagnostics=diagnostics)
                writes.update(stage_writes)
                # Bind the terminal unproven transaction to exact input Gate
                # revisions as well as the missing-subject fingerprint.
                # A later recovery review of this same Stage/baseline cannot
                # collide with a previously committed transaction id.
                review_token = _short_digest({"plan": context["plan_ref"], "gate": context["gate_ref"], "blocker": from_gate_blocker.get("current_ref") if from_gate_blocker else None}, 8)
                blocker_id = f"BLK-{_project_token(root)}-{context['active_stage']}-GATE-UNPROVEN-{token}-{review_token}"
                blocker_ref = f"{blocker_id}@1"
                blocker = {"id": blocker_id, "revision": 1, "kind": GATE_BLOCKER_KIND,
                    "level": context["active_stage"], "stage_plan_ref": context["plan_ref"],
                    "gate_ref": context["gate_ref"], "baseline_revision": context["baseline_revision"],
                    "reason": "Preparation verification passed without sufficient subject-specific Gate proof",
                    "failed_or_missing_items": deepcopy(missing_items),
                    "recovery_options": ["Supply authentic subject-bound evidence and resume-stage-gate"],
                    "resume_condition": "Add exact final-baseline proof, then run resume-stage-gate",
                    "status": "OPEN", "created_at": now}
                writes[Path(f".harness/blockers/{blocker_ref}.yaml")] = {"blocker": blocker}
                for document_path, envelope in [(Path(refs["plan_path"]), "stage_plan"), (Path(refs["gate_path"]), "stage_gate")]:
                    if document_path in writes:
                        entity = writes[document_path][envelope]
                        if envelope == "stage_plan": entity["gate_blocker_ref"] = blocker_ref
                        else: entity["critical_blocker_refs"] = list(dict.fromkeys((entity.get("critical_blocker_refs") or []) + [blocker_ref]))
                state = project_state_doc["state"]
                if blocker_ref not in state.setdefault("open_blocker_refs", []): state["open_blocker_refs"].append(blocker_ref)
                state.update({"current_task_ref": None, "active_run": None, "project_status": "BLOCKED",
                              "next_route": GATE_RECOVERY_ROUTE, "handoff_status": "STAGE_GATE_BLOCKED", "updated_at": now})
                writes[project_state_path] = project_state_doc
                writes[next_task_path] = {"next_task": {"status": "BLOCKED", "task_ref": None, "run_ref": None,
                    "active_stage": context["active_stage"], "stage_plan_ref": refs["plan_ref"], "gate_ref": refs["gate_ref"], "blocker_ref": blocker_ref, "blocker_kind": GATE_BLOCKER_KIND, "next_route": GATE_RECOVERY_ROUTE}}
                stage_state_writes, _ = _stage_state_revision(root, now=now)
                writes.update(stage_state_writes)
                result = {"status": "BLOCKED", "next_route": GATE_RECOVERY_ROUTE, "active_stage": context["active_stage"],
                          "gate_ref": refs["gate_ref"], "stage_plan_ref": refs["plan_ref"],
                          "missing_gate_items": deepcopy(missing_items)}
                return _transactional_write(root, writes,
                    transaction_id=f"STX-{_project_token(root)}-{context['active_stage']}-GATE-UNPROVEN-{token}-{review_token}",
                    operation_kind="PREPARE_STAGE_GATE", request_digest=stage_transaction_digest(result), result=result)
        prep_writes, prep = _preparation_artifacts(
            root,
            context=context,
            missing_items=missing_items,
            readiness_fingerprint=fingerprint,
            project_state_doc=project_state_doc,
            task_index_doc=task_index_doc,
            wp_index_doc=wp_index_doc,
        )
        if prep.get("existing"):
            project_state = project_state_doc["state"]
            active_run = project_state.get("active_run")
            if isinstance(active_run, dict):
                active_task_id = str(active_run.get("task_ref") or "").split("@", 1)[0]
                if active_task_id != prep["task_id"]:
                    raise ValidationFailure(
                        "Another Run is active while Stage acceptance preparation is pending",
                        {"active_task": active_task_id, "preparation_task": prep["task_id"]},
                    )
            else:
                project_state["current_task_ref"] = prep["task_id"]
                task_order = project_state.setdefault("task_order", [])
                if prep["task_id"] not in task_order:
                    task_order.append(prep["task_id"])
                project_state["project_status"] = "ACTIVE"
                project_state["next_route"] = PREPARATION_ROUTE
                project_state["handoff_status"] = "STAGE_ACCEPTANCE_PREPARATION"
                project_state["updated_at"] = now
                # No Stage mutation is required for an idempotent retry.
                from .serialization import write_data

                write_data(root / project_state_path, project_state_doc)
            result = {
                "status": PREPARATION_ROUTE,
                "active_stage": context["active_stage"],
                "work_package_ref": prep.get("work_package_ref") or prep["work_package_id"],
                "task_ref": prep["task_ref"],
                "missing_gate_items": deepcopy(missing_items),
                "readiness_fingerprint": fingerprint,
                "idempotent": True,
            }
            if reserve_first:
                bundle = reserve_run(root, prep["task_id"])
                result["task_ref"] = bundle["task_ref"]
                result["next"] = bundle
            return result
        writes.update(prep_writes)
        prep_ref = str(prep["work_package_ref"])
        required_wp_refs = [ref for ref in existing_required if ref.split("@", 1)[0] != prep["work_package_id"]] + [prep_ref]
        detailed_wp_refs = [ref for ref in existing_detailed if ref.split("@", 1)[0] != prep["work_package_id"]] + [prep_ref]
        diagnostics = {
            "baseline_revision": context["baseline_revision"],
            "missing_items": deepcopy(missing_items),
            "candidate_count": len(readiness["candidates"]),
            "recovery_source_blocker_ref": from_gate_blocker.get("current_ref") if from_gate_blocker else None,
        }
        stage_writes, stage_refs = _stage_revision_writes(
            root,
            context=context,
            plan_status="ACTIVE",
            gate_status="ACTIVE",
            baseline_revision=str(context["baseline_revision"]),
            readiness_fingerprint=fingerprint,
            required_wp_refs=required_wp_refs,
            detailed_wp_refs=detailed_wp_refs,
            critical_blocker_refs=[],
            diagnostics=diagnostics,
        )
        writes.update(stage_writes)
        project_state = project_state_doc["state"]
        project_state["current_task_ref"] = prep["task_id"]
        task_order = project_state.setdefault("task_order", [])
        if prep["task_id"] not in task_order:
            task_order.append(prep["task_id"])
        project_state["project_status"] = "ACTIVE"
        project_state["next_route"] = PREPARATION_ROUTE
        project_state["handoff_status"] = "STAGE_ACCEPTANCE_PREPARATION"
        project_state["active_run"] = None
        if from_gate_blocker:
            gate_blocker_id = str(from_gate_blocker["id"])
            project_state["open_blocker_refs"] = [
                ref for ref in project_state.get("open_blocker_refs") or [] if str(ref).split("@", 1)[0] != gate_blocker_id
            ]
        project_state["updated_at"] = now
        writes[project_state_path] = project_state_doc
        writes[next_task_path] = {
            "next_task": {
                "status": "STAGE_ACCEPTANCE_PREPARATION_READY",
                "task_ref": prep["task_ref"],
                "run_ref": None,
                "implementation_stage": context["active_stage"],
                "gate_ref": stage_refs["gate_ref"],
                "next_route": PREPARATION_ROUTE,
            }
        }
        state_writes, _ = _stage_state_revision(root, now=now)
        writes.update(state_writes)
        if from_gate_blocker:
            writes.update(_resolved_gate_blocker_writes(root, from_gate_blocker, resolution_status="MITIGATING", now=now, recovery_route=PREPARATION_ROUTE))
        transaction_id = (
            f"STX-{from_gate_blocker['id']}-RESUME-{_short_digest({'baseline': context['baseline_revision'], 'missing': missing_items}, 8)}"
            if from_gate_blocker
            else f"STX-{_project_token(root)}-{context['active_stage']}-GATE-PREP-{_short_digest(fingerprint, 10)}"
        )
        operation_kind = "RESUME_STAGE_GATE" if from_gate_blocker else "PREPARE_STAGE_GATE"
        request_digest = stage_transaction_digest(
            {
                "operation_kind": operation_kind,
                "stage_plan_ref": context["plan_ref"],
                "gate_ref": context["gate_ref"],
                "baseline_revision": context["baseline_revision"],
                "missing_items": missing_items,
                "blocker_ref": from_gate_blocker.get("current_ref") if from_gate_blocker else None,
            }
        )
        stored_result = {
            "status": PREPARATION_ROUTE,
            "work_package_ref": prep_ref,
            "task_ref": prep["task_ref"],
            "gate_ref": stage_refs["gate_ref"],
            "stage_plan_ref": stage_refs["plan_ref"],
            "missing_gate_items": deepcopy(missing_items),
            "readiness_fingerprint": fingerprint,
        }
        committed = _transactional_write(
            root,
            writes,
            transaction_id=transaction_id,
            operation_kind=operation_kind,
            request_digest=request_digest,
            result=stored_result,
        )
        committed.update(
            {
                "active_stage": context["active_stage"],
                "next_route": PREPARATION_ROUTE,
                "idempotent": bool(committed.get("idempotent", False)),
            }
        )
        if reserve_first:
            bundle = reserve_run(root, prep["task_id"])
            committed["next"] = bundle
        return committed

    # No evidence preparation is needed; refresh exact current WP refs and move
    # the current Stage to formal review without creating any synthetic Task.
    diagnostics = {
        "baseline_revision": context["baseline_revision"],
        "missing_items": [],
        "candidate_count": len(readiness["candidates"]),
        "compatible_evidence_refs": [str(item["ref"]) for item in readiness["candidates"]],
        "recovery_source_blocker_ref": from_gate_blocker.get("current_ref") if from_gate_blocker else None,
    }
    stage_writes, stage_refs = _stage_revision_writes(
        root,
        context=context,
        plan_status="VERIFYING",
        gate_status="VERIFYING",
        baseline_revision=str(context["baseline_revision"]),
        readiness_fingerprint=fingerprint,
        required_wp_refs=existing_required,
        detailed_wp_refs=existing_detailed,
        critical_blocker_refs=[],
        diagnostics=diagnostics,
    )
    writes.update(stage_writes)
    project_state = project_state_doc["state"]
    project_state["current_task_ref"] = None
    project_state["active_run"] = None
    project_state["project_status"] = "ACTIVE"
    project_state["next_route"] = GATE_REVIEW_ROUTE
    project_state["handoff_status"] = "STAGE_GATE_PENDING"
    if from_gate_blocker:
        gate_blocker_id = str(from_gate_blocker["id"])
        project_state["open_blocker_refs"] = [
            ref for ref in project_state.get("open_blocker_refs") or [] if str(ref).split("@", 1)[0] != gate_blocker_id
        ]
    project_state["updated_at"] = now
    writes[project_state_path] = project_state_doc
    writes[next_task_path] = {
        "next_task": {
            "status": "STAGE_GATE_PENDING",
            "task_ref": None,
            "run_ref": None,
            "active_stage": context["active_stage"],
            "gate_ref": stage_refs["gate_ref"],
            "next_route": GATE_REVIEW_ROUTE,
        }
    }
    state_writes, _ = _stage_state_revision(root, now=now)
    writes.update(state_writes)
    if from_gate_blocker:
        writes.update(_resolved_gate_blocker_writes(root, from_gate_blocker, resolution_status="RESOLVED", now=now, recovery_route=GATE_REVIEW_ROUTE))
    transaction_id = (
        f"STX-{from_gate_blocker['id']}-RESUME-{_short_digest({'baseline': context['baseline_revision'], 'missing': []}, 8)}"
        if from_gate_blocker
        else f"STX-{_project_token(root)}-{context['active_stage']}-GATE-VERIFY-{_short_digest(fingerprint, 10)}"
    )
    operation_kind = "RESUME_STAGE_GATE" if from_gate_blocker else "PREPARE_STAGE_GATE"
    request_digest = stage_transaction_digest(
        {
            "operation_kind": operation_kind,
            "stage_plan_ref": context["plan_ref"],
            "gate_ref": context["gate_ref"],
            "baseline_revision": context["baseline_revision"],
            "missing_items": [],
            "blocker_ref": from_gate_blocker.get("current_ref") if from_gate_blocker else None,
        }
    )
    stored_result = {
        "status": "VERIFYING",
        "gate_ref": stage_refs["gate_ref"],
        "stage_plan_ref": stage_refs["plan_ref"],
        "baseline_revision": context["baseline_revision"],
        "readiness_fingerprint": fingerprint,
    }
    committed = _transactional_write(
        root,
        writes,
        transaction_id=transaction_id,
        operation_kind=operation_kind,
        request_digest=request_digest,
        result=stored_result,
    )
    committed.update(
        {
            "active_stage": context["active_stage"],
            "next_route": GATE_REVIEW_ROUTE,
            "idempotent": bool(committed.get("idempotent", False)),
        }
    )
    return committed


@guarded_mutation
def evaluate_stage_gate_readiness(root: Path, *, reserve_first: bool = True) -> dict[str, Any]:
    """Evaluate final-baseline Gate evidence and persist the exact next route."""
    root = root.expanduser().resolve()
    recover_stage_transactions(root)
    readiness = missing_gate_evidence_items(root)
    context = readiness["context"]
    plan_status = str(context["plan"].get("status"))
    gate_status = str(context["gate"].get("status"))
    if plan_status == "VERIFYING" and gate_status == "VERIFYING" and not readiness["missing_items"]:
        return {
            "status": "VERIFYING",
            "active_stage": context["active_stage"],
            "stage_plan_ref": context["plan_ref"],
            "gate_ref": context["gate_ref"],
            "baseline_revision": context["baseline_revision"],
            "next_route": GATE_REVIEW_ROUTE,
            "idempotent": True,
        }
    if plan_status == "BLOCKED" or gate_status == "BLOCKED":
        raise ValidationFailure(
            "Gate-related BLOCKED Stage requires resume-stage-gate",
            {"stage_plan_status": plan_status, "gate_status": gate_status, "next_route": GATE_RECOVERY_ROUTE},
        )
    if plan_status != "ACTIVE" or gate_status != "ACTIVE":
        raise ValidationFailure(
            "Stage Gate readiness evaluation requires ACTIVE Stage Plan and Gate",
            {"stage_plan_status": plan_status, "gate_status": gate_status},
        )
    work_packages = _current_work_package_views(root, context["gate"].get("required_work_package_refs") or [])
    incomplete = [item for item in work_packages if item.get("status") != "COMPLETED"]
    ordinary_incomplete: list[dict[str, Any]] = []
    for item in incomplete:
        current_ref = item.get("current_ref")
        wp_id = str(current_ref or item.get("requested_ref") or "").split("@", 1)[0]
        current_path = item.get("path")
        body = load_data(root / str(current_path)).get("work_package") if current_path and (root / str(current_path)).is_file() else None
        if not isinstance(body, dict) or body.get("kind") != PREPARATION_KIND:
            ordinary_incomplete.append(item)
    if ordinary_incomplete:
        raise ValidationFailure("Stage Gate readiness evaluation requires all ordinary mandatory Work Packages to be completed", ordinary_incomplete)
    blockers = _current_blocker_views(root, context["gate"].get("critical_blocker_refs") or [])
    open_blockers = [item for item in blockers if item.get("status") not in {"RESOLVED", "SUPERSEDED", "CLOSED"}]
    if open_blockers:
        raise ValidationFailure("Stage Gate readiness evaluation cannot bypass critical blockers", open_blockers)
    return _persist_readiness_route(root, readiness, reserve_first=reserve_first)


def materialize_preparation_task_evidence(
    root: Path,
    *,
    task: dict[str, Any],
    active_run: dict[str, Any],
    verification_report: dict[str, Any],
) -> list[dict[str, str]]:
    """Surface only existing, separately validated Gate proof for a PASS preparation Task.

    Verification success cannot manufacture subject-specific proof or PASS EVDs.
    """
    metadata = task.get("stage_acceptance_preparation")
    if not isinstance(metadata, dict) or metadata.get("kind") != PREPARATION_KIND:
        return []
    if verification_report.get("status") != "PASS":
        raise ValidationFailure("Preparation evidence requires a PASS verification report")
    level = str(task.get("implementation_stage"))
    current = _current_stage_gate_context(root)
    if current["active_stage"] != level:
        raise ValidationFailure("Preparation Task no longer belongs to the active Stage", {"task_stage": level, "active_stage": current["active_stage"]})
    baseline = product_baseline_revision(root)
    report_path = active_run.get("verification_report_path")
    report_ref = active_run.get("verification_report_ref")
    if not isinstance(report_path, str) or not isinstance(report_ref, str) or not (root / report_path).is_file():
        raise ValidationFailure("Preparation verification report source is unavailable")
    # Only independently provided, already normalized and semantically checked
    # immutable evidence can close a subject.  A generic verification report is
    # never converted into one or more PASS EVDs. Existing EVDs are surfaced as
    # exact bindings to the completed Run; readiness will still BLOCK if a
    # single mandatory subject is unresolved.
    definitions = _stage_contract_definitions(current)
    candidates = _evidence_candidate_views(current, definitions)
    required_subjects = {str(item["subject_ref"]) for item in (metadata.get("missing_gate_items") or [])}
    bindings = [
        {key: candidate[key] for key in ("ref", "path", "sha256")}
        for candidate in candidates
        if required_subjects.intersection(candidate["compatible_subject_refs"])
    ]
    return sorted(bindings, key=lambda item: item["ref"])


def _latest_gate_blocker(root: Path, blocker_id: str) -> dict[str, Any]:
    candidates: list[tuple[int, Path]] = []
    for path in (root / ".harness/blockers").glob(f"{blocker_id}@*.yaml"):
        suffix = path.stem.rsplit("@", 1)
        if len(suffix) == 2 and suffix[0] == blocker_id and suffix[1].isdigit():
            candidates.append((int(suffix[1]), path))
    if not candidates:
        raise ValidationFailure("Gate blocker record is missing", blocker_id)
    _, path = max(candidates, key=lambda item: item[0])
    body = load_data(path).get("blocker") or {}
    if body.get("id") != blocker_id or body.get("kind") != GATE_BLOCKER_KIND:
        raise ValidationFailure("Referenced blocker is not a Stage Gate blocker", blocker_id)
    result = deepcopy(body)
    result["path"] = path.relative_to(root).as_posix()
    result["current_ref"] = f"{blocker_id}@{body.get('revision')}"
    return result


def _resolved_gate_blocker_writes(
    root: Path,
    blocker: dict[str, Any],
    *,
    resolution_status: str,
    now: str,
    recovery_route: str,
) -> dict[Path, Any]:
    revised = deepcopy(blocker)
    revised.pop("path", None)
    revised.pop("current_ref", None)
    revised["revision"] = int(blocker["revision"]) + 1
    revised["previous_revision_ref"] = blocker["current_ref"]
    revised["status"] = resolution_status
    revised["recovery_route"] = recovery_route
    revised["revalidated_baseline_revision"] = product_baseline_revision(root)
    revised["updated_at"] = now
    if resolution_status == "RESOLVED":
        revised["resolved_at"] = now
    else:
        revised["mitigation_started_at"] = now
    return {Path(f".harness/blockers/{blocker['id']}@{revised['revision']}.yaml"): {"blocker": revised}}


def _idempotent_recovery_view(root: Path) -> dict[str, Any] | None:
    state = load_data(root / ".harness/state/CURRENT_STATE.yaml").get("state") or {}
    route = state.get("next_route")
    if state.get("project_status") != "ACTIVE" or route not in {PREPARATION_ROUTE, "EXECUTE_CURRENT_TASK_WITH_CODEX", GATE_REVIEW_ROUTE}:
        return None
    blocker_dir = root / ".harness/blockers"
    latest: dict[str, Any] | None = None
    for path in blocker_dir.glob("BLK-*@*.yaml") if blocker_dir.is_dir() else []:
        body = load_data(path).get("blocker") or {}
        if body.get("kind") != GATE_BLOCKER_KIND or body.get("status") not in {"MITIGATING", "RESOLVED"}:
            continue
        if latest is None or str(body.get("updated_at") or body.get("resolved_at") or "") > str(latest.get("updated_at") or latest.get("resolved_at") or ""):
            latest = body
    if latest is None:
        return None
    result = {
        "status": PREPARATION_ROUTE if route in {PREPARATION_ROUTE, "EXECUTE_CURRENT_TASK_WITH_CODEX"} else "VERIFYING",
        "active_stage": state.get("active_stage"),
        "next_route": route,
        "blocker_ref": f"{latest.get('id')}@{latest.get('revision')}",
        "idempotent": True,
    }
    if state.get("current_task_ref"):
        result["task_ref"] = state["current_task_ref"]
        result["next"] = reserve_run(root, str(state["current_task_ref"]))
    else:
        context = _current_stage_gate_context(root)
        result["gate_ref"] = context["gate_ref"]
        result["stage_plan_ref"] = context["plan_ref"]
    return result


@guarded_mutation
def resume_stage_gate(root: Path) -> dict[str, Any]:
    """Recover only a persisted Stage-Gate blocker, preserving blocked history."""
    root = root.expanduser().resolve()
    recover_stage_transactions(root)
    state_doc = load_data(root / ".harness/state/CURRENT_STATE.yaml")
    state = state_doc.get("state") or {}
    if state.get("project_status") != "BLOCKED" or state.get("next_route") != GATE_RECOVERY_ROUTE:
        replay = _idempotent_recovery_view(root)
        if replay is not None:
            return replay
        raise ValidationFailure(
            "resume-stage-gate is allowed only for persisted Gate-related BLOCKED state",
            {"project_status": state.get("project_status"), "next_route": state.get("next_route")},
        )
    open_refs = [str(ref).split("@", 1)[0] for ref in state.get("open_blocker_refs") or []]
    gate_blockers: list[dict[str, Any]] = []
    for blocker_id in open_refs:
        blocker = _latest_gate_blocker(root, blocker_id)
        if blocker.get("status") == "OPEN":
            gate_blockers.append(blocker)
    if len(gate_blockers) != 1:
        raise ValidationFailure(
            "Gate recovery requires exactly one OPEN Stage Gate blocker",
            {"gate_blockers": [item.get("current_ref") for item in gate_blockers], "open_blocker_refs": open_refs},
        )
    blocker = gate_blockers[0]
    context = _current_stage_gate_context(root)
    if context["plan"].get("status") != "BLOCKED" or context["gate"].get("status") != "BLOCKED":
        raise ValidationFailure("Current Stage Plan/Gate is not persisted BLOCKED", {"plan": context["plan_ref"], "gate": context["gate_ref"]})
    if str(blocker.get("level")) != str(context["active_stage"]):
        raise ValidationFailure("Gate blocker belongs to another Stage", blocker.get("current_ref"))
    readiness = missing_gate_evidence_items(root)
    # Resuming an unchanged unproven Gate is a stable BLOCKED no-op, not a
    # license to generate the same Task or another blocker indefinitely.
    if (readiness["missing_items"]
            and blocker.get("baseline_revision") == readiness["context"]["baseline_revision"]
            and blocker.get("failed_or_missing_items") == readiness["missing_items"]):
        return {"status": "BLOCKED", "next_route": GATE_RECOVERY_ROUTE,
                "active_stage": context["active_stage"], "gate_ref": context["gate_ref"],
                "stage_plan_ref": context["plan_ref"], "blocker_ref": blocker["current_ref"],
                "missing_gate_items": deepcopy(readiness["missing_items"]), "idempotent": True}
    return _persist_readiness_route(root, readiness, from_gate_blocker=blocker)

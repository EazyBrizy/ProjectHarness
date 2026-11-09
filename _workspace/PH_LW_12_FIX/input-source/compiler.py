from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .operation_guard import guarded_mutation
from .archive import zip_directory
from .errors import ValidationFailure, WaitingDecision, WaitingInput
from .hashing import build_manifest, sha256_bytes, sha256_file, tree_hash, tree_entries
from .intake import check_intake
from .inventory import build_repository_inventory
from .planner import normalize_plan
from .project_input import (PROJECT_INPUT_MIGRATION_ID, EXECUTION_POLICY_MIGRATION_ID,
                            QUESTION_BANK, DEFAULT_EXECUTION_POLICY, migrate_project_input,
                            validate_project_input, exact_execution_profile_bindings)
from .prompting import reserve_run
from .registry import registry_lock
from .render import render_project_documents, render_status
from .resources import distribution_root
from .safety import copy_tree_filtered
from .platform_fs import ensure_native_path, _native_io_path
from .serialization import canonical_json_bytes, load_data, write_data, atomic_write_text
from .stages import create_initial_stage_artifacts
from .util import ENGINE_VERSION, SCHEMA_VERSION, deep_get, id_token, nonempty, slugify, utc_now
from .workspace import record_phase_boundary


def _write_entity(root: Path, relative: str, key: str, value: dict[str, Any]) -> str:
    write_data(root / relative, {key: value})
    return relative


def _ref(entity_id: str, revision: int = 1) -> str:
    return f"{entity_id}@{revision}"


def _statement(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("statement") or item.get("title") or item.get("name") or item)
    return str(item)


def _copy_intake_sources(workspace: Path, root: Path, inventory: dict[str, Any]) -> dict[str, Any]:
    target = root / ".harness/incoming/SOURCES"
    target.mkdir(parents=True, exist_ok=True)
    source_paths = sorted((workspace / "sources").iterdir()) if (workspace / "sources").exists() else []
    mapping: dict[str, str] = {}
    for path in source_paths:
        destination = target / path.name
        if path.is_dir():
            copy_tree_filtered(path, destination, excluded_dirs={".git", ".harness", "node_modules", ".venv", "__pycache__"})
        else:
            shutil.copy2(path, destination)
        mapping[path.name] = destination.relative_to(root).as_posix()
    sanitized = deepcopy(inventory)
    for source in sanitized["source_inventory"].get("sources") or []:
        name = source.get("name")
        source["path"] = mapping.get(str(name), f".harness/incoming/SOURCES/{name}")
    return sanitized


def _copy_runtime(root: Path) -> None:
    distribution = distribution_root()
    engine_root = root / ".harness/engine"
    package_source = distribution / "src/project_harness"
    if not package_source.is_dir():
        # Installed wheel: copy the executing package itself into the handoff.
        package_source = Path(__file__).resolve().parent
    package_target = engine_root / "project_harness"
    shutil.copytree(
        package_source,
        package_target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    launcher = """#!/usr/bin/env python3
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
from pathlib import Path
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from project_harness.cli import main
raise SystemExit(main())
"""
    atomic_write_text(engine_root / "project-harness.py", launcher)
    (engine_root / "project-harness.py").chmod(0o755)
    shutil.copytree(distribution / "schemas", engine_root / "schemas", dirs_exist_ok=True)
    shutil.copytree(distribution / "skills", engine_root / "skills", dirs_exist_ok=True)
    atomic_write_text(root / ".harness/VERSION", ENGINE_VERSION + "\n")


def _seed_skills(root: Path, project_input: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    distribution = distribution_root()
    active_dir = root / ".harness/skills/ACTIVE"
    active_dir.mkdir(parents=True, exist_ok=True)
    available: list[dict[str, Any]] = []
    for path in sorted((distribution / "skills").glob("SKL-*.yaml")):
        target = active_dir / path.name
        shutil.copy2(path, target)
        skill = load_data(path)["skill"]
        available.append(
            {
                "ref": _ref(skill["id"], int(skill["revision"])),
                "path": target.relative_to(root).as_posix(),
                "digest": f"sha256:{sha256_file(target)}",
                "status": skill["status"],
                "level": skill["level"],
                "applies_to_task_types": skill["applies_to_task_types"],
            }
        )
    resolved: list[dict[str, Any]] = []
    available_refs = {item["ref"] for item in available}
    for item in project_input["skills"]["resolutions"]:
        ref = item.get("skill_ref")
        if ref and ref not in available_refs:
            raise ValidationFailure(
                "Resolved skill is not ACTIVE in the bundled distribution",
                {"skill_ref": ref, "available": sorted(available_refs)},
            )
        resolved.append(deepcopy(item))
    registry = {
        "skill_registry_index": {
            "generated": True,
            "source_of_truth": [item["path"] for item in available],
            "available": available,
            "resolved": resolved,
            "generated_at": utc_now(),
        }
    }
    write_data(root / ".harness/skills/registry.yaml", registry)
    write_data(
        root / ".harness/reports/VAL-SKILL-GAP-001.yaml",
        {
            "validation_report": {
                "id": "VAL-SKILL-GAP-001",
                "kind": "SKILL_GAP_ANALYSIS",
                "status": "PASS",
                "resolutions": resolved,
                "authoring_actions_blocked": ["CREATE", "EXTEND"],
                "summary": "Project-local resolution uses ACTIVE distribution skills; no skill is created per project unless a later governed authoring route is approved.",
            }
        },
    )
    return [str(item.get("skill_ref")) for item in resolved if item.get("skill_ref")], registry


def _primary_skill(task: dict[str, Any]) -> str:
    route = task.get("route") or {}
    if route.get("primary_skill_ref"):
        return str(route["primary_skill_ref"])
    task_type = str(task.get("type", "IMPLEMENT")).upper()
    if task_type in {"DOCUMENT", "DESIGN"}:
        return "SKL-UNIVERSAL-DOCUMENT@1"
    if task_type == "VERIFY":
        return "SKL-UNIVERSAL-VERIFY@1"
    return "SKL-UNIVERSAL-IMPLEMENT@3"


def _default_capabilities(task: dict[str, Any]) -> list[str]:
    task_type = str(task.get("type", "IMPLEMENT")).upper()
    if task_type == "VERIFY":
        return ["FILESYSTEM_READ", "COMMAND_EXECUTE"]
    if task_type in {"DOCUMENT", "DESIGN"}:
        return ["FILESYSTEM_READ", "FILESYSTEM_WRITE"]
    return ["FILESYSTEM_READ", "FILESYSTEM_WRITE", "COMMAND_EXECUTE"]


def _create_requirements(root: Path, project_input: dict[str, Any], token: str) -> tuple[list[str], list[str], dict[str, Any]]:
    project = project_input["project"]
    requirement_refs: list[str] = []
    success_refs: list[str] = []
    trace_rows: list[dict[str, Any]] = []
    for index, item in enumerate(project["scope"]["in"], 1):
        req_id = f"REQ-{token}-{index:03d}"
        value = {
            "id": req_id,
            "revision": 1,
            "statement": _statement(item),
            "source": "PROJECT_SCOPE",
            "status": "ACTIVE",
        }
        rel = f".harness/canonical/REQUIREMENTS/{req_id}@1.yaml"
        _write_entity(root, rel, "requirement", value)
        requirement_refs.append(_ref(req_id))
        trace_rows.append({"requirement_ref": _ref(req_id), "source": "PROJECT_INPUT.project.scope.in", "task_refs": []})
    for index, item in enumerate(project["success_criteria"], 1):
        suc_id = f"SUC-{token}-{index:03d}"
        statement = _statement(item)
        value = {
            "id": suc_id,
            "revision": 1,
            "statement": statement,
            "verification": item.get("verification") if isinstance(item, dict) else None,
            "status": "ACTIVE",
        }
        rel = f".harness/canonical/REQUIREMENTS/{suc_id}@1.yaml"
        _write_entity(root, rel, "success_criterion", value)
        success_refs.append(_ref(suc_id))
    traceability = {"traceability": {"requirements": trace_rows, "generated_at": utc_now()}}
    write_data(root / ".harness/canonical/REQUIREMENTS/TRACEABILITY.yaml", traceability)
    return requirement_refs, success_refs, traceability


def _create_constraints(root: Path, project_input: dict[str, Any], token: str) -> tuple[list[str], list[str], list[str]]:
    project = project_input["project"]
    constraint_refs: list[str] = []
    assumption_refs: list[str] = []
    unknown_refs: list[str] = []
    counter = 0
    for kind in ("mandatory", "forbidden", "non_functional"):
        for item in project["constraints"].get(kind) or []:
            counter += 1
            entity_id = f"CST-{token}-{counter:03d}"
            _write_entity(
                root,
                f".harness/canonical/CONSTRAINTS/{entity_id}@1.yaml",
                "constraint",
                {
                    "id": entity_id,
                    "revision": 1,
                    "kind": kind.upper(),
                    "statement": _statement(item),
                    "status": "ACTIVE",
                },
            )
            constraint_refs.append(_ref(entity_id))
    for index, item in enumerate(project.get("assumptions") or [], 1):
        entity_id = f"ASM-{token}-{index:03d}"
        value = item if isinstance(item, dict) else {"statement": str(item)}
        _write_entity(
            root,
            f".harness/canonical/CONSTRAINTS/{entity_id}@1.yaml",
            "assumption",
            {
                "id": entity_id,
                "revision": 1,
                "statement": value.get("statement"),
                "owner": value.get("owner", "ACT-USER-001"),
                "review_trigger": value.get("review_trigger"),
                "status": "ACTIVE",
            },
        )
        assumption_refs.append(_ref(entity_id))
    for index, item in enumerate(project.get("unknowns") or [], 1):
        entity_id = f"UNK-{token}-{index:03d}"
        value = item if isinstance(item, dict) else {"question": str(item)}
        _write_entity(
            root,
            f".harness/canonical/CONSTRAINTS/{entity_id}@1.yaml",
            "unknown",
            {
                "id": entity_id,
                "revision": 1,
                "question": value.get("question") or value.get("statement"),
                "owner": value.get("owner", "ACT-USER-001"),
                "decision_plan": value.get("decision_plan"),
                "blocking": bool(value.get("blocking", False)),
                "status": "OPEN",
            },
        )
        unknown_refs.append(_ref(entity_id))
    return constraint_refs, assumption_refs, unknown_refs


def _create_intake_records(root: Path, workspace: Path, project_input: dict[str, Any], token: str) -> tuple[str, str, str]:
    state = load_data(workspace / "STATE.yaml")["state"]
    session_id = state["session_ref"]
    questionnaire_id = state["questionnaire_ref"]
    source_inventory = _copy_intake_sources(workspace, root, load_data(workspace / "SOURCE_INVENTORY.yaml"))
    source_id = source_inventory["source_inventory"]["id"]
    write_data(root / f".harness/intake/INVENTORIES/{source_id}@1.yaml", source_inventory)
    session = load_data(workspace / "SESSION.yaml")["session"]
    session.update(
        {
            "status": "COMPLETED",
            "project_ref": slugify(project_input["project"]["name"]),
            "provisional_workspace": "EXTERNAL_PROVISIONAL_WORKSPACE",
            "updated_at": utc_now(),
            "completed_at": utc_now(),
        }
    )
    _write_entity(root, f".harness/sessions/{session_id}@1.yaml", "session", session)
    questions = []
    answers = []
    for index, q in enumerate(QUESTION_BANK, 1):
        value = deep_get(project_input, q["field"])
        q_record = deepcopy(q)
        q_record.update(
            {
                "session_ref": questionnaire_id,
                "status": "ANSWERED" if nonempty(value) else "SKIPPED",
                "revision": 1,
            }
        )
        _write_entity(root, f".harness/intake/QUESTIONS/{q['id']}@1.yaml", "question", q_record)
        questions.append(q["id"])
        if nonempty(value):
            answer_id = f"ANS-{token}-{index:03d}"
            _write_entity(
                root,
                f".harness/intake/ANSWERS/{answer_id}.yaml",
                "answer",
                {
                    "id": answer_id,
                    "question_ref": q["id"],
                    "actor_ref": "ACT-USER-001",
                    "value": value,
                    "confidence": "CONFIRMED",
                    "source_refs": [],
                    "answered_at": utc_now(),
                },
            )
            answers.append(answer_id)
    questionnaire = {
        "id": questionnaire_id,
        "intake_session_ref": session_id,
        "project_mode": project_input["project"]["mode"],
        "source_inventory_ref": source_id,
        "question_budget": {"target": 10, "hard_limit_before_draft": 15, "asked": len(questions), "answered": len(answers)},
        "question_refs": questions,
        "answer_refs": answers,
        "status": "COMPLETED",
    }
    _write_entity(root, f".harness/intake/QUESTIONNAIRES/{questionnaire_id}@1.yaml", "questionnaire_session", questionnaire)
    if (workspace / "REPOSITORY_INVENTORY.yaml").exists():
        riv = load_data(workspace / "REPOSITORY_INVENTORY.yaml")
        riv["repository_inventory"]["repository_path"] = "."
        write_data(
            root / f".harness/intake/INVENTORIES/{riv['repository_inventory']['id']}@1.yaml",
            riv,
        )
    return session_id, questionnaire_id, source_id


def _create_baselines(
    root: Path,
    project_input: dict[str, Any],
    token: str,
    session_id: str,
    source_id: str,
    requirement_refs: list[str],
    success_refs: list[str],
    constraint_refs: list[str],
    assumption_refs: list[str],
    unknown_refs: list[str],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    project = project_input["project"]
    approvals = project_input["approvals"]
    scope_id = f"SCP-{token}-001"
    _write_entity(
        root,
        f".harness/canonical/DEFINITION/{scope_id}@1.yaml",
        "scope",
        {"id": scope_id, "revision": 1, "in": project["scope"]["in"], "out": project["scope"]["out"], "status": "ACTIVE"},
    )
    decision_id = f"DEC-{token}-PROJECT-001"
    _write_entity(
        root,
        f".harness/canonical/DECISIONS/{decision_id}@1.yaml",
        "decision",
        {
            "id": decision_id,
            "revision": 1,
            "kind": "PROJECT_DEFINITION_APPROVAL",
            "actor": approvals["project_definition"]["actor"],
            "approved_at": approvals["project_definition"].get("approved_at") or utc_now(),
            "status": "ACCEPTED",
        },
    )
    pjd_id = f"PJD-{token}-001"
    project_definition = {
        "id": pjd_id,
        "revision": 1,
        "status": "ACCEPTED",
        "session_ref": session_id,
        "source_refs": [source_id],
        "name": project["name"],
        "mode": project["mode"],
        "problem_statement": project["problem_statement"],
        "primary_outcome": project["primary_outcome"],
        "user_refs": [f"ACT-USER-{index:03d}" for index, _ in enumerate(project["users"], 1)],
        "outcome_refs": [f"OUT-{token}-001"],
        "goal_refs": [f"GOL-{token}-001"],
        "success_criterion_refs": success_refs,
        "scope_ref": _ref(scope_id),
        "constraint_refs": constraint_refs,
        "assumption_refs": assumption_refs,
        "unknown_refs": unknown_refs,
        "profile_ref": project_input["profile"]["ref"],
        "ambiguity_mode": project.get("ambiguity_mode", "PRAGMATIC"),
        "accepted_by": decision_id,
        "dimension_statuses": {
            "documentation": project["documentation"]["availability"],
            "connectivity": project["connectivity"],
            "platform": "CONFIRMED",
            "data": project["data"]["sensitivity"],
            "integrations": "CONFIRMED",
            "constraints": "CONFIRMED",
            "success": "CONFIRMED",
        },
    }
    pjd_rel = _write_entity(root, f".harness/canonical/DEFINITION/{pjd_id}@1.yaml", "project_definition", project_definition)

    decision_refs: list[str] = []
    for index, item in enumerate(project_input["architecture"].get("decisions") or [], 1):
        adr_id = f"ADR-{token}-{index:03d}"
        value = item if isinstance(item, dict) else {"title": str(item), "decision": str(item)}
        adr = {
            "id": adr_id,
            "revision": 1,
            "title": value.get("title") or f"Architecture decision {index}",
            "decision_type": "MATERIAL_ARCHITECTURE" if value.get("material", True) else "IMPLEMENTATION",
            "status": "ACCEPTED",
            "context": {"driver_refs": requirement_refs, "constraint_refs": constraint_refs},
            "decision": {
                "statement": value.get("decision") or value.get("statement"),
                "rationale": value.get("rationale"),
            },
            "approved_by": approvals["architecture_baseline"]["actor"],
        }
        _write_entity(root, f".harness/canonical/DECISIONS/{adr_id}@1.yaml", "adr", adr)
        decision_refs.append(_ref(adr_id))

    arb_id = f"ARB-{token}-001"
    arch = project_input["architecture"]
    architecture_baseline = {
        "id": arb_id,
        "revision": 1,
        "status": "ACCEPTED",
        "project_definition_ref": _ref(pjd_id),
        "summary": arch["summary"],
        "style": arch["style"],
        "components": arch["components"],
        "interfaces": arch.get("interfaces") or [],
        "data_flow": arch.get("data_flow") or [],
        "quality_attributes": arch.get("quality_attributes") or [],
        "constraints": constraint_refs,
        "decision_refs": decision_refs,
        "risks": arch.get("risks") or [],
        "accepted_by": approvals["architecture_baseline"]["actor"],
    }
    arb_rel = _write_entity(root, f".harness/canonical/ARCHITECTURE/{arb_id}@1.yaml", "architecture_baseline", architecture_baseline)

    tbl_id = f"TBL-{token}-001"
    technology_baseline = {
        "id": tbl_id,
        "revision": 1,
        "status": "ACCEPTED",
        "driver_refs": requirement_refs + constraint_refs,
        "selections": project_input["technology"]["selections"],
        "build_commands": project_input["technology"].get("build_commands") or [],
        "test_commands": project_input["technology"].get("test_commands") or [],
        "lint_commands": project_input["technology"].get("lint_commands") or [],
        "verification_commands": (
            project_input["technology"].get("build_commands", [])
            + project_input["technology"].get("test_commands", [])
            + project_input["technology"].get("lint_commands", [])
        ),
        "accepted_by": approvals["technology_baseline"]["actor"],
    }
    tbl_rel = _write_entity(root, f".harness/canonical/TECHNOLOGY/{tbl_id}@1.yaml", "technology_baseline", technology_baseline)
    return (
        {"value": project_definition, "path": pjd_rel},
        {"value": architecture_baseline, "path": arb_rel},
        {"value": technology_baseline, "path": tbl_rel},
        decision_refs,
    )


def _create_tasks(root: Path, project_input: dict[str, Any], plan: dict[str, Any], token: str, requirement_refs: list[str], constraint_refs: list[str], architecture_ref: str) -> tuple[dict[str, str], dict[str, str]]:
    task_paths: dict[str, str] = {}
    wp_paths: dict[str, str] = {}
    for task in plan["tasks"]:
        task_id = task["id"]
        primary_skill = _primary_skill(task)
        route_in = task.get("route") or {}
        required_caps = route_in.get("required_capabilities") or _default_capabilities(task)
        verification_id = f"VFP-{token}-{task['sequence'] // 10:03d}"
        verification = deepcopy(task.get("verification") or {})
        verification_profile = {
            "id": verification_id,
            "revision": 1,
            "task_ref": _ref(task_id),
            "implementation_stage": task["implementation_stage"],
            "commands": verification.get("commands") or [],
            "expected_paths": verification.get("expected_paths") or [],
            "manual_checks": verification.get("manual_checks") or [],
            "timeout_seconds": int(verification.get("timeout_seconds", 300)),
            "allow_manual": bool(verification.get("allow_manual", False)),
            "status": "ACTIVE",
        }
        _write_entity(root, f".harness/verification/PROFILES/{verification_id}@1.yaml", "verification_profile", verification_profile)

        prompt_plan_id = f"PPL-{token}-{task['sequence'] // 10:03d}"
        context_plan_id = f"CTX-{token}-{task['sequence'] // 10:03d}"
        prompt_plan = {
            "id": prompt_plan_id,
            "revision": 1,
            "task_ref": _ref(task_id),
            "implementation_stage": task["implementation_stage"],
            "prompt_spec_ref": task.get("prompt_spec_ref") or "PSP-IMPLEMENT@1",
            "module_refs": ["PMD-CORE-ROLE@1", "PMD-TASK-CONTRACT@1", "PMD-RESULT-SCHEMA@1"],
            "resolved_inputs": {
                "task_hash": f"sha256:{sha256_bytes(canonical_json_bytes(task))}",
                "skill_ref": primary_skill,
                "context_plan_ref": _ref(context_plan_id),
            },
            "output_schema_ref": "SCHEMA-AGENT-TASK-RESULT@1",
            "status": "RESOLVED",
        }
        _write_entity(root, f".harness/prompts/PLANS/{prompt_plan_id}@1.yaml", "prompt_plan", prompt_plan)
        context_plan = {
            "id": context_plan_id,
            "revision": 1,
            "task_ref": _ref(task_id),
            "implementation_stage": task["implementation_stage"],
            "include": {
                "project_definition": True,
                "architecture_baseline": True,
                "technology_baseline": True,
                "task_dependencies": task.get("depends_on_tasks") or [],
                "read_paths": task.get("context", {}).get("read_paths", task["scope"].get("read") or []),
            },
            "exclude": ["secrets", "unrelated tasks", "provider accounting"],
            "status": "READY",
        }
        _write_entity(root, f".harness/context/PLANS/{context_plan_id}@1.yaml", "context_plan", context_plan)

        contract = {
            "id": task_id,
            "revision": 1,
            "work_package_ref": task["work_package_ref"],
            "implementation_stage": task["implementation_stage"],
            "title": task["title"],
            "type": str(task["type"]).upper(),
            "track": task.get("track", "PRIMARY"),
            "priority": task.get("priority", "NORMAL"),
            "sequence": task["sequence"],
            "purpose": task["purpose"],
            "expected_result": task["expected_result"],
            "requirement_refs": task.get("requirement_refs") or requirement_refs,
            "constraint_refs": task.get("constraint_refs") or constraint_refs,
            "architecture_refs": task.get("architecture_refs") or [architecture_ref],
            "documentation": task.get("documentation") or {
                "source_refs": [],
                "impact": "NONE",
                "required_updates": [],
            },
            "depends_on_tasks": task.get("depends_on_tasks") or [],
            "requires_artifacts": task.get("requires_artifacts") or [],
            "produces_artifacts": task.get("produces_artifacts") or [],
            "scope": task["scope"],
            "route": {
                "primary_skill_ref": primary_skill,
                "supporting_skill_refs": route_in.get("supporting_skill_refs") or [],
                "required_capabilities": required_caps,
            },
            "prompt_spec_ref": prompt_plan["prompt_spec_ref"],
            "prompt_plan_ref": _ref(prompt_plan_id),
            "context_policy_ref": "CTP-TASK-STANDARD@1",
            "context_plan_ref": _ref(context_plan_id),
            "verification_profile_ref": _ref(verification_id),
            "verification": verification,
            "acceptance_criteria": task["acceptance_criteria"],
            "rollback": task.get("rollback") or {"strategy": "RESTORE_PRE_RUN_SNAPSHOT"},
            "status": task["status"],
        }
        rel = f".harness/tasks/{task_id}@1.yaml"
        _write_entity(root, rel, "task", contract)
        task_paths[task_id] = rel

    dag_id = f"DAG-{token}-001"
    write_data(
        root / f".harness/dags/{dag_id}@1.yaml",
        {
            "dependency_graph": {
                "id": dag_id,
                "revision": 1,
                "nodes": plan["task_order"],
                "edges": [
                    {"from": dep, "to": task["id"]}
                    for task in plan["tasks"]
                    for dep in task.get("depends_on_tasks") or []
                ],
                "scheduler_policy": "SINGLE_ACTIVE_TASK",
                "implementation_stage": plan["active_stage"],
                "status": "ACTIVE",
            }
        },
    )
    for wp in plan["work_packages"]:
        value = {
            "id": wp["id"],
            "revision": 1,
            "request_refs": [f"RQ-{token}-PREPARE-001"],
            "title": wp["title"],
            "objective": wp["objective"],
            "implementation_stage": wp["implementation_stage"],
            "requirement_refs": wp.get("requirement_refs") or requirement_refs,
            "architecture_refs": [architecture_ref],
            "documentation_refs": [],
            "mandatory_task_refs": wp["mandatory_task_refs"],
            "dependency_graph_ref": _ref(dag_id),
            "aggregation_rule": "ALL_MANDATORY_PASS",
            "status": wp["status"],
        }
        rel = f".harness/work-packages/{wp['id']}@1.yaml"
        _write_entity(root, rel, "work_package", value)
        wp_paths[wp["id"]] = rel
    write_data(
        root / ".harness/tasks/INDEX.yaml",
        {"task_index": {"order": plan["task_order"], "current": task_paths, "aliases": plan["task_aliases"]}},
    )
    write_data(
        root / ".harness/work-packages/INDEX.yaml",
        {"work_package_index": {"order": [wp["id"] for wp in plan["work_packages"]], "current": wp_paths}},
    )
    return task_paths, wp_paths


def _create_brownfield(
    root: Path,
    workspace: Path,
    project_input: dict[str, Any],
    token: str,
    refs: dict[str, str],
    first_wp: str,
    active_stage: str,
) -> None:
    if project_input["project"]["mode"] not in {"BROWNFIELD", "HYBRID"}:
        return
    inventory_doc = load_data(workspace / "REPOSITORY_INVENTORY.yaml")
    inventory = inventory_doc["repository_inventory"]
    bfi_id = f"BFI-{token}-001"
    bfb_id = f"BFB-{token}-001"
    decision_id = f"DEC-{token}-BROWNFIELD-001"
    test_id = f"TSB-{token}-001"
    approval = project_input["approvals"].get("brownfield_baseline")
    if not isinstance(approval, dict) or approval.get("approved") is not True:
        raise ValidationFailure("Explicit Brownfield Baseline approval is required")
    approved_at = approval.get("approved_at") or utc_now()
    actor = approval.get("actor")
    if not actor:
        raise ValidationFailure("Brownfield Baseline approval actor is required")
    _write_entity(
        root,
        f".harness/verification/BASELINES/{test_id}@1.yaml",
        "test_baseline",
        {
            "id": test_id,
            "revision": 1,
            "candidate_commands": inventory.get("candidate_commands") or {},
            "known_test_paths": inventory.get("test_paths") or [],
            "status": "ACTIVE",
        },
    )
    _write_entity(
        root,
        f".harness/intake/BROWNFIELD/{bfi_id}@1.yaml",
        "brownfield_intake",
        {
            "id": bfi_id,
            "revision": 1,
            "session_ref": refs["session"],
            "repository_inventory_ref": _ref(inventory["id"]),
            "mode": "READ_ONLY_DISCOVERY_THEN_HANDOFF_COPY",
            "status": "ACCEPTED",
        },
    )
    _write_entity(
        root,
        f".harness/canonical/DECISIONS/{decision_id}@1.yaml",
        "decision",
        {
            "id": decision_id,
            "revision": 1,
            "kind": "BROWNFIELD_BASELINE_APPROVAL",
            "actor": actor,
            "approved_at": approved_at,
            "subject_ref": _ref(bfb_id),
            "status": "ACCEPTED",
        },
    )
    _write_entity(
        root,
        f".harness/canonical/DEFINITION/BROWNFIELD/{bfb_id}@1.yaml",
        "brownfield_baseline",
        {
            "id": bfb_id,
            "revision": 1,
            "repository_revision": inventory["repository_revision"],
            "status": "ACCEPTED",
            "accepted_actual_structure_ref": _ref(inventory["id"]),
            "project_definition_ref": refs["project_definition"],
            "architecture_baseline_ref": refs["architecture_baseline"],
            "technology_baseline_ref": refs["technology_baseline"],
            "test_baseline_ref": _ref(test_id),
            "accepted_by": decision_id,
            "accepted_at": approved_at,
            "known_gaps": project_input["brownfield"].get("known_gaps") or [],
            "known_defects": project_input["brownfield"].get("known_defects") or [],
            "technical_debt_items": project_input["brownfield"].get("technical_debt") or [],
            "documentation_conflicts": project_input["brownfield"].get("documentation_conflicts") or [],
        },
    )
    routes = [
        ("CONTINUE_DEVELOPMENT", "Продолжить принятую разработку", "Deliver accepted roadmap outcomes"),
        ("FIX_KNOWN_BUGS", "Исправить известные дефекты", "Reduce verified defects without architectural drift"),
        ("IMPROVE_PROJECT", "Улучшить проект", "Separate architecture/security/performance/test improvements"),
        ("STABILIZE_BASELINE", "Стабилизировать baseline", "Restore reliable build/test/documentation prerequisites"),
    ]
    route_refs: list[str] = []
    for index, (route, title, value) in enumerate(routes, 1):
        route_token = route.split("_")[0]
        wp_id = f"WP-{token}-ROUTE-{route_token}"
        _write_entity(
            root,
            f".harness/work-packages/{wp_id}@1.yaml",
            "work_package",
            {
                "id": wp_id,
                "revision": 1,
                "title": title,
                "objective": value,
                "implementation_stage": active_stage,
                "mandatory_task_refs": [],
                "status": "DRAFT",
            },
        )
        bri_id = f"BRI-{token}-{index:03d}"
        _write_entity(
            root,
            f".harness/work-packages/ROUTE_PORTFOLIO/{bri_id}@1.yaml",
            "brownfield_route_item",
            {
                "id": bri_id,
                "route": route,
                "title": title,
                "evidence_refs": [_ref(inventory["id"]), _ref(bfb_id)],
                "estimated_risk": "TO_ASSESS",
                "value": value,
                "proposed_work_package_ref": first_wp if route == "CONTINUE_DEVELOPMENT" else wp_id,
                "status": "PROPOSED",
            },
        )
        route_refs.append(_ref(bri_id))
    write_data(root / ".harness/work-packages/ROUTE_PORTFOLIO/INDEX.yaml", {"brownfield_route_portfolio": {"route_refs": route_refs, "status": "PROPOSED"}})


def _create_request_records(root: Path, token: str, project_ref: str, session_id: str, first_wp: str) -> None:
    request_id = f"RQ-{token}-PREPARE-001"
    plan_id = f"RQP-{token}-PREPARE-001"
    correlation = f"COR-{token}-PREPARE-001"
    request = {
        "id": request_id,
        "schema_version": 1,
        "project_ref": project_ref,
        "session_ref": session_id,
        "correlation_id": correlation,
        "idempotency_key": f"sha256:{sha256_bytes(f'{project_ref}:PREPARE_FOR_CODEX'.encode())}",
        "input": {"raw_text": "Prepare accepted project for Codex", "source_refs": [], "actor_ref": "ACT-USER-001", "received_at": utc_now()},
        "classification": {"request_class": "PROJECT_START", "mode": "PLAN", "confidence": 1.0, "material_ambiguity_refs": []},
        "status": "CLASSIFIED",
    }
    _write_entity(root, f".harness/requests/REQUESTS/{request_id}.yaml", "request", request)
    request_plan = {
        "id": plan_id,
        "request_ref": request_id,
        "project_ref": project_ref,
        "base_project_revision": "PRE_BOOTSTRAP",
        "objective": "Create a validated Browser GPT to Codex handoff package",
        "request_class": "PROJECT_START",
        "mode": "PLAN",
        "routes": [
            {"id": f"RTE-{token}-INTAKE", "sequence": 10, "operation": "START_INTAKE", "depends_on": []},
            {"id": f"RTE-{token}-HANDOFF", "sequence": 20, "operation": "PREPARE_HANDOFF", "depends_on": [f"RTE-{token}-INTAKE"]},
        ],
        "work_package_refs": [first_wp],
        "status": "COMPLETED",
    }
    _write_entity(root, f".harness/requests/PLANS/{plan_id}@1.yaml", "request_plan", request_plan)
    trace_id = f"TRT-{token}-PREPARE-001"
    _write_entity(
        root,
        f".harness/requests/TRACES/{trace_id}.yaml",
        "request_trace",
        {
            "id": trace_id,
            "request_ref": request_id,
            "events": [
                {"operation": "START_INTAKE", "status": "COMPLETED"},
                {"operation": "PREPARE_HANDOFF", "status": "COMPLETED"},
            ],
            "created_at": utc_now(),
        },
    )


def _create_handoff_instructions(root: Path, project_input: dict[str, Any], first: dict[str, Any]) -> None:
    code_start = f"""# Codex Start

This archive is a validated Project Harness handoff. Open this directory as the repository root.

## Mandatory sequence

1. Validate the handoff:

```bash
python .harness/engine/project-harness.py validate-handoff --project .
```

2. Inspect current state:

```bash
python .harness/engine/project-harness.py status --project .
python .harness/engine/project-harness.py next --project .
```

3. Read only the current compiled prompt:

`{first['prompt_markdown_path']}`

4. Implement only `{first['task_ref']}`. Do not select another task, edit accepted baselines, or write outside declared scope.

5. Run Harness verification and write the Agent Task Result to `.harness/runtime/AGENT_RESULTS/{first['run_ref']}.json`.

6. Complete the transition. Harness will then compile the next READY task JIT.

## Non-negotiable rules

- `.harness/` is machine-owned, except the exact Agent Task Result path.
- A completed task requires an independent verification report with status PASS.
- Material ambiguity becomes a Blocker; it is not resolved by silent redesign.
- Git push, deploy and publication are not granted by this handoff.
- Future prompts are not precompiled. Run `next` after every accepted result.
"""
    agents = """# AGENTS.md

Project Harness governs this repository.

- Read `CODEX_START.md` before changing files.
- Execute only `.harness/state/NEXT_TASK.yaml`.
- Obey task read/write/forbidden scope.
- Do not edit accepted Project Definition, Architecture Baseline or Technology Baseline.
- Do not edit `.harness/` except the current Agent Task Result file.
- Run independent verification before completion.
- Use the Harness blocker command for material ambiguity.
"""
    summary = f"""# Handoff Summary

- Project: **{project_input['project']['name']}**
- Mode: `{project_input['project']['mode']}`
- Profile: `{project_input['profile']['ref']}`
- Engine: `{ENGINE_VERSION}`
- Status: `READY_FOR_CODEX`
- First task: `{first['task_ref']}`
- First run reservation: `{first['run_ref']}`
- First compiled prompt: `{first['prompt_markdown_path']}`
- Future compiled prompts: **0** until their task becomes READY.

The Browser GPT preparation layer produced accepted baselines, a causal task DAG, reusable prompt/context plans, verification profiles and the first JIT bundle. Codex remains the implementation executor.
"""
    atomic_write_text(root / "CODEX_START.md", code_start)
    atomic_write_text(root / "AGENTS.md", agents)
    atomic_write_text(root / "HANDOFF_SUMMARY.md", summary)


@guarded_mutation
def prepare_handoff(workspace: Path, output: Path, *, keep_directory: Path | None = None) -> dict[str, Any]:
    ensure_native_path(workspace, tree=True)
    ensure_native_path(output.parent)
    if keep_directory is not None:
        ensure_native_path(keep_directory, tree=True)
    workspace = workspace.expanduser().resolve()
    checked = check_intake(workspace)
    readiness = checked["readiness"]
    if readiness["status"] == "WAITING_INPUT":
        raise WaitingInput("Project input is incomplete", readiness)
    if readiness["status"] == "WAITING_DECISION":
        raise WaitingDecision("Material approvals are required", readiness)
    if readiness["status"] != "READY_FOR_HANDOFF":
        raise ValidationFailure("Intake is not ready", readiness)
    source_input = load_data(workspace / "PROJECT_INPUT.yaml")
    project_input, _migration = migrate_project_input(source_input)
    strict = validate_project_input(project_input, require_approvals=True)
    if strict["status"] != "READY_FOR_HANDOFF":
        raise ValidationFailure("Project input failed final validation", strict)

    # PH-051-01 defines the opt-in contract, NOT an executor activation route.
    # Reject automatic preparation rather than claim validated profiles/doctor
    # before PH-051-02..09 provide a trusted container-backed activation path.
    if project_input["execution"]["mode"] != "MANUAL_HANDOFF":
        exact_execution_profile_bindings(workspace, project_input["execution"])
        raise ValidationFailure(
            "LOCAL_AUTOMATIC activation is unavailable until executor and sandbox are implemented and verified",
            {"reason": "AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED", "stage": "PH-051-01"},
        )
    project = project_input["project"]
    slug = project.get("slug") or slugify(project["name"])
    token = id_token(slug)
    generated_at = deep_get(project_input, "metadata.generated_at") or utc_now()
    output = output.expanduser().resolve()
    if output.suffix.lower() != ".zip":
        output = output / f"{slug}_Codex_Handoff_v1.zip"

    with tempfile.TemporaryDirectory(prefix="project-harness-handoff-") as temp_name:
        temp_root = Path(temp_name)
        handoff_root = temp_root / f"{slug}_Codex_Handoff_v1"
        handoff_root.mkdir(parents=True)

        intake_state = load_data(workspace / "STATE.yaml")["state"]
        if project["mode"] in {"BROWNFIELD", "HYBRID"}:
            effective = Path(intake_state["effective_repository_path"])
            current_inventory = build_repository_inventory(effective, session_ref=intake_state["session_ref"])
            expected_digest = intake_state.get("repository_tree_digest")
            actual_digest = current_inventory["repository_inventory"]["tree_digest"]
            if expected_digest != actual_digest:
                raise ValidationFailure(
                    "Repository changed after read-only intake; restart intake or explicitly refresh the baseline",
                    {"expected": expected_digest, "actual": actual_digest},
                )
            copy_tree_filtered(effective, handoff_root)
        else:
            atomic_write_text(
                handoff_root / "README.md",
                f"# {project['name']}\n\n{project['primary_outcome']}\n\nImplementation is governed by `CODEX_START.md`.\n",
            )

        # Canonical directory skeleton.
        directories = [
            ".harness/config", ".harness/registries", ".harness/sessions",
            ".harness/requests/REQUESTS", ".harness/requests/PLANS", ".harness/requests/RESULTS", ".harness/requests/TRACES",
            ".harness/intake/INVENTORIES", ".harness/intake/QUESTIONNAIRES", ".harness/intake/QUESTIONS", ".harness/intake/ANSWERS", ".harness/intake/BROWNFIELD",
            ".harness/canonical/DEFINITION", ".harness/canonical/REQUIREMENTS", ".harness/canonical/CONSTRAINTS", ".harness/canonical/DECISIONS", ".harness/canonical/ARCHITECTURE", ".harness/canonical/TECHNOLOGY", ".harness/canonical/DOCUMENTATION",
            ".harness/work-packages/ROUTE_PROPOSALS", ".harness/tasks", ".harness/dags",
            ".harness/prompts/PLANS", ".harness/prompts/BUNDLES_BY_RUN",
            ".harness/context/PLANS", ".harness/context/PACKETS_BY_RUN",
            ".harness/skills/ACTIVE", ".harness/skills/DRAFT", ".harness/skills/VALIDATING", ".harness/skills/VALIDATED", ".harness/skills/REJECTED", ".harness/skills/SUSPENDED", ".harness/skills/DEPRECATED", ".harness/skills/RETIRED", ".harness/skills/EVALUATIONS", ".harness/skills/MIGRATIONS",
            ".harness/verification/PROFILES", ".harness/verification/TEST_ENVIRONMENTS", ".harness/verification/BASELINES",
            ".harness/runtime/RUN_PLANS", ".harness/runtime/RUNS", ".harness/runtime/AGENT_RESULTS", ".harness/runtime/TOOL_INVOCATIONS", ".harness/runtime/CAPABILITY_GRANTS", ".harness/runtime/SNAPSHOTS", ".harness/runtime/OPERATION_JOURNAL",
            ".harness/evidence", ".harness/reports", ".harness/blockers", ".harness/changes/BOOTSTRAP", ".harness/events", ".harness/state", ".harness/incoming/SOURCES",
            ".harness/stages/PLANS", ".harness/stages/GATES", ".harness/stages/ACCEPTANCE", ".harness/stages/ASSESSMENTS", ".harness/stages/STATE_HISTORY", ".harness/stages/TRANSACTIONS",
        ]
        for relative in directories:
            (handoff_root / relative).mkdir(parents=True, exist_ok=True)

        distribution = distribution_root()
        for registry_file in sorted((distribution / "registries").glob("*.yaml")):
            shutil.copy2(registry_file, handoff_root / ".harness/registries" / registry_file.name)
        _copy_runtime(handoff_root)

        session_id, questionnaire_id, source_id = _create_intake_records(handoff_root, workspace, project_input, token)
        requirement_refs, success_refs, _ = _create_requirements(handoff_root, project_input, token)
        constraint_refs, assumption_refs, unknown_refs = _create_constraints(handoff_root, project_input, token)
        pjd, arb, tbl, decision_refs = _create_baselines(
            handoff_root, project_input, token, session_id, source_id,
            requirement_refs, success_refs, constraint_refs, assumption_refs, unknown_refs,
        )
        plan = normalize_plan(project_input, token)
        task_paths, wp_paths = _create_tasks(
            handoff_root, project_input, plan, token,
            requirement_refs, constraint_refs, _ref(arb["value"]["id"]),
        )
        implementation = create_initial_stage_artifacts(
            handoff_root,
            project_input,
            token=token,
            baseline_ref=_ref(pjd["value"]["id"]),
            scope_refs=requirement_refs,
            work_package_refs=[_ref(wp["id"]) for wp in plan["work_packages"]],
        )
        skill_refs, _ = _seed_skills(handoff_root, project_input)
        first_wp = plan["work_packages"][0]["id"]
        _create_brownfield(
            handoff_root, workspace, project_input, token,
            {
                "session": session_id,
                "project_definition": _ref(pjd["value"]["id"]),
                "architecture_baseline": _ref(arb["value"]["id"]),
                "technology_baseline": _ref(tbl["value"]["id"]),
            },
            first_wp,
            implementation["active_stage"],
        )
        _create_request_records(handoff_root, token, slug, session_id, first_wp)

        bootstrap_id = f"BST-{token}-001"
        _write_entity(
            handoff_root,
            f".harness/changes/BOOTSTRAP/{bootstrap_id}@1.yaml",
            "bootstrap_plan",
            {
                "id": bootstrap_id,
                "revision": 1,
                "project_ref": slug,
                "mode": project["mode"],
                "base_revision": "PROVISIONAL_INTAKE_ACCEPTED",
                "repository_actions": ["COPY_ACCEPTED_BROWNFIELD_SNAPSHOT"] if project["mode"] != "GREENFIELD" else ["CREATE_EMPTY_PRODUCT_ROOT"],
                "directory_actions": directories,
                "build_toolchain_actions": [],
                "test_environment_actions": [],
                "documentation_actions": ["GENERATE_HUMAN_VIEWS", "GENERATE_CODEX_START"],
                "harness_instance_actions": ["INSTALL_PROJECT_CONTROL_PLANE", "PIN_PROJECT_LOCK"],
                "verification_profile_ref": "VFP-HANDOFF-001@1",
                "rollback": "remove generated handoff directory; original sources remain unchanged",
                "status": "COMPLETED",
            },
        )

        versions, digests = registry_lock(distribution)
        project_lock = {
            "harness_distribution": ENGINE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "registry_versions": versions,
            "registry_digests": digests,
            "profile_refs": [project_input["profile"]["ref"]],
            "adapter_refs": ["ADP-CODEX@1"],
            "execution": deepcopy(project_input["execution"]),
            "execution_profile_bindings": {
                "adapter": {"ref": None, "digest": None},
                "sandbox": {"ref": None, "digest": None},
            },
            "skill_refs": skill_refs,
            "prompt_spec_refs": ["PSP-IMPLEMENT@1"],
            "migrations_applied": [
                "MIG-DOC-0.3.1-TO-0.4.0",
                "MIG-ENGINE-0.4.0-TO-0.4.1",
                PROJECT_INPUT_MIGRATION_ID,
                EXECUTION_POLICY_MIGRATION_ID,
            ],
            "created_at": generated_at,
        }
        write_data(handoff_root / ".harness/config/PROJECT_LOCK.yaml", {"project_lock": project_lock})
        project_config = {
            "id": slug,
            "id_token": token,
            "name": project["name"],
            "harness_schema_version": SCHEMA_VERSION,
            "lifecycle_mode": project["mode"],
            "profile_ref": project_input["profile"]["ref"],
            "project_definition_ref": _ref(pjd["value"]["id"]),
            "architecture_baseline_ref": _ref(arb["value"]["id"]),
            "technology_baseline_ref": _ref(tbl["value"]["id"]),
            "target_implementation_level": implementation["target_level"],
            "stage_state_ref": ".harness/stages/STAGE_STATE.yaml",
            "state_ref": ".harness/state/CURRENT_STATE.yaml",
            "ambiguity_mode": project.get("ambiguity_mode", "PRAGMATIC"),
            "project_lock_ref": ".harness/config/PROJECT_LOCK.yaml",
        }
        write_data(handoff_root / ".harness/config/PROJECT.yaml", {"project": project_config})

        state = {
            "project_ref": slug,
            "project_status": "ACTIVE",
            "handoff_status": "PREPARING",
            "scheduler_policy": "SINGLE_ACTIVE_TASK",
            "active_stage": implementation["active_stage"],
            "target_implementation_level": implementation["target_level"],
            "task_order": plan["task_order"],
            "current_task_ref": plan["task_order"][0],
            "completed_task_refs": [],
            "blocked_task_refs": [],
            "task_report_refs": [],
            "attempts": {},
            "active_run": None,
            "entity_paths": {
                "project_definition": pjd["path"],
                "architecture_baseline": arb["path"],
                "technology_baseline": tbl["path"],
            },
            "next_route": "COMPILE_FIRST_READY_TASK",
            "created_at": generated_at,
            "updated_at": generated_at,
        }
        write_data(handoff_root / ".harness/state/CURRENT_STATE.yaml", {"state": state})
        write_data(handoff_root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml", project_input)
        render_project_documents(handoff_root, project_input, plan)
        first = reserve_run(handoff_root)
        state_doc = load_data(handoff_root / ".harness/state/CURRENT_STATE.yaml")
        state_doc["state"]["handoff_status"] = "READY_FOR_CODEX"
        state_doc["state"]["updated_at"] = generated_at
        write_data(handoff_root / ".harness/state/CURRENT_STATE.yaml", state_doc)
        render_status(handoff_root)
        _create_handoff_instructions(handoff_root, project_input, first)

        # Structural validation runs before the manifest; manifest is checked once written.
        from .validation import validate_handoff_directory
        preliminary = validate_handoff_directory(handoff_root, check_manifest=False, check_control_plane_state=False)
        write_data(
            handoff_root / "VALIDATION_REPORT.json",
            {
                "validation_report": {
                    **preliminary,
                    "validation_scope": "STRUCTURE_BEFORE_MANIFEST",
                    "manifest_note": "MANIFEST.sha256 is generated after this immutable report and verified by the prepare command and validate-handoff.",
                }
            },
        )
        result_id = f"RES-{token}-HANDOFF-001"
        result_envelope = {
            "id": result_id,
            "request_ref": f"RQ-{token}-PREPARE-001",
            "correlation_id": f"COR-{token}-PREPARE-001",
            "project_ref": slug,
            "work_package_ref": first_wp,
            "task_ref": first["task_ref"],
            "run_ref": first["run_ref"],
            "status": "COMPLETED",
            "title": "Codex handoff prepared",
            "summary": "Accepted project model, causal tasks, reusable plans and the first JIT prompt bundle are ready for Codex.",
            "changes": {"added": [], "changed": [], "removed": []},
            "verification": {"status": preliminary["status"], "checks": preliminary["checks"]},
            "documentation": {"status": "UPDATED", "updated_refs": ["PROJECT.md", "ARCHITECTURE.md", "TECHNOLOGY.md", "ROADMAP.md", "STATUS.md"]},
            "blockers": [],
            "recovery_options": [],
            "next_step": {"route": "EXECUTE_CURRENT_TASK_WITH_CODEX", "task_ref": first["task_ref"], "requires_user_action": False},
        }
        _write_entity(handoff_root, f".harness/requests/RESULTS/{result_id}.yaml", "result", result_envelope)
        write_data(
            handoff_root / ".harness/state/HANDOFF_RESULT.json",
            {
                "status": "READY_FOR_CODEX",
                "project_ref": slug,
                "first_task_ref": first["task_ref"],
                "first_run_ref": first["run_ref"],
                "first_prompt": first["prompt_markdown_path"],
                "future_compiled_prompt_count": 0,
                "generated_at": generated_at,
            },
        )
        atomic_write_text(handoff_root / "MANIFEST.sha256", build_manifest(handoff_root))
        sealed_state = load_data(handoff_root / ".harness/state/CURRENT_STATE.yaml")["state"]
        sealed_active = sealed_state.get("active_run")
        if not isinstance(sealed_active, dict):
            raise ValidationFailure("Prepared handoff lost its active Run before sealing")
        record_phase_boundary(
            handoff_root,
            sealed_active,
            phase="HANDOFF_SEALED",
            kernel_written_paths=[
                ".harness/state/CURRENT_STATE.yaml",
                ".harness/state/HANDOFF_RESULT.json",
                f".harness/requests/RESULTS/{result_id}.yaml",
                "CODEX_START.md",
                "AGENTS.md",
                "HANDOFF_SUMMARY.md",
                "VALIDATION_REPORT.json",
                "MANIFEST.sha256",
                "STATUS.md",
            ],
            recorded_at=generated_at,
        )
        final_validation = validate_handoff_directory(handoff_root, check_manifest=True, check_control_plane_state=True)
        if final_validation["status"] != "PASS":
            raise ValidationFailure("Generated handoff failed validation", final_validation)

        if keep_directory:
            keep_directory = keep_directory.expanduser().resolve()
            if keep_directory.exists():
                shutil.rmtree(_native_io_path(keep_directory))
            shutil.copytree(_native_io_path(handoff_root), _native_io_path(keep_directory))
        zip_directory(handoff_root, output, timestamp=generated_at)

    return {
        "status": "READY_FOR_CODEX",
        "project_ref": slug,
        "handoff_archive": str(output),
        "sha256": f"sha256:{sha256_file(output)}",
        "first_task_ref": first["task_ref"],
        "first_run_ref": first["run_ref"],
        "validation": final_validation,
        "directory_output": str(keep_directory) if keep_directory else None,
    }

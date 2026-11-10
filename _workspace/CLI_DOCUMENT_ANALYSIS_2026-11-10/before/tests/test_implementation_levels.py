from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from project_harness.errors import ValidationFailure
from project_harness.evidence import normalized_evidence_body, write_normalized_evidence
from project_harness.hashing import sha256_file
from project_harness.maintenance import start_maintenance
from project_harness.project_input import validate_project_input
from project_harness.prompting import reserve_run
from project_harness.registry import implementation_level_model, load_registries, validate_implementation_levels
from project_harness.runtime import complete_current, next_task, verify_current
from project_harness.stage_gate_lifecycle import resume_stage_gate
from project_harness.serialization import load_data, write_data
from project_harness.stages import (
    _product_baseline_revision,
    accept_stage,
    assess_maturity,
    canonical_levels,
    level_up,
    load_stage_state,
    stage_status,
)
from project_harness.validation import validate_project_directory

from tests.maintenance_fixtures import maintenance_plan_document
from tests.test_engine import (
    add_brownfield_approval,
    implement_first_task,
    implement_second_task,
    load_fixture,
    prepare_demo,
    write_agent_result,
)


APPROVED_AT = "2026-08-18T12:00:00Z"
ACTOR = "ACT-STAGE-APPROVER-001"


def complete_prototype(root: Path) -> None:
    implement_first_task(root)
    verification = verify_current(root, allow_command_execution=True)
    complete_current(root, write_agent_result(root, verification, "Implemented add/list"))
    implement_second_task(root)
    verification = verify_current(root, allow_command_execution=True)
    result = complete_current(root, write_agent_result(root, verification, "Implemented done"))
    if result.get("stage_gate", {}).get("status") != "STAGE_ACCEPTANCE_PREPARATION":
        raise AssertionError(result)
    verification = verify_current(root, allow_command_execution=True)
    result = complete_current(root, write_agent_result(root, verification, "Prepared bounded final Gate evidence work"))
    if result.get("stage_gate", {}).get("status") != "BLOCKED":
        raise AssertionError(result)
    # Preparation verification cannot forge proofs. The independent operator
    # supplies exact, reviewable sources only after the active Run ends.
    from tests.gate_proof_fixtures import all_gate_subjects
    all_gate_subjects(root)
    resumed = resume_stage_gate(root)
    if resumed.get("status") != "VERIFYING":
        raise AssertionError(resumed)


def current_gate(root: Path, level: str) -> dict:
    index = load_data(root / ".harness/stages/GATES/INDEX.yaml")["stage_gate_index"]
    gate_id = index["by_level"][level]
    return load_data(root / index["current"][gate_id])["stage_gate"]


def _materialize_gate_evidence(root: Path, gate: dict) -> dict[str, str]:
    # Semantic fixtures use actual per-subject sources, never a generic
    # synthetic PASS report promoted into arbitrary evidence kinds.
    from tests.gate_proof_fixtures import proof_for_subject
    model = implementation_level_model()
    overrides = {str(item["key"]): item for item in (gate.get("hard_constraint_overrides") or []) if isinstance(item, dict)}
    result = {}
    for item in gate["criteria_results"]:
        ref = str(item["criterion_ref"])
        required = model["criteria"][ref]["required_evidence_kinds"] if ref in model["criteria"] else overrides[ref]["required_evidence_kinds"]
        result[ref] = proof_for_subject(root, ref, str(required[0]))
    return result


def closed_criteria(
    root: Path,
    gate: dict,
    *,
    first_status: str = "PASS",
    omit_na_validator: bool = False,
) -> list[dict]:
    evidence_by_criterion = _materialize_gate_evidence(root, gate)
    results: list[dict] = []
    for index, item in enumerate(gate["criteria_results"]):
        status = first_status if index == 0 else "PASS"
        if status == "NOT_APPLICABLE":
            result = {
                "criterion_ref": item["criterion_ref"],
                "status": status,
                "evidence_refs": [],
                "rationale": "Criterion is explicitly inapplicable to this bounded local CLI.",
                "validator": None if omit_na_validator else ACTOR,
            }
        else:
            result = {
                "criterion_ref": item["criterion_ref"],
                "status": status,
                "evidence_refs": [evidence_by_criterion[item["criterion_ref"]]] if status == "PASS" else [],
                "rationale": "Accepted test evidence.",
                "validator": ACTOR,
            }
        results.append(result)
    return results


def stage_approval(root: Path, level: str, *, decision_suffix: str, method: str = "EXECUTED_STAGE_WORK",
                   criteria_results: list[dict] | None = None, extra: dict | None = None) -> dict:
    gate = current_gate(root, level)
    record = {
        "id": f"DEC-HARNESS-DEMO-STAGE-{decision_suffix}",
        "approved": True,
        "actor": ACTOR,
        "approved_at": APPROVED_AT,
        "level": level,
        "acceptance_method": method,
        "baseline_revision": _product_baseline_revision(root),
        "criteria_results": criteria_results if criteria_results is not None else closed_criteria(root, gate),
        "evidence_refs": [],
        "permitted_use": {
            "users": ["DEVELOPER"],
            "environments": ["LOCAL"],
            "data_classes": ["PUBLIC"],
            "data_constraints": ["SYNTHETIC_ONLY"],
        },
        "known_limitations": ["Single local process only."],
        "next_stage_gaps": ["Re-plan the next stage from the accepted baseline."],
        "notes": "Formal stage approval fixture.",
    }
    if extra:
        record.update(extra)
    return {"stage_approval": record}


def write_approval(base: Path, name: str, value: dict) -> Path:
    path = base / name
    write_data(path, value)
    return path


class ImplementationLevelTests(unittest.TestCase):
    def test_01_registry_graph_and_input_decision_semantics(self) -> None:
        registries = load_registries()
        model = implementation_level_model(registries)
        self.assertEqual(canonical_levels(), ("PROTOTYPE", "ALPHA", "BETA", "MVP", "RELEASE"))
        self.assertEqual(model["initial"], "PROTOTYPE")
        self.assertEqual(model["final"], "RELEASE")
        self.assertEqual(model["levels"]["MVP"]["display_name"], "Production MVP")

        duplicate = deepcopy(registries["implementation_levels"])
        duplicate["registry"]["levels"][1]["ordinal"] = 1
        with self.assertRaises(ValidationFailure):
            validate_implementation_levels(duplicate)

        cycle = deepcopy(registries["implementation_levels"])
        cycle["registry"]["levels"][-1]["next"] = "PROTOTYPE"
        with self.assertRaises(ValidationFailure):
            validate_implementation_levels(cycle)

        unsure = load_fixture()
        unsure["implementation"]["target_level"] = "UNSURE"
        result = validate_project_input(unsure, require_approvals=True)
        self.assertEqual(result["status"], "WAITING_DECISION")
        self.assertIn(result["implementation_recommendation"]["recommended_level"], canonical_levels())
        self.assertEqual(unsure["implementation"]["target_level"], "UNSURE")

        invalid = load_fixture()
        invalid["implementation"]["target_level"] = "PRODUCTION"
        self.assertEqual(validate_project_input(invalid)["status"], "INVALID")

        invalid_greenfield = load_fixture()
        invalid_greenfield["implementation"]["claimed_current_level"] = "BETA"
        self.assertEqual(validate_project_input(invalid_greenfield)["status"], "INVALID")

        brownfield = load_fixture()
        brownfield["project"]["mode"] = "BROWNFIELD"
        brownfield["implementation"].pop("claimed_current_level")
        result = validate_project_input(brownfield)
        self.assertEqual(result["status"], "WAITING_INPUT")
        self.assertIn("implementation.claimed_current_level", result["missing_fields"])

    def test_02_stage_planning_is_sequential_and_only_active_stage_is_detailed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            state = load_stage_state(root)
            self.assertEqual(state["stage_path"], ["PROTOTYPE", "ALPHA", "BETA", "MVP"])
            self.assertEqual(state["active_stage"], "PROTOTYPE")
            plan_index = load_data(root / ".harness/stages/PLANS/INDEX.yaml")["stage_plan_index"]
            self.assertEqual(list(plan_index["by_level"]), state["stage_path"])
            for level in state["stage_path"]:
                plan_id = plan_index["by_level"][level]
                plan = load_data(root / plan_index["current"][plan_id])["stage_plan"]
                if level == "PROTOTYPE":
                    self.assertEqual(plan["status"], "ACTIVE")
                    self.assertTrue(plan["detailed_work_package_refs"])
                else:
                    self.assertEqual(plan["status"], "PLANNED")
                    self.assertEqual(plan["detailed_work_package_refs"], [])

            task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
            for rel in task_index["current"].values():
                self.assertEqual(load_data(root / rel)["task"]["implementation_stage"], "PROTOTYPE")
            for path in (root / ".harness/prompts/PLANS").glob("PPL-*@*.yaml"):
                self.assertEqual(load_data(path)["prompt_plan"]["implementation_stage"], "PROTOTYPE")
            bundles = list((root / ".harness/prompts/BUNDLES_BY_RUN").glob("CPB-*.yaml"))
            self.assertEqual(len(bundles), 1)
            prompt_text = bundles[0].with_suffix(".md").read_text(encoding="utf-8")
            self.assertIn("CURRENT_IMPLEMENTATION_STAGE: PROTOTYPE", prompt_text)
            self.assertIn("TARGET_IMPLEMENTATION_LEVEL: MVP", prompt_text)
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_03_runtime_rejects_task_from_future_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            task_id = state["current_task_ref"]
            task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
            task_path = root / task_index["current"][task_id]
            task_doc = load_data(task_path)
            task_doc["task"]["implementation_stage"] = "ALPHA"
            write_data(task_path, task_doc)
            with self.assertRaisesRegex(ValidationFailure, "STAGE_SCOPE_VIOLATION"):
                reserve_run(root, task_id)

    def test_04_gate_rejects_unknown_and_unjustified_na_then_accepts_immutable_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            data = load_fixture()
            data["implementation"]["target_level"] = "PROTOTYPE"
            _, _, root = prepare_demo(base, data=data)
            complete_prototype(root)
            gate = current_gate(root, "PROTOTYPE")
            self.assertEqual(gate["status"], "VERIFYING")

            unknown = stage_approval(
                root,
                "PROTOTYPE",
                decision_suffix="UNKNOWN-001",
                criteria_results=closed_criteria(root, gate, first_status="UNKNOWN"),
            )
            blocked = accept_stage(root, "PROTOTYPE", write_approval(base, "unknown.yaml", unknown))
            self.assertEqual(blocked["status"], "BLOCKED")
            self.assertEqual(blocked["next_route"], "RESOLVE_STAGE_GATE")
            self.assertEqual(next_task(root)["blocker_kind"], "STAGE_GATE_BLOCKER")
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "NONE")
            resumed = resume_stage_gate(root)
            self.assertEqual(resumed["status"], "VERIFYING")

            gate = current_gate(root, "PROTOTYPE")
            invalid_na = stage_approval(
                root,
                "PROTOTYPE",
                decision_suffix="NA-001",
                criteria_results=closed_criteria(root, gate, first_status="NOT_APPLICABLE", omit_na_validator=True),
            )
            with self.assertRaisesRegex(ValidationFailure, "NOT_APPLICABLE"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "na.yaml", invalid_na))

            approval = stage_approval(root, "PROTOTYPE", decision_suffix="PASS-001")
            result = accept_stage(root, "PROTOTYPE", write_approval(base, "pass.yaml", approval))
            self.assertEqual(result["status"], "TARGET_LEVEL_REACHED")
            self.assertEqual(result["accepted_levels"], ["PROTOTYPE"])
            self.assertEqual(next_task(root)["status"], "TARGET_LEVEL_REACHED")
            reports = list((root / ".harness/stages/ACCEPTANCE").glob("VAL-*-PROTOTYPE-001@1.yaml"))
            self.assertEqual(len(reports), 1)
            report = load_data(reports[0])["stage_acceptance"]
            self.assertEqual(report["revision"], 1)
            self.assertEqual(report["baseline_revision"], approval["stage_approval"]["baseline_revision"])
            self.assertEqual(report["permitted_use"]["status"], "CONFIRMED")
            self.assertTrue(report["known_limitations"])
            self.assertTrue(report["next_stage_gaps"])
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_05_acceptance_transition_rolls_back_on_mid_commit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            data = load_fixture()
            data["implementation"]["target_level"] = "PROTOTYPE"
            _, _, root = prepare_demo(base, data=data)
            complete_prototype(root)
            approval_path = write_approval(
                base,
                "rollback.yaml",
                stage_approval(root, "PROTOTYPE", decision_suffix="ROLLBACK-001"),
            )
            protected = [
                root / ".harness/stages/STAGE_STATE.yaml",
                root / ".harness/stages/PLANS/INDEX.yaml",
                root / ".harness/stages/GATES/INDEX.yaml",
                root / ".harness/state/CURRENT_STATE.yaml",
            ]
            before = {path: sha256_file(path) for path in protected}
            real_replace = os.replace
            failed = {"value": False}

            def flaky_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
                source = Path(src)
                destination = Path(dst)
                is_commit_replace = source.name.startswith("staged-") and "TRANSACTIONS" not in destination.parts
                if is_commit_replace and not failed["value"]:
                    failed["value"] = True
                    raise OSError("injected stage transaction failure")
                real_replace(src, dst)

            with mock.patch("project_harness.stages.os.replace", side_effect=flaky_replace):
                with self.assertRaisesRegex(OSError, "injected"):
                    accept_stage(root, "PROTOTYPE", approval_path)
            self.assertTrue(failed["value"])
            self.assertEqual({path: sha256_file(path) for path in protected}, before)
            self.assertEqual(list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")), [])
            transactions = [
                path
                for path in (root / ".harness/stages/TRANSACTIONS").glob("*/TRANSACTION.yaml")
                if load_data(path)["stage_transaction"].get("operation_kind") == "ACCEPT_STAGE"
            ]
            self.assertEqual(len(transactions), 1)
            self.assertEqual(load_data(transactions[0])["stage_transaction"]["status"], "ROLLED_BACK")

    def test_06_maturity_assessment_is_read_only_repeatable_and_stale_aware(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            _, _, root = prepare_demo(base)
            (root / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
            with mock.patch.object(subprocess, "run", side_effect=AssertionError("commands forbidden")), \
                 mock.patch.object(subprocess, "Popen", side_effect=AssertionError("commands forbidden")):
                first = assess_maturity(root)
                second = assess_maturity(root)
            self.assertFalse(first["automatic_command_execution"])
            self.assertEqual(first["previous_highest_accepted_level"], "NONE")
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "NONE")
            self.assertNotIn(first["highest_satisfied_candidate_level"], {"MVP", "RELEASE"})
            self.assertTrue(first["assessment_ref"].endswith("@1"))
            self.assertTrue(second["assessment_ref"].endswith("@2"))
            persisted = load_data(Path(first["assessment_path"]))["maturity_assessment"]
            self.assertEqual(persisted["automatic_command_execution"], "FORBIDDEN")
            self.assertTrue(any(
                item["status"] == "UNKNOWN" and "does not run commands" in item["rationale"]
                for items in persisted["criteria_results"].values() for item in items
            ))

            stale_evidence = {
                "evidence": [{
                    "id": "EVD-STALE-PROTOTYPE-001",
                    "kind": "TEST_REPORT",
                    "criterion_refs": ["PROTOTYPE_CORE_FLOW"],
                    "status": "PASS",
                    "provenance": "A report for a different tree.",
                    "base_revision": "tree:sha256:" + "0" * 64,
                }]
            }
            evidence_path = write_approval(base, "stale-evidence.yaml", stale_evidence)
            stale = assess_maturity(root, evidence_path=evidence_path)
            self.assertEqual(stale["status"], "STALE")
            assessment = load_data(Path(stale["assessment_path"]))["maturity_assessment"]
            criterion = next(item for item in assessment["criteria_results"]["PROTOTYPE"] if item["criterion_ref"] == "PROTOTYPE_CORE_FLOW")
            self.assertEqual(criterion["status"], "UNKNOWN")
            self.assertTrue(stale["warnings"])

    def test_07_baseline_assessment_can_accept_multiple_prior_levels_without_skipping_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            data = load_fixture()
            data["project"]["mode"] = "BROWNFIELD"
            data["implementation"]["target_level"] = "MVP"
            data["brownfield"]["baseline_summary"] = "Existing bounded local CLI repository."
            add_brownfield_approval(data)
            repository = base / "repository"
            repository.mkdir()
            (repository / "README.md").write_text("# Existing CLI\n", encoding="utf-8")
            (repository / "existing.py").write_text("VALUE = 1\n", encoding="utf-8")
            _, _, root = prepare_demo(base / "prepared", data=data, repository=repository)
            model = implementation_level_model()
            baseline = _product_baseline_revision(root)
            refs = model["profiles"]["PROTOTYPE"]["criteria_refs"] + model["profiles"]["ALPHA"]["criteria_refs"]
            evidence = {
                "evidence": [{
                    "id": f"EVD-BASELINE-{index:03d}",
                    "kind": model["criteria"][ref]["required_evidence_kinds"][0],
                    "criterion_refs": [ref],
                    "status": "PASS",
                    "provenance": "Explicit exact-baseline evidence fixture.",
                    "base_revision": baseline,
                    "validator": ACTOR,
                } for index, ref in enumerate(refs, 1)]
            }
            assessment = assess_maturity(root, evidence_path=write_approval(base, "baseline-evidence.yaml", evidence))
            self.assertEqual(assessment["highest_satisfied_candidate_level"], "ALPHA")

            levels: dict[str, dict] = {}
            for level in ("PROTOTYPE", "ALPHA"):
                gate = current_gate(root, level)
                levels[level] = {
                    "criteria_results": closed_criteria(root, gate),
                    "evidence_refs": [],
                    "permitted_use": {
                        "users": ["INTERNAL_USER"],
                        "environments": ["LOCAL", "DEV_TEST"],
                        "data_classes": ["INTERNAL"],
                        "data_constraints": ["NO_PRODUCTION_DATA"],
                    },
                    "known_limitations": [f"{level} limitations remain explicit."],
                    "next_stage_gaps": [f"Plan the next stage after accepting {level}."],
                }
            approval = {
                "stage_approval": {
                    "id": "DEC-HARNESS-DEMO-STAGE-BASELINE-001",
                    "approved": True,
                    "actor": ACTOR,
                    "approved_at": APPROVED_AT,
                    "level": "ALPHA",
                    "acceptance_method": "SATISFIED_BY_BASELINE",
                    "baseline_revision": baseline,
                    "assessment_ref": assessment["assessment_ref"],
                    "assessment_digest": assessment["assessment_digest"],
                    "levels": levels,
                    "notes": "Accept contiguous baseline-satisfied stages.",
                }
            }
            result = accept_stage(root, "ALPHA", write_approval(base, "baseline-approval.yaml", approval))
            self.assertEqual(result["accepted_levels"], ["PROTOTYPE", "ALPHA"])
            self.assertEqual(result["highest_accepted_level"], "ALPHA")
            self.assertEqual(result["active_stage"], "BETA")
            reports = sorted((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
            self.assertEqual(len(reports), 2)
            self.assertEqual({load_data(path)["stage_acceptance"]["level"] for path in reports}, {"PROTOTYPE", "ALPHA"})
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_08_level_up_and_same_level_maintenance_preserve_acceptance_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)

            maintenance_base = base / "maintenance"
            data = load_fixture()
            data["implementation"]["target_level"] = "PROTOTYPE"
            _, _, maintenance_root = prepare_demo(maintenance_base, data=data)
            complete_prototype(maintenance_root)
            accepted = accept_stage(
                maintenance_root,
                "PROTOTYPE",
                write_approval(maintenance_base, "prototype-pass.yaml", stage_approval(maintenance_root, "PROTOTYPE", decision_suffix="MAINT-BASE-001")),
            )
            self.assertEqual(accepted["status"], "TARGET_LEVEL_REACHED")
            acceptance_path = next((maintenance_root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
            acceptance_digest = sha256_file(acceptance_path)
            maintenance = maintenance_plan_document(maintenance_root, suffix="HISTORY-001")
            maintenance_result = start_maintenance(
                maintenance_root,
                write_approval(maintenance_base, "maintenance.yaml", maintenance),
            )
            self.assertEqual(maintenance_result["route"], "MAINTAIN_CURRENT_STAGE")
            self.assertEqual(maintenance_result["highest_accepted_level"], "PROTOTYPE")
            self.assertEqual(sha256_file(acceptance_path), acceptance_digest)
            self.assertEqual(validate_project_directory(maintenance_root)["status"], "PASS")

            blocked_level_up = {
                "level_up_approval": {
                    "id": "DEC-HARNESS-DEMO-LEVEL-UP-BLOCKED-001",
                    "approved": True,
                    "actor": ACTOR,
                    "approved_at": APPROVED_AT,
                    "target_level": "MVP",
                    "rationale": "This must not bypass open same-level maintenance.",
                }
            }
            with self.assertRaisesRegex(ValidationFailure, "maintenance work remains open"):
                level_up(
                    maintenance_root,
                    "MVP",
                    write_approval(maintenance_base, "level-up-blocked.yaml", blocked_level_up),
                )

            levelup_base = base / "levelup"
            data = load_fixture()
            data["implementation"]["target_level"] = "PROTOTYPE"
            _, _, root = prepare_demo(levelup_base, data=data)
            complete_prototype(root)
            accept_stage(
                root,
                "PROTOTYPE",
                write_approval(levelup_base, "prototype-pass.yaml", stage_approval(root, "PROTOTYPE", decision_suffix="LEVELUP-BASE-001")),
            )
            acceptance_path = next((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
            acceptance_digest = sha256_file(acceptance_path)
            level_up_approval = {
                "level_up_approval": {
                    "id": "DEC-HARNESS-DEMO-LEVEL-UP-001",
                    "approved": True,
                    "actor": ACTOR,
                    "approved_at": APPROVED_AT,
                    "target_level": "MVP",
                    "rationale": "Start a separately approved progression cycle through Alpha, Beta and MVP.",
                }
            }
            result = level_up(root, "MVP", write_approval(levelup_base, "level-up.yaml", level_up_approval))
            self.assertEqual(result["status"], "ACTIVE")
            self.assertEqual(result["highest_accepted_level"], "PROTOTYPE")
            self.assertEqual(result["active_stage"], "ALPHA")
            self.assertEqual(result["stage_path"], ["PROTOTYPE", "ALPHA", "BETA", "MVP"])
            self.assertEqual(sha256_file(acceptance_path), acceptance_digest)
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "PROTOTYPE")
            self.assertEqual(stage_status(root)["active_stage"], "ALPHA")
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

            no_change = {
                "level_up_approval": {
                    "id": "DEC-HARNESS-DEMO-LEVEL-UP-NOOP-001",
                    "approved": True,
                    "actor": ACTOR,
                    "approved_at": APPROVED_AT,
                    "target_level": "PROTOTYPE",
                    "rationale": "No destructive downgrade is permitted.",
                }
            }
            state_before = sha256_file(root / ".harness/stages/STAGE_STATE.yaml")
            noop = level_up(root, "PROTOTYPE", write_approval(levelup_base, "level-up-noop.yaml", no_change))
            self.assertEqual(noop["status"], "TARGET_ALREADY_REACHED")
            self.assertFalse(noop["changed"])
            self.assertEqual(sha256_file(root / ".harness/stages/STAGE_STATE.yaml"), state_before)


if __name__ == "__main__":
    unittest.main()

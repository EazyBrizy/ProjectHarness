from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from project_harness.errors import ValidationFailure, WaitingDecision, WaitingInput
from project_harness.hashing import sha256_file
from project_harness.intake import start_intake
from project_harness.compiler import prepare_handoff
from project_harness.migration import migrate_project
from project_harness.project_input import (
    DATA_SENSITIVITY_CLASSES,
    PROJECT_INPUT_MIGRATION_ID,
    QUESTION_BANK,
    load_project_input_schema,
    migrate_project_input,
    project_input_schema_issues,
    validate_project_input,
)
from project_harness.runtime import block_current, complete_current, resume_blocked, verify_current
from project_harness.serialization import load_data, write_data
from project_harness.validation import validate_project_directory
from project_harness.workspace import check_control_plane

from tests.test_engine import (
    ROOT,
    add_brownfield_approval,
    file_tree_digest,
    implement_first_task,
    implement_second_task,
    load_fixture,
    prepare_demo,
    write_agent_result,
)


LEGACY_UNEXECUTED_FIXTURE = ROOT / "fixtures/legacy_v0.4.1_demo_handoff.zip"
LEGACY_COMPLETED_FIXTURE = ROOT / "fixtures/legacy_v0.4.1_completed_handoff.zip"


def extract_legacy_fixture(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            member = Path(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise AssertionError(f"Unsafe legacy fixture member: {info.filename}")
        zf.extractall(destination)
    locks = list(destination.rglob(".harness/config/PROJECT_LOCK.yaml"))
    if len(locks) != 1:
        raise AssertionError(f"Expected one legacy project root, found {len(locks)}")
    return locks[0].parents[2]


def write_migration_input(root: Path, destination: Path, *, target: str = "MVP") -> Path:
    value = load_data(root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml")
    migrated, _ = migrate_project_input(value)
    migrated["implementation"]["target_level"] = target
    if migrated["project"]["mode"] in {"BROWNFIELD", "HYBRID"}:
        migrated["implementation"]["claimed_current_level"] = "UNKNOWN"
    write_data(destination, migrated)
    return destination


class ContractHardeningStatusTests(unittest.TestCase):
    def test_success_uses_entity_specific_terminal_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            implement_first_task(root)
            verify1 = verify_current(root, allow_command_execution=True)
            result1 = write_agent_result(root, verify1, "Implemented add/list")
            complete1 = complete_current(root, result1)

            task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
            first_task = load_data(root / task_index["current"]["TSK-HARNESS-DEMO-TASK-CLI-001"])["task"]
            first_run = load_data(root / ".harness/runtime/RUNS/RUN-HARNESS-DEMO-TASK-CLI-001-A1.yaml")["run"]
            first_report = load_data(root / ".harness/reports/TRP-HARNESS-DEMO-TASK-CLI-001-A1.yaml")["task_report"]
            agent_result = load_data(result1)

            self.assertEqual(first_task["status"], "DONE")
            self.assertEqual(first_run["status"], "SUCCEEDED")
            self.assertEqual(first_report["status"], "COMPLETED")
            self.assertEqual(agent_result["status"], "COMPLETED")
            self.assertEqual(complete1["status"], "COMPLETED")

            implement_second_task(root)
            verify2 = verify_current(root, allow_command_execution=True)
            complete2 = complete_current(root, write_agent_result(root, verify2, "Implemented done"))
            wp_index = load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]
            wp_id = wp_index["order"][0]
            work_package = load_data(root / wp_index["current"][wp_id])["work_package"]
            self.assertEqual(work_package["status"], "COMPLETED")
            self.assertEqual(complete2["status"], "COMPLETED")
            self.assertEqual(complete2["project_status"], "ACTIVE")
            self.assertEqual(complete2["stage_gate"]["status"], "STAGE_ACCEPTANCE_PREPARATION")
            verify3 = verify_current(root, allow_command_execution=True)
            complete3 = complete_current(root, write_agent_result(root, verify3, "Prepared final Stage Gate evidence"))
            self.assertEqual(complete3["status"], "COMPLETED")
            # PH-F02: general PASS never proves the mandatory Gate subjects.
            self.assertEqual(complete3["stage_gate"]["status"], "BLOCKED")
            from project_harness.stage_gate_lifecycle import resume_stage_gate
            from tests.gate_proof_fixtures import all_gate_subjects
            all_gate_subjects(root)
            self.assertEqual(resume_stage_gate(root)["status"], "VERIFYING")

    def test_new_task_and_run_completed_values_are_rejected(self) -> None:
        with self.subTest(entity="task"), tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
            path = root / index["current"][index["order"][0]]
            value = load_data(path)
            value["task"]["status"] = "COMPLETED"
            write_data(path, value)
            report = validate_project_directory(root)
            status_check = next(item for item in report["checks"] if item["name"] == "Registry-driven entity statuses")
            self.assertEqual(status_check["status"], "FAIL")
            self.assertTrue(any("task.status='COMPLETED'" in error for error in status_check["details"]["errors"]))

        with self.subTest(entity="run"), tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            implement_first_task(root)
            verification = verify_current(root, allow_command_execution=True)
            complete_current(root, write_agent_result(root, verification))
            path = root / ".harness/runtime/RUNS/RUN-HARNESS-DEMO-TASK-CLI-001-A1.yaml"
            value = load_data(path)
            value["run"]["status"] = "COMPLETED"
            write_data(path, value)
            report = validate_project_directory(root)
            status_check = next(item for item in report["checks"] if item["name"] == "Registry-driven entity statuses")
            self.assertEqual(status_check["status"], "FAIL")
            self.assertTrue(any("run.status='COMPLETED'" in error for error in status_check["details"]["errors"]))

    def test_legacy_v041_completed_project_is_read_compatibly_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = extract_legacy_fixture(LEGACY_COMPLETED_FIXTURE, Path(temp))
            before = file_tree_digest(root)
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            self.assertEqual(state["project_status"], "COMPLETED")
            self.assertFalse((root / ".harness/stages").exists())
            report = validate_project_directory(root)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(file_tree_digest(root), before)
            self.assertEqual(load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]["project_status"], "COMPLETED")


class ContractHardeningBrownfieldTests(unittest.TestCase):
    @staticmethod
    def _brownfield_input() -> dict:
        data = load_fixture()
        data["project"].update({"name": "Brownfield Gate Demo", "slug": "brownfield-gate-demo", "mode": "BROWNFIELD"})
        data["implementation"]["claimed_current_level"] = "UNKNOWN"
        data["brownfield"]["baseline_summary"] = "Existing repository inventory and test baseline were reviewed."
        return data

    def test_greenfield_four_approvals_is_ready(self) -> None:
        data = load_fixture()
        self.assertNotIn("brownfield_baseline", data["approvals"])
        report = validate_project_input(data, require_approvals=True)
        self.assertEqual(report["status"], "READY_FOR_HANDOFF")
        self.assertEqual(report["missing_approvals"], [])

    def test_brownfield_four_approvals_waits_for_separate_decision(self) -> None:
        data = self._brownfield_input()
        report = validate_project_input(data, require_approvals=True)
        self.assertEqual(report["status"], "WAITING_DECISION")
        self.assertEqual(report["missing_approvals"], ["brownfield_baseline"])

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "repository"
            repository.mkdir()
            (repository / "README.md").write_text("existing\n", encoding="utf-8")
            input_path = base / "input.json"
            write_data(input_path, data)
            workspace = base / "intake"
            started = start_intake(
                workspace,
                project_name=data["project"]["name"],
                mode="BROWNFIELD",
                repository=repository,
                initial_input=input_path,
            )
            self.assertEqual(started["status"], "WAITING_DECISION")
            with self.assertRaises(WaitingDecision):
                prepare_handoff(workspace, base / "handoff.zip")

    def test_explicit_brownfield_approval_creates_immutable_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repository = base / "repository"
            repository.mkdir()
            (repository / "README.md").write_text("existing\n", encoding="utf-8")
            data = self._brownfield_input()
            data["approvals"]["project_definition"]["actor"] = "ACT-PROJECT-APPROVER-001"
            add_brownfield_approval(data, actor="ACT-BASELINE-APPROVER-002")
            _, _, root = prepare_demo(base / "run", data=data, repository=repository)

            baseline_path = next((root / ".harness/canonical/DEFINITION/BROWNFIELD").glob("BFB-*@1.yaml"))
            baseline = load_data(baseline_path)["brownfield_baseline"]
            decision_path = root / f".harness/canonical/DECISIONS/{baseline['accepted_by']}@1.yaml"
            decision = load_data(decision_path)["decision"]

            self.assertEqual(decision["kind"], "BROWNFIELD_BASELINE_APPROVAL")
            self.assertEqual(decision["actor"], "ACT-BASELINE-APPROVER-002")
            self.assertNotEqual(decision["actor"], data["approvals"]["project_definition"]["actor"])
            self.assertEqual(decision["subject_ref"], f"{baseline['id']}@{baseline['revision']}")
            self.assertEqual(decision["approved_at"], baseline["accepted_at"])
            self.assertEqual(decision["status"], "ACCEPTED")
            self.assertEqual(decision_path.name, f"{decision['id']}@{decision['revision']}.yaml")

            contracts = load_data(root / ".harness/registries/contracts.yaml")["registry"]
            statuses = load_data(root / ".harness/registries/statuses.yaml")["registry"]
            self.assertEqual(contracts["version"], 6)
            self.assertEqual(contracts["entities"]["decision"], {
                "id_prefix": "DEC",
                "persistence": "PERSISTENT",
                "lifecycle": "decision",
                "storage_path": ".harness/canonical/DECISIONS/{id}@{revision}.yaml",
                "revision_policy": "IMMUTABLE",
            })
            self.assertEqual(statuses["version"], 6)
            self.assertEqual(statuses["groups"]["decision"], ["ACCEPTED", "REJECTED", "SUPERSEDED"])
            self.assertEqual(validate_project_directory(root)["status"], "PASS")


class ContractHardeningSensitivityTests(unittest.TestCase):
    def test_all_six_canonical_classes_are_ready(self) -> None:
        self.assertEqual(DATA_SENSITIVITY_CLASSES, {
            "PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "SECRET", "REGULATED",
        })
        for sensitivity in sorted(DATA_SENSITIVITY_CLASSES):
            with self.subTest(sensitivity=sensitivity):
                data = load_fixture()
                data["project"]["data"]["sensitivity"] = sensitivity
                report = validate_project_input(data, require_approvals=True)
                self.assertEqual(report["status"], "READY_FOR_HANDOFF")

    def test_unknown_is_waiting_input_and_unrecognized_value_is_invalid(self) -> None:
        data = load_fixture()
        data["project"]["data"]["sensitivity"] = "UNKNOWN"
        report = validate_project_input(data, require_approvals=True)
        self.assertEqual(report["status"], "WAITING_INPUT")
        self.assertIn("project.data.sensitivity", report["missing_fields"])

        data["project"]["data"]["sensitivity"] = "TOP_SECRETISH"
        report = validate_project_input(data, require_approvals=True)
        self.assertEqual(report["status"], "INVALID")

    def test_questionnaire_options_match_schema_enum(self) -> None:
        question = next(item for item in QUESTION_BANK if item["id"] == "QST-DATA-001")
        schema = load_project_input_schema()
        schema_values = [item for item in schema["$defs"]["data"]["properties"]["sensitivity"]["enum"] if item is not None]
        self.assertEqual(question["options"], schema_values)
        self.assertEqual(set(schema_values), DATA_SENSITIVITY_CLASSES | {"UNKNOWN"})


class ContractHardeningSchemaTests(unittest.TestCase):
    def assertRejected(self, data: dict) -> None:  # noqa: N802 - unittest-style helper
        strict_schema_accepts = not project_input_schema_issues(data)
        python_accepts = validate_project_input(data, require_approvals=True)["status"] == "READY_FOR_HANDOFF"
        self.assertFalse(strict_schema_accepts)
        self.assertFalse(python_accepts)

    def test_unknown_properties_are_rejected_at_every_normative_level(self) -> None:
        mutations = {
            "top-level": lambda value: value.__setitem__("unexpected", True),
            "nested-project": lambda value: value["project"].__setitem__("unexpected", True),
            "nested-task": lambda value: value["planning"]["work_packages"][0]["tasks"][0].__setitem__("unexpected", True),
            "nested-approval": lambda value: value["approvals"]["project_definition"].__setitem__("unexpected", True),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                data = load_fixture()
                mutate(data)
                report = validate_project_input(data, require_approvals=True)
                self.assertEqual(report["status"], "INVALID")
                self.assertTrue(any("unknown property" in error for error in report["errors"]))
                self.assertRejected(data)

    def test_wrong_type_and_empty_required_collection_are_not_accepted(self) -> None:
        wrong_type = load_fixture()
        wrong_type["project"]["users"] = "one user"
        report = validate_project_input(wrong_type, require_approvals=True)
        self.assertEqual(report["status"], "INVALID")
        self.assertRejected(wrong_type)

        empty = load_fixture()
        empty["project"]["users"] = []
        report = validate_project_input(empty, require_approvals=True)
        self.assertEqual(report["status"], "WAITING_INPUT")
        self.assertRejected(empty)

    def test_conditional_brownfield_approval_is_enforced_by_both_layers(self) -> None:
        data, _ = migrate_project_input(load_fixture())
        data["project"]["mode"] = "BROWNFIELD"
        data["implementation"]["claimed_current_level"] = "UNKNOWN"
        data["brownfield"]["baseline_summary"] = "Reviewed baseline"
        schema_issues = project_input_schema_issues(data)
        self.assertTrue(any(item["path"] == "approvals.brownfield_baseline" and item["keyword"] == "required" for item in schema_issues))
        report = validate_project_input(data, require_approvals=True)
        self.assertEqual(report["status"], "WAITING_DECISION")

        add_brownfield_approval(data)
        self.assertEqual(project_input_schema_issues(data), [])
        self.assertEqual(validate_project_input(data, require_approvals=True)["status"], "READY_FOR_HANDOFF")

    def test_machine_schema_and_python_acceptance_match_fixture_matrix(self) -> None:
        matrix: list[tuple[str, dict, bool]] = []
        matrix.append(("valid", load_fixture(), True))

        unknown = load_fixture()
        unknown["architecture"]["unknown_field"] = "no"
        matrix.append(("unknown", unknown, False))

        wrong_type = load_fixture()
        wrong_type["technology"]["selections"] = {"technology": "Python"}
        matrix.append(("wrong-type", wrong_type, False))

        empty = load_fixture()
        empty["planning"]["work_packages"] = []
        matrix.append(("empty-required", empty, False))

        invalid_enum = load_fixture()
        invalid_enum["project"]["connectivity"] = "SOMETIMES"
        matrix.append(("invalid-enum", invalid_enum, False))

        brownfield_missing_gate = load_fixture()
        brownfield_missing_gate["project"]["mode"] = "BROWNFIELD"
        brownfield_missing_gate["implementation"]["claimed_current_level"] = "UNKNOWN"
        brownfield_missing_gate["brownfield"]["baseline_summary"] = "Reviewed"
        matrix.append(("conditional-gate", brownfield_missing_gate, False))

        # Existing fixture is an accepted historical v3 input; schema-specific
        # assertions deliberately exercise its in-memory v4 normalization.
        matrix = [(name, migrate_project_input(data)[0], expected) for name, data, expected in matrix]
        schema = load_project_input_schema()
        try:
            from jsonschema import Draft202012Validator
        except ImportError:  # pragma: no cover - jsonschema is deliberately optional
            Draft202012Validator = None
        external = Draft202012Validator(schema) if Draft202012Validator else None

        for name, data, expected in matrix:
            with self.subTest(name=name):
                internal_schema_accepts = not project_input_schema_issues(data)
                python_accepts = validate_project_input(data, require_approvals=True)["status"] == "READY_FOR_HANDOFF"
                self.assertEqual(internal_schema_accepts, expected)
                self.assertEqual(python_accepts, expected)
                if external is not None:
                    self.assertEqual(not list(external.iter_errors(data)), expected)

    def test_provider_accounting_inside_open_configuration_is_still_rejected(self) -> None:
        data, _ = migrate_project_input(load_fixture())
        data["skills"]["resolutions"][0]["configuration"] = {
            "safe_option": True,
            "nested": {"token_usage": 123},
        }
        self.assertEqual(project_input_schema_issues(data), [])
        report = validate_project_input(data, require_approvals=True)
        self.assertEqual(report["status"], "INVALID")
        self.assertTrue(any("Forbidden provider accounting field" in error for error in report["errors"]))


class ContractHardeningMigrationTests(unittest.TestCase):
    def test_v1_to_v4_migration_is_explicit_conservative_and_idempotent(self) -> None:
        greenfield = load_fixture()
        greenfield["schema_version"] = 1
        greenfield.pop("implementation", None)
        migrated_greenfield, greenfield_report = migrate_project_input(greenfield)
        self.assertEqual(migrated_greenfield["schema_version"], 4)
        self.assertEqual(migrated_greenfield["implementation"], {
            "target_level": None,
            "claimed_current_level": "NONE",
        })
        self.assertEqual(migrated_greenfield["execution"], {
            "mode": "MANUAL_HANDOFF", "adapter_profile_ref": None, "sandbox_profile_ref": None,
            "network_mode": "NONE", "completion_policy": "EXPLICIT_AFTER_VERIFICATION",
        })
        self.assertNotIn("brownfield_baseline", migrated_greenfield["approvals"])
        self.assertEqual(greenfield_report["status"], "MIGRATED")
        self.assertEqual(validate_project_input(migrated_greenfield, require_approvals=True)["status"], "WAITING_INPUT")

        brownfield = load_fixture()
        brownfield["schema_version"] = 1
        brownfield.pop("implementation", None)
        brownfield["project"]["mode"] = "BROWNFIELD"
        brownfield["brownfield"]["baseline_summary"] = "Reviewed"
        migrated, report = migrate_project_input(brownfield)
        self.assertEqual(migrated["implementation"], {
            "target_level": None,
            "claimed_current_level": "UNKNOWN",
        })
        self.assertEqual(migrated["approvals"]["brownfield_baseline"], {
            "approved": False, "actor": None, "approved_at": None, "notes": None,
        })
        self.assertEqual(report["migration_id"], PROJECT_INPUT_MIGRATION_ID)
        self.assertEqual(report["actions"], [
            "schema_version:1->2",
            "approvals.brownfield_baseline:added-unapproved",
            "implementation.target_level:added-null",
            "implementation.claimed_current_level:added-UNKNOWN",
            "schema_version:2->3",
            "execution:added-manual-default",
            "schema_version:3->4",
        ])
        self.assertEqual(validate_project_input(migrated, require_approvals=True)["status"], "WAITING_INPUT")

        second, second_report = migrate_project_input(migrated)
        self.assertEqual(second, migrated)
        self.assertEqual(second_report["status"], "NO_ACTION")
        self.assertEqual(second_report["actions"], [])

    def test_migration_preserves_unknown_properties_and_reports_exact_paths(self) -> None:
        legacy = load_fixture()
        legacy["schema_version"] = 1
        legacy.pop("implementation", None)
        legacy["project"]["legacy_extension"] = {"keep": True}
        migrated, report = migrate_project_input(legacy)
        self.assertEqual(migrated["project"]["legacy_extension"], {"keep": True})
        self.assertIn("project.legacy_extension", report["unknown_properties"])
        self.assertTrue(report["requires_manual_correction"])
        self.assertEqual(validate_project_input(migrated, require_approvals=True)["status"], "INVALID")

    def test_project_migration_requires_target_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = extract_legacy_fixture(LEGACY_UNEXECUTED_FIXTURE, Path(temp))
            before = file_tree_digest(root)
            with self.assertRaises(WaitingInput):
                migrate_project(root)
            self.assertEqual(file_tree_digest(root), before)

    def test_unexecuted_v041_project_is_recompiled_and_migration_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = extract_legacy_fixture(LEGACY_UNEXECUTED_FIXTURE, base / "legacy")
            old_bundle = root / ".harness/prompts/BUNDLES_BY_RUN/CPB-HARNESS-DEMO-TASK-CLI-001-A1.yaml"
            old_bundle_digest = sha256_file(old_bundle)
            supplied = write_migration_input(root, base / "migration-input.json", target="MVP")

            result = migrate_project(root, input_path=supplied)
            self.assertEqual(result["status"], "MIGRATED")
            self.assertEqual(result["validation_status"], "PASS")
            self.assertEqual(result["stage_path"], ["PROTOTYPE", "ALPHA", "BETA", "MVP"])
            self.assertEqual(sha256_file(old_bundle), old_bundle_digest)

            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            self.assertEqual(state["project_status"], "ACTIVE")
            self.assertEqual(state["active_stage"], "PROTOTYPE")
            self.assertTrue(state["active_run"]["run_ref"].endswith("-A2"))
            self.assertEqual(state["active_run"]["implementation_stage"], "PROTOTYPE")
            self.assertEqual(state["active_run"]["target_implementation_level"], "MVP")
            self.assertEqual(result["cancelled_unexecuted_run"]["status"], "CANCELLED")
            prompt = (root / state["active_run"]["prompt_markdown_path"]).read_text(encoding="utf-8")
            self.assertIn("CURRENT_IMPLEMENTATION_STAGE: PROTOTYPE", prompt)
            self.assertIn("TARGET_IMPLEMENTATION_LEVEL: MVP", prompt)
            self.assertEqual(validate_project_directory(root)["status"], "PASS")
            self.assertEqual(migrate_project(root)["status"], "NO_ACTION")

    def test_completed_v041_history_is_preserved_and_requires_maturity_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = extract_legacy_fixture(LEGACY_COMPLETED_FIXTURE, base / "legacy")
            historical_paths = sorted((root / ".harness/tasks").glob("TSK-*@*.yaml")) + sorted(
                (root / ".harness/runtime/RUNS").glob("RUN-*.yaml")
            )
            historical_digests = {path.relative_to(root).as_posix(): sha256_file(path) for path in historical_paths}
            supplied = write_migration_input(root, base / "migration-input.json", target="MVP")

            result = migrate_project(root, input_path=supplied)
            self.assertEqual(result["status"], "MIGRATED")
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            self.assertEqual(state["project_status"], "ACTIVE")
            self.assertEqual(state["next_route"], "REVIEW_MATURITY_ASSESSMENT")
            self.assertIsNone(state["active_run"])
            stage_state = load_data(root / ".harness/stages/STAGE_STATE.yaml")["implementation"]
            self.assertEqual(stage_state["highest_accepted_level"], "NONE")
            self.assertEqual(stage_state["observed_candidate_level"], "PROTOTYPE")
            assessments = list((root / ".harness/stages/ASSESSMENTS").glob("VAL-*@*.yaml"))
            self.assertEqual(len(assessments), 1)
            assessment = load_data(assessments[0])["maturity_assessment"]
            self.assertEqual(assessment["highest_satisfied_candidate_level"], "NONE")
            self.assertEqual(assessment["automatic_command_execution"], "FORBIDDEN")
            self.assertEqual(assessment["recommended_route"], "COMPLETE_CURRENT_STAGE")
            for rel, digest in historical_digests.items():
                self.assertEqual(sha256_file(root / rel), digest)
            assessment_path = Path(result["provisional_assessment"]["assessment_path"])
            if not assessment_path.is_absolute():
                assessment_path = root / assessment_path
            self.assertTrue(assessment_path.exists())
            self.assertEqual(validate_project_directory(root)["status"], "PASS")
            self.assertEqual(migrate_project(root)["status"], "NO_ACTION")

    def test_migration_with_agent_output_fails_transactionally(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = extract_legacy_fixture(LEGACY_UNEXECUTED_FIXTURE, base / "legacy")
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            result_path = root / state["active_run"]["allowed_agent_output_path"]
            write_data(result_path, {"status": "COMPLETED"})
            supplied = write_migration_input(root, base / "migration-input.json", target="MVP")
            before = file_tree_digest(root)
            with self.assertRaisesRegex(ValidationFailure, "already has agent or verification output"):
                migrate_project(root, input_path=supplied)
            self.assertEqual(file_tree_digest(root), before)


class ContractHardeningControlPlaneTests(unittest.TestCase):
    def _assert_safety_block(self, root: Path, expected_path: str) -> dict:
        result = verify_current(root, allow_command_execution=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "SAFETY_VIOLATION")
        self.assertEqual(result["commands"], [])
        affected = set(result["control_plane"]["changed"] + result["control_plane"]["deleted"] + result["control_plane"]["unexpected"])
        affected.update(item.get("path") for item in result["control_plane"]["unsafe"])
        agent_result = result["control_plane"].get("agent_result") or {}
        if agent_result.get("status") == "FAIL":
            affected.add(agent_result.get("path"))
        if expected_path:
            self.assertIn(expected_path, affected)
        state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
        self.assertEqual(state["project_status"], "BLOCKED")
        self.assertIsNone(state["active_run"])
        self.assertEqual(state["next_route"], "RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN")
        return result

    def test_task_contract_mutation_blocks_before_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            task_id = state["current_task_ref"]
            index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
            rel = index["current"][task_id]
            path = root / rel
            path.write_text(path.read_text(encoding="utf-8") + "\n# agent mutation\n", encoding="utf-8")
            self._assert_safety_block(root, rel)

    def test_project_lock_mutation_blocks_before_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            rel = ".harness/config/PROJECT_LOCK.yaml"
            path = root / rel
            path.write_text(path.read_text(encoding="utf-8") + "\n# agent mutation\n", encoding="utf-8")
            self._assert_safety_block(root, rel)

    def test_prompt_bundle_deletion_blocks_before_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            rel = state["active_run"]["prompt_bundle_path"]
            (root / rel).unlink()
            self._assert_safety_block(root, rel)

    def test_unexpected_protected_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            rel = ".harness/evidence/AGENT-INJECTED.txt"
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("unexpected\n", encoding="utf-8")
            self._assert_safety_block(root, rel)

    def test_wrong_run_result_file_is_unexpected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            rel = ".harness/runtime/AGENT_RESULTS/RUN-WRONG.json"
            (root / rel).write_text("{}\n", encoding="utf-8")
            self._assert_safety_block(root, rel)

    def test_agent_result_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            active = state["active_run"]
            outside = root / "outside-result.json"
            outside.write_text(json.dumps({"task_ref": active["task_ref"], "run_ref": active["run_ref"]}) + "\n", encoding="utf-8")
            expected = root / active["allowed_agent_output_path"]
            from tests.platform_capabilities import symlink_or_skip
            symlink_or_skip(self, expected, outside)
            result = self._assert_safety_block(root, active["allowed_agent_output_path"])
            self.assertEqual(result["control_plane"]["agent_result"]["status"], "FAIL")

    @unittest.skipUnless(hasattr(os, "link"), "hardlinks are not supported")
    def test_agent_result_hardlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            active = state["active_run"]
            source = root / "result-source.json"
            source.write_text(json.dumps({"task_ref": active["task_ref"], "run_ref": active["run_ref"]}) + "\n", encoding="utf-8")
            expected = root / active["allowed_agent_output_path"]
            os.link(source, expected)
            result = self._assert_safety_block(root, active["allowed_agent_output_path"])
            self.assertEqual(result["control_plane"]["agent_result"]["status"], "FAIL")

    def test_verification_command_control_plane_write_is_not_sealed_as_trusted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            implement_first_task(root)
            module = root / "task_cli.py"
            text = module.read_text(encoding="utf-8")
            injection = (
                "from pathlib import Path as _HarnessPath\n"
                "(_HarnessPath('.harness/evidence') / 'COMMAND-TAMPER.txt').write_text('tampered\\n', encoding='utf-8')\n"
            )
            text = text.replace("from __future__ import annotations\n", "from __future__ import annotations\n" + injection, 1)
            module.write_text(text, encoding="utf-8")

            result = verify_current(root, allow_command_execution=True)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["reason"], "SAFETY_VIOLATION")
            self.assertTrue(result["control_plane"]["detected_after_verification_commands"])
            self.assertIn(".harness/evidence/COMMAND-TAMPER.txt", result["control_plane"]["unexpected"])
            self.assertEqual(len(result["commands"]), 2)
            self.assertEqual(
                load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]["next_route"],
                "RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN",
            )

    def test_exact_regular_result_and_kernel_verify_records_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            implement_first_task(root)
            verification = verify_current(root, allow_command_execution=True)
            self.assertEqual(verification["status"], "PASS")
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            active = state["active_run"]
            after_verify = check_control_plane(root, active, allow_missing_agent_result=True)
            self.assertEqual(after_verify["status"], "PASS")

            result_path = write_agent_result(root, verification)
            with_result = check_control_plane(root, active, allow_missing_agent_result=False)
            self.assertEqual(with_result["status"], "PASS")
            self.assertEqual(with_result["agent_result"]["status"], "PASS")
            self.assertEqual(result_path.relative_to(root).as_posix(), active["allowed_agent_output_path"])
            completed = complete_current(root, result_path)
            self.assertEqual(completed["status"], "COMPLETED")

    def test_declared_product_diff_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            implement_first_task(root)
            verification = verify_current(root, allow_command_execution=True)
            self.assertEqual(verification["status"], "PASS")
            self.assertEqual(verification["gates"]["scope"], "PASS")
            self.assertEqual(set(verification["diff"]["added"]), {"task_cli.py", "tests/test_task_cli.py"})
            self.assertEqual(verification["diff"]["modified"], ["README.md"])

    def test_product_change_after_verify_requires_reverification(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            implement_first_task(root)
            verification = verify_current(root, allow_command_execution=True)
            result_path = write_agent_result(root, verification)
            with (root / "README.md").open("a", encoding="utf-8") as handle:
                handle.write("\nchanged after verification\n")
            with self.assertRaisesRegex(ValidationFailure, "changed after verification"):
                complete_current(root, result_path)


if __name__ == "__main__":
    unittest.main()

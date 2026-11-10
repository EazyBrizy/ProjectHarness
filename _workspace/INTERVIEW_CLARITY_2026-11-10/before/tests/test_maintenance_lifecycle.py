from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from project_harness.cli import build_parser
from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.maintenance import cancel_maintenance, start_maintenance
from project_harness.runtime import complete_current, next_task, verify_current
from project_harness.serialization import load_data, write_data
from project_harness.stages import accept_stage, level_up, load_stage_state
from project_harness.validation import validate_project_directory

from tests.maintenance_fixtures import maintenance_cancel_document, maintenance_plan_document, write_record
from tests.test_engine import load_fixture, prepare_demo, write_agent_result
from tests.test_implementation_levels import complete_prototype, stage_approval, write_approval


class SameLevelMaintenanceLifecycleTests(unittest.TestCase):
    def accepted_project(self, base: Path) -> Path:
        data = load_fixture()
        data["implementation"]["target_level"] = "PROTOTYPE"
        _, _, root = prepare_demo(base, data=data)
        complete_prototype(root)
        result = accept_stage(
            root,
            "PROTOTYPE",
            write_approval(base, "prototype-acceptance.yaml", stage_approval(root, "PROTOTYPE", decision_suffix="MAINT-BASE-001")),
        )
        self.assertEqual(result["status"], "TARGET_LEVEL_REACHED")
        return root

    def complete_maintenance_task(self, root: Path, marker: str) -> dict:
        with (root / "README.md").open("a", encoding="utf-8") as fh:
            fh.write(f"\n{marker}\n")
        verification = verify_current(root, allow_command_execution=True)
        self.assertEqual(verification["status"], "PASS")
        return complete_current(root, write_agent_result(root, verification, marker))

    @staticmethod
    def immutable_bytes(root: Path, pattern: str) -> dict[str, bytes]:
        return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.glob(pattern))}

    @staticmethod
    def harness_digests(root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): sha256_file(path)
            for path in sorted((root / ".harness").rglob("*"))
            if path.is_file()
        }

    def test_start_creates_governed_artifacts_and_exactly_one_first_jit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.accepted_project(base)
            stage_before = (root / ".harness/stages/STAGE_STATE.yaml").read_bytes()
            bundles_before = set((root / ".harness/prompts/BUNDLES_BY_RUN").glob("CPB-*.yaml"))
            plan = maintenance_plan_document(root, suffix="START-001", task_count=2)
            plan_path = write_record(base, "maintenance-plan.yaml", plan)

            result = start_maintenance(root, plan_path)
            self.assertEqual(result["status"], "MAINTENANCE_ACTIVE")
            self.assertEqual(result["route"], "MAINTAIN_CURRENT_STAGE")
            self.assertEqual(result["implementation_stage"], "PROTOTYPE")
            self.assertEqual(result["highest_accepted_level"], "PROTOTYPE")
            self.assertEqual(result["target_level"], "PROTOTYPE")
            self.assertEqual(result["next"]["status"], "READY_FOR_CODEX")
            self.assertEqual(result["next"]["maintenance_route"], "MAINTAIN_CURRENT_STAGE")
            self.assertEqual((root / ".harness/stages/STAGE_STATE.yaml").read_bytes(), stage_before)

            bundles_after = set((root / ".harness/prompts/BUNDLES_BY_RUN").glob("CPB-*.yaml"))
            new_bundles = bundles_after - bundles_before
            self.assertEqual(len(new_bundles), 1)
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            self.assertEqual(state["maintenance_route"], "MAINTAIN_CURRENT_STAGE")
            self.assertIsInstance(state["active_run"], dict)
            self.assertEqual(state["active_run"]["maintenance_route"], "MAINTAIN_CURRENT_STAGE")

            decision = load_data(root / f".harness/canonical/DECISIONS/{plan['maintenance_plan']['decision']['id']}@1.yaml")["decision"]
            self.assertEqual(decision["kind"], "MAINTAIN_CURRENT_STAGE")
            wp_id = plan["maintenance_plan"]["work_package"]["id"]
            wp_index = load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]
            wp = load_data(root / wp_index["current"][wp_id])["work_package"]
            self.assertEqual(wp["maintenance_route"], "MAINTAIN_CURRENT_STAGE")
            self.assertEqual(wp["status"], "READY")
            self.assertEqual(len(wp["mandatory_task_refs"]), 2)

            task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
            for task_id in wp["mandatory_task_refs"]:
                task = load_data(root / task_index["current"][task_id])["task"]
                self.assertEqual(task["maintenance_route"], "MAINTAIN_CURRENT_STAGE")
                self.assertEqual(task["implementation_stage"], "PROTOTYPE")
                for field, directory, envelope in (
                    ("prompt_plan_ref", ".harness/prompts/PLANS", "prompt_plan"),
                    ("context_plan_ref", ".harness/context/PLANS", "context_plan"),
                    ("verification_profile_ref", ".harness/verification/PROFILES", "verification_profile"),
                ):
                    artifact = load_data(root / directory / f"{task[field]}.yaml")[envelope]
                    self.assertEqual(artifact["maintenance_route"], "MAINTAIN_CURRENT_STAGE")
                    self.assertEqual(artifact["implementation_stage"], "PROTOTYPE")
            dag = load_data(root / ".harness/dags" / f"{wp['dependency_graph_ref']}.yaml")["dependency_graph"]
            self.assertEqual(dag["maintenance_route"], "MAINTAIN_CURRENT_STAGE")

            replay = start_maintenance(root, plan_path)
            self.assertTrue(replay["idempotent"])
            self.assertTrue(replay["next"]["idempotent"])
            self.assertEqual(set((root / ".harness/prompts/BUNDLES_BY_RUN").glob("CPB-*.yaml")), bundles_after)
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_next_verify_complete_closes_maintenance_and_preserves_maturity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.accepted_project(base)
            stage_before = (root / ".harness/stages/STAGE_STATE.yaml").read_bytes()
            accepted_before = self.immutable_bytes(root, ".harness/stages/ACCEPTANCE/*.yaml")
            runs_before = self.immutable_bytes(root, ".harness/runtime/RUNS/*.yaml")
            plan = maintenance_plan_document(root, suffix="FLOW-001", task_count=2, product_changing=[True, False])
            start = start_maintenance(root, write_record(base, "maintenance-flow.yaml", plan))
            first_next = next_task(root)
            self.assertEqual(first_next["run_ref"], start["next"]["run_ref"])
            self.assertTrue(first_next["idempotent"])

            first = self.complete_maintenance_task(root, "Maintenance flow step one")
            self.assertIn("next", first)
            self.assertNotIn("stage_gate", first)
            self.assertEqual(first["next"]["maintenance_route"], "MAINTAIN_CURRENT_STAGE")
            second = self.complete_maintenance_task(root, "Maintenance flow step two")
            self.assertEqual(second["maintenance"]["status"], "MAINTENANCE_COMPLETED")
            self.assertNotIn("stage_gate", second)
            self.assertEqual(second["project_status"], "TARGET_LEVEL_REACHED")
            self.assertEqual(second["next_route"], "TARGET_ALREADY_REACHED")

            stage = load_stage_state(root)
            self.assertEqual(stage["highest_accepted_level"], "PROTOTYPE")
            self.assertEqual(stage["target_level"], "PROTOTYPE")
            self.assertEqual((root / ".harness/stages/STAGE_STATE.yaml").read_bytes(), stage_before)
            self.assertEqual(self.immutable_bytes(root, ".harness/stages/ACCEPTANCE/*.yaml"), accepted_before)
            for path, content in runs_before.items():
                self.assertEqual((root / path).read_bytes(), content)

            current = load_data(root / ".harness/maintenance/CURRENT.yaml")
            self.assertIsNone(current["maintenance_current"])
            wp_id = plan["maintenance_plan"]["work_package"]["id"]
            wp_index = load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]
            wp = load_data(root / wp_index["current"][wp_id])["work_package"]
            self.assertEqual(wp["status"], "COMPLETED")
            report_path = root / f".harness/maintenance/REPORTS/{second['maintenance']['report_ref']}.yaml"
            report = load_data(report_path)["maintenance_report"]
            self.assertEqual(report["status"], "COMPLETED")
            self.assertEqual(len(report["task_refs"]), 2)
            self.assertEqual(len(report["run_refs"]), 2)
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_level_up_blocked_while_open_and_allowed_after_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.accepted_project(base)
            plan = maintenance_plan_document(root, suffix="LEVELUP-001")
            start_maintenance(root, write_record(base, "maintenance-level-up.yaml", plan))
            approval = {
                "level_up_approval": {
                    "id": "DEC-HARNESS-DEMO-TASK-CLI-LEVEL-UP-AFTER-MAINT-001",
                    "approved": True,
                    "actor": "ACT-STAGE-APPROVER-001",
                    "approved_at": "2026-08-20T03:00:00Z",
                    "target_level": "ALPHA",
                    "rationale": "Advance only after the open maintenance route closes.",
                }
            }
            approval_path = write_record(base, "level-up-after-maintenance.yaml", approval)
            with self.assertRaisesRegex(ValidationFailure, "maintenance work remains open"):
                level_up(root, "ALPHA", approval_path)

            result = self.complete_maintenance_task(root, "Finish maintenance before level-up")
            self.assertEqual(result["maintenance"]["status"], "MAINTENANCE_COMPLETED")
            level_result = level_up(root, "ALPHA", approval_path)
            self.assertEqual(level_result["status"], "ACTIVE")
            self.assertEqual(level_result["highest_accepted_level"], "PROTOTYPE")
            self.assertEqual(level_result["target_level"], "ALPHA")
            self.assertEqual(level_result["active_stage"], "ALPHA")
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_valid_pre_execution_cancel_restores_previous_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.accepted_project(base)
            stage_before = (root / ".harness/stages/STAGE_STATE.yaml").read_bytes()
            previous_state = deepcopy(load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"])
            previous_next = deepcopy(load_data(root / ".harness/state/NEXT_TASK.yaml"))
            plan = maintenance_plan_document(root, suffix="CANCEL-001")
            start_maintenance(root, write_record(base, "maintenance-cancel.yaml", plan))
            cancel = maintenance_cancel_document(root, suffix="AUTH-001")
            result = cancel_maintenance(root, write_record(base, "maintenance-cancel-approval.yaml", cancel))

            self.assertEqual(result["status"], "MAINTENANCE_CANCELLED")
            self.assertIsNotNone(result["cancelled_run_ref"])
            self.assertEqual((root / ".harness/stages/STAGE_STATE.yaml").read_bytes(), stage_before)
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            for field in ("project_status", "handoff_status", "current_task_ref", "next_route", "active_stage"):
                self.assertEqual(state[field], previous_state[field])
            self.assertIsNone(state["active_run"])
            self.assertEqual(load_data(root / ".harness/state/NEXT_TASK.yaml"), previous_next)
            self.assertIsNone(load_data(root / ".harness/maintenance/CURRENT.yaml")["maintenance_current"])
            run = load_data(root / f".harness/runtime/RUNS/{result['cancelled_run_ref']}.yaml")["run"]
            self.assertEqual(run["status"], "CANCELLED")
            wp_id = plan["maintenance_plan"]["work_package"]["id"]
            wp_index = load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]
            self.assertEqual(load_data(root / wp_index["current"][wp_id])["work_package"]["status"], "CANCELLED")
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_cancel_after_completed_product_change_is_rejected_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.accepted_project(base)
            plan = maintenance_plan_document(root, suffix="NO-SILENT-CANCEL-001", task_count=2, product_changing=[True, False])
            start_maintenance(root, write_record(base, "maintenance-no-silent-cancel.yaml", plan))
            first = self.complete_maintenance_task(root, "Completed product-changing maintenance task")
            self.assertIn("next", first)
            cancel = maintenance_cancel_document(root, suffix="NO-SILENT-001")
            approval_path = write_record(base, "maintenance-no-silent-cancel-approval.yaml", cancel)
            before = self.harness_digests(root)
            with self.assertRaisesRegex(ValidationFailure, "Silent maintenance cancel is forbidden"):
                cancel_maintenance(root, approval_path)
            self.assertEqual(self.harness_digests(root), before)
            current = load_data(root / ".harness/maintenance/CURRENT.yaml")["maintenance_current"]
            self.assertEqual(current["status"], "ACTIVE")
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_wrong_binding_future_scope_and_conflicting_duplicate_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = self.accepted_project(base)
            invalid_plans = [
                maintenance_plan_document(root, suffix="WRONG-LEVEL", level="ALPHA"),
                maintenance_plan_document(root, suffix="WRONG-TARGET", target="ALPHA"),
                maintenance_plan_document(root, suffix="FUTURE-SCOPE", future_stage_refs=["REQ-FUTURE-STAGE@1"]),
                maintenance_plan_document(root, suffix="WRONG-TASK-STAGE", task_stage="ALPHA"),
            ]
            for index, plan in enumerate(invalid_plans, 1):
                with self.subTest(index=index):
                    with self.assertRaises(ValidationFailure):
                        start_maintenance(root, write_record(base, f"invalid-maintenance-{index}.yaml", plan))
            self.assertFalse((root / ".harness/maintenance/CURRENT.yaml").exists())

            valid = maintenance_plan_document(root, suffix="DUPLICATE-001")
            path = write_record(base, "maintenance-duplicate.yaml", valid)
            first = start_maintenance(root, path)
            replay = start_maintenance(root, path)
            self.assertTrue(replay["idempotent"])
            self.assertEqual(first["work_package_ref"], replay["work_package_ref"])
            conflict = deepcopy(valid)
            conflict["maintenance_plan"]["rationale"] = "Conflicting content under the same immutable plan and Decision ids."
            with self.assertRaisesRegex(ValidationFailure, "reused with a different request"):
                start_maintenance(root, write_record(base, "maintenance-duplicate-conflict.yaml", conflict))

    def test_cli_exposes_public_start_and_cancel_operations(self) -> None:
        parser = build_parser()
        start = parser.parse_args(["start-maintenance", "--project", ".", "--plan", "plan.yaml"])
        cancel = parser.parse_args(["cancel-maintenance", "--project", ".", "--approval", "cancel.yaml"])
        self.assertEqual(start.command, "start-maintenance")
        self.assertEqual(cancel.command, "cancel-maintenance")


if __name__ == "__main__":
    unittest.main()

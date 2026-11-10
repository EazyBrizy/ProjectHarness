"""PH-F04: public runtime reachability, exact Stage/Gate and executable-stage fences."""
from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from project_harness.active_stage_planning import plan_active_stage, prepare_active_stage_plan
from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.maintenance import start_maintenance
from project_harness.resources import distribution_root
from project_harness.runtime import block_current, next_task
from project_harness.serialization import load_data, write_data
from project_harness.stages import runtime_continuation, stage_status
from project_harness.validation import validate_project_directory, validate_runtime_reachability
from tests.maintenance_fixtures import maintenance_plan_document, write_record
from tests.ph_f01_fixtures import build_accepted_prototype
from tests.test_engine import prepare_demo


class PHF04RuntimeReachabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="ph-f04-reachability-")
        cls.base = Path(cls.temporary.name)
        cls.planning_template = build_accepted_prototype(cls.base / "prototype")
        _, _, cls.running_template = prepare_demo(cls.base / "running")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def copy(self, fixture: Path, name: str) -> Path:
        project = self.base / name
        if project.exists():
            shutil.rmtree(project)
        shutil.copytree(fixture, project)
        return project

    @staticmethod
    def status_check(root: Path) -> dict:
        return next(check for check in validate_project_directory(root)["checks"]
                    if check["name"] == "Persisted runtime continuation and Stage boundary reachability")

    def test_alpha_planning_has_two_real_public_commands(self) -> None:
        root = self.copy(self.planning_template, "alpha-route")
        before = sha256_file(root / ".harness/stages/STAGE_STATE.yaml")
        first = next_task(root)
        second = next_task(root)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "STAGE_PLANNING_REQUIRED")
        self.assertIn("prepare-active-stage-plan", first["next_command"])
        self.assertIn("plan-active-stage", first["next_operator_route"]["follow_up_command"])
        self.assertEqual(stage_status(root)["runtime_phase"], "STAGE_PLANNING_REQUIRED")
        self.assertEqual(first["next_operator_route"], stage_status(root)["next_operator_route"])
        self.assertEqual(self.status_check(root)["status"], "PASS")
        self.assertEqual(before, sha256_file(root / ".harness/stages/STAGE_STATE.yaml"))
        for command in ("next", "stage-status", "validate-project"):
            result = subprocess.run([sys.executable, str(distribution_root() / "project-harness.py"), command,
                                     "--project", str(root)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn(payload["status"], {"ACTIVE", "STAGE_PLANNING_REQUIRED", "PASS"})

    def test_planned_ready_jit_is_stable_and_current_stage_only(self) -> None:
        root = self.copy(self.planning_template, "planned-ready")
        record = self.base / "f04-alpha-plan.yaml"
        prepare_active_stage_plan(root, record, force=True)
        applied = plan_active_stage(root, record)
        self.assertEqual(applied["status"], "STAGE_PLANNED")
        initial = next_task(root)
        before = sorted(path.name for path in (root / ".harness/runtime/RUN_PLANS").glob("*.yaml"))
        self.assertEqual(initial["status"], "READY_FOR_CODEX")
        self.assertEqual(initial["implementation_stage"], "ALPHA")
        self.assertEqual(stage_status(root)["runtime_phase"], "READY_FOR_CODEX")
        self.assertIn("project-harness verify", stage_status(root)["next_operator_route"]["command"])
        self.assertEqual(self.status_check(root)["status"], "PASS")
        repeated = plan_active_stage(root, record)
        self.assertTrue(repeated.get("idempotent"))
        self.assertEqual(repeated["first_jit"]["run_ref"], initial["run_ref"])
        self.assertEqual(next_task(root)["run_ref"], initial["run_ref"])
        self.assertEqual(before, sorted(path.name for path in (root / ".harness/runtime/RUN_PLANS").glob("*.yaml")))

    def test_next_recomputes_operator_route_after_ready_task_reservation(self) -> None:
        # A Task is READY with no Run; reserving it moves persisted state from
        # public `next` to public `verify`. Never return a stale next command.
        root = self.copy(self.running_template, "reserve-new-run-route")
        path = root / ".harness/state/CURRENT_STATE.yaml"
        document = load_data(path)
        document["state"]["active_run"] = None
        document["state"]["next_route"] = "COMPILE_FIRST_READY_TASK"
        write_data(path, document)

        def reserve_once(project: Path, task_ref: str) -> dict:
            updated = load_data(path)
            updated["state"]["active_run"] = {"task_ref": task_ref}
            updated["state"]["next_route"] = "EXECUTE_CURRENT_TASK_WITH_CODEX"
            write_data(path, updated)
            return {"status": "READY_FOR_CODEX", "run_ref": "RUN-F04-RESERVED-001"}

        with patch("project_harness.runtime.reserve_run", side_effect=reserve_once):
            reserved = next_task(root)
        self.assertEqual(reserved["status"], "READY_FOR_CODEX")
        self.assertEqual(reserved["next_operator_route"]["route"], "VERIFY_CURRENT_TASK")
        self.assertIn("project-harness verify", reserved["next_command"])

    def test_terminal_release_does_not_advertise_impossible_level_up(self) -> None:
        # RELEASE is the final canonical level; no higher target exists.
        root = self.copy(self.planning_template, "terminal-release-route")
        terminal = {"project_status": "TARGET_LEVEL_REACHED", "next_route": "TARGET_ALREADY_REACHED", "current_task_ref": None, "active_run": None}
        accepted_release = {
            "state": {"highest_accepted_level": "RELEASE"},
            "target_level": "RELEASE", "plan": {"status": "ACCEPTED"},
            "gate": {"status": "ACCEPTED"},
        }
        with patch("project_harness.stages._current_stage_gate_context", return_value=accepted_release):
            route = runtime_continuation(root, terminal)
        self.assertEqual(route["route"], "TARGET_ALREADY_REACHED")
        self.assertIsNone(route["command"])
        self.assertIn("start-maintenance", route["optional_command"])

    def test_unsupported_boundary_is_defect_not_stage_planning(self) -> None:
        root = self.copy(self.planning_template, "synthetic-dead-end")
        current_path = root / ".harness/state/CURRENT_STATE.yaml"
        state = load_data(current_path)
        state["state"]["next_route"] = "UNIMPLEMENTED_INVISIBLE_STAGE_ROUTE"
        write_data(current_path, state)
        self.assertEqual(self.status_check(root)["status"], "FAIL")
        self.assertTrue(any("No supported continuation" in error for error in validate_runtime_reachability(root)["errors"]))
        self.assertEqual(stage_status(root)["next_operator_route"]["route"], "INVALID_RUNTIME_ROUTE")
        with self.assertRaises(ValidationFailure):
            next_task(root)
        validation = validate_project_directory(root)
        self.assertEqual(validation["status"], "FAIL")
        accepted_files = (root / ".harness/stages/ACCEPTANCE").glob("*.yaml")
        self.assertEqual(len(list(accepted_files)), 1)

    def test_inconsistent_planning_contract_is_rejected_before_reservation(self) -> None:
        root = self.copy(self.planning_template, "mismatched-stage-plan")
        status = stage_status(root)
        gate_path = root / status["gate_path"]
        gate = load_data(gate_path)
        gate["stage_gate"]["stage_plan_ref"] = status["stage_plan_ref"].rsplit("@", 1)[0] + "@1"
        write_data(gate_path, gate)
        before_index = sha256_file(root / ".harness/tasks/INDEX.yaml")
        with self.assertRaises(ValidationFailure):
            next_task(root)
        self.assertEqual(self.status_check(root)["status"], "FAIL")
        self.assertEqual(before_index, sha256_file(root / ".harness/tasks/INDEX.yaml"))

    def test_forged_stage_boundary_without_review_contract_is_not_actionable(self) -> None:
        root = self.copy(self.planning_template, "forgot-review")
        status = stage_status(root)
        plan_path = root / status["stage_plan_path"]
        doc = load_data(plan_path)
        doc["stage_plan"]["review_required"] = False
        write_data(plan_path, doc)
        self.assertEqual(self.status_check(root)["status"], "FAIL")
        self.assertEqual(stage_status(root)["next_operator_route"]["route"], "INVALID_RUNTIME_ROUTE")
        with self.assertRaises(ValidationFailure):
            next_task(root)

    def test_future_stage_task_cannot_get_new_jit_even_if_scheduler_tampered(self) -> None:
        root = self.copy(self.planning_template, "future-stage-fence")
        # Existing completed prototype Tasks remain in the index; no Alpha
        # Task has been authorized. A forced current Beta Task must fail closed.
        task_index_path = root / ".harness/tasks/INDEX.yaml"
        index = load_data(task_index_path)
        old_id = index["task_index"]["order"][0]
        old = load_data(root / index["task_index"]["current"][old_id])["task"]
        future = dict(old)
        future["id"] = old["id"] + "-FORGED-BETA"
        future["revision"] = 1
        future["status"] = "READY"
        future["implementation_stage"] = "BETA"
        future["depends_on_tasks"] = []
        future_path = f".harness/tasks/{future['id']}@1.yaml"
        write_data(root / future_path, {"task": future})
        index["task_index"]["order"].append(future["id"])
        index["task_index"]["current"][future["id"]] = future_path
        write_data(task_index_path, index)
        state_path = root / ".harness/state/CURRENT_STATE.yaml"
        doc = load_data(state_path)
        doc["state"]["current_task_ref"] = future["id"]
        doc["state"]["task_order"].append(future["id"])
        doc["state"]["next_route"] = "COMPILE_FIRST_READY_TASK"
        write_data(state_path, doc)
        before = sha256_file(task_index_path)
        with self.assertRaises(ValidationFailure) as captured:
            next_task(root)
        self.assertIn("STAGE_SCOPE_VIOLATION", str(captured.exception))
        self.assertEqual(before, sha256_file(task_index_path))
        self.assertEqual(self.status_check(root)["status"], "FAIL")

    def test_ordinary_blocker_is_not_stage_gate_blocker(self) -> None:
        root = self.copy(self.running_template, "ordinary-blocker")
        result = block_current(root, "Missing approved implementation detail", options=["Supply scoped clarification"])
        self.assertEqual(result["status"], "BLOCKED")
        current = stage_status(root)
        self.assertEqual(current["runtime_phase"], "TASK_BLOCKED")
        self.assertEqual(current["next_operator_route"]["route"], "RESUME_BLOCKED_TASK")
        self.assertIn("project-harness resume", next_task(root)["next_command"])
        self.assertEqual(self.status_check(root)["status"], "PASS")

    def test_maintenance_running_at_predecessor_stage_is_not_future_work(self) -> None:
        root = self.copy(self.planning_template, "maintenance-during-alpha-planning")
        document = maintenance_plan_document(root, suffix="F04-REACH", task_count=1)
        record = write_record(self.base, "f04-maintenance.yaml", document)
        started = start_maintenance(root, record)
        self.assertEqual(started["status"], "MAINTENANCE_ACTIVE")
        self.assertEqual(started["next"]["implementation_stage"], "PROTOTYPE")
        stage = stage_status(root)
        self.assertEqual(stage["runtime_phase"], "MAINTENANCE")
        self.assertEqual(stage["active_stage"], "ALPHA")
        self.assertEqual(stage["maintenance_route"], "MAINTAIN_CURRENT_STAGE")
        self.assertEqual(next_task(root)["implementation_stage"], "PROTOTYPE")
        check = self.status_check(root)
        self.assertEqual(check["status"], "PASS", check["details"])
        self.assertEqual(validate_project_directory(root)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

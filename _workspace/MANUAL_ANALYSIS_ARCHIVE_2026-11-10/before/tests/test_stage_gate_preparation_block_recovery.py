from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest

from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.runtime import complete_current, next_task, verify_current
from project_harness.serialization import load_data, write_data
from project_harness.stage_approvals import validate_stage_approval_document
from project_harness.stage_gate_lifecycle import evaluate_stage_gate_readiness, resume_stage_gate
from project_harness.stages import accept_stage, prepare_stage_approval, stage_status
from project_harness.validation import validate_project_directory
from tests.test_engine import (
    implement_first_task,
    implement_second_task,
    load_fixture,
    prepare_demo,
    write_agent_result,
)
from tests.test_implementation_levels import ACTOR, APPROVED_AT, current_gate


class StageGatePreparationBlockRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._suite_temp = tempfile.TemporaryDirectory()
        suite = Path(cls._suite_temp.name)
        data = load_fixture()
        data["implementation"]["target_level"] = "PROTOTYPE"

        _, _, root = prepare_demo(suite / "ordinary", data=data)
        implement_first_task(root)
        verification = verify_current(root, allow_command_execution=True)
        complete_current(root, write_agent_result(root, verification, "Implemented add/list"))
        implement_second_task(root)
        cls.last_ordinary_template = root

        cls.verifying_template = suite / "verifying-template"
        shutil.copytree(root, cls.verifying_template)
        cls._trigger_preparation(cls.verifying_template)
        cls._complete_preparation(cls.verifying_template)
        if stage_status(cls.verifying_template)["gate_status"] != "VERIFYING":
            raise AssertionError(stage_status(cls.verifying_template))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._suite_temp.cleanup()

    def setUp(self) -> None:
        self._case_temp = tempfile.TemporaryDirectory()
        self.base = Path(self._case_temp.name)

    def tearDown(self) -> None:
        self._case_temp.cleanup()

    @staticmethod
    def _trigger_preparation(root: Path) -> dict:
        verification = verify_current(root, allow_command_execution=True)
        result = complete_current(root, write_agent_result(root, verification, "Implemented final ordinary Task"))
        if result.get("stage_gate", {}).get("status") != "STAGE_ACCEPTANCE_PREPARATION":
            raise AssertionError(result)
        return result

    @staticmethod
    def _complete_preparation(root: Path) -> dict:
        verification = verify_current(root, allow_command_execution=True)
        result = complete_current(root, write_agent_result(root, verification, "Prepared exact final-baseline Gate evidence"))
        if result.get("stage_gate", {}).get("status") != "BLOCKED":
            raise AssertionError(result)
        from tests.gate_proof_fixtures import all_gate_subjects
        all_gate_subjects(root)
        resumed = resume_stage_gate(root)
        if resumed.get("status") != "VERIFYING":
            raise AssertionError(resumed)
        return {"stage_gate": resumed}

    def _copy(self, template: Path, name: str) -> Path:
        root = self.base / name
        shutil.copytree(template, root)
        return root

    @staticmethod
    def _snapshot(root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): sha256_file(path)
            for path in sorted(root.rglob("*"))
            if path.is_file() and not path.is_symlink()
        }

    def _strict_approval(
        self,
        root: Path,
        *,
        name: str,
        decision_id: str,
        open_field: str | None = None,
        open_index: int = 0,
        open_status: str = "UNKNOWN",
    ) -> tuple[Path, dict]:
        path = self.base / name
        prepare_stage_approval(root, path)
        document = load_data(path)
        approval = document["stage_approval"]
        by_subject: dict[str, list[str]] = {}
        for candidate in approval["evidence_candidates"]:
            for subject in candidate["compatible_subject_refs"]:
                by_subject.setdefault(subject, []).append(candidate["ref"])

        result_fields = (
            ("outcome_results", "outcome_ref"),
            ("criteria_results", "criterion_ref"),
            ("hard_constraint_results", "constraint_ref"),
            ("profile_control_results", "control_ref"),
        )
        for field, ref_field in result_fields:
            for item in approval[field]:
                subject = item[ref_field]
                candidates = sorted(set(by_subject.get(subject) or []))
                if not candidates:
                    raise AssertionError({"field": field, "subject": subject, "candidates": approval["evidence_candidates"]})
                item.update(
                    {
                        "status": "PASS",
                        "evidence_refs": [candidates[0]],
                        "rationale": "Validated against the exact final product-tree baseline.",
                        "validator": ACTOR,
                    }
                )

        if open_field is not None:
            item = approval[open_field][open_index]
            item.update(
                {
                    "status": open_status,
                    "evidence_refs": [],
                    "rationale": "Formal review did not confirm this mandatory result.",
                    "validator": ACTOR,
                }
            )

        approval.update(
            {
                "record_state": "APPROVED",
                "id": decision_id,
                "approved": True,
                "actor": ACTOR,
                "approved_at": APPROVED_AT,
                "known_limitations": ["Bounded local test fixture."],
                "next_stage_gaps": ["No next Stage is activated when the target is reached."],
                "notes": "Strict exact-bound formal Stage review.",
            }
        )
        approval["permitted_use"]["status"] = "CONFIRMED"
        validate_stage_approval_document(document)
        write_data(path, document)
        return path, approval

    def test_last_ordinary_task_creates_one_idempotent_preparation_wp_and_first_jit(self) -> None:
        root = self._copy(self.last_ordinary_template, "one-preparation")
        before_tasks = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
        before_wps = load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]
        before_bundles = set((root / ".harness/prompts/BUNDLES_BY_RUN").glob("*.yaml"))

        result = self._trigger_preparation(root)
        stage_gate = result["stage_gate"]
        bundle = result["next"]
        self.assertEqual(stage_gate["status"], "STAGE_ACCEPTANCE_PREPARATION")
        self.assertEqual(bundle["status"], "READY_FOR_CODEX")
        self.assertEqual(bundle["task_ref"], stage_gate["task_ref"])

        task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
        wp_index = load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]
        self.assertEqual(len(task_index["order"]), len(before_tasks["order"]) + 1)
        self.assertEqual(len(wp_index["order"]), len(before_wps["order"]) + 1)
        self.assertEqual(len(set((root / ".harness/prompts/BUNDLES_BY_RUN").glob("*.yaml")) - before_bundles), 1)

        task_id = stage_gate["task_ref"].split("@", 1)[0]
        task = load_data(root / task_index["current"][task_id])["task"]
        wp_id = stage_gate["work_package_ref"].split("@", 1)[0]
        wp = load_data(root / wp_index["current"][wp_id])["work_package"]
        state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
        self.assertEqual(task["stage_acceptance_preparation"]["kind"], "STAGE_ACCEPTANCE_PREPARATION")
        self.assertEqual(wp["kind"], "STAGE_ACCEPTANCE_PREPARATION")
        self.assertEqual(task["implementation_stage"], "PROTOTYPE")
        self.assertEqual(wp["implementation_stage"], "PROTOTYPE")
        self.assertEqual(state["current_task_ref"], task_id)
        self.assertIn(task_id, state["task_order"])
        self.assertEqual(state["next_route"], "EXECUTE_CURRENT_TASK_WITH_CODEX")

        repeated = evaluate_stage_gate_readiness(root)
        self.assertTrue(repeated["idempotent"])
        self.assertEqual(repeated["task_ref"], stage_gate["task_ref"])
        self.assertEqual(repeated["next"]["run_ref"], bundle["run_ref"])
        self.assertEqual(load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]["order"], task_index["order"])
        self.assertEqual(load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]["order"], wp_index["order"])
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_preparation_completion_refreshes_verifying_gate_and_exact_draft_without_future_stage_work(self) -> None:
        root = self._copy(self.last_ordinary_template, "complete-preparation")
        preparation = self._trigger_preparation(root)["stage_gate"]
        prep_plan_ref = preparation["stage_plan_ref"]
        prep_gate_ref = preparation["gate_ref"]

        task_id = preparation["task_ref"].split("@", 1)[0]
        task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
        task = load_data(root / task_index["current"][task_id])["task"]
        self.assertEqual(task["stage_acceptance_preparation"]["future_stage_work"], "FORBIDDEN")
        self.assertEqual(task["requirement_refs"], [])
        self.assertEqual(task["produces_artifacts"], ["IMMUTABLE_GATE_EVIDENCE_BINDINGS"])
        self.assertNotIn("src/**", task["scope"]["write"])
        self.assertTrue(all("ALPHA" not in str(item) for item in task["stage_acceptance_preparation"]["missing_gate_items"]))

        completed = self._complete_preparation(root)["stage_gate"]
        self.assertEqual(completed["status"], "VERIFYING")
        self.assertNotEqual(completed["stage_plan_ref"], prep_plan_ref)
        self.assertNotEqual(completed["gate_ref"], prep_gate_ref)
        status = stage_status(root)
        self.assertEqual(status["stage_plan_status"], "VERIFYING")
        self.assertEqual(status["gate_status"], "VERIFYING")
        self.assertEqual(status["next_operator_route"]["route"], "PREPARE_STAGE_APPROVAL")

        draft_path = self.base / "exact-draft.yaml"
        prepare_stage_approval(root, draft_path)
        approval = load_data(draft_path)["stage_approval"]
        self.assertEqual(approval["stage_plan_ref"], status["stage_plan_ref"])
        self.assertEqual(approval["gate_ref"], status["gate_ref"])
        self.assertEqual(approval["gate_digest"], status["gate_digest"])
        self.assertEqual(approval["baseline_revision"], status["baseline_revision"])
        subjects = {
            item[field]
            for collection, field in (
                (approval["outcome_results"], "outcome_ref"),
                (approval["criteria_results"], "criterion_ref"),
                (approval["hard_constraint_results"], "constraint_ref"),
                (approval["profile_control_results"], "control_ref"),
            )
            for item in collection
        }
        candidate_subjects = {
            subject
            for candidate in approval["evidence_candidates"]
            for subject in candidate["compatible_subject_refs"]
        }
        self.assertTrue(subjects.issubset(candidate_subjects))
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_malformed_strict_approvals_do_not_mutate_state(self) -> None:
        mutations = ("schema", "invalid_na", "wrong_ref")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                root = self._copy(self.verifying_template, f"malformed-{mutation}")
                path, approval = self._strict_approval(
                    root,
                    name=f"{mutation}.yaml",
                    decision_id=f"DEC-MALFORMED-{mutation.upper()}-001",
                )
                document = load_data(path)
                if mutation == "schema":
                    document["stage_approval"]["unexpected"] = True
                elif mutation == "invalid_na":
                    item = document["stage_approval"]["criteria_results"][0]
                    item.update({"status": "NOT_APPLICABLE", "evidence_refs": [], "rationale": None, "validator": None})
                else:
                    gate_ref = str(document["stage_approval"]["gate_ref"])
                    document["stage_approval"]["gate_ref"] = gate_ref.split("@", 1)[0] + "@999999"
                write_data(path, document)
                before = self._snapshot(root)
                with self.assertRaises(ValidationFailure):
                    accept_stage(root, "PROTOTYPE", path)
                self.assertEqual(self._snapshot(root), before)
                self.assertEqual(stage_status(root)["gate_status"], "VERIFYING")
                self.assertEqual(list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")), [])

    def test_valid_unknown_persists_gate_blocker_then_recovers_to_verifying_and_accepts_target(self) -> None:
        root = self._copy(self.verifying_template, "blocked-recover-verifying")
        original_status = stage_status(root)
        approval_path, _ = self._strict_approval(
            root,
            name="unknown-review.yaml",
            decision_id="DEC-STRICT-UNKNOWN-001",
            open_field="outcome_results",
        )
        result = accept_stage(root, "PROTOTYPE", approval_path)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["next_route"], "RESOLVE_STAGE_GATE")
        self.assertFalse(result["acceptance_created"])
        self.assertEqual(list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")), [])

        blocked_status = stage_status(root)
        self.assertEqual(blocked_status["status"], "BLOCKED")
        self.assertEqual(blocked_status["stage_plan_status"], "BLOCKED")
        self.assertEqual(blocked_status["gate_status"], "BLOCKED")
        self.assertGreater(blocked_status["stage_plan_revision"], original_status["stage_plan_revision"])
        self.assertGreater(blocked_status["gate_revision"], original_status["gate_revision"])
        self.assertEqual(blocked_status["next_operator_route"]["route"], "RESUME_STAGE_GATE")
        blocked_next = next_task(root)
        self.assertEqual(blocked_next["blocker_kind"], "STAGE_GATE_BLOCKER")
        blocker_ref = result["blocker_ref"]
        blocker = load_data(root / f".harness/blockers/{blocker_ref}.yaml")["blocker"]
        self.assertEqual(blocker["kind"], "STAGE_GATE_BLOCKER")
        self.assertEqual(blocker["status"], "OPEN")
        self.assertTrue(blocker["failed_or_missing_items"])
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

        resumed = resume_stage_gate(root)
        self.assertEqual(resumed["status"], "VERIFYING")
        self.assertNotEqual(resumed["stage_plan_ref"], result["stage_plan_ref"])
        self.assertNotEqual(resumed["gate_ref"], result["gate_ref"])
        replay = resume_stage_gate(root)
        self.assertTrue(replay["idempotent"])
        self.assertEqual(replay["status"], "VERIFYING")

        final_path, _ = self._strict_approval(
            root,
            name="accepted-after-recovery.yaml",
            decision_id="DEC-STRICT-RECOVERED-001",
        )
        accepted = accept_stage(root, "PROTOTYPE", final_path)
        self.assertEqual(accepted["status"], "TARGET_LEVEL_REACHED")
        self.assertEqual(accepted["accepted_levels"], ["PROTOTYPE"])
        accepted_gate = current_gate(root, "PROTOTYPE")
        self.assertEqual(accepted_gate["status"], "ACCEPTED")
        self.assertTrue(all(item["status"] == "PASS" for item in accepted_gate["outcome_results"]))
        self.assertTrue(all(item["status"] == "PASS" for item in accepted_gate["profile_control_results"]))
        self.assertTrue(all(item["status"] == "PASS" for item in accepted_gate["hard_constraint_results"]))
        self.assertEqual(next_task(root)["status"], "TARGET_LEVEL_REACHED")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_baseline_drift_recovery_returns_active_preparation_then_accepts(self) -> None:
        root = self._copy(self.verifying_template, "blocked-recover-active")
        approval_path, _ = self._strict_approval(
            root,
            name="failed-review.yaml",
            decision_id="DEC-STRICT-FAIL-001",
            open_field="criteria_results",
            open_status="FAIL",
        )
        blocked = accept_stage(root, "PROTOTYPE", approval_path)
        self.assertEqual(blocked["status"], "BLOCKED")

        drift = root / "src/recovery-drift.txt"
        drift.parent.mkdir(parents=True, exist_ok=True)
        drift.write_text("new exact product baseline\n", encoding="utf-8")
        resumed = resume_stage_gate(root)
        self.assertEqual(resumed["status"], "STAGE_ACCEPTANCE_PREPARATION")
        self.assertEqual(resumed["next_route"], "STAGE_ACCEPTANCE_PREPARATION")
        self.assertIn("next", resumed)
        state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
        self.assertEqual(state["project_status"], "ACTIVE")
        self.assertEqual(state["next_route"], "EXECUTE_CURRENT_TASK_WITH_CODEX")
        self.assertEqual(state["current_task_ref"], resumed["task_ref"].split("@", 1)[0])

        task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
        task = load_data(root / task_index["current"][state["current_task_ref"]])["task"]
        self.assertEqual(task["implementation_stage"], "PROTOTYPE")
        self.assertEqual(task["stage_acceptance_preparation"]["future_stage_work"], "FORBIDDEN")
        self.assertNotIn("src/**", task["scope"]["write"])
        self.assertTrue(all(item["baseline_revision"] == stage_status(root)["baseline_revision"] for item in task["stage_acceptance_preparation"]["missing_gate_items"]))

        completed = self._complete_preparation(root)
        self.assertEqual(completed["stage_gate"]["status"], "VERIFYING")
        accepted_path, _ = self._strict_approval(
            root,
            name="accepted-after-new-evidence.yaml",
            decision_id="DEC-STRICT-NEW-EVIDENCE-001",
        )
        accepted = accept_stage(root, "PROTOTYPE", accepted_path)
        self.assertEqual(accepted["status"], "TARGET_LEVEL_REACHED")
        self.assertEqual(next_task(root)["status"], "TARGET_LEVEL_REACHED")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

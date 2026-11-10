"""PH-F03: governed, exact-bound current Stage planning integration and rejection cases."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from project_harness.active_stage_planning import prepare_active_stage_plan, plan_active_stage
from project_harness.errors import ValidationFailure, SafetyViolation
from project_harness.hashing import sha256_file
from project_harness.resources import distribution_root
from project_harness.runtime import next_task
from project_harness.serialization import load_data, write_data
from project_harness.stages import level_up, stage_status
from project_harness.validation import validate_project_directory
from tests.ph_f01_fixtures import build_accepted_prototype, build_target_reached_mvp
from tests.test_implementation_levels import ACTOR, APPROVED_AT, write_approval


class PHF03ActiveStagePlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="ph-f03-active-")
        cls.folder = Path(cls.temp.name)
        cls.prototype = build_accepted_prototype(cls.folder / "prototype")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def case(self, name: str) -> tuple[Path, Path]:
        project = self.folder / f"{name}-project"
        if project.exists():
            shutil.rmtree(project)
        shutil.copytree(self.prototype, project)
        draft_path = self.folder / f"{name}-review.json"
        draft_path.unlink(missing_ok=True)
        return project, draft_path

    @staticmethod
    def preserved(root: Path) -> dict[str, str]:
        protected = [root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml"]
        for folder in [".harness/stages/ACCEPTANCE", ".harness/stages/STATE_HISTORY", ".harness/runs"]:
            protected.extend(sorted((root / folder).rglob("*.yaml")))
        return {p.relative_to(root).as_posix(): sha256_file(p) for p in protected}

    def test_read_only_draft_schema_and_public_cli(self) -> None:
        root, path = self.case("readonly")
        before = self.preserved(root)
        state_digest = sha256_file(root / ".harness/stages/STAGE_STATE.yaml")
        result = prepare_active_stage_plan(root, path)
        self.assertEqual(result["status"], "DRAFT_PREPARED")
        self.assertFalse(result["control_plane_mutated"])
        self.assertEqual(before, self.preserved(root))
        self.assertEqual(state_digest, sha256_file(root / ".harness/stages/STAGE_STATE.yaml"))
        draft = load_data(path)["active_stage_plan_review"]
        self.assertEqual(draft["binding"]["highest_accepted_level"], "PROTOTYPE")
        self.assertEqual(draft["binding"]["active_stage"], "ALPHA")
        self.assertEqual(draft["review"]["decision"], None)
        self.assertTrue(draft["planning_basis"]["criteria_refs"])
        self.assertEqual({wp["implementation_stage"] for wp in draft["work_packages"]}, {"ALPHA"})
        self.assertTrue(all(t["implementation_stage"] == "ALPHA" and t["future_stage_work"] == "FORBIDDEN"
                            for wp in draft["work_packages"] for t in wp["tasks"]))
        self.assertEqual(next_task(root)["status"], "STAGE_PLANNING_REQUIRED")
        self.assertIn("prepare-active-stage-plan", stage_status(root)["next_operator_route"]["command"])
        cli_result = subprocess.run([sys.executable, str(distribution_root() / "project-harness.py"), "prepare-active-stage-plan",
                                    "--project", str(root), "--output", str(path)], capture_output=True, text=True)
        self.assertEqual(cli_result.returncode, 0, cli_result.stderr)
        self.assertEqual(json.loads(cli_result.stdout)["status"], "DRAFT_PREPARED")

    def test_alpha_apply_exact_revision_indexes_first_jit_and_replay(self) -> None:
        root, path = self.case("alpha")
        old = self.preserved(root)
        draft = prepare_active_stage_plan(root, path)
        result = plan_active_stage(root, path)
        self.assertEqual(result["status"], "STAGE_PLANNED")
        self.assertEqual(result["active_stage"], "ALPHA")
        self.assertEqual(result["first_jit"]["status"], "READY_FOR_CODEX")
        self.assertEqual(next_task(root)["status"], "READY_FOR_CODEX")
        self.assertEqual(stage_status(root)["highest_accepted_level"], "PROTOTYPE")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")
        self.assertEqual(old, {k: self.preserved(root)[k] for k in old})
        self.assertGreater(int(result["stage_plan_ref"].split("@")[-1]), 1)
        self.assertGreater(int(result["gate_ref"].split("@")[-1]), 1)
        plan = load_data(root / f".harness/stages/PLANS/{result['stage_plan_ref']}.yaml")["stage_plan"]
        gate = load_data(root / f".harness/stages/GATES/{result['gate_ref']}.yaml")["stage_gate"]
        self.assertEqual(plan["gate_ref"], result["gate_ref"])
        self.assertEqual(gate["stage_plan_ref"], result["stage_plan_ref"])
        self.assertEqual(gate["required_work_package_refs"], result["work_package_refs"])
        self.assertEqual(len(plan["detailed_work_package_refs"]), 1)
        self.assertEqual(draft["candidate_task_count"], result["task_count"])
        status_after = self.preserved(root)
        stage_doc_before = sha256_file(root / ".harness/stages/STAGE_STATE.yaml")
        repeat = plan_active_stage(root, path)
        self.assertTrue(repeat.get("idempotent"))
        self.assertEqual(repeat["first_task_ref"], result["first_task_ref"])
        self.assertEqual(stage_doc_before, sha256_file(root / ".harness/stages/STAGE_STATE.yaml"))
        self.assertEqual(status_after, self.preserved(root))
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_stale_product_baseline_fails_before_mutation(self) -> None:
        root, path = self.case("stale-product")
        prepare_active_stage_plan(root, path)
        (root / "README.md").write_text((root / "README.md").read_text() + "\nupdated product\n")
        before = sha256_file(root / ".harness/stages/STAGE_STATE.yaml")
        with self.assertRaises(ValidationFailure):
            plan_active_stage(root, path)
        self.assertEqual(before, sha256_file(root / ".harness/stages/STAGE_STATE.yaml"))
        self.assertEqual(next_task(root)["status"], "STAGE_PLANNING_REQUIRED")

    def test_tampered_binding_and_future_work_rejected(self) -> None:
        root, path = self.case("tamper")
        prepare_active_stage_plan(root, path)
        doc = load_data(path)
        doc["active_stage_plan_review"]["binding"]["target_level"] = "BETA"
        write_data(path, doc)
        with self.assertRaises(ValidationFailure):
            plan_active_stage(root, path)
        self.assertEqual(next_task(root)["status"], "STAGE_PLANNING_REQUIRED")
        prepare_active_stage_plan(root, path, force=True)
        doc = load_data(path)
        doc["active_stage_plan_review"]["work_packages"][0]["tasks"][0]["implementation_stage"] = "BETA"
        write_data(path, doc)
        with self.assertRaises(ValidationFailure):
            plan_active_stage(root, path)

    def test_edited_record_needs_review_and_material_change_is_blocked(self) -> None:
        root, path = self.case("review")
        prepare_active_stage_plan(root, path)
        doc = load_data(path)
        body = doc["active_stage_plan_review"]
        body["work_packages"][0]["tasks"][0]["purpose"] += " Verify application-specific use case."
        write_data(path, doc)
        with self.assertRaises(ValidationFailure):
            plan_active_stage(root, path)
        body["review"]["decision"] = {
            "id": f"DEC-{body['id'].removeprefix('RQP-')}-REVIEW",
            "kind": "ACTIVE_STAGE_PLAN_REVIEW", "approved": True, "actor": ACTOR, "approved_at": APPROVED_AT,
            "rationale": "Reviewed in the existing accepted product scope.",
        }
        body["review"]["material_change"] = True
        write_data(path, doc)
        with self.assertRaises(ValidationFailure):
            plan_active_stage(root, path)
        body["review"]["material_change"] = False
        write_data(path, doc)
        result = plan_active_stage(root, path)
        self.assertEqual(result["status"], "STAGE_PLANNED")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")
        ref = body["review"]["decision"]["id"]
        self.assertTrue((root / f".harness/canonical/DECISIONS/{ref}@1.yaml").is_file())

    def test_no_write_to_control_plane_or_unaccepted_requirements(self) -> None:
        root, path = self.case("no-scope")
        prepare_active_stage_plan(root, path)
        doc = load_data(path)
        body = doc["active_stage_plan_review"]
        body["work_packages"][0]["tasks"][0]["scope"]["write"].append(".harness/state/CURRENT_STATE.yaml")
        body["review"]["decision"] = {
            "id": f"DEC-{body['id'].removeprefix('RQP-')}-REVIEW",
            "kind": "ACTIVE_STAGE_PLAN_REVIEW", "approved": True, "actor": ACTOR, "approved_at": APPROVED_AT,
            "rationale": "Reviewed.",
        }
        write_data(path, doc)
        with self.assertRaises((ValidationFailure, SafetyViolation)):
            plan_active_stage(root, path)
        prepare_active_stage_plan(root, path, force=True)
        doc = load_data(path)
        body = doc["active_stage_plan_review"]
        body["work_packages"][0]["tasks"][0]["requirement_refs"].append("REQ-UNACCEPTED@1")
        body["review"]["decision"] = {
            "id": f"DEC-{body['id'].removeprefix('RQP-')}-REVIEW",
            "kind": "ACTIVE_STAGE_PLAN_REVIEW", "approved": True, "actor": ACTOR, "approved_at": APPROVED_AT, "rationale": "Reviewed.",
        }
        write_data(path, doc)
        with self.assertRaises(ValidationFailure):
            plan_active_stage(root, path)

    def test_transaction_recovery_restores_pre_plan_boundary(self) -> None:
        root, path = self.case("recovery")
        prepare_active_stage_plan(root, path)
        from project_harness import stage_transactions
        original_replace = stage_transactions.os.replace
        fail = {"occurred": False}

        def interrupted(src, dest):
            if not fail["occurred"] and Path(dest).parts[-3:] == (".harness", "stages", "STAGE_STATE.yaml"):
                fail["occurred"] = True
                raise OSError("injected planner interruption")
            return original_replace(src, dest)

        with patch.object(stage_transactions.os, "replace", side_effect=interrupted):
            with self.assertRaises(Exception):
                plan_active_stage(root, path)
        # The journal must either recover the entire old or entire new transaction.
        from project_harness.stage_transactions import recover_stage_transactions
        recover_stage_transactions(root)
        self.assertEqual(stage_status(root)["next_route"], "PLAN_ACTIVE_STAGE")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")
        # A transaction ID from a rolled-back transaction is never reused.
        with self.assertRaises(ValidationFailure):
            plan_active_stage(root, path)
        prepare_active_stage_plan(root, path, force=True)
        new_doc = load_data(path)["active_stage_plan_review"]
        self.assertIn("-RETRY-02", new_doc["id"])
        result = plan_active_stage(root, path)
        self.assertEqual(result["status"], "STAGE_PLANNED")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_level_up_mvp_release_first_ready_jit(self) -> None:
        root = build_target_reached_mvp(self.folder / "release-case")
        acceptance_before = self.preserved(root)
        approval = {"level_up_approval": {
            "id": "DEC-PH-F03-RELEASE-001", "approved": True, "actor": ACTOR, "approved_at": APPROVED_AT,
            "target_level": "RELEASE", "rationale": "Governed advancement from accepted MVP to Release."}}
        level_up(root, "RELEASE", write_approval(self.folder, "f03-release-approval.yaml", approval))
        path = self.folder / "release-review.yaml"
        self.assertEqual(next_task(root)["status"], "STAGE_PLANNING_REQUIRED")
        prepare_active_stage_plan(root, path)
        result = plan_active_stage(root, path)
        self.assertEqual(result["active_stage"], "RELEASE")
        self.assertEqual(result["first_jit"]["status"], "READY_FOR_CODEX")
        self.assertEqual(stage_status(root)["highest_accepted_level"], "MVP")
        self.assertEqual(next_task(root)["implementation_stage"], "RELEASE")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")
        self.assertEqual(acceptance_before, {k: self.preserved(root)[k] for k in acceptance_before})
        self.assertEqual(load_data(root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml")["implementation"]["target_level"], "MVP")


if __name__ == "__main__":
    unittest.main()

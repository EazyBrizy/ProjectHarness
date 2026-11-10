from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from project_harness import prepare_stage_approval as public_prepare_stage_approval
from project_harness import product_baseline_revision as public_product_baseline_revision
from project_harness.evidence import normalized_evidence_body, write_normalized_evidence
from project_harness.errors import ValidationFailure, WaitingDecision
from project_harness.hashing import sha256_file
from project_harness.serialization import load_data, write_data
from project_harness.stage_approvals import validate_stage_approval_document
from project_harness.stages import accept_stage, prepare_stage_approval, product_baseline_revision, stage_status
from project_harness.validation import validate_project_directory
from tests.test_engine import load_fixture, prepare_demo
from tests.test_implementation_levels import ACTOR, APPROVED_AT, closed_criteria, complete_prototype, current_gate


class StageApprovalPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._suite_temp = tempfile.TemporaryDirectory()
        data = load_fixture(); data["implementation"]["target_level"] = "PROTOTYPE"
        _, _, root = prepare_demo(Path(cls._suite_temp.name), data=data)
        complete_prototype(root)
        cls.template = root

    @classmethod
    def tearDownClass(cls) -> None:
        cls._suite_temp.cleanup()

    def setUp(self) -> None:
        self._case_temp = tempfile.TemporaryDirectory()
        self.base = Path(self._case_temp.name); self.root = self.base / "project"
        shutil.copytree(self.template, self.root)

    def tearDown(self) -> None:
        self._case_temp.cleanup()

    def _draft(self, name: str = "approval.yaml") -> tuple[Path, dict]:
        output = self.base / name
        result = prepare_stage_approval(self.root, output)
        self.assertEqual(result["status"], "DRAFT_PREPARED")
        return output, load_data(output)["stage_approval"]

    def _snapshot(self) -> dict[str, str]:
        return {p.relative_to(self.root).as_posix(): sha256_file(p) for p in sorted(self.root.rglob("*")) if p.is_file() and not p.is_symlink()}

    def _aux_evidence(self, approval: dict) -> dict[str, str]:
        from tests.gate_proof_fixtures import proof_for_subject
        subjects = [(item["outcome_ref"], "outcome_refs") for item in approval["outcome_results"]]
        subjects += [(item["control_ref"], "profile_control_refs") for item in approval["profile_control_results"]]
        return {subject: proof_for_subject(self.root, subject, "REVIEW_RECORD", mapping=mapping)
                for subject, mapping in subjects}

    def _fill(self, path: Path, approval: dict, decision: str) -> None:
        combined = {x["criterion_ref"]: x for x in closed_criteria(self.root, current_gate(self.root, "PROTOTYPE"))}
        for item in approval["criteria_results"]: item.update(deepcopy(combined[item["criterion_ref"]]))
        for item in approval["hard_constraint_results"]:
            value = deepcopy(combined[item["constraint_ref"]]); value.pop("criterion_ref", None); item.update(value)
        auxiliary = self._aux_evidence(approval)
        for item in approval["outcome_results"] + approval["profile_control_results"]:
            subject = item.get("outcome_ref") or item.get("control_ref")
            item.update({"status": "PASS", "evidence_refs": [auxiliary[subject]], "rationale": "Reviewed against exact current baseline.", "validator": "ACT-VALIDATOR-001"})
        approval.update({"record_state": "APPROVED", "id": decision, "approved": True, "actor": ACTOR, "approved_at": APPROVED_AT,
            "known_limitations": ["Bounded test fixture."], "next_stage_gaps": ["Re-plan from the accepted baseline."], "notes": "Formal approval filled from generated draft."})
        approval["permitted_use"]["status"] = "CONFIRMED"
        document = {"stage_approval": approval}; validate_stage_approval_document(document); write_data(path, document)

    def test_generated_draft_has_exact_contract_and_unknown_results(self) -> None:
        output, approval = self._draft(); status = stage_status(self.root)
        validate_stage_approval_document({"stage_approval": approval})
        self.assertFalse(approval["approved"]); self.assertEqual(approval["record_state"], "DRAFT")
        self.assertIsNone(approval["id"]); self.assertIsNone(approval["actor"]); self.assertIsNone(approval["approved_at"])
        self.assertEqual(approval["stage_plan_ref"], status["stage_plan_ref"]); self.assertEqual(approval["gate_ref"], status["gate_ref"])
        self.assertEqual(approval["gate_digest"], status["gate_digest"]); self.assertEqual(approval["baseline_revision"], product_baseline_revision(self.root))
        self.assertEqual(len(approval["outcome_results"]), status["gate_counts"]["required_outcomes"]["total"])
        self.assertEqual(len(approval["criteria_results"]), status["gate_counts"]["level_criteria"]["total"])
        self.assertEqual(len(approval["hard_constraint_results"]), status["gate_counts"]["hard_constraints"]["total"])
        self.assertEqual(len(approval["profile_control_results"]), status["gate_counts"]["profile_controls"]["total"])
        results = approval["outcome_results"] + approval["criteria_results"] + approval["hard_constraint_results"] + approval["profile_control_results"]
        self.assertTrue(all(x["status"] == "UNKNOWN" and x["evidence_refs"] == [] and x["rationale"] is None and x["validator"] is None for x in results)); self.assertTrue(output.is_file())

    def test_preparation_only_writes_requested_operator_file_and_never_approves(self) -> None:
        before = self._snapshot(); decisions = sorted((self.root / ".harness/canonical/DECISIONS").glob("*.yaml")); reports = sorted((self.root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
        output = self.root / ".harness/operator/APPROVALS/prototype.yaml"
        result = prepare_stage_approval(self.root, output); after = self._snapshot(); expected = dict(before); expected[output.relative_to(self.root).as_posix()] = sha256_file(output)
        self.assertEqual(after, expected); self.assertFalse(result["approved"])
        self.assertEqual(decisions, sorted((self.root / ".harness/canonical/DECISIONS").glob("*.yaml"))); self.assertEqual(reports, sorted((self.root / ".harness/stages/ACCEPTANCE").glob("*.yaml")))
        with self.assertRaises(WaitingDecision): accept_stage(self.root, "PROTOTYPE", output)
        with self.assertRaisesRegex(ValidationFailure, "restricted to .harness/operator/APPROVALS"): prepare_stage_approval(self.root, self.root / "approval.yaml")

    def test_deterministic_force_and_safe_no_overwrite(self) -> None:
        output, _ = self._draft(); first = output.read_bytes()
        with self.assertRaisesRegex(ValidationFailure, "already exists"): prepare_stage_approval(self.root, output)
        prepare_stage_approval(self.root, output, force=True); self.assertEqual(first, output.read_bytes())
        second = self.base / "second.yaml"; prepare_stage_approval(self.root, second); self.assertEqual(first, second.read_bytes())

    def test_product_or_gate_change_updates_new_draft_and_rejects_old_record(self) -> None:
        old_path, old = self._draft("old.yaml")
        old.update({"record_state": "APPROVED", "id": "DEC-STALE-PRODUCT-001", "approved": True, "actor": ACTOR, "approved_at": APPROVED_AT}); write_data(old_path, {"stage_approval": old})
        product = self.root / "src/product-drift.txt"; product.parent.mkdir(parents=True, exist_ok=True); product.write_text("changed\n")
        with self.assertRaisesRegex(ValidationFailure, "stale|exact-bound"): accept_stage(self.root, "PROTOTYPE", old_path)
        new_path, new = self._draft("product-new.yaml"); self.assertNotEqual(old["baseline_revision"], new["baseline_revision"])
        index_path = self.root / ".harness/stages/GATES/INDEX.yaml"; index = load_data(index_path); gate_id = index["stage_gate_index"]["by_level"]["PROTOTYPE"]
        gate = current_gate(self.root, "PROTOTYPE"); revised = deepcopy(gate); revised["previous_revision_ref"] = f"{gate['id']}@{gate['revision']}"; revised["revision"] += 1; revised["updated_at"] = "2026-08-20T13:00:00Z"
        rel = f".harness/stages/GATES/{gate_id}@{revised['revision']}.yaml"; write_data(self.root / rel, {"stage_gate": revised}); index["stage_gate_index"]["current"][gate_id] = rel; write_data(index_path, index)
        new.update({"record_state": "APPROVED", "id": "DEC-STALE-GATE-001", "approved": True, "actor": ACTOR, "approved_at": APPROVED_AT}); write_data(new_path, {"stage_approval": new})
        with self.assertRaisesRegex(ValidationFailure, "stale|exact-bound"): accept_stage(self.root, "PROTOTYPE", new_path)
        _, newest = self._draft("gate-new.yaml"); self.assertNotEqual(new["gate_ref"], newest["gate_ref"]); self.assertNotEqual(new["gate_digest"], newest["gate_digest"])

    def test_filled_generated_record_is_accepted(self) -> None:
        path, approval = self._draft(); decisions = self.root / ".harness/canonical/DECISIONS"; before = list(decisions.glob("*.yaml"))
        self._fill(path, approval, "DEC-PREPARED-STAGE-APPROVAL-001"); result = accept_stage(self.root, "PROTOTYPE", path)
        self.assertIn(result["status"], {"ACCEPTED", "TARGET_LEVEL_REACHED"}); self.assertEqual(result["accepted_levels"], ["PROTOTYPE"])
        self.assertEqual(len(list(decisions.glob("*.yaml"))), len(before) + 1)
        self.assertEqual(validate_project_directory(self.root)["status"], "PASS")

    def test_stage_status_exposes_exact_gate_counts_baseline_and_route(self) -> None:
        status = stage_status(self.root)
        self.assertEqual(status["next_operator_route"]["route"], "PREPARE_STAGE_APPROVAL"); self.assertIn("prepare-stage-approval", status["next_operator_route"]["command"])
        self.assertTrue(status["gate_ref"].endswith(f"@{status['gate_revision']}")); self.assertTrue(status["gate_digest"].startswith("sha256:"))
        self.assertEqual(status["baseline_digest"], product_baseline_revision(self.root)); self.assertGreater(status["gate_counts"]["required_outcomes"]["total"], 0)
        self.assertGreater(status["gate_counts"]["level_criteria"]["total"], 0); self.assertIn("profile_controls", status["gate_counts"])

    def test_public_api_and_cli_write_the_required_output_file(self) -> None:
        api_output = self.base / "api-approval.yaml"
        result = public_prepare_stage_approval(self.root, api_output)
        self.assertEqual(result["baseline_revision"], public_product_baseline_revision(self.root))
        validate_stage_approval_document(load_data(api_output))

        cli_output = self.base / "cli-approval.yaml"
        env = dict(os.environ)
        source_root = Path(__file__).resolve().parents[1] / "src"
        env["PYTHONPATH"] = os.pathsep.join([str(source_root), str(Path(__file__).resolve().parents[1]), env.get("PYTHONPATH", "")])
        completed = subprocess.run(
            [sys.executable, "-m", "project_harness.cli", "prepare-stage-approval", "--project", str(self.root), "--output", str(cli_output)],
            check=False, capture_output=True, text=True, env=env,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "DRAFT_PREPARED")
        self.assertEqual(Path(payload["approval_path"]), cli_output)
        self.assertTrue(cli_output.is_file())
        self.assertEqual(api_output.read_bytes(), cli_output.read_bytes())
        validate_stage_approval_document(load_data(cli_output))

if __name__ == "__main__": unittest.main()

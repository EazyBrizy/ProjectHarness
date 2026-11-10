"""PH-F01: semantically unjustified Gate evidence (intentional RED: PH-F02).

No monkeypatches, no hand-crafted Gate-eligible evidence: exercise the real
ordinary Task -> preparation Task -> PASS verification -> completion path.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from project_harness.evidence import resolve_evidence_artifact
from project_harness.runtime import complete_current, next_task, verify_current
from project_harness.serialization import load_data
from project_harness.stage_gate_lifecycle import missing_gate_evidence_items
from project_harness.stages import _product_baseline_revision, stage_status
from project_harness.validation import validate_project_directory

from tests.ph_f01_fixtures import build_greenfield_mvp
from tests.test_engine import implement_first_task, implement_second_task, write_agent_result

INVALID_NOOP_KINDS = (
    "ARCHITECTURE_RECORD",
    "LIMITATIONS_RECORD",
    "PERMITTED_USE_RECORD",
    "EXTERNAL_EVIDENCE",
)


class PHF01GateSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="ph-f01-gate-")
        cls.base = Path(cls.temp.name)
        cls.template = build_greenfield_mvp(cls.base / "ordinary-tasks")
        implement_first_task(cls.template)
        first = verify_current(cls.template, allow_command_execution=True)
        complete_current(cls.template, write_agent_result(cls.template, first, "Implemented first ordinary Task"))
        implement_second_task(cls.template)
        second = verify_current(cls.template, allow_command_execution=True)
        completed = complete_current(cls.template, write_agent_result(cls.template, second, "Implemented final ordinary Task"))
        if completed.get("stage_gate", {}).get("status") != "STAGE_ACCEPTANCE_PREPARATION":
            raise AssertionError({"fixture": "PREPARATION_READY", "result": completed})

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def _copy(self, name: str) -> Path:
        root = self.base / name
        if root.exists():
            shutil.rmtree(root)
        shutil.copytree(self.template, root)
        return root

    @staticmethod
    def _noop_verified_completion(root: Path) -> tuple[dict, list[dict], str]:
        """No product/README/test files are added or modified in this Task."""
        run = next_task(root)
        assert run["status"] == "READY_FOR_CODEX", run
        task_id = run["task_ref"].split("@", 1)[0]
        task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
        task = load_data(root / task_index["current"][task_id])["task"]
        assert task["stage_acceptance_preparation"]["kind"] == "STAGE_ACCEPTANCE_PREPARATION"
        assert task["verification"]["expected_paths"] == []
        assert task["verification"]["manual_checks"] == []
        assert task["scope"]["write"]

        before_product = _product_baseline_revision(root)
        prior_evidence = {p.name for p in (root / ".harness/evidence").glob("*.yaml")}
        verification = verify_current(root, allow_command_execution=True)
        assert verification["status"] == "PASS", verification
        # Write ONLY the ordinary required Agent Task Result under .harness.
        completed = complete_current(root, write_agent_result(root, verification, "No source changes; generic verification passed."))
        after_product = _product_baseline_revision(root)
        assert before_product == after_product, (before_product, after_product)
        created = [
            load_data(path)["verification_evidence"]
            for path in sorted((root / ".harness/evidence").glob("*.yaml"))
            if path.name not in prior_evidence
        ]
        manufactured = [
            ev for ev in created
            if ev.get("provenance", {}).get("source_type") == "STAGE_ACCEPTANCE_PREPARATION_VERIFICATION"
        ]
        return completed, manufactured, verification["status"]

    def test_01_preparation_fixture_has_all_four_mandatory_proof_kinds(self) -> None:
        """GREEN fixture preconditions, independent of PH-F02's later fix."""
        root = self._copy("preparation-contract-preconditions")
        baseline_before = _product_baseline_revision(root)
        missing = missing_gate_evidence_items(root)["missing_items"]
        selected = {item["selected_evidence_kind"] for item in missing}
        for kind in INVALID_NOOP_KINDS:
            with self.subTest(kind=kind):
                self.assertIn(kind, selected, "Fixture must exercise the actual mandatory Gate kind")
        current = next_task(root)
        self.assertEqual(current["status"], "READY_FOR_CODEX")
        self.assertEqual(stage_status(root)["active_stage"], "PROTOTYPE")
        self.assertEqual(_product_baseline_revision(root), baseline_before)
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_ph_f02_noop_pass_cannot_fabricate_semantically_unverified_kinds(self) -> None:
        root = self._copy("no-op-must-not-fabricate")
        completed, manufactured, status = self._noop_verified_completion(root)
        self.assertEqual(status, "PASS")
        # Formal digest/source/subject compatibility currently passes for all
        # produced EVDs, but it does NOT mean their semantics were examined.
        kinds = {record["kind"] for record in manufactured if record["status"] == "PASS"}
        for kind in INVALID_NOOP_KINDS:
            with self.subTest(kind=kind):
                self.assertNotIn(
                    kind,
                    kinds,
                    f"PH-F02: no-change PASS verification cannot certify {kind} without a subject-specific source",
                )

    def test_ph_f02_noop_pass_keeps_gate_unclosed_without_subject_proofs(self) -> None:
        root = self._copy("no-op-gate-must-remain-open")
        completed, manufactured, status = self._noop_verified_completion(root)
        self.assertEqual(status, "PASS")
        self.assertEqual(manufactured, [], "Generic PASS cannot mint any subject-specific evidence")
        # No independent architecture, limitations, permitted-use or external
        # artifacts were supplied by the preparation Task. Do not mark the
        # mandatory Gate as VERIFYING from an unqualified generic report.
        self.assertNotEqual(
            completed["stage_gate"]["status"],
            "VERIFYING",
            "PH-F02: semantically unresolved subjects must remain UNKNOWN/BLOCKED",
        )


if __name__ == "__main__":
    unittest.main()

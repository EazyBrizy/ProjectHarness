from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from project_harness.hashing import sha256_file
from project_harness.runtime import project_status
from project_harness.serialization import load_data, write_data
from project_harness.stages import (
    accept_stage,
    assess_maturity,
    level_up,
    load_current_target_level,
    load_stage_state,
    stage_status,
)
from project_harness.validation import validate_project_directory

from tests.test_engine import load_fixture, prepare_demo
from tests.test_implementation_levels import complete_prototype, stage_approval, write_approval


APPROVED_AT = "2026-08-18T12:00:00Z"
ACTOR = "ACT-STAGE-APPROVER-001"


class CanonicalCurrentTargetTests(unittest.TestCase):
    """L-01 regressions: one canonical current-cycle target after level-up."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._workspace = tempfile.TemporaryDirectory()
        cls.workspace = Path(cls._workspace.name)

        data = load_fixture()
        data["implementation"]["target_level"] = "PROTOTYPE"
        _, _, cls.initial_template = prepare_demo(cls.workspace / "initial-build", data=data)

        cls.accepted_template = cls.workspace / "accepted-template"
        shutil.copytree(cls.initial_template, cls.accepted_template)
        complete_prototype(cls.accepted_template)
        approval = stage_approval(
            cls.accepted_template,
            "PROTOTYPE",
            decision_suffix="CANONICAL-TARGET-BASE-001",
        )
        result = accept_stage(
            cls.accepted_template,
            "PROTOTYPE",
            write_approval(cls.workspace, "prototype-approval.yaml", approval),
        )
        if result.get("status") != "TARGET_LEVEL_REACHED":
            raise AssertionError(result)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._workspace.cleanup()

    @classmethod
    def _copy_case(cls, source: Path, name: str) -> Path:
        base = cls.workspace / f"case-{name}"
        root = base / "project"
        if base.exists():
            shutil.rmtree(base)
        base.mkdir(parents=True)
        shutil.copytree(source, root)
        return root

    @classmethod
    def _level_up_to_mvp(cls, root: Path, suffix: str) -> dict:
        approval = {
            "level_up_approval": {
                "id": f"DEC-HARNESS-DEMO-LEVEL-UP-L01-{suffix}",
                "approved": True,
                "actor": ACTOR,
                "approved_at": APPROVED_AT,
                "target_level": "MVP",
                "rationale": "Governed L-01 regression transition from accepted PROTOTYPE to MVP.",
            }
        }
        approval_path = write_approval(root.parent, f"level-up-{suffix}.yaml", approval)
        return level_up(root, "MVP", approval_path)

    def test_01_initial_prepared_project_has_one_target_in_all_current_projections(self) -> None:
        root = self._copy_case(self.initial_template, "initial-projections")
        stage_target = load_stage_state(root)["target_level"]
        project_target = load_data(root / ".harness/config/PROJECT.yaml")["project"]["target_implementation_level"]
        current_target = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]["target_implementation_level"]
        initial_target = load_data(root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml")["implementation"]["target_level"]

        self.assertEqual(stage_target, "PROTOTYPE")
        self.assertEqual(project_target, stage_target)
        self.assertEqual(current_target, stage_target)
        self.assertEqual(initial_target, stage_target)
        self.assertEqual(load_current_target_level(root), stage_target)
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_02_level_up_syncs_current_projections_and_preserves_initial_accepted_target(self) -> None:
        root = self._copy_case(self.accepted_template, "level-up-projections")
        accepted_path = root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml"
        accepted_digest = sha256_file(accepted_path)

        result = self._level_up_to_mvp(root, "PROJECTIONS-001")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["target_level"], "MVP")

        stage_target = load_stage_state(root)["target_level"]
        project_target = load_data(root / ".harness/config/PROJECT.yaml")["project"]["target_implementation_level"]
        current_target = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]["target_implementation_level"]
        accepted_target = load_data(accepted_path)["implementation"]["target_level"]

        self.assertEqual(stage_target, "MVP")
        self.assertEqual(project_target, "MVP")
        self.assertEqual(current_target, "MVP")
        self.assertEqual(accepted_target, "PROTOTYPE")
        self.assertEqual(sha256_file(accepted_path), accepted_digest)
        self.assertEqual(load_current_target_level(root), "MVP")

        level_up_journals = [
            load_data(path)["stage_transaction"]
            for path in (root / ".harness/stages/TRANSACTIONS").glob("*/TRANSACTION.yaml")
            if load_data(path)["stage_transaction"].get("operation_kind") == "LEVEL_UP"
        ]
        self.assertEqual(len(level_up_journals), 1)
        transaction_targets = {entry["target"] for entry in level_up_journals[0]["entries"]}
        self.assertTrue(
            {
                ".harness/stages/STAGE_STATE.yaml",
                ".harness/config/PROJECT.yaml",
                ".harness/state/CURRENT_STATE.yaml",
            }.issubset(transaction_targets)
        )

        self.assertEqual(project_status(root)["implementation"]["target_level"], "MVP")
        self.assertEqual(stage_status(root)["target_level"], "MVP")
        self.assertIn("- Target Level: `MVP`", (root / "STATUS.md").read_text(encoding="utf-8"))
        self.assertIn("- Target Level: `MVP`", (root / "ROADMAP.md").read_text(encoding="utf-8"))
        project_md = (root / "PROJECT.md").read_text(encoding="utf-8")
        self.assertIn("- Current Target Level: `MVP`", project_md)
        self.assertIn("- Initial Accepted Target Level: `PROTOTYPE`", project_md)
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_03_prepared_assessment_after_level_up_routes_against_mvp(self) -> None:
        root = self._copy_case(self.accepted_template, "assessment-after-level-up")
        self._level_up_to_mvp(root, "ASSESSMENT-001")

        result = assess_maturity(root)
        self.assertEqual(result["target_level"], "MVP")
        self.assertNotEqual(result["recommended_route"], "TARGET_ALREADY_REACHED")

        assessment = load_data(Path(result["assessment_path"]))["maturity_assessment"]
        self.assertEqual(assessment["target_level"], "MVP")
        self.assertEqual(assessment["previous_highest_accepted_level"], "PROTOTYPE")
        self.assertNotEqual(assessment["recommended_route"], "TARGET_ALREADY_REACHED")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_04_validate_project_rejects_project_and_current_state_target_divergence(self) -> None:
        for projection, relative, envelope in (
            ("PROJECT", ".harness/config/PROJECT.yaml", "project"),
            ("CURRENT_STATE", ".harness/state/CURRENT_STATE.yaml", "state"),
        ):
            with self.subTest(projection=projection):
                root = self._copy_case(self.accepted_template, f"divergence-{projection.lower()}")
                self._level_up_to_mvp(root, f"DIVERGENCE-{projection}-001")
                path = root / relative
                document = load_data(path)
                document[envelope]["target_implementation_level"] = "BETA"
                write_data(path, document)

                validation = validate_project_directory(root)
                self.assertEqual(validation["status"], "FAIL")
                rendered = json.dumps(validation, ensure_ascii=False)
                self.assertIn(f"{projection}.target_implementation_level differs", rendered)

    def test_05_external_intake_assessment_reads_current_project_input_target(self) -> None:
        workspace = self.workspace / "external-intake"
        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True)
        repository = workspace / "repository"
        repository.mkdir()
        (repository / "README.md").write_text("# Existing project\n", encoding="utf-8")
        (repository / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

        project_input = load_fixture()
        project_input["project"]["mode"] = "BROWNFIELD"
        project_input["implementation"]["target_level"] = "BETA"
        project_input["implementation"]["claimed_current_level"] = "UNKNOWN"
        write_data(workspace / "PROJECT_INPUT.yaml", project_input)
        write_data(
            workspace / "REPOSITORY_INVENTORY.yaml",
            {
                "repository_inventory": {
                    "repository_path": str(repository),
                    "repository_revision": "tree:external-intake-l01",
                    "tree_digest": "external-intake-l01",
                    "build_markers": [],
                    "test_paths": [],
                    "documentation_paths": ["README.md"],
                }
            },
        )
        write_data(workspace / "STATE.yaml", {"state": {"effective_repository_path": str(repository)}})

        # A non-canonical historical-looking file must not override external intake.
        historical = deepcopy(project_input)
        historical["implementation"]["target_level"] = "PROTOTYPE"
        write_data(workspace / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml", historical)

        self.assertEqual(load_current_target_level(workspace), "BETA")
        result = assess_maturity(workspace)
        self.assertEqual(result["target_level"], "BETA")
        self.assertEqual(load_data(workspace / "MATURITY_ASSESSMENT.yaml")["maturity_assessment"]["target_level"], "BETA")


if __name__ == "__main__":
    unittest.main()

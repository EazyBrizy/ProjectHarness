"""PH-F01: boundary reachability contract (intentionally RED until PH-F03).

These tests use the real v0.5.0 public operations and assert actual persisted
state, API results, CLI exit codes, and first-JIT continuation. The supported
review-record format is completed by PH-F03; only current public contracts are
used for fixture construction.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from project_harness.hashing import sha256_file
from project_harness.resources import distribution_root
from project_harness.runtime import next_task, project_status
from project_harness.serialization import load_data
from project_harness.stages import level_up, stage_status
from project_harness.validation import validate_project_directory

from tests.ph_f01_fixtures import (
    build_accepted_prototype,
    build_brownfield,
    build_greenfield_mvp,
    build_target_reached_mvp,
    contracts,
    input_document,
)
from tests.test_implementation_levels import ACTOR, APPROVED_AT, write_approval

ENGINE = distribution_root()


def cli(*args: str) -> tuple[int, dict | None, str]:
    """Invoke bundled public CLI in a distinct interpreter, inspect real exit/status."""
    completed = subprocess.run(
        [sys.executable, str(ENGINE / "project-harness.py"), *args],
        cwd=ENGINE,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except (ValueError, TypeError):
        payload = None
    return completed.returncode, payload, completed.stderr


class PHF01FixtureAndPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="ph-f01-planner-")
        cls.base = Path(cls.temp.name)
        cls.greenfield = build_greenfield_mvp(cls.base / "greenfield")
        cls.brownfield = build_brownfield(cls.base / "brownfield")
        cls.accepted_prototype = build_accepted_prototype(cls.base / "accepted-prototype")
        cls.target_reached = build_target_reached_mvp(cls.base / "target-reached")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def _copy(self, template: Path, name: str) -> Path:
        dest = self.base / f"case-{name}"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(template, dest)
        return dest

    def test_01_greenfield_and_brownfield_fixture_independence_and_statuses(self) -> None:
        spec = contracts()["fixture_scenarios"]
        self.assertEqual(input_document("greenfield_mvp_project_input.json")["implementation"]["target_level"], "MVP")
        self.assertEqual(input_document("brownfield_project_input.json")["project"]["mode"], "BROWNFIELD")
        self.assertNotEqual(
            input_document("greenfield_mvp_project_input.json")["project"]["slug"],
            input_document("brownfield_project_input.json")["project"]["slug"],
        )
        for key, root in (("GREENFIELD_MVP", self.greenfield), ("BROWNFIELD", self.brownfield)):
            with self.subTest(key=key):
                actual = stage_status(root)
                self.assertEqual(actual["target_level"], spec[key]["target_level"])
                self.assertEqual(actual["highest_accepted_level"], "NONE")
                self.assertEqual(actual["active_stage"], "PROTOTYPE")
                self.assertEqual(validate_project_directory(root)["status"], "PASS")
                cli_code, cli_value, cli_error = cli("stage-status", "--project", str(root))
                self.assertEqual(cli_code, 0, cli_error)
                self.assertEqual(cli_value["target_level"], actual["target_level"])

        stages = stage_status(self.greenfield)["stages"]
        self.assertEqual([item["level"] for item in stages], ["PROTOTYPE", "ALPHA", "BETA", "MVP"])
        self.assertEqual([item["detailed_work_package_count"] for item in stages[1:]], [0, 0, 0])
        self.assertEqual(stage_status(self.brownfield)["claimed_current_level"], "UNKNOWN")

    def test_02_accepted_prototype_fixture_exposes_real_planning_boundary(self) -> None:
        root = self._copy(self.accepted_prototype, "accepted-prototype-boundary")
        self._assert_current_missing_planner_boundary(root, "PROTOTYPE", "ALPHA", "MVP")

    def test_03_mvp_target_reached_fixture_then_governed_level_up_to_release(self) -> None:
        root = self._copy(self.target_reached, "mvp-level-up-boundary")
        baseline = stage_status(root)
        self.assertEqual(baseline["target_level"], "MVP")
        self.assertEqual(baseline["highest_accepted_level"], "MVP")
        self.assertEqual(baseline["status"], "TARGET_LEVEL_REACHED")
        self.assertEqual(next_task(root)["status"], "TARGET_LEVEL_REACHED")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")
        self._apply_release_level_up(root)
        self._assert_current_missing_planner_boundary(root, "MVP", "RELEASE", "RELEASE")

    def _apply_release_level_up(self, root: Path) -> None:
        old_input_digest = sha256_file(root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml")
        acceptance_digests = {
            file.name: sha256_file(file)
            for file in (root / ".harness/stages/ACCEPTANCE").glob("*.yaml")
        }
        self.assertEqual(len(acceptance_digests), 4)
        approval = {"level_up_approval": {
            "id": "DEC-PH-F01-LEVEL-UP-MVP-RELEASE-001",
            "approved": True, "actor": ACTOR, "approved_at": APPROVED_AT,
            "target_level": "RELEASE",
            "rationale": "Advance only from formally accepted MVP to the next RELEASE Stage.",
        }}
        record = write_approval(self.base, "ph-f01-release-approval.yaml", approval)
        code, output, stderr = cli(
            "level-up", "--project", str(root), "--target", "RELEASE", "--approval", str(record)
        )
        self.assertEqual(code, 0, stderr)
        self.assertEqual(output["status"], "ACTIVE")
        self.assertEqual(output["active_stage"], "RELEASE")
        self.assertEqual(output["highest_accepted_level"], "MVP")
        self.assertEqual(sha256_file(root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml"), old_input_digest)
        self.assertEqual(
            {file.name: sha256_file(file) for file in (root / ".harness/stages/ACCEPTANCE").glob("*.yaml")},
            acceptance_digests,
        )
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def _assert_current_missing_planner_boundary(self, root: Path, accepted: str, next_stage: str, target: str) -> None:
        """Baseline observation is PASS: confirm defect, not repair its semantics."""
        status = stage_status(root)
        nxt = next_task(root)
        self.assertEqual(status["highest_accepted_level"], accepted)
        self.assertEqual(status["active_stage"], next_stage)
        self.assertEqual(status["target_level"], target)
        self.assertEqual(status["next_route"], "PLAN_ACTIVE_STAGE")
        self.assertEqual(status["stage_plan_status"], "ACTIVE")
        self.assertEqual(status["stages"][next(i for i, s in enumerate(status["stages"]) if s["level"] == next_stage)]["detailed_work_package_count"], 0)
        self.assertEqual(nxt["status"], "STAGE_PLANNING_REQUIRED")
        self.assertEqual(nxt["next_route"], "PLAN_ACTIVE_STAGE")
        self.assertIsNone(project_status(root)["current_task"])
        for operation in ("stage-status", "next"):
            code, payload, stderr = cli(operation, "--project", str(root))
            self.assertEqual(code, 0, stderr)
            self.assertEqual(payload["active_stage"], next_stage)
            self.assertEqual(payload["next_route"], "PLAN_ACTIVE_STAGE")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def _assert_first_jit_via_governed_cli(self, root: Path, level: str) -> None:
        """PH-F03 acceptance contract: read-only draft then governed application.

        The reviewed-record shape is not yet defined in PH-F01. PH-F03 will
        supply the exact-bound review adapter once its public schema is defined.
        For the current build, draft CLI absence is the first intentional RED.
        """
        draft = self.base / f"ph-f01-{level.lower()}-draft.yaml"
        code, payload, stderr = cli(
            "prepare-active-stage-plan", "--project", str(root), "--output", str(draft)
        )
        self.assertEqual(code, 0, f"PH-F03 missing public preparation route: {stderr}")
        self.assertTrue(draft.is_file(), "PH-F03 preparation must create an exact-bound draft")
        self.assertIn(payload["status"], {"DRAFT_PREPARED", "READY_FOR_REVIEW"})
        # The reviewed form remains a separate governed operation: preparing
        # a draft must not silently activate tasks.
        self.assertEqual(next_task(root)["status"], "STAGE_PLANNING_REQUIRED")
        code, payload, stderr = cli("plan-active-stage", "--project", str(root), "--plan", str(draft))
        self.assertEqual(code, 0, f"PH-F03 missing governed application route: {stderr}")
        first = next_task(root)
        self.assertEqual(first["status"], "READY_FOR_CODEX")
        self.assertEqual(stage_status(root)["active_stage"], level)
        self.assertEqual(project_status(root)["current_task"]["implementation_stage"], level)
        self.assertEqual(first["implementation_stage"], level)

    def test_ph_f03_accept_prototype_to_first_alpha_ready_jit(self) -> None:
        root = self._copy(self.accepted_prototype, "alpha-first-ready")
        self._assert_current_missing_planner_boundary(root, "PROTOTYPE", "ALPHA", "MVP")
        self._assert_first_jit_via_governed_cli(root, "ALPHA")

    def test_ph_f03_level_up_mvp_to_first_release_ready_jit(self) -> None:
        root = self._copy(self.target_reached, "release-first-ready")
        self._apply_release_level_up(root)
        self._assert_current_missing_planner_boundary(root, "MVP", "RELEASE", "RELEASE")
        self._assert_first_jit_via_governed_cli(root, "RELEASE")

    def test_ph_f03_route_is_actionable_in_public_status_api(self) -> None:
        root = self._copy(self.accepted_prototype, "alpha-operator-route")
        status = stage_status(root)
        self.assertEqual(status["next_route"], "PLAN_ACTIVE_STAGE")
        command = status["next_operator_route"]["command"]
        self.assertIsInstance(command, str, "PH-F03/PH-F04 must expose an executable planner command")
        self.assertIn("prepare-active-stage-plan", command)


if __name__ == "__main__":
    unittest.main()

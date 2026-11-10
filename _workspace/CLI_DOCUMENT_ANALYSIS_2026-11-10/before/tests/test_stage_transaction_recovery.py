from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.serialization import load_data, write_data
from project_harness.stage_transactions import recover_stage_transactions
from project_harness.stages import accept_stage, level_up, load_stage_state
from project_harness.validation import validate_project_directory

from tests.test_engine import load_fixture, prepare_demo
from tests.test_implementation_levels import complete_prototype, stage_approval, write_approval


class SimulatedProcessCrash(BaseException):
    """Bypass ordinary exception reconciliation to model abrupt process loss."""


def _digest(path: Path) -> str:
    return f"sha256:{sha256_file(path)}"


class StageTransactionRecoveryTests(unittest.TestCase):
    """Crash-consistency proofs for the local Stage transaction boundary."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._workspace = tempfile.TemporaryDirectory()
        cls.workspace = Path(cls._workspace.name)
        data = load_fixture()
        data["implementation"]["target_level"] = "PROTOTYPE"
        _, _, cls.template_root = prepare_demo(cls.workspace / "template-build", data=data)
        complete_prototype(cls.template_root)

        probe_root, probe_approval = cls._fresh_case("PROBE")
        probe_result = accept_stage(probe_root, "PROTOTYPE", probe_approval)
        if probe_result["transaction_status"] != "COMMITTED":
            raise AssertionError(probe_result)
        probe_journal = cls._only_journal(probe_root)
        cls.accepted_template_root = probe_root
        cls.apply_point_count = len(probe_journal["entries"])
        if cls.apply_point_count < 2:
            raise AssertionError("accept-stage fault matrix requires a multi-file write set")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._workspace.cleanup()

    @classmethod
    def _fresh_case(cls, suffix: str) -> tuple[Path, Path]:
        case_base = cls.workspace / f"case-{suffix}"
        root = case_base / "project"
        if case_base.exists():
            shutil.rmtree(case_base)
        case_base.mkdir(parents=True)
        shutil.copytree(cls.template_root, root)
        approval = stage_approval(root, "PROTOTYPE", decision_suffix=f"TX-{suffix}")
        approval_path = write_approval(case_base, "stage-approval.yaml", approval)
        return root, approval_path

    @classmethod
    def _fresh_level_up_case(cls, suffix: str) -> tuple[Path, Path]:
        case_base = cls.workspace / f"case-{suffix}"
        root = case_base / "project"
        if case_base.exists():
            shutil.rmtree(case_base)
        case_base.mkdir(parents=True)
        shutil.copytree(cls.accepted_template_root, root)
        approval = {
            "level_up_approval": {
                "id": f"DEC-HARNESS-DEMO-LEVEL-UP-TX-{suffix}",
                "approved": True,
                "actor": "ACT-STAGE-APPROVER-001",
                "approved_at": "2026-08-18T12:00:00Z",
                "target_level": "MVP",
                "rationale": "Fault-injection fixture for a governed level-up transition.",
            }
        }
        return root, write_approval(case_base, "level-up-approval.yaml", approval)

    @staticmethod
    def _journals(root: Path) -> list[dict]:
        paths = sorted((root / ".harness/stages/TRANSACTIONS").glob("*/TRANSACTION.yaml"))
        journals = [load_data(path)["stage_transaction"] for path in paths]
        # The governed Gate-readiness lifecycle now has its own committed
        # PREPARE/RESUME transactions.  This fault matrix concerns only the
        # ACCEPT_STAGE and LEVEL_UP transaction boundaries it was designed for.
        return [item for item in journals if item.get("operation_kind") in {"ACCEPT_STAGE", "LEVEL_UP"}]

    @classmethod
    def _only_journal(cls, root: Path) -> dict:
        journals = cls._journals(root)
        if len(journals) != 1:
            raise AssertionError(f"expected one journal, got {len(journals)}")
        return journals[0]

    @classmethod
    def _latest_journal(cls, root: Path) -> dict:
        journals = cls._journals(root)
        if not journals:
            raise AssertionError("expected at least one journal")
        return max(journals, key=lambda item: int(item["sequence"]))

    @staticmethod
    def _semantic_snapshot(root: Path) -> dict:
        stage_state_path = root / ".harness/stages/STAGE_STATE.yaml"
        current_state_path = root / ".harness/state/CURRENT_STATE.yaml"
        next_task_path = root / ".harness/state/NEXT_TASK.yaml"
        return {
            "stage_state_digest": _digest(stage_state_path),
            "current_state_digest": _digest(current_state_path),
            "next_task_digest": _digest(next_task_path),
            "stage_state": deepcopy(load_data(stage_state_path)["implementation"]),
            "current_state": deepcopy(load_data(current_state_path)["state"]),
            "next_task": deepcopy(load_data(next_task_path)["next_task"]),
            "acceptance_paths": sorted(
                path.relative_to(root).as_posix()
                for path in (root / ".harness/stages/ACCEPTANCE").glob("*.yaml")
            ),
        }

    @staticmethod
    def _assert_terminal_write_set(test: unittest.TestCase, root: Path, journal: dict, terminal: str) -> None:
        observed_states: list[str] = []
        for entry in journal["entries"]:
            target = root / entry["target"]
            if terminal == "NEW":
                test.assertTrue(target.is_file(), entry["target"])
                test.assertEqual(_digest(target), entry["expected_new_digest"], entry["target"])
                observed_states.append("NEW")
            elif entry["existed_before"]:
                test.assertTrue(target.is_file(), entry["target"])
                test.assertEqual(_digest(target), entry["old_digest"], entry["target"])
                observed_states.append("OLD")
            else:
                test.assertFalse(target.exists(), entry["target"])
                observed_states.append("OLD")
        test.assertEqual(set(observed_states), {terminal})

    @classmethod
    def _assert_old(cls, test: unittest.TestCase, root: Path, before: dict, journal: dict | None = None) -> None:
        after = cls._semantic_snapshot(root)
        test.assertEqual(after, before)
        if journal is not None:
            test.assertEqual(journal["status"], "ROLLED_BACK")
            cls._assert_terminal_write_set(test, root, journal, "OLD")
            test.assertTrue(all(entry["recovery_state"] == "VERIFIED" for entry in journal["entries"]))

    @classmethod
    def _assert_new(cls, test: unittest.TestCase, root: Path, journal: dict) -> None:
        test.assertEqual(journal["status"], "COMMITTED")
        cls._assert_terminal_write_set(test, root, journal, "NEW")
        test.assertTrue(all(entry["apply_state"] == "VERIFIED" for entry in journal["entries"]))
        state = load_stage_state(root)
        test.assertEqual(state["highest_accepted_level"], "PROTOTYPE")
        test.assertEqual(state["active_stage"], "PROTOTYPE")
        current = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
        test.assertEqual(current["project_status"], "TARGET_LEVEL_REACHED")
        test.assertEqual(current["next_route"], "TARGET_ALREADY_REACHED")
        next_task = load_data(root / ".harness/state/NEXT_TASK.yaml")["next_task"]
        test.assertEqual(next_task["status"], "TARGET_LEVEL_REACHED")
        acceptances = list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
        test.assertEqual(len(acceptances), 1)
        test.assertEqual(load_data(acceptances[0])["stage_acceptance"]["status"], "PASS")

    def test_01_controlled_failure_at_every_apply_point_restores_full_old_state(self) -> None:
        real_replace = os.replace
        for point in range(1, self.apply_point_count + 1):
            with self.subTest(apply_point=point):
                root, approval_path = self._fresh_case(f"APPLY-ERROR-{point:02d}")
                before = self._semantic_snapshot(root)
                counter = {"value": 0}

                def fail_before_point(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
                    source = Path(src)
                    destination = Path(dst)
                    is_apply = source.name.startswith("staged-") and "TRANSACTIONS" not in destination.parts
                    if is_apply:
                        counter["value"] += 1
                        if counter["value"] == point:
                            raise OSError(f"injected apply failure {point}")
                    real_replace(src, dst)

                with mock.patch("project_harness.stages.os.replace", side_effect=fail_before_point):
                    with self.assertRaisesRegex(OSError, f"apply failure {point}"):
                        accept_stage(root, "PROTOTYPE", approval_path)
                self.assertEqual(counter["value"], point)
                journal = self._only_journal(root)
                self._assert_old(self, root, before, journal)
                self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_02_abrupt_crash_after_every_apply_point_recovers_only_old_or_new(self) -> None:
        real_replace = os.replace
        for point in range(1, self.apply_point_count + 1):
            with self.subTest(apply_point=point):
                root, approval_path = self._fresh_case(f"APPLY-CRASH-{point:02d}")
                before = self._semantic_snapshot(root)
                counter = {"value": 0}

                def crash_after_point(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
                    source = Path(src)
                    destination = Path(dst)
                    is_apply = source.name.startswith("staged-") and "TRANSACTIONS" not in destination.parts
                    if is_apply:
                        counter["value"] += 1
                    real_replace(src, dst)
                    if is_apply and counter["value"] == point:
                        raise SimulatedProcessCrash(f"crash after apply {point}")

                with mock.patch("project_harness.stages.os.replace", side_effect=crash_after_point):
                    with self.assertRaises(SimulatedProcessCrash):
                        accept_stage(root, "PROTOTYPE", approval_path)
                intermediate = self._only_journal(root)
                self.assertIn(intermediate["status"], {"APPLYING", "PREPARED"})

                validation = validate_project_directory(root)
                self.assertEqual(validation["status"], "PASS", validation)
                journal = self._only_journal(root)
                if point == self.apply_point_count:
                    self._assert_new(self, root, journal)
                else:
                    self._assert_old(self, root, before, journal)

    def test_03_prepared_journal_write_failure_changes_no_canonical_state(self) -> None:
        root, approval_path = self._fresh_case("PREPARED-WRITE-ERROR")
        before = self._semantic_snapshot(root)
        from project_harness import stage_transactions as tx

        original = tx._persist_journal
        fired = {"value": False}

        def fail_prepared(project_root: Path, journal: dict) -> None:
            if journal.get("status") == "PREPARED" and not fired["value"]:
                fired["value"] = True
                raise OSError("injected PREPARED journal write failure")
            original(project_root, journal)

        with mock.patch("project_harness.stage_transactions._persist_journal", side_effect=fail_prepared):
            with self.assertRaisesRegex(OSError, "PREPARED journal"):
                accept_stage(root, "PROTOTYPE", approval_path)
        self.assertTrue(fired["value"])
        self._assert_old(self, root, before)
        self.assertEqual(self._journals(root), [])
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_04_durable_prepared_crash_before_replacements_is_recovered_idempotently(self) -> None:
        root, approval_path = self._fresh_case("PREPARED-CRASH")
        before = self._semantic_snapshot(root)
        from project_harness import stage_transactions as tx

        original = tx._persist_journal
        fired = {"value": False}

        def crash_after_prepared(project_root: Path, journal: dict) -> None:
            original(project_root, journal)
            if journal.get("status") == "PREPARED" and not fired["value"]:
                fired["value"] = True
                raise SimulatedProcessCrash("crash after durable PREPARED")

        with mock.patch("project_harness.stage_transactions._persist_journal", side_effect=crash_after_prepared):
            with self.assertRaises(SimulatedProcessCrash):
                accept_stage(root, "PROTOTYPE", approval_path)
        journal = self._only_journal(root)
        self.assertEqual(journal["status"], "PREPARED")

        first = recover_stage_transactions(root)
        self.assertEqual(first["recovered"][0]["status"], "ROLLED_BACK")
        second = recover_stage_transactions(root)
        self.assertEqual(second["recovered"], [])
        journal = self._only_journal(root)
        self._assert_old(self, root, before, journal)
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_05_per_entry_state_write_failure_rolls_back_verified_old_state(self) -> None:
        from project_harness import stage_transactions as tx

        with self.subTest(phase="APPLYING"):
            root, approval_path = self._fresh_case("ENTRY-STATE-ERROR")
            before = self._semantic_snapshot(root)
            original = tx._persist_journal
            fired = {"value": False}

            def fail_first_applied_state(project_root: Path, journal: dict) -> None:
                if (
                    journal.get("status") == "APPLYING"
                    and any(entry.get("apply_state") == "APPLIED" for entry in journal.get("entries", []))
                    and not fired["value"]
                ):
                    fired["value"] = True
                    raise OSError("injected per-entry state write failure")
                original(project_root, journal)

            with mock.patch("project_harness.stage_transactions._persist_journal", side_effect=fail_first_applied_state):
                with self.assertRaisesRegex(OSError, "per-entry state"):
                    accept_stage(root, "PROTOTYPE", approval_path)
            self.assertTrue(fired["value"])
            journal = self._only_journal(root)
            self._assert_old(self, root, before, journal)
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

        with self.subTest(phase="ROLLING_BACK"):
            root, approval_path = self._fresh_case("RECOVERY-ENTRY-STATE-ERROR")
            before = self._semantic_snapshot(root)
            original = tx._persist_journal
            real_replace = os.replace
            apply_fired = {"value": False}
            progress_fired = {"value": False}

            def fail_apply_once(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
                source = Path(src)
                destination = Path(dst)
                is_apply = source.name.startswith("staged-") and "TRANSACTIONS" not in destination.parts
                if is_apply and not apply_fired["value"]:
                    apply_fired["value"] = True
                    raise OSError("injected apply error to enter rollback")
                real_replace(src, dst)

            def fail_first_recovery_progress(project_root: Path, journal: dict) -> None:
                has_progress = any(
                    entry.get("recovery_state") in {"RESTORED", "REMOVED"}
                    for entry in journal.get("entries", [])
                )
                if journal.get("status") == "ROLLING_BACK" and has_progress and not progress_fired["value"]:
                    progress_fired["value"] = True
                    raise OSError("injected recovery per-entry state write failure")
                original(project_root, journal)

            with mock.patch("project_harness.stages.os.replace", side_effect=fail_apply_once):
                with mock.patch(
                    "project_harness.stage_transactions._persist_journal",
                    side_effect=fail_first_recovery_progress,
                ):
                    with self.assertRaisesRegex(OSError, "enter rollback"):
                        accept_stage(root, "PROTOTYPE", approval_path)
            self.assertTrue(apply_fired["value"])
            self.assertTrue(progress_fired["value"])
            journal = self._only_journal(root)
            self._assert_old(self, root, before, journal)
            self.assertTrue(journal.get("recovery_progress_warnings"))
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_06_one_shot_final_committed_marker_failure_returns_committed_success(self) -> None:
        root, approval_path = self._fresh_case("COMMIT-MARKER-ONCE")
        from project_harness import stage_transactions as tx

        original = tx._persist_journal
        fired = {"value": False}

        def fail_commit_once(project_root: Path, journal: dict) -> None:
            if journal.get("status") == "COMMITTED" and not fired["value"]:
                fired["value"] = True
                raise OSError("injected final COMMITTED journal failure")
            original(project_root, journal)

        with mock.patch("project_harness.stage_transactions._persist_journal", side_effect=fail_commit_once):
            result = accept_stage(root, "PROTOTYPE", approval_path)
        self.assertTrue(fired["value"])
        self.assertEqual(result["transaction_status"], "COMMITTED")
        self.assertTrue(any(item.get("code") == "STAGE_TRANSACTION_COMMIT_RECOVERED" for item in result.get("warnings", [])))
        journal = self._only_journal(root)
        self._assert_new(self, root, journal)
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_07_persistent_commit_marker_failure_reports_error_only_after_full_rollback(self) -> None:
        root, approval_path = self._fresh_case("COMMIT-MARKER-PERSISTENT")
        before = self._semantic_snapshot(root)
        from project_harness import stage_transactions as tx

        original = tx._persist_journal

        def fail_every_commit(project_root: Path, journal: dict) -> None:
            if journal.get("status") == "COMMITTED":
                raise OSError("persistent COMMITTED journal failure")
            original(project_root, journal)

        with mock.patch("project_harness.stage_transactions._persist_journal", side_effect=fail_every_commit):
            with self.assertRaisesRegex(OSError, "persistent COMMITTED"):
                accept_stage(root, "PROTOTYPE", approval_path)
        journal = self._only_journal(root)
        self._assert_old(self, root, before, journal)
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_08_crash_with_all_replacements_and_no_commit_marker_recovers_commit(self) -> None:
        root, approval_path = self._fresh_case("COMMIT-MARKER-CRASH")
        from project_harness import stage_transactions as tx

        original = tx._persist_journal
        fired = {"value": False}

        def crash_before_commit_marker(project_root: Path, journal: dict) -> None:
            if journal.get("status") == "COMMITTED" and not fired["value"]:
                fired["value"] = True
                raise SimulatedProcessCrash("crash before COMMITTED marker")
            original(project_root, journal)

        with mock.patch("project_harness.stage_transactions._persist_journal", side_effect=crash_before_commit_marker):
            with self.assertRaises(SimulatedProcessCrash):
                accept_stage(root, "PROTOTYPE", approval_path)
        intermediate = self._only_journal(root)
        self.assertEqual(intermediate["status"], "APPLYING")

        first = recover_stage_transactions(root)
        self.assertEqual(first["recovered"][0]["status"], "COMMITTED")
        second = recover_stage_transactions(root)
        self.assertEqual(second["recovered"], [])
        journal = self._only_journal(root)
        self._assert_new(self, root, journal)
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_09_committed_replay_is_idempotent_and_does_not_create_second_transition(self) -> None:
        root, approval_path = self._fresh_case("IDEMPOTENT-COMMIT")
        first = accept_stage(root, "PROTOTYPE", approval_path)
        journal_before = self._only_journal(root)
        first_digest = _digest(root / ".harness/stages/TRANSACTIONS" / first["transaction_ref"] / "TRANSACTION.yaml")

        second = accept_stage(root, "PROTOTYPE", approval_path)
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(second["transaction_ref"], first["transaction_ref"])
        self.assertEqual(len(self._journals(root)), 1)
        self.assertEqual(_digest(root / ".harness/stages/TRANSACTIONS" / first["transaction_ref"] / "TRANSACTION.yaml"), first_digest)
        self._assert_new(self, root, journal_before)

    def test_10_rolled_back_transaction_id_requires_new_approval(self) -> None:
        root, approval_path = self._fresh_case("ROLLED-BACK-RETRY")
        real_replace = os.replace
        fired = {"value": False}

        def fail_once(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
            source = Path(src)
            destination = Path(dst)
            is_apply = source.name.startswith("staged-") and "TRANSACTIONS" not in destination.parts
            if is_apply and not fired["value"]:
                fired["value"] = True
                raise OSError("injected rollback for retry policy")
            real_replace(src, dst)

        with mock.patch("project_harness.stages.os.replace", side_effect=fail_once):
            with self.assertRaises(OSError):
                accept_stage(root, "PROTOTYPE", approval_path)
        with self.assertRaisesRegex(ValidationFailure, "new formal approval and transaction id"):
            accept_stage(root, "PROTOTYPE", approval_path)

        new_approval = stage_approval(root, "PROTOTYPE", decision_suffix="TX-ROLLED-BACK-RETRY-NEW")
        new_path = write_approval(approval_path.parent, "stage-approval-new.yaml", new_approval)
        result = accept_stage(root, "PROTOTYPE", new_path)
        self.assertEqual(result["transaction_status"], "COMMITTED")
        self.assertEqual(len(self._journals(root)), 2)
        statuses = [journal["status"] for journal in self._journals(root)]
        self.assertEqual(statuses, ["ROLLED_BACK", "COMMITTED"])
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_11_corrupt_backup_blocks_recovery_validation_and_new_mutation(self) -> None:
        root, approval_path = self._fresh_case("CORRUPT-BACKUP")
        from project_harness import stage_transactions as tx

        original = tx._persist_journal
        fired = {"value": False}

        def crash_after_prepared(project_root: Path, journal: dict) -> None:
            original(project_root, journal)
            if journal.get("status") == "PREPARED" and not fired["value"]:
                fired["value"] = True
                raise SimulatedProcessCrash("leave PREPARED for corruption test")

        with mock.patch("project_harness.stage_transactions._persist_journal", side_effect=crash_after_prepared):
            with self.assertRaises(SimulatedProcessCrash):
                accept_stage(root, "PROTOTYPE", approval_path)
        journal = self._only_journal(root)
        backup_entry = next(entry for entry in journal["entries"] if entry["backup_path"] is not None)
        (root / backup_entry["backup_path"]).unlink()

        validation = validate_project_directory(root)
        self.assertEqual(validation["status"], "FAIL")
        self.assertIn("STAGE_TRANSACTION_CORRUPT", str(validation["errors"]))
        replacement_approval = stage_approval(root, "PROTOTYPE", decision_suffix="TX-CORRUPT-BACKUP-NEW")
        replacement_path = write_approval(approval_path.parent, "replacement.yaml", replacement_approval)
        with self.assertRaisesRegex(ValidationFailure, "STAGE_TRANSACTION_CORRUPT"):
            accept_stage(root, "PROTOTYPE", replacement_path)

    def test_12_level_up_apply_failure_restores_exact_pre_level_up_state(self) -> None:
        root, approval_path = self._fresh_level_up_case("LEVEL-UP-ROLLBACK")
        before = self._semantic_snapshot(root)
        acceptance = next((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
        acceptance_digest = _digest(acceptance)
        real_replace = os.replace
        applied = {"value": 0}

        def fail_second_level_up_apply(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
            source = Path(src)
            destination = Path(dst)
            is_apply = source.name.startswith("staged-") and "TRANSACTIONS" not in destination.parts
            if is_apply:
                applied["value"] += 1
                if applied["value"] == 2:
                    raise OSError("injected level-up apply failure")
            real_replace(src, dst)

        with mock.patch("project_harness.stages.os.replace", side_effect=fail_second_level_up_apply):
            with self.assertRaisesRegex(OSError, "level-up apply"):
                level_up(root, "MVP", approval_path)
        journal = self._latest_journal(root)
        self.assertEqual(journal["operation_kind"], "LEVEL_UP")
        self._assert_old(self, root, before, journal)
        self.assertEqual(_digest(acceptance), acceptance_digest)
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_13_level_up_missing_commit_marker_recovers_and_replays_idempotently(self) -> None:
        root, approval_path = self._fresh_level_up_case("LEVEL-UP-COMMIT-RECOVERY")
        acceptance = next((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
        acceptance_digest = _digest(acceptance)
        from project_harness import stage_transactions as tx

        original = tx._persist_journal
        fired = {"value": False}

        def crash_level_up_commit(project_root: Path, journal: dict) -> None:
            if (
                journal.get("operation_kind") == "LEVEL_UP"
                and journal.get("status") == "COMMITTED"
                and not fired["value"]
            ):
                fired["value"] = True
                raise SimulatedProcessCrash("crash before level-up COMMITTED marker")
            original(project_root, journal)

        with mock.patch("project_harness.stage_transactions._persist_journal", side_effect=crash_level_up_commit):
            with self.assertRaises(SimulatedProcessCrash):
                level_up(root, "MVP", approval_path)
        recovered = recover_stage_transactions(root)
        self.assertEqual(recovered["recovered"][0]["status"], "COMMITTED")
        journal = self._latest_journal(root)
        self.assertEqual(journal["operation_kind"], "LEVEL_UP")
        self._assert_terminal_write_set(self, root, journal, "NEW")
        state = load_stage_state(root)
        self.assertEqual(state["target_level"], "MVP")
        self.assertEqual(state["highest_accepted_level"], "PROTOTYPE")
        self.assertEqual(state["active_stage"], "ALPHA")
        current = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
        self.assertEqual(current["project_status"], "ACTIVE")
        self.assertEqual(current["active_stage"], "ALPHA")
        self.assertEqual(current["next_route"], "PLAN_ACTIVE_STAGE")
        self.assertEqual(_digest(acceptance), acceptance_digest)

        replay = level_up(root, "MVP", approval_path)
        self.assertTrue(replay["idempotent"])
        self.assertEqual(replay["transaction_ref"], journal["id"])
        self.assertEqual(len(self._journals(root)), 2)
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_14_render_failure_is_a_recoverable_warning_after_commit(self) -> None:
        root, approval_path = self._fresh_case("RENDER-WARNING")
        with mock.patch("project_harness.render.render_roadmap", side_effect=OSError("injected render failure")):
            result = accept_stage(root, "PROTOTYPE", approval_path)
        self.assertEqual(result["transaction_status"], "COMMITTED")
        self.assertEqual(result["render_status"], "FAILED_RECOVERABLE")
        self.assertTrue(any(item.get("code") == "DERIVED_VIEW_RENDER_FAILED" for item in result.get("warnings", [])))
        self._assert_new(self, root, self._only_journal(root))

        replay = accept_stage(root, "PROTOTYPE", approval_path)
        self.assertTrue(replay["idempotent"])
        self.assertEqual(replay["render_status"], "PASS")
        self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_15_validate_project_rejects_mixed_committed_canonical_state(self) -> None:
        with self.subTest(target="STAGE_PLAN_INDEX"):
            root, approval_path = self._fresh_case("MIXED-PLAN-INDEX")
            index_path = root / ".harness/stages/PLANS/INDEX.yaml"
            before_index = deepcopy(load_data(index_path))
            result = accept_stage(root, "PROTOTYPE", approval_path)
            self.assertEqual(result["transaction_status"], "COMMITTED")
            write_data(index_path, before_index)

            validation = validate_project_directory(root)
            self.assertEqual(validation["status"], "FAIL")
            transaction_errors = (
                validation["stage_transaction_recovery"]["validation"] or {}
            ).get("errors") or []
            self.assertTrue(
                any("PLANS/INDEX.yaml" in str(error) for error in transaction_errors),
                transaction_errors,
            )
            self.assertEqual(self._only_journal(root)["status"], "COMMITTED")

        with self.subTest(target="CURRENT_STATE"):
            root, approval_path = self._fresh_case("MIXED-CURRENT-STATE")
            before = self._semantic_snapshot(root)
            result = accept_stage(root, "PROTOTYPE", approval_path)
            self.assertEqual(result["transaction_status"], "COMMITTED")
            write_data(root / ".harness/state/CURRENT_STATE.yaml", {"state": before["current_state"]})

            validation = validate_project_directory(root)
            self.assertEqual(validation["status"], "FAIL")
            transaction_errors = (
                validation["stage_transaction_recovery"]["validation"] or {}
            ).get("errors") or []
            self.assertTrue(
                any("CURRENT_STATE" in str(error) for error in transaction_errors),
                transaction_errors,
            )
            self.assertEqual(self._only_journal(root)["status"], "COMMITTED")

        with self.subTest(target="ACCEPTANCE"):
            root, approval_path = self._fresh_case("MIXED-ACCEPTANCE")
            result = accept_stage(root, "PROTOTYPE", approval_path)
            self.assertEqual(result["transaction_status"], "COMMITTED")
            acceptance = next((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
            acceptance.unlink()

            validation = validate_project_directory(root)
            self.assertEqual(validation["status"], "FAIL")
            transaction_errors = (
                validation["stage_transaction_recovery"]["validation"] or {}
            ).get("errors") or []
            self.assertTrue(
                any("ACCEPTANCE" in str(error) for error in transaction_errors),
                transaction_errors,
            )
            self.assertEqual(self._only_journal(root)["status"], "COMMITTED")


if __name__ == "__main__":
    unittest.main()

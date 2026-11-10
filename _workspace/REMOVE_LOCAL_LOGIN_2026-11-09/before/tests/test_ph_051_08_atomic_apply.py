"""PH-051-08 — bounded diff/write-set, secret and crash-recovery tests.

The Fake runner below is a deterministic unit double, not evidence of actual
rootless Podman security. Public automatic execution remains PH-051-09.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import os
import stat
import tempfile
import unittest
from unittest import mock

from project_harness.apply import ApplyFailure, apply_verified_diff, recover_apply
from project_harness.execution_roots import prepare_execution_root
from project_harness.executors.result import normalize_exact_execution_result
from project_harness.sandbox.verification import verify_disposable
from project_harness.serialization import load_data
from project_harness.util import utc_now
from project_harness.workspace import (check_control_plane, diff_snapshots, record_phase_boundary,
                                       snapshot_product)
from tests.test_engine import prepare_demo
from tests.test_ph_051_03_rootless_podman import profile
from tests.test_ph_051_05_codex_adapter import ADP, SBX, install_profiles, local_profile
from tests.test_ph_051_06_result_channel import agent, sandbox_return, write_result


class Crash(BaseException):
    pass


class FakeVerifiedRunner:
    def __init__(self, result=None):
        self.result = result or {"isolation_verified": True, "termination_reason": "EXITED", "exit_code": 0}
        self.calls = 0

    def run(self, request):
        self.calls += 1
        assert request["network_mode"] == "NONE"
        assert "run_context" not in request
        return self.result


class AtomicApplyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ph05108-test-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.project = prepare_demo(base / "build")[2]
        self.active = load_data(self.project / ".harness/state/CURRENT_STATE.yaml")["state"]["active_run"]
        self.runtime_root = base / "isolated-runtime"
        self.secrets = {}
        self.adp = local_profile()
        self.before = None
        self.execution = None
        self.product = None
        self.diff = None
        self.verification = None

    def _publish_profile(self, *, manual=False):
        install_profiles(self.project, adp=self.adp, manual=manual)
        record_phase_boundary(self.project, self.active, phase="TEST_EXPLICIT_EXECUTION_POLICY",
                              kernel_written_paths=[], recorded_at=utc_now())

    def _start(self, *, new_old=False, secrets=None, manual=False):
        if secrets:
            self.adp["agent_adapter_profile"]["secret_environment_refs"] = ["ENV:" + name for name in secrets]
            self.secrets = secrets
        self._publish_profile(manual=manual)
        if new_old:
            old = self.project / "tests/old.py"
            old.parent.mkdir(exist_ok=True)
            old.write_text("legacy\n")
            record_phase_boundary(self.project, self.active, phase="TEST_ACCEPTED_PRODUCT_BASELINE",
                                  kernel_written_paths=[], recorded_at=utc_now())
        self.before = snapshot_product(self.project)
        binding = prepare_execution_root(self.project, self.runtime_root, run_ref=self.active["run_ref"])
        self.execution = Path(binding["execution_root"])
        self.product = Path(binding["product_dir"])
        return binding

    def _write_candidate(self, *, replace_readme=False, delete_old=False):
        (self.product / "tests").mkdir(exist_ok=True)
        (self.product / "tests/test_task_cli.py").write_text("print('bounded-test')\n")
        (self.product / "task_cli.py").write_text("print('bounded-implementation')\n")
        if replace_readme:
            (self.product / "README.md").write_text("changed readme\n")
        if delete_old:
            (self.product / "tests/old.py").unlink()

    def _normalized(self, *, agent_diff=None, stdout="ordinary bounded log"):
        self.diff = diff_snapshots(self.before, snapshot_product(self.product))
        result = agent(self.active["run_ref"], self.active["task_ref"])
        result["changes"] = self.diff if agent_diff is None else agent_diff
        write_result(self.execution / "output", result)
        response = normalize_exact_execution_result(
            sandbox_return(stdout=stdout), self.execution / "output",
            run_ref=self.active["run_ref"], task_ref=self.active["task_ref"],
            adapter_profile_ref=ADP, sandbox_profile_ref=SBX,
            execution_root_digest="sha256:" + "9" * 64,
            project_root=self.project, secret_values=self.secrets)
        self.assertEqual(response["status"], "PENDING_INDEPENDENT_VERIFICATION", response)

    def _verify(self, *, runner=None):
        task = load_data(self.execution / "control/task-contract.yaml")["task"]
        self.verification = verify_disposable(
            canonical_project_root=self.project, execution_root=self.execution,
            sandbox_profile=profile(), task_contract=task, baseline_files=self.before,
            runner=runner or FakeVerifiedRunner())
        return self.verification

    def _ready(self, *, replace_readme=False, delete_old=False, secrets=None, agent_diff=None):
        self._start(new_old=delete_old, secrets=secrets)
        self._write_candidate(replace_readme=replace_readme, delete_old=delete_old)
        self._normalized(agent_diff=agent_diff)
        value = self._verify()
        self.assertEqual(value["status"], "PASS", value)
        return value

    def apply(self, **kwargs):
        return apply_verified_diff(self.project, self.execution, verification=self.verification,
                                   secret_values=self.secrets, **kwargs)

    def assert_rejected(self, code, **kwargs):
        before = snapshot_product(self.project)
        with self.assertRaises(ApplyFailure) as result:
            self.apply(**kwargs)
        self.assertEqual(result.exception.reason_code, code)
        self.assertEqual(before, snapshot_product(self.project))
        self.assertFalse((self.project / ".harness/evidence" / ("EVD-APPLY-" + self.active["run_ref"] + "-R1.yaml")).exists())

    def test_01_create_replace_and_allowed_delete_end_to_end(self):
        self._ready(replace_readme=True, delete_old=True)
        status = self.apply()
        self.assertEqual(status["status"], "APPLIED")
        self.assertEqual(status["write_set"], 4)
        self.assertFalse((self.project / "tests/old.py").exists())
        self.assertEqual((self.project / "README.md").read_text(), "changed readme\n")
        record = load_data(self.project / ".harness/evidence" / (status["evidence_ref"] + ".yaml"))["apply_evidence"]
        self.assertEqual({row["operation"] for row in record["write_set"]}, {"CREATE", "REPLACE", "DELETE"})
        self.assertEqual(record["verification_ref"], status["verification_ref"])
        self.assertEqual(check_control_plane(self.project, self.active)["status"], "PASS")
        self.assertFalse((self.execution / "apply-journal").exists())
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema optional")
        schema = json.loads((Path(__file__).parents[1] / "schemas/apply_evidence.schema.json").read_text())
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate({"apply_evidence": record})

    def test_02_idempotent_replay_never_rewrites_immutable_evidence(self):
        self._ready()
        first = self.apply()
        path = self.project / ".harness/evidence" / (first["evidence_ref"] + ".yaml")
        payload = path.read_bytes()
        second = self.apply()
        self.assertTrue(second["idempotent"])
        self.assertEqual(payload, path.read_bytes())
        self.assertEqual(len(list((self.project / ".harness/evidence").glob("EVD-APPLY-*.yaml"))), 1)

    def test_03_unverified_or_failing_sandbox_never_applies(self):
        self._ready()
        for mutant in ({**self.verification, "status": "FAIL"}, {**self.verification, "reason_code": "VERIFICATION_FAILED"},
                       {**self.verification, "command_results": []}, {**self.verification, "verified_subjects": ["ARCHITECTURE_RECORD"]}):
            with self.subTest(mutant=mutant):
                self.verification = mutant
                self.assert_rejected("VERIFICATION_FAILED")

    def test_04_actual_vs_scope_violation_after_verification(self):
        self._ready()
        (self.product / "unapproved.txt").write_text("out of scope")
        self.assert_rejected("VERIFICATION_FAILED")

    def test_05_special_fifo_after_verification_rejected_without_opening(self):
        self._ready()
        os.mkfifo(self.product / "task.fifo")
        self.assert_rejected("SCOPE_VIOLATION")

    def test_06_symlink_escape_and_hardlink_rejected(self):
        self._ready()
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("SECRET_OUTSIDE")
        for mode in ("symlink", "hardlink"):
            with self.subTest(mode=mode):
                p = self.product / "escape.txt"
                p.symlink_to(outside) if mode == "symlink" else os.link(outside, p)
                self.assert_rejected("SCOPE_VIOLATION")
                p.unlink()
        self.assertEqual(outside.read_text(), "SECRET_OUTSIDE")

    def test_07_control_or_git_tree_in_disposable_rejected(self):
        self._ready()
        for name in (".harness", ".git"):
            with self.subTest(name=name):
                folder = self.product / name
                folder.mkdir()
                (folder / "tampered.txt").write_text("malicious")
                self.assert_rejected("SCOPE_VIOLATION")
                (folder / "tampered.txt").unlink(); folder.rmdir()

    def test_08_changed_canonical_baseline_denies_apply(self):
        self._ready()
        (self.project / "README.md").write_text("concurrent edit")
        with self.assertRaises(ApplyFailure) as result:
            self.apply()
        self.assertEqual(result.exception.reason_code, "BASELINE_CHANGED")
        self.assertEqual((self.project / "README.md").read_text(), "concurrent edit")

    def test_09_changed_verified_content_denies_apply(self):
        self._ready()
        (self.product / "task_cli.py").write_text("modified after verification")
        self.assert_rejected("VERIFICATION_FAILED")

    def test_10_exact_secret_in_changed_file_blocks_before_write(self):
        self._ready(secrets={"FAKE_CLI_SECRET": "TOKEN-VERY-PRIVATE-98765"})
        (self.product / "task_cli.py").write_text("# TOKEN-VERY-PRIVATE-98765")
        # Read-only PH-051-08 gate scans before post-verifier consistency checks
        # when verification is called again on the changed candidate.
        self._verify()
        self.assertEqual(self.verification["status"], "PASS")
        self.assert_rejected("SECRET_LEAK_DETECTED")

    def test_11_omitted_configured_secret_cannot_bypass_scan(self):
        self._ready(secrets={"FAKE_CLI_SECRET": "secret-example-18926"})
        with self.assertRaises(ApplyFailure) as result:
            apply_verified_diff(self.project, self.execution, verification=self.verification, secret_values={})
        self.assertEqual(result.exception.reason_code, "SECRET_REFERENCE_MISSING")
        self.assertEqual(snapshot_product(self.project), self.before)

    def test_12_forged_agent_change_declaration_never_authorizes_apply(self):
        self._ready(agent_diff={"added": [], "modified": [], "deleted": []})
        self.assert_rejected("SCOPE_VIOLATION")

    def test_13_mode_only_or_mode_escalation_not_copied(self):
        self._ready()
        (self.product / "README.md").chmod(0o755)
        self.assert_rejected("SCOPE_VIOLATION")

    def test_14_expected_path_absent_is_rejected(self):
        self._ready()
        (self.product / "task_cli.py").unlink()
        self.assert_rejected("VERIFICATION_FAILED")

    def test_15_no_implicit_automatic_opt_in(self):
        self._start(manual=True)
        self._write_candidate()
        self._normalized()
        self._verify()
        self.assert_rejected("VERIFICATION_FAILED")

    def test_16_preserve_manual_runtime_with_public_opt_in_cli(self):
        from project_harness.cli import build_parser
        self.assertIn("execute-current", build_parser().format_help())
        self.assertFalse((self.project / ".harness/runtime/APPLY_JOURNALS").exists())

    def test_17_interrupted_apply_recovers_all_old_or_all_new(self):
        for point in ("JOURNAL_PREPARED", "AFTER_OPERATION_1", "AFTER_OPERATION_2",
                      "AFTER_OPERATION_3", "PRODUCT_APPLIED", "EVIDENCE_WRITTEN",
                      "BEFORE_COMMIT_MARKER", "COMMITTED"):
            with self.subTest(point=point):
                # New self-contained Run fixture per fault point.
                case = AtomicApplyTests(methodName="runTest")
                case.setUp()
                try:
                    case._ready(replace_readme=True, delete_old=True)
                    original = snapshot_product(case.project)
                    def stop(event):
                        if event == point:
                            raise Crash(event)
                    with self.assertRaises(Crash):
                        case.apply(fault_hook=stop)
                    result = recover_apply(case.project, case.execution)
                    if point == "COMMITTED":
                        self.assertEqual(result["status"], "APPLIED")
                        self.assertNotEqual(snapshot_product(case.project), original)
                        self.assertEqual(check_control_plane(case.project, case.active)["status"], "PASS")
                    else:
                        self.assertEqual(result["status"], "ROLLED_BACK")
                        self.assertEqual(snapshot_product(case.project), original)
                        self.assertEqual(check_control_plane(case.project, case.active)["status"], "PASS")
                    self.assertFalse((case.execution / "apply-journal").exists())
                finally:
                    case.doCleanups()

    def test_18_recovery_is_safe_to_repeat_without_journal(self):
        self._ready()
        self.assertEqual(recover_apply(self.project, self.execution)["status"], "NO_JOURNAL")
        self.assertEqual(recover_apply(self.project, self.execution)["status"], "NO_JOURNAL")

    def test_19_exception_after_first_operation_rolls_back_immediately(self):
        self._ready(replace_readme=True)
        before = snapshot_product(self.project)
        with self.assertRaises(ApplyFailure) as result:
            self.apply(fault_hook=lambda event: (_ for _ in ()).throw(OSError("simulated interrupted IO"))
                       if event == "AFTER_OPERATION_1" else None)
        self.assertEqual(result.exception.reason_code, "APPLY_FAILED_RECOVERABLE")
        self.assertEqual(snapshot_product(self.project), before)
        self.assertFalse((self.execution / "apply-journal").exists())

    def test_20_recovery_rejects_corrupted_backup_before_touching_product(self):
        self._ready(replace_readme=True)
        def stop(event):
            if event == "AFTER_OPERATION_1": raise Crash()
        with self.assertRaises(Crash):
            self.apply(fault_hook=stop)
        backup = self.execution / "apply-journal/backup/000000"
        # First changed item may be CREATE without backup; corrupt the first
        # available backup to model disk/tamper damage.
        files = list((self.execution / "apply-journal/backup").glob("*"))
        self.assertTrue(files)
        files[0].write_bytes(b"corrupted backup")
        with self.assertRaises(ApplyFailure) as result:
            recover_apply(self.project, self.execution)
        self.assertEqual(result.exception.reason_code, "APPLY_FAILED_RECOVERABLE")
        self.assertTrue((self.execution / "apply-journal/journal.json").exists())

    def test_21_post_commit_cleanup_exception_reports_committed_truthfully(self):
        self._ready()
        from project_harness import apply as apply_module
        original_rename = apply_module.os.rename
        def fail_after_retire(source, target):
            original_rename(source, target)
            raise OSError("fault after durable cleanup-directory rename")
        with mock.patch.object(apply_module.os, "rename", side_effect=fail_after_retire):
            outcome = self.apply()
        self.assertEqual(outcome["status"], "APPLIED")
        self.assertTrue(outcome["cleanup_pending"])
        self.assertEqual(check_control_plane(self.project, self.active)["status"], "PASS")
        self.assertFalse((self.execution / "apply-journal").exists())
        self.assertTrue((self.execution / ".apply-cleanup").exists())
        self.assertTrue(self.apply()["idempotent"])

    def test_22_fault_before_journal_marker_cannot_modify_canonical(self):
        self._ready()
        original = snapshot_product(self.project)
        from project_harness import apply as apply_module
        real_write = apply_module._exclusive_write
        def fail_staging(path, data, **kwargs):
            if path.parent.name == "stage":
                raise OSError("injected failure before prepared journal")
            return real_write(path, data, **kwargs)
        with mock.patch.object(apply_module, "_exclusive_write", side_effect=fail_staging):
            with self.assertRaises(ApplyFailure) as result:
                self.apply()
        self.assertEqual(result.exception.reason_code, "APPLY_FAILED_RECOVERABLE")
        self.assertEqual(snapshot_product(self.project), original)
        self.assertFalse((self.execution / "apply-journal").exists())
        self.assertEqual(check_control_plane(self.project, self.active)["status"], "PASS")

    def test_23_bounded_log_exact_secret_is_rescanned_at_apply(self):
        self._ready(secrets={"FAKE_CLI_SECRET": "VERY-PRIVATE-KEY-443211"})
        log_path = next((self.project / ".harness/runtime/EXECUTION_LOGS").glob("ART-STDOUT-*.log"))
        log_path.write_text("VERY-PRIVATE-KEY-443211", encoding="utf-8")
        # Simulates a kernel-signed but wrongly published bounded log: the
        # independent PH-051-08 gate must still reject its exact secret.
        record_phase_boundary(self.project, self.active, phase="TEST_RECHECK_BOUNDED_LOG",
                              kernel_written_paths=[], recorded_at=utc_now())
        self.assert_rejected("SECRET_LEAK_DETECTED")

    def test_24_parent_directory_symlink_after_verification(self):
        self._ready()
        target = Path(self.temp.name) / "outside-dir"
        target.mkdir()
        import shutil
        shutil.rmtree(self.product / "tests")
        (self.product / "tests").symlink_to(target, target_is_directory=True)
        self.assert_rejected("SCOPE_VIOLATION")

    def test_25_replacing_product_preserves_nondefault_canonical_mode(self):
        self._publish_profile()
        target = self.project / "README.md"
        target.chmod(0o600)
        record_phase_boundary(self.project, self.active, phase="TEST_README_MODE_BASELINE",
                              kernel_written_paths=[], recorded_at=utc_now())
        self.before = snapshot_product(self.project)
        setup = prepare_execution_root(self.project, self.runtime_root, run_ref=self.active["run_ref"])
        self.execution = Path(setup["execution_root"])
        self.product = Path(setup["product_dir"])
        self._write_candidate(replace_readme=True)
        self._normalized()
        self._verify()
        self.assertEqual(self.verification["status"], "PASS")
        self.assertEqual(self.apply()["status"], "APPLIED")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)


if __name__ == "__main__":
    unittest.main()

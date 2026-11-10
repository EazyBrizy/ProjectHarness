"""PH-051-09 integration of actual public routes and focused negative cases.

Podman and CLI are *mocked* here at the trusted sandbox transport boundary.
No case in this module is proof of rootless OS isolation. Live security
acceptance requires separately provisioned rootless Podman in PH-051-11/12.
"""
from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest import mock

from project_harness.cli import build_parser, main
from project_harness.errors import ValidationFailure
from project_harness.runtime import (execute_current, executor_doctor, next_task, project_status,
                                    verify_current, complete_current, automatic_run_phase)
from project_harness.sandbox.podman_rootless import RootlessPodmanRunner
from project_harness.serialization import load_data, write_data
from project_harness.workspace import (check_control_plane, diff_snapshots, record_phase_boundary,
                                       snapshot_product)
from project_harness.util import utc_now
from tests.test_engine import prepare_demo
from tests.test_ph_051_05_codex_adapter import install_profiles
from tests.test_ph_051_06_result_channel import agent, sandbox_return


HEALTH = {"status": "PASS", "backend": "ROOTLESS_PODMAN",
          "isolation_verified": True, "network_mode": "NONE",
          "checks": {"rootless": "PASS", "effective_uid": "PASS", "network_none": "PASS"}}


class SimulatedPodman:
    """A deterministic *transport double*, not a security attestation."""
    def __init__(self, *, fail: str | None = None, result_status: str = "COMPLETED",
                 wrong_paths: bool = False, baseline_drift: bool = False,
                 verify_fail: bool = False, secret_echo: bool = False):
        self.agent_calls = 0
        self.verifier_calls = 0
        self.fail = fail
        self.result_status = result_status
        self.wrong_paths = wrong_paths
        self.baseline_drift = baseline_drift
        self.verify_fail = verify_fail
        self.secret_echo = secret_echo

    def run(self, _runner, request, **kwargs):
        if "run_context" not in request:
            self.verifier_calls += 1
            self.assert_sandbox_request(request)
            return {"termination_reason": "EXITED", "exit_code": 1 if self.verify_fail else 0,
                    "isolation_verified": True, "stdout": "verify-failed" if self.verify_fail else "verify-ok", "stderr": ""}
        self.agent_calls += 1
        self.assert_sandbox_request(request)
        if self.fail == "TIMEOUT":
            return sandbox_return(termination_reason="TIMED_OUT", reason_code="EXECUTOR_TIMEOUT", exit_code=None)
        if self.fail == "NONZERO":
            return sandbox_return(exit_code=17)
        product = Path(request["product_dir"])
        (product / "tests").mkdir(exist_ok=True)
        (product / "tests/test_task_cli.py").write_text("print('bounded-test')\n")
        (product / "task_cli.py").write_text("print('bounded-implementation')\n")
        if self.wrong_paths:
            (product / "unapproved-secret.txt").write_text("not authorized")
        if self.baseline_drift:
            Path(request["canonical_project_root"], "external-drift.txt").write_text("changed")
        from project_harness.workspace import snapshot_product
        before = snapshot_product(Path(request["canonical_project_root"]))
        # Original project has no agent writes; compare exact baseline with product.
        declared = diff_snapshots(before, snapshot_product(product))
        payload = agent(request["run_context"]["run_id"], request["run_context"]["task_id"])
        payload["status"] = self.result_status
        payload["changes"] = declared
        if self.fail != "MISSING":
            target = Path(request["output_dir"]) / "agent-result.json"
            target.write_text(json.dumps(payload), encoding="utf-8")
        return sandbox_return(stdout=os.environ.get("TEST_SECRET", "") if self.secret_echo else "bounded stdout")

    @staticmethod
    def assert_sandbox_request(request):
        assert request["network_mode"] == "NONE"
        assert str(request["product_dir"]) != str(request["canonical_project_root"])
        assert str(request["control_dir"]).endswith("control")
        assert str(request["output_dir"]).endswith("output")


class AutomaticRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ph05109-public-")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.project = prepare_demo(base / "source")[2]
        self.runtime_root = base / "trusted-runtime"
        self.initial = load_data(self.project / ".harness/state/CURRENT_STATE.yaml")["state"]
        self.initial_ref = self.initial["active_run"]["run_ref"]

    def activate(self, *, completion="EXPLICIT_AFTER_VERIFICATION", secret=None):
        from tests.test_ph_051_05_codex_adapter import local_profile
        profile = local_profile()
        if secret is not None:
            profile["agent_adapter_profile"]["secret_environment_refs"] = ["ENV:TEST_SECRET"]
        install_profiles(self.project, adp=profile)
        if completion != "EXPLICIT_AFTER_VERIFICATION":
            lock = self.project / ".harness/config/PROJECT_LOCK.yaml"
            value = load_data(lock)
            value["project_lock"]["execution"]["completion_policy"] = completion
            write_data(lock, value)
        record_phase_boundary(self.project, self.initial["active_run"],
                              phase="TEST_APPROVED_PROFILE_ACTIVATION",
                              kernel_written_paths=[], recorded_at=utc_now())

    def run_fake(self, simulation=None):
        simulated = simulation or SimulatedPodman()
        with mock.patch.object(RootlessPodmanRunner, "doctor", return_value=deepcopy(HEALTH)), \
             mock.patch.object(RootlessPodmanRunner, "run", autospec=True, side_effect=simulated.run):
            result = execute_current(self.project, runtime_root=self.runtime_root)
        return result, simulated

    def test_01_cli_commands_exported_python_api_and_flags(self):
        parser = build_parser()
        for name in ("executor-doctor", "execute-current"):
            args = parser.parse_args([name, "--project", str(self.project),
                                      "--adapter-profile", "ADP-X@1", "--network", "NONE"])
            self.assertEqual(args.command, name)
        from project_harness import execute_current as public_execute, executor_doctor as public_doctor
        self.assertIs(public_execute, execute_current)
        self.assertIs(public_doctor, executor_doctor)

    def test_02_manual_default_does_not_reserve_or_invoke_cli(self):
        original = (self.project / ".harness/config/PROJECT_LOCK.yaml").read_bytes()
        with mock.patch.object(RootlessPodmanRunner, "run", side_effect=AssertionError("host/sandbox should not run")) as runner:
            self.assertEqual(executor_doctor(self.project)["reason_code"], "EXECUTOR_UNAVAILABLE")
            result = execute_current(self.project, runtime_root=self.runtime_root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason_code"], "EXECUTOR_UNAVAILABLE")
        runner.assert_not_called()
        self.assertEqual(original, (self.project / ".harness/config/PROJECT_LOCK.yaml").read_bytes())
        self.assertEqual(project_status(self.project)["status"], "ACTIVE")

    def test_03_missing_podman_doctor_fail_closed_no_host_fallback(self):
        self.activate()
        with mock.patch.object(RootlessPodmanRunner, "doctor", return_value={"status":"BLOCKED","reason_code":"SANDBOX_UNAVAILABLE"}), \
             mock.patch.object(RootlessPodmanRunner, "run", side_effect=AssertionError("must not run")) as runner:
            value = execute_current(self.project, runtime_root=self.runtime_root)
        self.assertEqual(value["status"], "BLOCKED")
        self.assertEqual(value["reason_code"], "SANDBOX_UNAVAILABLE")
        runner.assert_not_called()
        self.assertEqual(check_control_plane(self.project, self.initial["active_run"])["status"], "PASS")

    def test_04_no_egress_or_unpinned_adapter_override_or_unapproved_debug(self):
        self.activate()
        for options, reason in [
            ({"network": "EXPLICIT_APPROVED_EGRESS"}, "NETWORK_NOT_APPROVED"),
            ({"network": "EXPLICIT_APPROVED_EGRESS", "approval": Path("/dev/null")}, "NETWORK_NOT_APPROVED"),
            ({"adapter_profile": "ADP-FOREIGN@1"}, "SANDBOX_POLICY_FAILURE"),
            ({"keep_execution_root": True}, "SANDBOX_POLICY_FAILURE"),
            ({"approval": Path("/dev/null")}, "NETWORK_NOT_APPROVED"),
        ]:
            with self.subTest(options=options):
                self.assertEqual(executor_doctor(self.project, **options)["reason_code"], reason)
                self.assertEqual(execute_current(self.project, runtime_root=self.runtime_root, **options)["reason_code"], reason)

    def test_05_controlled_success_explicit_completion_and_idempotent_replay(self):
        self.activate()
        before = snapshot_product(self.project)
        result, simulated = self.run_fake()
        self.assertEqual(result["status"], "SUCCEEDED", result)
        self.assertEqual(result["completion_status"], "WAITING_EXPLICIT_COMPLETION")
        self.assertEqual((simulated.agent_calls, simulated.verifier_calls), (1, 2))
        self.assertNotEqual(snapshot_product(self.project), before)
        self.assertEqual(check_control_plane(self.project, self.initial["active_run"])["status"], "PASS")
        status = project_status(self.project)
        self.assertEqual(status["automatic_run"]["status"], "SUCCEEDED")
        self.assertEqual(status["next_route"], "COMPLETE_TASK")
        self.assertEqual(next_task(self.project)["next_operator_route"]["route"], "COMPLETE_VERIFIED_TASK")
        from project_harness.validation import validate_runtime_reachability
        self.assertEqual(validate_runtime_reachability(self.project)["status"], "PASS", validate_runtime_reachability(self.project))
        from project_harness.validation import validate_project_directory
        validated = validate_project_directory(self.project)
        self.assertEqual(validated["status"], "PASS", validated)
        self.assertEqual(result["run_ref"], self.initial_ref)
        second, simulated2 = self.run_fake()
        self.assertEqual(second["status"], "SUCCEEDED")
        self.assertTrue(second["idempotent"])
        self.assertEqual(simulated2.agent_calls, 0)
        with self.assertRaises(ValidationFailure):
            verify_current(self.project, allow_command_execution=True)
        completed = complete_current(self.project, self.project / self.initial["active_run"]["allowed_agent_output_path"])
        self.assertEqual(completed["status"], "COMPLETED", completed)
        self.assertEqual(completed["run_status"], "SUCCEEDED")
        self.assertTrue((self.project / ".harness/runtime/RUNS" / (self.initial_ref + ".yaml")).is_file())
        self.assertEqual(validate_project_directory(self.project)["status"], "PASS")

    def test_06_auto_after_pass_completes_without_stage_approval(self):
        self.activate(completion="AUTO_AFTER_PASS")
        result, simulated = self.run_fake()
        self.assertEqual(result["status"], "COMPLETED", result)
        self.assertEqual(result["run_status"], "SUCCEEDED")
        self.assertEqual(result["automatic_execution"], True)
        self.assertEqual((simulated.agent_calls, simulated.verifier_calls), (1, 2))
        self.assertFalse((self.project / ".harness/state/CURRENT_STATE.yaml").read_text().find('STAGE_ACCEPTED') >= 0)

    def test_07_timeout_immutable_run_blocker_then_new_attempt_on_resume(self):
        self.activate()
        result, simulated = self.run_fake(SimulatedPodman(fail="TIMEOUT"))
        self.assertEqual(result["status"], "TIMED_OUT", result)
        self.assertEqual(result["reason_code"], "EXECUTOR_TIMEOUT")
        self.assertEqual((simulated.agent_calls, simulated.verifier_calls), (1, 0))
        old = self.project / ".harness/runtime/RUNS" / (self.initial_ref + ".yaml")
        historic = old.read_bytes()
        self.assertEqual(load_data(old)["run"]["status"], "TIMED_OUT")
        self.assertEqual(project_status(self.project)["status"], "BLOCKED")
        subsequent, simulated2 = self.run_fake()
        self.assertEqual(subsequent["status"], "BLOCKED")
        self.assertEqual(simulated2.agent_calls, 0)
        from project_harness.runtime import resume_blocked
        resumed = resume_blocked(self.project, resolution="Checked and corrected timeout prerequisite")
        self.assertEqual(resumed["status"], "RESUMED")
        self.assertNotEqual(resumed["next"]["run_ref"], self.initial_ref)
        self.assertEqual(old.read_bytes(), historic)

    def test_08_nonzero_or_agent_failed_or_result_missing_never_applies(self):
        for name, case, reason in (
            ("NONZERO", SimulatedPodman(fail="NONZERO"), "EXECUTOR_EXIT_NONZERO"),
            ("MISSING", SimulatedPodman(fail="MISSING"), "RESULT_INVALID"),
            ("FAILED", SimulatedPodman(result_status="FAILED"), "RESULT_INVALID"),
        ):
            with self.subTest(name=name):
                case_instance = AutomaticRunTests(methodName="runTest")
                case_instance.setUp()
                try:
                    case_instance.activate()
                    before = snapshot_product(case_instance.project)
                    result, runner = case_instance.run_fake(case)
                    self.assertIn(result["status"], {"FAILED_RETRYABLE", "BLOCKED"}, result)
                    self.assertEqual(result["reason_code"], reason)
                    self.assertEqual(before, snapshot_product(case_instance.project))
                    self.assertEqual(runner.verifier_calls, 0)
                finally:
                    case_instance.tearDown()
                    case_instance.doCleanups()

    def test_09_scope_or_baseline_violation_no_apply(self):
        for name, case, reason in (
            ("SCOPE", SimulatedPodman(wrong_paths=True), "SCOPE_VIOLATION"),
            ("BASELINE", SimulatedPodman(baseline_drift=True), "BASELINE_CHANGED"),
        ):
            with self.subTest(name=name):
                instance = AutomaticRunTests(methodName="runTest")
                instance.setUp()
                try:
                    instance.activate()
                    before = snapshot_product(instance.project)
                    result, runner = instance.run_fake(case)
                    self.assertEqual(result["reason_code"], reason, result)
                    self.assertFalse((instance.project / "task_cli.py").exists())
                    self.assertTrue(runner.agent_calls == 1)
                finally:
                    instance.tearDown()
                    instance.doCleanups()

    def test_10_independent_verification_failure_never_applies(self):
        self.activate()
        before = snapshot_product(self.project)
        result, simulation = self.run_fake(SimulatedPodman(verify_fail=True))
        self.assertEqual(result["status"], "FAILED_RETRYABLE", result)
        self.assertEqual(result["reason_code"], "VERIFICATION_FAILED", result)
        self.assertEqual((simulation.agent_calls, simulation.verifier_calls), (1, 1))
        self.assertEqual(before, snapshot_product(self.project))
        self.assertEqual(project_status(self.project)["status"], "BLOCKED")

    def test_11_secret_echo_before_verification_never_applies(self):
        self.activate(secret=True)
        before = snapshot_product(self.project)
        with mock.patch.dict(os.environ, {"TEST_SECRET": "TEST_SECRET_VALUE_987654321"}):
            result, simulation = self.run_fake(SimulatedPodman(secret_echo=True))
        self.assertEqual(result["reason_code"], "SECRET_LEAK_DETECTED", result)
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertEqual(simulation.agent_calls, 1)
        self.assertEqual(simulation.verifier_calls, 0)
        self.assertEqual(before, snapshot_product(self.project))
        for path in (self.project / ".harness").rglob("*"):
            if path.is_file():
                self.assertNotIn(b"TEST_SECRET_VALUE_987654321", path.read_bytes(), path.name)

    def test_12_current_run_continuation_is_local_auto_not_host_verify(self):
        self.activate()
        status = project_status(self.project)
        self.assertEqual(status["next_operator_route"]["route"], "EXECUTE_LOCAL_AUTOMATIC")
        self.assertEqual(status["next_operator_route"]["command"],
                         "project-harness execute-current --project <root>")
        from project_harness.validation import validate_runtime_reachability
        value = validate_runtime_reachability(self.project)
        self.assertEqual(value["status"], "PASS", value)

    def test_13_replayed_inflight_run_does_not_launch_twice(self):
        self.activate()
        record_phase_boundary(self.project, self.initial["active_run"], phase="AUTO_RUNNING",
                              kernel_written_paths=[], recorded_at=utc_now())
        result, runner = self.run_fake()
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertEqual(result["run_status"], "RUNNING")
        self.assertEqual(runner.agent_calls, 0)
        self.assertEqual(automatic_run_phase(self.project, self.initial["active_run"])["status"], "RUNNING")

    def test_14_tampered_apply_evidence_fails_project_validation_and_completion(self):
        self.activate()
        result, _ = self.run_fake()
        self.assertEqual(result["status"], "SUCCEEDED", result)
        proof_path = self.project / ".harness/evidence" / (result["apply_evidence_ref"] + ".yaml")
        proof = load_data(proof_path)
        proof["apply_evidence"]["run_ref"] = "RUN-UNRELATED@1"
        write_data(proof_path, proof)
        from project_harness.validation import validate_project_directory
        bad = validate_project_directory(self.project)
        self.assertEqual(bad["status"], "FAIL", bad)
        self.assertTrue(any(check["status"] == "FAIL" for check in bad["checks"]))
        completion = complete_current(self.project, self.project / self.initial["active_run"]["allowed_agent_output_path"])
        self.assertEqual(completion["status"], "BLOCKED", completion)

    def test_15_cli_json_exit_codes_manual_doctor_and_public_execute(self):
        from io import StringIO
        with mock.patch("sys.stdout", new_callable=StringIO) as capture:
            code = main(["executor-doctor", "--project", str(self.project)])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(capture.getvalue())["reason_code"], "EXECUTOR_UNAVAILABLE")
        with mock.patch("sys.stdout", new_callable=StringIO) as capture:
            code = main(["execute-current", "--project", str(self.project)])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(capture.getvalue())["status"], "BLOCKED")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

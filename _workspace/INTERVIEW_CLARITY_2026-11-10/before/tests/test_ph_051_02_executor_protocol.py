"""PH-051-02 unit/negative tests; no real or fake host CLI launch."""

from __future__ import annotations

import ast
import contextlib
import io
import os
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from project_harness.cli import build_parser
from project_harness.errors import ValidationFailure
from project_harness.executors import CodexCliLocalAdapter, ExecutorAdapter
from project_harness.executors.codex_cli_local import ALLOWED_PLACEHOLDERS, prepare_argv

ROOT = Path(__file__).resolve().parents[1]
FAKE = ROOT / "tests/fixtures/fake_codex_cli.py"


def profile(template=None) -> dict:
    return {
        "id": "ADP-CODEX-CLI-LOCAL-001", "revision": 1,
        "status": "ACTIVE", "kind": "CODEX_CLI_LOCAL",
        "executable": "codex",
        "argv_template": template if template is not None else [
            "codex", "exec", "--prompt-file", "{prompt_bundle_path}",
            "--result-file", "{agent_result_path}",
        ],
        "working_directory": "/workspace/product", "timeout_seconds": 1200,
        "stdin_mode": "CLOSED", "environment_allowlist": ["LANG", "LC_ALL"],
        "secret_environment_refs": ["ENV:FAKE_CLI_SECRET"],
        "sandbox_profile_ref": "SBX-ROOTLESS-PODMAN-001@1",
    }


def context(p=None) -> dict:
    return {
        "adapter_profile": p if p is not None else profile(),
        "prompt_bundle_path": "/workspace/control/prompt-bundle.md",
        "context_packet_path": "/workspace/control/context.json",
        "agent_result_path": "/output/agent-result.json",
        "workspace_path": "/workspace/product",
        "run_id": "RUN-TEST-001@1", "task_id": "TSK-TEST-001",
    }


class RecordingSandboxStub:
    """Non-executing in-memory protocol double, NOT a security self-test."""

    def __init__(self, health=None):
        self.health = health or {"status": "PASS", "backend": "ROOTLESS_PODMAN", "isolation_verified": True}
        self.requests: list[dict] = []

    def doctor(self, sandbox_profile):
        return dict(self.health)

    def run(self, request):
        self.requests.append(request)
        return {"termination_reason": "EXITED", "exit_code": 17}


class ExecutorProtocolTests(unittest.TestCase):
    def test_01_interface_is_minimal_and_wip(self):
        instance = CodexCliLocalAdapter()
        self.assertTrue(isinstance(instance, ExecutorAdapter))  # structural typing not runtime-checkable?

    def test_02_all_six_allowlisted_placeholders(self):
        self.assertEqual(set(ALLOWED_PLACEHOLDERS), {
            "prompt_bundle_path", "context_packet_path", "agent_result_path",
            "workspace_path", "run_id", "task_id",
        })
        c = context(profile(["codex", "exec", "{prompt_bundle_path}", "{context_packet_path}",
                             "{agent_result_path}", "{workspace_path}", "{run_id}", "{task_id}"]))
        self.assertEqual(prepare_argv(c), ["codex", "exec", c["prompt_bundle_path"],
                                           c["context_packet_path"], c["agent_result_path"],
                                           c["workspace_path"], c["run_id"], c["task_id"]])
        self.assertEqual(prepare_argv(c), prepare_argv(c))

    def test_03_exact_binary_policy(self):
        for exe in ("codex", "/usr/bin/codex", "/opt/tools/codex"):
            p = profile([exe, "exec"])
            p["executable"] = exe
            self.assertEqual(prepare_argv(context(p))[0], exe)
        for exe in ("./codex", "../codex", "tools/codex", "/bin/../codex",
                    "/bin//codex", "codex;whoami", "codex --version", "$(whoami)"):
            p = profile([exe, "exec"]);p["executable"] = exe
            with self.subTest(exe=exe), self.assertRaises(ValidationFailure):
                prepare_argv(context(p))
        p = profile(["another", "exec"])
        with self.assertRaises(ValidationFailure):
            prepare_argv(context(p))

    def test_04_command_strings_and_shell_modes_rejected(self):
        bad_templates = [
            "codex exec --prompt-file {prompt_bundle_path}",
            ["codex exec", "--prompt-file", "{prompt_bundle_path}"],
            ["codex", "exec | tee leaked"], ["codex", "exec", ";", "rm"],
            ["codex", "exec", "&&", "sh"], ["codex", "exec", ">/output/x"],
            ["codex", "exec", "<input"], ["codex", "exec", "$(whoami)"],
            ["codex", "exec", "`id`"], ["codex", "exec", "${HOME}"],
            ["codex", "exec", "--flag=a\\;b"], ["codex", "exec\nsh"],
            ["codex", "'exec'"], ["codex", "exec", "foo bar"],
        ]
        for value in bad_templates:
            with self.subTest(value=value), self.assertRaises(ValidationFailure):
                prepare_argv(context(profile(value)))

    def test_05_only_full_known_placeholders(self):
        for item in ("{unknown}", "{prompt_bundle_path}suffix", "--file={prompt_bundle_path}",
                     "{prompt_bundle_path.__class__}", "{{prompt_bundle_path}}", "{run_id!r}",
                     "{__globals__}", "{prompt_bundle_path", "{run_id}-{task_id}"):
            with self.subTest(arg=item), self.assertRaises(ValidationFailure):
                prepare_argv(context(profile(["codex", "exec", item])))

    def test_06_exact_trusted_container_paths_and_ids(self):
        changes = (
            ("prompt_bundle_path", "/home/operator/codex.md"),
            ("prompt_bundle_path", "/workspace/control/../product/secret"),
            ("context_packet_path", "/workspace/control//d.json"),
            ("context_packet_path", "/workspace/control/"),
            ("agent_result_path", "/workspace/product/agent-result.json"),
            ("agent_result_path", "/output/other.json"),
            ("workspace_path", "/home/operator/project"),
            ("run_id", "RUN-X;touch /tmp/host"),
            ("task_id", "TSK-test"),
            ("task_id", "RUN-TEST-001"),
        )
        for key, value in changes:
            c = context(profile(["codex", "{prompt_bundle_path}", "{context_packet_path}",
                                 "{agent_result_path}", "{workspace_path}", "{run_id}", "{task_id}"]))
            c[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValidationFailure):
                prepare_argv(c)

    def test_07_no_raw_text_secrets_or_host_env_substitution(self):
        for extra in ("user_message", "env", "secret_values", "api_key", "shell", "host_env", "prompt"):
            c = context();c[extra] = "SECRET-RAW-DO-NOT-PASS"
            with self.subTest(extra=extra), self.assertRaises(ValidationFailure):
                prepare_argv(c)
        for flag in ("--api-key=SECRET", "--password=abc", "--token=abc", "--secret", "--credential=abc"):
            with self.subTest(flag=flag), self.assertRaises(ValidationFailure):
                prepare_argv(context(profile(["codex", flag])))

    def test_08_profile_strict_required_fields_and_active_identity(self):
        for change in ({"kind": "REMOTE_HTTP"}, {"status": "DRAFT"},
                       {"id": "ABC-LOCAL"}, {"revision": 0}, {"revision": True},
                       {"stdin_mode": "OPEN"}, {"working_directory": "/host"},
                       {"timeout_seconds": 0}, {"timeout_seconds": 999999},
                       {"sandbox_profile_ref": "SBX-LOCAL@latest"}):
            p = profile();p.update(change)
            with self.subTest(change=change), self.assertRaises(ValidationFailure):
                prepare_argv(context(p))
        for key in profile():
            p = profile(); del p[key]
            with self.subTest(missing=key), self.assertRaises(ValidationFailure):
                prepare_argv(context(p))
        p = profile();p["secret_values"] = {"ENV:KEY": "danger"}
        with self.assertRaises(ValidationFailure):
            prepare_argv(context(p))

    def test_09_environment_names_and_refs_only(self):
        for change in ({"environment_allowlist": "HOME"},
                       {"environment_allowlist": ["PATH", "PATH"]},
                       {"environment_allowlist": ["FOO=secret"]},
                       {"secret_environment_refs": ["raw-secret-value"]},
                       {"secret_environment_refs": ["ENV:LC_ALL"]},
                       {"secret_environment_refs": ["ENV:X", "ENV:X"]},
                       {"secret_environment_refs": ["ENV:LD_PRELOAD"]},
                       {"environment_allowlist": ["OPENAI_API_KEY"]},
                       {"environment_allowlist": ["PATH"]},
                       {"environment_allowlist": ["SSH_AUTH_SOCK"]}):
            p = profile();p.update(change)
            with self.subTest(change=change), self.assertRaises(ValidationFailure):
                prepare_argv(context(p))
        p = profile();p["secret_environment_refs"] = ["ENV:CODEX_API_KEY"]
        self.assertEqual(prepare_argv(context(p))[0], "codex")

    def test_10_doctor_no_mocked_isolation_pass(self):
        instance = CodexCliLocalAdapter()
        response = instance.doctor(profile())
        self.assertEqual(response["status"], "BLOCKED")
        self.assertEqual(response["reason_code"], "SANDBOX_UNAVAILABLE")
        self.assertEqual(response["profile_validation"], "PASS")
        broken = profile();broken["kind"] = "OTHER"
        self.assertEqual(instance.doctor(broken)["reason_code"], "SANDBOX_POLICY_FAILURE")

    def test_11_no_host_fallback_when_sandbox_unavailable(self):
        instance = CodexCliLocalAdapter()
        c = context(); argv = instance.prepare_invocation(c)
        with mock.patch("subprocess.Popen", side_effect=AssertionError("host spawned")) as popen, \
             mock.patch("subprocess.run", side_effect=AssertionError("host spawned")) as runner, \
             mock.patch("os.system", side_effect=AssertionError("host spawned")) as system:
            r = instance.execute(argv, {"run_context": c, "sandbox_profile": {"backend": "ROOTLESS_PODMAN"}})
        self.assertEqual(r, {"status": "BLOCKED", "reason_code": "SANDBOX_UNAVAILABLE"})
        popen.assert_not_called();runner.assert_not_called();system.assert_not_called()
        self.assertIn("execute-current", build_parser().format_help())

    def test_12_execute_rejects_injection_before_runner_call(self):
        runner = RecordingSandboxStub();adapter = CodexCliLocalAdapter(runner)
        c = context(); argv = prepare_argv(c)
        cases = [
            (argv + [";", "touch", "/tmp/evil"], {"run_context": c}),
            ("codex exec --prompt-file /tmp/p", {"run_context": c}),
            (argv, {"run_context": c, "shell": True}),
            (argv, {"run_context": c, "host_env": {"HOME": "/home/user"}}),
            (argv, {"run_context": c, "secret_values": {"KEY": "raw"}}),
            (argv, {"run_context": c, "argv": ["sh", "-c", "id"]}),
            (argv, {}),
        ]
        for invocation, extra in cases:
            with self.subTest(extra=extra):
                result = adapter.execute(invocation, {"sandbox_profile": {}, **extra})
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["reason_code"], "SANDBOX_POLICY_FAILURE")
        self.assertEqual(runner.requests, [])

    def test_13_only_sandbox_runner_receives_prepared_list(self):
        stub = RecordingSandboxStub()
        adapter = CodexCliLocalAdapter(stub);c = context()
        argv = adapter.prepare_invocation(c)
        output = adapter.execute(argv, {"run_context": c, "sandbox_profile": {"backend": "ROOTLESS_PODMAN"},
                                        "network_mode": "NONE"})
        self.assertEqual(output["exit_code"], 17)
        self.assertEqual(stub.requests[0]["argv"], argv)
        self.assertEqual(stub.requests[0]["stdin_mode"], "CLOSED")
        self.assertEqual(len(stub.requests), 1)

    def test_14_unverified_or_mismatched_backend_does_not_dispatch(self):
        for health in ({"status": "PASS", "backend": "ROOTLESS_PODMAN"},
                       {"status": "PASS", "backend": "DOCKER", "isolation_verified": True},
                       {"status": "UNKNOWN", "backend": "ROOTLESS_PODMAN", "isolation_verified": True},
                       {"status": "PASS", "backend": "ROOTLESS_PODMAN", "isolation_verified": "true"}):
            stub = RecordingSandboxStub(health)
            adapter = CodexCliLocalAdapter(stub);c = context()
            with self.subTest(health=health):
                response = adapter.execute(prepare_argv(c), {"run_context": c, "sandbox_profile": {}})
                self.assertEqual(response["reason_code"], "SANDBOX_UNAVAILABLE")
                self.assertEqual(stub.requests, [])

    def test_15_nonzero_timeout_flood_and_backend_failure_mapping(self):
        adapter = CodexCliLocalAdapter()
        for original, reason in (
            ({"termination_reason": "EXITED", "exit_code": 17}, "EXECUTOR_EXIT_NONZERO"),
            ({"termination_reason": "TIMED_OUT", "exit_code": None}, "EXECUTOR_TIMEOUT"),
            ({"termination_reason": "EXITED", "exit_code": 0, "output_limit_exceeded": True}, "OUTPUT_LIMIT_EXCEEDED"),
            ({"termination_reason": "SANDBOX_UNAVAILABLE", "exit_code": None}, "SANDBOX_UNAVAILABLE"),
            ({"termination_reason": "SIGNALED", "exit_code": -9}, "EXECUTOR_EXIT_NONZERO"),
            ({"termination_reason": "EXITED", "exit_code": False}, "RESULT_INVALID"),
            ({"termination_reason": "WHAT", "exit_code": 0}, "SANDBOX_POLICY_FAILURE"),
            ({"termination_reason": "EXITED", "exit_code": 0, "reason_code": "SECRET_LEAK_DETECTED"}, "SECRET_LEAK_DETECTED"),
        ):
            with self.subTest(original=original), tempfile.TemporaryDirectory() as temp:
                result = adapter.normalize_result(original, Path(temp))
                self.assertEqual(result["reason_code"], reason)
                self.assertFalse(result["result_validated"])
                self.assertNotIn(result["status"], {"SUCCEEDED", "COMPLETED", "PASS"})

    def test_16_missing_malformed_and_oversized_output(self):
        adapter = CodexCliLocalAdapter(); exited = {"termination_reason": "EXITED", "exit_code": 0}
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp); output = d / "agent-result.json"
            self.assertEqual(adapter.normalize_result(exited, d)["reason_code"], "RESULT_MISSING")
            output.write_text('{"bad":', encoding="utf-8")
            self.assertEqual(adapter.normalize_result(exited, d)["reason_code"], "RESULT_INVALID")
            output.write_bytes(b"X" * (1024 * 1024 + 1))
            self.assertEqual(adapter.normalize_result(exited, d)["reason_code"], "RESULT_INVALID")

    def test_16b_symlink_output_rejected(self):
        from tests.platform_capabilities import symlink_or_skip
        adapter = CodexCliLocalAdapter(); exited = {"termination_reason": "EXITED", "exit_code": 0}
        with tempfile.TemporaryDirectory() as temp:
            d = Path(temp); output = d / "agent-result.json"
            target = d / "untrusted.json";target.write_text("{}", encoding="utf-8")
            symlink_or_skip(self, output, target)
            self.assertEqual(adapter.normalize_result(exited, d)["reason_code"], "RESULT_INVALID")

    def test_17_exit_zero_does_not_trust_agents_claim(self):
        adapter = CodexCliLocalAdapter()
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)
            (d / "agent-result.json").write_text('{"status": "COMPLETED", "test": "PASS"}', encoding="utf-8")
            result = adapter.normalize_result({"termination_reason": "EXITED", "exit_code": 0,
                                               "status": "SUCCEEDED", "stdout": "Secret-XXX"}, d)
            self.assertEqual(result["status"], "PENDING_RESULT_VALIDATION")
            self.assertFalse(result["result_validated"])
            self.assertNotIn("stdout", result)
            self.assertNotIn("Secret-XXX", str(result))

    def test_18_fake_scenarios_are_available_for_later_podman(self):
        manifest = json.loads((ROOT / "tests/fixtures/PH_051_02_FAKE_CODEX_CASES.json").read_text())
        expected={"success", "exit_nonzero", "timeout", "missing_output", "invalid_output",
                  "output_flood", "child_process", "control_write", "wrong_paths", "secret_echo",
                  "secret_product", "secret_result", "baseline_drift"}
        self.assertEqual(set(manifest["scenarios"]), expected)
        self.assertIn("NEVER_HOST_AUTO_RUN", manifest["execution_boundary"])
        spec = importlib.util.spec_from_file_location("fake_codex_cli", FAKE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.SCENARIOS, expected)
        candidate = module.agent_result("RUN-TEST-001@1", "TSK-TEST-001")
        self.assertEqual(candidate["status"], "COMPLETED")
        self.assertEqual(candidate["run_ref"], "RUN-TEST-001@1")

    def test_19_fake_success_is_pure_inprocess_test_double_only(self):
        spec = importlib.util.spec_from_file_location("fake_codex_cli", FAKE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);work=d/"product";ctrl=d/"control";ctrl.mkdir()
            result=d/"output"/"agent-result.json"
            with mock.patch("subprocess.Popen", side_effect=AssertionError("host spawn forbidden")) as popen:
                code=module.run_case("success", workspace=work, control=ctrl, result=result,
                                     run_id="RUN-TEST-001@1", task_id="TSK-TEST-001")
            self.assertEqual(code,0);popen.assert_not_called()
            self.assertEqual((work/"implemented.txt").read_text(), "deterministic fixture output\n")
            self.assertEqual(json.loads(result.read_text())["status"], "COMPLETED")
            adapter_result=CodexCliLocalAdapter().normalize_result(
                {"termination_reason":"EXITED","exit_code":0}, result.parent)
            self.assertEqual(adapter_result["status"], "PENDING_RESULT_VALIDATION")
            self.assertFalse(adapter_result["result_validated"])

    def test_21_fake_failure_fixture_matrix_without_host_spawn(self):
        spec=importlib.util.spec_from_file_location("fake_codex_cli",FAKE)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp);control=d/"control";control.mkdir()
            with mock.patch("subprocess.Popen", side_effect=AssertionError("host CLI spawned")) as popen:
                for scenario in ("exit_nonzero", "missing_output", "invalid_output",
                                 "wrong_paths", "baseline_drift", "secret_echo", "secret_product",
                                 "secret_result", "control_write"):
                    work=d/scenario/"product";out=d/scenario/"output"/"agent-result.json"
                    output=io.StringIO()
                    with self.subTest(scenario=scenario), mock.patch.dict(os.environ, {"FAKE_CLI_SECRET":"TEST-SENTINEL-ONLY"}), contextlib.redirect_stdout(output):
                        code=module.run_case(scenario, workspace=work, control=control,
                                             result=out, run_id="RUN-TEST-001@1", task_id="TSK-TEST-001")
                        self.assertEqual(code,17 if scenario=="exit_nonzero" else 0)
                        self.assertEqual(out.exists(), scenario not in {"exit_nonzero","missing_output"})
                        if scenario=="invalid_output":
                            with self.assertRaises(json.JSONDecodeError):json.loads(out.read_text())
                        elif scenario in {"wrong_paths","baseline_drift", "secret_echo", "secret_product", "secret_result"}:
                            candidate=json.loads(out.read_text())
                            self.assertEqual(candidate["run_ref"], "RUN-TEST-001@1")
                    if scenario=="wrong_paths":
                        self.assertTrue((work/"outside_allowed.txt").exists())
                    if scenario=="secret_echo":
                        self.assertIn("TEST-SENTINEL-ONLY",output.getvalue())
                    if scenario=="secret_product":
                        self.assertIn("TEST-SENTINEL-ONLY",(work/"implemented.txt").read_text())
                    if scenario=="secret_result":
                        self.assertIn("TEST-SENTINEL-ONLY",out.read_text())
                popen.assert_not_called()
                # This directory is *not isolated*; the fixture must prove the
                # attack is attempted, not misrepresent that Podman has passed.
                self.assertTrue((control/"illicit.txt").exists())

    def test_22_untrusted_unused_binding_and_unsafe_literal_file(self):
        c=context();c["context_packet_path"]="/home/operator/host.ini"
        with self.assertRaises(ValidationFailure):
            prepare_argv(c)
        for literal in ("/etc/passwd", "@/etc/shadow"):
            with self.subTest(literal=literal),self.assertRaises(ValidationFailure):
                prepare_argv(context(profile(["codex","exec",literal])))

    def test_23_malformed_sandbox_process_envelopes_are_bounded(self):
        adapter=CodexCliLocalAdapter()
        with tempfile.TemporaryDirectory() as temp:
            for bad in ({"exit_code":0,"termination_reason":"EXITED","reason_code":[]},
                        {"exit_code":0,"termination_reason":{}},
                        {"exit_code":0,"termination_reason":None},
                        {"exit_code":0,"termination_reason":"EXITED","reason_code":"MADE_UP"}):
                with self.subTest(bad=bad):
                    actual=adapter.normalize_result(bad,Path(temp))
                    self.assertEqual(actual["reason_code"],"SANDBOX_POLICY_FAILURE")
                    self.assertFalse(actual["result_validated"])

    def test_24_sandbox_errors_fail_closed(self):
        class BrokenRunner(RecordingSandboxStub):
            def run(self, request):
                raise OSError("container failure")
        runner=BrokenRunner(); adapter=CodexCliLocalAdapter(runner);c=context()
        outcome=adapter.execute(prepare_argv(c),{"run_context":c,"sandbox_profile":{}})
        self.assertEqual(outcome["reason_code"],"SANDBOX_UNAVAILABLE")
        self.assertFalse(runner.requests)

    def test_20_imports_have_no_os_process_primitive(self):
        base = ROOT / "src/project_harness/executors"
        for filename in ("__init__.py", "base.py", "codex_cli_local.py", "result.py"):
            tree = ast.parse((base / filename).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertFalse(any(alias.name.startswith("subprocess") for alias in node.names))
                if isinstance(node, ast.ImportFrom):
                    self.assertNotEqual(node.module, "subprocess")
                if isinstance(node, ast.Call):
                    self.assertNotIn(ast.unparse(node.func), {"subprocess.run", "subprocess.Popen", "os.system", "Popen"})


if __name__ == "__main__":
    unittest.main()

"""PH-051-05: exact ADP/SBX binding, JIT argv and fail-closed Podman dispatch.

No fake CLI is spawned on host. Only the opt-in real integration test can
execute it, inside an already provisioned rootless Podman digest-pinned image.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from project_harness.errors import ValidationFailure
from project_harness.executors.codex_cli_local import (
    CodexCliLocalAdapter, load_active_codex_profiles, prepare_argv,
)
from project_harness.hashing import sha256_file
from project_harness.project_input import DEFAULT_EXECUTION_POLICY
from project_harness.sandbox import RootlessPodmanRunner
from project_harness.serialization import load_data, write_data
from project_harness.workspace import check_control_plane, record_phase_boundary
from project_harness.util import utc_now
from tests.test_engine import prepare_demo
from tests.test_ph_051_03_rootless_podman import profile as sandbox_profile, dirs

ROOT = Path(__file__).resolve().parents[1]
FAKE = ROOT / "tests/fixtures/fake_codex_cli.py"
ADP = "ADP-CODEX-CLI-LOCAL-001@1"
SBX = "SBX-ROOTLESS-PODMAN-001@1"


def local_profile(*, executable="codex", template=None, timeout=150):
    return {"agent_adapter_profile": {
        "id": ADP.split("@")[0], "revision": 1, "status": "ACTIVE",
        "kind": "CODEX_CLI_LOCAL", "executable": executable,
        "argv_template": template if template is not None else [
            executable, "exec", "--prompt-file", "{prompt_bundle_path}",
            "--result-file", "{agent_result_path}",
        ],
        "working_directory": "/workspace/product", "timeout_seconds": timeout,
        "stdin_mode": "CLOSED", "environment_allowlist": ["LANG", "LC_ALL"],
        "secret_environment_refs": [], "sandbox_profile_ref": SBX,
    }}


def install_profiles(root: Path, *, manual=False, adp=None, sbx=None):
    """Isolated test records; not a real user approval or policy migration."""
    adp = deepcopy(adp if adp is not None else local_profile())
    sbx = deepcopy(sbx if sbx is not None else sandbox_profile())
    for folder, ref, record in (("ADAPTERS", ADP, adp), ("SANDBOXES", SBX, sbx)):
        dest = root / ".harness/config" / folder / (ref + ".yaml")
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_data(dest, record)
    bindings = {
        "adapter": {"ref": ADP, "digest": "sha256:" + sha256_file(root / ".harness/config/ADAPTERS" / (ADP + ".yaml"))},
        "sandbox": {"ref": SBX, "digest": "sha256:" + sha256_file(root / ".harness/config/SANDBOXES" / (SBX + ".yaml"))},
    }
    policy = dict(DEFAULT_EXECUTION_POLICY) if manual else {
        "mode": "LOCAL_AUTOMATIC", "adapter_profile_ref": ADP,
        "sandbox_profile_ref": SBX, "network_mode": "NONE",
        "completion_policy": "EXPLICIT_AFTER_VERIFICATION",
    }
    lock_path = root / ".harness/config/PROJECT_LOCK.yaml"
    previous = load_data(lock_path) if lock_path.exists() else {"project_lock": {}}
    previous["project_lock"].update(execution=policy, execution_profile_bindings=bindings)
    write_data(lock_path, previous)
    return bindings


class ExactActiveProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ph05105-profile-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "canonical"
        self.root.mkdir()
        self.bindings = install_profiles(self.root)

    def test_01_load_two_exact_project_profiles_with_pinned_digests(self):
        loaded = load_active_codex_profiles(self.root)
        self.assertEqual(loaded["profile_bindings"], self.bindings)
        self.assertEqual(loaded["adapter_profile"]["executable"], "codex")
        self.assertEqual(loaded["sandbox_profile"]["backend"], "ROOTLESS_PODMAN")
        adapter = CodexCliLocalAdapter.from_project(self.root)
        self.assertIs(type(adapter._sandbox_runner), RootlessPodmanRunner)
        self.assertEqual(adapter._sandbox_runner._configured_executable, "codex")
        self.assertEqual(adapter._bound["profile_bindings"], self.bindings)

    def test_02_manual_mode_cannot_activate_even_with_valid_profiles(self):
        install_profiles(self.root, manual=True)
        with self.assertRaises(ValidationFailure):
            CodexCliLocalAdapter.from_project(self.root)

    def test_03_lock_digest_or_revision_mismatch_rejects(self):
        path = self.root / ".harness/config/ADAPTERS" / (ADP + ".yaml")
        path.write_text(path.read_text() + "\n", encoding="utf-8")
        with self.assertRaises(ValidationFailure):
            load_active_codex_profiles(self.root)
        install_profiles(self.root)
        lock = self.root / ".harness/config/PROJECT_LOCK.yaml"
        record = load_data(lock)
        record["project_lock"]["execution_profile_bindings"]["adapter"]["ref"] = "ADP-OTHER@1"
        write_data(lock, record)
        with self.assertRaises(ValidationFailure):
            load_active_codex_profiles(self.root)

    def test_04_profile_identity_status_and_sandbox_ref_rejected(self):
        for field, bad_value in (("status", "VALIDATED"), ("kind", "HTTP_REMOTE"),
                                 ("revision", 2), ("sandbox_profile_ref", "SBX-OTHER@1")):
            with self.subTest(field=field):
                altered = local_profile()
                altered["agent_adapter_profile"][field] = bad_value
                install_profiles(self.root, adp=altered)
                with self.assertRaises(ValidationFailure):
                    CodexCliLocalAdapter.from_project(self.root)

    def test_05_symlink_profile_denied(self):
        from tests.platform_capabilities import symlink_or_skip
        path = self.root / ".harness/config/ADAPTERS" / (ADP + ".yaml")
        original = path.read_bytes()
        path.unlink()
        external = Path(self.temp.name) / "external.yaml"
        external.write_bytes(original)
        symlink_or_skip(self, path, external)
        with self.assertRaises(ValidationFailure):
            load_active_codex_profiles(self.root)

    def test_05b_hardlink_profile_denied(self):
        path = self.root / ".harness/config/ADAPTERS" / (ADP + ".yaml")
        original = path.read_bytes()
        path.unlink()
        external = Path(self.temp.name) / "external.yaml"
        external.write_bytes(original)
        os.link(external, path)
        with self.assertRaises(ValidationFailure):
            load_active_codex_profiles(self.root)

    def test_06_network_egress_rejected_before_podman(self):
        lock = self.root / ".harness/config/PROJECT_LOCK.yaml"
        value = load_data(lock)
        value["project_lock"]["execution"]["network_mode"] = "EXPLICIT_APPROVED_EGRESS"
        write_data(lock, value)
        with self.assertRaises(ValidationFailure):
            CodexCliLocalAdapter.from_project(self.root)

    def test_07_no_host_codex_when_podman_missing(self):
        adapter = CodexCliLocalAdapter.from_project(self.root)
        with mock.patch.object(adapter._sandbox_runner, "_podman", return_value=None), \
             mock.patch("os.geteuid", return_value=1001), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("host cli spawned")) as spawn:
            outcome = adapter.doctor(adapter._bound["adapter_profile"])
        self.assertEqual(outcome["status"], "BLOCKED")
        self.assertEqual(outcome["reason_code"], "SANDBOX_UNAVAILABLE")
        spawn.assert_not_called()
        self.assertIn("execute-current", __import__("project_harness.cli", fromlist=["build_parser"]).build_parser().format_help())

    def test_08_missing_secret_reference_blocks_before_podman_and_allowlist_supported(self):
        p=local_profile();p["agent_adapter_profile"]["secret_environment_refs"]=["ENV:FAKE_CLI_SECRET"]
        install_profiles(self.root, adp=p)
        adapter=CodexCliLocalAdapter.from_project(self.root)
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(adapter._sandbox_runner,"doctor",side_effect=AssertionError("secret missing; no Podman")):
            actual=adapter.doctor(adapter._bound["adapter_profile"])
            self.assertEqual(actual["reason_code"], "SECRET_REFERENCE_MISSING")
        p=local_profile();p["agent_adapter_profile"]["environment_allowlist"]=["LANG","LC_ALL","TZ"]
        install_profiles(self.root, adp=p)
        adapter=CodexCliLocalAdapter.from_project(self.root)
        with mock.patch.object(adapter._sandbox_runner,"doctor",return_value={
                "status":"BLOCKED","backend":"ROOTLESS_PODMAN","reason_code":"SANDBOX_UNAVAILABLE",
                "isolation_verified":False}):
            actual=adapter.doctor(adapter._bound["adapter_profile"])
            self.assertEqual(actual["reason_code"], "SANDBOX_UNAVAILABLE")

    def test_09_cannot_call_execute_from_raw_invocation_instead_of_jit(self):
        adapter = CodexCliLocalAdapter.from_project(self.root)
        c = {"adapter_profile": adapter._bound["adapter_profile"],
             "prompt_bundle_path": "/workspace/control/prompt-bundle.md",
             "context_packet_path": "/workspace/control/context-packet.json",
             "agent_result_path": "/output/agent-result.json", "workspace_path": "/workspace/product",
             "run_id": "RUN-TEST", "task_id": "TSK-TEST"}
        argv = prepare_argv(c)
        with mock.patch.object(adapter._sandbox_runner, "doctor", side_effect=AssertionError("unprepared invocation")):
            outcome = adapter.execute(argv, {"run_context": c, "sandbox_profile": adapter._bound["sandbox_profile"]})
        self.assertEqual(outcome["reason_code"], "SANDBOX_POLICY_FAILURE")

    def test_10_doctor_requires_complete_attestation(self):
        adapter = CodexCliLocalAdapter.from_project(self.root)
        for incomplete in ({"status": "PASS", "backend": "ROOTLESS_PODMAN", "isolation_verified": True},
                           {"status": "PASS", "backend": "ROOTLESS_PODMAN", "isolation_verified": True,
                            "network_mode": "NONE", "checks": {"network": "UNKNOWN"}}):
            with self.subTest(incomplete=incomplete), mock.patch.object(adapter._sandbox_runner, "doctor", return_value=incomplete):
                self.assertEqual(adapter.doctor(adapter._bound["adapter_profile"])["reason_code"], "SANDBOX_UNAVAILABLE")


class PreparedJitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ph05105-jit-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = prepare_demo(self.base / "build")[2]
        self.runtime = self.base / "runtime-external"
        install_profiles(self.root)
        # This synthetic *test fixture* re-seals a changed lock as a new
        # signed boundary; this is NOT a supported user activation/approval.
        self.active = load_data(self.root / ".harness/state/CURRENT_STATE.yaml")["state"]["active_run"]
        record_phase_boundary(self.root, self.active, phase="TEST_FIXTURE_ONLY",
                              kernel_written_paths=[".harness/config/PROJECT_LOCK.yaml",
                                                    ".harness/config/ADAPTERS/" + ADP + ".yaml",
                                                    ".harness/config/SANDBOXES/" + SBX + ".yaml"],
                              recorded_at=utc_now())
        self.assertEqual(check_control_plane(self.root, self.active)["status"], "PASS")

    def test_11_exact_active_jit_paths_task_and_bounded_timeout(self):
        adapter = CodexCliLocalAdapter.from_project(self.root)
        prepared = adapter.prepare_current_run(self.runtime)
        self.assertEqual(prepared["status"], "PREPARED")
        req = prepared["sandbox_request"]
        self.assertEqual(prepared["run_ref"], self.active["run_ref"])
        self.assertEqual(req["run_context"]["task_id"], self.active["task_ref"])
        self.assertEqual(req["run_context"]["prompt_bundle_path"], "/workspace/control/prompt-bundle.md")
        self.assertEqual(req["run_context"]["context_packet_path"], "/workspace/control/context-packet.json")
        self.assertEqual(req["run_context"]["agent_result_path"], "/output/agent-result.json")
        self.assertEqual(req["timeout_seconds"], 150)
        self.assertEqual(prepared["invocation"][-1], "/output/agent-result.json")
        self.assertFalse((Path(req["product_dir"]) / ".harness").exists())
        self.assertFalse((Path(req["output_dir"]) / "agent-result.json").exists())
        self.assertEqual(adapter.prepare_current_run(self.runtime)["invocation"], prepared["invocation"])
        with mock.patch.object(adapter._sandbox_runner, "doctor", return_value={
            "status": "BLOCKED", "backend": "ROOTLESS_PODMAN",
            "isolation_verified": False, "reason_code": "SANDBOX_UNAVAILABLE"
        }), mock.patch("subprocess.Popen", side_effect=AssertionError("no host CLI")) as spawn:
            response = adapter.execute(prepared["invocation"], req)
        self.assertEqual(response["reason_code"], "SANDBOX_UNAVAILABLE")
        spawn.assert_not_called()
        self.assertEqual(list(Path(req["output_dir"]).iterdir()), [])

    def test_12_tamper_or_base_drift_blocks_without_doctor_or_launch(self):
        adapter = CodexCliLocalAdapter.from_project(self.root)
        prepared = adapter.prepare_current_run(self.runtime)
        (self.root / "base-drift.txt").write_text("changed", encoding="utf-8")
        with mock.patch.object(adapter._sandbox_runner, "doctor", side_effect=AssertionError("cannot launch stale run")):
            r = adapter.execute(prepared["invocation"], prepared["sandbox_request"])
        self.assertEqual(r["status"], "BLOCKED")
        self.assertEqual(r["reason_code"], "SANDBOX_POLICY_FAILURE")

    def test_13_template_change_or_request_override_blocks(self):
        adapter = CodexCliLocalAdapter.from_project(self.root)
        prepared = adapter.prepare_current_run(self.runtime)
        bad_request = deepcopy(prepared["sandbox_request"])
        bad_request["timeout_seconds"] = 300
        for argv, req in ((prepared["invocation"], bad_request),
                          (prepared["invocation"] + ["--unsafe"], prepared["sandbox_request"]),
                          (prepared["invocation"], {**prepared["sandbox_request"], "shell": True})):
            with self.subTest(argv=argv), mock.patch.object(adapter._sandbox_runner, "doctor", side_effect=AssertionError("unsafe")):
                r = adapter.execute(argv, req)
                self.assertEqual(r["reason_code"], "SANDBOX_POLICY_FAILURE")

    def test_14_bounded_failures_never_become_agent_pass(self):
        adapter = CodexCliLocalAdapter.from_project(self.root)
        with tempfile.TemporaryDirectory() as output:
            for raw, reason in (({"termination_reason":"EXITED", "exit_code":19}, "EXECUTOR_EXIT_NONZERO"),
                                ({"termination_reason":"TIMED_OUT", "exit_code":None}, "EXECUTOR_TIMEOUT"),
                                ({"termination_reason":"OUTPUT_LIMIT_EXCEEDED", "exit_code":-9,
                                  "reason_code":"OUTPUT_LIMIT_EXCEEDED"}, "OUTPUT_LIMIT_EXCEEDED"),
                                ({"termination_reason":"EXITED", "exit_code":0}, "RESULT_MISSING")):
                with self.subTest(reason=reason):
                    outcome = adapter.normalize_result(raw, Path(output))
                    self.assertEqual(outcome["reason_code"], reason)
                    self.assertFalse(outcome["result_validated"])


class RealRootlessIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("PH_TEST_PODMAN_IMAGE") and shutil.which("podman") and os.geteuid() != 0,
                         "NOT RUN: real non-root Podman and pinned PH_TEST_PODMAN_IMAGE required")
    def test_15_fake_codex_in_real_rootless_podman_not_on_host(self):
        """Only this test launches fake CLI, and exclusively via Podman process."""
        image = os.environ["PH_TEST_PODMAN_IMAGE"]
        with tempfile.TemporaryDirectory(prefix="ph05105-real-") as tmp:
            paths = dirs(Path(tmp))
            (paths["product_dir"] / "fake_codex_cli.py").write_bytes(FAKE.read_bytes())
            (paths["control_dir"] / "prompt-bundle.md").write_text("task", encoding="utf-8")
            sbx = sandbox_profile()
            sbx["sandbox_profile"]["image"] = image
            exe = "python3"
            adp = local_profile(executable=exe, template=[
                exe, "-m", "fake_codex_cli", "--scenario", "success",
                "--workspace-path", "{workspace_path}", "--control-path", "{prompt_bundle_path}",
                "--result-file", "{agent_result_path}", "--run-id", "{run_id}",
                "--task-id", "{task_id}",
            ])
            c = {"adapter_profile": adp, "prompt_bundle_path": "/workspace/control/prompt-bundle.md",
                 "context_packet_path": "/workspace/control/context-packet.json",
                 "agent_result_path": "/output/agent-result.json", "workspace_path": "/workspace/product",
                 "run_id": "RUN-TEST-001", "task_id": "TSK-TEST-001"}
            adapter = CodexCliLocalAdapter(RootlessPodmanRunner(configured_executable=exe))
            request = {**paths, "run_context": c, "sandbox_profile": sbx,
                       "stdin_mode": "CLOSED", "network_mode": "NONE", "timeout_seconds": 15}
            raw = adapter.execute(adapter.prepare_invocation(c), request)
            self.assertEqual(raw.get("termination_reason"), "EXITED", raw)
            self.assertEqual(raw.get("exit_code"), 0, raw)
            pending = adapter.normalize_result(raw, paths["output_dir"])
            self.assertEqual(pending["status"], "PENDING_RESULT_VALIDATION")
            self.assertFalse(pending["result_validated"])
            self.assertTrue((paths["product_dir"] / "implemented.txt").exists())
            self.assertFalse((paths["canonical_project_root"] / "implemented.txt").exists())


if __name__ == "__main__":
    unittest.main()

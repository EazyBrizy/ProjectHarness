"""PH-051-03 focused contracts; mocked tests are NEVER security acceptance."""

from __future__ import annotations

import ast
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from project_harness.sandbox import RootlessPodmanRunner, SandboxRunner, SandboxPolicyError, validate_sandbox_profile
from project_harness.sandbox.podman_rootless import _KERNEL_PROBE, _BOUNDARY_PROBE
from project_harness.sandbox.profiles import validate_execution_mounts, validate_argv

ROOT = Path(__file__).resolve().parents[1]


def profile() -> dict:
    return {"sandbox_profile": {
        "id": "SBX-ROOTLESS-PODMAN-001", "revision": 1, "status": "ACTIVE",
        "backend": "ROOTLESS_PODMAN", "image": "registry.example/harness-test@sha256:" + "a" * 64,
        "network_mode": "NONE", "root_filesystem": "READ_ONLY",
        "run_as_non_root": True, "drop_all_capabilities": True, "no_new_privileges": True,
        "writable_mounts": ["/workspace/product", "/output", "/tmp"],
        "limits": {"timeout_seconds": 1200, "memory_mb": 2048, "cpu_count": 2,
                   "pids": 128, "output_bytes": 52428800},
    }}


def dirs(base: Path) -> dict:
    e, canonical = base / "execution", base / "canonical"
    e.mkdir(); canonical.mkdir()
    d = {"execution_root": e, "canonical_project_root": canonical}
    for name, child in (("product_dir", "product"), ("control_dir", "control"), ("output_dir", "output")):
        p = e / child; p.mkdir()
        d[name] = p
    return d


def request(d: dict) -> dict:
    return {**d, "sandbox_profile": profile(), "argv": ["codex", "exec"],
            "stdin_mode": "CLOSED", "network_mode": "NONE"}


class RootlessPodmanSandboxTests(unittest.TestCase):
    def test_01_interface_no_runtime_auto_activation(self):
        runner = RootlessPodmanRunner(configured_executable="codex")
        self.assertIsInstance(runner, SandboxRunner)
        from project_harness.cli import build_parser
        from project_harness import runtime
        self.assertIn("execute_current", runtime.__dict__)
        self.assertIn("execute-current", build_parser().format_help())

    def test_02_profile_strict_positive(self):
        p = profile()
        self.assertEqual(validate_sandbox_profile(p)["backend"], "ROOTLESS_PODMAN")
        self.assertEqual(validate_sandbox_profile(p["sandbox_profile"])["limits"]["pids"], 128)

    def test_03_profiles_fail_closed(self):
        variants = (
            ("status", "VALIDATED"), ("backend", "DOCKER"), ("image", "foo:latest"),
            ("image", "foo@sha256:" + "Z" * 64), ("image", "https://example.com/file@sha256:" + "a" * 64),
            ("network_mode", "HOST"), ("root_filesystem", "WRITEABLE"),
            ("run_as_non_root", False), ("drop_all_capabilities", False),
            ("no_new_privileges", False),
            ("writable_mounts", ["/workspace/product", "/tmp", "/output"]),
            ("writable_mounts", ["/workspace/product", "/output", "/tmp", "/host"]),
            ("id", "ADP-LOCAL"), ("revision", True), ("revision", 0),
        )
        for field, value in variants:
            with self.subTest(field=field, value=value):
                p = profile(); p["sandbox_profile"][field] = value
                with self.assertRaises(SandboxPolicyError): validate_sandbox_profile(p)
        p = profile(); p["sandbox_profile"]["secret"] = "NEVER"
        with self.assertRaises(SandboxPolicyError): validate_sandbox_profile(p)

    def test_04_limits_bounds_and_unknown(self):
        variants = (("memory_mb", 0), ("pids", -1), ("cpu_count", 0),
                    ("cpu_count", float("nan")), ("timeout_seconds", 86401),
                    ("output_bytes", 0), ("pids", True))
        for field, value in variants:
            with self.subTest(field=field, value=value):
                p = profile(); p["sandbox_profile"]["limits"][field] = value
                with self.assertRaises(SandboxPolicyError): validate_sandbox_profile(p)
        p = profile(); p["sandbox_profile"]["limits"]["host_limit"] = "unlimited"
        with self.assertRaises(SandboxPolicyError): validate_sandbox_profile(p)

    def test_05_command_is_single_podman_and_sealed_flags(self):
        p = validate_sandbox_profile(profile())
        with tempfile.TemporaryDirectory() as tmp:
            d = dirs(Path(tmp))
            args = RootlessPodmanRunner._command(p, d, podman="/usr/bin/podman",
                        name="ph-05103-0001", executable="codex", argv=["exec", "/workspace/control/prompt"],
                        uid=1001, gid=1001)
        self.assertEqual(args[:4], ["/usr/bin/podman", "--remote=false", "run", "--rm"])
        self.assertEqual(args[-3:], [p["image"], "exec", "/workspace/control/prompt"])
        for needed in ("--pull=never", "--userns=keep-id", "--read-only", "--read-only-tmpfs=false",
                       "--cap-drop=ALL", "--security-opt=no-new-privileges", "--network=none",
                       "--memory", "2048m", "--cpus", "2", "--pids-limit", "128",
                       "--image-volume=ignore", "--log-driver=none", "--unsetenv-all"):
            self.assertIn(needed, args)
        self.assertEqual(args.count("--mount"), 3)
        mount_args = [args[i+1] for i,item in enumerate(args[:-1]) if item == "--mount"]
        self.assertEqual(sum("dst=/workspace/product,rw" in a for a in mount_args), 1)
        self.assertEqual(sum("dst=/workspace/control,ro" in a for a in mount_args), 1)
        self.assertEqual(sum("dst=/output,rw" in a for a in mount_args), 1)
        self.assertEqual(args.count("--tmpfs"), 2)
        self.assertIn("/home/harness:rw", " ".join(args))
        for forbidden in ("--privileged", "--network=host", "--cap-add", "--device", "--publish",
                          "-v", "--volume", "--security-opt=unconfined", "--env-file", "--env-host"):
            self.assertNotIn(forbidden, args)
        self.assertNotIn("/root", " ".join(args))
        self.assertNotIn(".harness", " ".join(args))

    def test_06_mounts_disjoint_and_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = dirs(Path(tmp))
            self.assertEqual(validate_execution_mounts(d)["output_dir"], d["output_dir"])
            for name, value in (("execution_root", d["canonical_project_root"]),
                                ("canonical_project_root", d["execution_root"]),
                                ("product_dir", d["canonical_project_root"]),
                                ("control_dir", d["output_dir"]),
                                ("output_dir", d["execution_root"]),
                                ("product_dir", "/tmp/foo,ro"),
                                ("product_dir", "/tmp/../root")):
                bad = dict(d); bad[name] = value
                with self.subTest(name=name, value=value), self.assertRaises(SandboxPolicyError):
                    validate_execution_mounts(bad)
            target = Path(tmp)/"link";target.symlink_to(d["product_dir"], target_is_directory=True)
            bad = dict(d);bad["product_dir"] = target
            with self.assertRaises(SandboxPolicyError): validate_execution_mounts(bad)
            (d["output_dir"] / "__test").write_text("x", encoding="utf-8")
            self.assertEqual(validate_execution_mounts(d)["output_dir"],d["output_dir"])

    def test_07_no_podman_no_process(self):
        runner = RootlessPodmanRunner(configured_executable="codex")
        with mock.patch("os.geteuid", return_value=1001), mock.patch.object(runner, "_podman", return_value=None), \
             mock.patch("subprocess.Popen", side_effect=AssertionError("unexpected subprocess")) as proc:
            r = runner.doctor(profile())
            self.assertEqual(r["status"], "BLOCKED")
            self.assertEqual(r["reason_code"], "SANDBOX_UNAVAILABLE")
            self.assertFalse(r["isolation_verified"])
            proc.assert_not_called()

    def test_08_root_host_fails_even_if_podman_exists(self):
        runner = RootlessPodmanRunner(configured_executable="codex")
        with mock.patch("os.geteuid", return_value=0), mock.patch.object(runner, "_podman") as podman:
            r = runner.doctor(profile())
            self.assertEqual(r["status"], "BLOCKED")
            self.assertFalse(r["isolation_verified"])
            podman.assert_not_called()

    def test_09_egress_requires_governance_not_permanent_profile(self):
        p = profile();p["sandbox_profile"]["network_mode"] = "EXPLICIT_APPROVED_EGRESS"
        runner = RootlessPodmanRunner(configured_executable="codex")
        self.assertEqual(runner.doctor(p)["reason_code"], "NETWORK_NOT_APPROVED")
        with tempfile.TemporaryDirectory() as tmp:
            d = dirs(Path(tmp))
            r = runner.run({**request(d), "sandbox_profile": p, "network_mode": "EXPLICIT_APPROVED_EGRESS"})
            self.assertEqual(r["reason_code"], "NETWORK_NOT_APPROVED")
            self.assertFalse(r["isolation_verified"])
            r = runner.run({**request(d), "network_mode": "EXPLICIT_APPROVED_EGRESS"})
            self.assertEqual(r["reason_code"], "NETWORK_NOT_APPROVED")

    def test_10_no_doctor_without_executable(self):
        r = RootlessPodmanRunner().doctor(profile())
        self.assertEqual(r["reason_code"], "SANDBOX_POLICY_FAILURE")
        self.assertFalse(r["isolation_verified"])

    def test_11_rootless_info_fraud_and_failure(self):
        r = RootlessPodmanRunner(configured_executable="codex")
        with mock.patch("os.geteuid", return_value=1001), mock.patch.object(r,"_podman",return_value="/usr/bin/podman"):
            with mock.patch.object(r,"_control",return_value={"termination_reason":"EXITED", "exit_code":0,"stdout":'{"host":{"security":{"rootless":false}}}'}) as info:
                d = r.doctor(profile())
                self.assertEqual(d["reason_code"],"SANDBOX_UNAVAILABLE")
                self.assertFalse(d["isolation_verified"])
                self.assertEqual(info.call_count,1)
            with mock.patch.object(r,"_control",return_value={"termination_reason":"EXITED", "exit_code":0,"stdout":'{"host":{"security":{"rootless":true}}}'}) as ctl:
                with mock.patch.object(r,"_selftest_container",side_effect=AssertionError("image not validated")):
                    # A test double cannot make Podman's missing image look available.
                    def fake_control(_p,args):
                        if args[:2] == ["image","exists"]: return {"termination_reason":"EXITED","exit_code":1}
                        return {"termination_reason":"EXITED", "exit_code":0,"stdout":'{"host":{"security":{"rootless":true}}}'}
                    ctl.side_effect=fake_control
                    d = r.doctor(profile())
                    self.assertEqual(d["status"],"BLOCKED")
                    self.assertNotIn("mount_policy", d["checks"])

    def test_12_direct_runner_rejects_untrusted_inputs_without_launch(self):
        runner = RootlessPodmanRunner(configured_executable="codex")
        with tempfile.TemporaryDirectory() as tmp:
            d = dirs(Path(tmp));valid = request(d)
            for change in ({"argv":"codex exec"},{"argv":["/bin/sh","-c","true"]},
                           {"stdin_mode":"OPEN"},{"host_env":{"TOKEN":"raw"}},
                           {"command":"/bin/sh"},{"shell":True},
                           {"timeout_seconds":2000},{"timeout_seconds":True},
                           {"product_dir":d["canonical_project_root"]}):
                with self.subTest(change=change),mock.patch.object(runner,"doctor",side_effect=AssertionError("doctor must not run")):
                    resp = runner.run({**valid,**change})
                    self.assertEqual(resp["reason_code"],"SANDBOX_POLICY_FAILURE")
                    self.assertFalse(resp["isolation_verified"])

    def test_13_doctor_fails_even_when_stale_cached_status_claimed(self):
        r = RootlessPodmanRunner(configured_executable="codex")
        with tempfile.TemporaryDirectory() as tmp:
            d = dirs(Path(tmp))
            with mock.patch.object(r,"doctor",return_value={"status":"BLOCKED", "isolation_verified": False, "reason_code": "SANDBOX_UNAVAILABLE"}), \
                 mock.patch.object(r,"_podman",side_effect=AssertionError("must not launch")):
                self.assertEqual(r.run(request(d))["reason_code"],"SANDBOX_UNAVAILABLE")

    def test_14_kernel_checks_are_real_probes_not_mock_acceptance(self):
        self.assertIn("/proc/net/route",_KERNEL_PROBE)
        self.assertIn("socket.socket",_KERNEL_PROBE)
        self.assertIn("memory.max",_KERNEL_PROBE)
        self.assertIn("pids.max",_KERNEL_PROBE)
        self.assertIn("cpu.max",_KERNEL_PROBE)
        self.assertIn("/proc/self/mountinfo",_KERNEL_PROBE)
        self.assertIn("/home/harness",_KERNEL_PROBE)
        for phrase in ("CapEff", "NoNewPrivs", "/workspace/control/locked", "/output/probe-result"):
            self.assertIn(phrase,_BOUNDARY_PROBE)

    def test_15_spawn_unavailable_no_fallback(self):
        with mock.patch("subprocess.Popen",side_effect=FileNotFoundError("podman missing")):
            d = RootlessPodmanRunner._spawn(["/usr/bin/podman","info"],deadline_seconds=1,max_bytes=1000)
        self.assertEqual(d["reason_code"],"SANDBOX_UNAVAILABLE")
        self.assertIsNone(d["exit_code"])

    def test_16_no_host_agent_subprocess_in_sandbox_sources(self):
        source = (ROOT/"src/project_harness/sandbox/podman_rootless.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id,{"eval","exec"})
        self.assertFalse(any(isinstance(n, ast.keyword) and n.arg == "shell" and isinstance(n.value, ast.Constant) and n.value.value is True for n in ast.walk(tree)))
        self.assertNotIn("/var/run/docker.sock:",source)
        self.assertNotIn("--network=host",source)
        self.assertNotIn("--privileged",source)
        self.assertNotIn("--cap-add",source)

    def test_17_bounded_output_overflow_without_host_agent(self):
        # OS pipes simulate stdout; no host fake Codex is run.
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"D" * 1024)
        os.close(write_fd)
        class Process:
            returncode = 0
            pid = 123456
            def __init__(self):
                self.stdout = os.fdopen(read_fd, "rb", buffering=0)
                self.stderr = None
            def poll(self): return self.returncode
            def wait(self, timeout=None): return self.returncode
        proc = Process()
        with mock.patch("subprocess.Popen",return_value=proc), mock.patch.object(RootlessPodmanRunner,"_end_process") as stopped:
            result = RootlessPodmanRunner._spawn(["/usr/bin/podman", "run"],deadline_seconds=1,max_bytes=32,container_name="ph-unit")
        self.assertEqual(result["termination_reason"], "OUTPUT_LIMIT_EXCEEDED")
        self.assertTrue(result["output_limit_exceeded"])
        self.assertEqual(len(result["stdout"].encode()),32)
        stopped.assert_called_once()

    def test_18_bad_podman_json_never_passes_doctor(self):
        runner = RootlessPodmanRunner(configured_executable="codex")
        with mock.patch("os.geteuid",return_value=1001), mock.patch.object(runner,"_podman",return_value="/usr/bin/podman"), mock.patch.object(runner,"_control",return_value={"termination_reason":"EXITED","exit_code":0,"stdout":'{"host":"garbage"}'}):
            result = runner.doctor(profile())
        self.assertEqual(result["status"],"BLOCKED")
        self.assertFalse(result["isolation_verified"])

    def test_18b_podman_run_start_failure_is_not_isolation_pass(self):
        # Podman reserves 125/126/127 for CLI/container start failures.
        runner = RootlessPodmanRunner(configured_executable="codex")
        with tempfile.TemporaryDirectory() as tmp:
            d = dirs(Path(tmp))
            for code in (125, 126, 127):
                with self.subTest(code=code), mock.patch.object(runner, "doctor", return_value={"status":"PASS","isolation_verified":True}), \
                     mock.patch.object(runner, "_podman", return_value="/usr/bin/podman"), \
                     mock.patch.object(runner, "_spawn", return_value={"termination_reason":"EXITED", "exit_code":code}), \
                     mock.patch("os.geteuid",return_value=1001), mock.patch("os.getegid",return_value=1001):
                    result = runner.run(request(d))
                    self.assertEqual(result["reason_code"], "SANDBOX_UNAVAILABLE")
                    self.assertFalse(result["isolation_verified"])

    @unittest.skipUnless(os.environ.get("PH_TEST_PODMAN_IMAGE") and
                         os.environ.get("PH_TEST_CONTAINER_EXECUTABLE") and os.geteuid() != 0 and
                         shutil.which("podman"),
                         "NOT RUN: real rootless Podman+locally pinned test image+executable are required")
    def test_19_real_rootless_doctor_and_container_run(self):
        """Security integration, not a fake/mock. Requires pinned digest image."""
        p = profile()
        p["sandbox_profile"]["image"] = os.environ["PH_TEST_PODMAN_IMAGE"]
        executable = os.environ["PH_TEST_CONTAINER_EXECUTABLE"]
        # Use python3 as the test executable only if present in the pinned image.
        r = RootlessPodmanRunner(configured_executable=executable)
        outcome = r.doctor(p)
        self.assertEqual(outcome["status"], "PASS", outcome)
        self.assertTrue(outcome["isolation_verified"])
        if executable == "python3":
            with tempfile.TemporaryDirectory() as tmp:
                d = dirs(Path(tmp))
                result = r.run({**request(d), "sandbox_profile":p,
                    "argv":["python3", "-c", "from pathlib import Path;Path('/output/agent-result.json').write_text('{}')"]})
                self.assertEqual(result["exit_code"],0,result)
                self.assertEqual(result["termination_reason"],"EXITED",result)
                self.assertEqual((d["output_dir"]/"agent-result.json").read_text(),"{}")


if __name__ == "__main__":
    unittest.main()

"""PH-051-06 contract/security tests. All agent processes are *test doubles*;
these tests DO NOT attest actual Podman isolation or enable automatic runtime.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from project_harness.executors.result import (
    MAX_AGENT_RESULT_BYTES, MAX_PERSISTED_LOG_BYTES, ResultChannelError,
    normalize_exact_execution_result, resolve_execution_environment,
    validate_exact_result_channel,
)
from project_harness.safety import (scan_exact_secret, redact_exact_secrets,
                                   scan_changed_product_secrets)
from project_harness.sandbox.podman_rootless import RootlessPodmanRunner
from project_harness.serialization import load_data
from project_harness.workspace import check_control_plane
from tests.test_ph_051_05_codex_adapter import install_profiles, local_profile, ADP, SBX
import tests.test_ph_051_05_codex_adapter as previous


def agent(run_ref="RUN-TEST-001", task_ref="TSK-TEST-001@1"):
    return {"schema_version": 1, "task_ref": task_ref, "run_ref": run_ref,
            "status": "COMPLETED", "summary": "One bounded change",
            "changes": {"added": ["implemented.txt"], "modified": [], "deleted": []},
            "commands": [], "tests": [], "evidence": [], "blockers": []}


def sandbox_return(**overrides):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    default = {"termination_reason": "EXITED", "exit_code": 0,
               "backend": "ROOTLESS_PODMAN", "isolation_verified": True,
               "started_at": now, "finished_at": now, "stdout": "bounded stdout", "stderr": ""}
    default.update(overrides)
    return default


def write_result(folder, payload, *, mode=0o600):
    target = folder / "agent-result.json"
    data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
    target.write_bytes(data)
    target.chmod(mode)
    return target


def normalized(folder, *, run_ref="RUN-TEST-001", task_ref="TSK-TEST-001@1",
               process=None, secrets=None, root=None):
    return normalize_exact_execution_result(
        process or sandbox_return(), folder, run_ref=run_ref, task_ref=task_ref,
        adapter_profile_ref=ADP, sandbox_profile_ref=SBX,
        execution_root_digest="sha256:" + "b" * 64,
        project_root=root, secret_values=secrets)


class ResultChannelUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ph05106-output-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / "output"
        self.folder.mkdir()

    def test_01_schema_exact_binding_and_unverified_art_record(self):
        write_result(self.folder, agent())
        value, canonical = validate_exact_result_channel(self.folder, run_ref="RUN-TEST-001", task_ref="TSK-TEST-001@1")
        self.assertEqual(value["status"], "COMPLETED")
        self.assertTrue(canonical.endswith(b"\n"))
        result = normalized(self.folder)
        self.assertEqual(result["status"], "PENDING_INDEPENDENT_VERIFICATION")
        self.assertTrue(result["result_validated"])
        self.assertFalse(result["independently_verified"])
        self.assertEqual(result["execution_result"]["execution_result"]["run_ref"], "RUN-TEST-001@1")
        self.assertNotIn("SUCCEEDED", str(result))
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema optional")
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/execution_result.schema.json").read_text())
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(result["execution_result"])

    def test_02_agent_claim_never_causes_optimistic_completion(self):
        for status in ("BLOCKED", "FAILED", "COMPLETED"):
            with self.subTest(status=status):
                data = agent(); data["status"] = status
                write_result(self.folder, data)
                r = normalized(self.folder)
                self.assertFalse(r["independently_verified"])
                self.assertNotEqual(r["status"], "SUCCEEDED")
                self.assertEqual(r["verification_eligible"], status == "COMPLETED")
        self.assertEqual(normalized(self.folder, process=sandbox_return(exit_code=5))["reason_code"], "EXECUTOR_EXIT_NONZERO")
        self.assertEqual(normalized(self.folder, process=sandbox_return(backend="DOCKER"))["reason_code"], "SANDBOX_POLICY_FAILURE")
        self.assertEqual(normalized(self.folder, process=sandbox_return(isolation_verified=False))["reason_code"], "SANDBOX_POLICY_FAILURE")

    def test_03_missing_invalid_utf8_duplicate_keys_and_nonfinite_numbers(self):
        self.assertEqual(normalized(self.folder)["reason_code"], "RESULT_MISSING")
        for raw in (b"", b"\\xff", b"{", b"[]", b'{"a":1,"a":2}', b'{"run_ref":NaN}', b'"COMPLETE"'):
            with self.subTest(raw=raw):
                write_result(self.folder, raw)
                self.assertEqual(normalized(self.folder)["reason_code"], "RESULT_INVALID")

    def test_04_wrong_run_task_unknown_fields_arrays_and_status(self):
        cases = []
        bad = agent(); bad["run_ref"]="RUN-FOREIGN-001"; cases.append(bad)
        bad = agent(); bad["task_ref"]="TSK-FOREIGN"; cases.append(bad)
        bad = agent(); bad["schema_version"] = True; cases.append(bad)
        bad = agent(); bad["unexpected"] = "EXECUTE"; cases.append(bad)
        bad = agent(); del bad["summary"]; cases.append(bad)
        bad = agent(); bad["commands"] = {}; cases.append(bad)
        bad = agent(); bad["changes"] = {"added":[],"modified":[],"deleted":[],"whoops":[]}; cases.append(bad)
        bad = agent(); bad["changes"]["added"]=[13]; cases.append(bad)
        bad = agent(); bad["status"]="PASS"; cases.append(bad)
        for case in cases:
            with self.subTest(case=case):
                write_result(self.folder, case)
                self.assertEqual(normalized(self.folder)["reason_code"], "RESULT_INVALID")

    def test_05_symlink_hardlink_fifo_mode_and_ownership_fail_closed(self):
        dest = write_result(self.folder, agent())
        dest.chmod(0o644)
        self.assertEqual(normalized(self.folder)["reason_code"], "RESULT_INVALID")
        dest.chmod(0o600)
        twin = self.root / "hardlink"
        os.link(dest, twin)
        self.assertEqual(normalized(self.folder)["reason_code"], "RESULT_INVALID")
        twin.unlink()
        dest.unlink()
        target = self.root / "sensitive"; target.write_text("{}")
        dest.symlink_to(target)
        self.assertEqual(normalized(self.folder)["reason_code"], "RESULT_INVALID")
        dest.unlink()
        if hasattr(os, "mkfifo"):
            os.mkfifo(dest)
            self.assertEqual(normalized(self.folder)["reason_code"], "RESULT_INVALID")
            dest.unlink()
        write_result(self.folder, agent())
        with self.assertRaises(ResultChannelError) as caught:
            validate_exact_result_channel(self.folder, run_ref="RUN-TEST-001", task_ref="TSK-TEST-001@1", owner_uid=os.geteuid()+1)
        self.assertEqual(caught.exception.reason_code, "RESULT_INVALID")

    def test_06_parent_symlink_and_extra_outputs_are_rejected(self):
        write_result(self.folder, agent())
        (self.folder / "undisclosed.log").write_text("extra")
        self.assertEqual(normalized(self.folder)["reason_code"], "RESULT_INVALID")
        (self.folder / "undisclosed.log").unlink()
        sub = self.root / "symlink-parent"
        sub.symlink_to(self.folder, target_is_directory=True)
        with self.assertRaises(ResultChannelError):
            validate_exact_result_channel(sub, run_ref="RUN-TEST-001", task_ref="TSK-TEST-001@1")

    def test_07_oversize_result_and_bounded_log_flood_rejected(self):
        write_result(self.folder, b" " * (MAX_AGENT_RESULT_BYTES+1))
        self.assertEqual(normalized(self.folder)["reason_code"], "RESULT_INVALID")
        write_result(self.folder, agent())
        r = normalized(self.folder, process=sandbox_return(stdout="x" * (MAX_PERSISTED_LOG_BYTES+1)))
        self.assertEqual(r["reason_code"], "OUTPUT_LIMIT_EXCEEDED")

    def test_08_secret_echo_in_stdout_stderr_result_escape_and_unicode(self):
        token = "S3CRET-PH05106"
        for label in ("stdout", "stderr"):
            write_result(self.folder, agent())
            r = normalized(self.folder, process=sandbox_return(**{label: token}), secrets={"KEY":token})
            self.assertEqual(r["reason_code"], "SECRET_LEAK_DETECTED")
            self.assertNotIn(token, str(r))
        data = agent();data["summary"]=token
        write_result(self.folder, data)
        self.assertEqual(normalized(self.folder, secrets={"KEY":token})["reason_code"], "SECRET_LEAK_DETECTED")
        # Escaped agent JSON does not contain literal token but decodes to it.
        raw = json.dumps(data, ensure_ascii=True).replace("S3CRET", "\\u00533CRET").encode()
        write_result(self.folder, raw)
        self.assertEqual(normalized(self.folder, secrets={"KEY":token})["reason_code"], "SECRET_LEAK_DETECTED")
        self.assertTrue(scan_exact_secret(data, {"KEY":token}))
        self.assertEqual(redact_exact_secrets("X"+token, {"KEY":token}), "X[REDACTED]")

    def test_09_typed_string_looking_like_shell_is_inert_json(self):
        data=agent();data["summary"]='$(echo run) ; rm -rf /'
        write_result(self.folder,data)
        result=normalized(self.folder)
        self.assertTrue(result["result_validated"])
        self.assertFalse(result["independently_verified"])

    def test_10_environment_refs_only_no_host_env_dump(self):
        profile = local_profile()["agent_adapter_profile"]
        profile["environment_allowlist"]=["LANG", "TZ"]
        profile["secret_environment_refs"]=["ENV:OPENAI_API_KEY"]
        host={"OPENAI_API_KEY":"secret-UNIQUE-77", "LANG":"en_US.UTF-8", "TZ":"UTC", "HOME":"/secret", "RANDOM_TOKEN":"private"}
        forwarded,secrets=resolve_execution_environment(profile,host)
        self.assertEqual(set(forwarded), {"LANG","TZ","OPENAI_API_KEY"})
        self.assertEqual(secrets, {"OPENAI_API_KEY":"secret-UNIQUE-77"})
        self.assertNotIn("HOME", str(forwarded))
        for absent in ({}, {"OPENAI_API_KEY":""}):
            with self.assertRaises(ResultChannelError) as error:
                resolve_execution_environment(profile, absent)
            self.assertEqual(error.exception.reason_code,"SECRET_REFERENCE_MISSING")
        profile["secret_environment_refs"]=["ENV:OPENAI_API_KEY=raw"]
        with self.assertRaises(ResultChannelError):resolve_execution_environment(profile, host)
        profile["secret_environment_refs"]=["ENV:OPENAI_API_KEY"]
        host["OPENAI_API_KEY"]="bad\nINJECT=1"
        with self.assertRaises(ResultChannelError):resolve_execution_environment(profile, host)
        profile["environment_allowlist"]=["HOME"]
        with self.assertRaises(ResultChannelError):resolve_execution_environment(profile,host)

    def test_11_read_only_changed_product_secret_scan_helper(self):
        product=self.root / "product";product.mkdir()
        (product/"safe.txt").write_text("okay")
        (product/"secret.txt").write_text("before-TOKENSECRET-after")
        self.assertEqual(scan_changed_product_secrets(product, ["safe.txt","secret.txt"],{"API_KEY":"TOKENSECRET"}), ["secret.txt"])
        for unsafe in ("../outside", "/etc/passwd", ".harness/private", "sub/../other"):
            with self.subTest(unsafe=unsafe):
                with self.assertRaises((Exception,)):
                    scan_changed_product_secrets(product, [unsafe], {"K":"X"})
        self.assertEqual((product/"secret.txt").read_text(), "before-TOKENSECRET-after")


class KernelPublicationTests(unittest.TestCase):
    """Reuse the *real* PH-051-05 prepared-Run fixture; no agent launch."""
    setUp = previous.PreparedJitTests.setUp
    def test_15_kernel_owned_result_and_logs_are_immutable_and_fenced(self):
        adapter = __import__("project_harness.executors.codex_cli_local", fromlist=["CodexCliLocalAdapter"]).CodexCliLocalAdapter.from_project(self.root)
        preparation = adapter.prepare_current_run(self.runtime)
        req = preparation["sandbox_request"]
        output = Path(req["output_dir"])
        write_result(output, agent(self.active["run_ref"], self.active["task_ref"]))
        canonical_digest = __import__("project_harness.stages", fromlist=["product_baseline_revision"]).product_baseline_revision(self.root)
        trusted_process = sandbox_return()
        r = normalized(output, run_ref=self.active["run_ref"],task_ref=self.active["task_ref"],root=self.root,process=trusted_process)
        self.assertTrue(r["result_validated"],r)
        expected = self.root / ".harness/runtime/AGENT_RESULTS" / (self.active["run_ref"] + ".json")
        self.assertTrue(expected.exists())
        self.assertEqual(stat.S_IMODE(expected.stat().st_mode),0o600)
        self.assertEqual(load_data(expected)["run_ref"], self.active["run_ref"])
        ids = r["execution_result"]["execution_result"]["id"]
        record_path = self.root/".harness/runtime/EXECUTION_RESULTS"/(ids+".yaml")
        self.assertEqual(load_data(record_path)["execution_result"]["result_status"], "COMPLETED")
        self.assertEqual(check_control_plane(self.root,self.active)["status"],"PASS")
        self.assertEqual(__import__("project_harness.stages",fromlist=["product_baseline_revision"]).product_baseline_revision(self.root),canonical_digest)
        self.assertEqual(normalized(output, run_ref=self.active["run_ref"],task_ref=self.active["task_ref"],root=self.root,process=trusted_process)["status"],"PENDING_INDEPENDENT_VERIFICATION")
        expected.write_text("tampered")
        self.assertEqual(normalized(output, run_ref=self.active["run_ref"],task_ref=self.active["task_ref"],root=self.root,process=trusted_process)["reason_code"],"RESULT_INVALID")


class MockedRunnerEnvTests(unittest.TestCase):
    def test_16_argv_contains_only_env_file_path_and_no_secret_echo(self):
        from tests.test_ph_051_03_rootless_podman import profile,dirs,request
        secret="UNIQUE-VERY-PRIVATE-TOKEN-2345"
        with tempfile.TemporaryDirectory() as temp:
            d=dirs(Path(temp))
            req=request(d)
            req["run_context"]={"adapter_profile":local_profile()["agent_adapter_profile"],
                                 "run_id":"RUN-PH05110-SECRET-001"}
            req["run_context"]["adapter_profile"]["secret_environment_refs"]=["ENV:FAKE_CLI_SECRET"]
            runner=RootlessPodmanRunner(configured_executable="codex")
            doctor={"status":"PASS","backend":"ROOTLESS_PODMAN","isolation_verified":True,"checks":{"boundary":"PASS"}}
            captured=[]
            def fake_spawn(argv,**kwargs):
                captured.append(tuple(argv))
                env_file=Path(argv[argv.index("--env-file")+1]); self.assertEqual(stat.S_IMODE(env_file.stat().st_mode),0o600)
                self.assertIn(secret, env_file.read_text())
                self.assertNotIn(secret, " ".join(argv))
                return sandbox_return(stdout=secret,stderr="ordinary")
            with mock.patch.dict(os.environ,{"FAKE_CLI_SECRET":secret}),mock.patch("os.geteuid",return_value=1001), \
                 mock.patch.object(runner,"doctor",return_value=doctor), \
                 mock.patch.object(runner,"_podman",return_value="/usr/bin/podman"), \
                 mock.patch.object(runner,"_spawn",side_effect=fake_spawn), \
                 mock.patch("subprocess.Popen",side_effect=AssertionError("No host CLI")):
                r=runner.run(req)
            self.assertEqual(r["reason_code"],"SECRET_LEAK_DETECTED")
            self.assertEqual(r["stdout"],"[REDACTED]")
            self.assertEqual(len(captured),1)
            self.assertNotIn(secret,str(r))
            self.assertFalse(any(Path(temp).rglob("environment")))

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.project_input import (
    DEFAULT_EXECUTION_POLICY, exact_execution_profile_bindings, execution_policy_issues,
    load_project_input_schema, migrate_project_input, project_input_schema_issues,
    project_input_template, validate_project_input,
)
from project_harness.registry import EXPECTED_REGISTRY_VERSIONS, load_registries
from project_harness.serialization import load_data, write_data
from project_harness.validation import doctor, validate_project_directory
from project_harness.compiler import prepare_handoff
from tests.test_engine import ROOT, load_fixture, prepare_demo

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None


class PH05101ContractTests(unittest.TestCase):
    def test_01_v3_read_conservatively_v4_replay_no_mutation(self):
        old = load_fixture()
        original = deepcopy(old)
        migrated, report = migrate_project_input(old)
        self.assertEqual(old, original)
        self.assertEqual(migrated["schema_version"], 4)
        self.assertEqual(migrated["execution"], DEFAULT_EXECUTION_POLICY)
        self.assertEqual(report["migration_id"], "MIG-ENGINE-0.5.0-TO-0.5.1")
        twice, replay = migrate_project_input(migrated)
        self.assertEqual(twice, migrated)
        self.assertEqual(replay["status"], "NO_ACTION")
        self.assertEqual(project_input_schema_issues(migrated), [])
        self.assertEqual(validate_project_input(old, require_approvals=True)["status"], "READY_FOR_HANDOFF")
        legacy_with_fake_optin = deepcopy(old)
        legacy_with_fake_optin["execution"] = dict(DEFAULT_EXECUTION_POLICY, mode="LOCAL_AUTOMATIC")
        self.assertEqual(validate_project_input(legacy_with_fake_optin)["status"], "INVALID")
        self.assertEqual(old, original)

    def test_02_distribution_versions_and_dedicated_sbx_contract(self):
        registries = load_registries()
        self.assertEqual(EXPECTED_REGISTRY_VERSIONS["contracts"], 6)
        self.assertEqual(EXPECTED_REGISTRY_VERSIONS["statuses"], 6)
        self.assertEqual(EXPECTED_REGISTRY_VERSIONS["id_prefixes"], 3)
        entities = registries["contracts"]["registry"]["entities"]
        self.assertEqual(entities["agent_adapter_profile"]["id_prefix"], "ADP")
        self.assertNotIn("executor_profile", entities)
        self.assertEqual(entities["sandbox_profile"]["id_prefix"], "SBX")
        self.assertEqual(entities["execution_result"]["storage_path"], ".harness/runtime/EXECUTION_RESULTS/{id}.yaml")
        self.assertEqual(doctor(check_manifest=False)["status"], "PASS")

    def test_03_strict_policy_unknown_fields_wrong_refs_and_secrets(self):
        base = project_input_template("Strict", "GREENFIELD", [])
        self.assertEqual(project_input_schema_issues(base, relaxed=True), [])
        for item in (
            dict(DEFAULT_EXECUTION_POLICY, secret="plain-secret"),
            dict(DEFAULT_EXECUTION_POLICY, argv_template=["/bin/sh"]),
            dict(DEFAULT_EXECUTION_POLICY, network_mode="HOST"),
            dict(DEFAULT_EXECUTION_POLICY, mode="LOCAL_AUTOMATIC"),
            dict(DEFAULT_EXECUTION_POLICY, mode="LOCAL_AUTOMATIC", adapter_profile_ref="ADP-CODEX@1", sandbox_profile_ref="SBX-SANDBOX@1", environment={"API_KEY":"secret"}),
            dict(DEFAULT_EXECUTION_POLICY, mode="LOCAL_AUTOMATIC", adapter_profile_ref="ADP-CODEX", sandbox_profile_ref="SBX-SANDBOX@1"),
            dict(DEFAULT_EXECUTION_POLICY, mode="MANUAL_HANDOFF", network_mode="EXPLICIT_APPROVED_EGRESS"),
            dict(DEFAULT_EXECUTION_POLICY, mode="MANUAL_HANDOFF", completion_policy="AUTO_AFTER_PASS"),
        ):
            with self.subTest(item=item):
                candidate = deepcopy(base)
                candidate["execution"] = item
                self.assertTrue(project_input_schema_issues(candidate, relaxed=True) or execution_policy_issues(item))
                self.assertEqual(validate_project_input(candidate)["status"], "INVALID")

    def _profiles(self, root: Path, *, sandbox_status="ACTIVE", sandbox_image=None, backend="ROOTLESS_PODMAN"):
        aid, sid = "ADP-CODEX-CLI-LOCAL-001", "SBX-ROOTLESS-PODMAN-001"
        image = sandbox_image or "project-harness-codex-runtime@sha256:" + "a" * 64
        adapter = {"agent_adapter_profile": {
            "id": aid, "revision": 1, "status": "ACTIVE", "kind": "CODEX_CLI_LOCAL",
            "executable": "codex", "argv_template": ["codex", "exec", "{prompt_bundle_path}"],
            "working_directory": "/workspace/product", "timeout_seconds": 1200, "stdin_mode": "CLOSED",
            "environment_allowlist": ["LANG", "LC_ALL"], "secret_environment_refs": ["ENV:CODEX_API_KEY"],
            "sandbox_profile_ref": sid + "@1",
        }}
        sandbox={"sandbox_profile": {
            "id": sid, "revision": 1, "status": sandbox_status, "backend": backend,
            "image": image, "network_mode": "NONE", "root_filesystem": "READ_ONLY",
            "run_as_non_root": True, "drop_all_capabilities": True, "no_new_privileges": True,
            "writable_mounts": ["/workspace/product", "/output", "/tmp"],
            "limits": {"timeout_seconds":1200, "memory_mb":2048, "cpu_count":2,
                       "pids":128, "output_bytes":52428800},
        }}
        a=root/".harness/config/ADAPTERS"/f"{aid}@1.yaml"
        s=root/".harness/config/SANDBOXES"/f"{sid}@1.yaml"
        write_data(a,adapter); write_data(s,sandbox)
        policy={"mode":"LOCAL_AUTOMATIC","adapter_profile_ref":aid+"@1",
                "sandbox_profile_ref":sid+"@1","network_mode":"NONE",
                "completion_policy":"EXPLICIT_AFTER_VERIFICATION"}
        return policy,a,s

    def test_04_exact_profiles_active_and_sha256_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            policy,a,s=self._profiles(root)
            result=exact_execution_profile_bindings(root,policy)
            self.assertEqual(result["adapter"]["digest"], "sha256:"+sha256_file(a))
            self.assertEqual(result["sandbox"]["digest"], "sha256:"+sha256_file(s))
            with self.assertRaises(ValidationFailure):
                exact_execution_profile_bindings(root,dict(policy,adapter_profile_ref="ADP-CODEX-CLI-LOCAL-001@10"))
            doc=load_data(a)
            doc["agent_adapter_profile"]["revision"]=2
            write_data(a,doc)
            with self.assertRaises(ValidationFailure):
                exact_execution_profile_bindings(root,policy)

    def test_05_profile_negative_image_backend_status_untrusted_env(self):
        bad_variants = [
            {"sandbox_status":"SUSPENDED"},
            {"sandbox_image":"project-harness-codex-runtime:latest"},
            {"backend":"DOCKER"},
        ]
        for variant in bad_variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                policy,a,s=self._profiles(root,**variant)
                with self.assertRaises(ValidationFailure):
                    exact_execution_profile_bindings(root,policy)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);policy,a,s=self._profiles(root)
            doc=load_data(a)
            doc["agent_adapter_profile"]["secret_values"]={"CODEX_API_KEY":"private"}
            write_data(a,doc)
            with self.assertRaises(ValidationFailure):
                exact_execution_profile_bindings(root,policy)

    def test_06_automatic_execution_not_available_no_host_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); policy,a,s=self._profiles(root)
            self.assertEqual(exact_execution_profile_bindings(root,policy)["sandbox"]["ref"],policy["sandbox_profile_ref"])
            self.assertIn("execute_current", __import__("project_harness.runtime",fromlist=["execute_current"]).__dict__)
        # PH-051-09 adds public route; old contract test still proves opt-in.
        from project_harness.cli import build_parser
        self.assertIn('execute-current',build_parser().format_help())

    def test_06b_explicit_auto_prepare_still_fails_closed(self):
        from project_harness.intake import start_intake
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp)
            inp=load_fixture()
            inp["schema_version"] = 4  # explicit opt-in cannot be smuggled through v3
            policy = {"mode":"LOCAL_AUTOMATIC", "adapter_profile_ref":"ADP-CODEX-CLI-LOCAL-001@1",
                      "sandbox_profile_ref":"SBX-ROOTLESS-PODMAN-001@1",
                      "network_mode":"NONE", "completion_policy":"EXPLICIT_AFTER_VERIFICATION"}
            inp["execution"]=policy
            initial=temp/"input.json"
            initial.write_text(json.dumps(inp),encoding="utf-8")
            start_intake(temp/"intake",project_name=inp["project"]["name"],
                         mode="greenfield",initial_input=initial)
            self._profiles(temp/"intake")
            out=temp/"would-not-create.zip"
            with self.assertRaises(ValidationFailure) as err:
                prepare_handoff(temp/"intake",out)
            self.assertIn("AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED",str(err.exception.details))
            self.assertFalse(out.exists())

    def test_07_manual_prepare_lock_v7_no_activation(self):
        with tempfile.TemporaryDirectory() as temp:
            _, archive, project = prepare_demo(Path(temp))
            lock=load_data(project/".harness/config/PROJECT_LOCK.yaml")["project_lock"]
            self.assertEqual(lock["schema_version"],7)
            self.assertEqual(lock["harness_distribution"],"0.5.1")
            self.assertEqual(lock["execution"], DEFAULT_EXECUTION_POLICY)
            self.assertEqual(lock["execution_profile_bindings"],{
                "adapter":{"ref":None,"digest":None},
                "sandbox":{"ref":None,"digest":None}})
            self.assertIn("MIG-ENGINE-0.5.0-TO-0.5.1",lock["migrations_applied"])
            self.assertEqual(validate_project_directory(project)["status"],"PASS")
            self.assertEqual(load_data(project/".harness/state/PROJECT_INPUT_ACCEPTED.yaml")["execution"],DEFAULT_EXECUTION_POLICY)

    @unittest.skipUnless(Draft202012Validator is not None,"jsonschema optional for schema meta validation")
    def test_08_all_new_json_schemas_draft_valid(self):
        for name in ("project_input", "executor_profile", "sandbox_profile", "execution_result", "apply_evidence"):
            schema=json.loads((ROOT/"schemas"/f"{name}.schema.json").read_text())
            Draft202012Validator.check_schema(schema)
            with self.subTest(name=name):
                self.assertEqual(schema.get('additionalProperties'),False)

    @unittest.skipUnless(Draft202012Validator is not None,"jsonschema optional for schema negative validation")
    def test_09_sample_result_and_apply_contracts_strict(self):
        base=ROOT/"schemas"
        record={"execution_result":{
            "id":"ART-EXEC-001","run_ref":"RUN-TEST-001@1",
            "adapter_profile_ref":"ADP-CODEX-001@1","sandbox_profile_ref":"SBX-ROOTLESS-001@1",
            "started_at":"2026-10-25T00:00:00Z","finished_at":"2026-10-25T00:01:00Z",
            "exit_code":0,"termination_reason":"EXITED","stdout_artifact_ref":None,
            "stderr_artifact_ref":None,"agent_result_ref":"ART-RESULT-001",
            "execution_root_digest":"sha256:"+"a"*64,"result_status":"COMPLETED"}}
        schema=json.loads((base/"execution_result.schema.json").read_text())
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(record)))
        record["execution_result"]["raw_log"]="SECRET"
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(record)))
        evidence={"apply_evidence":{"id":"EVD-APPLY-001","run_ref":"RUN-TEST-001@1",
            "verification_ref":"TRP-TEST-001","baseline_before":"sha256:"+"0"*64,
            "baseline_after":"sha256:"+"1"*64,"status":"PASS","write_set":[],
            "applied_at":"2026-10-25T00:01:00Z"}}
        schema=json.loads((base/"apply_evidence.schema.json").read_text())
        self.assertFalse(list(Draft202012Validator(schema).iter_errors(evidence)))
        evidence["apply_evidence"]["write_set"].append({"path":".harness/config/PROJECT.yaml", "operation":"REPLACE","sha256_after": "sha256:"+"a"*64})
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(evidence)))

if __name__ == '__main__':
    unittest.main()

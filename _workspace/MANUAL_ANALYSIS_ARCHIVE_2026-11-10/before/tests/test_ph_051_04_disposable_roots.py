"""PH-051-04: product byte equality, bounded control, path-escape, no apply."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from project_harness.archive import zip_directory
from project_harness.errors import SafetyViolation, ValidationFailure
from project_harness.execution_roots import check_execution_baseline, prepare_execution_root
from project_harness.sandbox.profiles import validate_execution_mounts
from project_harness.serialization import load_data, write_data
from project_harness.stages import product_baseline_revision
from project_harness.validation import validate_project_directory
from project_harness.workspace import check_control_plane, load_phase_boundary
from project_harness.workspace import snapshot_product
from tests.test_engine import prepare_demo


class DisposableRootTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ph05104-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = prepare_demo(self.base / "build")[2]
        self.runtime = self.base / "external-runtime"
        self.state = self.root / ".harness/state/CURRENT_STATE.yaml"
        self.run = load_data(self.state)["state"]["active_run"]

    def build(self):
        return prepare_execution_root(self.root, self.runtime, run_ref=self.run["run_ref"])

    def binding(self):
        path = self.root / ".harness/runtime/EXECUTION_BINDINGS" / (self.run["run_ref"] + ".yaml")
        return path, load_data(path)["execution_binding"]

    def test_01_snapshot_equal_canonical_and_no_shared_inode(self):
        original = product_baseline_revision(self.root)
        result = self.build()
        self.assertEqual(original, result["execution_baseline"]["canonical_product_digest"])
        self.assertEqual(original, result["execution_baseline"]["snapshot_product_digest"])
        for relative, meta in snapshot_product(self.root).items():
            copied = Path(result["product_dir"]) / relative
            canonical = self.root / relative
            self.assertEqual(meta["sha256"], __import__("hashlib").sha256(copied.read_bytes()).hexdigest())
            self.assertNotEqual(canonical.stat().st_ino, copied.stat().st_ino)
        self.assertFalse((Path(result["product_dir"]) / ".harness").exists())
        for forbidden in ("AGENTS.md", "CODEX_START.md", "PROJECT.md", "MANIFEST.sha256"):
            self.assertFalse((Path(result["product_dir"]) / forbidden).exists())
        self.assertEqual(product_baseline_revision(self.root), original)

    def test_02_exact_projection_allowlist_readonly_and_binding_only_metadata(self):
        result = self.build()
        control = Path(result["control_dir"])
        self.assertEqual({p.name for p in control.iterdir()}, {
            "prompt-bundle.md", "prompt-bundle.yaml", "context-packet.json", "task-contract.yaml",
            "run-plan.yaml", "permitted-config.json", "agent-task-result.schema.json",
        })
        self.assertFalse(control.stat().st_mode & stat.S_IWUSR)
        self.assertTrue(all(p.is_file() and not p.is_symlink() and not (p.stat().st_mode & 0o222)
                            for p in control.iterdir()))
        self.assertFalse((control / ".harness").exists())
        self.assertEqual(load_data(control / "run-plan.yaml")["run_plan"]["task_ref"], self.run["task_ref"])
        self.assertEqual(load_data(control / "context-packet.json")["context_packet"]["run_ref"], self.run["run_ref"])
        self.assertEqual(json.loads((control / "agent-task-result.schema.json").read_text())["$id"], "SCHEMA-AGENT-TASK-RESULT@1")
        conf = load_data(control / "permitted-config.json")
        self.assertEqual(set(conf), {"execution"})
        self.assertEqual(set(conf["execution"]), {
            "mode", "adapter_profile_ref", "sandbox_profile_ref", "network_mode", "completion_policy"})
        path, binding = self.binding()
        self.assertNotIn(str(self.runtime), path.read_text())
        self.assertEqual(binding["execution_baseline"]["task_ref"], self.run["task_ref"])
        self.assertEqual(binding["execution_baseline"]["prompt_bundle_ref"], self.run["prompt_bundle_ref"])
        self.assertEqual(binding["execution_baseline"]["base_revision"], product_baseline_revision(self.root))
        self.assertEqual(set(binding["projection_files"]), {p.name for p in control.iterdir()})
        self.assertEqual({p.name for p in Path(result["execution_root"]).iterdir()}, {"product", "control", "output"})
        self.assertEqual(validate_execution_mounts({"execution_root": result["execution_root"],
                "canonical_project_root": self.root, "product_dir": result["product_dir"],
                "control_dir": result["control_dir"], "output_dir": result["output_dir"]})["control_dir"], control)

    def test_03_replay_idempotent_no_duplicate_roots_or_bindings(self):
        original = self.build()
        before = self.binding()[0].read_bytes()
        second = self.build()
        self.assertTrue(second["idempotent"])
        self.assertEqual(before, self.binding()[0].read_bytes())
        self.assertEqual(original["execution_root"], second["execution_root"])
        self.assertEqual(len(list(self.runtime.rglob(self.run["run_ref"]))), 1)
        self.assertEqual(len(list(self.root.glob(".harness/runtime/EXECUTION_BINDINGS/*.yaml"))), 1)

    def test_04_writable_copy_does_not_modify_canonical_product_or_control(self):
        r = self.build()
        before = {p: (self.root / p).read_bytes() for p in snapshot_product(self.root)}
        canonical_digest = product_baseline_revision(self.root)
        protected_before = (self.root / ".harness/config/PROJECT_LOCK.yaml").read_bytes()
        product = Path(r["product_dir"])
        rel = next(iter(before))
        (product / rel).write_bytes(b"disposable-only mutation")
        (product / "new.txt").write_bytes(b"created only in isolated root")
        self.assertEqual({p: (self.root / p).read_bytes() for p in before}, before)
        self.assertEqual(product_baseline_revision(self.root), canonical_digest)
        self.assertEqual((self.root / ".harness/config/PROJECT_LOCK.yaml").read_bytes(), protected_before)
        with self.assertRaises(ValidationFailure):
            self.build()   # modified snapshot never silently reused/restored

    def test_05_baseline_changed_external_edit_is_reported(self):
        self.build()
        path, binding = self.binding()
        self.assertEqual(check_execution_baseline(self.root, binding)["status"], "PASS")
        (self.root / "external-change.txt").write_text("new", encoding="utf-8")
        self.assertEqual(check_execution_baseline(self.root, binding)["status"], "BASELINE_CHANGED")
        with self.assertRaisesRegex(ValidationFailure, "BASELINE_CHANGED"):
            self.build()
        self.assertEqual(path.read_bytes(), json.dumps({"execution_binding": binding}, ensure_ascii=False, indent=2).encode() + b"\n")

    def test_06_reject_noncurrent_run_and_escape_runtime_paths(self):
        for path in (self.root / "runtime", self.root / ".harness/runtime/outside", self.root.parent):
            with self.subTest(path=path), self.assertRaises(SafetyViolation):
                prepare_execution_root(self.root, path)
        with self.assertRaises(ValidationFailure):
            prepare_execution_root(self.root, self.runtime, run_ref="RUN-DIFFERENT-001")
        self.assertFalse((self.root / ".harness/runtime/EXECUTION_BINDINGS").exists())

    def test_07_reject_parent_symlink_before_writing(self):
        self.runtime.mkdir()
        pid = load_data(self.root / ".harness/config/PROJECT.yaml")["project"]["id"]
        (self.runtime / pid).symlink_to(self.root, target_is_directory=True)
        before = product_baseline_revision(self.root)
        with self.assertRaises(SafetyViolation):
            self.build()
        self.assertEqual(before, product_baseline_revision(self.root))
        self.assertFalse((self.root / "executions").exists())

    def test_08_ignore_symlinks_even_if_external_secret(self):
        secret = self.base / "private.txt"
        secret.write_text("secret-outside", encoding="utf-8")
        (self.root / "steal.txt").symlink_to(secret)
        (self.root / "jump").symlink_to(self.base, target_is_directory=True)
        original = product_baseline_revision(self.root)
        r = self.build()
        self.assertFalse((Path(r["product_dir"]) / "steal.txt").exists())
        self.assertFalse((Path(r["product_dir"]) / "jump").exists())
        self.assertEqual(original, product_baseline_revision(self.root))
        self.assertEqual(secret.read_text(), "secret-outside")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "Unix FIFO required")
    def test_09_reject_special_file_and_no_binding_or_partial_root(self):
        fifo = self.root / "injected-fifo"
        os.mkfifo(fifo)
        with self.assertRaises(SafetyViolation):
            self.build()
        self.assertFalse((self.root / ".harness/runtime/EXECUTION_BINDINGS" / f"{self.run['run_ref']}.yaml").exists())
        self.assertFalse((self.runtime / load_data(self.root / ".harness/config/PROJECT.yaml")["project"]["id"] / "executions" / self.run["run_ref"]).exists())

    def test_10_run_control_ref_or_text_digest_tampering_blocks(self):
        source = self.root / self.run["prompt_bundle_path"]
        data = load_data(source)
        data["compiled_prompt_bundle"]["run_ref"] = "RUN-OTHER-999"
        write_data(source, data)
        with self.assertRaises((SafetyViolation, ValidationFailure)):
            self.build()
        self.assertFalse((self.root / ".harness/runtime/EXECUTION_BINDINGS").exists())

    def test_11_control_symlink_substitution_refused(self):
        target = self.root / self.run["context_packet_path"]
        data = target.read_bytes()
        target.unlink()
        other = self.base / "outside.yaml"
        other.write_bytes(data)
        target.symlink_to(other)
        with self.assertRaises(SafetyViolation):
            self.build()

    def test_12_replay_reject_tampered_projection_and_result_dir(self):
        result = self.build()
        projected = Path(result["control_dir"]) / "prompt-bundle.md"
        projected.chmod(0o644)
        projected.write_text("tampered", encoding="utf-8")
        projected.chmod(0o444)
        with self.assertRaises(SafetyViolation):
            self.build()
        # Corrupted projection is not repaired in place.
        self.assertEqual(projected.read_text(), "tampered")

    def test_13_replay_reject_nonempty_output(self):
        result = self.build()
        (Path(result["output_dir"]) / "unexpected.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ValidationFailure):
            self.build()

    def test_14_binding_never_exported_or_in_project_lock(self):
        result = self.build()
        export = self.base / "handoff.zip"
        zip_directory(self.root, export)
        with zipfile.ZipFile(export) as zf:
            self.assertIsNone(zf.testzip())
            self.assertFalse(any("EXECUTION_BINDINGS" in n or "/executions/" in n for n in zf.namelist()))
            self.assertTrue(any(n.endswith(".harness/config/PROJECT_LOCK.yaml") for n in zf.namelist()))
        self.assertNotIn(result["execution_root"], (self.root / ".harness/config/PROJECT_LOCK.yaml").read_text())

    def test_15_orphan_root_not_adopted_without_exact_binding(self):
        pid = load_data(self.root / ".harness/config/PROJECT.yaml")["project"]["id"]
        orphan = self.runtime / pid / "executions" / self.run["run_ref"]
        orphan.mkdir(parents=True)
        with self.assertRaises(ValidationFailure):
            self.build()
        self.assertEqual(list(orphan.iterdir()), [])


    def test_16_replay_rejects_forged_metadata_even_with_updated_file_hashes(self):
        r = self.build()
        path, record = self.binding()
        projection = Path(r["control_dir"]) / "prompt-bundle.md"
        projection.chmod(0o644)
        projection.write_bytes(b"forgery")
        projection.chmod(0o444)
        record["projection_files"]["prompt-bundle.md"] = "sha256:" + __import__("hashlib").sha256(b"forgery").hexdigest()
        write_data(path, {"execution_binding": record})
        with self.assertRaises((SafetyViolation, ValidationFailure)):
            self.build()

    def test_17_replay_rejects_control_source_revision_drift(self):
        self.build()
        source = self.root / self.run["context_packet_path"]
        body = load_data(source)
        body["context_packet"]["selected_paths"] = ["changed-by-external"]
        write_data(source, body)
        with self.assertRaises((SafetyViolation, ValidationFailure)):
            self.build()

    def test_18_execution_policy_cannot_project_arbitrary_strings(self):
        lock = self.root / ".harness/config/PROJECT_LOCK.yaml"
        body = load_data(lock)
        body["project_lock"]["execution"]["network_mode"] = "HOST"
        write_data(lock, body)
        with self.assertRaises((SafetyViolation, ValidationFailure)):
            self.build()
        self.assertFalse((self.root / ".harness/runtime/EXECUTION_BINDINGS").exists())


    def test_19_hardlink_to_outside_secrets_cannot_be_copied(self):
        private = self.base / "private-outside.txt"
        private.write_text("do-not-copy-to-disposable", encoding="utf-8")
        os.link(private, self.root / "hardlink-leak.txt")
        with self.assertRaises(SafetyViolation):
            self.build()
        self.assertFalse((self.root / ".harness/runtime/EXECUTION_BINDINGS").exists())
        self.assertEqual(private.read_text(), "do-not-copy-to-disposable")

    def test_20_signed_phase_keeps_validate_project_pass_without_hidden_mutations(self):
        self.assertEqual(validate_project_directory(self.root)["status"], "PASS")
        baseline_phase = load_phase_boundary(self.root, self.run)
        first = self.build()
        phase = load_phase_boundary(self.root, self.run)
        self.assertEqual(phase["phase"], "EXECUTION_ROOT_PREPARED")
        self.assertEqual(phase["sequence"], baseline_phase["sequence"] + 1)
        self.assertEqual(phase["kernel_written_paths"], [
            ".harness/runtime/EXECUTION_BINDINGS/" + self.run["run_ref"] + ".yaml"])
        self.assertEqual(check_control_plane(self.root, self.run)["status"], "PASS")
        self.assertEqual(validate_project_directory(self.root)["status"], "PASS")
        self.assertTrue(self.build()["idempotent"])
        self.assertEqual(load_phase_boundary(self.root, self.run), phase)  # replay writes nothing
        self.assertEqual(first["execution_baseline"]["control_plane_digest"],
                         self.binding()[1]["execution_baseline"]["control_plane_digest"])

    def test_21_existing_unapproved_control_mutation_is_never_resealed(self):
        before = load_phase_boundary(self.root, self.run)
        fake = self.root / ".harness/runtime/UNTRUSTED_NEW.yaml"
        fake.write_text("unsafe: true\n", encoding="utf-8")
        with self.assertRaisesRegex(SafetyViolation, "integrity FAILED"):
            self.build()
        self.assertEqual(load_phase_boundary(self.root, self.run), before)
        self.assertEqual(check_control_plane(self.root, self.run)["status"], "FAIL")
        self.assertFalse((self.root / ".harness/runtime/EXECUTION_BINDINGS").exists())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from project_harness.evidence import (
    classify_evidence_document,
    normalized_evidence_body,
    write_normalized_evidence,
)
from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.registry import implementation_level_model
from project_harness.serialization import load_data, write_data
from project_harness.stages import _product_baseline_revision, accept_stage
from project_harness.validation import validate_project_directory

from tests.test_engine import load_fixture, prepare_demo
from tests.test_implementation_levels import (
    ACTOR,
    APPROVED_AT,
    closed_criteria,
    complete_prototype,
    current_gate,
    stage_approval,
    write_approval,
)


class GateEvidenceContractTests(unittest.TestCase):
    def _prepared_gate(self, base: Path) -> tuple[Path, dict]:
        data = load_fixture()
        data["implementation"]["target_level"] = "PROTOTYPE"
        _, _, root = prepare_demo(base, data=data)
        complete_prototype(root)
        return root, current_gate(root, "PROTOTYPE")

    def _write_evidence(
        self,
        root: Path,
        *,
        evidence_id: str,
        criterion_ref: str,
        kind: str,
        status: str = "PASS",
        base_revision: str | None = None,
        mapped_criterion_refs: list[str] | None = None,
        include_provenance: bool = True,
        legacy: bool = False,
    ) -> str:
        report_id = f"VAL-SOURCE-{evidence_id.removeprefix('EVD-')}"
        report_path = f".harness/reports/{report_id}.yaml"
        report = {
            "validation_report": {
                "id": report_id,
                "kind": "GATE_EVIDENCE_REGRESSION_SOURCE",
                "criterion_ref": criterion_ref,
                "status": status,
                "created_at": APPROVED_AT,
            }
        }
        write_data(root / report_path, report)
        if legacy:
            write_data(
                root / f".harness/evidence/{evidence_id}.yaml",
                {
                    "verification_evidence": {
                        "id": evidence_id,
                        "kind": kind,
                        "status": status,
                        "criterion_refs": mapped_criterion_refs or [criterion_ref],
                        "created_at": APPROVED_AT,
                    }
                },
            )
            return evidence_id

        body = normalized_evidence_body(
            evidence_id=evidence_id,
            kind=kind,
            status=status,
            provenance={
                "source_type": "REGRESSION_TEST_REPORT",
                "source_ref": report_id,
                "producer": "PROJECT_HARNESS_TEST_SUITE",
            },
            base_revision=base_revision or _product_baseline_revision(root),
            criterion_refs=mapped_criterion_refs or [criterion_ref],
            outcome_refs=[],
            profile_control_refs=[],
            source_bindings=[{
                "ref": report_id,
                "path": report_path,
                "sha256": f"sha256:{sha256_file(root / report_path)}",
            }],
            created_at=APPROVED_AT,
            report_refs=[report_id],
            rationale="Regression evidence fixture.",
            validator=ACTOR,
        )
        if include_provenance:
            write_normalized_evidence(root, body)
        else:
            malformed = deepcopy(body)
            malformed.pop("provenance")
            write_data(root / f".harness/evidence/{evidence_id}.yaml", {"verification_evidence": malformed})
        return evidence_id

    def _approval_with_first_ref(
        self,
        root: Path,
        gate: dict,
        evidence_ref: str,
        *,
        suffix: str,
        global_refs: list[str] | None = None,
    ) -> dict:
        results = closed_criteria(root, gate)
        results[0]["evidence_refs"] = [evidence_ref]
        approval = stage_approval(
            root,
            "PROTOTYPE",
            decision_suffix=suffix,
            criteria_results=results,
        )
        approval["stage_approval"]["evidence_refs"] = list(global_refs or [])
        return approval

    def test_dangling_evidence_ref_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, gate = self._prepared_gate(base)
            approval = self._approval_with_first_ref(
                root, gate, "EVD-DOES-NOT-EXIST", suffix="EVIDENCE-DANGLING-001"
            )
            with self.assertRaisesRegex(ValidationFailure, "absent at the exact canonical path"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "dangling.yaml", approval))

    def test_wrong_kind_and_wrong_subject_mapping_are_rejected(self) -> None:
        model = implementation_level_model()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, gate = self._prepared_gate(base)
            criterion = gate["criteria_results"][0]["criterion_ref"]
            wrong_kind = self._write_evidence(
                root,
                evidence_id="EVD-WRONG-KIND-001",
                criterion_ref=criterion,
                kind="ARCHITECTURE_RECORD",
            )
            approval = self._approval_with_first_ref(root, gate, wrong_kind, suffix="EVIDENCE-WRONG-KIND-001")
            with self.assertRaisesRegex(ValidationFailure, "kind does not satisfy"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "wrong-kind.yaml", approval))

            required_kind = model["criteria"][criterion]["required_evidence_kinds"][0]
            wrong_subject = self._write_evidence(
                root,
                evidence_id="EVD-WRONG-SUBJECT-001",
                criterion_ref=criterion,
                kind=required_kind,
                mapped_criterion_refs=[gate["criteria_results"][1]["criterion_ref"]],
            )
            approval = self._approval_with_first_ref(root, gate, wrong_subject, suffix="EVIDENCE-WRONG-SUBJECT-001")
            with self.assertRaisesRegex(ValidationFailure, "does not map the requested"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "wrong-subject.yaml", approval))

    def test_missing_provenance_stale_base_and_nonpositive_status_are_rejected(self) -> None:
        model = implementation_level_model()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, gate = self._prepared_gate(base)
            criterion = gate["criteria_results"][0]["criterion_ref"]
            kind = model["criteria"][criterion]["required_evidence_kinds"][0]

            missing_provenance = self._write_evidence(
                root,
                evidence_id="EVD-MISSING-PROVENANCE-001",
                criterion_ref=criterion,
                kind=kind,
                include_provenance=False,
            )
            approval = self._approval_with_first_ref(root, gate, missing_provenance, suffix="EVIDENCE-NO-PROVENANCE-001")
            with self.assertRaisesRegex(ValidationFailure, "not a valid normalized Gate artifact"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "missing-provenance.yaml", approval))

            stale = self._write_evidence(
                root,
                evidence_id="EVD-STALE-BASE-001",
                criterion_ref=criterion,
                kind=kind,
                base_revision="tree:sha256:" + "0" * 64,
            )
            approval = self._approval_with_first_ref(root, gate, stale, suffix="EVIDENCE-STALE-001")
            with self.assertRaisesRegex(ValidationFailure, "stale for this Gate baseline"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "stale.yaml", approval))

            for status in ("FAIL", "BLOCKED"):
                ref = self._write_evidence(
                    root,
                    evidence_id=f"EVD-{status}-STATUS-001",
                    criterion_ref=criterion,
                    kind=kind,
                    status=status,
                )
                approval = self._approval_with_first_ref(
                    root, gate, ref, suffix=f"EVIDENCE-{status}-001"
                )
                with self.subTest(status=status), self.assertRaisesRegex(ValidationFailure, "status cannot close"):
                    accept_stage(root, "PROTOTYPE", write_approval(base, f"{status.lower()}.yaml", approval))

    def test_exact_valid_evidence_and_global_ref_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, gate = self._prepared_gate(base)
            results = closed_criteria(root, gate)
            # Reuse one exact mapped criterion artifact as an explicit global Gate ref.
            global_ref = results[0]["evidence_refs"][0]
            approval = stage_approval(
                root,
                "PROTOTYPE",
                decision_suffix="EVIDENCE-VALID-001",
                criteria_results=results,
            )
            approval["stage_approval"]["evidence_refs"] = [global_ref]
            result = accept_stage(root, "PROTOTYPE", write_approval(base, "valid.yaml", approval))
            self.assertEqual(result["status"], "TARGET_LEVEL_REACHED")
            acceptance_path = next((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
            report = load_data(acceptance_path)["stage_acceptance"]
            self.assertEqual(
                sorted(report["evidence_refs"]),
                [item["ref"] for item in report["evidence_bindings"]],
            )
            self.assertTrue(all(item["sha256"].startswith("sha256:") for item in report["evidence_bindings"]))
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_global_dangling_or_wrong_mapping_ref_blocks_acceptance(self) -> None:
        model = implementation_level_model()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, gate = self._prepared_gate(base)
            approval = stage_approval(root, "PROTOTYPE", decision_suffix="GLOBAL-DANGLING-001")
            approval["stage_approval"]["evidence_refs"] = ["EVD-GLOBAL-DANGLING-001"]
            with self.assertRaisesRegex(ValidationFailure, "absent at the exact canonical path"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "global-dangling.yaml", approval))

            criterion = gate["criteria_results"][0]["criterion_ref"]
            kind = model["criteria"][criterion]["required_evidence_kinds"][0]
            ref = self._write_evidence(
                root,
                evidence_id="EVD-GLOBAL-NON-GATE-SUBJECT-001",
                criterion_ref=criterion,
                kind=kind,
                mapped_criterion_refs=["UNMATERIALIZED_OUTCOME_ONLY"],
            )
            approval = stage_approval(root, "PROTOTYPE", decision_suffix="GLOBAL-MAPPING-001")
            approval["stage_approval"]["evidence_refs"] = [ref]
            with self.assertRaisesRegex(ValidationFailure, "does not map a current mandatory subject"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "global-mapping.yaml", approval))

    def test_duplicate_conflicting_artifact_claiming_same_ref_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, gate = self._prepared_gate(base)
            criterion = gate["criteria_results"][0]["criterion_ref"]
            required_kind = implementation_level_model()["criteria"][criterion]["required_evidence_kinds"][0]
            ref = self._write_evidence(
                root,
                evidence_id="EVD-DUPLICATE-CONFLICT-001",
                criterion_ref=criterion,
                kind=required_kind,
            )
            canonical = load_data(root / f".harness/evidence/{ref}.yaml")
            conflicting = deepcopy(canonical)
            conflicting["verification_evidence"]["rationale"] = "Conflicting duplicate copy."
            write_data(root / ".harness/evidence/duplicate-conflicting-copy.yaml", conflicting)
            approval = self._approval_with_first_ref(
                root, gate, ref, suffix="EVIDENCE-DUPLICATE-CONFLICT-001"
            )
            with self.assertRaisesRegex(ValidationFailure, "Duplicate evidence artifact claims"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "duplicate.yaml", approval))

    def test_legacy_evidence_is_readable_but_cannot_close_new_gate(self) -> None:
        model = implementation_level_model()
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, gate = self._prepared_gate(base)
            criterion = gate["criteria_results"][0]["criterion_ref"]
            kind = model["criteria"][criterion]["required_evidence_kinds"][0]
            ref = self._write_evidence(
                root,
                evidence_id="EVD-LEGACY-001",
                criterion_ref=criterion,
                kind=kind,
                legacy=True,
            )
            legacy_doc = load_data(root / f".harness/evidence/{ref}.yaml")
            self.assertEqual(classify_evidence_document(root, legacy_doc)["classification"], "LEGACY")
            self.assertEqual(validate_project_directory(root)["status"], "PASS")
            approval = self._approval_with_first_ref(root, gate, ref, suffix="EVIDENCE-LEGACY-001")
            with self.assertRaisesRegex(ValidationFailure, "Legacy evidence is readable but not Gate-eligible"):
                accept_stage(root, "PROTOTYPE", write_approval(base, "legacy.yaml", approval))


    def test_explicit_unsupported_schema_version_is_invalid_not_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, gate = self._prepared_gate(base)
            criterion = gate["criteria_results"][0]["criterion_ref"]
            path = root / ".harness/evidence/EVD-UNSUPPORTED-SCHEMA-001.yaml"
            write_data(
                path,
                {
                    "verification_evidence": {
                        "schema_version": 2,
                        "id": "EVD-UNSUPPORTED-SCHEMA-001",
                        "ref": "EVD-UNSUPPORTED-SCHEMA-001",
                        "kind": "TEST_REPORT",
                        "status": "PASS",
                        "criterion_refs": [criterion],
                    }
                },
            )
            classified = classify_evidence_document(root, load_data(path))
            self.assertEqual(classified["classification"], "INVALID_NORMALIZED")
            validation = validate_project_directory(root)
            self.assertEqual(validation["status"], "FAIL")
            self.assertIn("Unsupported normalized evidence schema_version", str(validation["errors"]))

    def test_tampering_or_deletion_after_acceptance_fails_project_validation(self) -> None:
        for mutation in ("tamper", "delete"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                root, gate = self._prepared_gate(base)
                approval = stage_approval(root, "PROTOTYPE", decision_suffix=f"POST-ACCEPT-{mutation.upper()}-001")
                accept_stage(root, "PROTOTYPE", write_approval(base, f"{mutation}.yaml", approval))
                self.assertEqual(validate_project_directory(root)["status"], "PASS")
                acceptance = load_data(next((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")))["stage_acceptance"]
                binding = acceptance["evidence_bindings"][0]
                evidence_path = root / binding["path"]
                if mutation == "delete":
                    evidence_path.unlink()
                else:
                    doc = load_data(evidence_path)
                    doc["verification_evidence"]["rationale"] = "tampered after formal acceptance"
                    write_data(evidence_path, doc)
                validation = validate_project_directory(root)
                self.assertEqual(validation["status"], "FAIL")
                rendered_errors = str(validation["errors"])
                self.assertTrue(
                    "evidence binding changed after acceptance" in rendered_errors
                    or "evidence artifact is absent" in rendered_errors
                )

    def test_runtime_evidence_uses_exact_post_verification_product_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, _gate = self._prepared_gate(Path(temp))
            bodies = [
                load_data(path)["verification_evidence"]
                for path in sorted((root / ".harness/evidence").glob("EVD-*.yaml"))
                if (load_data(path).get("verification_evidence") or {}).get("run_ref")
                and (load_data(path).get("verification_evidence") or {}).get("kind") == "TEST_REPORT"
                and (load_data(path).get("verification_evidence") or {}).get("profile_control_refs") == ["RUNTIME_TASK_VERIFICATION"]
            ]
            self.assertGreaterEqual(len(bodies), 2)
            current = _product_baseline_revision(root)
            self.assertTrue(all(body["schema_version"] == 1 for body in bodies))
            self.assertTrue(all(body["kind"] == "TEST_REPORT" for body in bodies))
            self.assertTrue(all(body["criterion_refs"] == [] for body in bodies))
            self.assertTrue(all(body["profile_control_refs"] == ["RUNTIME_TASK_VERIFICATION"] for body in bodies))
            self.assertIn(current, {body["base_revision"] for body in bodies})
            self.assertTrue(any(body["base_revision"] != current for body in bodies))

            current_runtime = next(body for body in bodies if body["base_revision"] == current and body["status"] == "PASS")
            approval = self._approval_with_first_ref(
                root,
                current_gate(root, "PROTOTYPE"),
                current_runtime["ref"],
                suffix="RUNTIME-NOT-AUTO-MAPPED-001",
            )
            with self.assertRaisesRegex(ValidationFailure, "does not map the requested"):
                accept_stage(root, "PROTOTYPE", write_approval(Path(temp), "runtime-not-mapped.yaml", approval))


if __name__ == "__main__":
    unittest.main()

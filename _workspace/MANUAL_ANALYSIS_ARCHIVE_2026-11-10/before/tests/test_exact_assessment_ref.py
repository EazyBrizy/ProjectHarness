from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.registry import implementation_level_model
from project_harness.serialization import load_data, write_data
from project_harness.stages import _product_baseline_revision, accept_stage, assess_maturity
from project_harness.validation import validate_project_directory

from tests.test_engine import add_brownfield_approval, load_fixture, prepare_demo
from tests.test_implementation_levels import ACTOR, APPROVED_AT, closed_criteria, current_gate, write_approval


def file_tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def assessment_path(root: Path, assessment_ref: str) -> Path:
    return root / f".harness/stages/ASSESSMENTS/{assessment_ref}.yaml"


def prepare_brownfield_assessment(base: Path) -> tuple[Path, dict[str, object]]:
    data = load_fixture()
    data["project"]["mode"] = "BROWNFIELD"
    data["implementation"]["target_level"] = "PROTOTYPE"
    data["brownfield"]["baseline_summary"] = "Existing bounded local CLI repository."
    add_brownfield_approval(data)

    repository = base / "repository"
    repository.mkdir(parents=True)
    (repository / "README.md").write_text("# Existing CLI\n", encoding="utf-8")
    (repository / "existing.py").write_text("VALUE = 1\n", encoding="utf-8")
    _, _, root = prepare_demo(base / "prepared", data=data, repository=repository)

    baseline = _product_baseline_revision(root)
    refs = implementation_level_model()["profiles"]["PROTOTYPE"]["criteria_refs"]
    evidence = {
        "evidence": [
            {
                "id": f"EVD-B04-{index:03d}",
                "kind": implementation_level_model()["criteria"][ref]["required_evidence_kinds"][0],
                "criterion_refs": [ref],
                "status": "PASS",
                "provenance": "Exact immutable assessment_ref regression fixture.",
                "base_revision": baseline,
                "validator": ACTOR,
            }
            for index, ref in enumerate(refs, 1)
        ]
    }
    evidence_path = write_approval(base, "assessment-evidence.yaml", evidence)
    assessment = assess_maturity(root, evidence_path=evidence_path)
    if assessment["highest_satisfied_candidate_level"] != "PROTOTYPE":
        raise AssertionError(assessment)
    return root, assessment


def baseline_approval(
    root: Path,
    *,
    assessment_ref: object,
    assessment_digest: object,
    suffix: str,
) -> dict[str, object]:
    gate = current_gate(root, "PROTOTYPE")
    return {
        "stage_approval": {
            "id": f"DEC-HARNESS-DEMO-STAGE-B04-{suffix}",
            "approved": True,
            "actor": ACTOR,
            "approved_at": APPROVED_AT,
            "level": "PROTOTYPE",
            "acceptance_method": "SATISFIED_BY_BASELINE",
            "baseline_revision": _product_baseline_revision(root),
            "assessment_ref": assessment_ref,
            "assessment_digest": assessment_digest,
            "criteria_results": closed_criteria(root, gate),
            "evidence_refs": [],
            "permitted_use": {
                "users": ["INTERNAL_USER"],
                "environments": ["LOCAL", "DEV_TEST"],
                "data_classes": ["INTERNAL"],
                "data_constraints": ["NO_PRODUCTION_DATA"],
            },
            "known_limitations": ["Bounded local process only."],
            "next_stage_gaps": ["Plan the next stage from the accepted baseline."],
            "notes": "B-04 exact immutable assessment reference fixture.",
        }
    }


class ExactAssessmentRefTests(unittest.TestCase):
    def assert_rejected_without_mutation(
        self,
        root: Path,
        approval_path: Path,
        *,
        message: str | None = None,
    ) -> None:
        before = file_tree_snapshot(root)
        context = self.assertRaisesRegex(ValidationFailure, message) if message else self.assertRaises(ValidationFailure)
        with context:
            accept_stage(root, "PROTOTYPE", approval_path)
        self.assertEqual(file_tree_snapshot(root), before)

    def test_01_prefix_collision_at_1_and_at_10_is_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(base)
            ref1 = str(assessment["assessment_ref"])
            path1 = assessment_path(root, ref1)
            document10 = deepcopy(load_data(path1))
            document10["maturity_assessment"]["revision"] = 10
            ref10 = f"{document10['maturity_assessment']['id']}@10"
            path10 = assessment_path(root, ref10)
            write_data(path10, document10)
            digest10 = f"sha256:{sha256_file(path10)}"

            approval = baseline_approval(
                root,
                assessment_ref=ref1,
                assessment_digest=digest10,
                suffix="PREFIX-COLLISION-001",
            )
            approval_path = write_approval(base, "prefix-collision.yaml", approval)
            self.assert_rejected_without_mutation(root, approval_path, message="digest mismatch")
            self.assertEqual(list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")), [])

    def test_02_exact_revision_and_digest_pass_and_report_preserves_validated_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(base)
            exact_ref = str(assessment["assessment_ref"])
            approval = baseline_approval(
                root,
                assessment_ref=exact_ref,
                assessment_digest=assessment["assessment_digest"],
                suffix="EXACT-PASS-001",
            )
            result = accept_stage(root, "PROTOTYPE", write_approval(base, "exact-pass.yaml", approval))

            self.assertEqual(result["accepted_levels"], ["PROTOTYPE"])
            report_path = next((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
            report = load_data(report_path)["stage_acceptance"]
            self.assertEqual(report["acceptance_method"], "SATISFIED_BY_BASELINE")
            self.assertEqual(report["assessment_ref"], exact_ref)
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_03_unversioned_and_wildcard_like_refs_are_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(base)
            exact_ref = str(assessment["assessment_ref"])
            assessment_id = exact_ref.rsplit("@", 1)[0]
            malformed = [
                assessment_id,
                f"*{exact_ref}",
                f"{exact_ref}*",
                f"{exact_ref}?",
                f"{assessment_id}@01",
                f"{exact_ref}@10",
            ]
            for index, bad_ref in enumerate(malformed, 1):
                with self.subTest(assessment_ref=bad_ref):
                    approval = baseline_approval(
                        root,
                        assessment_ref=bad_ref,
                        assessment_digest=assessment["assessment_digest"],
                        suffix=f"MALFORMED-{index:03d}",
                    )
                    approval_path = write_approval(base, f"malformed-{index}.yaml", approval)
                    self.assert_rejected_without_mutation(root, approval_path, message="assessment_ref")

    def test_04_wrong_envelope_internal_id_and_internal_revision_are_rejected(self) -> None:
        mutations = {
            "wrong-envelope": lambda document: {"assessment": document["maturity_assessment"]},
            "extra-envelope-key": lambda document: {**document, "unexpected": {}},
            "internal-id": lambda document: {
                "maturity_assessment": {**document["maturity_assessment"], "id": "VAL-OTHER-MATURITY-001"}
            },
            "internal-revision": lambda document: {
                "maturity_assessment": {**document["maturity_assessment"], "revision": 10}
            },
        }
        for index, (name, mutate) in enumerate(mutations.items(), 1):
            with self.subTest(case=name), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                root, assessment = prepare_brownfield_assessment(base)
                exact_ref = str(assessment["assessment_ref"])
                exact_path = assessment_path(root, exact_ref)
                write_data(exact_path, mutate(deepcopy(load_data(exact_path))))
                matching_digest = f"sha256:{sha256_file(exact_path)}"
                approval = baseline_approval(
                    root,
                    assessment_ref=exact_ref,
                    assessment_digest=matching_digest,
                    suffix=f"INTERNAL-{index:03d}",
                )
                approval_path = write_approval(base, f"{name}.yaml", approval)
                self.assert_rejected_without_mutation(root, approval_path)

    def test_05_wrong_or_noncanonical_digest_is_rejected_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(base)
            exact_ref = str(assessment["assessment_ref"])
            invalid_digests = [
                "sha256:" + "0" * 64,
                "sha256:abcd",
                "SHA256:" + "0" * 64,
                "sha256:" + "A" * 64,
            ]
            for index, bad_digest in enumerate(invalid_digests, 1):
                with self.subTest(assessment_digest=bad_digest):
                    approval = baseline_approval(
                        root,
                        assessment_ref=exact_ref,
                        assessment_digest=bad_digest,
                        suffix=f"DIGEST-{index:03d}",
                    )
                    approval_path = write_approval(base, f"digest-{index}.yaml", approval)
                    self.assert_rejected_without_mutation(root, approval_path)


if __name__ == "__main__":
    unittest.main()

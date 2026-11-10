from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.registry import implementation_level_model
from project_harness.serialization import load_data, write_data
from project_harness.stages import (
    _product_baseline_revision,
    accept_stage,
    assess_maturity,
    level_up,
    load_stage_state,
    next_level,
)
from project_harness.validation import validate_project_directory

from tests.test_engine import add_brownfield_approval, load_fixture, prepare_demo
from tests.test_implementation_levels import ACTOR, APPROVED_AT, closed_criteria, current_gate, write_approval


def snapshot_without_assessments(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not path.relative_to(root).as_posix().startswith(".harness/stages/ASSESSMENTS/")
    }


def evidence_for_levels(root: Path, levels: tuple[str, ...], *, prefix: str) -> dict:
    baseline = _product_baseline_revision(root)
    model = implementation_level_model()
    refs: list[str] = []
    for level in levels:
        refs.extend(model["profiles"][level]["criteria_refs"])
    return {
        "evidence": [
            {
                "id": f"EVD-B03-{prefix}-{index:03d}",
                "kind": model["criteria"][ref]["required_evidence_kinds"][0],
                "criterion_refs": [ref],
                "status": "PASS",
                "provenance": "Exact current-tree Brownfield freshness fixture.",
                "base_revision": baseline,
                "validator": ACTOR,
            }
            for index, ref in enumerate(refs, 1)
        ]
    }


def prepare_brownfield_assessment(
    base: Path,
    *,
    target: str,
    satisfied_levels: tuple[str, ...],
    claimed: str = "UNKNOWN",
) -> tuple[Path, dict]:
    data = load_fixture()
    data["project"].update(
        {
            "name": "Brownfield Freshness Demo",
            "slug": "brownfield-freshness-demo",
            "mode": "BROWNFIELD",
        }
    )
    data["implementation"]["target_level"] = target
    data["brownfield"]["baseline_summary"] = "Existing bounded local CLI repository."
    add_brownfield_approval(data)
    data["implementation"]["claimed_current_level"] = claimed

    repository = base / "repository"
    repository.mkdir(parents=True)
    (repository / "README.md").write_text("# Existing CLI\n", encoding="utf-8")
    (repository / "existing.py").write_text("VALUE = 1\n", encoding="utf-8")
    _, _, root = prepare_demo(base / "prepared", data=data, repository=repository)

    evidence_path = write_approval(
        base,
        "assessment-evidence.yaml",
        evidence_for_levels(root, satisfied_levels, prefix="INITIAL"),
    )
    assessment = assess_maturity(root, evidence_path=evidence_path)
    expected = satisfied_levels[-1] if satisfied_levels else "NONE"
    if assessment["highest_satisfied_candidate_level"] != expected:
        raise AssertionError(assessment)
    if assessment["status"] != "COMPLETED":
        raise AssertionError(assessment)
    return root, assessment


def levels_for_request(root: Path, requested_level: str) -> list[str]:
    state = load_stage_state(root)
    accepted = state["highest_accepted_level"]
    start = next_level(str(accepted)) if accepted not in {"NONE", "UNKNOWN"} else "PROTOTYPE"
    if start is None:
        return []
    path = state["stage_path"]
    return path[path.index(start) : path.index(requested_level) + 1]


def baseline_approval(
    root: Path,
    *,
    assessment_ref: str,
    assessment_digest: str,
    requested_level: str,
    suffix: str,
    baseline_revision: str | None = None,
    invalid_level: str | None = None,
) -> dict:
    levels: dict[str, dict] = {}
    for level in levels_for_request(root, requested_level):
        gate = current_gate(root, level)
        criteria = closed_criteria(root, gate)
        if level == invalid_level:
            criteria = criteria[:-1]
        levels[level] = {
            "criteria_results": criteria,
            "evidence_refs": [],
            "permitted_use": {
                "users": ["INTERNAL_USER"],
                "environments": ["LOCAL", "DEV_TEST"],
                "data_classes": ["INTERNAL"],
                "data_constraints": ["NO_PRODUCTION_DATA"],
            },
            "known_limitations": [f"{level} limitations remain explicit."],
            "next_stage_gaps": [f"Plan the next stage after accepting {level}."],
        }
    return {
        "stage_approval": {
            "id": f"DEC-BROWNFIELD-FRESHNESS-{suffix}",
            "approved": True,
            "actor": ACTOR,
            "approved_at": APPROVED_AT,
            "level": requested_level,
            "acceptance_method": "SATISFIED_BY_BASELINE",
            "baseline_revision": baseline_revision or _product_baseline_revision(root),
            "assessment_ref": assessment_ref,
            "assessment_digest": assessment_digest,
            "levels": levels,
            "notes": "B-03 exact current-context baseline approval fixture.",
        }
    }


def copy_assessment_revision(
    root: Path,
    source_ref: str,
    revision: int,
    mutate,
) -> tuple[str, str, Path]:
    source_path = root / f".harness/stages/ASSESSMENTS/{source_ref}.yaml"
    document = deepcopy(load_data(source_path))
    document["maturity_assessment"]["revision"] = revision
    mutate(document["maturity_assessment"])
    ref = f"{document['maturity_assessment']['id']}@{revision}"
    output = root / f".harness/stages/ASSESSMENTS/{ref}.yaml"
    write_data(output, document)
    return ref, f"sha256:{sha256_file(output)}", output


class BrownfieldAssessmentFreshnessTests(unittest.TestCase):
    def test_01_tree_a_assessment_rejected_on_tree_b_with_zero_acceptance_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(
                base,
                target="PROTOTYPE",
                satisfied_levels=("PROTOTYPE",),
            )
            source_path = Path(assessment["assessment_path"])
            source_digest_before = sha256_file(source_path)
            tree_a = load_data(source_path)["maturity_assessment"]["repository_revision"]

            with (root / "existing.py").open("a", encoding="utf-8") as stream:
                stream.write("VALUE_B = 2\n")
            tree_b = _product_baseline_revision(root)
            self.assertNotEqual(tree_a, tree_b)

            approval = baseline_approval(
                root,
                assessment_ref=assessment["assessment_ref"],
                assessment_digest=assessment["assessment_digest"],
                requested_level="PROTOTYPE",
                suffix="TREE-DRIFT-001",
                baseline_revision=tree_b,
            )
            before = snapshot_without_assessments(root)
            result = accept_stage(root, "PROTOTYPE", write_approval(base, "tree-drift.yaml", approval))

            self.assertEqual(result["status"], "STALE")
            self.assertIn("ASSESSMENT_REPOSITORY_REVISION_MISMATCH", result["reason_codes"])
            self.assertEqual(result["assessment_context"]["repository_revision"], tree_a)
            self.assertEqual(result["current_context"]["repository_revision"], tree_b)
            self.assertEqual(snapshot_without_assessments(root), before)
            self.assertEqual(sha256_file(source_path), source_digest_before)
            self.assertEqual(result["acceptance_mutation"]["acceptance_reports_created"], [])
            self.assertFalse(result["acceptance_mutation"]["highest_accepted_level_changed"])
            self.assertEqual(list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")), [])
            self.assertFalse((root / ".harness/canonical/DECISIONS/DEC-BROWNFIELD-FRESHNESS-TREE-DRIFT-001@1.yaml").exists())

            stale_record = load_data(Path(result["staleness_record_path"]))["maturity_assessment"]
            self.assertEqual(stale_record["source_assessment_ref"], assessment["assessment_ref"])
            self.assertEqual(stale_record["repository_revision"], tree_a)
            self.assertEqual(stale_record["staleness"]["original_repository_revision"], tree_a)
            self.assertEqual(stale_record["staleness"]["detected_current_repository_revision"], tree_b)
            # The project remains between governed phase-boundary commits after
            # assess-maturity; this test intentionally validates only the zero
            # acceptance mutation contract and immutable STALE record.

    def test_02_reassessment_for_tree_b_restores_baseline_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment_a = prepare_brownfield_assessment(
                base,
                target="PROTOTYPE",
                satisfied_levels=("PROTOTYPE",),
            )
            with (root / "existing.py").open("a", encoding="utf-8") as stream:
                stream.write("VALUE_B = 2\n")

            stale = accept_stage(
                root,
                "PROTOTYPE",
                write_approval(
                    base,
                    "tree-a-approval.yaml",
                    baseline_approval(
                        root,
                        assessment_ref=assessment_a["assessment_ref"],
                        assessment_digest=assessment_a["assessment_digest"],
                        requested_level="PROTOTYPE",
                        suffix="TREE-A-001",
                    ),
                ),
            )
            self.assertEqual(stale["status"], "STALE")

            evidence_b = write_approval(
                base,
                "tree-b-evidence.yaml",
                evidence_for_levels(root, ("PROTOTYPE",), prefix="TREE-B"),
            )
            assessment_b = assess_maturity(root, evidence_path=evidence_b)
            self.assertEqual(assessment_b["status"], "COMPLETED")
            self.assertEqual(
                load_data(Path(assessment_b["assessment_path"]))["maturity_assessment"]["repository_revision"],
                _product_baseline_revision(root),
            )
            self.assertNotEqual(assessment_b["assessment_ref"], assessment_a["assessment_ref"])

            accepted = accept_stage(
                root,
                "PROTOTYPE",
                write_approval(
                    base,
                    "tree-b-approval.yaml",
                    baseline_approval(
                        root,
                        assessment_ref=assessment_b["assessment_ref"],
                        assessment_digest=assessment_b["assessment_digest"],
                        requested_level="PROTOTYPE",
                        suffix="TREE-B-001",
                    ),
                ),
            )
            self.assertEqual(accepted["status"], "TARGET_LEVEL_REACHED")
            report = load_data(next((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")))["stage_acceptance"]
            self.assertEqual(report["assessment_ref"], assessment_b["assessment_ref"])
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_03_target_change_after_assessment_marks_old_context_stale(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, old_assessment = prepare_brownfield_assessment(
                base,
                target="PROTOTYPE",
                satisfied_levels=("PROTOTYPE", "ALPHA"),
            )
            accept_stage(
                root,
                "PROTOTYPE",
                write_approval(
                    base,
                    "prototype-accept.yaml",
                    baseline_approval(
                        root,
                        assessment_ref=old_assessment["assessment_ref"],
                        assessment_digest=old_assessment["assessment_digest"],
                        requested_level="PROTOTYPE",
                        suffix="TARGET-BASE-001",
                    ),
                ),
            )
            level_up_approval = {
                "level_up_approval": {
                    "id": "DEC-BROWNFIELD-FRESHNESS-TARGET-UP-001",
                    "approved": True,
                    "actor": ACTOR,
                    "approved_at": APPROVED_AT,
                    "target_level": "ALPHA",
                    "rationale": "Change the canonical current target after assessment.",
                }
            }
            level_up(root, "ALPHA", write_approval(base, "target-up.yaml", level_up_approval))

            result = accept_stage(
                root,
                "ALPHA",
                write_approval(
                    base,
                    "old-target-assessment.yaml",
                    baseline_approval(
                        root,
                        assessment_ref=old_assessment["assessment_ref"],
                        assessment_digest=old_assessment["assessment_digest"],
                        requested_level="ALPHA",
                        suffix="TARGET-DRIFT-001",
                    ),
                ),
            )
            self.assertEqual(result["status"], "STALE")
            self.assertIn("ASSESSMENT_TARGET_LEVEL_MISMATCH", result["reason_codes"])
            self.assertEqual(result["assessment_context"]["target_level"], "PROTOTYPE")
            self.assertEqual(result["current_context"]["target_level"], "ALPHA")
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "PROTOTYPE")
            self.assertEqual(load_stage_state(root)["active_stage"], "ALPHA")

    def test_04_previous_accepted_level_change_invalidates_old_assessment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(
                base,
                target="ALPHA",
                satisfied_levels=("PROTOTYPE", "ALPHA"),
            )
            accept_stage(
                root,
                "PROTOTYPE",
                write_approval(
                    base,
                    "prototype-only.yaml",
                    baseline_approval(
                        root,
                        assessment_ref=assessment["assessment_ref"],
                        assessment_digest=assessment["assessment_digest"],
                        requested_level="PROTOTYPE",
                        suffix="PREVIOUS-BASE-001",
                    ),
                ),
            )
            approval = write_approval(
                base,
                "old-previous.yaml",
                baseline_approval(
                    root,
                    assessment_ref=assessment["assessment_ref"],
                    assessment_digest=assessment["assessment_digest"],
                    requested_level="ALPHA",
                    suffix="PREVIOUS-DRIFT-001",
                ),
            )
            before = snapshot_without_assessments(root)
            result = accept_stage(root, "ALPHA", approval)
            self.assertEqual(result["status"], "STALE")
            self.assertIn("ASSESSMENT_PREVIOUS_ACCEPTED_LEVEL_MISMATCH", result["reason_codes"])
            self.assertEqual(snapshot_without_assessments(root), before)
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "PROTOTYPE")
            self.assertEqual(len(list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))), 1)

    def test_05_claimed_context_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(
                base,
                target="PROTOTYPE",
                satisfied_levels=("PROTOTYPE",),
                claimed="UNKNOWN",
            )
            mismatched_ref, mismatched_digest, _ = copy_assessment_revision(
                root,
                assessment["assessment_ref"],
                2,
                lambda body: body.__setitem__("claimed_current_level", "ALPHA"),
            )
            result = accept_stage(
                root,
                "PROTOTYPE",
                write_approval(
                    base,
                    "claim-mismatch.yaml",
                    baseline_approval(
                        root,
                        assessment_ref=mismatched_ref,
                        assessment_digest=mismatched_digest,
                        requested_level="PROTOTYPE",
                        suffix="CLAIM-MISMATCH-001",
                    ),
                ),
            )
            self.assertEqual(result["status"], "STALE")
            self.assertIn("ASSESSMENT_CLAIMED_LEVEL_MISMATCH", result["reason_codes"])
            self.assertEqual(result["assessment_context"]["claimed_current_level"], "ALPHA")
            self.assertEqual(result["current_context"]["claimed_current_level"], "UNKNOWN")
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "NONE")

    def test_06_stale_external_evidence_cannot_close_baseline_criteria(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            data = load_fixture()
            data["project"].update({"name": "Stale Evidence Demo", "slug": "stale-evidence-demo", "mode": "BROWNFIELD"})
            data["implementation"]["target_level"] = "PROTOTYPE"
            data["brownfield"]["baseline_summary"] = "Existing repository."
            add_brownfield_approval(data)
            repository = base / "repository"
            repository.mkdir()
            (repository / "existing.py").write_text("VALUE = 1\n", encoding="utf-8")
            _, _, root = prepare_demo(base / "prepared", data=data, repository=repository)

            model = implementation_level_model()
            refs = model["profiles"]["PROTOTYPE"]["criteria_refs"]
            stale_evidence = {
                "evidence": [
                    {
                        "id": f"EVD-B03-STALE-{index:03d}",
                        "kind": model["criteria"][ref]["required_evidence_kinds"][0],
                        "criterion_refs": [ref],
                        "status": "PASS",
                        "provenance": "Evidence from another product tree.",
                        "base_revision": "tree:sha256:" + "0" * 64,
                        "validator": ACTOR,
                    }
                    for index, ref in enumerate(refs, 1)
                ]
            }
            stale = assess_maturity(root, evidence_path=write_approval(base, "stale-evidence.yaml", stale_evidence))
            self.assertEqual(stale["status"], "STALE")
            self.assertEqual(stale["highest_satisfied_candidate_level"], "NONE")

            def forge_completed(body: dict) -> None:
                body["status"] = "COMPLETED"
                body["highest_satisfied_candidate_level"] = "PROTOTYPE"
                for item in body["criteria_results"]["PROTOTYPE"]:
                    item["status"] = "PASS"
                    if not item.get("evidence_refs"):
                        item["evidence_refs"] = [f"EVD-B03-STALE-{refs.index(item['criterion_ref']) + 1:03d}"]
                    item["rationale"] = "Forged closure using stale evidence."
                    item["validator"] = ACTOR

            forged_ref, forged_digest, _ = copy_assessment_revision(
                root,
                stale["assessment_ref"],
                2,
                forge_completed,
            )
            result = accept_stage(
                root,
                "PROTOTYPE",
                write_approval(
                    base,
                    "forged-stale-approval.yaml",
                    baseline_approval(
                        root,
                        assessment_ref=forged_ref,
                        assessment_digest=forged_digest,
                        requested_level="PROTOTYPE",
                        suffix="STALE-EVIDENCE-001",
                    ),
                ),
            )
            self.assertEqual(result["status"], "STALE")
            self.assertTrue(
                {"STALE_EVIDENCE_USED_FOR_MANDATORY_CRITERIA", "ASSESSMENT_STALE_EVIDENCE_WARNING"}
                & set(result["reason_codes"])
            )
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "NONE")
            self.assertEqual(list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")), [])

    def test_07_multi_level_acceptance_is_atomic_for_one_exact_current_assessment(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(
                base,
                target="ALPHA",
                satisfied_levels=("PROTOTYPE", "ALPHA"),
            )
            invalid = baseline_approval(
                root,
                assessment_ref=assessment["assessment_ref"],
                assessment_digest=assessment["assessment_digest"],
                requested_level="ALPHA",
                suffix="ATOMIC-INVALID-001",
                invalid_level="ALPHA",
            )
            before = snapshot_without_assessments(root)
            with self.assertRaises(ValidationFailure):
                accept_stage(root, "ALPHA", write_approval(base, "atomic-invalid.yaml", invalid))
            self.assertEqual(snapshot_without_assessments(root), before)
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "NONE")
            self.assertEqual(list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")), [])

            valid = baseline_approval(
                root,
                assessment_ref=assessment["assessment_ref"],
                assessment_digest=assessment["assessment_digest"],
                requested_level="ALPHA",
                suffix="ATOMIC-VALID-001",
            )
            result = accept_stage(root, "ALPHA", write_approval(base, "atomic-valid.yaml", valid))
            self.assertEqual(result["status"], "TARGET_LEVEL_REACHED")
            self.assertEqual(result["accepted_levels"], ["PROTOTYPE", "ALPHA"])
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "ALPHA")
            reports = list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
            self.assertEqual(len(reports), 2)
            self.assertEqual(
                {load_data(path)["stage_acceptance"]["assessment_ref"] for path in reports},
                {assessment["assessment_ref"]},
            )
            self.assertEqual(validate_project_directory(root)["status"], "PASS")


    def test_08_approval_baseline_revision_must_equal_current_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(
                base,
                target="PROTOTYPE",
                satisfied_levels=("PROTOTYPE",),
            )
            wrong_baseline = "tree:sha256:" + "0" * 64
            approval = write_approval(
                base,
                "approval-baseline-mismatch.yaml",
                baseline_approval(
                    root,
                    assessment_ref=assessment["assessment_ref"],
                    assessment_digest=assessment["assessment_digest"],
                    requested_level="PROTOTYPE",
                    suffix="APPROVAL-BASE-MISMATCH-001",
                    baseline_revision=wrong_baseline,
                ),
            )
            before = snapshot_without_assessments(root)
            result = accept_stage(root, "PROTOTYPE", approval)
            self.assertEqual(result["status"], "STALE")
            self.assertIn("APPROVAL_BASELINE_REVISION_MISMATCH", result["reason_codes"])
            self.assertEqual(result["current_context"]["approval_baseline_revision"], wrong_baseline)
            self.assertEqual(result["issues"][0]["expected"], _product_baseline_revision(root))
            self.assertEqual(snapshot_without_assessments(root), before)
            self.assertEqual(list((root / ".harness/stages/ACCEPTANCE").glob("*.yaml")), [])

    def test_09_non_completed_assessment_cannot_authorize_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(
                base,
                target="PROTOTYPE",
                satisfied_levels=("PROTOTYPE",),
            )
            stale_ref, stale_digest, _ = copy_assessment_revision(
                root,
                assessment["assessment_ref"],
                2,
                lambda body: body.__setitem__("status", "STALE"),
            )
            approval = write_approval(
                base,
                "non-completed-assessment.yaml",
                baseline_approval(
                    root,
                    assessment_ref=stale_ref,
                    assessment_digest=stale_digest,
                    requested_level="PROTOTYPE",
                    suffix="NOT-COMPLETED-001",
                ),
            )
            before = snapshot_without_assessments(root)
            result = accept_stage(root, "PROTOTYPE", approval)
            self.assertEqual(result["status"], "STALE")
            self.assertIn("ASSESSMENT_NOT_COMPLETED", result["reason_codes"])
            self.assertEqual(snapshot_without_assessments(root), before)
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "NONE")

    def test_10_requested_level_cannot_exceed_recomputed_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root, assessment = prepare_brownfield_assessment(
                base,
                target="ALPHA",
                satisfied_levels=("PROTOTYPE",),
            )
            approval = write_approval(
                base,
                "candidate-exceeded.yaml",
                baseline_approval(
                    root,
                    assessment_ref=assessment["assessment_ref"],
                    assessment_digest=assessment["assessment_digest"],
                    requested_level="ALPHA",
                    suffix="CANDIDATE-EXCEEDED-001",
                ),
            )
            before = snapshot_without_assessments(root)
            result = accept_stage(root, "ALPHA", approval)
            self.assertEqual(result["status"], "STALE")
            self.assertIn("REQUESTED_LEVEL_EXCEEDS_ASSESSMENT_CANDIDATE", result["reason_codes"])
            self.assertEqual(result["assessment_context"]["highest_satisfied_candidate_level"], "PROTOTYPE")
            self.assertEqual(snapshot_without_assessments(root), before)
            self.assertEqual(load_stage_state(root)["highest_accepted_level"], "NONE")


if __name__ == "__main__":
    unittest.main()

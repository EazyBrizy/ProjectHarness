"""PH-F01 regression fixtures: public-route materialization, no engine mutations.

Only test fixtures use the synthesized Brownfield evidence. It demonstrates the
mechanical governance route; it is NOT independent proof of MVP product quality.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from project_harness.resources import distribution_root
from project_harness.serialization import write_data
from project_harness.stages import accept_stage, assess_maturity

from tests.test_engine import prepare_demo
from tests.test_implementation_levels import complete_prototype, stage_approval, write_approval
from tests.test_assessment_freshness import baseline_approval, evidence_for_levels

FIXTURES = distribution_root() / "tests" / "fixtures" / "ph_f01"


def contracts() -> dict[str, Any]:
    return json.loads((FIXTURES / "fixture_contracts.json").read_text(encoding="utf-8"))


def input_document(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def build_greenfield_mvp(base: Path) -> Path:
    """Independent target-MVP Greenfield input -> public prepare handoff."""
    _, _, root = prepare_demo(base, data=input_document("greenfield_mvp_project_input.json"))
    return root


def build_brownfield(base: Path) -> Path:
    """Independent source snapshot + five approvals -> public prepare handoff."""
    repository = base / "repository"
    repository.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURES / "brownfield_repository", repository)
    _, _, root = prepare_demo(
        base / "compiled", data=input_document("brownfield_project_input.json"), repository=repository
    )
    return root


def build_accepted_prototype(base: Path) -> Path:
    """Prototype via ordinary Task/JIT -> Gate preparation -> formal acceptance.

    Uses current-version Gate fixtures, which predate the PH-F02 semantic fix;
    this asserts a syntactically accepted state, not semantic proof quality.
    """
    root = build_greenfield_mvp(base / "greenfield")
    complete_prototype(root)
    decision = stage_approval(root, "PROTOTYPE", decision_suffix="PH-F01-PROTOTYPE-001")
    result = accept_stage(root, "PROTOTYPE", write_approval(base, "accepted-prototype.yaml", decision))
    if result.get("highest_accepted_level") != "PROTOTYPE" or result.get("active_stage") != "ALPHA":
        raise AssertionError({"fixture": "ACCEPTED_PROTOTYPE", "result": result})
    return root


def build_target_reached_mvp(base: Path) -> Path:
    """MVP target reached through supported Brownfield assessment + approval.

    The synthetic supplied evidence exercises the governance *state* plumbing
    without claiming the tiny repository really satisfies MVP requirements.
    Future PH-F02 must reject semantically inadequate evidence in real Gates.
    """
    root = build_brownfield(base / "brownfield")
    provided = evidence_for_levels(root, ("PROTOTYPE", "ALPHA", "BETA", "MVP"), prefix="PHF01")
    evidence_path = write_approval(base, "synthetic-assessment-evidence.yaml", provided)
    assessment = assess_maturity(root, evidence_path=evidence_path)
    if assessment.get("status") != "COMPLETED" or assessment.get("highest_satisfied_candidate_level") != "MVP":
        raise AssertionError({"fixture": "TARGET_LEVEL_REACHED", "assessment": assessment})
    approval = baseline_approval(
        root,
        assessment_ref=assessment["assessment_ref"],
        assessment_digest=assessment["assessment_digest"],
        requested_level="MVP",
        suffix="PH-F01-MVP-001",
    )
    accepted = accept_stage(root, "MVP", write_approval(base, "accepted-mvp.yaml", approval))
    if accepted.get("status") != "TARGET_LEVEL_REACHED" or accepted.get("highest_accepted_level") != "MVP":
        raise AssertionError({"fixture": "TARGET_LEVEL_REACHED", "acceptance": accepted})
    return root

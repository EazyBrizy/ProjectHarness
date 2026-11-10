"""PH-F02 fixture helpers: pinned subject documents, selected executed checks,
operator attestations and supplied external sources (not generic PASS clones).

The fixture authority is explicitly synthetic and never used by the engine.
"""
from __future__ import annotations
from pathlib import Path
import re
import subprocess
import sys
from project_harness.evidence import gate_proof_methods, normalized_evidence_body, write_normalized_evidence
from project_harness.hashing import sha256_file
from project_harness.serialization import write_data
from project_harness.stages import product_baseline_revision, _current_stage_gate_context, _stage_contract_definitions

ACTOR = "ACT-PH-F02-REVIEWER-001"
ISSUER = "PH-F02-THIRD-PARTY-FIXTURE"


def proof_for_subject(root: Path, subject: str, kind: str, *, mapping: str = "criterion_refs", source_in_product: bool = False) -> str:
    subject_token = re.sub(r"[^A-Z0-9-]", "-", subject.upper())
    # Re-assessment of a changed product must produce a *new* immutable
    # attestation; an old EVD must remain stale, never silently rebound.
    token = f"{subject_token}-{product_baseline_revision(root)[-12:].upper()}"
    evidence_id = f"EVD-PHF02-{token}"
    evidence_path = root / f".harness/evidence/{evidence_id}.yaml"
    if evidence_path.is_file():
        return evidence_id
    method = gate_proof_methods(kind)[0]
    source_ref = f"SRC-PHF02-{token}"
    checks = [f"Reviewed or executed a selected {kind} check for {subject}"]
    source_rel = f"docs/gate-proofs/{token}.md" if source_in_product and method == 'DOCUMENT_REVIEW' else f".harness/operator/SOURCES/{token}.yaml" if method != 'DOCUMENT_REVIEW' else f".harness/operator/SOURCES/{token}.md"
    source = root / source_rel
    source.parent.mkdir(parents=True, exist_ok=True)
    details = {"subject_ref": subject, "kind": kind, "method": method, "status": "PASS", "coverage": f"Concrete bounded demonstration of {subject} on the final project baseline", "source_ref": source_ref, "checked_items": checks}
    provenance = {"source_type": "OPERATOR_SUPPLIED_DOCUMENT" if method == 'DOCUMENT_REVIEW' else "INDEPENDENT_TEST_EXECUTION" if method == 'EXECUTED_TEST' else "INDEPENDENT_OPERATOR_REVIEW" if method == 'OPERATOR_VERIFICATION' else "EXTERNAL_EVIDENCE_IMPORT", "source_ref": source_ref, "producer": "PH_F02_TEST_FIXTURE", "actor": ACTOR}
    if method == "DOCUMENT_REVIEW":
        text = f"# {kind} — {subject}\n\nReviewed project artifact for the exact stated subject {subject}.\\nThis document records the tested local implementation and its supported scope.\n\n## Architecture and component boundaries\nThe task CLI contains one component with a simple architecture boundary, and uses a local JSON data file.\n\n## Local start and run command\nRun command `python task_cli.py list`; install Python first and run local tests after installation.\n\n## Known limitations and next steps\nKnown limitations: no concurrency, production authorization or distributed recovery; next steps require separate approval.\n\n## Permitted environments and data\nPermitted use is local development in the LOCAL environment with synthetic data only; production data is not permitted.\n"
        source.write_text(text, encoding='utf-8')
    elif method == "EXECUTED_TEST":
        # Run a selected real unit test for core flow/smoke; not py_compile or
        # an unscoped test-suite PASS. The command identifies the exact test.
        if (root / "tests/test_task_cli.py").is_file():
            test_ref = "test_add_and_list" if "CORE" in subject or "FLOW" in subject else "test_complete_and_unknown_id"
            command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-t', 'tests', '-p', 'test_task_cli.py', '-k', test_ref]
        else:
            # A Brownfield test fixture supplies its own read-only external
            # verification command. The engine's assessment does not execute it.
            test_ref = f"test_existing_{token.lower().replace('-', '_')}"
            script = root / f".harness/operator/SOURCES/{test_ref}.py"
            script.write_text("""from pathlib import Path
import sys
root = Path(sys.argv[1])
assert (root / 'existing.py').is_file(), 'Expected existing Brownfield module'
assert 'VALUE = 1' in (root / 'existing.py').read_text(), 'Existing module contract'
assert (root / 'existing.py').stat().st_size > 0, 'Expected nonempty Brownfield implementation'
print('1 selected Brownfield verification passed')
""", encoding='utf-8')
            command = [sys.executable, str(script), str(root)]
        run = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=25, check=False)
        if run.returncode != 0 or not ("Ran 1 test" in (run.stdout + run.stderr) or "1 selected Brownfield verification passed" in (run.stdout + run.stderr)):
            raise AssertionError({"command": command, "returncode": run.returncode, "stderr": run.stderr})
        details['test_ref'] = test_ref
        write_data(source, {"test_execution": {"subject_ref": subject, "test_ref": test_ref, "status": "PASS", "exit_code": run.returncode, "command": command, "checks": checks, "output": run.stdout + run.stderr}})
    elif method == "OPERATOR_VERIFICATION":
        write_data(source, {"operator_verification": {"subject_ref": subject, "status": "PASS", "actor": ACTOR, "checks": checks, "rationale": "The exact subject was evaluated separately by the fixture reviewer."}})
    else:
        provenance['details'] = {"issuer": ISSUER, "origin": "fixture://PH-F02/independently-supplied-record"}
        write_data(source, {"external_evidence": {"subject_ref": subject, "status": "PASS", "issuer": ISSUER, "checks": checks, "rationale": "A third-party source supplied solely for the test fixture."}})
    body = normalized_evidence_body(
        evidence_id=evidence_id, kind=kind, status="PASS", provenance=provenance,
        base_revision=product_baseline_revision(root), criterion_refs=[subject] if mapping == 'criterion_refs' else [],
        outcome_refs=[subject] if mapping == 'outcome_refs' else [],
        profile_control_refs=[subject] if mapping == 'profile_control_refs' else [],
        source_bindings=[{"ref": source_ref, "path": source_rel, "sha256": f"sha256:{sha256_file(source)}"}],
        created_at="2026-08-19T12:00:00Z", rationale=f"Selected {method} evidence for {subject}; fixture review only.",
        validator=ACTOR, details={"semantic_proof": details},
    )
    write_normalized_evidence(root, body)
    return evidence_id


def all_gate_subjects(root: Path, *, source_in_product: bool = False) -> dict[str, str]:
    context = _current_stage_gate_context(root)
    defs = _stage_contract_definitions(context)
    result = {}
    for item in defs['level_criteria']:
        subject = item['criterion_ref']
        result[subject] = proof_for_subject(root, subject, item['required_evidence_kinds'][0], source_in_product=source_in_product)
    for item in defs['hard_constraints']:
        subject = item['constraint_ref']
        result[subject] = proof_for_subject(root, subject, item['required_evidence_kinds'][0], source_in_product=source_in_product)
    for item in defs['required_outcomes']:
        subject = item['outcome_ref']
        result[subject] = proof_for_subject(root, subject, 'REVIEW_RECORD', mapping='outcome_refs')
    for item in defs['profile_controls']:
        subject = item['control_ref']
        result[subject] = proof_for_subject(root, subject, 'REVIEW_RECORD', mapping='profile_control_refs')
    return result

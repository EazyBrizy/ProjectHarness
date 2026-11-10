"""PH-F02: semantic Gate evidence must be independently reviewable and exact-bound."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from project_harness.evidence import resolve_evidence_artifact, validate_semantic_gate_proof
from project_harness.errors import ValidationFailure
from project_harness.serialization import load_data
from tests.gate_proof_fixtures import proof_for_subject
from tests.test_engine import load_fixture, prepare_demo, implement_first_task


class PHF02SemanticProofContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory(prefix='phf02-semantic-')
        data = load_fixture()
        data['implementation']['target_level'] = 'PROTOTYPE'
        _, _, cls.root = prepare_demo(Path(cls.tmp.name), data=data)
        implement_first_task(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_real_document_proof_has_exact_subject_and_source_integrity(self):
        ref = proof_for_subject(self.root, 'PROTOTYPE_SIMPLE_ARCHITECTURE', 'ARCHITECTURE_RECORD')
        body = resolve_evidence_artifact(self.root, ref, verify_sources=True)['body']
        validate_semantic_gate_proof(self.root, body, subject_ref='PROTOTYPE_SIMPLE_ARCHITECTURE')
        with self.assertRaisesRegex(ValidationFailure, 'exact-bound'):
            validate_semantic_gate_proof(self.root, body, subject_ref='PROTOTYPE_LIMITATIONS')

    def test_user_claim_or_generic_runtime_pass_never_certifies_document(self):
        ref = proof_for_subject(self.root, 'PROTOTYPE_LIMITATIONS', 'LIMITATIONS_RECORD')
        body = resolve_evidence_artifact(self.root, ref, verify_sources=True)['body']
        for source_type in ('USER_DECLARATION', 'STAGE_ACCEPTANCE_PREPARATION_VERIFICATION', 'PROJECT_HARNESS_RUNTIME'):
            altered = deepcopy(body)
            altered['provenance']['source_type'] = source_type
            with self.subTest(source_type=source_type), self.assertRaises(ValidationFailure):
                validate_semantic_gate_proof(self.root, altered, subject_ref='PROTOTYPE_LIMITATIONS')

    def test_no_test_level_coverage_cannot_certify_test_report(self):
        ref = proof_for_subject(self.root, 'PROTOTYPE_CORE_FLOW', 'TEST_REPORT')
        body = resolve_evidence_artifact(self.root, ref, verify_sources=True)['body']
        validate_semantic_gate_proof(self.root, body, subject_ref='PROTOTYPE_CORE_FLOW')
        for replacement in ({}, {'test_ref': 'py_compile'}, {'test_ref': 'nonexistent_case'}):
            altered = deepcopy(body)
            altered['details']['semantic_proof'].update(replacement)
            if not replacement:
                altered['details']['semantic_proof'].pop('test_ref', None)
            with self.subTest(replacement=replacement), self.assertRaises(ValidationFailure):
                validate_semantic_gate_proof(self.root, altered, subject_ref='PROTOTYPE_CORE_FLOW')

    def test_external_issuer_and_subject_are_not_interchangeable(self):
        ref = proof_for_subject(self.root, 'PHF02-EXTERNAL-REQUIREMENT', 'EXTERNAL_EVIDENCE')
        body = resolve_evidence_artifact(self.root, ref, verify_sources=True)['body']
        validate_semantic_gate_proof(self.root, body, subject_ref='PHF02-EXTERNAL-REQUIREMENT')
        for field, value in [('source_type', 'USER_DECLARATION'), ('source_type', 'PROJECT_HARNESS_RUNTIME')]:
            altered = deepcopy(body)
            altered['provenance'][field] = value
            with self.subTest(value=value), self.assertRaises(ValidationFailure):
                validate_semantic_gate_proof(self.root, altered, subject_ref='PHF02-EXTERNAL-REQUIREMENT')

    def test_source_tamper_prevents_evidence_resolution(self):
        ref = proof_for_subject(self.root, 'PROTOTYPE_PERMITTED_USE', 'PERMITTED_USE_RECORD')
        artifact = resolve_evidence_artifact(self.root, ref, verify_sources=True)
        src = self.root / artifact['body']['source_bindings'][0]['path']
        src.write_text(src.read_text(encoding='utf8') + '\nTAMPERED\n', encoding='utf8')
        with self.assertRaisesRegex(ValidationFailure, 'not a valid normalized Gate artifact|digest mismatch'):
            resolve_evidence_artifact(self.root, ref, verify_sources=True)


if __name__ == '__main__':
    unittest.main()

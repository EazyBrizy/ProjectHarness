from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest

from project_harness.compiler import prepare_handoff
from project_harness.errors import SafetyViolation
from project_harness.intake import check_intake, start_intake
from project_harness.project_input import approvals_for_mode, questions_for, validate_project_input
from project_harness.serialization import load_data, write_data
from project_harness.validation import validate_handoff
from tests.test_engine import load_fixture


class PHF05IntakeAcceptance(unittest.TestCase):
    def test_approval_counts_question_order_and_transitions(self):
        value = load_fixture()
        self.assertEqual(len(approvals_for_mode('GREENFIELD')), 4)
        self.assertEqual(len(approvals_for_mode('HYBRID')), 5)
        self.assertEqual(len(approvals_for_mode('BROWNFIELD')), 5)
        for decision, expected in [('UNSURE', 'WAITING_DECISION'), ('MVP', 'READY_FOR_HANDOFF')]:
            candidate = deepcopy(value)
            candidate['implementation']['target_level'] = decision
            result = validate_project_input(candidate, require_approvals=True)
            self.assertEqual(result['status'], expected, result)
        candidate = deepcopy(value)
        candidate['project']['data']['sensitivity'] = 'UNKNOWN'
        self.assertEqual(validate_project_input(candidate, require_approvals=True)['status'], 'WAITING_INPUT')
        candidate = deepcopy(value)
        candidate['approvals']['architecture_baseline']['approved'] = False
        self.assertEqual(validate_project_input(candidate, require_approvals=True)['status'], 'WAITING_DECISION')
        ordered = questions_for(candidate)
        self.assertEqual(ordered[0]['id'], 'QST-DOCUMENTATION-001')
        self.assertNotIn('QST-OUTCOME-001', [q['id'] for q in ordered])

    def test_minimal_and_documented_greenfield_handoff(self):
        for documented in (False, True):
            with self.subTest(documented=documented), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                document = root / 'requirements.md'
                if documented:
                    document.write_text('Scope: a local task CLI. Success: one verified task.\n')
                value = load_fixture()
                if not documented:
                    value['project']['documentation']['availability'] = 'NONE'
                    value['project']['documentation']['normative_sources'] = []
                input_path = root / 'initial.json'
                input_path.write_text(json.dumps(value))
                ws = root / 'intake'
                sources = [document] if documented else []
                start_intake(ws, project_name=value['project']['name'], mode='GREENFIELD', sources=sources, initial_input=input_path)
                self.assertEqual(check_intake(ws)['status'], 'READY_FOR_HANDOFF')
                self.assertEqual(len(load_data(ws / 'SOURCE_INVENTORY.yaml')['source_inventory']['sources']), int(documented))
                out = root / 'handoff.zip'
                prepared = prepare_handoff(ws, out)
                self.assertEqual(prepared['status'], 'READY_FOR_CODEX')
                self.assertTrue(out.is_file())
                self.assertTrue(validate_handoff(out)['status'] == 'PASS')

    def test_recheck_changed_answers_and_repeated_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            value = load_fixture()
            source = root / 'initial.json'; source.write_text(json.dumps(value))
            ws = root / 'intake'
            start_intake(ws, project_name=value['project']['name'], mode='GREENFIELD', initial_input=source)
            self.assertEqual(start_intake(ws, project_name=value['project']['name'], mode='GREENFIELD')['status'], 'READY_FOR_HANDOFF')
            candidate = load_data(ws / 'PROJECT_INPUT.yaml')
            candidate['implementation']['target_level'] = 'UNSURE'
            write_data(ws / 'PROJECT_INPUT.yaml', candidate)
            self.assertEqual(check_intake(ws)['status'], 'WAITING_DECISION')
            candidate['implementation']['target_level'] = 'MVP'
            write_data(ws / 'PROJECT_INPUT.yaml', candidate)
            self.assertEqual(check_intake(ws)['status'], 'READY_FOR_HANDOFF')

    def test_force_never_deletes_sources_or_initial_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / 'work'
            workspace.mkdir()
            source = workspace / 'requirements.md'; source.write_text('keep')
            for kwargs in ({'sources': [source]}, {'initial_input': source}, {'sources': [root]}):
                with self.assertRaises(SafetyViolation):
                    start_intake(workspace, project_name='Safe', mode='GREENFIELD', force=True, **kwargs)
                self.assertEqual(source.read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()

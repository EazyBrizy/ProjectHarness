"""Synthetic GPT fixtures only; no provider calls or automatic executor."""
from __future__ import annotations
from copy import deepcopy
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from project_harness.errors import ValidationFailure
from project_harness.local_web_service import LocalWebService, OperationRequest
from project_harness.local_web_exchange_contract import ExchangeError, PART_MAX, bytes_digest, digest
from project_harness.local_web_drafts import DRAFT_FIELDS, update_provisional_draft, draft_input_digest
from project_harness.project_input import validate_project_input, questions_for
from project_harness.serialization import load_data, write_data
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_05_import import archive
from tests.test_engine import load_fixture


class ExchangeFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ph-lw06-')
        self.addCleanup(self.temp.cleanup)
        self.app = Path(self.temp.name) / 'app'
        self.service = LocalWebService(self.app)
        self.addCleanup(lambda: self.service.close())
        self.pid = self.service.create_provisional_intake(project_name='PH-LW-06 fixture',
            no_documentation=True, idempotency_key='fixture-create-intake-0001')['project_id']
        self.root = self.service._registered(self.pid)[0]

    def answer(self, values):
        view = self.service.get_status(self.pid)
        request = OperationRequest(self.pid, 'update-draft', {'patch': values,
            'expected_input_digest': view['refs']['input_digest']},
            'test-answer-' + view['fingerprint'][7:40], view['fingerprint'])
        result = self.service.submit(request, check_current=True)
        result = self.service.wait_for(result['operation_id'], timeout=30)
        self.assertEqual(result['state'], 'SUCCEEDED', result)

    def upload(self, documents):
        return self.service.upload_sources(self.pid, [(name, BytesIO(data)) for name, data in documents],
            mode='append', expected_fingerprint=self.service.get_status(self.pid)['fingerprint'],
            expected_source_revision=self.service.list_sources(self.pid)['source_revision'])

    def export(self, key='test-export-key-00001'):
        review = self.service.get_export_review(self.pid)
        value = dict(expected_fingerprint=review['binding']['fingerprint'], review_digest=review['review_digest'],
            classifications={d['document_ref']: 'PUBLIC' for d in review['documents']},
            draft_classification='PUBLIC', consent=True, idempotency_key=key)
        return self.service.create_gpt_export(self.pid, **value)

    def reply(self, export, changes=None):
        pieces = [self.service.read_gpt_export(self.pid, export['exchange_id'], f['name']).decode()
                  for f in export['files'] if f['name'] != 'index.md']
        if len(pieces) > 1:
            pieces = [p.split('\n\n', 1)[1] for p in pieces]
        value = json.loads(''.join(pieces).split('## Return skeleton\n\n', 1)[1])
        for field, item in (changes or {}).items():
            child = value['project_input_draft']
            parts = field.split('.')
            for part in parts[:-1]:
                child = child[part]
            child[parts[-1]] = item
            value['claims'].append({'field': field, 'source_refs': ['INPUT']})
        return value

    def preview(self, reply):
        return self.service.preview_gpt_reply(self.pid, text=json.dumps(reply),
             expected_fingerprint=self.service.get_status(self.pid)['fingerprint'])

    def commit(self, preview):
        return self.service.commit_gpt_reply(self.pid, preview['import_id'], preview_digest=preview['preview_digest'],
            expected_fingerprint=preview['binding']['fingerprint'])

    def assert_rejected_unchanged(self, reply, code):
        before = byte_snapshot(Path(self.temp.name))
        result = self.preview(reply)
        self.assertEqual(result['status'], 'REJECTED', result)
        self.assertEqual(result['error']['code'], code, result)
        self.assertLessEqual(len(result['repair_prompt']), 8192)
        self.assertNotIn(str(self.temp.name), result['repair_prompt'])
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))


class ExchangeTests(ExchangeFixture):
    def test_documented_and_no_documentation_greenfield_typed_draft_roundtrip(self):
        for documented in (False, True):
            with self.subTest(documented=documented):
                if documented:
                    self.upload([('source.md', b'# Primary requirement'), ('docs.zip', archive([('detail.md', b'# Detail')]))])
                self.answer({'project.primary_outcome': 'User can record one item', 'implementation.target_level': 'UNSURE'})
                view = self.service.get_interview(self.pid)
                self.assertEqual(view['readiness']['status'], 'WAITING_DECISION')
                self.assertEqual(view['questions'][0]['id'], 'QST-DOCUMENTATION-001')
                self.assertNotIn('QST-OUTCOME-001', [q['id'] for q in view['questions']])
                export = self.export('test-export-roundtrip-' + str(documented))
                reply = self.reply(export, {'project.problem_statement': 'Explicit synthetic fixture claim'})
                before = (self.root / 'PROJECT_INPUT.yaml').read_bytes()
                result = self.preview(reply)
                self.assertEqual(result['status'], 'PREVIEW', result)
                self.assertEqual(before, (self.root / 'PROJECT_INPUT.yaml').read_bytes())
                preview = result['preview']
                self.assertEqual(preview['diff'][0]['field'], 'project.problem_statement')
                committed = self.commit(preview)
                self.assertEqual(committed['state'], 'COMMITTED')
                self.assertEqual(load_data(self.root / 'PROJECT_INPUT.yaml')['execution']['mode'], 'MANUAL_HANDOFF')
                facts = self.service.get_interview(self.pid)['known_answers']
                fact = next(f for f in facts if f['field'] == 'project.problem_statement')
                self.assertEqual(fact['provenance']['kind'], 'GPT_DRAFT_UNVERIFIED')
                # Keep a distinct change for the next loop.
                self.answer({'project.problem_statement': None})

    def test_read_only_interview_review_download_and_pack_binding(self):
        self.upload([('doc.md', '# Кириллица'.encode())])
        export = self.export()
        before = byte_snapshot(Path(self.temp.name))
        for _ in range(2):
            self.service.get_interview(self.pid)
            self.service.get_export_review(self.pid)
            for file in export['files']:
                data = self.service.read_gpt_export(self.pid, export['exchange_id'], file['name'])
                self.assertEqual(len(data), file['bytes'])
                self.assertEqual(bytes_digest(data), file['sha256'])
                self.assertIn(b'PROJECT_INPUT', data)
                self.assertNotIn(b'PROJECT_INPUT@3', data)
                self.assertNotIn(str(self.temp.name).encode(), data)
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))

    def test_invalid_envelopes_are_no_write_and_repair_is_bounded(self):
        export = self.export()
        original = self.reply(export)
        cases = []
        def case(edit, code):
            value = deepcopy(original); edit(value); cases.append((value, code))
        case(lambda v: v.update(unexpected='bad'), 'EXCHANGE_SCHEMA_INVALID')
        case(lambda v: v.update(project_ref='LWP-AAAA12345678'), 'WRONG_PROJECT')
        case(lambda v: v.update(export_sha256='sha256:'+'0'*64), 'BINDING_MISMATCH')
        case(lambda v: v.update(source_revision=99), 'BINDING_MISMATCH')
        case(lambda v: v['project_input_draft']['approvals']['project_definition'].update(approved=True, actor='Mallory'), 'APPROVAL_FORGERY')
        case(lambda v: v['project_input_draft']['approvals']['project_definition'].update(actor='Mallory'), 'APPROVAL_FORGERY')
        case(lambda v: v['project_input_draft']['execution'].update(mode='LOCAL_AUTOMATIC', adapter_profile_ref='ADP-X@1', sandbox_profile_ref='SBX-X@1'), 'PROTECTED_DRAFT_FIELDS')
        case(lambda v: v['project_input_draft']['project'].update(slug='changed'), 'PROTECTED_DRAFT_FIELDS')
        case(lambda v: v['project_input_draft']['project'].pop('primary_outcome'), 'DRAFT_SCHEMA_INVALID')
        case(lambda v: v['project_input_draft']['project'].update(unknown_field=True), 'DRAFT_SCHEMA_INVALID')
        case(lambda v: v['project_input_draft']['skills']['resolutions'][0]['configuration'].update(approved=True), 'PROTECTED_DRAFT_FIELDS')
        for reply, code in cases:
            with self.subTest(code=code):
                self.assert_rejected_unchanged(reply, code)

    def test_parse_limits_duplicate_keys_yaml_deep_and_nonfinite_no_write(self):
        before = byte_snapshot(Path(self.temp.name))
        for text in ('{"kind":"x","kind":"y"}', 'kind: LOCAL_WEB_GPT_DRAFT_ONLY', '{"x":NaN}', '{"x":1e999}',
                     '{"x":' + '['*26 + '0' + ']'*26 + '}', 'x' * (512*1024+1),
                     '{"x":[' + ','.join('0' for _ in range(30001)) + ']}'):
            result = self.service.preview_gpt_reply(self.pid, text=text,
                expected_fingerprint=self.service.get_status(self.pid)['fingerprint'])
            self.assertEqual(result['status'], 'REJECTED', result)
            self.assertEqual(before, byte_snapshot(Path(self.temp.name)))

    def test_stale_input_source_changed_and_two_previews_cannot_overwrite(self):
        export = self.export()
        reply = self.reply(export, {'project.primary_outcome': 'Imported outcome'})
        preview = self.preview(reply)['preview']
        alternate = self.reply(export, {'project.primary_outcome': 'Other outcome'})
        another = self.preview(alternate)['preview']
        self.commit(preview)
        before = byte_snapshot(Path(self.temp.name))
        with self.assertRaises(ExchangeError):
            self.commit(another)
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        self.assert_rejected_unchanged(alternate, 'STALE_EXCHANGE')
        next_export = self.export('test-next-export-source-change')
        reply = self.reply(next_export, {'project.problem_statement': 'Claim'})
        self.upload([('new.md', b'new source')])
        self.assert_rejected_unchanged(reply, 'STALE_EXCHANGE')

    def test_reload_restart_exact_replay_and_cancel_before_commit(self):
        export = self.export()
        reply = self.reply(export, {'project.primary_outcome': 'New answer'})
        preview = self.preview(reply)['preview']
        self.service.close(); self.service = LocalWebService(self.app)
        self.assertEqual(self.service.get_interview(self.pid)['imports'][0]['import_id'], preview['import_id'])
        self.commit(preview)
        snapshot = byte_snapshot(Path(self.temp.name))
        self.assertEqual(self.commit(preview)['state'], 'COMMITTED')
        self.assertEqual(self.preview(reply)['status'], 'REPLAYED')
        self.assertEqual(snapshot, byte_snapshot(Path(self.temp.name)))
        second = self.export('test-cancel-export-key-0001')
        p = self.preview(self.reply(second, {'project.primary_outcome': 'Cancelled answer'}))['preview']
        canonical = (self.root / 'PROJECT_INPUT.yaml').read_bytes()
        self.service.cancel_gpt_reply(self.pid, p['import_id'], preview_digest=p['preview_digest'])
        with self.assertRaises(ExchangeError):
            self.commit(p)
        self.assertEqual(canonical, (self.root / 'PROJECT_INPUT.yaml').read_bytes())

    def test_commit_crash_after_and_before_atomic_public_api(self):
        for after in (False, True):
            export = self.export('crash-export-before-after-' + str(after))
            preview = self.preview(self.reply(export, {'project.primary_outcome': 'After crash ' + str(after)}))['preview']
            def crash(*args, **kwargs):
                if after:
                    update_provisional_draft(*args, **kwargs)
                raise KeyboardInterrupt('synthetic process boundary')
            with patch('project_harness.local_web_exchange.update_provisional_draft', side_effect=crash):
                with self.assertRaises(KeyboardInterrupt):
                    self.commit(preview)
            self.service.close(); self.service = LocalWebService(self.app)
            before = byte_snapshot(Path(self.temp.name))
            self.assertTrue(self.service.get_interview(self.pid)['recovery_required'])
            self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
            with self.assertRaises(ExchangeError):
                self.answer({'project.primary_outcome': 'Should block'})
            result = self.service.recover_gpt_reply(self.pid)
            self.assertEqual(result['status'], 'COMMITTED_RECOVERED' if after else 'NOT_COMMITTED')
            if not after:
                self.commit(preview)

    def test_ambiguous_recovery_preserves_cli_change(self):
        export = self.export()
        p = self.preview(self.reply(export, {'project.primary_outcome': 'Reply'}))['preview']
        with patch('project_harness.local_web_exchange.update_provisional_draft', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.commit(p)
        update_provisional_draft(self.root, {'project.primary_outcome': 'Concurrent public CLI'},
                                expected_input_digest=draft_input_digest(self.root))
        before = byte_snapshot(Path(self.temp.name))
        with self.assertRaises(ExchangeError):
            self.service.recover_gpt_reply(self.pid)
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))

    def test_export_policy_classification_consent_secrets_and_size(self):
        review = self.service.get_export_review(self.pid)
        args = dict(expected_fingerprint=review['binding']['fingerprint'], review_digest=review['review_digest'],
            classifications={}, draft_classification='PUBLIC', consent=True, idempotency_key='policy-export-test-00001')
        for extra in ({'consent': False}, {'draft_classification': 'SECRET'}, {'draft_classification': []},
                      {'classifications': {'unknown': 'PUBLIC'}}, {'review_digest': 'sha256:'+'0'*64}):
            before = byte_snapshot(Path(self.temp.name))
            with self.assertRaises(ExchangeError):
                self.service.create_gpt_export(self.pid, **{**args, **extra})
            self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        self.upload([('secret.md', b'-----BEGIN PRIVATE KEY-----\nsynthetic-not-a-key')])
        before = byte_snapshot(Path(self.temp.name))
        with self.assertRaisesRegex(ExchangeError, 'секрет'):
            self.export()
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))

    def test_large_pack_has_all_parts_counts_and_hashes(self):
        data = ('Требование. ' * 30000 + '\nEND-EXACT-SOURCE').encode()
        self.upload([('large.md', data)])
        export = self.export()
        self.assertGreater(len(export['files']), 2)
        self.assertEqual(export['files'][0]['name'], 'index.md')
        chunks = []
        for f in export['files']:
            raw = self.service.read_gpt_export(self.pid, export['exchange_id'], f['name'])
            self.assertEqual(bytes_digest(raw), f['sha256'])
            if f['name'] != 'index.md':
                chunks.append(raw.decode().split('\n\n', 1)[1])
                self.assertLess(len(raw), PART_MAX + 256)
        self.assertIn('END-EXACT-SOURCE', ''.join(chunks))
        self.assertEqual(self.reply(export)['envelope_version'], 2)

    def test_actual_pack_limit_and_confidential_project_fail_closed(self):
        self.answer({'project.data.sensitivity': 'CONFIDENTIAL'})
        before = byte_snapshot(Path(self.temp.name))
        with self.assertRaisesRegex(ExchangeError, 'CONFIDENTIAL'):
            self.export()
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        self.answer({'project.data.sensitivity': 'PUBLIC'})
        self.upload([(f'large-{i}.md', b'x' * (7 * 1024 * 1024)) for i in range(3)])
        before = byte_snapshot(Path(self.temp.name))
        with self.assertRaisesRegex(ExchangeError, '20 MiB'):
            self.export()
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))

    def test_native_child_process_crash_after_commit_then_restart_recovery(self):
        export = self.export()
        preview = self.preview(self.reply(export, {'project.primary_outcome': 'Committed by child fixture'}))['preview']
        code = '''import json,os,sys
from pathlib import Path
from unittest.mock import patch
from project_harness.local_web_service import LocalWebService
from project_harness.local_web_drafts import update_provisional_draft
def crash(*args,**kwargs):
    update_provisional_draft(*args,**kwargs)
    os._exit(86)
service=LocalWebService(Path(sys.argv[1]))
with patch('project_harness.local_web_exchange.update_provisional_draft',side_effect=crash):
    service.commit_gpt_reply(sys.argv[2],sys.argv[3],**json.loads(sys.argv[4]))
'''
        command = [sys.executable, '-c', code, str(self.app), self.pid, preview['import_id'],
                   json.dumps({'preview_digest':preview['preview_digest'], 'expected_fingerprint':preview['binding']['fingerprint']})]
        result = subprocess.run(command, capture_output=True, timeout=30, env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        self.assertEqual(result.returncode, 86, result.stderr.decode(errors='replace'))
        self.service.close(); self.service = LocalWebService(self.app)
        self.assertEqual(self.service.recover_gpt_reply(self.pid)['status'], 'COMMITTED_RECOVERED')
        snapshot = byte_snapshot(Path(self.temp.name))
        self.assertEqual(self.commit(preview)['state'], 'COMMITTED')
        self.assertEqual(snapshot, byte_snapshot(Path(self.temp.name)))

    def test_source_provenance_reaffirmation_after_refresh(self):
        export = self.export()
        p = self.preview(self.reply(export, {'project.primary_outcome':'Source-bound claim'}))['preview']
        self.commit(p)
        self.upload([('revision.md', b'# New source')])
        view = self.service.get_interview(self.pid)
        self.assertTrue(any(q['id'] == 'SOURCE-REVIEW-project.primary_outcome' for q in view['questions']))
        new_export = self.export('source-provenance-reaffirm-01')
        reply = self.reply(new_export)
        reply['claims'] = [{'field':'project.primary_outcome','source_refs':[view['documents'][0]['document_ref']]}]
        p = self.preview(reply)['preview']; self.commit(p)
        fact = next(f for f in self.service.get_interview(self.pid)['known_answers'] if f['field']=='project.primary_outcome')
        self.assertEqual(fact['provenance']['kind'], 'GPT_DRAFT_UNVERIFIED')
        self.assertEqual(fact['provenance']['source_refs'], [view['documents'][0]['document_ref']])

    def test_forged_source_ref_and_semantic_repair_identifies_exact_field(self):
        export = self.export()
        reply = self.reply(export, {'project.scope.in':[{'statement':'Claim','source_ref':'EVD-FORGED@1'}]})
        self.assert_rejected_unchanged(reply, 'SOURCE_REF_UNKNOWN')
        reply = self.reply(export, {'profile.ref':'NOT-A-REGISTERED-PROFILE'})
        result = self.preview(reply)
        self.assertEqual(result['status'], 'REJECTED')
        self.assertEqual(result['error']['validation_errors'], [{'path':'profile.ref','keyword':'registered-profile-required'}])
        self.assertNotIn('NOT-A-REGISTERED-PROFILE', result['repair_prompt'])

    def test_unknowns_unsure_and_pending_approvals_cannot_become_ready(self):
        value = load_fixture()
        for field in ('connectivity',):
            bad = deepcopy(value); bad['project'][field] = 'UNKNOWN'
            self.assertEqual(validate_project_input(bad, require_approvals=True)['status'], 'WAITING_INPUT')
        for unknown in ('Material gap', {'question': 'Material gap', 'blocking': True}, {'question': 'Unclassified'}):
            bad = deepcopy(value); bad['project']['unknowns'] = [unknown]
            self.assertEqual(validate_project_input(bad, require_approvals=True)['status'], 'WAITING_INPUT')
            self.assertTrue(any(q['field'] == 'project.unknowns' and q['status'] == 'OPEN' for q in questions_for(bad)))
        self.answer({'implementation.target_level': 'UNSURE'})
        self.assertEqual(self.service.get_interview(self.pid)['readiness']['status'], 'WAITING_DECISION')
        export = self.export()
        reply = self.reply(export, {'implementation.target_level': 'MVP'})
        self.assert_rejected_unchanged(reply, 'TARGET_DECISION_REQUIRED')
        reply = self.reply(export)
        reply['questions'] = [{'id': 'GAP-1', 'question': 'Who owns data?', 'source_refs': []}]
        preview = self.preview(reply)['preview']
        self.commit(preview)
        self.assertIn('project.unknowns', self.service.get_interview(self.pid)['readiness']['missing_fields'])

    def test_synthetic_existing_approvals_unchanged_binding_or_invalidation(self):
        # Test setup only: represents pre-existing trusted operator approvals,
        # never a UI approval operation or a fabricated acceptance test result.
        value = load_data(self.root / 'PROJECT_INPUT.yaml')
        for approval in value['approvals'].values():
            approval.update(approved=True, actor='fixture-operator', approved_at='2026-11-07T00:00:00Z')
        write_data(self.root / 'PROJECT_INPUT.yaml', value)
        export = self.export()
        unchanged = self.preview(self.reply(export))['preview']
        self.commit(unchanged)
        self.assertEqual(load_data(self.root / 'PROJECT_INPUT.yaml')['approvals'], value['approvals'])
        next_export = self.export('test-approved-second-export')
        changed = self.preview(self.reply(next_export, {'project.primary_outcome': 'New material answer'}))['preview']
        self.assertEqual(len(changed['approval_invalidation_receipt']['subjects']), 4)
        self.commit(changed)
        self.assertTrue(all(v['approved'] is False for v in load_data(self.root / 'PROJECT_INPUT.yaml')['approvals'].values()))


if __name__ == '__main__':
    unittest.main()

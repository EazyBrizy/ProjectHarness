"""PH-LW-07 independent decisions; declared fixtures, never model consent."""
from __future__ import annotations
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from project_harness.errors import HarnessError
from project_harness.intake import start_intake, check_intake
from project_harness.local_web_service import LocalWebService, OperationRequest
from project_harness.local_web_drafts import DRAFT_FIELDS, draft_input_digest, update_provisional_draft
from project_harness.local_web_exchange_contract import get_field, digest
from project_harness.project_input import approvals_for_mode
from project_harness.serialization import load_data, write_data
from tests.test_ph_lw_06_exchange import ExchangeFixture
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_engine import load_fixture


class ApprovalFixture(ExchangeFixture):
    def answer(self, values):
        # Returning to identical content is a new edit, not a retry of a
        # previous request with the same fingerprint and different payload.
        self.answer_sequence = getattr(self, 'answer_sequence', 0) + 1
        view = self.service.get_status(self.pid)
        request = OperationRequest(self.pid, 'update-draft', {'patch': values,
            'expected_input_digest': view['refs']['input_digest']},
            'approval-fixture-edit-' + str(self.answer_sequence), view['fingerprint'])
        result = self.service.submit(request, check_current=True)
        self.assertEqual(self.service.wait_for(result['operation_id'], timeout=30)['state'], 'SUCCEEDED')

    def fill(self):
        fixture = load_fixture()
        self.answer({field: get_field(fixture, field) for field in DRAFT_FIELDS})

    def review(self):
        return self.service.get_approval_review(self.pid)

    def actor(self):
        return self.service.set_approval_actor(self.pid, actor='Оператор fixture',
            expected_fingerprint=self.review()['binding']['fingerprint'])

    def request(self, subject=None, decision='APPROVE', comment='', key=None, view=None):
        view = view or self.review()
        subject = subject or view['next_subject']
        row = next(row for row in view['subjects'] if row['subject'] == subject)
        return dict(subject=subject, decision=decision, comment=comment,
            review_digest=view['review_digest'], subject_digest=row['subject_digest'],
            expected_fingerprint=view['binding']['fingerprint'], confirm=True,
            idempotency_key=key or 'approval-' + str(len(view['receipts'])) + '-fixture-0001')

    def decide(self, **kwargs):
        return self.service.decide_approval(self.pid, **self.request(**kwargs))

    def assert_no_write_error(self, request):
        before = byte_snapshot(Path(self.temp.name))
        with self.assertRaises(HarnessError):
            self.service.decide_approval(self.pid, **request)
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))


class ApprovalTests(ApprovalFixture):
    def test_four_independent_actions_ready_only_after_handoff_and_no_project(self):
        self.fill(); self.actor()
        order = approvals_for_mode('GREENFIELD')
        for index, subject in enumerate(order):
            value = load_data(self.root / 'PROJECT_INPUT.yaml')
            self.assertEqual([k for k,v in value['approvals'].items() if v['approved']], order[:index])
            self.assertNotEqual(check_intake(self.root)['status'], 'READY_FOR_HANDOFF')
            receipt = self.decide(subject=subject)
            self.assertEqual(receipt['actor'], 'Оператор fixture')
            self.assertEqual(receipt['canonical_approval']['approved_at'], receipt['timestamp'])
            self.assertEqual(receipt['subject_digest'], digest(receipt['subject_content']))
            self.assertEqual(receipt['version'], 1)
        self.assertEqual(check_intake(self.root)['status'], 'READY_FOR_HANDOFF')
        self.assertEqual(self.review()['next_action'], 'PREPARATION_PENDING_PH_LW_08')
        self.assertFalse((self.root / '.harness').exists())
        self.assertEqual(len(self.review()['receipts']), 4)

    def test_missing_approval_and_wrong_sequence_are_no_write(self):
        self.fill(); self.actor()
        for subject in ('architecture_baseline', 'technology_baseline', 'codex_handoff', 'brownfield_baseline'):
            if subject == 'brownfield_baseline':
                args = self.request(); args['subject'] = subject
            else:
                args = self.request(subject)
            self.assert_no_write_error(args)
        self.decide(); self.decide(); self.decide()
        self.assertEqual(check_intake(self.root)['readiness']['missing_approvals'], ['codex_handoff'])

    def test_missing_material_fields_never_get_approved(self):
        self.fill(); self.actor()
        for field, value in [('architecture.summary', None), ('architecture.components', []),
                             ('technology.selections', []), ('implementation.target_level', None),
                             ('implementation.target_level', 'UNSURE'), ('project.data.sensitivity', 'UNKNOWN')]:
            with self.subTest(field=field, value=value):
                old = get_field(load_data(self.root/'PROJECT_INPUT.yaml'), field)
                self.answer({field:value})
                self.assert_no_write_error(self.request())
                self.assertFalse(any(a['approved'] for a in load_data(self.root/'PROJECT_INPUT.yaml')['approvals'].values()))
                self.answer({field:old})

    def test_actor_is_explicit_once_and_server_time_ignores_build_epoch(self):
        self.fill()
        self.assert_no_write_error(self.request())
        self.actor()
        before = byte_snapshot(Path(self.temp.name)); self.actor()
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        with self.assertRaises(HarnessError):
            self.service.set_approval_actor(self.pid, actor='Model', expected_fingerprint=self.review()['binding']['fingerprint'])
        with patch.dict(os.environ, {'SOURCE_DATE_EPOCH':'0'}):
            receipt = self.decide()
        self.assertFalse(receipt['timestamp'].startswith('1970'))

    def test_replay_exact_after_restart_and_key_conflict_no_write(self):
        self.fill(); self.actor(); args = self.request()
        first = self.service.decide_approval(self.pid, **args)
        self.service.close(); self.service = LocalWebService(self.app)
        before = byte_snapshot(Path(self.temp.name))
        self.assertEqual(first, self.service.decide_approval(self.pid, **args))
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        self.assert_no_write_error({**args, 'comment':'different'})
        self.assert_no_write_error(self.request('project_definition', key='another-click-key-0001'))

    def test_concurrent_double_click_has_one_receipt(self):
        self.fill(); self.actor(); args = self.request()
        def send():
            try:
                return self.service.decide_approval(self.pid, **args)
            except HarnessError:
                return None  # OS lock contention is retryable, never a second decision.
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _:send(), range(2)))
        self.assertTrue(any(results))
        self.assertEqual(len(self.review()['receipts']), 1)
        self.assertEqual(self.service.decide_approval(self.pid, **args)['receipt_id'], next(r for r in results if r)['receipt_id'])

    def test_stale_second_tab_fingerprint_and_subject_digest(self):
        self.fill(); self.actor(); args = self.request()
        self.assert_no_write_error({**args, 'subject_digest':'sha256:'+'0'*64})
        self.assert_no_write_error({**args, 'expected_fingerprint':'sha256:'+'0'*64})
        self.answer({'project.primary_outcome':'Changed in tab two'})
        self.assert_no_write_error(args)

    def test_material_draft_change_invalidation_and_immutable_receipts(self):
        self.fill(); self.actor(); first = self.decide(); self.decide()
        history = {p.name:p.read_bytes() for p in (self.root/'.local-web-approvals').glob('LWA-*.json')}
        self.answer({'architecture.summary':'Revised explicit architecture'})
        view = self.review()
        self.assertEqual({i['subject'] for i in view['invalidations']}, {'project_definition','architecture_baseline'})
        self.assertEqual({i['reason'] for i in view['invalidations']}, {'MATERIAL_DRAFT_CHANGE'})
        self.assertFalse(any(r['approved'] for r in view['subjects']))
        self.decide()
        for name, data in history.items():
            self.assertEqual((self.root/'.local-web-approvals'/name).read_bytes(), data)

    def test_source_change_invalidates_and_stale_request_rejected(self):
        self.fill(); self.actor(); self.decide()
        old = self.request()
        self.upload([('changed.md', b'# Material source change')])
        self.assert_no_write_error(old)
        self.assertEqual(self.review()['invalidations'][0]['reason'], 'SOURCE_CHANGED')
        self.assertFalse(any(r['approved'] for r in self.review()['subjects']))

    def test_rework_comment_only_current_draft_and_dependent_approvals_reset(self):
        self.fill(); self.actor()
        for _ in range(4): self.decide()
        self.assert_no_write_error(self.request('architecture_baseline', decision='REWORK'))
        receipt = self.decide(subject='architecture_baseline', decision='REWORK', comment='Уточните поток данных')
        value = load_data(self.root/'PROJECT_INPUT.yaml')
        self.assertTrue(value['approvals']['project_definition']['approved'])
        self.assertEqual(receipt['reset_subjects'], ['architecture_baseline','technology_baseline','codex_handoff'])
        self.assertEqual(value['approvals']['architecture_baseline']['notes'], 'Уточните поток данных')
        self.assertEqual(self.review()['readiness']['status'], 'WAITING_DECISION')
        self.assertEqual(len(self.review()['receipts']), 5)
        self.assertEqual(self.service.get_interview(self.pid)['approval_rework_requests'][0]['comment'], 'Уточните поток данных')
        self.decide(subject='architecture_baseline')
        self.assertEqual(self.review()['rework_requests'], [])

    def test_invalid_public_receipt_and_storage_budget_fail_before_write(self):
        from project_harness.local_web_approval_core import apply_provisional_approval
        self.fill(); self.actor()
        before = byte_snapshot(Path(self.temp.name))
        with self.assertRaises(HarnessError): apply_provisional_approval(self.root, {'version':1,'intent_digest':'forged'})
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        # An actual full companion store fails closed without pruning history.
        (self.root/'.local-web-approvals'/'full.bin').write_bytes(b'x'*(16*1024*1024))
        self.assert_no_write_error(self.request())

    def test_unbound_canonical_fields_block_until_explicit_reset(self):
        self.fill(); self.actor()
        value = load_data(self.root/'PROJECT_INPUT.yaml')
        value['approvals']['project_definition'].update(approved=True, actor='outside', approved_at='2026-11-07T00:00:00Z')
        write_data(self.root/'PROJECT_INPUT.yaml', value)
        self.assertEqual(self.review()['unbound_approvals'], ['project_definition'])
        self.assert_no_write_error(self.request('architecture_baseline'))
        self.decide(subject='project_definition', decision='INVALIDATE')
        self.assertEqual(self.review()['unbound_approvals'], [])
        self.assertEqual(self.review()['next_subject'], 'project_definition')

    def test_get_is_read_only_with_actor_decisions_and_pending(self):
        self.fill(); self.actor(); self.decide()
        before = byte_snapshot(Path(self.temp.name))
        for _ in range(3): self.review()
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        with patch('project_harness.local_web_approvals.apply_provisional_approval', side_effect=RuntimeError('before commit')):
            with self.assertRaises(RuntimeError): self.decide()
        before = byte_snapshot(Path(self.temp.name))
        self.assertTrue(self.review()['recovery_required'])
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        with self.assertRaises(HarnessError): self.upload([('blocked.md',b'# blocked')])
        self.assertEqual(self.service.recover_approval(self.pid)['status'], 'NOT_COMMITTED')
        self.assertEqual(self.service.recover_approval(self.pid)['status'], 'CLEAN')

    def test_native_child_crash_before_after_commit_and_restart_recovery(self):
        self.fill(); self.actor()
        for point in ('before','after','receipt'):
            with self.subTest(point=point):
                args = self.request(key='child-crash-' + point + '-0001')
                code = '''import json,os,sys
from pathlib import Path
from unittest.mock import patch
from project_harness.local_web_service import LocalWebService
from project_harness.local_web_approval_core import apply_provisional_approval
from project_harness.local_web_approvals import _save
def crash(*args, **kwargs):
    if sys.argv[4] == 'after': apply_provisional_approval(*args, **kwargs)
    os._exit(87)
def receipt_crash(path, value):
    _save(path, value)
    if path.name.startswith('LWA-'): os._exit(87)
service=LocalWebService(Path(sys.argv[1]))
target='project_harness.local_web_approvals.' + ('_save' if sys.argv[4]=='receipt' else 'apply_provisional_approval')
with patch(target, side_effect=receipt_crash if sys.argv[4]=='receipt' else crash):
    service.decide_approval(sys.argv[2], **json.loads(sys.argv[3]))
'''
                result = subprocess.run([sys.executable, '-c', code, str(self.app), self.pid, json.dumps(args), point],
                    capture_output=True, timeout=40, env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
                self.assertEqual(result.returncode,87,result.stderr.decode(errors='replace'))
                self.service.close(); self.service=LocalWebService(self.app)
                self.assertTrue(self.review()['recovery_required'])
                before=byte_snapshot(Path(self.temp.name))
                with self.assertRaises(HarnessError):
                    view=self.service.get_status(self.pid)
                    self.service.submit(OperationRequest(self.pid,'check-intake',{},'crash-fence-'+point+'-01',view['fingerprint']),check_current=True)
                self.assertEqual(before,byte_snapshot(Path(self.temp.name)))
                recovered=self.service.recover_approval(self.pid)
                self.assertEqual(recovered['status'],'NOT_COMMITTED' if point=='before' else 'COMMITTED_RECOVERED')
                receipt=self.service.decide_approval(self.pid,**args)
                self.assertEqual(receipt['state'],'COMMITTED')

    def test_ambiguous_recovery_fails_closed_and_keeps_intent(self):
        self.fill(); self.actor()
        with patch('project_harness.local_web_approvals.apply_provisional_approval',side_effect=RuntimeError()):
            with self.assertRaises(RuntimeError): self.decide()
        value=load_data(self.root/'PROJECT_INPUT.yaml'); value['project']['primary_outcome']='External CLI change'
        write_data(self.root/'PROJECT_INPUT.yaml',value)
        before=byte_snapshot(Path(self.temp.name))
        with self.assertRaises(HarnessError): self.service.recover_approval(self.pid)
        self.assertEqual(before,byte_snapshot(Path(self.temp.name)))

    def test_brownfield_hybrid_five_actions_baseline_order_and_repository_read_only(self):
        for mode in ('BROWNFIELD','HYBRID'):
            with self.subTest(mode=mode):
                repo=Path(self.temp.name)/('repo-'+mode); repo.mkdir(); (repo/'README.md').write_text('# Existing fixture','utf-8')
                fixture=load_fixture(); fixture['project']['mode']=mode
                fixture['implementation']['claimed_current_level']='UNKNOWN'
                fixture['brownfield']['baseline_summary']='Existing read-only inventory; no accepted maturity claim'
                fixture['approvals']={name:{'approved':False,'actor':None,'approved_at':None,'notes':None} for name in approvals_for_mode(mode)}
                initial=Path(self.temp.name)/('input-'+mode+'.json'); write_data(initial,fixture)
                root=Path(self.temp.name)/('intake-'+mode)
                start_intake(root,project_name='Brownfield fixture',mode=mode,repository=repo,initial_input=initial)
                self.pid=self.service.register_existing(root,kind='workspace'); self.root=root
                original=byte_snapshot(repo); self.actor(); self.decide()
                self.assert_no_write_error(self.request('architecture_baseline'))
                for _ in range(4): self.decide()
                self.assertEqual(check_intake(root)['status'],'READY_FOR_HANDOFF')
                self.assertEqual(len(self.review()['receipts']),5)
                baseline=self.review()['receipts'][1]['subject_content']['evidence_context']
                self.assertEqual(baseline['inventory_mode'],'READ_ONLY'); self.assertNotIn('repository_path',baseline)
                self.assertEqual(original,byte_snapshot(repo))
                (repo/'README.md').write_text('# Changed baseline','utf-8')
                self.assertFalse(self.review()['subject_complete'])
                self.assertEqual(self.review()['invalidations'][0]['reason'],'SOURCE_CHANGED')

    def test_prepared_history_guard_and_bounded_unknown_subject(self):
        self.fill(); self.actor()
        args=self.request(); args['subject']='../../outside'; self.assert_no_write_error(args)
        args=self.request(); args['comment']='x'*2001; self.assert_no_write_error(args)
        args=self.request(); args['confirm']=False; self.assert_no_write_error(args)
        op={'operation_id':'LWO-'+'A'*32,'project_id':self.pid,'action':'prepare','state':'SUCCEEDED'}
        with patch.object(self.service,'_load_op',return_value=op):
            path=self.app/'operations'/('LWO-'+'A'*32+'.json'); path.write_text('{}','utf-8')
            self.assert_no_write_error(self.request())


if __name__ == '__main__': unittest.main()

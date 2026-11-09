"""Task proof intake: real operator review, strict bindings and failure recovery."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from project_harness import task_manual_evidence as me, manual_tasks as tasks
from project_harness.errors import HarnessError
from project_harness.runtime import verify_current
from project_harness.serialization import load_data
from tests import test_ph_lw_09_tasks as support
from tests.test_ph_lw_09_tasks import agent_result, implement_first_task
from tests.test_ph_lw_03_service import byte_snapshot


def review_document(root, status='PASS'):
    context=me.manual_evidence_context(root)
    return {**context['binding'],'reviewer':'ACT-FIXTURE-INDEPENDENT-REVIEWER', 'checks':[
        {'index':i,'check':check,'status':status,
         'observation':'Fixture operator inspected task_cli.py parsing and persistence and README usage; explicit bounded review, no production claim.',
         'sources':[{'path':'task_cli.py','sha256':'sha256:'+context['product_files']['task_cli.py']['sha256']}]}
        for i,check in enumerate(context['binding']['checks'])]}


class ManualEvidenceTests(unittest.TestCase):
    setUp=support.TaskConsoleTests.setUp
    project=support.TaskConsoleTests.project
    run_action=support.TaskConsoleTests.run_action
    receive=support.TaskConsoleTests.receive
    verify=support.TaskConsoleTests.verify

    def prepare(self):
        root=self.project(manual=True);implement_first_task(root)
        return root,review_document(root)

    def test_positive_explicit_review_verify_complete_and_immutable_replay(self):
        root,document=self.prepare();self.receive()
        self.assertEqual(self.verify()['result']['core_status'],'BLOCKED')
        operation=self.run_action('manual-evidence',{'document':document,'confirmed':True})
        self.assertEqual(operation['state'],'SUCCEEDED',operation)
        before=byte_snapshot(root);result=me.record_manual_evidence(root,document,confirmed=True)
        self.assertEqual(before,byte_snapshot(root));self.assertEqual(result['review_status'],'PASS')
        v=tasks.task_console(root);self.assertEqual(v['manual_evidence']['evidence']['status'],'PASS')
        self.assertNotEqual(v['verification_report']['status'],'PASS')
        self.assertEqual(self.verify()['result']['core_status'],'PASS')
        ref=result['evidence_ref'];body=load_data(root/f'.harness/evidence/{ref}.yaml')['verification_evidence']
        self.assertFalse(body['criterion_refs']);self.assertFalse(body['outcome_refs']);self.assertNotIn('semantic_proof',body['details'])
        self.assertEqual(self.run_action('complete',{'binding_digest':tasks.task_console(root)['binding_digest']})['result']['core_status'],'COMPLETED')
        completed=list((root/'.harness/runtime/RUNS').glob('*.yaml'))
        self.assertTrue(any(ref in load_data(p)['run']['evidence_refs'] for p in completed))

    def test_consent_unknown_fields_and_missing_checks_rejected_before_mutation(self):
        root,document=self.prepare();before=byte_snapshot(root)
        for confirm in (False,1,'true',None):
            with self.assertRaises(HarnessError):me.record_manual_evidence(root,document,confirmed=confirm)
        cases=[{**document,'agent':'claims'}, {**document,'schema_version':True}, {**document,'reviewer':''}, {**document,'checks':[]},
            {**document,'checks':document['checks']*2}]
        for key,value in [('index',True),('check','wrong'),('status','NOT_APPLICABLE'),('observation',''),('sources',[])]:
            bad=deepcopy(document);bad['checks'][0][key]=value;cases.append(bad)
        for bad in cases:
            with self.assertRaises(HarnessError):me.record_manual_evidence(root,bad,confirmed=True)
            self.assertEqual(before,byte_snapshot(root))

    def test_forged_stale_refs_plan_and_product_source_digest_rejected(self):
        root,document=self.prepare();before=byte_snapshot(root)
        for key in ('run_ref','task_ref','binding_digest','plan_digest'):
            bad=deepcopy(document);bad[key]='FOREIGN'
            with self.assertRaises(HarnessError):me.record_manual_evidence(root,bad,confirmed=True)
        for path in ('../escape','C:/Windows','.harness/state/CURRENT_STATE.yaml','missing.txt'):
            bad=deepcopy(document);bad['checks'][0]['sources'][0]['path']=path
            with self.assertRaises(HarnessError):me.record_manual_evidence(root,bad,confirmed=True)
        bad=deepcopy(document);bad['checks'][0]['sources'][0]['sha256']='sha256:'+'0'*64
        with self.assertRaises(HarnessError):me.record_manual_evidence(root,bad,confirmed=True)
        self.assertEqual(before,byte_snapshot(root))
        (root/'README.md').write_text('Changed after review')
        with self.assertRaises(HarnessError):me.record_manual_evidence(root,document,confirmed=True)

    def test_fail_review_is_not_pass_and_cannot_be_overwritten(self):
        root,document=self.prepare();document['checks'][0]['status']='FAIL';self.receive()
        me.record_manual_evidence(root,document,confirmed=True)
        self.assertEqual(self.verify()['result']['core_status'],'FAIL')
        before=byte_snapshot(root);document['checks'][0]['status']='PASS'
        with self.assertRaisesRegex(HarnessError,'MANUAL_EVIDENCE_CHANGED'):me.record_manual_evidence(root,document,confirmed=True)
        self.assertEqual(before,byte_snapshot(root))
        with self.assertRaises(HarnessError):tasks.complete_manual_task(root,binding_digest=tasks.task_console(root)['binding_digest'])

    def test_later_product_edit_invalidates_manual_proof_even_on_reverify(self):
        root,document=self.prepare();me.record_manual_evidence(root,document,confirmed=True)
        self.assertEqual(verify_current(root,allow_command_execution=True)['status'],'PASS')
        (root/'README.md').write_text('Modified baseline')
        self.assertEqual(verify_current(root,allow_command_execution=True)['gates']['manual_checks'],'BLOCKED')

    def test_block_resume_does_not_reuse_old_run_proof(self):
        root,document=self.prepare();me.record_manual_evidence(root,document,confirmed=True)
        tasks.block_manual_task(root,run_ref=document['run_ref'],reason='Explicit retry')
        blocker=tasks.task_console(root)['blockers'][0]
        tasks.resume_manual_task(root,blocker_ref=f"{blocker['id']}@{blocker['revision']}",resolution='New review required')
        before=byte_snapshot(root)
        with self.assertRaises(HarnessError):me.record_manual_evidence(root,document,confirmed=True)
        self.assertEqual(before,byte_snapshot(root));self.assertEqual(me.manual_evidence_context(root)['evidence']['status'],'BLOCKED')

    def test_control_tamper_or_partial_publication_never_becomes_trusted(self):
        root,document=self.prepare()
        with patch.object(me,'write_normalized_evidence',side_effect=OSError('Injected publication crash')):
            with self.assertRaises(OSError):me.record_manual_evidence(root,document,confirmed=True)
        before=byte_snapshot(root)
        with self.assertRaises(HarnessError):me.record_manual_evidence(root,document,confirmed=True)
        self.assertEqual(before,byte_snapshot(root));self.assertEqual(verify_current(root)['status'],'BLOCKED')

    def test_review_file_tamper_is_safety_block_not_positive_evidence(self):
        root,document=self.prepare();result=me.record_manual_evidence(root,document,confirmed=True)
        evidence=root/f".harness/evidence/{result['evidence_ref']}.yaml";evidence.write_text('{}')
        self.assertEqual(me.evaluate_manual_evidence(root,tasks.runtime._state(root)[1]['state']['active_run'])['status'],'BLOCKED')
        self.assertEqual(verify_current(root)['status'],'BLOCKED')

    def test_strict_json_limits_and_duplicate_keys(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'[]',b'\xff',b' '* (me.MAX_BYTES+1)):
            with self.assertRaises(HarnessError):me.parse_document(raw)

    def test_automatic_and_unpermitted_manual_task_refused(self):
        root=self.project();implement_first_task(root)
        document=review_document(root)
        with self.assertRaises(HarnessError):me.record_manual_evidence(root,document,confirmed=True)
        from tests.test_ph_051_05_codex_adapter import install_profiles
        from project_harness.workspace import record_phase_boundary
        from project_harness.util import utc_now
        active=tasks.runtime._state(root)[1]['state']['active_run']
        install_profiles(root)  # Explicit negative fixture only; no executor dispatch.
        record_phase_boundary(root,active,phase='TEST_EXISTING_AUTOMATIC',recorded_at=utc_now())
        before=byte_snapshot(root)
        with self.assertRaisesRegex(HarnessError,'AUTOMATIC_DISABLED'):me.record_manual_evidence(root,document,confirmed=True)
        self.assertEqual(before,byte_snapshot(root))


if __name__=='__main__':unittest.main()


class ManualEvidenceHttpTests(unittest.TestCase):
    def test_real_tcp_auth_consent_fields_replay_and_stale_view(self):
        import tempfile
        from pathlib import Path
        from tests.test_ph_lw_04_05_acceptance import LiveServer
        from tests.test_engine import prepare_demo
        with tempfile.TemporaryDirectory(prefix='PH LW09 Manual HTTP ') as directory:
            live=LiveServer(directory)
            try:
                _,_,root=prepare_demo(Path(directory)/'fixture',data=support.fixture_input(manual=True))
                pid=live.service.register_existing(root,kind='project');live.login();implement_first_task(root)
                document=review_document(root);base='/api/projects/'+pid
                request={'action':'manual-evidence','payload':{'document':document,'confirmed':True},
                    'expected_fingerprint':live.service.get_status(pid)['fingerprint'],'idempotency_key':'manual-review-http-exact-key'}
                before=byte_snapshot(root)
                self.assertEqual(live.request('POST',base+'/operations',value=request,authenticated=False)[0],401)
                for headers in ({'Origin':'null'},{'X-CSRF-Token':'forged'},{'Host':'localhost:'+str(live.port)}):
                    self.assertEqual(live.request('POST',base+'/operations',value=request,headers=headers)[0],403)
                forged=deepcopy(request);forged['payload']['actor']='Agent claims operator'
                self.assertEqual(live.request('POST',base+'/operations',value=forged)[0],400)
                self.assertEqual(before,byte_snapshot(root))
                false=deepcopy(request);false['payload']['confirmed']=False;false['idempotency_key']+='-no-consent'
                accepted=live.request('POST',base+'/operations',value=false);self.assertEqual(accepted[0],202,accepted)
                rejected=live.service.wait_for(accepted[2]['operation_id'],timeout=90)
                self.assertEqual(rejected['state'],'BLOCKED')
                self.assertEqual(rejected['error']['code'],'MANUAL_EVIDENCE_CONSENT_REQUIRED')
                self.assertEqual(before,byte_snapshot(root))
                result=live.request('POST',base+'/operations',value=request);self.assertEqual(result[0],202,result)
                self.assertEqual(live.service.wait_for(result[2]['operation_id'],timeout=90)['state'],'SUCCEEDED')
                after=byte_snapshot(root);again=live.request('POST',base+'/operations',value=request)
                self.assertEqual(again[2]['operation_id'],result[2]['operation_id']);self.assertEqual(after,byte_snapshot(root))
                stale=deepcopy(request);stale['idempotency_key']+='-other-tab'
                self.assertEqual(live.request('POST',base+'/operations',value=stale)[0],409)
                self.assertEqual(after,byte_snapshot(root))
            finally:live.close()

"""Real public manual API/service tests; fixture agent writes only product bytes."""
from __future__ import annotations
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from project_harness import manual_tasks as core
from project_harness.errors import HarnessError
from project_harness.local_web_service import LocalWebService, OperationRequest
from project_harness.local_web_tasks import stage_result, view
from project_harness.runtime import verify_current
from project_harness.serialization import load_data, write_data
from tests.test_engine import prepare_demo, load_fixture, implement_first_task
from tests.test_ph_lw_03_service import byte_snapshot


def fixture_input(*, command=None, manual=False, automatic=False):
    data=load_fixture()
    for wp in data['planning']['work_packages']:
        for task in wp['tasks']:
            for cmd in task['verification']['commands']: cmd['argv'][0]=sys.executable
    first=data['planning']['work_packages'][0]['tasks'][0]
    if command is not None: first['verification']['commands']=command
    if manual: first['verification']['manual_checks']=['Review visible behavior']; first['verification']['allow_manual']=True
    if automatic:
        data['schema_version']=4
        data['execution']={'mode':'LOCAL_AUTOMATIC','adapter_profile_ref':'ADP-CODEX-CLI-LOCAL-001@1',
            'sandbox_profile_ref':'SBX-ROOTLESS-PODMAN-001@1','network_mode':'NONE','completion_policy':'EXPLICIT_AFTER_VERIFICATION'}
    return data


def agent_result(root):
    v=core.task_console(root); active=v['active_run']
    before=load_data(root/active['snapshot_path'])['snapshot']['product_files']
    from project_harness.workspace import snapshot_product,diff_snapshots
    return {'schema_version':1,'task_ref':active['task_ref'],'run_ref':active['run_ref'],'status':'COMPLETED',
        'summary':'Explicit fixture external agent implemented the product.','changes':diff_snapshots(before,snapshot_product(root)),
        'commands':[],'tests':[],'evidence':[],'blockers':[]}


class TaskConsoleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='PH LW09 Задача '); self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name); self.service=LocalWebService(self.base/'app');self.addCleanup(self.service.close)
        self.serial=0

    def project(self,**kwargs):
        _,_,self.root=prepare_demo(self.base/'fixture',data=fixture_input(**kwargs))
        self.pid=self.service.register_existing(self.root,kind='project'); return self.root

    def run_action(self,action,payload=None,request=None):
        self.serial+=1
        req=request or OperationRequest(self.pid,action,payload or {},'task-test-key-'+str(self.serial).zfill(8),self.service.get_status(self.pid)['fingerprint'])
        queued=self.service.submit(req,check_current=True)
        return self.service.wait_for(queued['operation_id'],timeout=90)

    def receive(self,raw=None,canonical=False):
        v=view(self.service,self.pid); raw=raw or json.dumps(agent_result(self.root)).encode()
        if canonical:
            (self.root/v['active_run']['allowed_agent_output_path']).write_bytes(raw)
            return core.ingest_manual_result(self.root,binding_digest=v['binding_digest'])
        upload=stage_result(self.service,self.pid,raw,expected_fingerprint=v['fingerprint'],binding_digest=v['binding_digest'])
        result=self.run_action('receive-result',{'upload_id':upload['upload_id'],'binding_digest':v['binding_digest']})
        self.assertEqual(result['state'],'SUCCEEDED',result);return result

    def verify(self,consent=True):
        v=view(self.service,self.pid)
        return self.run_action('verify',{'binding_digest':v['binding_digest'],'plan_digest':v['verification_plan']['digest'],'consent':consent})

    def test_read_only_refs_current_stage_and_exact_prompt(self):
        root=self.project(); before=byte_snapshot(root)
        for _ in range(3):
            v=view(self.service,self.pid);self.service.get_status(self.pid)
            self.assertIn(v['active_run']['task_ref'],v['prompt_text']);self.assertEqual(v['current']['scope']['write'],['task_cli.py','tests/**','README.md'])
            self.assertTrue(all(x['implementation_stage']==v['active_stage'] for x in v['tasks']))
            self.assertEqual([x['level'] for x in v['future_outlines']],['ALPHA','BETA','MVP'])
            self.assertTrue(all('tasks' not in x and x['work_package_outlines'] for x in v['future_outlines']))
            self.assertTrue(v['verification_plan']['commands']); self.assertTrue(v['context'])
        self.assertEqual(before,byte_snapshot(root))

    def test_upload_verify_complete_next_and_exact_duplicate_replay(self):
        root=self.project();implement_first_task(root);self.receive()
        v=view(self.service,self.pid); self.assertEqual(v['result']['status'],'RESULT_RECEIVED');self.assertIsNone(v['verification_report'])
        self.assertEqual(self.verify()['result']['core_status'],'PASS')
        v=view(self.service,self.pid); req=OperationRequest(self.pid,'complete',{'binding_digest':v['binding_digest']},'completion-duplicate-key',v['fingerprint'])
        completed=self.run_action('complete',request=req);self.assertEqual(completed['result']['core_status'],'COMPLETED',completed)
        before=byte_snapshot(root);again=self.run_action('complete',request=req)
        self.assertEqual(again,completed);self.assertEqual(before,byte_snapshot(root))
        next_run=view(self.service,self.pid)['active_run']['run_ref'];self.run_action('next');self.assertEqual(next_run,view(self.service,self.pid)['active_run']['run_ref'])

    def test_canonical_channel_intake_is_exact_and_replay_is_immutable(self):
        root=self.project();implement_first_task(root);self.receive(canonical=True)
        v=view(self.service,self.pid);before=byte_snapshot(root)
        core.ingest_manual_result(root,binding_digest=v['binding_digest'])
        self.assertEqual(before,byte_snapshot(root))
        raw=json.dumps({**agent_result(root),'summary':'changed'}).encode()
        with self.assertRaisesRegex(HarnessError,'RESULT_CHANGED'):core.ingest_manual_result(root,binding_digest=v['binding_digest'],raw=raw)
        self.assertEqual(before,byte_snapshot(root))

    def test_wrong_run_task_unknown_fields_strict_json_and_paths(self):
        root=self.project();v=view(self.service,self.pid);valid=agent_result(root);before=byte_snapshot(root)
        variants=[{**valid,'run_ref':valid['run_ref']+'@1'},{**valid,'task_ref':'TSK-FOREIGN@1'},
            {**valid,'approved':True},{**valid,'schema_version':True},{**valid,'changes':{'added':['../x'],'modified':[],'deleted':[]}},
            {**valid,'stage_scope_violations':[True]}]
        raws=[json.dumps(x).encode() for x in variants]+[b'{"schema_version":1,"schema_version":1}',b'{"x":NaN}',b'[]',b'x'*1048577]
        for raw in raws:
            with self.subTest(raw=raw[:80]),self.assertRaises(HarnessError):
                stage_result(self.service,self.pid,raw,expected_fingerprint=v['fingerprint'],binding_digest=v['binding_digest'])
        self.assertEqual(before,byte_snapshot(root))

    def test_no_consent_never_executes_product_commands(self):
        root=self.project();implement_first_task(root);self.receive()
        with patch('project_harness.runtime._run_command',side_effect=AssertionError('no consent')):
            op=self.verify(False)
        self.assertEqual(op['result']['core_status'],'BLOCKED');v=view(self.service,self.pid)
        self.assertEqual(v['verification_report']['gates']['commands'],'BLOCKED');self.assertFalse(v['status']['completed_task_refs'])
        first_report=root/v['active_run']['verification_report_path'];first_evidence=root/v['active_run']['verification_evidence_path']
        frozen=(first_report.read_bytes(),first_evidence.read_bytes())
        accepted=self.verify(True);self.assertEqual(accepted['state'],'SUCCEEDED',accepted)
        self.assertEqual(accepted['result']['core_status'],'PASS')
        self.assertEqual(frozen,(first_report.read_bytes(),first_evidence.read_bytes()))
        self.assertNotEqual(v['active_run']['verification_report_ref'],view(self.service,self.pid)['active_run']['verification_report_ref'])

    def test_failing_verification_is_real_and_not_completion(self):
        root=self.project(command=[{'argv':[sys.executable,'-c','raise SystemExit(7)'],'cwd':'.','timeout_seconds':15}]);implement_first_task(root);self.receive()
        self.assertEqual(self.verify()['result']['core_status'],'FAIL');v=view(self.service,self.pid)
        self.assertEqual(v['verification_report']['command_results'][0]['returncode'],7)
        with self.assertRaises(HarnessError):core.complete_manual_task(root,binding_digest=v['binding_digest'])

    def test_stale_product_before_ingestion_and_after_verification(self):
        root=self.project();implement_first_task(root);v=view(self.service,self.pid);raw=json.dumps(agent_result(root)).encode()
        (root/'task_cli.py').write_text('# changed','utf-8')
        with self.assertRaisesRegex(HarnessError,'STALE_RESULT_BASELINE'):core.ingest_manual_result(root,binding_digest=v['binding_digest'],raw=raw)
        implement_first_task(root);self.receive();self.verify();v=view(self.service,self.pid)
        (root/'task_cli.py').write_text('# later change','utf-8')
        with self.assertRaisesRegex(HarnessError,'STALE_RESULT_BASELINE'):core.complete_manual_task(root,binding_digest=v['binding_digest'])
        self.assertEqual(view(self.service,self.pid)['result']['status'],'STALE_OR_CHANGED')

    def test_changed_canonical_result_after_receive_is_rejected(self):
        root=self.project();implement_first_task(root);self.receive();v=view(self.service,self.pid)
        path=root/v['active_run']['allowed_agent_output_path'];raw=json.loads(path.read_text('utf-8'));raw['summary']='replacement';path.write_text(json.dumps(raw),'utf-8')
        with self.assertRaisesRegex(HarnessError,'RESULT_CHANGED'):core.verify_manual_task(root,binding_digest=v['binding_digest'],plan_digest=v['verification_plan']['digest'],consent=True)

    def test_forbidden_product_write_fails_scope(self):
        root=self.project(command=[]);implement_first_task(root);(root/'outside.txt').write_text('forbidden','utf-8');self.receive()
        self.assertEqual(self.verify()['result']['core_status'],'FAIL');v=view(self.service,self.pid)
        self.assertIn('outside.txt',v['verification_report']['scope_validation']['outside_write_scope'])

    def test_control_tamper_before_ingest_and_by_verification(self):
        root=self.project(command=[{'argv':[sys.executable,'-c',"from pathlib import Path; Path('AGENTS.md').write_text('tampered')"],'cwd':'.','timeout_seconds':15}]);implement_first_task(root);self.receive()
        self.assertEqual(self.verify()['result']['core_status'],'BLOCKED')
        state=load_data(root/'.harness/state/CURRENT_STATE.yaml')['state']
        self.assertEqual(state['next_route'],'RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN')
        with self.assertRaises(HarnessError):core.resume_manual_task(root,blocker_ref=state['open_blocker_refs'][0]+'@1',resolution='unsafe')

    def test_missing_toolchain_has_clear_prerequisite_no_install(self):
        root=self.project(command=[{'argv':['ph-lw09-tool-not-installed-9823'],'cwd':'.','timeout_seconds':15}]);implement_first_task(root);self.receive();v=view(self.service,self.pid)
        self.assertEqual(v['verification_plan']['commands'][0]['prerequisite'],'PRODUCT_TOOLCHAIN_OR_CWD_MISSING')
        op=self.verify();self.assertEqual(op['error']['code'],'PRODUCT_TOOLCHAIN_MISSING');self.assertIsNone(view(self.service,self.pid)['verification_report'])

    def test_manual_checks_cannot_pass_by_allow_manual_flag(self):
        root=self.project(manual=True,command=[]);implement_first_task(root);self.receive()
        op=self.verify();self.assertEqual(op['result']['core_status'],'BLOCKED')
        self.assertEqual(view(self.service,self.pid)['verification_report']['gates']['manual_checks'],'BLOCKED')

    def test_exact_block_resume_and_old_result_rejected(self):
        root=self.project();old=agent_result(root);v=view(self.service,self.pid)
        op=self.run_action('block',{'run_ref':v['active_run']['run_ref'],'reason':'Missing fixture input'});self.assertEqual(op['result']['core_status'],'BLOCKED')
        v=view(self.service,self.pid);ref=v['blockers'][0]['id']+'@1';before=byte_snapshot(root)
        for bad in ('BLK-FOREIGN@1',ref.replace('@1','@2'),'../escape'):
            with self.assertRaises(HarnessError):core.resume_manual_task(root,blocker_ref=bad,resolution='fixed')
        self.assertEqual(before,byte_snapshot(root))
        op=self.run_action('resume',{'blocker_ref':ref,'resolution':'Input supplied'});self.assertEqual(op['result']['core_status'],'RESUMED',op)
        v=view(self.service,self.pid);self.assertNotEqual(v['active_run']['run_ref'],old['run_ref'])
        with self.assertRaises(HarnessError):core.ingest_manual_result(root,binding_digest=v['binding_digest'],raw=json.dumps(old).encode())

    def test_stale_consent_wrong_plan_and_missing_result_refused(self):
        root=self.project();implement_first_task(root);v=view(self.service,self.pid)
        with self.assertRaisesRegex(HarnessError,'RESULT_REQUIRED'):core.verify_manual_task(root,binding_digest=v['binding_digest'],plan_digest=v['verification_plan']['digest'],consent=True)
        self.receive();v=view(self.service,self.pid)
        with self.assertRaisesRegex(HarnessError,'STALE_VERIFICATION_PLAN'):core.verify_manual_task(root,binding_digest=v['binding_digest'],plan_digest='sha256:'+'0'*64,consent=True)

    def test_automatic_project_read_only_no_host_fallback(self):
        root=self.project()
        # Synthetic pre-existing automatic policy, no automatic execution or
        # policy activation API. This fixture is not user acceptance of Podman.
        from tests.test_ph_051_05_codex_adapter import install_profiles
        from project_harness.workspace import record_phase_boundary
        from project_harness.util import utc_now
        active=load_data(root/'.harness/state/CURRENT_STATE.yaml')['state']['active_run']
        install_profiles(root)
        record_phase_boundary(root,active,phase='TEST_EXISTING_AUTOMATIC_PROJECT',recorded_at=utc_now())
        before=byte_snapshot(root);v=view(self.service,self.pid)
        self.assertEqual(v['execution_mode'],'LOCAL_AUTOMATIC');self.assertTrue(v['disabled_reason'])
        with self.assertRaises(HarnessError):core.ingest_manual_result(root,binding_digest=v['binding_digest'],raw=json.dumps(agent_result(root)).encode())
        with self.assertRaises(HarnessError):verify_current(root,allow_command_execution=True)
        self.assertEqual(before,byte_snapshot(root))

    def test_multitab_stale_revision_and_same_key_different_payload(self):
        root=self.project();v=view(self.service,self.pid)
        req=OperationRequest(self.pid,'block',{'run_ref':v['active_run']['run_ref'],'reason':'one'},'multitab-shared-key',v['fingerprint'])
        self.run_action('block',request=req);before=byte_snapshot(root)
        with self.assertRaises(HarnessError):self.service.submit(OperationRequest(self.pid,'block',{'run_ref':v['active_run']['run_ref'],'reason':'two'},req.idempotency_key,v['fingerprint']),check_current=True)
        with self.assertRaises(HarnessError):self.service.submit(OperationRequest(self.pid,'next',{},'different-tab-stale-key',v['fingerprint']),check_current=True)
        self.assertEqual(before,byte_snapshot(root))

    def test_recovery_never_reexecutes_ambiguous_command(self):
        root=self.project();implement_first_task(root);self.receive()
        op=self.verify();count=len(load_data(root/'.harness/runtime/OPERATION_JOURNAL'/ (view(self.service,self.pid)['active_run']['run_ref']+'.yaml'))['operation_journal']['boundaries'])
        op['state']='RUNNING';op['phase']='MUTATING';self.service._save_op(op)  # explicit crash fault, not product flow
        with patch('project_harness.runtime._run_command',side_effect=AssertionError('replayed command')):
            recovered=self.service.reconcile_operation(self.pid,op['operation_id'])
        self.assertEqual(recovered['state'],'BLOCKED');self.assertEqual(recovered['error']['code'],'AMBIGUOUS_COMMIT')
        self.assertEqual(count,len(load_data(root/'.harness/runtime/OPERATION_JOURNAL'/ (view(self.service,self.pid)['active_run']['run_ref']+'.yaml'))['operation_journal']['boundaries']))

    def test_forged_change_claim_does_not_complete_despite_verification_pass(self):
        root=self.project(command=[]);implement_first_task(root);raw=agent_result(root)
        raw['changes']={'added':[],'modified':[],'deleted':[]};self.receive(json.dumps(raw).encode())
        self.assertEqual(self.verify()['result']['core_status'],'PASS');v=view(self.service,self.pid)
        with self.assertRaisesRegex(HarnessError,'do not match'):core.complete_manual_task(root,binding_digest=v['binding_digest'])
        self.assertFalse(view(self.service,self.pid)['status']['completed_task_refs'])

    def test_missing_expected_paths_fail_without_trusting_completed_claim(self):
        root=self.project(command=[]);self.receive();self.assertEqual(self.verify()['result']['core_status'],'FAIL')
        self.assertIn('task_cli.py',view(self.service,self.pid)['verification_report']['missing_expected_paths'])

    def test_control_tamper_rejected_before_ingestion_without_sealing_it(self):
        root=self.project();v=view(self.service,self.pid);raw=json.dumps(agent_result(root)).encode()
        (root/'AGENTS.md').write_text('malicious instructions','utf-8');before=byte_snapshot(root)
        with self.assertRaisesRegex(HarnessError,'CONTROL_TAMPER'):core.ingest_manual_result(root,binding_digest=v['binding_digest'],raw=raw)
        self.assertEqual(before,byte_snapshot(root));self.assertTrue(view(self.service,self.pid)['disabled_reason'])

    def test_hardlinked_canonical_result_is_rejected(self):
        root=self.project();v=view(self.service,self.pid);raw=json.dumps(agent_result(root)).encode()
        external=self.base/'external.json';external.write_bytes(raw);os.link(external,root/v['active_run']['allowed_agent_output_path'])
        before=byte_snapshot(root)
        with self.assertRaises(HarnessError):core.ingest_manual_result(root,binding_digest=v['binding_digest'])
        self.assertEqual(before,byte_snapshot(root))

    def test_result_publication_interruption_preserves_partial_and_fails_closed(self):
        root=self.project();v=view(self.service,self.pid);raw=json.dumps(agent_result(root)).encode()
        with patch('project_harness.manual_tasks.record_phase_boundary',side_effect=OSError('injected interruption')):
            with self.assertRaises(OSError):core.ingest_manual_result(root,binding_digest=v['binding_digest'],raw=raw)
        before=byte_snapshot(root);self.assertTrue((root/v['active_run']['allowed_agent_output_path']).is_file())
        with self.assertRaisesRegex(HarnessError,'CONTROL_TAMPER'):core.ingest_manual_result(root,binding_digest=v['binding_digest'],raw=raw)
        self.assertEqual(before,byte_snapshot(root))

    def test_missing_task_dependency_refused_before_next_mutation(self):
        root=self.project()
        # Fault fixture: READY current task with an unmet dependency. The public
        # next wrapper must reject it before invoking the existing reservation API.
        statepath=root/'.harness/state/CURRENT_STATE.yaml';doc=load_data(statepath);doc['state']['active_run']=None
        doc['state']['next_route']='COMPILE_FIRST_READY_TASK';write_data(statepath,doc)
        tid=doc['state']['current_task_ref'];index=load_data(root/'.harness/tasks/INDEX.yaml')['task_index']
        path=root/index['current'][tid];task=load_data(path);task['task']['depends_on_tasks']=['TSK-MISSING-DEPENDENCY'];write_data(path,task)
        before=byte_snapshot(root)
        with self.assertRaisesRegex(HarnessError,'TASK_DEPENDENCIES_MISSING'):core.next_manual_task(root)
        self.assertEqual(before,byte_snapshot(root))

    def test_foreign_upload_id_cannot_be_used_by_another_project(self):
        root=self.project();v=view(self.service,self.pid);raw=json.dumps(agent_result(root)).encode()
        staged=stage_result(self.service,self.pid,raw,expected_fingerprint=v['fingerprint'],binding_digest=v['binding_digest'])
        _,_,other=prepare_demo(self.base/'other',data=fixture_input());other_id=self.service.register_existing(other,kind='project')
        other_view=view(self.service,other_id);before=byte_snapshot(other)
        from project_harness.local_web_tasks import execute
        with self.assertRaisesRegex(HarnessError,'RESULT_UPLOAD_MISMATCH'):
            execute(self.service,other_id,'receive-result',{'upload_id':staged['upload_id'],'binding_digest':other_view['binding_digest']})
        self.assertEqual(before,byte_snapshot(other))

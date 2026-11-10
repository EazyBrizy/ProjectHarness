"""PH-LW-10 service: public-flow advanced fixtures, strict negative/replay paths."""
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest
import atexit
import subprocess
import sys
import os
import ctypes
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from unittest import mock
from project_harness.local_web_service import LocalWebService, OperationRequest
from project_harness.local_web_lifecycle import view, read_draft
from project_harness.lifecycle_forms import repository_binding
from project_harness.serialization import load_data
from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.stages import stage_status
from tests.ph_f06_fixtures import prepared, reach_gate, accept, history_snapshot, complete_task
from tests.test_ph_lw_03_service import byte_snapshot


def request(service, pid, action, payload=None, *, key=None, fingerprint=None):
    from uuid import uuid4
    dto = OperationRequest(pid, action, payload or {}, key or uuid4().hex,
        fingerprint or service.get_status(pid)['fingerprint'])
    queued = service.submit(dto, check_current=True)
    return service.wait_for(queued['operation_id'], timeout=180)


def draft(service, pid, action):
    op = request(service, pid, action)
    if op['state'] != 'SUCCEEDED': raise AssertionError(op)
    return read_draft(service, pid, op['operation_id'])


def payload(form, document=None, **updates):
    return {'draft_id': form['draft_id'], 'document': deepcopy(form['document'] if document is None else document),
            'actor': 'ACT-LW10-REVIEWER', 'confirmed': True, 'rationale': '', **updates}


def review_gate(document):
    value=deepcopy(document); body=value['stage_approval']; candidates={}
    for candidate in body['evidence_candidates']:
        for subject in candidate['compatible_subject_refs']: candidates[subject]=candidate['ref']
    for field, key in [('outcome_results','outcome_ref'),('criteria_results','criterion_ref'),
                       ('hard_constraint_results','constraint_ref'),('profile_control_results','control_ref')]:
        for result in body[field]:
            result.update(status='PASS', evidence_refs=[candidates[result[key]]],
                rationale='Independent review of exact public fixture source for this subject.', validator='ACT-LW10-REVIEWER')
    body['permitted_use']['status']='CONFIRMED'
    body['known_limitations']=['Synthetic local CLI fixture, not a production maturity claim.']
    body['next_stage_gaps']=['Review next Stage only within accepted scope.']
    return value


def fill_maintenance(form):
    value=deepcopy(form['document']);body=value['maintenance_plan']
    body.update(objective='Maintain README within accepted scope.',rationale='Clarify existing local CLI usage.')
    wp=body['work_package'];wp.update(title='README clarification',objective=body['objective'])
    task=wp['tasks'][0];task.update(title='Document current CLI',purpose='Clarify existing usage',expected_result='README clarification reviewed',
        produces_artifacts=['README.md'],acceptance_criteria=['README describes existing CLI only.'])
    task['scope'].update(read=['README.md'],write=['README.md'])
    task['verification'].update(expected_paths=['README.md'],manual_checks=['README describes existing CLI only.'])
    task['documentation'].update(impact='UPDATE_EXISTING',required_updates=['README.md'])
    return value


@lru_cache(maxsize=1)
def public_fixtures():
    cache=tempfile.TemporaryDirectory(prefix='LW10 public fixture ');atexit.register(cache.cleanup);base=Path(cache.name)
    gate=prepared(base/'gate',target='MVP');reach_gate(gate,base/'gate-records','PROTOTYPE')
    accepted=prepared(base/'accepted',target='PROTOTYPE');accept(accepted,base/'accepted-records','PROTOTYPE')
    return gate,accepted


class MigrationPollingTests(unittest.TestCase):
    def test_owned_receipt_remains_readable_during_backup_cleanup(self):
        import threading
        from project_harness import migration,lifecycle_forms
        from tests.test_engine import prepare_demo
        from tests.test_ph_051_10_migration_recovery import downgrade_to_v050
        with tempfile.TemporaryDirectory(prefix='LW10 concurrent migration ') as directory:
            base=Path(directory);root=prepare_demo(base/'legacy')[2];downgrade_to_v050(root)
            service=LocalWebService(base/'app');self.addCleanup(service.close)
            pid=service.register_existing(root,kind='migration');form=draft(service,pid,'prepare-migration')
            renamed=threading.Event();commit=threading.Event();original=lifecycle_forms.sha256_file
            def pause(phase):
                if phase=='AFTER_NEW_RENAME':
                    renamed.set()
                    if not commit.wait(30):raise TimeoutError('Test did not release migration swap')
            def racing_read(path):
                backups=[p for p in Path(path).parents if '.ph05110-backup-' in p.name]
                if backups and threading.current_thread() is threading.main_thread():
                    # A real core cleanup removes the file after the poll has
                    # enumerated it, before open/hash. No fake canonical state.
                    commit.set();deadline=time.monotonic()+30
                    while backups[0].exists() and time.monotonic()<deadline:time.sleep(.01)
                    self.assertFalse(backups[0].exists())
                return original(path)
            try:
                with mock.patch.object(migration,'_v051_migration_fault',side_effect=pause),mock.patch.object(lifecycle_forms,'sha256_file',side_effect=racing_read):
                    op=service.submit(OperationRequest(pid,'migrate-project',payload(form),'migration-live-poll',form['fingerprint']),check_current=True)
                    self.assertTrue(renamed.wait(30))
                    try:
                        current=service.get_operation(pid,op['operation_id'])
                        self.assertEqual(current['state'],'RUNNING')
                    finally:commit.set()
                    self.assertEqual(service.wait_for(op['operation_id'],timeout=60)['state'],'SUCCEEDED')
                    self.assertEqual(service.get_operation(pid,op['operation_id'])['result']['core_status'],'MIGRATED')
            finally:
                commit.set();service.close()


class LifecycleServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate,cls.accepted=public_fixtures()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='LW10 service Кириллица ');self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.service=LocalWebService(self.base/'app');self.addCleanup(self.service.close)
        self.root=self.base/'project';shutil.copytree(self.gate,self.root)
        self.pid=self.service.register_existing(self.root,kind='project')
    def use_accepted(self):
        self.root=self.base/'accepted';shutil.copytree(self.accepted,self.root)
        self.pid=self.service.register_existing(self.root,kind='project')
    def assert_ok(self,op): self.assertEqual(op['state'],'SUCCEEDED',op);return op

    def test_get_is_read_only_and_lists_exact_semantic_subjects(self):
        before=byte_snapshot(self.root)
        actions=self.service.get_status(self.pid)['available_actions']
        self.assertEqual(len({a['id'] for a in actions}),len(actions))
        for _ in range(3):
            v=view(self.service,self.pid);self.assertEqual(v['status']['target_level'],'MVP')
            self.assertIn('claimed_current_level',v['status']);self.assertIn('observed_candidate_level',v['status'])
            self.assertTrue(v['evidence_candidates']);self.assertEqual(v['automatic_executor'],'DISABLED')
        self.assertEqual(before,byte_snapshot(self.root))

    def test_prototype_accept_alpha_plan_first_ready_and_exact_replay(self):
        form=draft(self.service,self.pid,'prepare-stage-approval');before=history_snapshot(self.root)
        self.assertFalse(form['document']['stage_approval']['approved'])
        body=payload(form,review_gate(form['document']));fp=view(self.service,self.pid)['fingerprint'];key='stage-accept-exact-replay'
        self.assert_ok(request(self.service,self.pid,'accept-stage',body,key=key,fingerprint=fp))
        after=byte_snapshot(self.root);self.assert_ok(request(self.service,self.pid,'accept-stage',body,key=key,fingerprint=fp));self.assertEqual(after,byte_snapshot(self.root))
        for rel,data in before.items():self.assertEqual(sha256_file(self.root/rel),data)
        plan=draft(self.service,self.pid,'prepare-active-stage-plan');self.assertIsNone(plan['document']['active_stage_plan_review']['review']['decision'])
        self.assert_ok(request(self.service,self.pid,'plan-active-stage',payload(plan)))
        s=stage_status(self.root);self.assertEqual(s['active_stage'],'ALPHA');self.assertEqual(s['highest_accepted_level'],'PROTOTYPE')
        from project_harness.runtime import project_status
        self.assertIsNotNone(project_status(self.root)['active_run'])
        self.assertTrue(all(x['detailed_work_package_count']==0 for x in s['stages'] if x['level'] in {'BETA','MVP'}))

    def test_missing_proof_and_unknown_results_cannot_raise_maturity(self):
        form=draft(self.service,self.pid,'prepare-stage-approval')
        op=request(self.service,self.pid,'accept-stage',payload(form))
        self.assertNotEqual(op['state'],'SUCCEEDED');self.assertEqual(stage_status(self.root)['highest_accepted_level'],'NONE')

    def test_forged_semantic_source_rejected_even_all_pass(self):
        form=draft(self.service,self.pid,'prepare-stage-approval');document=review_gate(form['document'])
        document['stage_approval']['criteria_results'][0]['evidence_refs']=['EVD-NOT-REAL']
        self.assertNotEqual(request(self.service,self.pid,'accept-stage',payload(form,document))['state'],'SUCCEEDED')
        self.assertEqual(stage_status(self.root)['highest_accepted_level'],'NONE')

    def test_consent_unknown_fields_changed_binding_and_cross_project_draft(self):
        form=draft(self.service,self.pid,'prepare-stage-approval');before=byte_snapshot(self.root)
        self.assertNotEqual(request(self.service,self.pid,'accept-stage',payload(form,confirmed=False))['state'],'SUCCEEDED')
        bad=payload(form);bad['document']['stage_approval']['target_level']='RELEASE'
        self.assertNotEqual(request(self.service,self.pid,'accept-stage',bad)['state'],'SUCCEEDED')
        with self.assertRaises(ValidationFailure):request(self.service,self.pid,'accept-stage',{**payload(form),'path':'C:/Windows'})
        self.use_accepted()
        with self.assertRaises(ValidationFailure):read_draft(self.service,self.pid,form['draft_id'])
        self.assertEqual(before,byte_snapshot(self.base/'project'))

    def test_stale_form_and_replay_key_payload_conflict(self):
        form=draft(self.service,self.pid,'prepare-stage-approval');fp=view(self.service,self.pid)['fingerprint']
        (self.root/'README.md').write_text('Changed external product baseline','utf-8')
        with self.assertRaisesRegex(ValidationFailure,'STALE_FINGERPRINT'):request(self.service,self.pid,'accept-stage',payload(form),fingerprint=fp)
        op=request(self.service,self.pid,'accept-stage',payload(form),key='stale-form-adapter-123')
        self.assertNotEqual(op['state'],'SUCCEEDED')
        with self.assertRaises(ValidationFailure):request(self.service,self.pid,'accept-stage',payload(form,actor='ACT-OTHER'),key='stale-form-adapter-123')

    def test_level_up_nearest_stage_canonical_target_and_noop(self):
        self.use_accepted();before=history_snapshot(self.root)
        form=draft(self.service,self.pid,'prepare-level-up')
        self.assertEqual(self.assert_ok(request(self.service,self.pid,'level-up',payload(form)))['result']['lifecycle']['status'],'TARGET_ALREADY_REACHED')
        document=deepcopy(form['document']);document['level_up_approval']['target_level']='RELEASE'
        self.assert_ok(request(self.service,self.pid,'level-up',payload(form,document)))
        status=stage_status(self.root);self.assertEqual(status['target_level'],'RELEASE');self.assertEqual(status['active_stage'],'ALPHA')
        self.assertEqual(load_data(self.root/'.harness/state/PROJECT_INPUT_ACCEPTED.yaml')['implementation']['target_level'],'PROTOTYPE')
        for rel,data in before.items():self.assertEqual(sha256_file(self.root/rel),data)
        again=draft(self.service,self.pid,'prepare-level-up');doc=deepcopy(again['document']);doc['level_up_approval']['target_level']='MVP'
        self.assertNotEqual(request(self.service,self.pid,'level-up',payload(again,doc))['state'],'SUCCEEDED')

    def test_maintenance_start_cancel_preserves_maturity(self):
        self.use_accepted();before=history_snapshot(self.root)
        form=draft(self.service,self.pid,'prepare-maintenance');self.assert_ok(request(self.service,self.pid,'start-maintenance',payload(form,fill_maintenance(form))))
        cancel=draft(self.service,self.pid,'prepare-maintenance-cancel');doc=deepcopy(cancel['document']);doc['maintenance_cancel_approval']['rationale']='Cancelled before any product change.'
        self.assert_ok(request(self.service,self.pid,'cancel-maintenance',payload(cancel,doc)))
        self.assertEqual(stage_status(self.root)['highest_accepted_level'],'PROTOTYPE')
        for rel,data in before.items():self.assertEqual(sha256_file(self.root/rel),data)

    def test_edited_active_plan_requires_review_and_rejects_material_scope_change(self):
        form=draft(self.service,self.pid,'prepare-stage-approval')
        self.assert_ok(request(self.service,self.pid,'accept-stage',payload(form,review_gate(form['document']))))
        plan=draft(self.service,self.pid,'prepare-active-stage-plan');doc=deepcopy(plan['document'])
        doc['active_stage_plan_review']['work_packages'][0]['title']='Reviewed current-stage work'
        self.assertNotEqual(request(self.service,self.pid,'plan-active-stage',payload(plan,doc))['state'],'SUCCEEDED')
        divergent=deepcopy(doc);divergent['active_stage_plan_review']['review']['material_change']=True
        self.assertNotEqual(request(self.service,self.pid,'plan-active-stage',payload(plan,divergent,rationale='Not authorized scope expansion'))['state'],'SUCCEEDED')
        self.assert_ok(request(self.service,self.pid,'plan-active-stage',payload(plan,doc,rationale='Only the work package title was clarified; accepted scope retained.')))

    def test_accepted_mvp_level_up_release_through_adapter(self):
        from tests.ph_f06_fixtures import plan
        # This setup is explicitly a public kernel advanced-state fixture.
        form=draft(self.service,self.pid,'prepare-stage-approval')
        self.assert_ok(request(self.service,self.pid,'accept-stage',payload(form,review_gate(form['document']))))
        for level in ('ALPHA','BETA','MVP'):
            plan(self.root,self.base/'mvp-records',level);accept(self.root,self.base/'mvp-records',level)
        before=history_snapshot(self.root);form=draft(self.service,self.pid,'prepare-level-up')
        doc=deepcopy(form['document']);doc['level_up_approval']['target_level']='RELEASE'
        self.assert_ok(request(self.service,self.pid,'level-up',payload(form,doc)))
        status=stage_status(self.root);self.assertEqual(status['active_stage'],'RELEASE');self.assertEqual(status['highest_accepted_level'],'MVP')
        for rel,data in before.items():self.assertEqual(sha256_file(self.root/rel),data)

    def test_maintenance_cancel_after_completed_product_change_rejected(self):
        self.use_accepted();form=draft(self.service,self.pid,'prepare-maintenance');doc=fill_maintenance(form)
        tasks=doc['maintenance_plan']['work_package']['tasks'];second=deepcopy(tasks[0]);second['id']=second['id'][:-3]+'002';second['depends_on_tasks']=[tasks[0]['id']];tasks.append(second)
        self.assert_ok(request(self.service,self.pid,'start-maintenance',payload(form,doc)))
        with (self.root/'README.md').open('a',encoding='utf-8') as f:f.write('\nFirst maintenance change.\n')
        complete_task(self.root,'Completed first product-changing maintenance Task')
        cancel=draft(self.service,self.pid,'prepare-maintenance-cancel');c=deepcopy(cancel['document']);c['maintenance_cancel_approval']['rationale']='Invalid cancellation after product change'
        before=byte_snapshot(self.root);self.assertNotEqual(request(self.service,self.pid,'cancel-maintenance',payload(cancel,c))['state'],'SUCCEEDED')
        self.assertEqual(before,byte_snapshot(self.root));self.assertEqual(stage_status(self.root)['highest_accepted_level'],'PROTOTYPE')

    def test_maintenance_complete_uses_existing_manual_task_lifecycle(self):
        self.use_accepted();form=draft(self.service,self.pid,'prepare-maintenance')
        self.assert_ok(request(self.service,self.pid,'start-maintenance',payload(form,fill_maintenance(form))))
        with (self.root/'README.md').open('a',encoding='utf-8') as f:f.write('\nClarified existing CLI usage.\n')
        complete_task(self.root,'Public external fixture manual maintenance')
        self.assertEqual(stage_status(self.root)['highest_accepted_level'],'PROTOTYPE')
        self.assertEqual(stage_status(self.root)['runtime_phase'],'TARGET_LEVEL_REACHED')

    def test_gate_recovery_is_separate_from_task_recovery(self):
        # Existing resolved Gate recovery is an idempotent public route.
        before=byte_snapshot(self.root)
        self.assertEqual(request(self.service,self.pid,'resume-stage-gate',{'confirmed':True})['result']['lifecycle']['status'],'VERIFYING')
        self.assertEqual(before,byte_snapshot(self.root))
        from tests.test_engine import prepare_demo
        from project_harness.runtime import block_current
        root=prepare_demo(self.base/'ordinary')[2];block_current(root,'Ordinary Task failure')
        pid=self.service.register_existing(root,kind='project');before=byte_snapshot(root)
        self.assertNotEqual(request(self.service,pid,'resume-stage-gate',{'confirmed':True})['state'],'SUCCEEDED')
        self.assertEqual(before,byte_snapshot(root))

    def test_migration_validator_confirmation_replay_history(self):
        from tests.test_engine import prepare_demo
        from tests.test_ph_051_10_migration_recovery import downgrade_to_v050
        root=prepare_demo(self.base/'legacy')[2];history=downgrade_to_v050(root)
        pid=self.service.register_existing(root,kind='migration');form=draft(self.service,pid,'prepare-migration')
        actions=self.service.get_status(pid)['available_actions']
        self.assertEqual(len({a['id'] for a in actions}),len(actions))
        self.assertTrue(form['document']['migration']['supported']);fp=view(self.service,pid)['fingerprint'];key='migration-replay-key-123'
        self.assert_ok(request(self.service,pid,'migrate-project',payload(form),key=key,fingerprint=fp))
        after=byte_snapshot(root);self.assert_ok(request(self.service,pid,'migrate-project',payload(form),key=key,fingerprint=fp));self.assertEqual(after,byte_snapshot(root))
        for rel,data in history.items():self.assertEqual((root/rel).read_bytes(),data)
        form=draft(self.service,pid,'prepare-migration');self.assertEqual(self.assert_ok(request(self.service,pid,'migrate-project',payload(form)))['result']['lifecycle']['status'],'NO_ACTION')

    def test_migration_process_crash_explicit_web_recovery_missing_root(self):
        from tests.test_engine import prepare_demo
        from tests.test_ph_051_10_migration_recovery import downgrade_to_v050
        code='import os,sys;from pathlib import Path;from project_harness import migration;migration._v051_migration_fault=lambda phase: os._exit(79) if phase==sys.argv[2] else None;migration.migrate_project(Path(sys.argv[1]))'
        for phase in ('AFTER_OLD_RENAME','AFTER_NEW_RENAME'):
            with self.subTest(phase=phase):
                root=prepare_demo(self.base/phase)[2];history=downgrade_to_v050(root)
                pid=self.service.register_existing(root,kind='migration')
                child=subprocess.run([sys.executable,'-B','-c',code,str(root),phase],capture_output=True,timeout=120)
                self.assertEqual(child.returncode,79,child.stderr)
                status=self.service.get_status(pid);self.assertEqual(status['core_status'],'MIGRATION_RECOVERY_REQUIRED')
                self.assertEqual(root.exists(),phase=='AFTER_NEW_RENAME')
                if phase=='AFTER_OLD_RENAME':
                    from project_harness.migration import _migration_marker
                    from project_harness.serialization import write_data
                    marker=_migration_marker(root);journal=load_data(marker);backup=root.parent/journal['backup']
                    accepted=backup/'.harness/state/PROJECT_INPUT_ACCEPTED.yaml';original=accepted.read_bytes()
                    value=load_data(accepted);value['execution']={'mode':'AUTOMATIC'};write_data(accepted,value)
                    snapshot=byte_snapshot(backup);marker_bytes=marker.read_bytes()
                    self.assertNotEqual(request(self.service,pid,'recover-migration',{'confirmed':True})['state'],'SUCCEEDED')
                    self.assertEqual(snapshot,byte_snapshot(backup));self.assertEqual(marker.read_bytes(),marker_bytes);self.assertFalse(root.exists())
                    accepted.write_bytes(original)
                self.assert_ok(request(self.service,pid,'recover-migration',{'confirmed':True}))
                for rel,data in history.items():self.assertEqual((root/rel).read_bytes(),data)
                self.assertEqual(load_data(root/'.harness/config/PROJECT_LOCK.yaml')['project_lock']['execution']['mode'],'MANUAL_HANDOFF')

    def test_brownfield_readonly_assessment_rejects_stale_repository(self):
        from project_harness.intake import start_intake
        from tests.test_engine import load_fixture, add_brownfield_approval
        from project_harness.serialization import write_data
        data=load_fixture();data['project']['mode']='BROWNFIELD';data['implementation']['claimed_current_level']='BETA';add_brownfield_approval(data)
        inp=self.base/'input.json';write_data(inp,data);repo=self.base/'repository';repo.mkdir();(repo/'README.md').write_text('# beta is a claim','utf-8')
        ws=self.base/'intake';start_intake(ws,project_name='Brownfield',mode='BROWNFIELD',repository=repo,initial_input=inp)
        pid=self.service.register_existing(ws,kind='workspace');before=byte_snapshot(repo);fp=view(self.service,pid)['fingerprint']
        self.assert_ok(request(self.service,pid,'assess-maturity',{'confirmed':True}));self.assertEqual(before,byte_snapshot(repo))
        self.assertTrue(view(self.service,pid)['baseline_approval_required'])
        (repo/'README.md').write_text('beta changed','utf-8');self.assertTrue(repository_binding(ws)['stale'])
        with self.assertRaises(ValidationFailure):request(self.service,pid,'assess-maturity',{'confirmed':True},fingerprint=fp)

    def test_legacy_v041_migration_form_keeps_completed_runs(self):
        from project_harness.resources import distribution_root
        with zipfile.ZipFile(distribution_root()/'fixtures/legacy_v0.4.1_completed_handoff.zip') as archive:
            archive.extractall(self.base/'v041')
        root=next((self.base/'v041').rglob('CURRENT_STATE.yaml')).parents[2]
        runs={p.relative_to(root).as_posix():p.read_bytes() for p in (root/'.harness/runtime/RUNS').glob('*.yaml')}
        pid=self.service.register_existing(root,kind='migration');form=draft(self.service,pid,'prepare-migration')
        self.assertTrue(form['document']['migration']['supported']);self.assertIn('$defs',form['schema'])
        document=deepcopy(form['document']);document['migration']['input_document']['implementation']['target_level']='MVP'
        self.assert_ok(request(self.service,pid,'migrate-project',payload(form,document)))
        for rel,data in runs.items():self.assertEqual((root/rel).read_bytes(),data)
        # The existing v0.4.1 converter uses the schema's MANUAL_HANDOFF default
        # when execution is absent in its immutable legacy lock contract.
        from project_harness.lifecycle_forms import assert_manual
        from project_harness.manual_tasks import task_console
        assert_manual(root);self.assertEqual(task_console(root)['execution_mode'],'MANUAL_HANDOFF')

    def test_automatic_lifecycle_is_rejected_before_mutation(self):
        from project_harness.serialization import write_data
        from project_harness.local_web_lifecycle import execute
        path=self.root/'.harness/state/PROJECT_INPUT_ACCEPTED.yaml';value=load_data(path)
        value['execution']['mode']='AUTOMATIC';write_data(path,value)
        before=byte_snapshot(self.root)
        with self.assertRaisesRegex(ValidationFailure,'AUTOMATIC_DISABLED'):
            execute(self.service,self.pid,'LWO-'+'A'*24,'prepare-level-up',{})
        self.assertEqual(before,byte_snapshot(self.root))

    def test_selection_is_narrow_and_cancel_does_not_mutate_repository(self):
        from project_harness.local_web_selection import select
        repo=self.base/'selected';repo.mkdir();(repo/'README.md').write_text('# beta','utf-8');before=byte_snapshot(repo)
        result=select(self.service,purpose='repository',project_name='Selected',mode='HYBRID',idempotency_key='selected-repository-123',picker=lambda:repo)
        self.assertEqual(result['status'],'SELECTED');self.assertEqual(before,byte_snapshot(repo))
        self.assertEqual(select(self.service,purpose='repository',project_name='Selected',mode='HYBRID',idempotency_key='selected-repository-123',picker=lambda: self.fail('replay opened picker')),result)

    def test_interruption_after_commit_never_reexecutes(self):
        self.use_accepted();form=draft(self.service,self.pid,'prepare-level-up');doc=deepcopy(form['document']);doc['level_up_approval']['target_level']='ALPHA'
        original=self.service._save_op
        def crash(op):
            if op['action']=='level-up' and op['state']=='SUCCEEDED':raise OSError('simulated receipt interruption after canonical commit')
            return original(op)
        with mock.patch.object(self.service,'_save_op',side_effect=crash):op=request(self.service,self.pid,'level-up',payload(form,doc))
        before=history_snapshot(self.root);recovered=self.service.reconcile_operation(self.pid,op['operation_id'])
        self.assertEqual(recovered['state'],'SUCCEEDED',recovered)
        self.assertEqual(stage_status(self.root)['active_stage'],'ALPHA');self.assertEqual(before,history_snapshot(self.root))


@unittest.skipUnless(os.name=='nt','Real Windows native folder dialog required')
class NativeSelectionTests(unittest.TestCase):
    def test_native_folder_picker_selection_and_cancel(self):
        from project_harness.local_web_selection import choose_directory
        user=ctypes.windll.user32
        user.SendMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_void_p]
        user.SendMessageW.restype=ctypes.c_ssize_t
        callback=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
        def window_info(hwnd):
            text=ctypes.create_unicode_buffer(2048);kind=ctypes.create_unicode_buffer(128)
            user.GetWindowTextW(hwnd,text,len(text));user.GetClassNameW(hwnd,kind,len(kind))
            return (hwnd,kind.value,text.value,user.GetDlgCtrlID(hwnd))
        def children(hwnd):
            rows=[]
            @callback
            def visit(h,p):rows.append(window_info(h));return True
            user.EnumChildWindows(hwnd,visit,0);return rows
        # Operate only our exact-titled dialog; no global keyboard or arbitrary window.
        for cancel in (False,True):
            with self.subTest(cancel=cancel),ThreadPoolExecutor() as pool:
                future=pool.submit(choose_directory);dialog=None
                try:
                    for _ in range(150):
                        windows=[]
                        @callback
                        def visit(h,p):
                            if user.IsWindowVisible(h):windows.append(window_info(h))
                            return True
                        user.EnumWindows(visit,0)
                        for item in windows:
                            if item[1]=='#32770' and any('Project Harness: select an existing' in row[2] for row in children(item[0])):
                                dialog=item[0];break
                        if dialog:break
                        time.sleep(.1)
                    self.assertIsNotNone(dialog,'Native dialog did not open')
                    buttons=[r for r in children(dialog) if r[1]=='Button' and r[3]==(2 if cancel else 1)]
                    self.assertEqual(len(buttons),1)
                    user.SendMessageW(buttons[0][0],0xF5,0,None)
                    result=future.result(timeout=20)
                    if cancel:self.assertIsNone(result)
                    else:self.assertTrue(result.is_dir());self.assertTrue(result.is_absolute())
                finally:
                    if dialog and user.IsWindow(dialog):user.SendMessageW(dialog,0x10,0,None)


if __name__=='__main__':unittest.main()

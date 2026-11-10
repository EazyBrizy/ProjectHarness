"""Native preparation/publication, exact refs, no-clobber and crash boundaries."""
from __future__ import annotations

from io import BytesIO
import os
import ctypes
import json
import subprocess
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

from project_harness.errors import HarnessError
from project_harness.local_web_service import LocalWebService
from project_harness.local_web_preparation import (get_preparation, confirm_target, submit_preparation,
    recover_preparation, read_preparation_artifact, open_prepared_folder, _record_path)
from project_harness.local_web_exchange import _load
from project_harness.materialization import check_new_destination, directory_identity, publish_project_directory
from project_harness.serialization import load_data
from project_harness.runtime import next_task, project_status
from project_harness.validation import validate_handoff, validate_project_directory
from tests.test_ph_lw_07_approvals import ApprovalFixture
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_05_import import archive


class PreparationFixture(ApprovalFixture):
    def setUp(self):
        super().setUp()
        self.service.projects_directory = Path(self.temp.name) / 'Новые проекты с пробелами'

    def approved(self, documents=None):
        if documents:
            self.upload(documents)
        self.fill(); self.actor()
        for _ in range(4): self.decide()

    def target(self, folder='Новый проект 08'):
        view = get_preparation(self.service, self.pid)
        return confirm_target(self.service, self.pid, folder_name=folder, binding_digest=view['binding_digest'],
            expected_fingerprint=view['expected_fingerprint'], confirm=True)

    def start(self, target=None, key='preparation-test-000001'):
        target = target or self.target()
        return submit_preparation(self.service, self.pid, **{k:target[k] for k in
            ('target_id','binding_digest','expected_fingerprint')}, idempotency_key=key)

    def run_preparation(self, target=None):
        op = self.start(target)
        result = self.service.wait_for(op['operation_id'], timeout=120)
        self.assertEqual(result['state'],'SUCCEEDED',result)
        return result


class PreparationTests(PreparationFixture):
    def test_single_md_and_zip_real_directory_validation_one_first_jit(self):
        self.approved([('Документ.md',b'# accepted source')])
        target=self.target(); result=self.run_preparation(target); data=result['result']
        destination=Path(data['destination'])
        self.assertTrue(destination.is_dir()); self.assertEqual(data['initial_validation'],dict(directory='PASS',zip='PASS',project='PASS'))
        self.assertEqual(validate_handoff(destination)['status'],'PASS')
        self.assertEqual(validate_project_directory(destination)['status'],'PASS')
        before=byte_snapshot(destination)
        current=project_status(destination)
        for _ in range(2):
            outcome=next_task(destination)
            self.assertEqual(outcome['run_ref'],data['first_run_ref'])
            self.assertEqual(outcome['task_ref'],data['first_task_ref'])
        self.assertEqual(current['active_run'],project_status(destination)['active_run'])
        self.assertEqual(before,byte_snapshot(destination))
        self.assertEqual(len(list((destination/'.harness/prompts/BUNDLES_BY_RUN').glob('*.md'))),1)
        self.assertEqual(len(list((destination/'.harness/runtime/RUN_PLANS').glob('*.yaml'))),1)
        for path in (destination/'.harness/tasks').rglob('*.yaml'):
            task=load_data(path).get('task')
            if task:self.assertEqual(task['implementation_stage'],'PROTOTYPE')
        prompt=read_preparation_artifact(self.service,self.pid,result['operation_id'],prompt=True)
        self.assertIn(data['first_task_ref'].encode(),prompt)
        with zipfile.ZipFile(BytesIO(self.service.read_handoff_artifact(self.pid,result['operation_id']))) as zf:
            self.assertIsNone(zf.testzip()); names=zf.namelist()
            for private in ('owner.json','.local-web-approvals','exchange/','auth','intake_requests','operations/'):
                self.assertFalse(any(private in n for n in names),private)
        self.assertEqual(self.start(target)['operation_id'],result['operation_id'])
        self.assertEqual(self.start(target,key='another-accepted-key-0001')['operation_id'],result['operation_id'])
        self.assertEqual(len([x for x in self.service.list_projects() if x['kind']=='project']),1)

    def test_zip_with_unicode_subdirectories(self):
        self.approved([('Пакет.zip',archive([('Документы/Требования.md',b'# request'),('skip.png',b'PNG')]))])
        result=self.run_preparation()
        self.assertEqual(result['result']['current_validation'],'PASS')
        self.assertEqual(len(self.service.list_sources(self.pid)['documents']),1)

    def test_missing_approval_readonly_get_and_no_target(self):
        self.fill(); self.actor()
        for _ in range(3): self.decide()
        before=byte_snapshot(Path(self.temp.name)); view=get_preparation(self.service,self.pid)
        self.assertFalse(view['ready'])
        with self.assertRaises(HarnessError): self.target()
        self.assertEqual(before,byte_snapshot(Path(self.temp.name)))

    def test_existing_destination_sentinel_and_empty_folder_are_unchanged(self):
        self.approved(); parent=self.service.projects_directory; parent.mkdir()
        for folder in ('existing','empty'):
            path=parent/folder; path.mkdir()
            if folder=='existing': (path/'sentinel.bin').write_bytes(bytes(range(256)))
            before=byte_snapshot(Path(self.temp.name))
            with self.assertRaises(HarnessError): self.target(folder)
            self.assertEqual(before,byte_snapshot(Path(self.temp.name)))

    def test_invalid_names_paths_and_unknown_targets_reject(self):
        self.approved()
        for name in ('../x','x/y','C:\\temp','NUL','abc:stream','x.','x ','\\\\server\\share','.harness','x\x00y'):
            with self.subTest(name=name):
                before=byte_snapshot(Path(self.temp.name))
                with self.assertRaises(HarnessError): self.target(name)
                self.assertEqual(before,byte_snapshot(Path(self.temp.name)))
        with self.assertRaises(HarnessError):
            submit_preparation(self.service,self.pid,target_id='../evil',binding_digest='bad',
                expected_fingerprint='bad',idempotency_key='unknown-target-00001')

    def test_stale_sources_and_build_fail_before_compile(self):
        self.approved([('one.md',b'# original')]); target=self.target()
        source=next((self.root/'sources').rglob('*.md')); source.write_bytes(b'# changed')
        before=byte_snapshot(Path(self.temp.name))
        with patch('project_harness.local_web_preparation.prepare_handoff') as compiler:
            with self.assertRaises(HarnessError): self.start(target)
            compiler.assert_not_called()
        self.assertEqual(before,byte_snapshot(Path(self.temp.name)))

    def test_target_collision_after_confirmation_before_worker_preserves_user_files(self):
        self.approved(); target=self.target(); dest=Path(target['destination']);dest.mkdir()
        (dest/'sentinel').write_bytes(b'keep')
        before=byte_snapshot(Path(self.temp.name))
        with self.assertRaises(HarnessError): self.start(target)
        self.assertEqual(before,byte_snapshot(Path(self.temp.name)))

    def test_different_target_stale_fingerprint_cross_project_and_build_binding(self):
        self.approved();first=self.target('first');second=self.target('second')
        other=self.service.create_provisional_intake(project_name='other',no_documentation=True,
            idempotency_key='other-target-owner-001')['project_id']
        args={k:first[k] for k in ('target_id','binding_digest','expected_fingerprint')}
        with self.assertRaises(HarnessError):submit_preparation(self.service,other,**args,idempotency_key='other-target-start-001')
        with self.assertRaises(HarnessError):self.start({**first,'expected_fingerprint':'sha256:'+'0'*64})
        from project_harness import local_web_preparation as prep
        binding=prep._binding(self.service,self.pid)
        with patch.object(prep,'_binding',return_value={**binding,'engine_build_digest':'sha256:'+'f'*64}):
            with self.assertRaises(HarnessError):self.start(first)
        with patch.object(prep,'_checkpoint',side_effect=lambda n:(_ for _ in ()).throw(OSError('pause')) if n=='before_compile' else None):
            op=self.start(first);self.service.wait_for(op['operation_id'],timeout=30)
        with self.assertRaises(HarnessError):self.start(second)

    def test_partial_compile_explicit_retry_uses_new_staging_and_preserves_partial(self):
        self.approved();target=self.target()
        def partial(root,output,keep_directory):
            keep_directory.mkdir();(keep_directory/'partial-sentinel').write_bytes(b'preserve')
            raise OSError('simulated interrupted compiler write')
        with patch('project_harness.local_web_preparation.prepare_handoff',side_effect=partial):
            op=self.start(target);blocked=self.service.wait_for(op['operation_id'],timeout=30)
        self.assertEqual(blocked['state'],'BLOCKED')
        old=_load(_record_path(self.service,self.pid));sentinel=Path(old['staging'])/'project/partial-sentinel'
        result=recover_preparation(self.service,self.pid,confirm=True)
        self.assertEqual(result['state'],'SUCCEEDED')
        new=_load(_record_path(self.service,self.pid))
        self.assertNotEqual(old['staging'],new['staging']);self.assertEqual(sentinel.read_bytes(),b'preserve')
        self.assertEqual(new['abandoned_staging'],[old['staging']])

    def test_faults_recover_without_duplicate_compile_or_first_run(self):
        # Independent public flows per boundary, no manufactured core state.
        self.approved()
        target=self.target()
        with patch('project_harness.local_web_preparation._checkpoint',side_effect=lambda n:
                (_ for _ in ()).throw(OSError('fixture interruption')) if n=='after_rename' else None):
            op=self.start(target); blocked=self.service.wait_for(op['operation_id'],timeout=120)
        self.assertEqual(blocked['state'],'BLOCKED')
        record=_load(_record_path(self.service,self.pid));dest=Path(record['destination'])
        self.assertTrue(dest.exists());before=byte_snapshot(dest)
        self.service.close();self.service=LocalWebService(self.app,projects_directory=dest.parent)
        with patch('project_harness.local_web_preparation.prepare_handoff',side_effect=AssertionError('duplicate compile')):
            result=recover_preparation(self.service,self.pid,confirm=True)
        self.assertEqual(result['state'],'SUCCEEDED');self.assertEqual(before,byte_snapshot(dest))
        self.assertEqual(recover_preparation(self.service,self.pid,confirm=True)['result'],result['result'])
        self.assertEqual(len([x for x in self.service.list_projects() if x['kind']=='project']),1)

    def test_mutable_validation_does_not_require_initial_manifest_after_product_edit(self):
        self.approved();op=self.run_preparation();dest=Path(op['result']['destination'])
        (dest/'product-note.txt').write_text('ordinary product change','utf-8')
        self.assertEqual(validate_project_directory(dest)['status'],'PASS')
        self.assertNotEqual(validate_handoff(dest)['status'],'PASS')
        with patch('project_harness.materialization.validate_handoff',side_effect=AssertionError('initial validator after publication')):
            recovered=recover_preparation(self.service,self.pid,confirm=True)
            self.assertEqual(recovered['state'],'SUCCEEDED')

    def test_registered_open_folder_and_artifact_tamper(self):
        self.approved();op=self.run_preparation()
        with patch('os.startfile') as opening:
            self.assertEqual(open_prepared_folder(self.service,self.pid,confirm=True)['status'],'OPEN_REQUESTED')
            opening.assert_called_once_with(op['result']['destination'],'explore')
        record=_load(_record_path(self.service,self.pid));(Path(record['staging'])/'handoff.zip').write_bytes(b'tamper')
        with self.assertRaises(HarnessError): self.service.read_handoff_artifact(self.pid,op['operation_id'])

    def test_real_windows_locked_directory_handle_and_retry(self):
        self.approved();target=self.target();handle=None
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_void_p]
        api.CreateFileW.restype=ctypes.c_void_p
        api.CloseHandle.argtypes=[ctypes.c_void_p]
        def hold(name):
            nonlocal handle
            if name=='before_rename' and handle is None:
                record=_load(_record_path(self.service,self.pid))
                handle=api.CreateFileW(str(Path(record['staging'])/'project'),0x80000000,1,None,3,0x02000000,None)
                self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
        try:
            with patch('project_harness.local_web_preparation._checkpoint',side_effect=hold):
                op=self.start(target);blocked=self.service.wait_for(op['operation_id'],timeout=120)
            self.assertEqual(blocked['state'],'BLOCKED',blocked)
            self.assertFalse(Path(target['destination']).exists())
        finally:
            if handle is not None:api.CloseHandle(handle)
        result=recover_preparation(self.service,self.pid,confirm=True)
        self.assertEqual(result['state'],'SUCCEEDED')

    def test_race_at_rename_never_clobbers_sentinel(self):
        self.approved();target=self.target();dest=Path(target['destination'])
        def collide(name):
            if name=='before_rename':dest.mkdir();(dest/'sentinel').write_bytes(b'keep bytes')
        with patch('project_harness.local_web_preparation._checkpoint',side_effect=collide):
            op=self.start(target);blocked=self.service.wait_for(op['operation_id'],timeout=120)
        self.assertEqual(blocked['state'],'BLOCKED');self.assertEqual((dest/'sentinel').read_bytes(),b'keep bytes')
        with self.assertRaises(HarnessError):recover_preparation(self.service,self.pid,confirm=True)
        self.assertEqual((dest/'sentinel').read_bytes(),b'keep bytes')

    def test_output_collision_is_never_sent_to_destructive_compiler(self):
        self.approved();target=self.target()
        with patch('project_harness.local_web_preparation._checkpoint',side_effect=lambda n:
                (_ for _ in ()).throw(OSError('before compile')) if n=='before_compile' else None):
            op=self.start(target);self.service.wait_for(op['operation_id'],timeout=120)
        record=_load(_record_path(self.service,self.pid));sentinel=Path(record['staging'])/'handoff.zip';sentinel.write_bytes(b'foreign output')
        with patch('project_harness.local_web_preparation.prepare_handoff') as compiler:
            with self.assertRaises(HarnessError):recover_preparation(self.service,self.pid,confirm=True)
            compiler.assert_not_called()
        self.assertEqual(sentinel.read_bytes(),b'foreign output')

    def test_readonly_root_and_junction_rejected_before_mutation(self):
        self.approved();parent=self.service.projects_directory;parent.mkdir()
        try:
            os.chmod(parent,0o444)
            with self.assertRaises(HarnessError):self.target()
        finally:os.chmod(parent,0o777)
        real=Path(self.temp.name)/'real';real.mkdir();junction=parent/'link'
        result=subprocess.run(['cmd.exe','/c','mklink','/J',str(junction),str(real)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        try:
            before=byte_snapshot(real)
            with self.assertRaises(HarnessError):check_new_destination(junction/'new')
            self.assertEqual(before,byte_snapshot(real))
        finally:
            self.assertTrue(junction.is_junction());self.assertTrue(junction.is_relative_to(Path(self.temp.name)))
            junction.rmdir()


class PreparationProcessCrashTests(PreparationFixture):
    def test_real_process_exit_after_compile_rename_catalog(self):
        self.approved();target=self.target()
        self.service.close()
        # A separate worker dies without exception cleanup. Parent never edits
        # canonical state or fabricates a successful operation receipt.
        script='''import json,os,sys
from pathlib import Path
from project_harness.local_web_service import LocalWebService
from project_harness import local_web_preparation as p
data=json.loads(sys.argv[1]);service=LocalWebService(Path(data['app']),projects_directory=Path(data['parent']))
p._checkpoint=lambda name:os._exit(91) if name==data['boundary'] else None
op=p.submit_preparation(service,data['pid'],**data['request'])
service.wait_for(op['operation_id'],timeout=120)
raise SystemExit(99)
'''
        # Each crash advances the SAME durable operation; first through start,
        # then explicit recovery, preserving one compiler result and one Run.
        for index,boundary in enumerate(('after_compile','after_rename','after_catalog')):
            code=script if index==0 else script.replace("op=p.submit_preparation(service,data['pid'],**data['request'])\nservice.wait_for(op['operation_id'],timeout=120)","p.recover_preparation(service,data['pid'],confirm=True)")
            data={'app':str(self.app),'parent':str(self.service.projects_directory),'pid':self.pid,'boundary':boundary,
                'request':{**{k:target[k] for k in ('target_id','binding_digest','expected_fingerprint')},'idempotency_key':'crash-native-process-001'}}
            result=subprocess.run([sys.executable,'-B','-c',code,json.dumps(data)],capture_output=True,timeout=180)
            self.assertEqual(result.returncode,91,result.stderr.decode('utf-8',errors='replace'))
        self.service=LocalWebService(self.app,projects_directory=Path(data['parent']))
        with patch('project_harness.local_web_preparation.prepare_handoff',side_effect=AssertionError('duplicate compiler')):
            result=recover_preparation(self.service,self.pid,confirm=True)
        self.assertEqual(result['state'],'SUCCEEDED')
        self.assertEqual(len([r for r in self.service.list_projects() if r['kind']=='project']),1)


def boundary_case(boundary):
    def test(self):
        self.approved();target=self.target()
        with patch('project_harness.local_web_preparation._checkpoint',side_effect=lambda n:
                (_ for _ in ()).throw(OSError('fixture '+boundary)) if n==boundary else None):
            op=self.start(target);blocked=self.service.wait_for(op['operation_id'],timeout=120)
        self.assertEqual(blocked['state'],'BLOCKED',blocked)
        result=recover_preparation(self.service,self.pid,confirm=True)
        self.assertEqual(result['state'],'SUCCEEDED')
        self.assertEqual(result['result']['current_validation'],'PASS')
        dest=Path(result['result']['destination'])
        self.assertEqual(project_status(dest)['active_run']['run_ref'],result['result']['first_run_ref'])
    return test


class PreparationFaultTests(PreparationFixture):
    pass


for boundary in ('before_compile','after_compile','before_validation','after_validation','before_rename',
                 'before_catalog','after_catalog','after_result'):
    setattr(PreparationFaultTests,'test_recover_'+boundary,boundary_case(boundary))


@unittest.skipUnless(os.name == 'nt', 'Native Windows sharing semantics required')
class PreparationJournalTests(unittest.TestCase):
    def test_transient_get_read_handle_does_not_interrupt_atomic_phase_write(self):
        import tempfile, threading
        from project_harness.local_web_preparation import _save
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receipt.json';_save(path,{'phase':'INTENT'})
            handle=path.open('rb')
            timer=threading.Timer(0.15,handle.close);timer.start()
            try:_save(path,{'phase':'STAGING'})
            finally:timer.join();handle.close()
            self.assertEqual(_load(path)['phase'],'STAGING')
            self.assertEqual({p.name for p in path.parent.iterdir()},{'receipt.json'})

    def test_persistent_read_handle_preserves_old_phase_and_requires_recovery(self):
        import tempfile,time
        from project_harness.local_web_preparation import _save
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receipt.json';_save(path,{'phase':'INTENT'})
            before=path.read_bytes();started=time.monotonic()
            with path.open('rb'):
                with self.assertRaises(PermissionError):_save(path,{'phase':'STAGING'})
            self.assertLess(time.monotonic()-started,5)
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual({p.name for p in path.parent.iterdir()},{'receipt.json'})


if __name__=='__main__':unittest.main()

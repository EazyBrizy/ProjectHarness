"""Real Windows preparation beyond MAX_PATH, without host configuration changes."""
import ctypes
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from tests.test_ph_lw_08_preparation import PreparationFixture
from project_harness.validation import validate_handoff,validate_project_directory
from project_harness.local_web_preparation import read_preparation_artifact
from project_harness.materialization import handoff_tree_digest

def setting():
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\FileSystem') as key:
        return winreg.QueryValueEx(key,'LongPathsEnabled')[0]

@unittest.skipUnless(os.name=='nt','Native Windows required')
class LongPathPreparationTests(PreparationFixture):
    def setUp(self):
        super().setUp()
        self.projects=Path(self.temp.name)/('Длинный-'+('x'*113))
        self.service.projects_directory=self.projects
        assert self.projects.is_absolute() and self.projects.is_relative_to(Path(self.temp.name))
        self.addCleanup(lambda:shutil.rmtree(Path('\\\\?\\'+str(self.projects)),ignore_errors=True))

    def test_long_preparation_publication_validation_and_first_jit(self):
        before=setting();self.assertFalse(ctypes.windll.shell32.IsUserAnAdmin())
        self.approved();target=self.target();op=self.run_preparation(target)
        root=Path(op['result']['destination'])
        leaf=root/'.harness/engine/project_harness/resources/schemas/maintenance_cancel_approval.schema.json'
        self.assertGreater(len(str(leaf)),260)
        self.assertEqual(validate_handoff(root)['status'],'PASS')
        self.assertEqual(validate_project_directory(root)['status'],'PASS')
        self.assertIn(op['result']['first_task_ref'].encode(),read_preparation_artifact(self.service,self.pid,op['operation_id'],prompt=True))
        from project_harness.manual_tasks import task_console
        self.assertIn(op['result']['first_task_ref'],task_console(root)['prompt_text'])
        self.assertNotIn('\\\\?\\',str(op))
        before_reads=handoff_tree_digest(root)
        self.assertEqual(self.start(target)['operation_id'],op['operation_id'])
        self.service.get_status(op['result']['published_project_id'])
        self.assertEqual(handoff_tree_digest(root),before_reads)
        io_leaf=Path('\\\\?\\'+str(leaf));original=io_leaf.read_bytes()
        try:
            io_leaf.write_bytes(original+b'\n ')
            self.assertEqual(validate_handoff(root)['status'],'FAIL')
        finally:io_leaf.write_bytes(original)
        self.assertEqual(setting(),before)

    def test_long_publication_recovery_never_reexecutes_compiler(self):
        from project_harness.local_web_preparation import recover_preparation
        self.approved();target=self.target()
        def interrupt(phase):
            if phase=='after_rename':raise OSError('test interruption after native publication')
        with patch('project_harness.local_web_preparation._checkpoint',side_effect=interrupt):
            op=self.start(target);op=self.service.wait_for(op['operation_id'],timeout=120)
        self.assertEqual(op['state'],'BLOCKED')
        root=Path(target['destination']);before=handoff_tree_digest(root)
        with patch('project_harness.local_web_preparation.prepare_handoff',side_effect=AssertionError('compiler replay forbidden')):
            result=recover_preparation(self.service,self.pid,confirm=True)
        self.assertEqual(result['state'],'SUCCEEDED')
        self.assertEqual(handoff_tree_digest(root),before)

    def test_internal_io_does_not_admit_device_unc_or_stream_input(self):
        from project_harness.platform_fs import _native_io_path,ensure_native_path
        from project_harness.errors import HarnessError
        for path in (r'\\?\C:\Windows',r'\\.\C:\Windows',r'\\server\share',r'C:\safe\file:stream'):
            with self.subTest(path=path):
                with self.assertRaises(HarnessError):_native_io_path(Path(path))
                with self.assertRaises(HarnessError):ensure_native_path(Path(path))

if __name__=='__main__':unittest.main()

"""PH-LW-02: portable negative controls + real OS integration on running host.

Linux results here are *not* evidence that native Windows/NTFS passed.
Windows-only checks are marked as SKIP outside Windows.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

import project_harness
from project_harness import runtime
from project_harness.errors import SafetyViolation, ValidationFailure
from project_harness.platform_fs import (assert_windows_root_form, assert_windows_tree,
    ensure_native_path, ensure_writable_target, safe_relative, stage_project_lock)
from project_harness.stage_transactions import (apply_stage_transaction, digest_value,
    recover_stage_transactions, validate_stage_transaction_journals)
from project_harness.serialization import atomic_write_text, load_data, write_data
from project_harness.safety import safe_extract_zip
from project_harness.intake import check_intake, start_intake
from project_harness.runtime import (complete_current, executor_doctor, execute_current,
    next_task, verify_current)
from project_harness.validation import validate_handoff, validate_project_directory
from tests.test_engine import prepare_demo, implement_first_task, write_agent_result


class WindowsCoreBoundaryTests(unittest.TestCase):
    def test_01_no_fcntl_during_package_cli_manual_import(self):
        # Do not merely patch cli.py; force the complete public import graph.
        code = ("import sys; sys.modules['fcntl'] = None; "
                "import project_harness; from project_harness import runtime; "
                "import project_harness.cli, project_harness.intake, project_harness.compiler; "
                "import project_harness.validation, project_harness.stage_transactions; "
                "print('MANUAL_IMPORT_PASS')")
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
               'PYTHONPATH': os.pathsep.join((str(Path(__file__).resolve().parents[1] / 'src'),
                                               str(Path(__file__).resolve().parents[1])))}
        result = subprocess.run([sys.executable, '-B', '-c', code], env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('MANUAL_IMPORT_PASS', result.stdout)

    def test_02_unsupported_host_fails_closed_not_host_exec(self):
        with mock.patch.object(runtime, '_automatic_supported_on_host', return_value=False), \
             mock.patch.object(runtime.subprocess, 'Popen', side_effect=AssertionError('host agent')) as popen:
            doctor = executor_doctor(Path('not-even-a-project'))
            result = execute_current(Path('not-even-a-project'))
        for item in (doctor, result):
            self.assertEqual(item['status'], 'BLOCKED')
            self.assertEqual(item['reason_code'], 'SANDBOX_UNAVAILABLE')
            self.assertEqual(item['isolation_verified'], False)
        popen.assert_not_called()

    def test_03_windows_drive_device_unc_root_forms(self):
        for raw in (r'C:relative', r'\\server\share\project',
                    r'\\?\C:\hidden', r'\\.\C:\hidden', r'\rooted',
                    r'//host/share', r'C:'):
            with self.subTest(raw=raw), self.assertRaises(SafetyViolation):
                assert_windows_root_form(raw)
        assert_windows_root_form('C:\\Папка пользователя\\Документы с пробелом')

    def test_04_windows_relative_drive_ads_device_and_escape(self):
        unsafe = ('C:foo', r'C:\outside', r'\\server\share\x', r'\\?\C:\x',
                  '../outside', r'good\..\outside', '/outside',
                  'AUX.txt', 'dir/CON', 'file.txt:stream', 'bad?.md',
                  'file. ', 'file.', 'dir//file')
        for item in unsafe:
            with self.subTest(item=item), self.assertRaises(SafetyViolation):
                safe_relative(item, field='test', windows=True)
        self.assertEqual(safe_relative('папка с пробелом/тест.md', field='test', windows=True).as_posix(),
                         'папка с пробелом/тест.md')

    def test_05_colliding_tree_rejected_without_rewriting_case(self):
        if os.name == 'nt':
            self.skipTest('NTFS casefold aliases require a case-sensitive directory; ZIP test is cross-platform')
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root / 'Test.txt').write_text('A', encoding='utf-8')
            (root / 'test.TXT').write_text('B', encoding='utf-8')
            with self.assertRaisesRegex(SafetyViolation, 'WINDOWS_CASE_COLLISION'):
                assert_windows_tree(root)
            self.assertEqual((root / 'Test.txt').read_text('utf-8'), 'A')
            self.assertEqual((root / 'test.TXT').read_text('utf-8'), 'B')

    def test_06_unsafe_zip_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as base:
            parent = Path(base)
            for entries in ({'A.md': '1', 'a.MD': '2'},
                            {'dir/CON.txt': 'x'},
                            {'safe.md': 'a', '../escape.txt': 'b'},
                            {'C:outside.md': 'x'}):
                source = parent / 'bad.zip'
                with zipfile.ZipFile(source, 'w') as z:
                    for name, body in entries.items():
                        z.writestr(name, body)
                dest = parent / 'out'
                self.assertFalse(dest.exists())
                with self.assertRaises(SafetyViolation):
                    safe_extract_zip(source, dest)
                self.assertFalse(dest.exists(), 'invalid archive must not create destination')

    def test_06b_unsafe_source_zip_rejected_before_intake_workspace_writes(self):
        with tempfile.TemporaryDirectory() as base:
            parent = Path(base)
            source = parent / 'unsafe.zip'
            with zipfile.ZipFile(source, 'w') as zf:
                zf.writestr('safe.md', 'okay')
                zf.writestr('CON.txt', 'unsafe on NTFS')
            workspace = parent / 'intake target'
            with self.assertRaises(SafetyViolation):
                start_intake(workspace, project_name='Тест', mode='GREENFIELD', sources=[source])
            self.assertFalse(workspace.exists())

    def test_07_utf8_crlf_and_atomic_temp_close(self):
        with tempfile.TemporaryDirectory() as base:
            path = Path(base) / 'Каталог с пробелом' / 'файл.yaml'
            path.parent.mkdir()
            path.write_bytes(b'{"value":"' + 'Юникод'.encode('utf-8') + b'"}\r\n')
            before = path.read_bytes()
            self.assertEqual(load_data(path), {'value': 'Юникод'})
            self.assertEqual(path.read_bytes(), before, 'read must not normalize CRLF')
            atomic_write_text(path, '{"value":"изменено"}\n')
            self.assertEqual(load_data(path), {'value': 'изменено'})
            self.assertNotIn(b'\r\n', path.read_bytes())
            self.assertEqual(list(path.parent.glob('.файл.yaml.*')), [])

    def test_08_permission_or_busy_replace_propagates_without_writes(self):
        with tempfile.TemporaryDirectory() as base:
            path = Path(base) / 'record.yaml'
            path.write_bytes(b'original\n')
            with mock.patch('project_harness.serialization.os.replace', side_effect=PermissionError('busy')):
                with self.assertRaises(PermissionError):
                    atomic_write_text(path, 'unaccepted\n')
            self.assertEqual(path.read_bytes(), b'original\n')
            self.assertFalse(list(path.parent.glob('.record.yaml.*')))

    def test_09_second_process_cannot_bypass_real_os_stage_lock(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base) / 'project'
            root.mkdir()
            src = ('from pathlib import Path\n'
                   'import sys, time\n'
                   'from project_harness.platform_fs import stage_project_lock\n'
                   'with stage_project_lock(Path(sys.argv[1])):\n'
                   ' print("LOCKED", flush=True)\n'
                   ' time.sleep(4)\n')
            env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                   'PYTHONPATH': os.pathsep.join((str(Path(__file__).resolve().parents[1] / 'src'),
                                                  str(Path(__file__).resolve().parents[1])))}
            child = subprocess.Popen([sys.executable, '-B', '-c', src, str(root)],
                                     env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(), 'LOCKED', child.stderr.read() if child.poll() else '')
                with self.assertRaisesRegex(ValidationFailure, 'STAGE_TRANSACTION_LOCKED'):
                    with stage_project_lock(root):
                        self.fail('Second process unexpectedly acquired Stage lock')
                with self.assertRaisesRegex(ValidationFailure, 'STAGE_TRANSACTION_LOCKED'):
                    apply_stage_transaction(root, {Path('first.yaml'): {'test': 1}},
                        transaction_id='TX-LW02-CONTENTION', operation_kind='TEST',
                        request_digest=digest_value({'request': 1}), result={'status': 'PASS'})
                self.assertFalse((root / 'first.yaml').exists())
            finally:
                child.terminate()
                child.communicate(timeout=10)

    def test_10_stage_fault_midwrite_reconciles_all_old(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            p1, p2 = root / 'one.yaml', root / 'two.yaml'
            write_data(p1, {'old': 1})
            write_data(p2, {'old': 2})
            old1, old2 = p1.read_bytes(), p2.read_bytes()
            counter = 0
            def fault(src: Path, target: Path) -> None:
                nonlocal counter
                counter += 1
                if counter == 2:
                    raise PermissionError('Windows busy target / sharing denial')
                os.replace(src, target)
            with self.assertRaises(PermissionError):
                apply_stage_transaction(root, {Path('one.yaml'): {'new': 1}, Path('two.yaml'): {'new': 2}},
                    transaction_id='TX-LW02-REPAIR', operation_kind='TEST',
                    request_digest=digest_value({'request': 2}), result={'status': 'PASS'},
                    replace_canonical=fault)
            self.assertEqual((p1.read_bytes(), p2.read_bytes()), (old1, old2))
            self.assertEqual(recover_stage_transactions(root)['status'], 'PASS')
            journal = load_data(root / '.harness/stages/TRANSACTIONS/TX-LW02-REPAIR/TRANSACTION.yaml')['stage_transaction']
            self.assertEqual(journal['status'], 'ROLLED_BACK')

    def test_11_manual_greenfield_full_api_through_complete(self):
        with tempfile.TemporaryDirectory(prefix='ph-lw02-') as directory:
            base = Path(directory) / 'Проект с пробелом'
            workspace, archive, root = prepare_demo(base)
            checked = check_intake(workspace)
            self.assertEqual(checked['status'], 'READY_FOR_HANDOFF')
            self.assertEqual(validate_handoff(archive)['status'], 'PASS')
            self.assertEqual(validate_project_directory(root)['status'], 'PASS')
            ready = next_task(root)
            self.assertEqual(ready['status'], 'READY_FOR_CODEX')
            self.assertTrue(ready['run_ref'])
            implement_first_task(root)
            verification = verify_current(root, allow_command_execution=True)
            self.assertEqual(verification['status'], 'PASS', verification)
            completed = complete_current(root, write_agent_result(root, verification, 'PH-LW-02 manual verified'))
            self.assertEqual(completed['project_status'], 'ACTIVE')
            self.assertEqual(validate_project_directory(root)['status'], 'PASS')

    @unittest.skipUnless(os.name == 'nt', 'Real native Windows/NTFS semantics not executable on Linux')
    def test_12_native_windows_disk_root_and_read_only(self):
        with tempfile.TemporaryDirectory(prefix='lw02-Проверка пробелы-') as base:
            root = Path(base)
            ensure_native_path(root, tree=True)
            target = root / 'проверка.txt'
            target.write_text('original', encoding='utf-8')
            target.chmod(0o444)
            try:
                with self.assertRaisesRegex(ValidationFailure, 'WINDOWS_READ_ONLY_TARGET'):
                    ensure_writable_target(target)
            finally:
                target.chmod(0o666)
            self.assertEqual(target.read_text('utf-8'), 'original')

    @unittest.skipUnless(os.name == 'nt', 'Only real Windows can demonstrate sharing-denied replace')
    def test_13_native_windows_open_handle_replace_denial(self):
        with tempfile.TemporaryDirectory(prefix='lw02-handle-') as base:
            old = Path(base) / 'old.txt'
            replacement = Path(base) / 'new.txt'
            old.write_text('old', encoding='utf-8')
            replacement.write_text('new', encoding='utf-8')
            with old.open('rb') as handle:
                with self.assertRaises((PermissionError, OSError)):
                    os.replace(replacement, old)
                self.assertEqual(handle.read(), b'old')
            self.assertEqual(old.read_text('utf-8'), 'old')
            self.assertEqual(replacement.read_text('utf-8'), 'new')


if __name__ == '__main__':
    unittest.main()

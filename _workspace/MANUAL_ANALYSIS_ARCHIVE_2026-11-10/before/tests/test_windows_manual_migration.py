"""Native manual migration: no automatic opt-in, real subprocess/crash/handles."""
from __future__ import annotations
import errno
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from project_harness import migration
from project_harness.errors import ValidationFailure
from project_harness.project_input import DEFAULT_EXECUTION_POLICY
from project_harness.runtime import (next_task, verify_current, complete_current,
                                     execute_current, executor_doctor)
from project_harness.serialization import load_data
from project_harness.validation import validate_project_directory
from tests.test_engine import prepare_demo, implement_first_task, write_agent_result
from tests.test_ph_051_10_migration_recovery import downgrade_to_v050


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts}


class ManualMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='manual-migration-')
        self.addCleanup(self.temp.cleanup)
        self.root = prepare_demo(Path(self.temp.name) / 'Проект с пробелами')[2]
        self.history = downgrade_to_v050(self.root)

    def assert_history(self):
        for relative, data in self.history.items():
            self.assertEqual((self.root / relative).read_bytes(), data, relative)

    def assert_no_storage(self):
        self.assertEqual(list(self.root.parent.glob(f'.{self.root.name}.ph05110-*')), [])

    def test_cli_migration_replay_and_manual_verified_completion(self):
        command = [sys.executable, '-c', 'from project_harness.cli import main; raise SystemExit(main())',
                   'migrate-project', '--project', str(self.root)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout)['status'], 'MIGRATED')
        self.assert_history()
        before = snapshot(self.root)
        self.assertEqual(migration.migrate_project(self.root)['status'], 'NO_ACTION')
        self.assertEqual(snapshot(self.root), before)
        lock = load_data(self.root / '.harness/config/PROJECT_LOCK.yaml')['project_lock']
        self.assertEqual(lock['execution'], DEFAULT_EXECUTION_POLICY)
        self.assertEqual(next_task(self.root)['status'], 'READY_FOR_CODEX')
        implement_first_task(self.root)
        verified = verify_current(self.root, allow_command_execution=True)
        self.assertEqual(verified['status'], 'PASS', verified)
        completed = complete_current(self.root, write_agent_result(self.root, verified))
        self.assertEqual(completed['project_status'], 'ACTIVE')
        self.assertEqual(validate_project_directory(self.root)['status'], 'PASS')
        self.assert_no_storage()

    def test_staged_flush_failure_preserves_every_canonical_byte_and_no_journal(self):
        before = snapshot(self.root)
        def broken(fd):
            raise OSError(errno.EIO, 'injected staged flush failure')
        original_sync = migration._migration_sync_staged_tree
        def stage_failure(root):
            with mock.patch.object(migration.os, 'fsync', side_effect=broken):
                original_sync(root)
        with mock.patch.object(migration, '_migration_sync_staged_tree', side_effect=stage_failure):
            with self.assertRaises(OSError):
                migration.migrate_project(self.root)
        self.assertEqual(snapshot(self.root), before)
        self.assert_no_storage()

    def test_second_rename_failure_rolls_back_and_retry_preserves_history(self):
        before = snapshot(self.root)
        original = migration.os.replace
        def denied(src, dst):
            if Path(dst) == self.root and '.ph05110-staged-' in Path(src).name:
                raise PermissionError('injected sharing denial on second rename')
            return original(src, dst)
        with mock.patch.object(migration.os, 'replace', side_effect=denied):
            with self.assertRaises(PermissionError):
                migration.migrate_project(self.root)
        self.assertEqual(snapshot(self.root), before)
        self.assert_no_storage()
        self.assertEqual(migration.migrate_project(self.root)['status'], 'MIGRATED')
        self.assert_history()

    def test_partial_copy_failure_preserves_source_and_removes_owned_stage(self):
        before = snapshot(self.root)
        original = migration.shutil.copy2
        calls = 0
        def interrupted(src, dst):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise PermissionError('source sharing denial during copy')
            return original(src, dst)
        with mock.patch.object(migration.shutil, 'copy2', side_effect=interrupted):
            with self.assertRaises(migration.shutil.Error):
                migration.migrate_project(self.root)
        self.assertGreater(calls, 3)
        self.assertEqual(snapshot(self.root), before)
        self.assert_no_storage()

    def test_real_process_exit_at_both_swap_boundaries_recovers_via_public_api(self):
        for boundary in ('AFTER_OLD_RENAME', 'AFTER_NEW_RENAME'):
            with self.subTest(boundary=boundary):
                if boundary == 'AFTER_NEW_RENAME':
                    self.root = prepare_demo(Path(self.temp.name) / 'Второй проект')[2]
                    self.history = downgrade_to_v050(self.root)
                code = ('import os,sys; from pathlib import Path; from project_harness import migration; '
                        'migration._v051_migration_fault=lambda phase: os._exit(75) if phase==sys.argv[2] else None; '
                        'migration.migrate_project(Path(sys.argv[1]))')
                child = subprocess.run([sys.executable, '-c', code, str(self.root), boundary],
                                       capture_output=True, timeout=120)
                self.assertEqual(child.returncode, 75, child.stderr)
                self.assertTrue(migration._migration_marker(self.root).is_file())
                recovered = migration.migrate_project(self.root)
                self.assertIn(recovered['status'], ('MIGRATED', 'NO_ACTION'))
                self.assert_history()
                self.assertEqual(validate_project_directory(self.root)['status'], 'PASS')
                self.assertEqual(next_task(self.root)['status'], 'READY_FOR_CODEX')
                self.assert_no_storage()

    @unittest.skipUnless(os.name == 'nt', 'Native Windows sharing semantics required')
    def test_windows_open_handle_denial_is_read_only_and_retryable(self):
        before = snapshot(self.root)
        with (self.root / '.harness/state/PROJECT_INPUT_ACCEPTED.yaml').open('rb') as held:
            with self.assertRaises(PermissionError):
                migration.migrate_project(self.root)
            self.assertTrue(held.read())
        self.assertEqual(snapshot(self.root), before)
        self.assert_no_storage()
        self.assertEqual(migration.migrate_project(self.root)['status'], 'MIGRATED')

    @unittest.skipUnless(os.name == 'nt', 'Native Windows read-only semantics required')
    def test_readonly_source_refusal_preserves_original_and_cleans_owned_stage(self):
        target = self.root / '.harness/state/PROJECT_INPUT_ACCEPTED.yaml'
        target.chmod(0o444)
        try:
            before = snapshot(self.root)
            with self.assertRaises(PermissionError):
                migration.migrate_project(self.root)
            self.assertEqual(snapshot(self.root), before)
            self.assert_no_storage()
            self.assertTrue(target.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
        finally:
            target.chmod(0o666)

    @unittest.skipUnless(os.name == 'nt', 'Windows automatic refusal boundary required')
    def test_windows_automatic_requests_never_dispatch_or_mutate_manual_project(self):
        migration.migrate_project(self.root)
        before = snapshot(self.root)
        with mock.patch('subprocess.Popen', side_effect=AssertionError('automatic host dispatch')) as spawn:
            for operation in (executor_doctor, execute_current):
                outcome = operation(self.root)
                self.assertEqual(outcome['status'], 'BLOCKED', outcome)
                self.assertEqual(outcome['reason_code'], 'SANDBOX_UNAVAILABLE')
            spawn.assert_not_called()
        self.assertEqual(snapshot(self.root), before)


class MigrationCleanupScopeTests(unittest.TestCase):
    @unittest.skipUnless(os.name == 'nt', 'Native Windows read-only hardlink required')
    def test_cleanup_never_clears_readonly_on_hardlinked_external_file(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            canonical = base / 'project'
            canonical.mkdir()
            storage = base / ('.project.ph05110-staged-' + 'b' * 32)
            storage.mkdir()
            outside = base / 'outside.txt'
            outside.write_bytes(b'original')
            os.link(outside, storage / 'linked.txt')
            outside.chmod(0o444)
            try:
                with self.assertRaises(ValidationFailure):
                    migration._migration_remove_storage(canonical, storage)
                self.assertEqual(outside.read_bytes(), b'original')
                self.assertTrue(outside.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
            finally:
                outside.chmod(0o666)

    def test_cleanup_refuses_unowned_sibling_and_different_parent_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            canonical = base / 'project'
            canonical.mkdir()
            outside = base / 'unrelated'
            elsewhere = base / 'other-parent' / ('.project.ph05110-staged-' + 'a' * 32)
            for target in (outside, elsewhere):
                target.mkdir(parents=True)
                sentinel = target / 'keep.txt'
                sentinel.write_bytes(b'untouched')
                with self.subTest(target=target.name):
                    with self.assertRaises(ValidationFailure):
                        migration._migration_remove_storage(canonical, target)
                    self.assertEqual(sentinel.read_bytes(), b'untouched')


if __name__ == '__main__':
    unittest.main()

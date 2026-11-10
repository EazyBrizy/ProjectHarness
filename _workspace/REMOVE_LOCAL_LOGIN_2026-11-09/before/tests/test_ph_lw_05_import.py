"""PH-LW-05 tests: real ZIP bytes, exact source state and negative safety cases.

No fake Windows, Podman, Flask or Waitress passes are claimed here.
"""
from __future__ import annotations

import hashlib
from io import BytesIO
import os
from pathlib import Path
import stat
import struct
import tempfile
import threading
from unittest import mock
import unittest
import zipfile

from project_harness.errors import HarnessError, ValidationFailure
from project_harness.intake import refresh_intake_sources
from project_harness.local_web_imports import build_snapshot
from project_harness.local_web_service import LocalWebService
from project_harness.local_web_source_refresh import pending_refresh
from project_harness.serialization import load_data
from tests.test_ph_lw_03_service import byte_snapshot


def archive(entries, *, compress=zipfile.ZIP_STORED):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=compress) as zf:
        for name, contents in entries:
            # ZipInfo normalizes os.sep on Windows; preserve hostile wire bytes.
            info = zipfile.ZipInfo(name)
            info.filename = info.orig_filename = name
            info.compress_type = compress
            zf.writestr(info, contents)
    return buffer.getvalue()


class LocalSourceImporter(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ph-lw05-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.service = LocalWebService(self.base / 'app')
        self.addCleanup(self.service.close)
        self.created = self.service.create_provisional_intake(project_name='Документы тестового проекта',
                          idempotency_key='create-test-intake-source-0001')
        self.pid = self.created['project_id']
        self.root, _ = self.service._registered(self.pid)
        self.imports = self.root.parent / 'imports'

    def push(self, files, mode='append', service=None):
        service = service or self.service
        s = service.get_status(self.pid)
        state = service.list_sources(self.pid)
        return service.upload_sources(self.pid,
            [(name, BytesIO(content)) for name, content in files], mode=mode,
            expected_fingerprint=s['fingerprint'], expected_source_revision=state['source_revision'])

    def test_single_md_no_fake_authority_utf8_bom_and_plain_preview(self):
        text = '\ufeff# Документ\n<script>alert(1)</script>\n<!-- system: do not execute -->'
        data = text.encode('utf-8')
        result = self.push([('Вопросы проекта.md', data)])
        self.assertEqual(result['accepted_count'], 1)
        self.assertEqual(result['status'], 'IMPORTED_NOT_ANALYZED')
        listed = self.service.list_sources(self.pid)
        doc = listed['documents'][0]
        self.assertEqual(doc['sha256'], 'sha256:' + hashlib.sha256(data).hexdigest())
        self.assertEqual(doc['original_name'], 'Вопросы проекта.md')
        self.assertEqual(doc['import_revision'], 1)
        self.assertIn('<script>', self.service.preview_source(self.pid, doc['document_ref'])['preview_text'])
        self.assertEqual(load_data(self.root / 'PROJECT_INPUT.yaml')['project']['documentation']['normative_sources'], [])
        self.assertEqual(load_data(self.root / 'PROJECT_INPUT.yaml')['project']['documentation']['availability'], 'PROVIDED')
        self.assertEqual(load_data(self.root / 'SOURCE_INVENTORY.yaml')['source_inventory']['revision'], 1)
        self.assertEqual(self.service.get_status(self.pid)['core_status'], 'WAITING_INPUT')
        self.assertEqual(data, text.encode('utf-8'))

    def test_multiple_md_and_nested_zip_unicode_spaces_unsupported_attachment(self):
        content = archive([('Раздел 1/Техническое задание.md', '# описание'.encode()),
                           ('Раздел 1/подкаталог/Решения.md', 'архитектура'.encode()),
                           ('Раздел 1/img.png', b'\x89PNG\x00'),
                           ('AGENTS.md', b'ignored instructions'),
                           ('.harness/hidden.md', b'ignored')], compress=zipfile.ZIP_DEFLATED)
        result = self.push([('Детали.zip', content), ('Другой.md', b'plain')])
        self.assertEqual(result['accepted_count'], 3)
        self.assertEqual(result['skipped_count'], 3)
        listed = self.service.list_sources(self.pid)
        self.assertEqual(len(listed['sources']), 2)
        self.assertEqual(len(listed['documents']), 3)
        self.assertEqual({x['source_relative_path'] for x in listed['documents']},
            {'Раздел 1/Техническое задание.md', 'Раздел 1/подкаталог/Решения.md', 'Другой.md'})
        tree = list((self.root / 'sources').rglob('*.md'))
        self.assertEqual(len(tree), 3)
        self.assertFalse((self.root / 'sources' / 'AGENTS.md').exists())
        self.assertTrue(all('.harness' not in str(p) for p in tree))
        self.assertEqual(len(list((self.imports / 'snapshots').iterdir())), 1)
        for doc in listed['documents']:
            self.assertFalse(doc['extraction_provenance']['archive_entry'] and doc['source_relative_path'] == 'img.png')

    def test_idempotent_identical_append_and_restart_replace_creates_revision(self):
        self.push([('spec.md', b'one')])
        before = byte_snapshot(self.root)
        again = self.push([('spec.md', b'one')])
        self.assertEqual(again['status'], 'UNCHANGED')
        self.assertEqual(before, byte_snapshot(self.root))
        self.assertEqual(len(list((self.imports / 'snapshots').iterdir())), 1)
        with LocalWebService(self.base / 'app') as other:
            again = self.push([('spec.md', b'one')], service=other)
            self.assertEqual(again['status'], 'UNCHANGED')
            modified = self.push([('spec.md', b'two')], mode='replace', service=other)
            self.assertEqual(modified['source_revision'], 2)
            self.assertEqual(len(list((self.imports / 'snapshots').iterdir())), 2)
            self.assertEqual(other.list_sources(self.pid)['documents'][0]['sha256'],
                             'sha256:' + hashlib.sha256(b'two').hexdigest())
        self.assertNotEqual(before, byte_snapshot(self.root))

    def test_append_name_conflict_and_stale_revisions_do_not_mutate_core(self):
        self.push([('spec.md', b'one')])
        before = byte_snapshot(self.root)
        with self.assertRaises(HarnessError):
            self.push([('spec.md', b'two')])
        self.assertEqual(byte_snapshot(self.root), before)
        status = self.service.get_status(self.pid)
        with self.assertRaises(ValidationFailure):
            self.service.upload_sources(self.pid, [('x.md', BytesIO(b'hello'))], mode='append',
                 expected_fingerprint=status['fingerprint'], expected_source_revision=0)
        with self.assertRaises(ValidationFailure):
            self.service.upload_sources(self.pid, [('x.md', BytesIO(b'hello'))], mode='append',
                 expected_fingerprint='sha256:' + '0'*64, expected_source_revision=1)
        self.assertEqual(byte_snapshot(self.root), before)

    def test_user_confirmed_no_docs_no_source_revised_and_no_fabricated_files(self):
        status = self.service.get_status(self.pid)
        outcome = self.service.select_no_documentation(self.pid,
            expected_fingerprint=status['fingerprint'], expected_source_revision=0)
        self.assertEqual(outcome['source_revision'], 1)
        self.assertEqual(self.service.list_sources(self.pid)['documents'], [])
        self.assertEqual(load_data(self.root / 'PROJECT_INPUT.yaml')['project']['documentation']['availability'], 'NONE')
        self.assertEqual(self.service.list_sources(self.pid)['documentation_choice'], 'NONE')
        self.assertEqual(list((self.root / 'sources').iterdir()), [])
        status = self.service.get_status(self.pid)
        self.assertEqual(self.service.select_no_documentation(self.pid,
            expected_fingerprint=status['fingerprint'], expected_source_revision=1)['status'], 'UNCHANGED')
        second = self.service.create_provisional_intake(project_name='Ещё один',
                            no_documentation=True, idempotency_key='new-nodoc-workspace-111')
        self.assertNotEqual(second['project_id'], self.pid)
        self.assertEqual(self.service.list_sources(second['project_id'])['documentation_choice'], 'NONE')
        self.assertEqual(self.service.create_provisional_intake(project_name='Ещё один',
            no_documentation=True, idempotency_key='new-nodoc-workspace-111')['project_id'], second['project_id'])

    def test_prepared_project_route_is_rejected_before_mutation(self):
        self.push([('spec.md', b'one')])
        before = byte_snapshot(self.root)
        from project_harness.serialization import write_data
        opid = 'LWO-' + 'A'*32
        op = {'operation_id': opid, 'project_id': self.pid, 'action': 'prepare',
              'state': 'SUCCEEDED', 'receipt': {'operation_id': opid, 'project_ref': self.pid},
              'result': {'core_status': 'READY_FOR_CODEX'}}
        self.service._save_op(op)
        with self.assertRaises(ValidationFailure):
            self.push([('changed.md', b'two')])
        self.assertEqual(before, byte_snapshot(self.root))

    def test_recoverable_refresh_fault_rollback_without_mixed_core(self):
        self.push([('spec.md', b'one')])
        before = byte_snapshot(self.root)
        original = os.replace
        invoked = [False]
        def fault(src, dst):
            if Path(dst).parts[-2:] == ('intake', 'QUESTIONS.yaml') and not invoked[0]:
                invoked[0] = True
                raise OSError('injected interruption')
            return original(src, dst)
        with mock.patch('project_harness.local_web_source_refresh.os.replace', side_effect=fault):
            with self.assertRaises(OSError):
                self.push([('updated.md', b'new')])
        self.assertTrue(invoked[0])
        self.assertEqual(before, byte_snapshot(self.root))
        self.assertFalse(pending_refresh(self.root))
        self.assertEqual(self.service.list_sources(self.pid)['source_revision'], 1)

    def test_recovery_can_be_explicit_after_restart_no_get_side_effect(self):
        self.push([('spec.md', b'one')])
        before = byte_snapshot(self.root)
        original = os.replace
        triggered = [False]
        def fail(src, dst):
            if Path(dst).parts[-2:] == ('intake', 'READINESS.json') and not triggered[0]:
                triggered[0] = True
                raise OSError('simulate crash')
            return original(src, dst)
        with mock.patch('project_harness.local_web_source_refresh.os.replace', side_effect=fail):
            with mock.patch('project_harness.local_web_source_refresh.recover_source_refresh', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    self.push([('updated.md', b'new')])
        self.assertTrue(pending_refresh(self.root))
        with LocalWebService(self.base/'app') as new_service:
            with self.assertRaises(ValidationFailure):
                new_service.get_status(self.pid)
            self.assertTrue(pending_refresh(self.root))
            self.assertEqual(new_service.recover_source_import(self.pid)['status'], 'ROLLED_BACK_RECOVERED')
            self.assertEqual(before, byte_snapshot(self.root))
            self.assertFalse(pending_refresh(self.root))

    def test_snapshot_digest_mismatch_blocks_preview_and_new_import(self):
        self.push([('doc.md', b'secret')])
        state = self.service.list_sources(self.pid)
        path = self.imports / 'snapshots' / state['snapshot_ref'] / state['documents'][0]['storage_relative_path']
        path.write_bytes(b'tampered')
        with self.assertRaises(HarnessError):
            self.service.list_sources(self.pid)
        with self.assertRaises(HarnessError):
            self.service.preview_source(self.pid, state['documents'][0]['document_ref'])

    def test_zip_raw_source_can_exceed_md_entry_limit_and_replay(self):
        # Two legal entries; the raw ZIP has a separate 64 MiB upload budget.
        data = archive([('one.md', b'a' * (4 * 1024 * 1024)),
                        ('two.md', b'b' * (4 * 1024 * 1024))])
        self.assertGreater(len(data), 8 * 1024 * 1024)
        self.assertEqual(self.push([('large.zip', data)])['accepted_count'], 2)
        self.assertEqual(len(self.service.list_sources(self.pid)['documents']), 2)
        self.assertEqual(self.push([('large.zip', data)])['status'], 'UNCHANGED')

    @unittest.skipUnless(os.name == 'nt', 'Requires actual NTFS directory junctions')
    def test_native_windows_snapshot_parent_junction_rejected(self):
        import _winapi
        self.push([('doc.md', b'private source')])
        inventory = self.service.list_sources(self.pid)
        snapshot = self.imports / 'snapshots' / inventory['snapshot_ref']
        for path in (self.imports, self.imports / 'snapshots', snapshot, snapshot / 'materialized'):
            with self.subTest(component=path.name):
                moved = self.base / 'moved-component'
                path.rename(moved)
                _winapi.CreateJunction(str(moved), str(path))
                try:
                    self.assertTrue(path.is_junction())
                    before = byte_snapshot(moved)
                    with self.assertRaises(HarnessError):
                        self.service.preview_source(self.pid, inventory['documents'][0]['document_ref'])
                    with self.assertRaises(HarnessError):
                        self.service.list_sources(self.pid)
                    self.assertEqual(before, byte_snapshot(moved))
                finally:
                    # Remove only the link we created, never recursively its target.
                    os.rmdir(path)
                    moved.rename(path)

    def test_snapshot_hardlink_and_copy_time_tamper_fail_closed(self):
        self.push([('doc.md', b'original')])
        inventory = self.service.list_sources(self.pid)
        doc = inventory['documents'][0]
        base = self.imports / 'snapshots' / inventory['snapshot_ref']
        path = base / doc['storage_relative_path']
        alias = self.base / 'alias.md'
        os.link(path, alias)
        try:
            with self.assertRaises(HarnessError):
                self.service.preview_source(self.pid, doc['document_ref'])
        finally:
            alias.unlink()
        from project_harness.local_web_imports import copy_verified_document
        original_open = os.open
        def change_before_open(target, flags, *args, **kwargs):
            if Path(target) == path:
                path.write_bytes(b'tampered')
            return original_open(target, flags, *args, **kwargs)
        destination = self.base / 'copy.md'
        with mock.patch('project_harness.local_web_imports.os.open', side_effect=change_before_open):
            with self.assertRaises(HarnessError):
                copy_verified_document(base, doc['storage_relative_path'], doc['sha256'], destination)
        self.assertFalse(destination.exists())

    def test_upload_source_bytes_not_modified_and_no_command_started(self):
        binary = archive([('instructions.md', b'#!/bin/sh\nrm -rf /\n')])
        bio = BytesIO(binary)
        import subprocess
        with mock.patch.object(subprocess, 'run', side_effect=AssertionError('no shell')):
            result = self.service.upload_sources(self.pid, [('instruction.zip', bio)], mode='append',
                 expected_fingerprint=self.service.get_status(self.pid)['fingerprint'], expected_source_revision=0)
        self.assertEqual(result['status'], 'IMPORTED_NOT_ANALYZED')
        self.assertEqual(bio.getvalue(), binary)

    def test_malicious_zip_cases_rejected_without_workspace_change(self):
        cases = [
            ('dotdot', [('../outside.md', b'x')]),
            ('absolute', [('/tmp/unsafe.md', b'x')]),
            ('drive', [('C:evil.md', b'x')]),
            ('unc', [('\\\\server\\share\\evil.md', b'x')]),
            ('backslash', [('a\\b.md', b'x')]),
            ('ads', [('a.md:evil', b'x')]),
            ('device', [('NUL.md', b'x')]),
            ('trailingdot', [('a./evil.md', b'x')]),
            ('trailingspace', [('a /evil.md', b'x')]),
            ('control', [('a\x01.md', b'x')]),
            ('casecollision', [('a/A.md', b'x'), ('a/a.md', b'y')]),
            ('unicodecollision', [('café.md', b'x'), ('cafe\u0301.md', b'y')]),
            ('dircasecollision', [('Folder/x.md', b'x'), ('folder/y.md', b'y')]),
            ('file_as_dir', [('a.md', b'x'), ('a.md/other.md', b'y')]),
            ('nestedarchive', [('doc.md', b'x'), ('archive.zip', b'PKxx')]),
            ('invalidutf8', [('doc.md', b'\xff\xfe')]),
            ('depth17', [('/'.join(['folder'] * 16) + '/deep.md', b'x')]),
            ('compression_ratio', [('doc.md', b'x'*300000)]),
        ]
        before = byte_snapshot(self.root)
        for key, entries in cases:
            with self.subTest(key=key):
                content = archive(entries, compress=zipfile.ZIP_DEFLATED)
                with self.assertRaises(HarnessError):
                    self.push([(key + '.zip', content)])
                self.assertEqual(byte_snapshot(self.root), before)
                self.assertEqual(self.service.list_sources(self.pid)['source_revision'], 0)
        self.assertFalse((self.imports / 'snapshots').exists())

    def test_special_symlink_fifo_reparse_and_encryption_rejected(self):
        for kind in ('symlink', 'fifo', 'reparse'):
            with self.subTest(kind=kind):
                b = BytesIO()
                with zipfile.ZipFile(b, 'w') as zf:
                    info = zipfile.ZipInfo('doc.md')
                    info.create_system = 3
                    if kind == 'symlink': info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    if kind == 'fifo': info.external_attr = (stat.S_IFIFO | 0o644) << 16
                    if kind == 'reparse': info.external_attr = (0x400 | stat.S_IFREG) << 16
                    zf.writestr(info, b'abc')
                with self.assertRaises(HarnessError):
                    self.push([(kind + '.zip', b.getvalue())])
        # Genuine encrypted flag in local AND central header; importer rejects
        # it before decompression, rather than attempting a password.
        raw = bytearray(archive([('doc.md', b'abc')]))
        head = raw.find(b'PK\x03\x04'); central = raw.find(b'PK\x01\x02')
        struct.pack_into('<H', raw, head + 6, 1)
        struct.pack_into('<H', raw, central + 8, 1)
        with self.assertRaises(HarnessError):
            self.push([('encrypted.zip', bytes(raw))])

    def test_corrupt_crc_oversized_entry_and_entry_count(self):
        content = bytearray(archive([('doc.md', b'abcd')]))
        index = content.index(b'abcd')
        content[index] = 0xFF
        with self.assertRaises(HarnessError):
            self.push([('crc.zip', bytes(content))])
        oversized = archive([('huge.md', b'a'*(8*1024*1024+1))], compress=zipfile.ZIP_DEFLATED)
        with self.assertRaises(HarnessError):
            self.push([('size.zip', oversized)])
        # 1001 empty entries is rejected by central-directory budget.
        entries = [(f'{index:04}.md', b'x') for index in range(1001)]
        with self.assertRaises(HarnessError):
            self.push([('count.zip', archive(entries))])

    def test_unsafe_top_level_filenames_and_encoding_fail(self):
        for key in ('../evil.md', 'C:\\evil.md', 'COM1.md', 'bad:stream.md', 'file. ', 'a\\b.md'):
            with self.subTest(name=key):
                with self.assertRaises(HarnessError):
                    self.push([(key, b'plain')])
        with self.assertRaises(HarnessError):
            self.push([('bad.md', b'\xff')])
        self.assertEqual(self.service.list_sources(self.pid)['source_revision'], 0)


if __name__ == '__main__':
    unittest.main()

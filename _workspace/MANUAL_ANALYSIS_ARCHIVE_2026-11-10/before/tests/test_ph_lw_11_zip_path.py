"""Native long app-data ZIP intake: exact bytes, inert data and recovery."""
import ctypes
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from project_harness.local_web_service import LocalWebService
from project_harness.local_web_imports import verify_snapshot
from project_harness.errors import HarnessError, ValidationFailure
from project_harness.local_web_source_refresh import pending_refresh
from project_harness.serialization import load_data
import tests.test_ph_lw_05_import as previous
import tests.test_ph_lw_06_exchange as exchange
archive=previous.archive

def snapshot(root):
    io=Path('\\\\?\\'+str(root.absolute())) if os.name=='nt' else root
    return {p.relative_to(io).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in io.rglob('*') if p.is_file()}

def setting():
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SYSTEM\CurrentControlSet\Control\FileSystem') as key:
        return winreg.QueryValueEx(key,'LongPathsEnabled')[0]

@unittest.skipUnless(os.name=='nt','Native Windows required')
class LongAppDataZipTests(unittest.TestCase):
    push=previous.LocalSourceImporter.push
    export=exchange.ExchangeFixture.export
    reply=exchange.ExchangeFixture.reply
    preview=exchange.ExchangeFixture.preview
    commit=exchange.ExchangeFixture.commit
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='zip-long-');self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.data=self.base/('Данные-'+('x'*45))
        assert self.data.is_absolute() and self.data.is_relative_to(self.base)
        self.addCleanup(lambda:shutil.rmtree(Path('\\\\?\\'+str(self.data)),ignore_errors=True))
        self.service=LocalWebService(self.data/'app');self.addCleanup(self.service.close)
        self.pid=self.service.create_provisional_intake(project_name='Long ZIP',idempotency_key='zip-long-create-000001')['project_id']
        self.root,_=self.service._registered(self.pid);self.imports=self.root.parent/'imports'

    def test_nested_zip_long_path_preview_exact_bytes_and_readonly(self):
        before=setting();self.assertFalse(ctypes.windll.shell32.IsUserAnAdmin())
        text='# Текст\n<script>inert()</script>'.encode('utf-8')
        wire=archive([('Раздел/Вложенный раздел/Требования.md',text),('AGENTS.md',b'never execute'),('image.png',b'image')])
        result=self.push([('Документы.zip',wire)])
        self.assertEqual(result['accepted_count'],1);self.assertEqual(result['skipped_count'],2)
        listed=self.service.list_sources(self.pid);doc=listed['documents'][0]
        path=self.imports/'snapshots'/listed['snapshot_ref']/doc['storage_relative_path']
        self.assertGreater(len(str(path)),260)
        self.assertEqual(doc['sha256'],'sha256:'+hashlib.sha256(text).hexdigest())
        self.assertEqual(verify_snapshot(self.imports,listed['snapshot_ref'])['record']['trust'],'UNTRUSTED_PROJECT_DATA')
        baseline=snapshot(self.data)
        preview=self.service.preview_source(self.pid,doc['document_ref'])
        self.assertIn('<script>',preview['preview_text']);self.assertEqual(preview['rendering'],'ESCAPED_PLAIN_TEXT')
        self.assertEqual(snapshot(self.data),baseline)
        self.assertNotIn('\\\\?\\',str(listed))
        self.assertEqual(load_data(self.root/'PROJECT_INPUT.yaml')['project']['documentation']['normative_sources'],[])
        self.assertEqual(setting(),before)

    def test_zip_append_replay_restart_replace_preserves_old_snapshot(self):
        first=archive([('длинный раздел/вложенные требования/spec.md',b'original')])
        self.push([('one.zip',first)])
        before=snapshot(self.data)
        self.assertEqual(self.push([('one.zip',first)])['status'],'UNCHANGED')
        self.assertEqual(snapshot(self.data),before)
        old=self.service.list_sources(self.pid)['snapshot_ref']
        preserved=snapshot(self.imports/'snapshots'/old)
        with LocalWebService(self.data/'app') as other:
            self.assertEqual(self.push([('one.zip',first)],service=other)['status'],'UNCHANGED')
            self.assertEqual(self.push([('two.zip',archive([('nested/deeper/two.md',b'two')]))],service=other)['source_revision'],2)
            self.assertEqual(len(other.list_sources(self.pid)['documents']),2)
            self.assertEqual(self.push([('new.zip',archive([('nested/deeper/new.md',b'new')]))],mode='replace',service=other)['source_revision'],3)
            self.assertEqual(len(other.list_sources(self.pid)['documents']),1)
        self.assertEqual(snapshot(self.imports/'snapshots'/old),preserved)
        self.assertEqual(verify_snapshot(self.imports,old)['record']['snapshot_ref'],old)

    def test_negative_zip_contracts_at_long_root_keep_canonical_bytes(self):
        # Execute the existing full wire-format negative cases at this root.
        # Only their snapshot reader is adapted, so no deep file is omitted.
        with patch.object(previous,'byte_snapshot',snapshot):
            previous.LocalSourceImporter.test_malicious_zip_cases_rejected_without_workspace_change(self)
            previous.LocalSourceImporter.test_special_symlink_fifo_reparse_and_encryption_rejected(self)
            previous.LocalSourceImporter.test_corrupt_crc_oversized_entry_and_entry_count(self)

    def test_interrupted_zip_refresh_explicit_restart_recovery_exact_bytes(self):
        self.push([('old.zip',archive([('section/nested/original.md',b'original')]))])
        before=snapshot(self.root);ledger=(self.imports/'state.json').read_bytes()
        original=os.replace;triggered=[]
        def fail(src,dst):
            if Path(dst).parts[-2:]==('intake','READINESS.json') and not triggered:
                triggered.append(True);raise OSError('injected ZIP refresh interruption')
            return original(src,dst)
        with patch('project_harness.local_web_source_refresh.os.replace',side_effect=fail):
            with patch('project_harness.local_web_source_refresh.recover_source_refresh',side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    self.push([('new.zip',archive([('section/nested/replacement.md',b'new')]))],mode='replace')
        self.assertTrue(triggered);self.assertTrue(pending_refresh(self.root))
        with LocalWebService(self.data/'app') as restarted:
            interrupted=snapshot(self.data)
            with self.assertRaises(ValidationFailure):restarted.get_status(self.pid)
            self.assertEqual(snapshot(self.data),interrupted)
            self.assertEqual(restarted.recover_source_import(self.pid)['status'],'ROLLED_BACK_RECOVERED')
            self.assertFalse(pending_refresh(self.root))
            self.assertEqual(snapshot(self.root),before)
            self.assertEqual((self.imports/'state.json').read_bytes(),ledger)
            self.assertEqual(restarted.list_sources(self.pid)['source_revision'],1)

    def test_deep_snapshot_tamper_and_junction_rejected_readonly(self):
        import _winapi
        self.push([('doc.zip',archive([('section/nested/original.md',b'original')]))])
        state=self.service.list_sources(self.pid);doc=state['documents'][0]
        path=self.imports/'snapshots'/state['snapshot_ref']/doc['storage_relative_path']
        io=Path('\\\\?\\'+str(path));self.assertGreater(len(str(path)),260)
        io.write_bytes(b'tampered');before=snapshot(self.data)
        with self.assertRaises(HarnessError):self.service.preview_source(self.pid,doc['document_ref'])
        self.assertEqual(snapshot(self.data),before);io.write_bytes(b'original')
        parent=path.parent;link=Path('\\\\?\\'+str(parent));moved=self.base/'moved-private-directory'
        link.rename(moved)
        _winapi.CreateJunction(str(moved),str(link))
        try:
            self.assertTrue(link.is_junction());before=snapshot(moved)
            with self.assertRaises(HarnessError):self.service.preview_source(self.pid,doc['document_ref'])
            with self.assertRaises(HarnessError):self.service.list_sources(self.pid)
            self.assertEqual(snapshot(moved),before)
        finally:
            os.rmdir(link);moved.rename(link)

    def test_deep_copy_time_tamper_and_hardlink_fail_closed(self):
        from project_harness.local_web_imports import copy_verified_document
        self.push([('doc.zip',archive([('section/nested/original.md',b'original')]))])
        state=self.service.list_sources(self.pid);doc=state['documents'][0]
        base=self.imports/'snapshots'/state['snapshot_ref'];path=base/doc['storage_relative_path']
        io=Path('\\\\?\\'+str(path));self.assertGreater(len(str(path)),260)
        alias=self.base/'hardlink.md';os.link(io,alias)
        try:
            with self.assertRaises(HarnessError):self.service.preview_source(self.pid,doc['document_ref'])
        finally:alias.unlink()
        original=os.open;triggered=[]
        def change(target,flags,*args,**kwargs):
            if Path(target)==io:
                triggered.append(True);io.write_bytes(b'tampered')
            return original(target,flags,*args,**kwargs)
        destination=self.base/'copy.md'
        with patch('project_harness.local_web_imports.os.open',side_effect=change):
            with self.assertRaises(HarnessError):copy_verified_document(base,doc['storage_relative_path'],doc['sha256'],destination)
        self.assertTrue(triggered);self.assertFalse(destination.exists())

    def test_imported_long_zip_document_manual_exchange_roundtrip(self):
        self.push([('doc.zip',archive([('section/nested/requirements.md',b'# exact untrusted text')]))])
        exported=self.export('long-zip-exchange-00001')
        reply=self.reply(exported,{'project.problem_statement':'Synthetic unverified claim'})
        before=snapshot(self.root)
        preview=self.preview(reply)
        self.assertEqual(preview['status'],'PREVIEW',preview)
        self.assertEqual(snapshot(self.root),before)
        self.assertEqual(self.commit(preview['preview'])['state'],'COMMITTED')
        data=load_data(self.root/'PROJECT_INPUT.yaml')
        self.assertEqual(data['execution']['mode'],'MANUAL_HANDOFF')
        self.assertEqual(data['project']['documentation']['normative_sources'],[])
        second=self.export('long-zip-exchange-00002')
        self.assertEqual(second['export_revision'],2)
        before=snapshot(self.data)
        self.assertEqual(self.export('long-zip-exchange-00002'),second)
        self.assertEqual(snapshot(self.data),before)

if __name__=='__main__':unittest.main()

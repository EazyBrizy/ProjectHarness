from __future__ import annotations
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from project_harness.errors import ValidationFailure
from project_harness.local_web_desktop import DesktopLifecycle, read_resume, save_resume
from project_harness.local_web_http import create_app
from project_harness.local_web_service import LocalWebService
from project_harness.windows_package import activate, verify_bundle


class DesktopContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='harness-lw11-')
        self.base = Path(self.tmp.name)
        self.service = LocalWebService(self.base/'app')
        self.app = create_app(self.service, port=32179)
        self.client = self.app.test_client()
        self.headers = {'Host':'127.0.0.1:32179','Origin':'http://127.0.0.1:32179'}

    def tearDown(self):
        self.service.close(); self.tmp.cleanup()

    def post(self, path, body):
        return self.client.post(path, json=body, headers=self.headers)

    def test_resume_read_is_readonly_restart_and_cas(self):
        before = sorted(str(p) for p in self.base.rglob('*'))
        self.assertEqual(self.client.get('/api/ui/resume',headers=self.headers).json['revision'],0)
        self.assertEqual(before, sorted(str(p) for p in self.base.rglob('*')))
        pid = self.service.create_provisional_intake(project_name='Resume', no_documentation=True,
                                                    idempotency_key='create-resume-00001')['project_id']
        data = {'project_id':pid, 'screen':'approvals', 'expected_revision':0}
        self.assertEqual(self.post('/api/ui/resume',data).status_code,200)
        saved = (self.service.app_data/'ui-resume.json').read_bytes()
        self.assertNotEqual(self.post('/api/ui/resume',data).status_code,200)
        self.assertEqual(saved,(self.service.app_data/'ui-resume.json').read_bytes())
        self.service.close(); self.service=LocalWebService(self.base/'app')
        self.assertEqual(read_resume(self.service),{'project_id':pid,'screen':'approvals','revision':1})

    def test_resume_rejects_unknown_fields_ids_paths_and_screen(self):
        for body in [dict(project_id='../bad',screen='projects',expected_revision=0),
                     dict(project_id=None,screen='shell',expected_revision=0),
                     dict(project_id=None,screen='projects',expected_revision=0,extra=1),
                     dict(project_id=None,screen='projects',expected_revision=True)]:
            self.assertGreaterEqual(self.post('/api/ui/resume',body).status_code,400)
        self.assertFalse((self.service.app_data/'ui-resume.json').exists())

    def test_stop_without_login_preserves_origin_and_field_validation(self):
        invalid={'Host':'127.0.0.1:32179','Origin':'http://evil.invalid'}
        self.assertEqual(self.client.post('/api/desktop/stop',json={},headers=invalid).status_code,403)
        self.assertEqual(self.post('/api/desktop/stop',{'force':True}).status_code,400)
        self.assertFalse(self.service.desktop_lifecycle.stopping.is_set())
        self.assertEqual(self.app.test_client().post('/api/desktop/stop',json={},headers=self.headers).status_code,200)

    def test_stop_busy_admission_and_background_work_then_clean_stop(self):
        life = self.service.desktop_lifecycle
        self.assertTrue(life.enter())
        self.assertGreaterEqual(self.post('/api/desktop/stop',{}).status_code,400)
        life.leave()
        future=concurrent.futures.Future();self.service._futures['fixture']=future
        self.assertGreaterEqual(self.post('/api/desktop/stop',{}).status_code,400)
        future.set_result(None)
        self.assertEqual(self.post('/api/desktop/stop',{}).json,{'status':'STOPPING'})
        self.assertEqual(self.post('/api/intakes',dict(project_name='must not exist',no_documentation=True,idempotency_key='do-not-create-0001')).status_code,409)
        self.assertFalse(life.enter())
        self.assertEqual(self.service.list_projects(),[])

    def test_independent_clients_access_without_sessions_or_cookies(self):
        for client in (self.client,self.app.test_client()):
            response=client.get('/api/ui/resume',headers=self.headers)
            self.assertEqual(response.status_code,200)
            self.assertNotIn('Set-Cookie',response.headers)

    def test_browser_failure_displays_plain_url_without_login_code(self):
        if os.name!='nt':self.skipTest('native Windows')
        from project_harness.local_web_launcher import open_local_browser
        with patch('webbrowser.open',return_value=False),patch('ctypes.windll.user32.MessageBoxW') as message,patch('builtins.print') as output:
            self.assertFalse(open_local_browser('http://127.0.0.1:1234/'))
            self.assertIn('http://127.0.0.1:1234/',message.call_args.args[1])
            self.assertNotIn('код',message.call_args.args[1]);output.assert_not_called()


class InstallerTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='harness-lw11-package-');self.base=Path(self.tmp.name)
        self.payload=self.base/'payload';self.payload.mkdir();(self.payload/'Harness.exe').write_bytes(b'unit fixture, not executable')
        self.inventory={'format':1,'build_id':'test-build','files':{'Harness.exe':hashlib.sha256((self.payload/'Harness.exe').read_bytes()).hexdigest()}}
        (self.payload/'PACKAGE_FILES.json').write_text(json.dumps(self.inventory),'utf-8');self.target=self.base/'Программа с пробелами'
    def tearDown(self):
        import shutil
        from project_harness.windows_package import _io_path
        self.assertEqual(self.base.parent.resolve(),Path(tempfile.gettempdir()).resolve())
        self.assertTrue(self.base.name.startswith('harness-lw11-package-'))
        shutil.rmtree(_io_path(self.base))
        self.tmp.cleanup()

    def test_activate_replay_preserves_project_and_current_version(self):
        product=self.base/'product';product.mkdir();(product/'sentinel').write_bytes(b'keep')
        first=activate(self.payload,self.target);saved=(first/'Harness.exe').read_bytes()
        self.assertEqual(first,activate(self.payload,self.target));self.assertEqual(saved,(first/'Harness.exe').read_bytes())
        self.assertEqual((product/'sentinel').read_bytes(),b'keep')
        self.assertEqual(json.loads((self.target/'current.json').read_text())['build_id'],'test-build')

    def test_corruption_and_extra_files_refused_before_destination(self):
        (self.payload/'extra.txt').write_bytes(b'extra')
        with self.assertRaises(ValidationFailure):activate(self.payload,self.target)
        self.assertFalse(self.target.exists());(self.payload/'extra.txt').unlink()
        (self.payload/'Harness.exe').write_bytes(b'tampered')
        with self.assertRaises(ValidationFailure):activate(self.payload,self.target)
        self.assertFalse(self.target.exists())

    def test_existing_foreign_directory_never_overwritten(self):
        self.target.mkdir();(self.target/'sentinel').write_bytes(b'keep')
        with self.assertRaises(ValidationFailure):activate(self.payload,self.target)
        self.assertEqual(list(self.target.iterdir()),[self.target/'sentinel'])

    def test_native_long_payload_path_without_system_setting_change(self):
        if os.name!='nt':self.skipTest('native Windows')
        from project_harness.windows_package import _io_path
        relative='documentation/'+'nested-'*15+'/'+('chapter-'*14)+'.md'
        file=_io_path(self.payload)/relative;file.parent.mkdir(parents=True);file.write_bytes(b'long path fixture')
        self.inventory['files'][relative]=hashlib.sha256(file.read_bytes()).hexdigest()
        (self.payload/'PACKAGE_FILES.json').write_text(json.dumps(self.inventory),'utf-8')
        installed=activate(self.payload,self.target)
        self.assertEqual(verify_bundle(installed),self.inventory)
        self.assertEqual((_io_path(installed)/relative).read_bytes(),b'long path fixture')

    def test_native_junction_and_hardlink_payload_rejected(self):
        if os.name!='nt':self.skipTest('native Windows')
        outside=self.base/'outside';outside.mkdir();(outside/'sentinel').write_bytes(b'keep')
        junction=self.payload/'linked'
        result=subprocess.run(['cmd.exe','/c','mklink','/J',str(junction),str(outside)],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        try:
            with self.assertRaises(ValidationFailure):verify_bundle(self.payload)
            self.assertEqual((outside/'sentinel').read_bytes(),b'keep')
        finally:junction.rmdir()
        os.link(self.payload/'Harness.exe',outside/'hardlink')
        with self.assertRaises(ValidationFailure):verify_bundle(self.payload)

    def test_injected_enospc_and_interruption_preserve_current_and_retry(self):
        activate(self.payload,self.target);current=(self.target/'current.json').read_bytes()
        self.inventory['build_id']='new-build';(self.payload/'PACKAGE_FILES.json').write_text(json.dumps(self.inventory),'utf-8')
        with patch('project_harness.windows_package.shutil.copytree',side_effect=OSError(28,'injected ENOSPC')):
            with self.assertRaises(OSError):activate(self.payload,self.target)
        self.assertEqual(current,(self.target/'current.json').read_bytes())
        def interrupted(source,target):
            target.mkdir();(target/'partial').write_bytes(b'partial');raise OSError('injected interruption')
        with patch('project_harness.windows_package.shutil.copytree',side_effect=interrupted):
            with self.assertRaises(OSError):activate(self.payload,self.target)
        self.assertEqual(current,(self.target/'current.json').read_bytes())
        activate(self.payload,self.target)
        self.assertTrue(any(self.target.glob('staging-*/partial')))

    def test_native_readonly_current_preserves_old_pointer(self):
        if os.name!='nt':self.skipTest('native Windows')
        import stat
        activate(self.payload,self.target);pointer=self.target/'current.json';before=pointer.read_bytes()
        self.inventory['build_id']='second-build';(self.payload/'PACKAGE_FILES.json').write_text(json.dumps(self.inventory),'utf-8')
        pointer.chmod(stat.S_IREAD)
        try:
            with self.assertRaises(Exception):activate(self.payload,self.target)
            self.assertEqual(pointer.read_bytes(),before)
        finally:pointer.chmod(stat.S_IWRITE|stat.S_IREAD)


@unittest.skipUnless(os.name=='nt','Windows mutex/DPAPI/TCP')
class NativeLauncherTests(unittest.TestCase):
    def test_launcher_resume_and_new_cookie_tab_keep_independent_navigation(self):
        from tests.test_ph_lw_04_05_acceptance import LiveServer
        from tests.test_ph_lw_03_service import byte_snapshot
        from project_harness.intake import start_intake
        from project_harness.local_web_desktop import save_resume
        from playwright.sync_api import sync_playwright,expect
        with tempfile.TemporaryDirectory(prefix='harness-lw11-tabs-') as folder:
            live=LiveServer(folder)
            try:
                root=Path(folder)/'intake';start_intake(root,project_name='Resume tab',mode='GREENFIELD')
                pid=live.service.register_existing(root,kind='workspace')
                save_resume(live.service,project_id=pid,screen='documents',expected_revision=0)
                before=byte_snapshot(Path(folder))
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel='msedge',headless=True)
                    try:
                        context=browser.new_context()
                        launched=context.new_page()
                        launched.goto(live.origin + '/',wait_until='networkidle')
                        expect(launched.locator('#documents-panel')).to_be_visible()
                        other=context.new_page();other.goto(live.origin,wait_until='networkidle')
                        expect(other.locator('#documents-panel')).to_be_visible()
                        launched.reload(wait_until='networkidle')
                        expect(launched.locator('#documents-panel')).to_be_visible()
                        self.assertEqual(before,byte_snapshot(Path(folder)))
                        context.close()
                    finally:browser.close()
            finally:live.close()

    def test_upload_success_waits_for_refresh_before_interview_can_start(self):
        import re
        from tests.test_ph_lw_04_05_acceptance import LiveServer
        from playwright.sync_api import sync_playwright,expect
        with tempfile.TemporaryDirectory(prefix='harness-lw11-upload-') as folder:
            live=LiveServer(folder)
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel='msedge',headless=True)
                    try:
                        page=browser.new_page();page.on('dialog',lambda d:d.accept())
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        page.locator('[data-screen="documents"]').click();page.locator('#new-project-name').fill('Delayed refresh')
                        page.locator('#create-intake').click();expect(page.locator('#notice')).to_contain_text('Проект создан')
                        held=[]
                        page.route(re.compile(r'/api/projects/LWP-[A-F0-9]+$'),lambda route:held.append(route))
                        page.locator('#source-files').set_input_files({'name':'fixture.md','mimeType':'text/markdown','buffer':b'# fixture'})
                        with page.expect_response(lambda r:r.url.endswith('/sources/upload')):
                            page.locator('#upload-sources').click()
                        for _ in range(40):
                            if held:break
                            page.wait_for_timeout(50)
                        self.assertTrue(held,'The project refresh must be held by the test')
                        try:
                            expect(page.locator('#upload-result')).not_to_contain_text('Принято:')
                            expect(page.locator('#upload-progress')).to_be_visible()
                        finally:
                            for route in held:route.continue_()
                            page.unroute_all(behavior='ignoreErrors')
                        expect(page.locator('#upload-result')).to_contain_text('Принято: 1')
                        expect(page.locator('#upload-progress')).to_be_hidden()
                    finally:browser.close()
            finally:live.close()

    def test_edge_direct_entry_without_login_controls_or_external_requests(self):
        from tests.test_ph_lw_04_05_acceptance import LiveServer
        from playwright.sync_api import sync_playwright,expect
        with tempfile.TemporaryDirectory(prefix='harness-direct-entry-') as folder:
            live=LiveServer(folder)
            try:
                with sync_playwright() as play:
                    browser=play.chromium.launch(channel='msedge',headless=True)
                    try:
                        page=browser.new_page();urls=[];page.on('request',lambda r:urls.append(r.url))
                        page.goto(live.origin+'/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        self.assertEqual(page.locator('#session-gate,#manual-bootstrap,#manual-login,#logout').count(),0)
                        self.assertNotIn('#',page.url)
                        self.assertTrue(all(url.startswith(live.origin+'/') for url in urls))
                        self.assertFalse(any('/api/session' in url for url in urls))
                    finally:browser.close()
            finally:live.close()

    def test_native_mutex_subprocess(self):
        from project_harness.local_web_instance import UserInstanceLock
        code='from project_harness.local_web_instance import UserInstanceLock; x=UserInstanceLock(); print(x.__enter__().owned); x.__exit__()'
        with UserInstanceLock() as first:
            self.assertTrue(first.owned)
            child=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,timeout=20)
            self.assertEqual(child.returncode,0,child.stderr);self.assertEqual(child.stdout.strip(),'False')

    def test_plain_instance_record_discovery_cleanup_and_invalid_records(self):
        from project_harness.local_web_instance import LauncherInstance,connect_existing
        from tests.test_ph_lw_04_05_acceptance import LiveServer
        with tempfile.TemporaryDirectory(prefix='harness-instance-') as folder:
            live=LiveServer(folder);base=live.service.app_data
            instance=LauncherInstance(base,live.port)
            try:
                self.assertEqual(connect_existing(base),live.origin+'/')
                record=json.loads((base/'launcher-instance.json').read_text('utf-8'))
                self.assertEqual(record,{'version':2,'pid':os.getpid(),'port':live.port})
                self.assertFalse((base/'launcher-private.json').exists())
            finally:instance.close();live.close()
            self.assertFalse((base/'launcher-instance.json').exists())
            for record in ({'version':2,'pid':0,'port':1234},{'version':2,'pid':os.getpid(),'port':True},
                           {'version':1,'identity':'old','key_dpapi':'unused'}):
                (base/'launcher-instance.json').write_text(json.dumps(record),'utf-8')
                with self.assertRaises(ValidationFailure):connect_existing(base)

if __name__=='__main__':unittest.main()

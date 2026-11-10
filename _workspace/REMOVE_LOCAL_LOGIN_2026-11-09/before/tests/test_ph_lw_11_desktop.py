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
from project_harness.local_web_http import LocalWebAuth, create_app
from project_harness.local_web_service import LocalWebService
from project_harness.windows_package import activate, verify_bundle


class DesktopContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='harness-lw11-')
        self.base = Path(self.tmp.name)
        self.service = LocalWebService(self.base/'app')
        self.auth = LocalWebAuth()
        self.app = create_app(self.service, port=32179, auth=self.auth)
        self.client = self.app.test_client()
        self.headers = {'Host':'127.0.0.1:32179','Origin':'http://127.0.0.1:32179'}
        response = self.client.post('/api/session/bootstrap',json={'token':self.auth.issue_bootstrap()},headers=self.headers)
        self.headers['X-CSRF-Token'] = response.json['csrf']

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

    def test_stop_requires_session_csrf_exact_origin_and_fields(self):
        for headers in [{'Host':'127.0.0.1:32179','Origin':'http://evil.invalid'},
                        {'Host':'127.0.0.1:32179','Origin':'http://127.0.0.1:32179'}]:
            self.assertGreaterEqual(self.client.post('/api/desktop/stop',json={},headers=headers).status_code,400)
        self.assertEqual(self.post('/api/desktop/stop',{'force':True}).status_code,400)
        self.assertFalse(self.service.desktop_lifecycle.stopping.is_set())
        stranger=self.app.test_client()
        self.assertEqual(stranger.post('/api/desktop/stop',json={},headers=self.headers).status_code,401)

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

    def test_bootstrap_reissue_does_not_revoke_other_tabs(self):
        old=self.auth.issue_bootstrap();new=self.auth.issue_bootstrap()
        self.assertEqual(self.client.post('/api/session/bootstrap',json={'token':old},headers=self.headers).status_code,401)
        self.assertEqual(self.client.get('/api/ui/resume',headers=self.headers).status_code,200)
        self.assertEqual(self.client.post('/api/session/bootstrap',json={'token':new},headers=self.headers).status_code,200)

    def test_browser_failure_displays_only_native_fallback(self):
        if os.name != 'nt': self.skipTest('native Windows')
        from project_harness.local_web_launcher import open_local_browser
        with patch('webbrowser.open',return_value=False),patch('ctypes.windll.user32.MessageBoxW') as message,patch('builtins.print') as output:
            self.assertFalse(open_local_browser('http://127.0.0.1:1234/#bootstrap='+'X'*43))
            self.assertIn('X'*43,message.call_args.args[1]);output.assert_not_called()


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
                        launched.goto(live.origin+'/#bootstrap='+live.auth.issue_bootstrap(),wait_until='networkidle')
                        expect(launched.locator('#documents-panel')).to_be_visible()
                        other=context.new_page();other.goto(live.origin,wait_until='networkidle')
                        expect(other.locator('#project-layout')).to_be_visible()
                        expect(other.locator('.project-button').filter(has_text=pid)).to_be_visible()
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
                        page.goto(live.origin+'/#bootstrap='+live.auth.issue_bootstrap())
                        expect(page.locator('#session-state')).to_have_text('Сессия активна')
                        page.locator('[data-screen="documents"]').click();page.locator('#new-project-name').fill('Delayed refresh')
                        page.locator('#create-intake').click();expect(page.locator('#notice')).to_contain_text('Intake создан')
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

    def test_edge_manual_code_login_without_fragment_or_external_requests(self):
        from tests.test_ph_lw_04_05_acceptance import LiveServer
        from playwright.sync_api import sync_playwright,expect
        with tempfile.TemporaryDirectory(prefix='harness-lw11-manual-login-') as folder:
            live=LiveServer(folder)
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel='msedge',headless=True)
                    try:
                        context=browser.new_context()
                        page=context.new_page();urls=[];page.on('request',lambda r:urls.append(r.url))
                        page.goto(live.origin)
                        expect(page.locator('#session-gate')).to_be_visible()
                        page.locator('#manual-bootstrap').fill(live.auth.issue_bootstrap())
                        page.locator('#manual-login').click()
                        expect(page.locator('#session-state')).to_have_text('Сессия активна')
                        expect(page.locator('#manual-bootstrap')).to_have_value('')
                        expect(page.locator('#notice')).to_contain_text('Список обновлён.')
                        self.assertNotIn('bootstrap',page.url)
                        self.assertTrue(all(url.startswith(live.origin+'/') for url in urls))
                        context.close()
                    finally:browser.close()
            finally:live.close()

    def test_dpapi_and_native_mutex_subprocess(self):
        from project_harness.local_web_instance import UserInstanceLock,protect
        self.assertEqual(protect(protect(b'private'),decrypt=True),b'private')
        code='from project_harness.local_web_instance import UserInstanceLock; x=UserInstanceLock(); print(x.__enter__().owned); x.__exit__()'
        with UserInstanceLock() as first:
            self.assertTrue(first.owned)
            child=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,timeout=20)
            self.assertEqual(child.returncode,0,child.stderr);self.assertEqual(child.stdout.strip(),'False')

    def test_fresh_authenticated_handshake_and_spoof_listener(self):
        import base64
        from project_harness.local_web_instance import LauncherChannel,connect_existing,protect,_receive,_send
        with tempfile.TemporaryDirectory(prefix='harness-lw11-handshake-') as folder:
            base=Path(folder);auth=LocalWebAuth();stop=threading.Event()
            channel=LauncherChannel(base,auth,32189,stop)
            try:
                url=connect_existing(base);self.assertTrue(url.startswith('http://127.0.0.1:32189/#bootstrap='))
                auth.exchange(url.split('=')[1])
                record=(base/'launcher-private.json').read_text();self.assertNotIn(url.split('=')[1],record)
                stop.set()
                with self.assertRaises(Exception):connect_existing(base)
            finally:channel.close()
            fake=socket.socket();fake.bind(('127.0.0.1',0));fake.listen();fake.settimeout(5)
            (base/'launcher-private.json').write_text(json.dumps({'version':1,'port':fake.getsockname()[1],
                'identity':'fake','key_dpapi':base64.b64encode(protect(b'K'*32)).decode()}),'utf-8')
            received=[]
            def peer():
                conn,_=fake.accept()
                with conn:
                    conn.settimeout(3);received.append(_receive(conn));_send(conn,{'port':1234,'challenge':'a'*64,'proof':'0'*64})
                    received.append(conn.recv(1024))
            thread=threading.Thread(target=peer);thread.start()
            try:
                with self.assertRaises(ValidationFailure):connect_existing(base)
                thread.join(5);self.assertEqual(received[-1],b'')
                self.assertTrue(fake.fileno()>=0) # no listener/process kill
            finally:fake.close()

if __name__=='__main__':unittest.main()

"""PH-LW-09 real Waitress/TCP and Edge; no Flask test-client substitutes."""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from project_harness.local_web_tasks import view
from tests.test_engine import prepare_demo, implement_first_task
from tests.test_ph_lw_09_tasks import fixture_input, agent_result
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_04_http import HAS_FLASK,HAS_WAITRESS,HAS_PLAYWRIGHT
from tests.test_ph_lw_03_service import byte_snapshot


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS,'Pinned real Waitress required')
class TasksHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='PH LW09 TCP ');self.addCleanup(self.tmp.cleanup)
        self.live=LiveServer(self.tmp.name);self.addCleanup(self.live.close)
        _,_,self.root=prepare_demo(Path(self.tmp.name)/'fixture',data=fixture_input(command=[]))
        self.pid=self.live.service.register_existing(self.root,kind='project');self.live.login();self.base='/api/projects/'+self.pid

    def upload(self,raw,extra=()):
        v=view(self.live.service,self.pid);boundary='HarnessTaskResultBoundary09';chunks=[]
        for key,value in [('binding_digest',v['binding_digest']),('expected_fingerprint',v['fingerprint']),*extra]:
            chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        chunks.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="result"; filename="result.json"\r\nContent-Type: application/json\r\n\r\n'.encode(),raw,b'\r\n',f'--{boundary}--\r\n'.encode()])
        return self.live.request('POST',self.base+'/tasks/result-upload',data=b''.join(chunks),headers={'Content-Type':'multipart/form-data; boundary='+boundary})

    def test_http_auth_origin_csrf_exact_fields_get_no_mutation(self):
        live=self.live;before=byte_snapshot(self.root)
        self.assertEqual(live.request('GET',self.base+'/tasks',authenticated=False)[0],401)
        for headers in ({'Host':'localhost:'+str(live.port)},{'Origin':'null'},{'Origin':'http://127.0.0.1:1'},{'X-CSRF-Token':'bad'}):
            self.assertEqual(live.request('POST',self.base+'/tasks/result-upload',value={},headers=headers)[0],403)
            self.assertEqual(live.request('POST',self.base+'/operations',value={},headers=headers)[0],403)
        for _ in range(3):self.assertEqual(live.request('GET',self.base+'/tasks')[0],200)
        self.assertEqual(self.upload(json.dumps(agent_result(self.root)).encode(),extra=[('path','C:\\Windows')])[0],400)
        self.assertEqual(live.request('POST',self.base+'/operations',value={'action':'complete','payload':{'path':'x'},'idempotency_key':'bad-fields-key-123','expected_fingerprint':view(live.service,self.pid)['fingerprint']})[0],400)
        self.assertEqual(before,byte_snapshot(self.root))

    def test_http_forged_result_staging_and_duplicate_click(self):
        implement_first_task(self.root);raw=agent_result(self.root);before=byte_snapshot(self.root)
        self.assertEqual(self.upload(json.dumps({**raw,'run_ref':'RUN-FOREIGN'}).encode())[0],400)
        status,_,staged=self.upload(json.dumps(raw).encode());self.assertEqual(status,201,staged)
        self.assertEqual(before,byte_snapshot(self.root))
        v=view(self.live.service,self.pid);request={'action':'receive-result','payload':{'upload_id':staged['upload_id'],'binding_digest':v['binding_digest']},'idempotency_key':'duplicate-http-task-click','expected_fingerprint':v['fingerprint']}
        first=self.live.request('POST',self.base+'/operations',value=request)
        self.assertEqual(first[0],202,first);opid=first[2]['operation_id']
        op=self.live.service.wait_for(opid,timeout=60);self.assertEqual(op['state'],'SUCCEEDED',op)
        after=byte_snapshot(self.root);second=self.live.request('POST',self.base+'/operations',value=request)
        self.assertEqual(second[2]['operation_id'],opid);self.assertEqual(after,byte_snapshot(self.root))
        self.assertEqual(view(self.live.service,self.pid)['result']['status'],'RESULT_RECEIVED')


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS and HAS_PLAYWRIGHT,'Real pinned Edge required')
class TasksBrowserTests(unittest.TestCase):
    def test_edge_external_agent_result_no_consent_verify_complete_next(self):
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=30000)
        with tempfile.TemporaryDirectory(prefix='PH LW09 Edge Кириллица ') as directory:
            live=LiveServer(directory)
            try:
                _,_,root=prepare_demo(Path(directory)/'fixture',data=fixture_input(manual=True))
                pid=live.service.register_existing(root,kind='project')
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL','msedge'),headless=True)
                    try:
                        context=browser.new_context(viewport={'width':1440,'height':1050});page=context.new_page();page.set_default_timeout(30000)
                        errors=[];urls=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:urls.append(r.url))
                        page.goto(live.origin+'/#bootstrap='+live.auth.issue_bootstrap());expect(page.locator('#session-state')).to_have_text('Сессия активна')
                        page.locator('.project-button').click();page.locator('[data-screen="tasks"]').click()
                        expect(page.locator('#task-copy')).to_be_enabled();old=view(live.service,pid)['active_run']['run_ref']
                        page.locator('#task-copy').click();self.assertIn(old,page.locator('#task-prompt').input_value())
                        before=byte_snapshot(root);page.reload(wait_until='networkidle');expect(page.locator('#task-copy')).to_be_enabled();self.assertEqual(before,byte_snapshot(root))
                        # Explicit fixture external agent: real product writes only. No canonical editing.
                        implement_first_task(root);page.locator('#refresh').click();expect(page.locator('#task-upload')).to_be_enabled()
                        raw=agent_result(root);raw['summary']='<img src="https://forbidden.invalid/x" onerror="alert(1)"> fixture'
                        page.locator('#task-result-file').set_input_files({'name':'Agent Result.json','mimeType':'application/json','buffer':json.dumps(raw).encode()})
                        page.locator('#task-upload').click();expect(page.locator('#task-result-state')).to_contain_text('RESULT_RECEIVED')
                        self.assertFalse(page.locator('#task-consent').is_checked());expect(page.locator('#task-complete')).to_be_disabled()
                        page.locator('#task-verify').click();expect(page.locator('#task-verification')).to_contain_text('BLOCKED');expect(page.locator('#task-complete')).to_be_disabled()
                        page.locator('#task-manual-panel summary').click()
                        page.locator('#task-manual-reviewer').fill('ACT-EDGE-INDEPENDENT-REVIEWER')
                        page.locator('#task-manual-checks textarea').fill('Inspected fixture CLI parsing, add/list output and persistence. <img src="https://forbidden.invalid/review"> remains inert review text.')
                        page.locator('#task-manual-checks [data-field=status]').select_option('PASS')
                        page.locator('#task-manual-checks [data-field=sources]').select_option(['task_cli.py'])
                        page.locator('#task-manual-confirm').check();page.locator('#task-manual-submit').click()
                        expect(page.locator('#task-manual-state')).to_contain_text('ACT-EDGE-INDEPENDENT-REVIEWER')
                        self.assertFalse(page.locator('#task-manual-confirm').is_checked())
                        expect(page.locator('#task-complete')).to_be_disabled()
                        page.locator('#task-consent').check();page.locator('#task-verify').click();expect(page.locator('#task-complete')).to_be_enabled(timeout=60000)
                        self.assertFalse(page.locator('#task-consent').is_checked());expect(page.locator('#task-verification')).to_contain_text('PASS')
                        screen=Path(os.environ.get('PH_LW_09_SCREENSHOT_DIR',str(Path(directory)/'screenshots')));screen.mkdir(parents=True,exist_ok=True)
                        page.screenshot(path=str(screen/'task-verified.png'),full_page=True)
                        page.locator('#task-complete').click();expect(page.locator('#tasks-summary')).to_contain_text('завершено: 1')
                        expect(page.locator('#task-prompt')).not_to_have_value('');new=view(live.service,pid)['active_run']['run_ref'];self.assertNotEqual(old,new)
                        page.locator('#task-next').click();expect(page.locator('#task-next')).to_be_enabled();self.assertEqual(new,view(live.service,pid)['active_run']['run_ref'])
                        page.screenshot(path=str(screen/'next-task.png'),full_page=True)
                        self.assertFalse(errors,errors);self.assertTrue(all(url.startswith(live.origin) for url in urls),urls)
                    finally:browser.close()
            finally:live.close()

    def test_edge_failing_check_block_resume_exact_ref(self):
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=30000)
        import sys
        with tempfile.TemporaryDirectory(prefix='PH LW09 Fail Edge ') as directory:
            live=LiveServer(directory)
            try:
                _,_,root=prepare_demo(Path(directory)/'fixture',data=fixture_input(command=[{'argv':[sys.executable,'-c','raise SystemExit(9)'],'cwd':'.','timeout_seconds':10}]))
                pid=live.service.register_existing(root,kind='project');implement_first_task(root)
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL','msedge'),headless=True)
                    try:
                        page=browser.new_page(viewport={'width':1400,'height':1000});page.set_default_timeout(30000)
                        page.goto(live.origin+'/#bootstrap='+live.auth.issue_bootstrap());expect(page.locator('#session-state')).to_have_text('Сессия активна')
                        page.locator('.project-button').click();page.locator('[data-screen="tasks"]').click();expect(page.locator('#task-upload')).to_be_enabled()
                        old=view(live.service,pid)['active_run']['run_ref']
                        page.locator('#task-result-file').set_input_files({'name':'result.json','mimeType':'application/json','buffer':json.dumps(agent_result(root)).encode()})
                        page.locator('#task-upload').click();expect(page.locator('#task-verify')).to_be_enabled()
                        page.locator('#task-consent').check();page.locator('#task-verify').click();expect(page.locator('#task-verification')).to_contain_text('FAIL')
                        expect(page.locator('#task-complete')).to_be_disabled();page.get_by_text('Block / resume и восстановление',exact=True).click()
                        page.locator('#task-reason').fill('Fixture test exit 9 requires correction');page.locator('#task-block').click()
                        expect(page.locator('#task-resume')).to_be_enabled();expect(page.locator('#task-blocker-ref option')).to_have_count(1)
                        page.locator('#task-resolution').fill('Explicit retry after fixture investigation');page.locator('#task-resume').click()
                        expect(page.locator('#task-copy')).to_be_enabled();self.assertNotEqual(old,view(live.service,pid)['active_run']['run_ref'])
                        expect(page.locator('#task-result-state')).to_contain_text('NOT_RECEIVED')
                    finally:browser.close()
            finally:live.close()

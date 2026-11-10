"""Direct local access with no login state, cookies or CSRF machinery."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_05_import import archive
from tests.test_ph_lw_03_service import byte_snapshot


class LocalWebNoLoginTests(unittest.TestCase):
    def test_plain_http_read_create_and_removed_login_endpoints(self):
        with tempfile.TemporaryDirectory(prefix='no-login-api-') as directory:
            live=LiveServer(directory)
            try:
                self.assertEqual(live.request('GET','/api/projects')[0],200)
                pid=live.create('direct-no-login-create-001')
                response=live.upload(pid,[('requirements.md',b'# local requirements')])
                self.assertEqual(response[0],200,response[2])
                self.assertNotIn('Set-Cookie',response[1])
                for route in ('/api/session','/api/session/bootstrap','/api/session/logout'):
                    self.assertEqual(live.request('GET',route)[0],404)
                    self.assertEqual(live.request('POST',route,value={})[0],404)
                view=live.request('GET',f'/api/projects/{pid}')[2]['project']
                stale={'action':'check-intake','payload':{},'expected_fingerprint':'sha256:'+'0'*64,
                       'idempotency_key':'no-login-stale-mutation-001'}
                self.assertEqual(live.request('POST',f'/api/projects/{pid}/operations',value=stale)[0],409)
                self.assertEqual(view['fingerprint'],live.request('GET',f'/api/projects/{pid}')[2]['project']['fingerprint'])
            finally:live.close()

    def test_fresh_browser_cookie_clear_reload_and_new_tab_need_no_login(self):
        from playwright.sync_api import sync_playwright,expect
        with tempfile.TemporaryDirectory(prefix='no-login-browser-') as directory:
            live=LiveServer(directory)
            try:
                with sync_playwright() as play:
                    browser=play.chromium.launch(channel='msedge',headless=True)
                    try:
                        context=browser.new_context();page=context.new_page();requests=[]
                        page.on('request',lambda r:requests.append((r.url,r.headers)))
                        page.on('dialog',lambda d:d.accept())
                        page.goto(live.origin+'/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        self.assertEqual(page.locator('#session-gate,#manual-login,#manual-bootstrap,#logout').count(),0)
                        page.locator('[data-screen="documents"]').click()
                        page.locator('#new-project-name').fill('Прямой доступ')
                        page.locator('#create-intake').click()
                        expect(page.locator('#source-summary')).to_contain_text('Revision 0')
                        page.locator('#source-files').set_input_files({'name':'Документы.zip','mimeType':'application/zip',
                            'buffer':archive([('Требования.md','# Требования'.encode())])})
                        page.locator('#upload-sources').click()
                        expect(page.locator('#upload-result')).to_contain_text('Принято: 1')
                        context.clear_cookies();page.reload()
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        expect(page.locator('#source-summary')).to_contain_text('Revision 1')
                        self.assertEqual(context.cookies(),[])
                        other=context.new_page();other.goto(live.origin+'/')
                        expect(other.locator('#connection-state')).to_have_text('Сервер готов')
                        for url,headers in requests:
                            self.assertTrue(url.startswith(live.origin+'/'))
                            self.assertNotIn('/api/session',url)
                            self.assertNotIn('x-csrf-token',headers)
                            self.assertNotIn('cookie',headers)
                        screenshots=os.environ.get('NO_LOGIN_SCREENSHOTS')
                        if screenshots:
                            Path(screenshots).mkdir(parents=True,exist_ok=True)
                            page.screenshot(path=str(Path(screenshots)/'direct-documents.png'),full_page=True)
                    finally:browser.close()
            finally:live.close()

    def test_restart_retains_project_without_session_and_gets_are_readonly(self):
        with tempfile.TemporaryDirectory(prefix='no-login-restart-') as directory:
            live=LiveServer(directory)
            try:
                pid=live.create('direct-restart-create-001')
                self.assertEqual(live.upload(pid,[('doc.md',b'# document')])[0],200)
            finally:live.close()
            live=LiveServer(directory)
            try:
                before=byte_snapshot(Path(directory))
                self.assertEqual(live.request('GET',f'/api/projects/{pid}')[0],200)
                self.assertEqual(live.request('GET',f'/api/projects/{pid}/sources')[2]['source_revision'],1)
                self.assertEqual(before,byte_snapshot(Path(directory)))
            finally:live.close()

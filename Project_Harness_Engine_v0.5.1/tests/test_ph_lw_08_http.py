"""Production Waitress/TCP + Edge: full MD/ZIP to real Project Instance."""
from __future__ import annotations
import json
import zipfile
import os
import re
from pathlib import Path
import tempfile
import unittest

from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_04_http import HAS_FLASK, HAS_WAITRESS, HAS_PLAYWRIGHT
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_05_import import archive
from tests.test_ph_lw_06_http import fixture_reply
from project_harness.project_input import approvals_for_mode
from project_harness.serialization import load_data
from project_harness.validation import validate_handoff, validate_project_directory


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS, 'Real pinned Flask/Waitress required')
class PreparationHttpTests(unittest.TestCase):
    def test_all_routes_auth_origin_host_csrf_unknown_fields_no_writes(self):
        with tempfile.TemporaryDirectory(prefix='ph-lw08-http-') as directory:
            live=LiveServer(directory)
            try:
                live.service.projects_directory=Path(directory)/'Проекты'
                live.ready();pid=live.create();base='/api/projects/'+pid
                before=byte_snapshot(Path(directory))
                for route in ('/preparation','/preparation/LWO-'+'A'*32+'/prompt'):
                    self.assertEqual(live.request('GET',base+route,headers={'Origin':'http://foreign.invalid'})[0],403)
                self.assertEqual(live.request('GET',base+'/preparation')[0],200)
                for route in ('target','start','recover','open-folder'):
                    for headers in ({'Origin':'null'},{'Origin':'http://127.0.0.1:1'},
                                    {'Host':'localhost:'+str(live.port)}):
                        self.assertEqual(live.request('POST',base+'/preparation/'+route,value={},headers=headers)[0],403)
                    self.assertEqual(live.request('POST',base+'/preparation/'+route,value={},headers={'Origin':'http://foreign.invalid'})[0],403)
                    self.assertEqual(live.request('POST',base+'/preparation/'+route,value={'path':'C:\\Windows'})[0],400)
                self.assertEqual(before,byte_snapshot(Path(directory)))
            finally:live.close()


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS and HAS_PLAYWRIGHT, 'Real Edge required')
class PreparationBrowserTests(unittest.TestCase):
    def test_edge_single_md_and_zip_full_flow_reconnect_first_jit_and_download(self):
        from playwright.sync_api import sync_playwright,expect
        with tempfile.TemporaryDirectory(prefix='PH LW08 Кириллица ') as directory:
            live=LiveServer(directory)
            live.service.projects_directory=Path(directory)/'Готовые проекты'
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL','msedge'),headless=True)
                    try:
                        context=browser.new_context(viewport={'width':1440,'height':1100},accept_downloads=True)
                        page=context.new_page();page.set_default_timeout(20000)
                        urls,errors,app_urls=[],[],[]
                        context.on('request',lambda r:urls.append(r.url));context.on('weberror',lambda e:errors.append(str(e)))
                        page.on('request',lambda r:app_urls.append(r.url))
                        page.on('dialog',lambda d:d.accept())
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        for zipped in (False,True):
                            page.locator('[data-screen="documents"]').click()
                            page.locator('#new-project-name').fill('Подготовка '+str(zipped))
                            page.locator('#create-intake').click()
                            expect(page.locator('#source-summary')).to_contain_text('Revision 0')
                            upload={'name':'Документ.md','mimeType':'text/markdown','buffer':b'# Fixture source'}
                            if zipped:upload={'name':'Документы.zip','mimeType':'application/zip',
                                'buffer':archive([('Раздел/Требования.md',b'# Fixture source'),('skip.png',b'image')])}
                            page.locator('#source-files').set_input_files(upload);page.locator('#upload-sources').click()
                            expect(page.locator('#upload-result')).to_contain_text('Принято: 1')
                            page.locator('[data-screen="interview"]').click()
                            expect(page.locator('#interview-body')).to_be_visible()
                            page.locator('#answer-implementation-target_level').select_option('MVP')
                            page.locator('#save-answers').click()
                            expect(page.locator('#notice')).to_contain_text('Ответы проверены и сохранены')
                            self.assertEqual(page.locator('#export-review').count(),0)
                            
                            with page.expect_download() as download:page.locator('#review-export').click()
                            expect(page.locator('#review-export')).to_be_enabled()
                            self.assertEqual(page.locator('#export-history').count(),0)
                            with zipfile.ZipFile(download.value.path()) as z:pack=z.read('pack.md').decode('utf-8')
                            reply=fixture_reply(json.loads(pack.split('## Return skeleton\n\n',1)[1]))
                            page.locator('#gpt-reply').fill(json.dumps(reply,ensure_ascii=False))
                            page.locator('#preview-reply').click();expect(page.locator('#import-preview')).to_be_visible()
                            page.locator('#commit-reply').click();expect(page.locator('#import-history')).to_contain_text('COMMITTED')
                            page.locator('[data-screen="approvals"]').click()
                            expect(page.locator('#approval-subjects section')).to_have_count(4)
                            page.locator('#approval-actor').fill('Оператор Windows Edge');page.locator('#save-approval-actor').click()
                            expect(page.locator('#approval-actor-display')).to_contain_text('Оператор Windows Edge')
                            for i,subject in enumerate(approvals_for_mode('GREENFIELD')):
                                page.locator('#approve-'+subject).click()
                                expect(page.locator('#approvals-status')).to_contain_text(f'{i+1} из 4')
                            expect(page.locator('#preparation-form')).to_be_visible()
                            name='Реальная папка '+str(zipped)
                            page.locator('#project-folder-name').fill(name);
                            with page.expect_response(lambda r:r.url.endswith('/preparation/start')) as started:
                                page.locator('#prepare-project').click()
                            self.assertEqual(started.value.status,202,started.value.text())
                            # Browser disconnect while worker continues; reload uses GET-only recovery projection.
                            page.reload(wait_until='networkidle')
                            expect(page.locator('#preparation-complete')).to_be_visible(timeout=180000)
                            destination=live.service.projects_directory/name
                            self.assertTrue(destination.is_dir())
                            expect(page.locator('#published-folder')).to_have_text(str(destination))
                            expect(page.locator('#published-refs')).to_contain_text('Target: MVP')
                            self.assertEqual(validate_project_directory(destination)['status'],'PASS')
                            first=load_data(destination/'.harness/state/HANDOFF_RESULT.json')
                            expect(page.locator('#published-refs')).to_contain_text(first['first_run_ref'])
                            self.assertIn(first['first_task_ref'],page.locator('#first-prompt').input_value())
                            # Real browser clipboard fallback: field remains selectable if permission is absent.
                            page.locator('#copy-first-prompt').click()
                            expect(page.locator('#notice')).to_contain_text(re.compile('Первый JIT скопирован|Промпт выделен'))
                            with page.expect_download() as download:page.locator('#download-handoff').click()
                            output=Path(directory)/('browser-handoff-'+str(zipped)+'.zip')
                            download.value.save_as(output)
                            self.assertEqual(validate_handoff(output)['status'],'PASS')
                            snapshot=byte_snapshot(destination)
                            page.reload(wait_until='networkidle');expect(page.locator('#preparation-complete')).to_be_visible()
                            self.assertEqual(snapshot,byte_snapshot(destination))
                            screenshots=os.environ.get('PH_LW_08_SCREENSHOT_DIR')
                            if screenshots:
                                Path(screenshots).mkdir(parents=True,exist_ok=True)
                                page.locator('#preparation-complete').screenshot(path=str(Path(screenshots)/('prepared-'+str(zipped)+'.png')))
                        page.locator('[data-screen="projects"]').click()
                        page.locator('#refresh').click()
                        page.locator('.project-button').filter(has_text='Проект ·').last.click()
                        expect(page.locator('#project-kind')).to_have_text('Project Instance')
                        expect(page.get_by_role('button',name='Подготовить handoff',exact=True)).to_be_disabled()
                        self.assertFalse(errors,errors)
                        self.assertTrue(all(u.startswith(live.origin+'/') for u in app_urls),app_urls)
                        # Edge's own downloads-hub/fileicon pages are browser UI,
                        # not external network requests from the application.
                        self.assertTrue(all(u.startswith(live.origin+'/') for u in urls if u.startswith(('http:','https:'))),urls)
                    finally:browser.close()
            finally:live.close()


if __name__=='__main__':unittest.main()

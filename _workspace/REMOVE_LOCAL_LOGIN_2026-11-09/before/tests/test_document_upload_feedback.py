"""Document upload guidance through real Waitress/TCP and headless Edge."""
from __future__ import annotations
import os
from pathlib import Path
import tempfile
import threading
import unittest

from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_04_http import HAS_FLASK, HAS_WAITRESS, HAS_PLAYWRIGHT
from tests.test_ph_lw_05_import import archive


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS and HAS_PLAYWRIGHT, 'Real Waitress and Edge required')
class DocumentUploadFeedbackTests(unittest.TestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright, expect
        self.expect = expect
        self.temp = tempfile.TemporaryDirectory(prefix='upload-feedback-')
        self.addCleanup(self.temp.cleanup)
        self.live = LiveServer(self.temp.name)
        self.addCleanup(self.live.close)
        self.pw = sync_playwright().start()
        self.addCleanup(self.pw.stop)
        self.browser = self.pw.chromium.launch(channel='msedge', headless=True)
        self.addCleanup(self.browser.close)
        self.page = self.browser.new_page(viewport={'width':1360,'height':1000})
        self.page.set_default_timeout(15000)
        self.errors, self.requests = [], []
        self.page.on('pageerror', lambda error:self.errors.append(str(error)))
        self.page.on('request',lambda request:self.requests.append((request.method,request.url)))
        self.page.on('dialog',lambda dialog:dialog.accept())
        self.page.goto(self.live.origin+'/#bootstrap='+self.live.auth.issue_bootstrap())
        expect(self.page.locator('#session-state')).to_have_text('Сессия активна')
        self.page.locator('[data-screen="documents"]').click()
        self.addCleanup(self.check_browser)

    def check_browser(self):
        self.assertFalse(self.errors)
        self.assertTrue(all(url.startswith(self.live.origin+'/') for _,url in self.requests))

    def choose(self, data=None, name='Документация.zip'):
        if data is None:
            data=archive([('Раздел/Требования.md','# Требования'.encode()),('картинка.png',b'image')])
        self.page.locator('#source-files').set_input_files({'name':name,'mimeType':'application/zip','buffer':data})

    def create(self, name='Проект загрузки', no_docs=False):
        self.page.locator('#new-project-name').fill(name)
        self.page.locator('#create-no-docs' if no_docs else '#create-intake').click()
        self.expect(self.page.locator('#source-summary')).to_contain_text('NONE' if no_docs else 'Revision 0')
        self.expect(self.page.locator('#confirm-no-docs')).to_be_enabled()

    def upload(self, revision=1):
        self.expect(self.page.locator('#upload-sources')).to_be_enabled()
        self.page.locator('#upload-sources').click()
        self.expect(self.page.locator('#upload-result')).to_contain_text(f'ревизия: {revision}',timeout=30000)
        self.expect(self.page.locator('#upload-step-title')).to_contain_text('Документы загружены: 1 MD')
        self.expect(self.page.locator('#documents-next')).to_be_enabled()

    def test_choose_before_project_import_and_explicit_next(self):
        self.choose()
        self.expect(self.page.locator('#upload-step-title')).to_contain_text('Сначала создайте или выберите проект')
        self.expect(self.page.locator('#upload-sources')).to_be_enabled()
        self.page.locator('#upload-sources').click()
        self.expect(self.page.locator('#document-validation')).to_contain_text('Введите название проекта')
        self.assertFalse(any(url.endswith('/sources/upload') for _,url in self.requests))
        self.create()
        self.expect(self.page.locator('#upload-step-title')).to_have_text('Файлы выбраны — загрузка ещё не началась')
        self.expect(self.page.locator('#documents-next')).to_be_enabled()
        self.page.locator('#documents-next').click()
        self.expect(self.page.locator('#document-validation')).to_contain_text('ещё не импортированы')
        self.upload()
        self.expect(self.page.locator('#upload-result')).to_contain_text('пропущено: 1')
        self.expect(self.page.locator('#upload-step-detail')).to_contain_text('Анализ и согласования выполняются отдельно')
        screenshots=os.environ.get('DOCUMENT_UPLOAD_SCREENSHOTS')
        if screenshots:
            Path(screenshots).mkdir(parents=True,exist_ok=True)
            self.page.screenshot(path=str(Path(screenshots)/'imported.png'),full_page=True)
        self.page.locator('#documents-next').click()
        self.expect(self.page.locator('#interview-panel')).to_be_visible()
        self.expect(self.page.locator('#interview-body')).to_be_visible()

    def test_reload_duplicate_and_switch_to_empty_project(self):
        self.create();self.choose();self.upload()
        self.page.reload()
        self.expect(self.page.locator('#upload-step-title')).to_contain_text('Документы загружены: 1 MD')
        self.expect(self.page.locator('#documents-next')).to_be_enabled()
        self.choose();self.upload(revision=1)
        self.expect(self.page.locator('#upload-result')).to_contain_text('уже загружены')
        self.create('Другой пустой проект')
        self.expect(self.page.locator('#upload-step-title')).to_have_text('Проект готов к загрузке документов')
        self.expect(self.page.locator('#documents-next')).to_be_enabled()
        self.page.locator('#documents-next').click()
        self.expect(self.page.locator('#document-validation')).to_contain_text('Сначала загрузите документацию')
        self.expect(self.page.locator('#source-list')).to_be_empty()

    def test_rejected_zip_preserves_sources_and_can_retry(self):
        self.create();self.choose();self.upload()
        self.choose(archive([('../escape.md',b'unsafe')]),'Опасный.zip')
        self.page.locator('#upload-sources').click()
        self.expect(self.page.locator('#upload-step-title')).to_have_text('Импорт не подтверждён')
        self.expect(self.page.locator('#documents-next')).to_be_enabled()
        self.page.locator('#documents-next').click()
        self.expect(self.page.locator('#document-validation')).to_contain_text('ещё не импортированы')
        self.expect(self.page.locator('#source-summary')).to_contain_text('Revision 1')
        self.expect(self.page.locator('#source-list .source-item')).to_have_count(1)
        self.page.locator('#clear-source-files').click()
        self.expect(self.page.locator('#documents-next')).to_be_enabled()
        self.choose();self.upload(revision=1)

    def test_no_documentation_has_explicit_next(self):
        self.create(no_docs=True)
        self.expect(self.page.locator('#upload-step-title')).to_have_text('Подтверждено: документации нет')
        self.expect(self.page.locator('#documents-next')).to_be_enabled()
        self.page.locator('#documents-next').click()
        self.expect(self.page.locator('#interview-body')).to_be_visible()

    def test_transfer_finished_is_still_validation_not_success(self):
        self.create();self.choose()
        entered,release=threading.Event(),threading.Event()
        original=self.live.service.upload_sources
        def held(*args,**kwargs):
            entered.set()
            if not release.wait(15):
                raise RuntimeError('Test timing latch expired')
            return original(*args,**kwargs)
        self.live.service.upload_sources=held
        try:
            self.page.locator('#upload-sources').click()
            self.assertTrue(entered.wait(10))
            self.expect(self.page.locator('#upload-step-title')).to_have_text('Файлы переданы. Проверяем архив и документы…')
            self.expect(self.page.locator('#upload-sources')).to_be_disabled()
            self.expect(self.page.locator('#documents-next')).to_be_disabled()
            self.assertIsNone(self.page.locator('#upload-progress').get_attribute('value'))
        finally:
            release.set()
        self.expect(self.page.locator('#upload-step-title')).to_contain_text('Документы загружены: 1 MD',timeout=30000)

    def test_lost_response_after_commit_refresh_recovers_without_reposting(self):
        self.create();self.choose()
        def lose_response(route):
            response=route.fetch()
            self.assertEqual(response.status,200)
            route.abort('connectionreset')
        self.page.route('**/sources/upload',lose_response)
        self.page.locator('#upload-sources').click()
        self.expect(self.page.locator('#upload-step-title')).to_have_text('Не удалось получить результат загрузки')
        self.page.unroute('**/sources/upload',lose_response)
        self.page.reload()
        self.expect(self.page.locator('#upload-step-title')).to_contain_text('Документы загружены: 1 MD')
        self.expect(self.page.locator('#source-summary')).to_contain_text('Revision 1')
        uploads=[url for method,url in self.requests if method=='POST' and url.endswith('/sources/upload')]
        self.assertEqual(len(uploads),1)
        self.expect(self.page.locator('#documents-next')).to_be_enabled()


if __name__=='__main__':
    unittest.main(verbosity=2)

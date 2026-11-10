"""Two new browser choices and automatic result, no classification forms."""
import os
from pathlib import Path
import unittest
from tests import test_cli_document_analysis as cli_tests


class CliDocumentUiTests(unittest.TestCase):
    setUp=cli_tests.CliAnalysisTests.setUp
    def open_page(self):
        from playwright.sync_api import sync_playwright,expect
        self.expect=expect;self.play=sync_playwright().start();self.addCleanup(self.play.stop)
        self.browser=self.play.chromium.launch(channel='msedge',headless=True);self.addCleanup(self.browser.close)
        self.page=self.browser.new_page(viewport={'width':1360,'height':1000})
        self.errors=[];self.dialogs=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('dialog',lambda d:(self.dialogs.append(d.message),d.dismiss()))
        self.page.goto(self.live.origin+'/')
        expect(self.page.locator('#connection-state')).to_have_text('Сервер готов')
        self.page.locator('.project-button').filter(has_text=self.pid).click()
        self.page.locator('[data-screen="interview"]').click()
        expect(self.page.locator('#cli-connect')).to_be_visible()
        self.addCleanup(lambda:self.assertEqual(self.errors,[]))
        self.addCleanup(lambda:self.assertEqual(self.dialogs,[]))

    def capture(self,name):
        folder=os.environ.get('CLI_DOCUMENT_SCREENSHOTS')
        if folder:
            Path(folder).mkdir(parents=True,exist_ok=True)
            self.page.screenshot(path=str(Path(folder)/name),full_page=True)

    def test_browser_manual_pack_one_click_and_persisted_connection(self):
        self.open_page();p=self.page;e=self.expect
        e(p.locator('#cli-analysis-title')).to_have_text('Автоматически через Codex CLI')
        e(p.locator('#manual-analysis-title')).to_have_text('Вручную через ChatGPT или Codex')
        self.assertEqual(p.locator('#export-review,#export-documents,#draft-classification,#export-consent').count(),0)
        self.assertEqual(self.fake.calls,[])
        with p.expect_download() as download:p.locator('#review-export').click()
        e(p.locator('#review-export')).to_be_enabled()
        self.assertEqual(p.locator('#export-history').count(),0)
        self.assertEqual(download.value.suggested_filename,'harness-analysis.zip')
        self.assertEqual(self.fake.calls,[])
        p.locator('#cli-connect').click()
        e(p.locator('#cli-connection-status')).to_have_text('Codex CLI подключён.')
        self.assertEqual(len(self.fake.calls),3)
        p.reload();e(p.locator('#cli-connection-status')).to_have_text('Codex CLI подключён.')
        self.assertEqual(len(self.fake.calls),3)
        self.capture('01-two-analysis-choices.png')

    def test_browser_cli_progress_reload_cancel_and_result_without_copying_json(self):
        self.open_page();p=self.page;e=self.expect
        self.fake.mode='slow';p.locator('#cli-analyze').click()
        e(p.locator('#cli-analysis-cancel')).to_be_visible()
        self.assertTrue(self.fake.started.wait(3))
        p.reload();e(p.locator('#cli-analysis-cancel')).to_be_visible()
        self.assertEqual(sum('--output-last-message' in call for call in self.fake.calls),1)
        p.locator('#cli-analysis-cancel').click()
        e(p.locator('#cli-analysis-status')).to_contain_text('остановлен',timeout=15000)
        self.fake.mode='ok'
        p.locator('#cli-analyze').click()
        e(p.locator('#preview-summary')).to_contain_text('Изменений:',timeout=20000)
        e(p.locator('#cli-analysis-status')).to_contain_text('Анализ завершён')
        e(p.locator('#gpt-reply')).to_have_value('')
        p.locator('#commit-reply').click()
        e(p.locator('#known-answers')).to_contain_text('Результат из подключённого CLI')
        e(p.locator('#known-answers')).to_contain_text('Предложено моделью')
        self.capture('02-cli-result-in-browser.png')

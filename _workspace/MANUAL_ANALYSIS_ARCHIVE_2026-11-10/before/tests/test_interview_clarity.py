"""Two changed interview UI paths; synthetic documents and model reply only."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_05_import import archive
from tests.test_ph_lw_06_http import fixture_reply


class InterviewClarityTests(unittest.TestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright,expect
        self.expect=expect;self.temp=tempfile.TemporaryDirectory(prefix='interview-clarity-')
        self.addCleanup(self.temp.cleanup)
        self.live=LiveServer(self.temp.name);self.addCleanup(self.live.close)
        self.pid=self.live.create('interview-clarity-fixture-001')
        self.assertEqual(self.live.upload(self.pid,[('Документы.zip',archive([(f'{i}_Требования.md',f'# Требования {i}'.encode()) for i in range(1,5)]))])[0],200)
        self.play=sync_playwright().start();self.addCleanup(self.play.stop)
        self.browser=self.play.chromium.launch(channel='msedge',headless=True);self.addCleanup(self.browser.close)
        self.page=self.browser.new_page(viewport={'width':1360,'height':1000},accept_downloads=True)
        self.errors=[];self.dialogs=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('dialog',lambda d:(self.dialogs.append(d.message),d.dismiss()))
        self.page.goto(self.live.origin+'/')
        expect(self.page.locator('#connection-state')).to_have_text('Сервер готов')
        self.page.locator('.project-button').filter(has_text=self.pid).click()
        self.page.locator('[data-screen="interview"]').click()
        expect(self.page.locator('#interview-status')).to_contain_text('Документы загружены')
        self.addCleanup(self.check_page)

    def check_page(self):
        self.assertEqual(self.errors,[]);self.assertEqual(self.dialogs,[])

    def screenshot(self,name):
        target=os.environ.get('INTERVIEW_CLARITY_SCREENSHOTS')
        if target:
            Path(target).mkdir(parents=True,exist_ok=True)
            self.page.screenshot(path=str(Path(target)/name),full_page=True)

    def test_uploaded_documents_show_next_step_without_template_facts_or_hashes(self):
        p=self.page;e=self.expect
        e(p.locator('#interview-next')).to_contain_text('автоматический анализ через CLI')
        e(p.locator('#interview-documents')).to_contain_text('Загружено документов: 4')
        button=p.locator('#review-export');e(button).to_have_text('Сформировать пакет вручную')
        self.assertLess(button.bounding_box()['y'],850,'The next action must be visible before the questionnaire')
        main=p.locator('#interview-panel').inner_text()
        for term in ('sha256:','LMD-','LOCAL_DRAFT_UNVERIFIED','PRAGMATIC','skills.resolutions','source revision','WAITING_INPUT','provenance','readiness'):
            self.assertNotIn(term,main)
        self.assertNotIn('GET',p.locator('#notice').inner_text())
        p.locator('#known-answers').locator('..').locator('summary').click()
        e(p.locator('#known-answers')).to_contain_text('Пока нет заполненных сведений')
        self.assertEqual(p.locator('#known-answers .known-answer').count(),0)
        p.locator('#interview-technical summary').click()
        e(p.locator('#interview-readiness')).to_contain_text('sha256:')
        e(p.locator('#interview-readiness')).to_contain_text('skills.resolutions')
        p.locator('#interview-technical summary').click()
        p.locator('#known-answers').locator('..').locator('summary').click()
        self.screenshot('01-next-step.png')

    def test_saved_answer_and_model_proposal_have_clear_origins_and_exchange_still_works(self):
        p=self.page;e=self.expect
        p.locator('#answer-project-primary_outcome').fill('Понятная цель проекта')
        p.locator('#save-answers').click()
        e(p.locator('#notice')).to_contain_text('Ответы проверены и сохранены')
        p.locator('#known-answers').locator('..').locator('summary').click()
        e(p.locator('#known-answers')).to_contain_text('Понятная цель проекта')
        e(p.locator('#known-answers')).to_contain_text('Сохранено в черновике проекта')
        self.assertEqual(p.locator('#export-review').count(),0)
        self.assertEqual(p.locator('#draft-classification').count(),0)
        
        p.locator('#review-export').click()
        e(p.locator('#export-history a')).to_have_count(1)
        e(p.locator('#interview-next')).to_contain_text('Скачайте пакет')
        self.assertNotIn('sha256:',p.locator('#export-history').inner_text())
        with p.expect_download() as download:p.locator('#export-history a').click()
        pack=Path(download.value.path()).read_text('utf-8')
        skeleton=json.loads(pack.split('## Return skeleton\n\n',1)[1])
        reply=fixture_reply(skeleton)
        reply['project_input_draft']['project']['primary_outcome']='Понятная цель от модели'
        p.locator('#gpt-reply').fill(json.dumps(reply,ensure_ascii=False))
        p.locator('#preview-reply').click()
        e(p.locator('#preview-summary')).to_contain_text('Изменений:')
        self.assertNotIn('sha256:',p.locator('#import-preview').inner_text())
        self.assertNotIn('project.primary_outcome',p.locator('#reply-diff').inner_text())
        p.locator('#commit-reply').click()
        e(p.locator('#notice')).to_contain_text('Предложения сохранены')
        e(p.locator('#known-answers')).to_contain_text('Понятная цель от модели')
        e(p.locator('#known-answers')).to_contain_text('Предложено моделью')
        e(p.locator('#import-history')).to_contain_text('сохранён')
        self.screenshot('02-saved-model-proposal.png')


if __name__=='__main__':unittest.main(verbosity=2)

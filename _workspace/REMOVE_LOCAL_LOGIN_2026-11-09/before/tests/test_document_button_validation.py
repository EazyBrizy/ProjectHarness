"""Active document controls validate before requests; real Waitress/Edge."""
import os
from pathlib import Path
import unittest
from tests import test_document_upload_feedback as feedback
from tests.test_ph_lw_04_http import HAS_FLASK, HAS_WAITRESS, HAS_PLAYWRIGHT


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS and HAS_PLAYWRIGHT, 'Real Waitress and Edge required')
class DocumentButtonValidationTests(unittest.TestCase):
    setUp=feedback.DocumentUploadFeedbackTests.setUp
    check_browser=feedback.DocumentUploadFeedbackTests.check_browser
    choose=feedback.DocumentUploadFeedbackTests.choose
    create=feedback.DocumentUploadFeedbackTests.create
    upload=feedback.DocumentUploadFeedbackTests.upload

    def writes(self):
        return [(method,url) for method,url in self.requests if method=='POST' and not url.endswith('/api/ui/resume')]

    def test_missing_name_all_buttons_active_error_focus_and_no_post(self):
        before=self.writes()
        for button in ('create-intake','create-no-docs','upload-sources','confirm-no-docs','documents-next'):
            with self.subTest(button=button):
                self.expect(self.page.locator('#'+button)).to_be_enabled()
                self.page.locator('#'+button).click()
                self.expect(self.page.locator('#document-validation')).to_be_visible()
                self.expect(self.page.locator('#document-validation')).to_contain_text('название проекта')
                self.expect(self.page.locator('#new-project-name')).to_be_focused()
                self.expect(self.page.locator('#new-project-name')).to_have_attribute('aria-invalid','true')
        self.assertEqual(self.writes(),before)

    def test_selected_zip_and_name_without_project_explains_create(self):
        self.choose();self.page.locator('#new-project-name').fill('Название уже введено')
        before=self.writes()
        self.page.locator('#upload-sources').click()
        self.expect(self.page.locator('#document-validation')).to_contain_text('Проект ещё не создан')
        self.expect(self.page.locator('#create-intake')).to_be_focused()
        self.expect(self.page.locator('#upload-selected')).to_contain_text('Документация.zip')
        self.assertEqual(self.writes(),before)
        screenshots=os.environ.get('DOCUMENT_BUTTON_SCREENSHOTS')
        if screenshots:
            Path(screenshots).mkdir(parents=True,exist_ok=True)
            self.page.screenshot(path=str(Path(screenshots)/'missing-project.png'),full_page=True)

    def test_missing_files_and_no_documentation_decision_do_not_mutate(self):
        self.create()
        before=self.writes()
        self.page.locator('#upload-sources').click()
        self.expect(self.page.locator('#document-validation')).to_contain_text('Выберите ZIP')
        self.expect(self.page.locator('#source-files')).to_be_focused()
        self.page.locator('#documents-next').click()
        self.expect(self.page.locator('#document-validation')).to_contain_text('Сначала загрузите документацию')
        self.expect(self.page.locator('#documents-panel')).to_be_visible()
        self.expect(self.page.locator('#source-summary')).to_contain_text('Revision 0')
        self.assertEqual(self.writes(),before)

    def test_validation_clears_on_correction_then_import_and_next_work(self):
        self.page.locator('#create-intake').click()
        self.expect(self.page.locator('#document-validation')).to_be_visible()
        self.page.locator('#new-project-name').fill('Исправленное название')
        self.expect(self.page.locator('#document-validation')).to_be_hidden()
        self.create('Исправленное название')
        self.page.locator('#upload-sources').click()
        self.expect(self.page.locator('#document-validation')).to_be_visible()
        self.choose()
        self.expect(self.page.locator('#document-validation')).to_be_hidden()
        self.upload()
        self.page.locator('#documents-next').click()
        self.expect(self.page.locator('#interview-body')).to_be_visible()


if __name__=='__main__':
    unittest.main(verbosity=2)

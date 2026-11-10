"""Targeted UI contracts: one action, no extra dialogs or consent controls."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_05_import import archive


class SingleActionUiTests(unittest.TestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright,expect
        self.expect=expect
        self.temp=tempfile.TemporaryDirectory(prefix='single-action-')
        self.addCleanup(self.temp.cleanup)
        self.live=LiveServer(self.temp.name);self.addCleanup(self.live.close)
        self.play=sync_playwright().start();self.addCleanup(self.play.stop)
        self.browser=self.play.chromium.launch(channel='msedge',headless=True)
        self.addCleanup(self.browser.close)
        self.page=self.browser.new_page(viewport={'width':1360,'height':1000})
        self.errors=[];self.dialogs=[];self.posts=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('dialog',lambda d:(self.dialogs.append(d.message),d.dismiss()))
        self.page.on('request',lambda r:self.posts.append(r) if r.method=='POST' else None)
        self.page.goto(self.live.origin+'/')
        expect(self.page.locator('#connection-state')).to_have_text('Сервер готов')
        self.assertEqual(self.page.locator('#lifecycle-confirm,#task-manual-confirm,#task-consent,#export-consent,#confirm-new-folder').count(),0)
        self.addCleanup(self.check_page)

    def check_page(self):
        self.assertEqual(self.dialogs,[])
        self.assertEqual(self.errors,[])

    def test_create_upload_replace_error_export_and_stop_without_confirmations(self):
        p=self.page;e=self.expect
        p.locator('[data-screen="documents"]').click()
        p.locator('#create-intake').click()
        e(p.locator('#document-validation')).to_contain_text('название проекта')
        p.locator('#new-project-name').fill('Single action documents')
        p.locator('#create-intake').click()
        e(p.locator('#source-summary')).to_contain_text('Revision 0')
        p.locator('#upload-sources').click()
        e(p.locator('#document-validation')).to_contain_text('Выберите ZIP')
        def choose(data):p.locator('#source-files').set_input_files({'name':'Документы.zip','mimeType':'application/zip','buffer':data})
        choose(archive([('Требования.md',b'# Requirements')]))
        p.locator('#upload-sources').click()
        e(p.locator('#upload-result')).to_contain_text('Принято: 1')
        e(p.locator('#source-summary')).to_contain_text('Revision 1')
        choose(archive([('../bad.md',b'unsafe')]))
        p.locator('#upload-sources').click()
        e(p.locator('#upload-step-title')).to_have_text('Импорт не подтверждён')
        e(p.locator('#source-summary')).to_contain_text('Revision 1')
        choose(archive([('Новые требования.md',b'# Replacement')]))
        p.locator('#source-import-mode').select_option('replace')
        p.locator('#upload-sources').click()
        e(p.locator('#source-summary')).to_contain_text('Revision 2')
        p.locator('#documents-next').click()
        e(p.locator('#interview-body')).to_be_visible()
        p.locator('#review-export').click()
        e(p.locator('#export-review')).to_be_visible()
        p.locator('#export-documents select').select_option('PUBLIC')
        p.locator('#draft-classification').select_option('PUBLIC')
        p.locator('#create-export').click()
        e(p.locator('#export-history a')).to_have_count(1)
        self.assertTrue(any(r.url.endswith('/gpt/exports') and r.post_data_json['consent'] is True for r in self.posts))
        p.locator('[data-screen="documents"]').click()
        p.locator('#confirm-no-docs').click()
        e(p.locator('#source-summary')).to_contain_text('NONE')
        p.locator('#new-project-name').fill('No docs directly')
        p.locator('#create-no-docs').click()
        e(p.locator('#source-summary')).to_contain_text('NONE')
        screenshots=os.environ.get('SINGLE_ACTION_SCREENSHOTS')
        if screenshots:
            Path(screenshots).mkdir(parents=True,exist_ok=True)
            p.screenshot(path=str(Path(screenshots)/'documents-without-confirmations.png'),full_page=True)
        p.locator('#stop-harness').click()
        e(p.locator('#connection-state')).to_have_text('Сервер остановлен')
        uploads=[r for r in self.posts if r.url.endswith('/sources/upload')]
        self.assertEqual(len(uploads),3)

    def test_decisions_and_folder_action_need_no_extra_checkbox(self):
        from tests.test_ph_lw_07_http import filled_intake
        pid,_=filled_intake(self.live.service,'single-action-review-001')
        p=self.page;e=self.expect
        p.locator('#refresh').click()
        p.locator('.project-button').filter(has_text=pid).click()
        p.locator('[data-screen="approvals"]').click()
        e(p.locator('#approval-subjects section')).to_have_count(4)
        p.locator('#approval-actor').fill('Single action reviewer')
        p.locator('#save-approval-actor').click()
        e(p.locator('#approval-actor-display')).to_contain_text('Single action reviewer')
        subjects=self.live.request('GET',f'/api/projects/{pid}/approvals')[2]['subjects']
        for index,subject in enumerate(subjects):
            self.assertEqual(p.locator('#approval-subjects input[type=checkbox]').count(),0)
            p.locator('#approve-'+subject['subject']).click()
            e(p.locator('#approvals-status')).to_contain_text(f'{index+1} из 4')
        e(p.locator('#preparation-form')).to_be_visible()
        p.locator('#project-folder-name').fill('Direct folder action')
        captured=[]
        def stop_target(route):
            captured.append(route.request.post_data_json)
            route.fulfill(status=409,content_type='application/json',body=json.dumps({'error':{'code':'OPERATION_CONFLICT','message_ru':'UI contract fixture: target request received'}}))
        p.route('**/preparation/target',stop_target)
        p.locator('#prepare-project').click()
        e(p.locator('#notice')).to_contain_text('target request received')
        self.assertEqual(len(captured),1)
        self.assertIs(captured[0]['confirm'],True)
        # No project compilation: only the changed folder-action event is checked.

    def test_task_and_lifecycle_clicks_submit_current_intent_without_checkbox(self):
        p=self.page;e=self.expect
        captured=[]
        def stop_operation(route):
            captured.append(route.request.post_data_json)
            route.fulfill(status=409,content_type='application/json',body=json.dumps({'error':{'code':'OPERATION_CONFLICT','message_ru':'UI contract fixture: action received'}}))
        p.route('**/operations',stop_operation)
        p.evaluate("""() => {
          state.activeProject='LWP-UI-FIXTURE';state.view={kind:'project',fingerprint:'sha256:'+'1'.repeat(64)};selectProject=async()=>{};
          taskView={fingerprint:state.view.fingerprint,binding_digest:'sha256:'+'2'.repeat(64),verification_plan:{digest:'sha256:'+'3'.repeat(64)},manual_evidence:{binding:{checks:[]},product_files:{}}};
          lifecycleView={fingerprint:state.view.fingerprint};lifecycleDraft={action:'level-up',draft_id:'UI-FIXTURE'};lifecycleRead=()=>({target_level:'ALPHA'});
          for (const id of ['task-verify','task-manual-submit','lifecycle-apply']) {
            const b=document.getElementById(id);b.disabled=false;
            for(let el=b;el;el=el.parentElement){el.hidden=false;el.classList.remove('hidden');if(el.tagName==='DETAILS')el.open=true;}
          }
          document.getElementById('task-manual-reviewer').value='UI reviewer';
        }""")
        # Typed fixture views isolate event wiring; HTTP stops each mutation at capture.
        with p.expect_response(lambda r:r.url.endswith('/operations') and r.request.method=='POST'):
            p.locator('#task-verify').click()
        e(p.locator('#notice')).to_contain_text('action received')
        p.wait_for_function('!state.requestBusy')
        self.assertIs(captured[-1]['payload']['consent'],True)
        p.evaluate("state.requestBusy=false;document.getElementById('task-manual-submit').disabled=false")
        with p.expect_response(lambda r:r.url.endswith('/operations') and r.request.method=='POST'):
            p.locator('#task-manual-submit').click()
        p.wait_for_function('!state.requestBusy')
        self.assertIs(captured[-1]['payload']['confirmed'],True)
        p.evaluate("state.requestBusy=false;document.getElementById('lifecycle-apply').disabled=false")
        with p.expect_response(lambda r:r.url.endswith('/operations') and r.request.method=='POST'):
            p.locator('#lifecycle-apply').click()
        p.wait_for_function('!state.requestBusy')
        self.assertIs(captured[-1]['payload']['confirmed'],True)
        self.assertEqual([r['action'] for r in captured],['verify','manual-evidence','level-up'])


if __name__=='__main__':unittest.main(verbosity=2)

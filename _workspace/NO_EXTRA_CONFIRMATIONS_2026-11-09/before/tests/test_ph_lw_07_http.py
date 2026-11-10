"""Real production TCP/Edge approval flows, using declared draft fixtures."""
from __future__ import annotations
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

from project_harness.intake import check_intake, start_intake
from project_harness.local_web_drafts import DRAFT_FIELDS, draft_input_digest, update_provisional_draft
from project_harness.local_web_exchange_contract import get_field
from project_harness.project_input import approvals_for_mode
from project_harness.serialization import load_data, write_data
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_04_http import HAS_FLASK, HAS_WAITRESS, HAS_PLAYWRIGHT
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_engine import load_fixture


def filled_intake(service, key='http-approval-fixture-001'):
    pid = service.create_provisional_intake(project_name='Approval HTTP fixture', no_documentation=True,
        idempotency_key=key)['project_id']
    root = service._registered(pid)[0]
    value = load_fixture()
    values = {f:get_field(value,f) for f in DRAFT_FIELDS}
    values['project.problem_statement'] = '<img src="https://invalid.example/x" onerror="window.injected=1">'
    update_provisional_draft(root, values, expected_input_digest=draft_input_digest(root))
    return pid, root


def request_for(view, subject=None, key=None):
    subject = subject or view['next_subject']
    row = next(r for r in view['subjects'] if r['subject']==subject)
    return {'subject':subject,'decision':'APPROVE','comment':'','review_digest':view['review_digest'],
        'subject_digest':row['subject_digest'],'expected_fingerprint':view['binding']['fingerprint'],
        'idempotency_key':key or 'http-decision-fixture-' + str(len(view['receipts'])), 'confirm':True}


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS, 'Real pinned Flask/Waitress required')
class ApprovalHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ph-lw07-http-'); self.addCleanup(self.temp.cleanup)
        self.live=LiveServer(self.temp.name); self.addCleanup(lambda:self.live.close()); self.live.ready()
        self.pid,self.root=filled_intake(self.live.service)
        self.base=f'/api/projects/{self.pid}'

    def review(self):
        code,_,view=self.live.request('GET',self.base+'/approvals')
        self.assertEqual(code,200,view); return view

    def actor(self):
        return self.live.request('POST',self.base+'/approvals/actor',value={'actor':'HTTP operator',
            'expected_fingerprint':self.review()['binding']['fingerprint']})

    def test_all_routes_exact_origin_session_csrf_methods_no_writes(self):
        before=byte_snapshot(Path(self.temp.name))
        self.assertEqual(self.live.request('GET',self.base+'/approvals',headers={'Origin':'http://foreign.invalid'})[0],403)
        self.review()
        for route in ('/approvals/actor','/approvals/decisions','/approvals/recover'):
            for headers in ({'Origin':'null'},{'Origin':self.live.origin+'/'},{'Origin':'http://127.0.0.1:1'},
                {'Host':'localhost:'+str(self.live.port)},{'Host':'127.0.0.1:1'}):
                self.assertEqual(self.live.request('POST',self.base+route,value={},headers=headers)[0],403)
            self.assertEqual(self.live.request('POST',self.base+route,value={},headers={'Origin':'http://foreign.invalid'})[0],403)
            self.assertEqual(self.live.request('GET',self.base+route)[0],405)
        self.assertEqual(before,byte_snapshot(Path(self.temp.name)))

    def test_four_posts_replay_reload_ready_and_prepare_honestly_pending(self):
        self.assertEqual(self.actor()[0],200)
        for _ in range(4):
            args=request_for(self.review())
            code,_,receipt=self.live.request('POST',self.base+'/approvals/decisions',value=args)
            self.assertEqual(code,200,receipt)
            before=byte_snapshot(Path(self.temp.name))
            self.assertEqual(self.live.request('POST',self.base+'/approvals/decisions',value=args)[2],receipt)
            self.review()
            self.assertEqual(before,byte_snapshot(Path(self.temp.name)))
        self.assertEqual(check_intake(self.root)['status'],'READY_FOR_HANDOFF')
        self.assertEqual(self.review()['next_action'],'PREPARATION_PENDING_PH_LW_08')
        before=byte_snapshot(Path(self.temp.name))
        code,_,result=self.live.request('POST',self.base+'/operations',value={'action':'prepare','payload':{},
            'idempotency_key':'http-prepare-blocked-001','expected_fingerprint':self.review()['binding']['fingerprint']})
        self.assertEqual(code,409); self.assertEqual(result['error']['code'],'PREPARATION_TARGET_REQUIRED')
        self.assertEqual(before,byte_snapshot(Path(self.temp.name)))

    def test_forged_fields_duplicate_keys_invalid_types_and_stale_digest_rejected(self):
        self.actor(); args=request_for(self.review()); before=byte_snapshot(Path(self.temp.name))
        for fields in ({'actor':'GPT'},{'approved_at':'2099-01-01T00:00:00Z'},{'approved':True},{'path':'C:/outside'}):
            self.assertEqual(self.live.request('POST',self.base+'/approvals/decisions',value={**args,**fields})[0],400)
        for change in ({'confirm':1},{'decision':'APPROVE_ALL'},{'decision':[]},{'subject':[]},{'comment':{}},
                       {'subject_digest':'sha256:'+'0'*64},{'expected_fingerprint':'sha256:'+'0'*64}):
            code,_,body=self.live.request('POST',self.base+'/approvals/decisions',value={**args,**change})
            self.assertIn(code,(400,409),body)
            self.assertNotEqual(body['error']['code'],'INTERNAL_ERROR')
        raw=json.dumps(args)[:-1]+',"confirm":true}'
        self.assertEqual(self.live.request('POST',self.base+'/approvals/decisions',data=raw.encode(),headers={'Content-Type':'application/json'})[0],400)
        self.assertEqual(self.live.request('POST',self.base+'/approvals/recover',value={'confirm':False})[0],400)
        self.assertEqual(before,byte_snapshot(Path(self.temp.name)))

    def test_gpt_actor_timestamp_forgery_cannot_become_local_consent(self):
        review=self.live.service.get_export_review(self.pid)
        export=self.live.service.create_gpt_export(self.pid,expected_fingerprint=review['binding']['fingerprint'],
            review_digest=review['review_digest'],classifications={},draft_classification='INTERNAL',consent=True,
            idempotency_key='http-forgery-export-00001')
        raw=self.live.service.read_gpt_export(self.pid,export['exchange_id'],'pack.md')
        skeleton=json.loads(raw.decode().split('## Return skeleton\n\n')[1])
        for field,value in [('actor','Model'),('approved_at','2026-11-07T00:00:00Z'),('approved',True)]:
            reply=deepcopy(skeleton); reply['project_input_draft']['approvals']['project_definition'][field]=value
            before=byte_snapshot(Path(self.temp.name))
            code,_,result=self.live.request('POST',self.base+'/gpt/replies/preview',value={
                'text':json.dumps(reply),'expected_fingerprint':review['binding']['fingerprint']})
            self.assertEqual(code,422,result); self.assertEqual(result['error']['code'],'APPROVAL_FORGERY')
            self.assertEqual(before,byte_snapshot(Path(self.temp.name)))


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS and HAS_PLAYWRIGHT, 'Real Edge and pinned Playwright required')
class ApprovalBrowserTests(unittest.TestCase):
    def test_edge_four_five_separate_forms_stale_tabs_reload_receipts_and_xss(self):
        from playwright.sync_api import sync_playwright, expect
        with tempfile.TemporaryDirectory(prefix='ph-lw07-edge-') as directory:
            live=LiveServer(directory)
            try:
                pid,root=filled_intake(live.service)
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL','msedge'),headless=True)
                    try:
                        context=browser.new_context(viewport={'width':1440,'height':1000})
                        page=context.new_page(); page.set_default_timeout(15000)
                        urls,errors=[],[]
                        context.on('request',lambda r:urls.append(r.url)); page.on('pageerror',lambda e:errors.append(str(e)))
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        page.locator('.project-button').filter(has_text=pid).click()
                        expect(page.locator('#project-kind')).to_have_text('Черновик')
                        page.locator('[data-screen="approvals"]').click()
                        expect(page.locator('#approval-subjects section')).to_have_count(4)
                        page.locator('#approval-actor').fill('Оператор Edge')
                        page.locator('#save-approval-actor').click()
                        expect(page.locator('#approval-actor-display')).to_contain_text('Оператор Edge')
                        second=context.new_page(); second.goto(live.origin)
                        second.locator('.project-button').filter(has_text=pid).click()
                        expect(second.locator('#project-kind')).to_have_text('Черновик')
                        second.locator('[data-screen="approvals"]').click()
                        expect(second.locator('#approval-subjects section')).to_have_count(4)
                        self.assertEqual(page.locator('#approval-subjects img').count(),0)
                        self.assertIsNone(page.evaluate('window.injected'))
                        page.locator('#approve-project_definition').click()
                        expect(page.locator('#notice')).to_contain_text('Подтвердите')
                        for index,subject in enumerate(approvals_for_mode('GREENFIELD')):
                            page.locator('#confirm-'+subject).check()
                            page.locator('#approve-'+subject).click()
                            expect(page.locator('#approvals-status')).to_contain_text(f'{index+1} из 4')
                            if index==0:
                                second.locator('#confirm-project_definition').check()
                                second.locator('#approve-project_definition').click()
                                expect(second.locator('#notice')).to_contain_text('изменились')
                                self.assertEqual(len(live.service.get_approval_review(pid)['receipts']),1)
                                second.close()
                        expect(page.locator('#approvals-next')).to_contain_text('Проект пока не создан')
                        self.assertEqual(check_intake(root)['status'],'READY_FOR_HANDOFF')
                        before=byte_snapshot(Path(directory)); page.reload(wait_until='networkidle')
                        expect(page.locator('#approvals-status')).to_contain_text('4 из 4')
                        self.assertEqual(before,byte_snapshot(Path(directory)))
                        screenshot_dir=os.environ.get('PH_LW_07_SCREENSHOT_DIR')
                        if screenshot_dir:
                            dest=Path(screenshot_dir); dest.mkdir(parents=True,exist_ok=True)
                            page.screenshot(path=str(dest/'approvals-greenfield.png'),full_page=True)
                        page.locator('#comment-technology_baseline').fill('Проверьте версии')
                        page.locator('#rework-technology_baseline').click()
                        expect(page.locator('#interview-panel')).to_be_visible()
                        # Wait for the new interview response to render, not a
                        # navigation's already-fired networkidle lifecycle event.
                        expect(page.locator('#interview-next')).to_contain_text('Проверьте версии')
                        # Existing Brownfield/Hybrid intake is trusted local registration;
                        # the browser never receives a filesystem path or repository command.
                        for mode in ('BROWNFIELD','HYBRID'):
                            repo=Path(directory)/('repo-'+mode); repo.mkdir(); (repo/'README.md').write_text('# baseline','utf-8')
                            fixture=load_fixture(); fixture['project']['mode']=mode
                            fixture['implementation']['claimed_current_level']='UNKNOWN'
                            fixture['brownfield']['baseline_summary']='Explicit existing baseline fixture'
                            fixture['approvals']={name:{'approved':False,'actor':None,'approved_at':None,'notes':None} for name in approvals_for_mode(mode)}
                            initial=Path(directory)/(mode+'.json'); write_data(initial,fixture)
                            work=Path(directory)/('intake-'+mode)
                            start_intake(work,project_name=mode,mode=mode,repository=repo,initial_input=initial)
                            registered=live.service.register_existing(work,kind='workspace')
                            page.locator('[data-screen="projects"]').click(); page.locator('#refresh').click()
                            page.locator('.project-button').filter(has_text=registered).click()
                            page.locator('[data-screen="approvals"]').click()
                            expect(page.locator('#approval-subjects section')).to_have_count(5)
                            page.locator('#approval-actor').fill('Оператор Edge'); page.locator('#save-approval-actor').click()
                            expect(page.locator('#approval-actor-display')).to_contain_text('Оператор Edge')
                            for index,subject in enumerate(approvals_for_mode(mode)):
                                if subject=='brownfield_baseline': expect(page.locator('#approve-architecture_baseline')).to_be_disabled()
                                page.locator('#confirm-'+subject).check(); page.locator('#approve-'+subject).click()
                                expect(page.locator('#approvals-status')).to_contain_text(f'{index+1} из 5')
                            self.assertEqual(check_intake(work)['status'],'READY_FOR_HANDOFF')
                            if screenshot_dir: page.screenshot(path=str(dest/('approvals-'+mode.lower()+'.png')),full_page=True)
                        self.assertFalse(errors,errors)
                        self.assertTrue(all(url.startswith(live.origin) for url in urls),urls)
                    finally: browser.close()
            finally: live.close()


if __name__ == '__main__': unittest.main()

"""Real loopback Waitress/Edge PH-LW-06 acceptance; synthetic external GPT."""
from __future__ import annotations
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_04_http import HAS_FLASK, HAS_WAITRESS, HAS_PLAYWRIGHT
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_05_import import archive
from tests.test_engine import load_fixture
from project_harness.local_web_drafts import DRAFT_FIELDS
from project_harness.local_web_exchange_contract import get_field


def fixture_reply(skeleton):
    """A declared test fixture, NOT an actual model conversation."""
    value = deepcopy(skeleton)
    fixture = load_fixture()
    for field in sorted(DRAFT_FIELDS):
        if field == 'implementation.target_level':
            continue  # chosen in the typed form
        proposed = get_field(fixture, field)
        if proposed == get_field(value['project_input_draft'], field):
            continue
        current = value['project_input_draft']
        parts = field.split('.')
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = proposed
        value['claims'].append({'field': field, 'source_refs': ['INPUT']})
    return value


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS, 'Real pinned Flask/Waitress required')
class ExchangeHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ph-lw06-http-')
        self.addCleanup(self.temp.cleanup)
        self.live = LiveServer(self.temp.name)
        self.addCleanup(lambda: self.live.close())
        self.live.ready()
        code, _, result = self.live.request('POST', '/api/intakes', value={
            'project_name':'Exchange HTTP fixture', 'no_documentation':True, 'idempotency_key':'http-exchange-create-001'})
        self.assertEqual(code, 201)
        self.pid = result['project_id']; self.base = f'/api/projects/{self.pid}'

    def export(self):
        review = self.live.request('GET', self.base + '/gpt/export-review')[2]
        args = dict(expected_fingerprint=review['binding']['fingerprint'], review_digest=review['review_digest'],
                    classifications={}, draft_classification='PUBLIC', consent=True, idempotency_key='http-export-key-000001')
        code, _, result = self.live.request('POST', self.base + '/gpt/exports', value=args)
        self.assertEqual(code, 200, result)
        raw = self.live.request('GET', self.base + '/gpt/exports/' + result['exchange_id'] + '/pack.md')[2]
        return result, json.loads(raw.decode().split('## Return skeleton\n\n', 1)[1])

    def test_http_security_all_new_routes_and_read_only_gets(self):
        export, reply = self.export()
        reads = ['/interview', '/gpt/export-review', '/gpt/exports/' + export['exchange_id'] + '/pack.md']
        writes = ['/gpt/exports', '/gpt/replies/preview', '/gpt/replies/LWI-'+'A'*32+'/commit',
                  '/gpt/replies/LWI-'+'A'*32+'/cancel', '/gpt/replies/recover']
        before = byte_snapshot(Path(self.temp.name))
        for route in reads:
            self.assertEqual(self.live.request('GET', self.base + route, headers={'Origin':'http://foreign.invalid'})[0], 403)
            self.assertEqual(self.live.request('GET', self.base + route)[0], 200)
        for route in writes:
            for headers in ({'Origin':'null'}, {'Host':'localhost:'+str(self.live.port)},
                            {'Host':'127.0.0.1:1'}, {'Origin':'http://127.0.0.1:1'}):
                self.assertEqual(self.live.request('POST', self.base + route, value={}, headers=headers)[0], 403)
            self.assertEqual(self.live.request('POST', self.base + route, value={}, headers={'Origin':'http://foreign.invalid'})[0], 403)
            self.assertEqual(self.live.request('GET', self.base + route)[0], 405)
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))

    def test_http_negative_then_preview_cancel_commit_replay_and_check_intake(self):
        export, reply = self.export()
        view = self.live.request('GET', self.base + '/interview')[2]
        fp = view['fingerprint']
        negative = deepcopy(reply); negative['project_input_draft']['approvals']['project_definition']['approved'] = True
        before = byte_snapshot(Path(self.temp.name))
        code, _, result = self.live.request('POST', self.base+'/gpt/replies/preview', value={'text':json.dumps(negative),'expected_fingerprint':fp})
        self.assertEqual(code, 422); self.assertEqual(result['error']['code'], 'APPROVAL_FORGERY')
        self.assertIn('repair_prompt', result); self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        reply['project_input_draft']['project']['primary_outcome'] = '<img src="https://invalid.example/x" onerror="window.injected=1">'
        reply['claims'] = [{'field':'project.primary_outcome','source_refs':['INPUT']}]
        code, _, result = self.live.request('POST', self.base+'/gpt/replies/preview', value={'text':json.dumps(reply),'expected_fingerprint':fp})
        self.assertEqual(code, 200, result)
        preview = result['preview']
        post = {'preview_digest':preview['preview_digest'],'expected_fingerprint':fp}
        code, _, result = self.live.request('POST', self.base+'/gpt/replies/'+preview['import_id']+'/commit', value=post)
        self.assertEqual(code, 200, result); self.assertEqual(result['state'], 'COMMITTED')
        before = byte_snapshot(Path(self.temp.name))
        self.assertEqual(self.live.request('POST', self.base+'/gpt/replies/'+preview['import_id']+'/commit', value=post)[0], 200)
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        self.assertEqual(self.live.request('GET', self.base+'/gpt/exports/'+export['exchange_id']+'/pack.md')[0], 409)
        self.assertEqual(self.live.request('POST', self.base+'/gpt/replies/'+preview['import_id']+'/cancel', value={'preview_digest':preview['preview_digest']})[0], 409)

    def test_http_duplicate_unknown_oversize_and_wrong_project_no_mutation(self):
        export, reply = self.export()
        fp = self.live.request('GET', self.base+'/interview')[2]['fingerprint']
        before = byte_snapshot(Path(self.temp.name))
        for value in ({'text':'{}','expected_fingerprint':fp,'server_path':'C:/host'},
                      {'text':'x'*(512*1024+1),'expected_fingerprint':fp},
                      {'text':'{"kind":1,"kind":2}','expected_fingerprint':fp}):
            self.assertIn(self.live.request('POST', self.base+'/gpt/replies/preview', value=value)[0], (400,422))
        raw = ('{"text":"{}","text":"{}","expected_fingerprint":'+json.dumps(fp)+'}').encode()
        self.assertEqual(self.live.request('POST', self.base+'/gpt/replies/preview', data=raw, headers={'Content-Type':'application/json'})[0], 400)
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))
        other = self.live.create('http-exchange-other-project')
        self.assertEqual(self.live.request('GET', f'/api/projects/{other}/gpt/exports/{export["exchange_id"]}/pack.md')[0], 400)


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS and HAS_PLAYWRIGHT, 'Real Edge and pinned Playwright required')
class ExchangeBrowserTests(unittest.TestCase):
    def test_edge_two_greenfield_scenarios_typed_forms_fixture_exchange_reload_and_xss(self):
        from playwright.sync_api import sync_playwright, expect
        with tempfile.TemporaryDirectory(prefix='ph-lw06-edge-') as directory:
            live = LiveServer(directory)
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL', 'msedge'), headless=True)
                    try:
                        page = browser.new_page(accept_downloads=True, viewport={'width':1440,'height':1000})
                        page.set_default_timeout(15000)
                        requests, errors = [], []
                        page.on('request', lambda r: requests.append(r.url))
                        page.on('pageerror', lambda err: errors.append(str(err)))
                        page.on('dialog', lambda dialog: dialog.accept())
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        for documented in (False, True):
                            page.locator('[data-screen="documents"]').click()
                            page.locator('#new-project-name').fill('Greenfield fixture ' + str(documented))
                            page.locator('#create-intake' if documented else '#create-no-docs').click()
                            expect(page.locator('#source-summary')).to_contain_text('Revision 0' if documented else 'Revision 1')
                            if documented:
                                page.locator('#source-files').set_input_files([
                                    {'name':'source.md','mimeType':'text/markdown','buffer':b'# Fixture specification'},
                                    {'name':'docs.zip','mimeType':'application/zip','buffer':archive([('detail.md',b'<img src="https://invalid.example/x" onerror="window.injected=1">')])}])
                                page.locator('#upload-sources').click()
                                expect(page.locator('#upload-result')).to_contain_text('Принято: 2')
                            page.locator('[data-screen="interview"]').click()
                            expect(page.locator('#interview-body')).to_be_visible()
                            page.locator('#answer-project-primary_outcome').fill('Typed outcome fixture')
                            page.locator('#answer-implementation-target_level').select_option('PROTOTYPE')
                            page.locator('#save-answers').click()
                            expect(page.locator('#known-answers')).to_contain_text('Typed outcome fixture')
                            expect(page.locator('#answer-project-primary_outcome')).to_have_count(0)
                            page.locator('#check-answers').click()
                            expect(page.locator('#notice')).to_contain_text('Ответы проверены')
                            page.locator('#review-export').click()
                            expect(page.locator('#export-review')).to_be_visible()
                            for selector in page.locator('#export-documents select').all():
                                selector.select_option('PUBLIC')
                            page.locator('#draft-classification').select_option('PUBLIC')
                            
                            page.locator('#create-export').click()
                            expect(page.locator('#export-history a')).to_have_count(1)
                            with page.expect_download() as download:
                                page.locator('#export-history a').click()
                            file = Path(download.value.path())
                            pack = file.read_text('utf-8')
                            self.assertNotIn('PROJECT_INPUT@3', pack)
                            skeleton = json.loads(pack.split('## Return skeleton\n\n',1)[1])
                            reply = fixture_reply(skeleton)
                            reply['project_input_draft']['project']['problem_statement'] = '<img src="https://invalid.example/x" onerror="window.injected=1">'
                            # Declared synthetic GPT reply; browser performs every write.
                            page.locator('#gpt-reply').fill(json.dumps(reply, ensure_ascii=False))
                            page.locator('#preview-reply').click()
                            expect(page.locator('#import-preview')).to_be_visible()
                            expect(page.locator('#notice')).to_contain_text('Preview готов')
                            expect(page.locator('#preview-summary')).to_contain_text('Изменений:')
                            expect(page.locator('#reply-diff')).to_contain_text('<img')
                            self.assertEqual(page.locator('img,iframe,script:not([src])').count(),0)
                            self.assertIsNone(page.evaluate('window.injected'))
                            before = byte_snapshot(Path(directory))
                            page.reload(wait_until='networkidle')
                            expect(page.locator('#preview-summary')).to_contain_text('Изменений:')
                            after = byte_snapshot(Path(directory))
                            self.assertEqual(before, after, {k:(before.get(k),after.get(k)) for k in before.keys() | after.keys() if before.get(k)!=after.get(k)})
                            page.locator('#commit-reply').click()
                            expect(page.locator('#import-history')).to_contain_text('COMMITTED')
                            expect(page.locator('#interview-status')).to_contain_text('Нужно выбрать целевой уровень')
                            page.locator('#gpt-reply').fill(json.dumps(reply))
                            page.locator('#preview-reply').click()
                            expect(page.locator('#notice')).to_contain_text('уже применён')
                            # New live binding for a forged approval negative response.
                            page.locator('#review-export').click()
                            expect(page.locator('#export-review')).to_be_visible()
                            for selector in page.locator('#export-documents select').all(): selector.select_option('PUBLIC')
                            page.locator('#draft-classification').select_option('PUBLIC')
                            
                            with page.expect_response(lambda r: r.url.endswith('/gpt/exports') and r.request.method=='POST') as posted:
                                page.locator('#create-export').click()
                            self.assertEqual(posted.value.status, 200, posted.value.text())
                            expect(page.locator('#export-history a')).to_have_count(1)
                            with page.expect_download() as download:
                                page.locator('#export-history a').click()
                            skeleton = json.loads(Path(download.value.path()).read_text('utf-8').split('## Return skeleton\n\n',1)[1])
                            skeleton['project_input_draft']['approvals']['project_definition']['approved'] = True
                            before = byte_snapshot(Path(directory))
                            page.locator('#gpt-reply').fill(json.dumps(skeleton)); page.locator('#preview-reply').click()
                            expect(page.locator('#repair-prompt')).to_contain_text('APPROVAL_FORGERY')
                            self.assertEqual(before, byte_snapshot(Path(directory)))
                            evidence = os.environ.get('PH_LW_06_SCREENSHOT_DIR')
                            if evidence:
                                Path(evidence).mkdir(parents=True,exist_ok=True)
                                page.screenshot(path=str(Path(evidence)/f'greenfield-{documented}.png'),full_page=True)
                        self.assertFalse(errors, errors)
                        self.assertTrue(all(url.startswith(live.origin + '/') for url in requests), requests)
                    finally:
                        browser.close()
            finally:
                live.close()


if __name__ == '__main__':
    unittest.main()

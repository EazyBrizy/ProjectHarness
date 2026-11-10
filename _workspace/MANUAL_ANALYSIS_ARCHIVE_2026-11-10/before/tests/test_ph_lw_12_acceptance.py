"""Final acceptance regressions: real Edge, delayed resume, no POST replay."""
import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ph_lw_04_05_acceptance import LiveServer


class FinalBrowserRegressionTests(unittest.TestCase):
    def test_refresh_after_commit_does_not_reuse_older_lifecycle_response(self):
        from playwright.sync_api import sync_playwright,expect
        from tests.test_engine import prepare_demo
        from tests.test_ph_lw_09_tasks import fixture_input
        from project_harness.runtime import block_current
        from project_harness.stages import stage_status
        with tempfile.TemporaryDirectory(prefix='LW12 stale read ') as folder:
            live=LiveServer(folder)
            try:
                root=prepare_demo(Path(folder)/'fixture',data=fixture_input(command=[]))[2]
                pid=live.service.register_existing(root,kind='project')
                with sync_playwright() as play:
                    browser=play.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL','msedge'),headless=True)
                    try:
                        page=browser.new_page();page.set_default_timeout(15000)
                        reference=os.environ.get('PH_LW_12_REFERENCE_ASSETS')
                        if reference:
                            def old_asset(asset):
                                def serve(route):route.fulfill(path=str(Path(reference)/asset),content_type='application/javascript')
                                return serve
                            for asset in ('app.js','lifecycle.js'):
                                page.route('**/assets/'+asset,old_asset(asset))
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        page.locator('.project-button').filter(has_text=pid).click();page.locator('[data-screen="gates"]').click()
                        expect(page.locator('#lifecycle-summary')).not_to_have_text('Выберите проект.')
                        page.evaluate('lifecycleLoading?.promise')
                        live.ready()
                        older=live.request('GET','/api/projects/'+pid+'/lifecycle')[2]
                        paused=[]
                        page.route('**/api/projects/'+pid+'/lifecycle',lambda route:paused.append(route),times=1)
                        page.evaluate('void loadLifecycle()');page.wait_for_timeout(300)
                        self.assertEqual(len(paused),1)
                        # Public fixture mutation while an older GET response is
                        # delayed. This is a projection fault test, not UI E2E.
                        block_current(root,'Explicit public fixture blocker')
                        expected=stage_status(root)['runtime_phase']
                        try:
                            with page.expect_response(lambda r:r.url==live.origin+'/api/projects/'+pid and r.request.method=='GET') as read:
                                page.locator('#refresh').click()
                                # A serialized transport correctly waits for
                                # this earlier read. Release the injected fault
                                # before awaiting the subsequent GET response.
                                page.wait_for_timeout(200)
                                for route in paused:route.fulfill(status=200,json=older)
                                paused.clear()
                            self.assertNotEqual(read.value.json()['project']['fingerprint'],older['fingerprint'])
                            page.wait_for_function('(fp)=>state.view?.fingerprint===fp',arg=read.value.json()['project']['fingerprint'])
                        finally:
                            for route in paused:route.fulfill(status=200,json=older)
                        expect(page.locator('#lifecycle-summary')).to_have_text(expected)
                    finally:
                        page.unroute_all(behavior='ignoreErrors')
                        browser.close()
            finally:live.close()

    def test_final_ui_has_no_obsolete_manual_lifecycle_placeholders(self):
        from importlib.resources import files
        assets=files('project_harness').joinpath('resources/local_web/assets')
        self.assertNotIn('ожидает PH-LW-09',assets.joinpath('index.html').read_text('utf-8'))
        self.assertNotIn('Форма появится на следующем этапе',assets.joinpath('app.js').read_text('utf-8'))

    def test_stage_status_and_manual_evidence_use_existing_forms(self):
        from playwright.sync_api import sync_playwright,expect
        from tests.test_engine import prepare_demo
        from tests.test_ph_lw_09_tasks import fixture_input
        with tempfile.TemporaryDirectory(prefix='LW12 controls ') as folder:
            live=LiveServer(folder)
            try:
                root=prepare_demo(Path(folder)/'fixture',data=fixture_input(command=[],manual=True))[2]
                pid=live.service.register_existing(root,kind='project')
                with sync_playwright() as play:
                    browser=play.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL','msedge'),headless=True)
                    try:
                        page=browser.new_page();page.set_default_timeout(15000)
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        page.locator('.project-button').filter(has_text=pid).click()
                        status=page.locator('#action-list button').filter(has_text='stage-status')
                        expect(status).to_be_enabled();status.click()
                        expect(page.locator('#screen-title')).to_have_text('Стадии и доказательства')
                        page.locator('[data-screen="projects"]').click()
                        manual=page.locator('#action-list button').filter(has_text='manual-evidence')
                        expect(manual).to_be_enabled();manual.click()
                        expect(page.locator('#screen-title')).to_have_text('Задачи и Run')
                    finally:browser.close()
            finally:live.close()

    def test_navigation_resume_finishes_before_user_mutation(self):
        from playwright.sync_api import sync_playwright, expect
        with tempfile.TemporaryDirectory(prefix='LW12 resume ') as folder:
            live=LiveServer(folder)
            try:
                live.ready();pid=live.create('lw12-resume-fixture-0001')
                with sync_playwright() as p:
                    browser=p.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL','msedge'),headless=True)
                    try:
                        page=browser.new_page();page.set_default_timeout(15000)
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        page.locator('.project-button').filter(has_text=pid).click()
                        expect(page.locator('#project-kind')).to_have_text('Черновик')
                        page.evaluate('resumeWrites')
                        paused=[];posts=[]
                        page.route('**/api/ui/resume',lambda route:paused.append(route) if route.request.method=='POST' else route.continue_())
                        page.on('request',lambda r:posts.append(r.url) if r.method=='POST' and r.url.endswith('/operations') else None)
                        page.locator('[data-screen="interview"]').click()
                        expect(page.locator('#interview-body')).to_be_visible()
                        page.locator('#answer-implementation-target_level').select_option('MVP')
                        page.locator('#save-answers').click()
                        page.wait_for_timeout(300)
                        try:
                            self.assertTrue(paused,'The real navigation resume request must be held')
                            self.assertEqual(posts,[],'User mutation overtook its own pending navigation write')
                        finally:
                            for route in paused:route.continue_()
                        expect(page.locator('#notice')).to_contain_text('Ответы проверены и сохранены')
                        self.assertEqual(len(posts),1,'Exactly one explicit mutation; no automatic POST retry')
                    finally:browser.close()
            finally:live.close()


if __name__=='__main__':unittest.main()

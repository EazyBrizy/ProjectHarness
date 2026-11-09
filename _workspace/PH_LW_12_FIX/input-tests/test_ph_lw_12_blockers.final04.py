"""Windows regressions for the three PH-LW-12 acceptance blockers.

Browser delays are explicit projection/network fault injection. Real Edge,
Waitress, filesystem and public kernel APIs remain in use; POSTs are counted.
"""
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import patch

from project_harness.errors import ValidationFailure
from project_harness.local_web_service import LocalWebService
from project_harness.operation_guard import project_operation_guard
from project_harness.platform_fs import _native_io_path
from project_harness.serialization import write_data
from tests.test_ph_lw_05_import import archive
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_engine import prepare_demo, implement_first_task
from tests.test_ph_lw_09_tasks import fixture_input, agent_result


@unittest.skipUnless(os.name == 'nt', 'Native Windows filesystem required')
class DeepAppDataTests(unittest.TestCase):
    def setUp(self):
        self.base=Path(tempfile.mkdtemp(prefix='LW12 deep fix ')).resolve()
        assert self.base.is_relative_to(Path(tempfile.gettempdir()).resolve())
        self.addCleanup(shutil.rmtree,_native_io_path(self.base))
        self.app=self.base/('Глубокий-'+('x'*120))/('данные-'+('y'*25))
        self.assertGreater(len(str(self.app)),213)

    def test_deep_intake_sources_replay_and_restart(self):
        with LocalWebService(self.app) as service:
            created=service.create_provisional_intake(project_name='Deep Windows intake',idempotency_key='deep-root-fixed-intake-0001')
            pid=created['project_id'];root,_=service._registered(pid)
            self.assertGreater(len(str(root)),260)
            for name,raw in [('safe.md',b'# safe'),('safe.zip',archive([('подкаталог/two.md',b'# two')]))]:
                status=service.get_status(pid);sources=service.list_sources(pid)
                result=service.upload_sources(pid,[(name,BytesIO(raw))],mode='replace',
                    expected_fingerprint=status['fingerprint'],expected_source_revision=sources['source_revision'])
                self.assertEqual(result['accepted_count'],1)
                doc=service.list_sources(pid)['documents'][0]
                self.assertIn('# ',json.dumps(service.preview_source(pid,doc['document_ref'])))
            self.assertTrue(service.get_interview(pid)['questions'])
            replay=service.create_provisional_intake(project_name='Deep Windows intake',idempotency_key='deep-root-fixed-intake-0001')
            self.assertEqual(replay['project_id'],pid);self.assertTrue(replay['replayed'])
            catalog=service._catalog()
            self.assertNotIn('\\\\?\\',json.dumps(catalog))
        with LocalWebService(self.app) as service:
            self.assertEqual(service.get_status(pid)['project_id'],pid)
            self.assertEqual(service.list_sources(pid)['source_revision'],2)

    def test_deep_creation_cleanup_preserves_original_error_and_committed_root(self):
        with LocalWebService(self.app) as service:
            def failed(root,**kwargs):
                write_data(root/'partial'/'record.json',{'injected':True})
                raise OSError('injected original intake error')
            with patch('project_harness.local_web_sources_service.start_intake',side_effect=failed):
                with self.assertRaisesRegex(OSError,'injected original intake error'):
                    service.create_provisional_intake(project_name='Failure',idempotency_key='deep-root-cleanup-fault-0001')
            managed=self.app.parent/(self.app.name+'-workspaces')
            self.assertEqual(list(_native_io_path(managed).iterdir()),[])
            original=service.register_existing
            def registered_then_failed(*args,**kwargs):
                original(*args,**kwargs)
                raise OSError('injected lost registration response')
            with patch.object(service,'register_existing',side_effect=registered_then_failed):
                with self.assertRaisesRegex(OSError,'lost registration response'):
                    service.create_provisional_intake(project_name='Retained',idempotency_key='deep-root-receipt-fault-0001')
            replay=service.create_provisional_intake(project_name='Retained',idempotency_key='deep-root-receipt-fault-0001')
            self.assertTrue(replay['replayed'])
            self.assertEqual(service.get_status(replay['project_id'])['kind'],'workspace')

    def test_cleanup_denial_retains_original_error_and_requires_review(self):
        with LocalWebService(self.app) as service:
            def failed(root,**kwargs):
                write_data(root/'partial.json',{'injected':True})
                raise OSError('injected original creation error')
            with patch('project_harness.local_web_sources_service.start_intake',side_effect=failed), \
                 patch('project_harness.local_web_sources_service.shutil.rmtree',side_effect=PermissionError('injected cleanup denial')):
                with self.assertRaisesRegex(OSError,'original creation error') as caught:
                    service.create_provisional_intake(project_name='Review',idempotency_key='deep-root-cleanup-denied-0001')
            self.assertTrue(any('operator review' in note for note in caught.exception.__notes__))
            self.assertEqual(service._catalog()['projects'],{})
            with self.assertRaisesRegex(ValidationFailure,'INCOMPLETE_INTAKE_CREATION_REQUIRES_OPERATOR_REVIEW'):
                service.create_provisional_intake(project_name='Review',idempotency_key='deep-root-cleanup-denied-0001')

    def test_handoff_archive_long_output_keeps_exact_names_and_crc(self):
        from project_harness.archive import zip_directory
        from project_harness.safety import inspect_zip, safe_extract_zip
        import zipfile
        source=self.base/'handoff';source.mkdir()
        (source/'README.md').write_bytes(b'# exact source bytes')
        output=self.app/'nested-publication-stage'/('artifact-'+('x'*40))/'handoff.zip'
        _native_io_path(output.parent).mkdir(parents=True)
        self.assertGreater(len(str(output.parent)),260)
        zip_directory(source,output)
        self.assertEqual([info.filename for info in inspect_zip(output)],['handoff/README.md'])
        extracted=output.parent/'extracted'
        safe_extract_zip(output,extracted)
        self.assertEqual(_native_io_path(extracted/'handoff/README.md').read_bytes(),b'# exact source bytes')
        with zipfile.ZipFile(_native_io_path(output)) as packed:
            self.assertIsNone(packed.testzip())
            self.assertEqual(packed.namelist(),['handoff/README.md'])
            self.assertEqual(packed.read('handoff/README.md'),b'# exact source bytes')

    def test_long_control_plane_scan_keeps_files_and_detects_tamper(self):
        from project_harness.workspace import scan_protected_control_plane,diff_protected_control_plane
        source=self.base/'short-project'
        write_data(source/'.harness/state/test.json',{'value':'original'})
        write_data(source/'STATUS.md',{'view':'protected'})
        before=scan_protected_control_plane(source)
        target=self.app/('stage-'+('x'*60))/'project'
        self.assertGreater(len(str(target)),260)
        shutil.copytree(_native_io_path(source),_native_io_path(target))
        self.assertEqual(scan_protected_control_plane(target),before)
        write_data(target/'.harness/state/test.json',{'value':'tampered'})
        diff=diff_protected_control_plane(before,scan_protected_control_plane(target),allowed_agent_output_path=None)
        self.assertEqual(diff['status'],'FAIL')
        self.assertEqual(diff['changed'],['.harness/state/test.json'])
        _native_io_path(target/'STATUS.md').unlink()
        diff=diff_protected_control_plane(before,scan_protected_control_plane(target),allowed_agent_output_path=None)
        self.assertEqual(diff['deleted'],['STATUS.md'])

    def test_deep_publication_keeps_identity_and_refuses_existing_destination(self):
        from project_harness.materialization import publish_project_directory,directory_identity
        staged=self.app/('staging-'+('x'*60));destination=self.app/'published'
        write_data(staged/'owned.json',{'fixture':True})
        self.assertGreater(len(str(staged)),260)
        identity=directory_identity(staged)
        publish_project_directory(staged,destination,identity=identity)
        self.assertEqual(directory_identity(destination),identity)
        self.assertFalse(_native_io_path(staged).exists())
        write_data(staged/'second.json',{'fixture':True})
        sentinel=_native_io_path(destination/'sentinel.txt');sentinel.write_bytes(b'user data')
        with self.assertRaisesRegex(ValidationFailure,'DESTINATION_EXISTS'):
            publish_project_directory(staged,destination,identity=directory_identity(staged))
        self.assertEqual(sentinel.read_bytes(),b'user data')
        self.assertTrue(_native_io_path(staged).exists())


class BlockerBrowserTests(unittest.TestCase):
    @contextmanager
    def browser_fixture(self):
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=30000)
        with tempfile.TemporaryDirectory(prefix='LW12 fix Edge ') as folder:
            root=prepare_demo(Path(folder)/'fixture',data=fixture_input(command=[],manual=True))[2]
            implement_first_task(root);raw=agent_result(root) # explicit external fixture agent
            live=LiveServer(folder)
            try:
                pid=live.service.register_existing(root,kind='project')
                with sync_playwright() as play:
                    browser=play.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL','msedge'),headless=True)
                    page=browser.new_page();page.set_default_timeout(30000)
                    try:
                        reference=os.environ.get('PH_LW_12_REFERENCE_ASSETS')
                        if reference:
                            for asset in ('app.js','tasks.js'):
                                def serve(route,request,name=asset):route.fulfill(path=str(Path(reference)/name),content_type='application/javascript')
                                page.route('**/assets/'+asset,serve)
                        page.goto(live.origin+'/#bootstrap='+live.auth.issue_bootstrap())
                        expect(page.locator('#session-state')).to_have_text('Сессия активна')
                        page.locator('.project-button').filter(has_text=pid).click()
                        page.locator('[data-screen="tasks"]').click()
                        expect(page.locator('#task-upload')).to_be_enabled()
                        page.evaluate('projectRead?.promise');page.evaluate('resumeWrites')
                        page.locator('#task-result-file').set_input_files({'name':'result.json','mimeType':'application/json','buffer':json.dumps(raw).encode()})
                        yield page,live,pid,root
                    finally:
                        page.unroute_all(behavior='ignoreErrors');browser.close()
            finally:live.close()

    def test_result_upload_waits_for_prior_project_read_without_post_replay(self):
        from playwright.sync_api import expect
        with self.browser_fixture() as (page,live,pid,root):
            paused=[];posts=[]
            page.route('**/api/projects/'+pid+'/tasks',lambda route:paused.append(route),times=1)
            page.on('request',lambda r:posts.append(r.url) if r.method=='POST' and r.url.endswith('/tasks/result-upload') else None)
            page.evaluate('void api(taskBase()+"/tasks")');page.wait_for_timeout(200)
            self.assertEqual(len(paused),1)
            page.locator('#task-upload').click();page.wait_for_timeout(300)
            try:self.assertEqual(posts,[],'Upload overtook an earlier project read')
            finally:paused[0].continue_()
            expect(page.locator('#task-result-state')).to_contain_text('RESULT_RECEIVED')
            self.assertEqual(len(posts),1)

    def test_multipart_result_waits_for_navigation_resume(self):
        from playwright.sync_api import expect
        with self.browser_fixture() as (page,live,pid,root):
            paused=[];posts=[]
            page.route('**/api/ui/resume',lambda route:paused.append(route),times=1)
            page.on('request',lambda r:posts.append(r.url) if r.method=='POST' and r.url.endswith('/tasks/result-upload') else None)
            page.evaluate('rememberSelection()');page.wait_for_timeout(200)
            self.assertEqual(len(paused),1)
            page.locator('#task-upload').click();page.wait_for_timeout(300)
            try:self.assertEqual(posts,[],'Multipart bypassed its pending resume write')
            finally:paused[0].continue_()
            expect(page.locator('#task-result-state')).to_contain_text('RESULT_RECEIVED')
            self.assertEqual(len(posts),1)

    def test_project_card_matches_fresh_core_after_browser_block(self):
        from playwright.sync_api import expect
        with self.browser_fixture() as (page,live,pid,root):
            page.get_by_text('Block / resume и восстановление',exact=True).click()
            page.locator('#task-reason').fill('Explicit PH-LW-12 regression blocker')
            page.locator('#task-block').click()
            expect(page.locator('#task-operation')).to_contain_text('SUCCEEDED')
            expect(page.locator('#core-status')).to_have_text('BLOCKED')
            expect(page.locator('.project-button').filter(has_text=pid)).to_contain_text('BLOCKED')

    def test_external_project_conflict_is_not_replayed_automatically(self):
        from playwright.sync_api import expect
        with self.browser_fixture() as (page,live,pid,root):
            held=threading.Event();release=threading.Event();responses=[]
            def owner():
                with project_operation_guard(root):
                    held.set();release.wait(20)
            worker=threading.Thread(target=owner);worker.start();self.assertTrue(held.wait(5))
            page.on('response',lambda r:responses.append(r.status) if r.url.endswith('/tasks/result-upload') else None)
            try:
                with page.expect_response(lambda r:r.url.endswith('/tasks/result-upload')) as response:
                    page.locator('#task-upload').click()
                self.assertEqual(response.value.status,409)
                self.assertEqual(responses,[409])
            finally:release.set();worker.join(5)
            page.locator('#refresh').click()
            expect(page.locator('#task-upload')).to_be_enabled()
            page.wait_for_timeout(300);self.assertEqual(responses,[409])
            page.locator('#task-upload').click()
            expect(page.locator('#task-result-state')).to_contain_text('RESULT_RECEIVED')
            self.assertEqual(responses,[409,201])

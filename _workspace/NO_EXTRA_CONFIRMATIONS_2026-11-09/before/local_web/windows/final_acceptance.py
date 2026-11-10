"""PH-LW-12 actual installed EXE: UI lifecycle and real TCP security.

Advanced-state setup is explicitly separate: existing public-kernel fixture
recipes and public catalog registration supply initial state. All tested
approvals/transitions/results use real browser forms. No private kernel edits.
"""
from __future__ import annotations
from contextlib import contextmanager
import argparse
import ctypes
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import tempfile
import types
import unittest
import shutil
from io import BytesIO
import stat,struct,zipfile
# A pre-imported installed package keeps public advanced-fixture construction
# independent of the development distribution (which contains historical logs).
# Production requests still go to the real installed frozen executable.
DRIVER_PACKAGE=None
if os.environ.get('PH_LW_12_INSTALLED_DRIVER')=='1':
    import project_harness
    DRIVER_PACKAGE=str(Path(project_harness.__file__).resolve())
    assert Path(DRIVER_PACKAGE).is_relative_to(Path(sys.prefix).resolve())
import acceptance

ENGINE=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ENGINE/'src'),str(ENGINE)]
from project_harness.local_web_service import LocalWebService
from project_harness.windows_package import verify_bundle
from project_harness.platform_fs import _native_io_path, native_glob, ensure_native_path
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_05_import import archive
from tests.test_ph_lw_06_http import fixture_reply
from tests.test_engine import implement_first_task
from tests.test_ph_lw_09_tasks import agent_result

OPTIONS=None

@contextmanager
def owned_temporary_directory(prefix):
    root=Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    assert root.is_relative_to(Path(tempfile.gettempdir()).resolve()) and root.name.startswith(prefix)
    try:yield str(root)
    finally:
        ensure_native_path(root,tree=True)
        shutil.rmtree(_native_io_path(root))

def control_bytes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(_native_io_path(p).read_bytes()).hexdigest()
            for p in native_glob(root,'*',recursive=True) if _native_io_path(p).is_file()}

def observe_task_responses(page,name):
    """Record application responses, never authentication headers/cookies."""
    rows=[]
    def response(value):
        tracked_post=value.request.method=='POST' and any(value.url.endswith(p) for p in ('/tasks/result-upload','/operations'))
        tracked_error=value.status>=400 and '/api/projects/' in value.url
        if not (tracked_post or tracked_error):return
        try:body=value.json()
        except Exception:body={'unreadable_response':True}
        rows.append({'path':value.url.split('/api/',1)[-1],'method':value.request.method,'status':value.status,'body':body})
        (OPTIONS.output/('task-responses-'+name+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),'utf-8')
    page.on('response',response)

class FrozenFixtureServer(acceptance.FrozenServer):
    def __init__(self,directory=None):
        acceptance.OPTIONS.runtime_root=Path(directory) if directory else OPTIONS.output/'full-flow'
        if getattr(OPTIONS,'deep_full_flow',False):
            base=acceptance.OPTIONS.runtime_root
            count=194-len(str(base))-1
            assert 0<count<240
            acceptance.OPTIONS.runtime_root=base/('d'*count)
            assert len(str(acceptance.OPTIONS.runtime_root))==194
        super().__init__()
        projects=self.service.projects_directory
        # Driver uses only public registration/read helpers for initial advanced
        # fixtures. This does not claim UI registration or a full advanced E2E.
        self.service=LocalWebService(self.app_data,projects_directory=projects)
        if getattr(OPTIONS,'deep_full_flow',False):
            (OPTIONS.output/'DEEP_PROFILE.json').write_text(json.dumps({'app_data_length':len(str(self.app_data)),
                'project_parent_length':len(str(projects)),'ordinary_paths':True,'system_settings_changed':False},indent=2),'utf-8')
    def request(self,method,path,*,value=None,data=None,headers=None):
        # Win32 may reset an oversized-header rejection after the 431 status
        # was received. Status assertions remain exact; successful responses
        # must always deliver their complete body.
        hdr={'Origin':self.origin}
        
        if value is not None:data=json.dumps(value).encode('utf-8');hdr['Content-Type']='application/json'
        hdr.update(headers or {})
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=10)
        try:
            conn.request(method,path,body=data,headers=hdr);response=conn.getresponse()
            try:raw=response.read()
            except ConnectionResetError:
                if response.status!=431:raise
                raw=b''
                print('Observed exact HTTP 431 status; Windows reset while reading rejection body',flush=True)
            return response.status,dict(response.getheaders()),json.loads(raw) if raw.startswith(b'{') else raw
        finally:conn.close()
    def close(self):
        super().close()
        self.service.close()


class InstalledFullFlowTests(unittest.TestCase):
    def test_no_documents_gpt_approvals_publish_manual_evidence_verify_complete(self):
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=30000)
        from project_harness.project_input import approvals_for_mode
        with owned_temporary_directory(prefix='LW12 installed no-doc ') as directory:
            live=FrozenFixtureServer(directory)
            self.live=live
            try:
                with sync_playwright() as play:
                    browser=play.chromium.launch(channel='msedge',headless=True)
                    try:
                        context=browser.new_context(accept_downloads=True,viewport={'width':1440,'height':1100})
                        page=context.new_page();page.set_default_timeout(30000);self.page=page
                        observe_task_responses(page,'no-doc')
                        urls=[];errors=[];page.on('request',lambda r:urls.append(r.url));page.on('pageerror',lambda e:errors.append(str(e)))
                        page.on('dialog',lambda d:d.accept())
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        page.locator('[data-screen="documents"]').click()
                        page.locator('#new-project-name').fill('PH-LW-12 no documentation')
                        page.locator('#create-intake').click()
                        expect(page.locator('#source-summary')).to_contain_text('Revision 0')
                        page.locator('#confirm-no-docs').click()
                        expect(page.locator('#source-summary')).to_contain_text('NONE')
                        page.locator('[data-screen="interview"]').click()
                        expect(page.locator('#interview-body')).to_be_visible()
                        page.locator('#answer-implementation-target_level').select_option('MVP')
                        page.locator('#save-answers').click()
                        expect(page.locator('#notice')).to_contain_text('Ответы проверены и сохранены ядром')
                        page.locator('#review-export').click();expect(page.locator('#export-review')).to_be_visible()
                        self.assertEqual(page.locator('#export-documents select').count(),0)
                        page.locator('#draft-classification').select_option('PUBLIC');page.locator('#export-consent').check()
                        page.locator('#create-export').click();expect(page.locator('#export-history a')).to_have_count(1)
                        with page.expect_download() as download:page.locator('#export-history a').click()
                        pack=Path(download.value.path()).read_text('utf-8')
                        reply=fixture_reply(json.loads(pack.split('## Return skeleton\n\n',1)[1]))
                        # Declared external GPT fixture: positive manual-only
                        # verification requires no installed product SDK.
                        first=reply['project_input_draft']['planning']['work_packages'][0]['tasks'][0]
                        first['verification']['commands']=[]
                        first['verification']['manual_checks']=['Review add/list CLI and README against this Task']
                        first['verification']['allow_manual']=True
                        page.locator('#gpt-reply').fill(json.dumps(reply,ensure_ascii=False))
                        page.locator('#preview-reply').click();expect(page.locator('#import-preview')).to_be_visible()
                        page.locator('#commit-reply').click();expect(page.locator('#import-history')).to_contain_text('COMMITTED')
                        page.locator('[data-screen="approvals"]').click()
                        expect(page.locator('#approval-subjects section')).to_have_count(4)
                        page.locator('#approval-actor').fill('ACT-WIN12-OPERATOR');page.locator('#save-approval-actor').click()
                        expect(page.locator('#approval-actor-display')).to_contain_text('ACT-WIN12-OPERATOR')
                        for i,subject in enumerate(approvals_for_mode('GREENFIELD')):
                            page.locator('#confirm-'+subject).check();page.locator('#approve-'+subject).click()
                            expect(page.locator('#approvals-status')).to_contain_text(str(i+1)+' из 4')
                        expect(page.locator('#preparation-form')).to_be_visible()
                        page.locator('#project-folder-name').fill('No documents product');page.locator('#confirm-new-folder').check()
                        with page.expect_response(lambda r:r.url.endswith('/preparation/start')) as started:
                            page.locator('#prepare-project').click()
                        self.assertEqual(started.value.status,202,started.value.text())
                        page.reload(wait_until='networkidle')
                        expect(page.locator('#preparation-complete')).to_be_visible(timeout=180000)
                        root=live.service.projects_directory/'No documents product'
                        before=control_bytes(root/'.harness');self.assertTrue(before)
                        implement_first_task(_native_io_path(root)) # external fixture agent; product plane only
                        self.assertEqual(before,control_bytes(root/'.harness'))
                        raw=agent_result(root)
                        page.locator('[data-screen="projects"]').click();page.locator('#refresh').click()
                        page.locator('.project-button').filter(has_text='Проект ·').last.click()
                        page.locator('[data-screen="tasks"]').click();expect(page.locator('#task-upload')).to_be_enabled()
                        page.locator('#task-result-file').set_input_files({'name':'result.json','mimeType':'application/json','buffer':json.dumps(raw).encode()})
                        page.locator('#task-upload').click();expect(page.locator('#task-result-state')).to_contain_text('RESULT_RECEIVED')
                        expect(page.locator('#task-complete')).to_be_disabled()
                        page.locator('#task-verify').click();expect(page.locator('#task-verification')).to_contain_text('BLOCKED')
                        page.locator('#task-manual-panel summary').click()
                        page.locator('#task-manual-reviewer').fill('ACT-WIN12-INDEPENDENT-REVIEWER')
                        page.locator('#task-manual-checks textarea').fill('Inspected add/list parsing, persisted task IDs, expected product files and README. Synthetic fixture only.')
                        page.locator('#task-manual-checks [data-field="status"]').select_option('PASS')
                        page.locator('#task-manual-checks [data-field="sources"]').select_option(['task_cli.py','README.md'])
                        page.locator('#task-manual-confirm').check();page.locator('#task-manual-submit').click()
                        expect(page.locator('#task-manual-state')).to_contain_text('ACT-WIN12-INDEPENDENT-REVIEWER')
                        page.locator('#task-verify').click();expect(page.locator('#task-complete')).to_be_enabled(timeout=60000)
                        expect(page.locator('#task-verification')).to_contain_text('PASS')
                        page.screenshot(path=str(OPTIONS.output/'installed-task-pass.png'),full_page=True)
                        page.locator('#task-complete').click();expect(page.locator('#tasks-summary')).to_contain_text('завершено: 1')
                        expect(page.locator('#task-prompt')).not_to_have_value('')
                        self.assertFalse(errors,errors)
                        self.assertTrue(all(url.startswith(live.origin+'/') for url in urls),urls)
                    finally:browser.close()
            finally:
                # This method owns cleanup; retain operation evidence before
                # close kills the frozen process and TemporaryDirectory exits.
                target=OPTIONS.output/'operations-no-doc';target.mkdir(exist_ok=True)
                try:
                    for path in native_glob(live.app_data/'operations','*.json'):
                        (target/path.name).write_bytes(_native_io_path(path).read_bytes())
                finally:live.close()

    def test_installed_tcp_security_and_ownership(self):
        with tempfile.TemporaryDirectory(prefix='LW12 installed security ') as directory:
            live=FrozenFixtureServer(directory)
            try:
                self.assertEqual(live.request('GET','/api/projects',headers={'Origin':'http://foreign.invalid'})[0],403)
                live.ready()
                self.assertEqual(live.request('GET','/api/projects')[0],200)
                pid=live.create('lw12-installed-security-0001');base='/api/projects/'+pid
                for headers in ({'Host':'evil.example'},{'Host':'127.0.0.1:1'},{'Host':'localhost:'+str(live.port)},
                                {'Origin':'null'},{'Origin':'https://foreign.example'},{'Origin':'http://127.0.0.1:1'}):
                    self.assertEqual(live.upload(pid,[('ok.md',b'# safe')],headers=headers)[0],403)
                bad_names=['../escape.md','C:/drive.md','C:relative.md','//host/share.md','x:ads.md','NUL.md','trail. /x.md','a\\b.md']
                for name in bad_names:
                    self.assertEqual(live.upload(pid,[('hostile.zip',archive([(name,b'x')]))])[0],400,name)
                link=BytesIO()
                with zipfile.ZipFile(link,'w') as z:
                    info=zipfile.ZipInfo('link.md');info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,'../../escape')
                corrupt=bytearray(archive([('crc.md',b'UNIQUE_CRC_PAYLOAD')]))
                corrupt[corrupt.index(b'UNIQUE_CRC_PAYLOAD')]=ord('X')
                encrypted=bytearray(archive([('encrypted.md',b'x')]))
                struct.pack_into('<H',encrypted,6,1)
                at=encrypted.index(b'PK\x01\x02');struct.pack_into('<H',encrypted,at+8,1)
                attacks={'casefold_collision':archive([('a.md',b'x'),('A.md',b'y')]),
                    'unicode_collision':archive([('é.md',b'x'),('e\u0301.md',b'y')]),
                    'symlink_entry':link.getvalue(),'crc_corruption':bytes(corrupt),'encryption':bytes(encrypted),
                    'entry_count':archive([(str(i)+'.md',b'x') for i in range(1001)]),
                    'depth':archive([('/'.join(['d']*17)+'/x.md',b'x')]),
                    'oversize_entry':archive([('huge.md',b'x'*(8*1024*1024+1))]),
                    'compression_bomb':archive([('bomb.md',b'x'*(2*1024*1024))],compress=zipfile.ZIP_DEFLATED),
                    'nested_zip':archive([('inside.zip',archive([('x.md',b'x')]))])}
                for name,raw in attacks.items():
                    self.assertEqual(live.upload(pid,[(name+'.zip',raw)])[0],400,name)
                self.assertEqual(live.request('GET',base+'/sources')[2]['source_revision'],0)
                self.assertEqual(live.upload(pid,[('safe.md',b'<script>window.injected=1</script>')])[0],200)
                doc=live.request('GET',base+'/sources')[2]['documents'][0]['document_ref']
                other=live.create('lw12-installed-security-0002')
                self.assertEqual(live.request('GET','/api/projects/'+other+'/documents/'+doc+'/preview')[0],400)
                self.assertNotEqual(live.request('GET',base+'/documents/..%2f..%2fWindows/preview')[0],200)
                code,headers,_=live.request('GET',base+'/documents/'+doc+'/preview')
                self.assertEqual(code,200);self.assertNotIn('Access-Control-Allow-Origin',headers)
                self.assertIn("default-src 'none'",headers['Content-Security-Policy'])
                for info in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET):
                    address=info[4][0]
                    if address.startswith('127.') or address=='0.0.0.0':continue
                    with self.assertRaises(OSError):socket.create_connection((address,live.port),timeout=.3)
                save={'checked_host_origin':True,'direct_entry_without_login':True,'cross_project':True,
                      'malicious_zip_names':bad_names,'archive_attacks':list(attacks),'no_lan_cors':True,'raw_credentials_logged':False}
                (OPTIONS.output/'INSTALLED_SECURITY.json').write_text(json.dumps(save,indent=2),'utf-8')
            finally:live.close()


def main():
    global OPTIONS
    parser=argparse.ArgumentParser();parser.add_argument('--installer',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--case',action='append',help='Focused rerun; preserve previous full evidence')
    parser.add_argument('--advanced-fixtures',type=Path,help='Exact validated public-kernel initial-state cache')
    parser.add_argument('--deep-full-flow',action='store_true',help='Owned deep app-data/project profile for focused actual EXE no-doc E2E')
    OPTIONS=parser.parse_args()
    OPTIONS.installer=OPTIONS.installer.resolve();OPTIONS.output=OPTIONS.output.resolve();OPTIONS.output.mkdir(parents=True,exist_ok=False)
    if sys.platform!='win32' or ctypes.windll.shell32.IsUserAnAdmin():raise RuntimeError('Native non-admin Windows required')
    OPTIONS.install_dir=OPTIONS.output/'Установленная программа'
    command=[str(OPTIONS.installer),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/DIR='+str(OPTIONS.install_dir),'/LOG='+str(OPTIONS.output/'install.log')]
    setup=subprocess.run(command,timeout=180);assert setup.returncode==0
    OPTIONS.build_id=json.loads((OPTIONS.install_dir/'current.json').read_text())['build_id']
    acceptance.OPTIONS=types.SimpleNamespace(install_dir=OPTIONS.install_dir,build_id=OPTIONS.build_id,output=OPTIONS.output,runtime_root=None,installer=OPTIONS.installer)
    verify_bundle(OPTIONS.install_dir/'versions'/OPTIONS.build_id)
    import tests.test_ph_lw_10_http as lifecycle
    import tests.test_ph_lw_09_http as tasks
    import tests.test_ph_lw_07_http as approvals
    import tests.test_ph_lw_12_acceptance as final_regressions
    import tests.test_ph_lw_12_blockers as blocker_regressions
    import tests.test_ph_lw_04_05_acceptance as transport
    if OPTIONS.advanced_fixtures:
        base=OPTIONS.advanced_fixtures.resolve()
        for name in ('gate','accepted'):
            from project_harness.validation import validate_project_directory
            assert validate_project_directory(base/name)['status']=='PASS'
        lifecycle.public_fixtures=lambda:(base/'gate',base/'accepted')
    lifecycle.LiveServer=tasks.LiveServer=approvals.LiveServer=FrozenFixtureServer
    final_regressions.LiveServer=FrozenFixtureServer
    blocker_regressions.LiveServer=FrozenFixtureServer
    transport.LiveServer=FrozenFixtureServer
    class AdditionalLifecycleTests(lifecycle.LifecycleBrowserTests):
        @classmethod
        def setUpClass(cls):
            cls.gate,cls.accepted=lifecycle.public_fixtures()
        def test_accepted_mvp_to_release_form_preserves_history(self):
            from tests.ph_f06_fixtures import prepared,accept,plan,history_snapshot
            from project_harness.stages import stage_status
            from playwright.sync_api import expect
            source=self.base/'mvp-fixture'
            cache=OPTIONS.advanced_fixtures/'mvp' if OPTIONS.advanced_fixtures else None
            if cache and cache.exists():
                recorded=json.loads((ENGINE.parent/'_workspace/PH_LW_12/MATURITY_SETUP_CACHE.json').read_text('utf-8'))
                actual={p.relative_to(cache).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in cache.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
                self.assertEqual(actual,recorded['hashes'])
                self.assertEqual(stage_status(cache)['highest_accepted_level'],'MVP')
                shutil.copytree(cache,source)
            else:
                # A gate fixture is already VERIFYING and cannot be passed to
                # the READY-task recipe; build this initial state from scratch.
                source=prepared(self.base/'mvp-setup')
                for i,level in enumerate(('PROTOTYPE','ALPHA','BETA','MVP')):
                    if i:plan(source,self.base/'mvp-records',level)
                    accept(source,self.base/'mvp-records',level)
            self.open(source);before=history_snapshot(self.root)
            self.prepare('prepare-level-up');self.field('level_up_approval.target_level').select_option('RELEASE');self.apply()
            expect(self.page.locator('#lifecycle-levels')).to_contain_text('RELEASE',timeout=90000)
            expect(self.page.locator('#lifecycle-summary')).to_have_text('STAGE_PLANNING_REQUIRED',timeout=90000)
            expect(self.page.locator('#core-status')).to_have_text('ACTIVE',timeout=90000)
            expect(self.page.locator('.project-button').filter(has_text=self.pid)).to_contain_text('ACTIVE')
            status=stage_status(self.root);self.assertEqual(status['highest_accepted_level'],'MVP');self.assertEqual(status['active_stage'],'RELEASE')
            for rel,digest in before.items():self.assertEqual(hashlib.sha256((self.root/rel).read_bytes()).hexdigest(),digest)
            self.screenshot('mvp-to-release.png');self.check_browser()
        def test_maintenance_task_completion_through_browser(self):
            from playwright.sync_api import expect
            from project_harness.stages import stage_status
            self.open(self.accepted);self.prepare('prepare-maintenance')
            observe_task_responses(self.page,'maintenance')
            values={'objective':'Clarify current usage','rationale':'Same-level maintenance',
                'work_package.title':'README maintenance','work_package.objective':'README clarification',
                'work_package.tasks.0.title':'Clarify README','work_package.tasks.0.purpose':'Current usage',
                'work_package.tasks.0.expected_result':'Reviewed README','work_package.tasks.0.produces_artifacts':'README.md',
                'work_package.tasks.0.scope.read':'README.md','work_package.tasks.0.scope.write':'README.md',
                'work_package.tasks.0.verification.expected_paths':'README.md',
                'work_package.tasks.0.verification.manual_checks':'README describes current CLI',
                'work_package.tasks.0.acceptance_criteria':'README describes current CLI'}
            for path,value in values.items():self.field('maintenance_plan.'+path).fill(value)
            self.apply();expect(self.page.locator('#lifecycle-summary')).to_contain_text('MAINTENANCE',timeout=90000)
            self.page.wait_for_function('!state.requestBusy && !projectRead && !lifecycleLoading')
            with (self.root/'README.md').open('a',encoding='utf-8') as f:f.write('\nExternal fixture agent: clarified current local CLI usage.\n')
            # The external fixture result is constructed before starting UI
            # reads; task_console deliberately rejects a concurrent reader.
            raw=agent_result(self.root)
            self.page.locator('[data-screen="tasks"]').click();self.page.locator('#refresh').click()
            expect(self.page.locator('#task-upload')).to_be_enabled()
            self.page.locator('#task-result-file').set_input_files({'name':'maintenance-result.json','mimeType':'application/json','buffer':json.dumps(raw).encode()})
            self.page.locator('#task-upload').click();expect(self.page.locator('#task-verify')).to_be_enabled()
            self.page.locator('#task-manual-panel summary').click();self.page.locator('#task-manual-reviewer').fill('ACT-WIN12-REVIEWER')
            self.page.locator('#task-manual-checks textarea').fill('Reviewed the README addition against existing local CLI usage; no scope expansion.')
            self.page.locator('#task-manual-checks [data-field="status"]').select_option('PASS')
            self.page.locator('#task-manual-checks [data-field="sources"]').select_option(['README.md'])
            self.page.locator('#task-manual-confirm').check();self.page.locator('#task-manual-submit').click()
            expect(self.page.locator('#task-manual-state')).to_contain_text('ACT-WIN12-REVIEWER')
            self.page.locator('#task-verify').click();expect(self.page.locator('#task-complete')).to_be_enabled(timeout=60000)
            self.page.locator('#task-complete').click();expect(self.page.locator('#task-operation')).to_contain_text('SUCCEEDED',timeout=60000)
            self.page.locator('[data-screen="gates"]').click();expect(self.page.locator('#lifecycle-summary')).to_contain_text('TARGET_LEVEL_REACHED',timeout=60000)
            self.assertEqual(stage_status(self.root)['highest_accepted_level'],'PROTOTYPE');self.check_browser()
    for stage in ('07','09','10'):os.environ['PH_LW_'+stage+'_SCREENSHOT_DIR']=str(OPTIONS.output/'screenshots'/stage)
    os.environ['PH_LW_04_BROWSER_CHANNEL']='msedge'
    names=[InstalledFullFlowTests,tasks.TasksBrowserTests,lifecycle.LifecycleBrowserTests,approvals.ApprovalBrowserTests,
           final_regressions.FinalBrowserRegressionTests,blocker_regressions.BlockerBrowserTests]
    globals()['AdditionalLifecycleTests']=AdditionalLifecycleTests
    globals()['transport']=transport
    suite=(unittest.defaultTestLoader.loadTestsFromNames(OPTIONS.case) if OPTIONS.case else
           unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in names))
    if not OPTIONS.case:
        for name in ('test_real_upload_malicious_archives_auth_and_read_only_preview','test_production_wsgi_declared_and_chunked_body_header_and_idle_limits'):
            suite.addTest(transport.ProductionHttpAcceptance(name))
        for name in ('test_accepted_mvp_to_release_form_preserves_history','test_maintenance_task_completion_through_browser'):
            suite.addTest(AdditionalLifecycleTests(name))
    class ImmediateResult(unittest.TextTestResult):
        def capture(self,test):
            page=getattr(test,'page',None)
            if page:
                state={}
                for key in ('notice','lifecycle-summary','lifecycle-operation','tasks-summary','task-operation','task-result-state'):
                    try:state[key]=page.locator('#'+key).inner_text(timeout=2000)
                    except Exception:pass
                (OPTIONS.output/('ui-'+test.id().split('.')[-1]+'.json')).write_text(json.dumps(state,ensure_ascii=False,indent=2),'utf-8')
            live=getattr(test,'live',None)
            if live:
                target=OPTIONS.output/('operations-'+test.id().split('.')[-1]);target.mkdir(exist_ok=True)
                for path in (live.app_data/'operations').glob('*.json'):
                    (target/path.name).write_bytes(path.read_bytes())
        def addFailure(self,test,err):
            super().addFailure(test,err)
            (OPTIONS.output/('failure-'+test.id().split('.')[-1]+'.txt')).write_text(self._exc_info_to_string(err,test),'utf-8')
            self.capture(test)
        def addError(self,test,err):
            super().addError(test,err)
            (OPTIONS.output/('error-'+test.id().split('.')[-1]+'.txt')).write_text(self._exc_info_to_string(err,test),'utf-8')
            self.capture(test)
    with (OPTIONS.output/'browser.log').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=ImmediateResult).run(suite)
    uninstall=next((OPTIONS.install_dir/'uninstall').glob('unins*.exe'))
    removed=subprocess.run([str(uninstall),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/LOG='+str(OPTIONS.output/'uninstall.log')],timeout=120)
    report={'status':'PASS' if result.wasSuccessful() and not result.skipped and removed.returncode==0 else 'FAIL',
            'platform':platform.platform(),'python':sys.version,'non_admin':True,'build_id':OPTIONS.build_id,
            'installer_sha256':hashlib.sha256(OPTIONS.installer.read_bytes()).hexdigest(),'driver_package':DRIVER_PACKAGE,
            'tests':{'ran':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped)},
            'advanced_fixture_boundary':'Public-kernel initial fixtures and catalog registration; all tested browser segment mutations through UI. Migration downgrade is an explicit legacy-state fixture, not acceptance mutation.',
            'advanced_fixture_cache':str(OPTIONS.advanced_fixtures) if OPTIONS.advanced_fixtures else None,
            'product_sdk':'Existing Task command fixtures explicitly use developer interpreter as product SDK; separate no-doc full flow uses manual checks without product SDK.',
            'clean_machine':'NOT RUN; accepted limitation','physical_offline':'NOT RUN; accepted limitation',
            'deep_full_flow':OPTIONS.deep_full_flow,
            'actual_unicode_username':'NOT RUN; accepted limitation','real_disk_full':'NOT RUN; accepted limitation',
            'uninstall_exit':removed.returncode,'zip_created':False}
    (OPTIONS.output/'RESULT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n','utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));return report['status']!='PASS'

if __name__=='__main__':raise SystemExit(main())

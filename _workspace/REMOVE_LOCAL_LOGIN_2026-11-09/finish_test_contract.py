import ast
from pathlib import Path
import textwrap

ROOT=Path(__file__).resolve().parents[2];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1';TESTS=ENGINE/'tests'
def write(p,s):ast.parse(s);p.write_text(s,'utf-8')
def method(p,cls,name,code):
    s=p.read_text('utf-8');tree=ast.parse(s)
    c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    n=next(n for n in c.body if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=s.splitlines(True);lines[n.lineno-1:n.end_lineno]=[textwrap.indent(textwrap.dedent(code).strip()+'\n','    ')]
    write(p,''.join(lines))

for p in TESTS.glob('test_*.py'):
    s=p.read_text('utf-8');lines=s.splitlines(True)
    for i,line in enumerate(lines):
        if 'foreign.invalid' in line and '401' in line:lines[i]=line.replace('401','403')
    write(p,''.join(lines)) if ''.join(lines)!=s else None

p=TESTS/'test_ph_lw_05_http.py';s=p.read_text('utf-8')
s=s.replace("        response = self.client.post('/api/session/bootstrap', json={'token': token}, headers=self.host)\n        self.assertEqual(response.status_code, 200)\n",'')
s=s.replace('test_auth_upload_list_preview_and_replay','test_direct_upload_list_preview_and_replay')
s=s.replace('self.assertEqual(unauth.status_code, 401)','self.assertEqual(unauth.status_code, 200)')
s=s.replace('self.assertEqual(self._upload(headers=self.host).status_code, 403)',"self.assertNotIn('Set-Cookie', unauth.headers)")
s=s.replace('self.assertEqual(missing.status_code, 401)','self.assertEqual(missing.status_code, 201)')
s=s.replace('self.assertIn(result.status_code, (401, 405))',"self.assertEqual(result.status_code, 405 if method == 'get' else 200)")
write(p,s)

p=TESTS/'test_ph_lw_04_05_acceptance.py';s=p.read_text('utf-8').replace("conn.putrequest('POST', '/api/session/bootstrap')","conn.putrequest('POST', '/api/intakes')")
write(p,s)
p=TESTS/'test_ph_lw_04_http.py';s=p.read_text('utf-8')
s=s.replace('cookie=None, csrf=None','cookie=None')
s=s.replace("        if csrf is not None: headers['X-CSRF-Token'] = csrf\n",'')
s=s.replace('test_browser_bootstrap_fragment_removed_no_external_requests_xss_inert','test_browser_direct_entry_no_external_requests_xss_inert')
write(p,s)

p=TESTS/'test_ph_lw_11_desktop.py';s=p.read_text('utf-8')
s=s.replace("        response = self.client.post('/api/session/bootstrap',json={'token':self.auth.issue_bootstrap()},headers=self.headers)\n",'')
s=s.replace("expect(page.locator('#notice')).to_contain_text('Intake создан')","expect(page.locator('#notice')).to_contain_text('Проект создан')")
s=s.replace("expect(other.locator('#project-layout')).to_be_visible()\n                        expect(other.locator('.project-button').filter(has_text=pid)).to_be_visible()", "expect(other.locator('#documents-panel')).to_be_visible()")
write(p,s)
method(p,'DesktopContractTests','test_stop_requires_session_csrf_exact_origin_and_fields','''
def test_stop_without_login_preserves_origin_and_field_validation(self):
    invalid={'Host':'127.0.0.1:32179','Origin':'http://evil.invalid'}
    self.assertEqual(self.client.post('/api/desktop/stop',json={},headers=invalid).status_code,403)
    self.assertEqual(self.post('/api/desktop/stop',{'force':True}).status_code,400)
    self.assertFalse(self.service.desktop_lifecycle.stopping.is_set())
    self.assertEqual(self.app.test_client().post('/api/desktop/stop',json={},headers=self.headers).status_code,200)
''')
method(p,'DesktopContractTests','test_bootstrap_reissue_does_not_revoke_other_tabs','''
def test_independent_clients_access_without_sessions_or_cookies(self):
    for client in (self.client,self.app.test_client()):
        response=client.get('/api/ui/resume',headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertNotIn('Set-Cookie',response.headers)
''')
method(p,'DesktopContractTests','test_browser_failure_displays_only_native_fallback','''
def test_browser_failure_displays_plain_url_without_login_code(self):
    if os.name!='nt':self.skipTest('native Windows')
    from project_harness.local_web_launcher import open_local_browser
    with patch('webbrowser.open',return_value=False),patch('ctypes.windll.user32.MessageBoxW') as message,patch('builtins.print') as output:
        self.assertFalse(open_local_browser('http://127.0.0.1:1234/'))
        self.assertIn('http://127.0.0.1:1234/',message.call_args.args[1])
        self.assertNotIn('код',message.call_args.args[1]);output.assert_not_called()
''')
method(p,'NativeLauncherTests','test_edge_manual_code_login_without_fragment_or_external_requests','''
def test_edge_direct_entry_without_login_controls_or_external_requests(self):
    from tests.test_ph_lw_04_05_acceptance import LiveServer
    from playwright.sync_api import sync_playwright,expect
    with tempfile.TemporaryDirectory(prefix='harness-direct-entry-') as folder:
        live=LiveServer(folder)
        try:
            with sync_playwright() as play:
                browser=play.chromium.launch(channel='msedge',headless=True)
                try:
                    page=browser.new_page();urls=[];page.on('request',lambda r:urls.append(r.url))
                    page.goto(live.origin+'/')
                    expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                    self.assertEqual(page.locator('#session-gate,#manual-bootstrap,#manual-login,#logout').count(),0)
                    self.assertNotIn('#',page.url)
                    self.assertTrue(all(url.startswith(live.origin+'/') for url in urls))
                    self.assertFalse(any('/api/session' in url for url in urls))
                finally:browser.close()
        finally:live.close()
''')
method(p,'NativeLauncherTests','test_dpapi_and_native_mutex_subprocess','''
def test_native_mutex_subprocess(self):
    from project_harness.local_web_instance import UserInstanceLock
    code='from project_harness.local_web_instance import UserInstanceLock; x=UserInstanceLock(); print(x.__enter__().owned); x.__exit__()'
    with UserInstanceLock() as first:
        self.assertTrue(first.owned)
        child=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,timeout=20)
        self.assertEqual(child.returncode,0,child.stderr);self.assertEqual(child.stdout.strip(),'False')
''')
method(p,'NativeLauncherTests','test_fresh_authenticated_handshake_and_spoof_listener','''
def test_plain_instance_record_discovery_cleanup_and_invalid_records(self):
    from project_harness.local_web_instance import LauncherInstance,connect_existing
    from tests.test_ph_lw_04_05_acceptance import LiveServer
    with tempfile.TemporaryDirectory(prefix='harness-instance-') as folder:
        live=LiveServer(folder);base=live.service.app_data
        instance=LauncherInstance(base,live.port)
        try:
            self.assertEqual(connect_existing(base),live.origin+'/')
            record=json.loads((base/'launcher-instance.json').read_text('utf-8'))
            self.assertEqual(record,{'version':2,'pid':os.getpid(),'port':live.port})
            self.assertFalse((base/'launcher-private.json').exists())
        finally:instance.close();live.close()
        self.assertFalse((base/'launcher-instance.json').exists())
        for record in ({'version':2,'pid':0,'port':1234},{'version':2,'pid':os.getpid(),'port':True},
                       {'version':1,'identity':'old','key_dpapi':'unused'}):
            (base/'launcher-instance.json').write_text(json.dumps(record),'utf-8')
            with self.assertRaises(ValidationFailure):connect_existing(base)
''')

p=ENGINE/'local_web/windows/acceptance.py';s=p.read_text('utf-8')
s=s.replace("self.origin=url.split('/#')[0];self.port=int(self.origin.rsplit(':',1)[1]);self.cookie=self.csrf=None", "self.origin=url.rstrip('/');self.port=int(self.origin.rsplit(':',1)[1])")
s=s.replace("        self.auth=types.SimpleNamespace(issue_bootstrap=lambda:connect_existing(self.app_data).split('=')[1])\n",'')
write(p,s)
p=ENGINE/'local_web/windows/final_acceptance.py';s=p.read_text('utf-8')
s=s.replace("headers={'Origin':'http://foreign.invalid'})[0],401)","headers={'Origin':'http://foreign.invalid'})[0],403)")
s=s.replace("                token=live.ready()\n                self.assertEqual(live.request('POST','/api/session/bootstrap',value={'token':token})[0],401)","                live.ready()\n                self.assertEqual(live.request('GET','/api/projects')[0],200)")
s=s.replace(",\n                                {'X-CSRF-Token':'wrong'}",'')
s=s.replace("'checked_host_origin_csrf':True,'bootstrap_replay':True", "'checked_host_origin':True,'direct_entry_without_login':True")
write(p,s)

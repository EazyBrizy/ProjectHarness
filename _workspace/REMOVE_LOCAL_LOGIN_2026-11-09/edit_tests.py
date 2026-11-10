"""Migrate active fixtures to the explicitly approved no-login contract."""
import ast
from pathlib import Path
import re
import textwrap

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
TESTS=ENGINE/'tests'

def write(p,s):
    ast.parse(s)
    p.write_text(s,'utf-8')

def method(p,cls,name,code):
    s=p.read_text('utf-8');tree=ast.parse(s)
    c=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
    n=next(n for n in c.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    lines=s.splitlines(True)
    replacement=textwrap.indent(textwrap.dedent(code).strip()+'\n','    ')
    write(p,''.join(lines[:n.lineno-1])+replacement+''.join(lines[n.end_lineno:]))

p=TESTS/'test_ph_lw_04_http.py'
method(p,'LocalHttpDependencyIndependent','test_auth_bootstrap_one_use_rotation_expiry_idle_csrf','''
def test_local_login_implementation_removed(self):
    import project_harness.local_web_http as http
    self.assertFalse(hasattr(http, 'LocalWebAuth'))
    self.assertFalse(hasattr(http, 'SESSION_COOKIE'))
''')
method(p,'FlaskAppSecurityTests','login','''
def ready(self):
    self.assertEqual(self.call('GET','/api/projects').status_code,200)
''')
method(p,'FlaskAppSecurityTests','test_unauthenticated_all_private_routes_and_public_health_minimal','''
def test_direct_reads_without_login_and_removed_login_routes(self):
    for route in ('/api/projects', f'/api/projects/{self.pid}'):
        response=self.call('GET',route)
        self.assertEqual(response.status_code,200,response.json)
        self.assertNotIn('Set-Cookie',response.headers)
    for route in ('/api/session','/api/session/bootstrap','/api/session/logout'):
        self.assertEqual(self.call('GET',route).status_code,404)
        self.assertEqual(self.call('POST',route,body={},origin=self.origin).status_code,404)
    self.assertEqual(self.call('GET','/health').json,{'status':'ok'})
''')
method(p,'FlaskAppSecurityTests','test_token_replay_expiry_bad_host_origin_null_and_wrong_port','''
def test_exact_host_origin_null_port_and_proxy_rejected(self):
    for header in ('evil.example','127.0.0.1','127.0.0.1:9999',f'127.0.0.1:{self.port}.evil.example','localhost:48761'):
        self.assertEqual(self.call('GET','/api/projects',host=header).status_code,403)
    self.assertEqual(self.call('GET','/api/projects',origin='http://evil.example').status_code,403)
    self.assertEqual(self.call('POST',f'/api/projects/{self.pid}/operations',origin='null',body={}).status_code,403)
    self.assertEqual(self.call('POST',f'/api/projects/{self.pid}/operations',body={}).status_code,403)
    self.assertEqual(self.call('GET','/api/projects',headers={'X-Forwarded-Host':'evil.test'}).status_code,403)
    self.assertEqual(self.before,byte_snapshot(self.workspace))
''')
method(p,'FlaskAppSecurityTests','test_session_csrf_exact_json_and_security_headers','''
def test_no_login_mutation_exact_json_and_transport_headers(self):
    req={'action':'check-intake','payload':{},'idempotency_key':'no-login-check-001',
         'expected_fingerprint':self.service.get_status(self.pid)['fingerprint']}
    path=f'/api/projects/{self.pid}/operations'
    accepted=self.call('POST',path,body=req,origin=self.origin)
    self.assertEqual(accepted.status_code,202,accepted.json)
    self.service.wait_for(accepted.json['operation_id'],timeout=90)
    bad={**req,'root':'C:/Windows/System32'}
    self.assertEqual(self.call('POST',path,body=bad,origin=self.origin).status_code,400)
    response=self.call('GET','/api/projects')
    for name in ('Content-Security-Policy','X-Frame-Options','X-Content-Type-Options','Referrer-Policy','Cache-Control'):
        self.assertIn(name,response.headers)
    self.assertNotIn('Set-Cookie',response.headers)
    self.assertNotIn('Access-Control-Allow-Origin',response.headers)
    self.assertIn('no-store',response.headers['Cache-Control'])
''')
method(p,'FlaskAppSecurityTests','test_malformed_action_and_non_ascii_csrf_are_denied_without_mutation','''
def test_malformed_action_is_rejected_without_mutation(self):
    req={'action':[],'payload':{},'idempotency_key':'malformed-action-0001',
         'expected_fingerprint':self.service.get_status(self.pid)['fingerprint']}
    self.assertEqual(self.call('POST',f'/api/projects/{self.pid}/operations',body=req,origin=self.origin).status_code,400)
    self.assertEqual(self.before,byte_snapshot(self.workspace))
''')
method(p,'RealWaitressHttpTests','test_real_tcp_host_csrf_no_session_replay_body_limit','''
def test_real_tcp_direct_access_host_origin_and_body_limit(self):
    self.assertEqual(self.raw('GET','/api/projects')[0],200)
    self.assertEqual(self.raw('GET','/api/projects',host='localhost:'+str(self.port))[0],403)
    self.assertEqual(self.raw('GET','/api/projects',origin='http://foreign.invalid')[0],403)
    self.assertEqual(self.raw('POST','/api/intakes',body={},origin='null')[0],403)
    import http.client
    connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=6)
    try:
        connection.putrequest('POST','/api/intakes')
        connection.putheader('Content-Length','2000')
        connection.endheaders()
        self.assertEqual(connection.getresponse().status,413)
    finally:
        connection.close()
''')
s=p.read_text('utf-8').replace("        self.assertIn('history.replaceState', js)","        self.assertNotIn('/api/session', js)")
write(p,s)

p=TESTS/'test_ph_lw_04_05_acceptance.py'
method(p,'LiveServer','login','''
def ready(self):
    status,_,data=self.request('GET','/health')
    if status!=200 or data!={'status':'ok'}:
        raise AssertionError('Loopback listener is not ready')
''')
s=p.read_text('utf-8')
s=s.replace("        self.assertEqual(live.request('GET', path, authenticated=False)[0], 401)","        self.assertEqual(live.request('GET', path)[0], 200)")
s=s.replace("        self.assertEqual(live.request('POST', '/api/session/bootstrap', value={'token': token})[0], 401)\n",'')
s=s.replace(", {'X-CSRF-Token': 'wrong'}",'')
s=s.replace('        token = live.login()','        live.ready()')
s=s.replace('        token = live.auth.issue_bootstrap()\n        issued = time.monotonic()\n','')
start=s.index('        # Real monotonic expiry;');end=s.index('\n\n\n@unittest.skipUnless',start)
s=s[:start]+"        live.ready()\n        self.assertEqual(live.request('GET', '/api/projects')[0], 200)\n"+s[end:]
s=s.replace('test_real_bootstrap_elapsed_expiry_and_connection_limit','test_real_connection_limit_without_login')
write(p,s)

# Passive browser entry and session-free transport fixtures across active suites.
paths=[p for p in TESTS.glob('test_*.py') if any(x in p.read_text('utf-8') for x in ('LocalWebAuth','issue_bootstrap','session-state','authenticated=False'))]
paths += list((ENGINE/'local_web/windows').glob('*acceptance.py'))
for p in paths:
    s=p.read_text('utf-8')
    # All direct browser navigation is now a plain root URL.
    s=re.sub(r"([\w.]+\.origin)\s*\+\s*['\"]/#bootstrap=['\"]\s*\+\s*[\w.]+\.auth\.issue_bootstrap\(\)",r"\1 + '/'",s)
    s=s.replace("f'{self.origin}/#bootstrap={token}'","self.origin + '/'")
    s=s.replace("'#session-state'","'#connection-state'").replace('Сессия активна','Сервер готов')
    s=s.replace('.login()','.ready()')
    s=s.replace(', authenticated=True','').replace(',authenticated=True','')
    # Former absent-session negatives now exercise foreign-origin rejection.
    s=s.replace('authenticated=False',"headers={'Origin':'http://foreign.invalid'}")
    s=s.replace(', auth=self.auth','').replace(',auth=self.auth','')
    s=s.replace('self.service, self.auth, self.socket','self.service, self.socket')
    s=s.replace("'launcher-private.json'","'launcher-instance.json'")
    # These are test transport headers, not application authority.
    s=s.replace("'X-CSRF-Token': self.csrf",'').replace("'X-CSRF-Token':self.csrf",'')
    s=s.replace("'X-CSRF-Token': csrf",'').replace("'X-CSRF-Token':csrf",'')
    s=re.sub(r'\{\s*,','{',s)
    s=s.replace("if authenticated and self.cookie:\n            hdr.update({'Cookie': self.cookie, })",'')
    s=s.replace("if authenticated and self.cookie:hdr.update({'Cookie':self.cookie,})",'')
    s=s.replace("if authenticated and self.cookie:hdr.update({'Cookie':self.cookie,})",'')
    lines=s.splitlines(True)
    drop=[]
    for i,line in enumerate(lines):
        stripped=line.strip()
        if ('self.auth = LocalWebAuth(' in line or 'self.auth=LocalWebAuth(' in line or
            stripped.startswith('self.cookie = self.csrf =') or stripped.startswith('self.cookie=self.csrf=') or
            stripped.startswith('self.csrf = response.json') or stripped.startswith('self.csrf=response.json') or
            stripped.startswith("self.headers['X-CSRF-Token']") or
            stripped.startswith('token = self.auth.issue_bootstrap()') or
            stripped.startswith('token=self.auth.issue_bootstrap()') or
            stripped.startswith('csrf = self.ready()') or
            stripped.startswith('token = self.ready()')):
            drop.append(i)
    s=''.join(line for i,line in enumerate(lines) if i not in drop)
    # Remove imports of deleted login implementation/TTL constants only.
    lines=s.splitlines(True);edits=[]
    tree=ast.parse(s)
    for n in ast.walk(tree):
        if isinstance(n,ast.ImportFrom) and n.module=='project_harness.local_web_http':
            names=[a for a in n.names if a.name not in {'LocalWebAuth','BOOTSTRAP_TTL_SECONDS','SESSION_COOKIE','SESSION_IDLE_SECONDS','SESSION_TTL_SECONDS'}]
            if len(names)!=len(n.names):
                value=('from '+n.module+' import '+', '.join(a.name+((' as '+a.asname) if a.asname else '') for a in names)+'\n') if names else ''
                edits.append((n.lineno-1,n.end_lineno,value))
    for start,end,value in sorted(edits,reverse=True):lines[start:end]=[value]
    s=''.join(lines)
    write(p,s)

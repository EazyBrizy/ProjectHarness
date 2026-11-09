"""PH-LW-04 security tests: real service + Flask + Waitress + browser when available.

A SKIP on this runner is NOT equivalent to Windows/browser/Waitress acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib.util import find_spec
from importlib import resources
import json
import os
from pathlib import Path
from types import ModuleType
import socket
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest import mock

from project_harness.errors import ValidationFailure
from project_harness.intake import start_intake
from project_harness.local_web_http import (BOOTSTRAP_TTL_SECONDS, SESSION_COOKIE,
          JSON_BODY_LIMIT, WSGI_BODY_LIMIT, LocalWebAuth, WebError)
from project_harness.local_web_launcher import open_bound_loopback_socket, run_local_web
from project_harness.local_web_service import LocalWebService, OperationRequest
from tests.test_engine import prepare_demo
from tests.test_ph_lw_03_service import byte_snapshot

HAS_FLASK = find_spec('flask') is not None
HAS_WAITRESS = find_spec('waitress') is not None
HAS_PLAYWRIGHT = find_spec('playwright') is not None


class LocalHttpDependencyIndependent(unittest.TestCase):
    def test_auth_bootstrap_one_use_rotation_expiry_idle_csrf(self):
        now = [100.0]
        auth = LocalWebAuth(clock=lambda: now[0])
        first = auth.issue_bootstrap()
        replacement = auth.issue_bootstrap()
        with self.assertRaises(WebError): auth.exchange(first)
        cookie, csrf = auth.exchange(replacement)
        with self.assertRaises(WebError): auth.exchange(replacement)
        with self.assertRaises(WebError): auth.authorize(cookie, csrf='bad', mutation=True)
        self.assertIsNotNone(auth.authorize(cookie, csrf, mutation=True))
        auth.revoke(cookie)
        with self.assertRaises(WebError): auth.authorize(cookie)
        expired = auth.issue_bootstrap()
        now[0] += BOOTSTRAP_TTL_SECONDS + 1
        with self.assertRaises(WebError): auth.exchange(expired)
        valid = auth.issue_bootstrap()
        cookie, csrf = auth.exchange(valid)
        now[0] += 31 * 60
        with self.assertRaises(WebError): auth.authorize(cookie)

    def test_missing_web_dependencies_fail_before_binding_or_browser(self):
        with mock.patch.dict('sys.modules', {'flask': None}):
            with mock.patch('project_harness.local_web_launcher.open_bound_loopback_socket',
                            side_effect=AssertionError('listener should not bind')):
                with self.assertRaises(ValidationFailure):
                    run_local_web(open_browser=False)
        with mock.patch.dict('sys.modules', {'flask': ModuleType('flask'), 'waitress': None}):
            with mock.patch('project_harness.local_web_launcher.open_bound_loopback_socket',
                            side_effect=AssertionError('listener should not bind')):
                with self.assertRaises(ValidationFailure):
                    run_local_web(open_browser=False)

    def test_socket_is_prebound_ipv4_loopback_and_non_wildcard(self):
        with open_bound_loopback_socket() as sock:
            address, port = sock.getsockname()
            self.assertEqual(address, '127.0.0.1')
            self.assertTrue(1 <= port <= 65535)
            self.assertEqual(sock.family, socket.AF_INET)
            with self.assertRaises(OSError):
                same = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    same.bind(('127.0.0.1', port))
                finally:
                    same.close()

    def test_assets_are_local_text_only_and_no_dynamic_html(self):
        base = resources.files('project_harness').joinpath('resources/local_web/assets')
        js = base.joinpath('app.js').read_text(encoding='utf-8')
        html = base.joinpath('index.html').read_text(encoding='utf-8')
        css = base.joinpath('app.css').read_text(encoding='utf-8')
        self.assertIn('history.replaceState', js)
        self.assertIn('textContent', js)
        self.assertNotIn('innerHTML', js)
        self.assertNotIn('eval(', js)
        self.assertNotIn('http://', js + html + css)
        self.assertNotIn('https://', js + html + css)
        self.assertNotIn('<script>', html)
        self.assertNotIn('onerror=', html.lower())
        self.assertIn('type="button"', html)

    def test_service_catalog_no_path_and_artifact_owner_validation(self):
        with tempfile.TemporaryDirectory(prefix='lw04-base-') as tmp:
            base = Path(tmp)
            with LocalWebService(base/'app') as service:
                ws = base/'workspace'
                start_intake(ws, project_name='Новый проект', mode='GREENFIELD')
                project_id = service.register_existing(ws, kind='workspace')
                before = byte_snapshot(ws)
                listed = service.list_projects()
                self.assertEqual(len(listed), 1)
                self.assertEqual(listed[0]['project_id'], project_id)
                self.assertNotIn(str(ws), json.dumps(listed))
                with self.assertRaises(ValidationFailure):
                    service.read_handoff_artifact(project_id, 'LWO-'+'F'*32)
                self.assertEqual(before, byte_snapshot(ws))


@unittest.skipUnless(HAS_FLASK, 'Flask==3.1.3 unavailable: HTTP tests NOT RUN')
class FlaskAppSecurityTests(unittest.TestCase):
    def setUp(self):
        from project_harness.local_web_http import create_app
        self.temp = tempfile.TemporaryDirectory(prefix='lw04-flask-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.service = LocalWebService(self.base / 'appdata')
        self.addCleanup(self.service.close)
        self.workspace = self.base / 'workspace'
        start_intake(self.workspace, project_name='<script>bad</script>', mode='GREENFIELD')
        self.pid = self.service.register_existing(self.workspace, kind='workspace')
        self.clock = [1000.0]
        self.auth = LocalWebAuth(clock=lambda: self.clock[0])
        self.port = 48761
        self.app = create_app(self.service, port=self.port, auth=self.auth)
        self.client = self.app.test_client()
        self.origin = f'http://127.0.0.1:{self.port}'
        self.before = byte_snapshot(self.workspace)

    def call(self, method, url, *, body=None, origin=None, host=None, headers=None):
        args = {'base_url': self.origin, 'headers': dict(headers or {})}
        if origin is not None:
            args['headers']['Origin'] = origin
        if host is not None:
            args['headers']['Host'] = host
        if body is not None:
            args['data'] = json.dumps(body)
            args['content_type'] = 'application/json'
        return self.client.open(url, method=method, **args)

    def login(self):
        token = self.auth.issue_bootstrap()
        response = self.call('POST', '/api/session/bootstrap', body={'token': token}, origin=self.origin)
        self.assertEqual(response.status_code, 200, response.json)
        csrf = response.json['csrf']
        self.assertIn('HttpOnly', response.headers['Set-Cookie'])
        self.assertIn('SameSite=Strict', response.headers['Set-Cookie'])
        return csrf

    def test_unauthenticated_all_private_routes_and_public_health_minimal(self):
        for route in ('/api/projects', f'/api/projects/{self.pid}',
                      f'/api/projects/{self.pid}/operations/LWO-' + 'F'*32,
                      f'/api/projects/{self.pid}/artifacts/LWO-' + 'F'*32):
            r = self.call('GET', route)
            self.assertEqual(r.status_code, 401, (route, r.json))
            self.assertNotIn(str(self.base), r.get_data(as_text=True))
        h = self.call('GET', '/health')
        self.assertEqual(h.json, {'status': 'ok'})
        self.assertNotIn('0.5.1', h.get_data(as_text=True))
        self.assertEqual(self.call('GET', '/api/session').json, {'authenticated': False})

    def test_token_replay_expiry_bad_host_origin_null_and_wrong_port(self):
        token = self.auth.issue_bootstrap()
        bad = self.call('POST', '/api/session/bootstrap', body={'token':token}, origin='null')
        self.assertEqual(bad.status_code, 403)
        csrf = self.call('POST', '/api/session/bootstrap', body={'token':token}, origin=self.origin).json['csrf']
        replay = self.call('POST', '/api/session/bootstrap', body={'token':token}, origin=self.origin)
        self.assertEqual(replay.status_code, 401)
        new = self.auth.issue_bootstrap()
        self.clock[0] += BOOTSTRAP_TTL_SECONDS + 1
        self.assertEqual(self.call('POST', '/api/session/bootstrap', body={'token':new},origin=self.origin).status_code,401)
        for header in ('evil.example', '127.0.0.1', '127.0.0.1:9999',
                       f'127.0.0.1:{self.port}.evil.example', 'localhost:48761'):
            self.assertEqual(self.call('GET', '/api/projects',host=header).status_code,403)
        self.assertEqual(self.call('GET','/api/projects', origin='http://evil.example').status_code, 403)
        self.assertEqual(self.call('POST',f'/api/projects/{self.pid}/operations',origin='null',body={}).status_code,403)
        self.assertEqual(self.call('POST',f'/api/projects/{self.pid}/operations',body={}).status_code,403)
        self.assertEqual(self.call('GET', '/api/projects',headers={'X-Forwarded-Host':'evil.test'}).status_code,403)
        self.assertTrue(csrf)

    def test_session_csrf_exact_json_and_security_headers(self):
        csrf = self.login()
        req = {'action':'check-intake', 'payload':{}, 'idempotency_key':'test-csrf-check-001',
               'expected_fingerprint': self.service.get_status(self.pid)['fingerprint']}
        path = f'/api/projects/{self.pid}/operations'
        for invalid in (None, 'wrong'):
            r = self.call('POST',path,body=req,origin=self.origin,
                          headers={} if invalid is None else {'X-CSRF-Token':invalid})
            self.assertEqual(r.status_code, 403)
        accepted = self.call('POST',path,body=req,origin=self.origin,headers={'X-CSRF-Token':csrf})
        self.assertEqual(accepted.status_code,202,accepted.json)
        self.service.wait_for(accepted.json['operation_id'], timeout=90)
        bad_fields = {**req, 'root':'C:\\Windows\\System32'}
        self.assertEqual(self.call('POST',path,body=bad_fields,origin=self.origin,
                        headers={'X-CSRF-Token':csrf}).status_code,400)
        r = self.call('GET','/api/projects')
        for header in ('Content-Security-Policy','X-Frame-Options','X-Content-Type-Options',
                       'Referrer-Policy','Cache-Control'):
            self.assertIn(header,r.headers)
        self.assertIn("frame-ancestors 'none'",r.headers['Content-Security-Policy'])
        self.assertNotIn('Access-Control-Allow-Origin',r.headers)
        self.assertIn('no-store',r.headers['Cache-Control'])
        self.assertNotIn('Traceback',r.get_data(as_text=True))
        self.assertEqual(self.call('GET','/api/projects').status_code,200)

    def test_malformed_action_and_non_ascii_csrf_are_denied_without_mutation(self):
        csrf = self.login()
        path = f'/api/projects/{self.pid}/operations'
        req = {'action': [], 'payload': {}, 'idempotency_key': 'malformed-action-0001',
               'expected_fingerprint': self.service.get_status(self.pid)['fingerprint']}
        self.assertEqual(self.call('POST', path, body=req, origin=self.origin,
                         headers={'X-CSRF-Token': csrf}).status_code, 400)
        req['action'] = 'check-intake'
        self.assertEqual(self.call('POST', path, body=req, origin=self.origin,
                         headers={'X-CSRF-Token': '\u00e9'}).status_code, 403)
        self.assertEqual(self.before, byte_snapshot(self.workspace))

    def test_http_replay_after_commit_returns_original_operation(self):
        csrf = self.login()
        path = f'/api/projects/{self.pid}/operations'
        view = self.service.get_status(self.pid)
        req = {'action': 'update-draft', 'payload': {'patch': {'project.primary_outcome': 'Reviewed new outcome'},
               'expected_input_digest': view['refs']['input_digest']},
               'idempotency_key': 'http-replay-after-commit-001', 'expected_fingerprint': view['fingerprint']}
        headers = {'X-CSRF-Token': csrf}
        first = self.call('POST', path, body=req, origin=self.origin, headers=headers)
        self.assertEqual(first.status_code, 202, first.json)
        op = self.service.wait_for(first.json['operation_id'], timeout=90)
        self.assertEqual(op['state'], 'SUCCEEDED', op.get('error'))
        self.assertNotEqual(req['expected_fingerprint'], self.service.get_status(self.pid)['fingerprint'])
        committed = byte_snapshot(self.workspace)
        replay = self.call('POST', path, body=req, origin=self.origin, headers=headers)
        self.assertEqual(replay.status_code, 202, replay.json)
        self.assertEqual(replay.json['operation_id'], first.json['operation_id'])
        self.assertEqual(replay.json['state'], 'SUCCEEDED')
        conflict = self.call('POST', path, body={**req, 'payload': {'unexpected': True}},
                             origin=self.origin, headers=headers)
        self.assertIn(conflict.status_code, (400, 409))
        self.assertEqual(committed, byte_snapshot(self.workspace))

    def test_get_refresh_read_only_xss_text_and_download_paths_rejected(self):
        self.login()
        for _ in range(3):
            view = self.call('GET',f'/api/projects/{self.pid}')
            self.assertEqual(view.status_code,200,view.json)
            self.assertEqual(view.json['project']['project_id'],self.pid)
            self.assertEqual(self.call('GET','/').status_code,200)
            self.assertEqual(self.call('GET','/assets/app.js').status_code,200)
        self.assertEqual(self.before, byte_snapshot(self.workspace))
        self.assertIn('textContent',self.call('GET','/assets/app.js').get_data(as_text=True))
        for invalid in ('..', '%2e%2e', 'C:%5cWindows', 'etc%2fpasswd'):
            r=self.call('GET',f'/api/projects/{self.pid}/artifacts/{invalid}')
            self.assertNotEqual(r.status_code,200)
        self.assertEqual(self.call('GET','/assets/unknown.js').status_code,404)

    def test_no_access_to_another_project_artifact_and_tamper(self):
        self.login()
        _, _, root = prepare_demo(self.base / 'fixture')
        other_pid = self.service.register_existing(root, kind='project')
        work, _handoff, _root = prepare_demo(self.base / 'fixture2')
        approved_pid = self.service.register_existing(work, kind='workspace')
        status = self.service.get_status(approved_pid)
        op = self.service.submit(OperationRequest(approved_pid, 'prepare', {},
                                  'web-prepare-good-00001', status['fingerprint']))
        completed = self.service.wait_for(op['operation_id'],timeout=90)
        self.assertEqual(completed['state'],'SUCCEEDED', completed.get('error'))
        oid = op['operation_id']
        url = f'/api/projects/{approved_pid}/artifacts/{oid}'
        self.assertEqual(self.call('GET',url).status_code,200)
        self.assertEqual(self.call('GET',f'/api/projects/{other_pid}/artifacts/{oid}').status_code,400)
        p = self.service.app_data / 'artifacts' / oid / 'handoff.zip'
        p.write_bytes(b'tampered')
        self.assertEqual(self.call('GET',url).status_code,400)


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS, 'Flask/Waitress unavailable: real WSGI NOT RUN')
class RealWaitressHttpTests(unittest.TestCase):
    """Actual TCP listener; no app.test_client shortcuts."""
    def setUp(self):
        from waitress import create_server
        from project_harness.local_web_http import create_app
        self.temp = tempfile.TemporaryDirectory(prefix='lw04-wsgi-')
        self.addCleanup(self.temp.cleanup)
        self.service = LocalWebService(Path(self.temp.name)/'appdata')
        self.addCleanup(self.service.close)
        sock = open_bound_loopback_socket()
        self.sock = sock
        self.port = sock.getsockname()[1]
        self.auth = LocalWebAuth()
        self.origin = f'http://127.0.0.1:{self.port}'
        app = create_app(self.service, port=self.port, auth=self.auth)
        self.server = create_server(app, sockets=[sock], threads=2, channel_timeout=5,
                                    connection_limit=16, max_request_body_size=1024,
                                    max_request_header_size=4096, expose_tracebacks=False,
                                    trusted_proxy=None, clear_untrusted_proxy_headers=True)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.close()
        self.sock.close()
        self.thread.join(timeout=8)

    def raw(self, method, path, *, body=None, origin=None, host=None, cookie=None, csrf=None):
        data = json.dumps(body).encode('utf-8') if body is not None else None
        headers = {'Host':host or f'127.0.0.1:{self.port}'}
        if origin is not None: headers['Origin'] = origin
        if csrf is not None: headers['X-CSRF-Token'] = csrf
        if cookie is not None: headers['Cookie'] = cookie
        if data is not None: headers['Content-Type'] = 'application/json'
        request = Request(self.origin + path, method=method, data=data, headers=headers)
        try:
            with urlopen(request, timeout=6) as res:
                return res.status, dict(res.headers.items()), res.read()
        except HTTPError as err:
            try:
                return err.code, dict(err.headers.items()), err.read()
            finally:
                err.close()

    def test_real_tcp_host_csrf_no_session_replay_body_limit(self):
        health = self.raw('GET','/health')
        self.assertEqual(health[0],200)
        self.assertEqual(json.loads(health[2]),{'status':'ok'})
        self.assertEqual(self.raw('GET','/api/projects')[0],401)
        self.assertEqual(self.raw('GET','/api/projects',host='evil.example')[0],403)
        tok = self.auth.issue_bootstrap()
        self.assertEqual(self.raw('POST','/api/session/bootstrap',body={'token':tok},origin='null')[0],403)
        valid = self.raw('POST','/api/session/bootstrap',body={'token':tok},origin=self.origin)
        self.assertEqual(valid[0],200,valid)
        cookie=valid[1]['Set-Cookie'].split(';',1)[0]
        self.assertEqual(self.raw('POST','/api/session/bootstrap',body={'token':tok},origin=self.origin)[0],401)
        self.assertEqual(self.raw('GET','/api/projects',cookie=cookie)[0],200)
        # A WSGI-layer limit should stop oversized bodies even before Flask.
        # Send the declaration first: Windows may reset a connection if body
        # bytes race the early 413 close. Actual streamed bytes are covered by
        # the production-limit acceptance test, not this reduced-limit fixture.
        import http.client
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=6)
        try:
            connection.putrequest('POST', '/api/session/bootstrap')
            connection.putheader('Content-Length', '2000')
            connection.endheaders()
            self.assertEqual(connection.getresponse().status, 413)
        finally:
            connection.close()

    def test_not_bound_to_nonloopback_lan_if_available(self):
        candidates=set()
        try:
            for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
                ip=item[4][0]
                if not ip.startswith('127.') and ip!='0.0.0.0':candidates.add(ip)
        except OSError: pass
        if not candidates: self.skipTest('No nonloopback LAN IP on Linux host')
        for ip in candidates:
            with self.assertRaises((ConnectionRefusedError, TimeoutError, OSError)):
                socket.create_connection((ip,self.port),timeout=.3)


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS and HAS_PLAYWRIGHT,
                     'Flask/Waitress/Playwright unavailable: real browser NOT RUN')
class LocalBrowserTests(RealWaitressHttpTests):
    def test_browser_bootstrap_fragment_removed_no_external_requests_xss_inert(self):
        from playwright.sync_api import sync_playwright
        workspace = Path(self.temp.name)/'malicious-workspace'
        start_intake(workspace, project_name='<img src=x onerror=alert(1)>', mode='GREENFIELD')
        pid = self.service.register_existing(workspace, kind='workspace')
        original_status = self.service.get_status
        def malicious_status(project_id):
            view = original_status(project_id)
            view['blockers'] = ['<img src=x onerror=window.__injected=1>',
                                '<script>window.__injected=2</script>',
                                '[bad](javascript:alert(1))']
            return view
        token = self.auth.issue_bootstrap()
        with mock.patch.object(self.service, 'get_status', side_effect=malicious_status):
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, **({'channel': os.environ['PH_LW_04_BROWSER_CHANNEL']} if os.environ.get('PH_LW_04_BROWSER_CHANNEL') else {}))
                try:
                    page = browser.new_page()
                    requests = []
                    page.on('request', lambda req: requests.append(req.url))
                    page.goto(f'{self.origin}/#bootstrap={token}',wait_until='networkidle',timeout=20000)
                    self.assertNotIn('bootstrap',page.url)
                    self.assertEqual(page.locator('#session-state').inner_text(),'Сессия активна')
                    page.get_by_role('button',name=pid).click()
                    page.locator('#blockers').wait_for(state='visible')
                    self.assertIn('<img src=x',page.locator('#blockers').inner_text())
                    self.assertEqual(page.locator('script:not([src])').count(),0)
                    self.assertTrue(all(url.startswith(self.origin + '/') for url in requests))
                    self.assertEqual(page.locator('iframe').count(),0)
                    self.assertEqual(page.locator('img').count(),0)
                    self.assertIsNone(page.evaluate('window.__injected'))
                finally: browser.close()


if __name__ == '__main__':
    unittest.main()

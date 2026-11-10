"""Native HTTP/browser acceptance of production Waitress and source import.

Synthetic documents only. Browser actions use public HTTP; no fabricated
approvals, private canonical edits or automatic product execution.
"""
from __future__ import annotations
import http.client
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
import zipfile

from project_harness.local_web_http import WSGI_BODY_LIMIT
from project_harness.local_web_launcher import create_loopback_server, open_bound_loopback_socket
from project_harness.local_web_service import LocalWebService
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_04_http import HAS_FLASK, HAS_WAITRESS, HAS_PLAYWRIGHT
from tests.test_ph_lw_05_import import archive


class LiveServer:
    def __init__(self, directory):
        self.service = LocalWebService(Path(directory) / 'app')
        self.socket = open_bound_loopback_socket()
        self.port = self.socket.getsockname()[1]
        self.origin = f'http://127.0.0.1:{self.port}'
        self.server = create_loopback_server(self.service, self.socket)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()

    def close(self):
        self.server.close()
        self.thread.join(timeout=8)
        self.socket.close()
        self.service.close()

    def request(self, method, path, *, value=None, data=None, headers=None):
        hdr = {'Origin': self.origin}
        
        if value is not None:
            data = json.dumps(value).encode('utf-8')
            hdr['Content-Type'] = 'application/json'
        hdr.update(headers or {})
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        try:
            conn.request(method, path, body=data, headers=hdr)
            res = conn.getresponse()
            raw = res.read()
            return res.status, dict(res.getheaders()), json.loads(raw) if raw.startswith(b'{') else raw
        finally:
            conn.close()

    def ready(self):
        status,_,data=self.request('GET','/health')
        if status!=200 or data!={'status':'ok'}:
            raise AssertionError('Loopback listener is not ready')

    def create(self, key='live-create-intake-00001'):
        status, _, data = self.request('POST', '/api/intakes', value={
            'project_name': 'Тест приёмки', 'no_documentation': False, 'idempotency_key': key})
        if status != 201:
            raise AssertionError((status, data))
        return data['project_id']

    def upload(self, pid, documents, *, extra=(), headers=None):
        status = self.request('GET', f'/api/projects/{pid}')[2]['project']
        sources = self.request('GET', f'/api/projects/{pid}/sources')[2]
        boundary = 'HarnessAcceptanceBoundary071126'
        chunks = []
        fields = [('mode', 'append'), ('expected_fingerprint', status['fingerprint']),
                  ('expected_source_revision', str(sources['source_revision'])), *extra]
        for name, value in fields:
            chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        for name, data in documents:
            chunks += [f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode(), data, b'\r\n']
        chunks.append(f'--{boundary}--\r\n'.encode())
        return self.request('POST', f'/api/projects/{pid}/sources/upload', data=b''.join(chunks),
                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}', **(headers or {})})


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS, 'Real Flask/Waitress required')
class ProductionHttpAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='lw0405-live-')
        self.addCleanup(self.temp.cleanup)
        self.live = LiveServer(self.temp.name)
        self.addCleanup(lambda: self.live.close())

    def test_real_upload_malicious_archives_auth_and_read_only_preview(self):
        live = self.live
        live.ready()
        pid = live.create()
        path = f'/api/projects/{pid}'
        self.assertEqual(live.request('GET', path)[0], 200)
        for headers in ({'Host': 'evil.test'}, {'Host': '127.0.0.1:1'}, {'Origin': 'null'},
                        {'Origin': 'http://127.0.0.1:1'}):
            self.assertEqual(live.upload(pid, [('ok.md', b'plain')], headers=headers)[0], 403)
        self.assertEqual(live.upload(pid, [('ok.md', b'plain')], extra=[('mode', 'replace')])[0], 400)
        for bad in (archive([('../escape.md', b'x')]), archive([('NUL.md', b'x')]),
                    archive([('a\\b.md', b'x')]), archive([('a.md', b'a'), ('A.md', b'b')])):
            self.assertEqual(live.upload(pid, [('hostile.zip', bad)])[0], 400)
            self.assertEqual(live.request('GET', path + '/sources')[2]['source_revision'], 0)
        zipdata = archive([('Раздел с пробелом/Требования.md', '# Текст'.encode()), ('image.png', b'ignored')])
        hostile_md = b'<img src="https://invalid.example/" onerror="window.__injected=1">'
        result = live.upload(pid, [('Документы.zip', zipdata), ('source.md', hostile_md)])
        self.assertEqual(result[0], 200, result[2])
        self.assertEqual(result[2]['accepted_count'], 2)
        self.assertEqual(result[2]['skipped_count'], 1)
        before = byte_snapshot(live.service.app_data.parent)
        inventory = live.request('GET', path + '/sources')[2]
        for doc in inventory['documents']:
            preview = live.request('GET', path + f'/documents/{doc["document_ref"]}/preview')
            self.assertEqual(preview[0], 200)
            self.assertEqual(preview[2]['rendering'], 'ESCAPED_PLAIN_TEXT')
        self.assertEqual(before, byte_snapshot(live.service.app_data.parent))
        other = live.create('live-create-intake-00002')
        docref = inventory['documents'][0]['document_ref']
        self.assertEqual(live.request('GET', f'/api/projects/{other}/documents/{docref}/preview')[0], 400)
        self.assertEqual(live.upload(pid, [('Документы.zip', zipdata), ('source.md', hostile_md)])[2]['status'], 'UNCHANGED')

    def test_production_wsgi_declared_and_chunked_body_header_and_idle_limits(self):
        live = self.live
        # These are the actual production listener settings, not reduced limits.
        conn = http.client.HTTPConnection('127.0.0.1', live.port, timeout=10)
        try:
            conn.putrequest('POST', '/api/intakes')
            conn.putheader('Origin', live.origin)
            conn.putheader('Content-Length', str(WSGI_BODY_LIMIT + 1))
            conn.endheaders()
            self.assertEqual(conn.getresponse().status, 413)
        finally:
            conn.close()
        self.assertEqual(live.request('GET', '/health', headers={'X-Large': 'x' * (17 * 1024)})[0], 431)
        conn = http.client.HTTPConnection('127.0.0.1', live.port, timeout=15)
        try:
            conn.putrequest('POST', '/api/intakes')
            conn.putheader('Origin', live.origin)
            conn.putheader('Transfer-Encoding', 'chunked')
            conn.endheaders()
            # Chunked input has no Content-Length: exercise actual received bytes.
            conn.send(f'{WSGI_BODY_LIMIT + 1:x}\r\n'.encode())
            for _ in range(64):
                conn.send(b'x' * (1024 * 1024))
            conn.send(b'x\r\n0\r\n\r\n')
            self.assertEqual(conn.getresponse().status, 413)
        finally:
            conn.close()
        # A partial request must be dropped by channel_timeout, not remain forever.
        with socket.create_connection(('127.0.0.1', live.port), timeout=2) as idle:
            idle.sendall(b'GET /health HTTP/1.1\r\n')
            idle.settimeout(55)
            self.assertEqual(idle.recv(1), b'')

    def test_http_operation_replay_after_restart_and_new_stale_request(self):
        live = self.live
        live.ready()
        pid = live.create()
        path = f'/api/projects/{pid}'
        view = live.request('GET', path)[2]['project']
        request = {'action': 'update-draft', 'payload': {
            'patch': {'project.primary_outcome': 'Explicit new outcome'},
            'expected_input_digest': view['refs']['input_digest']},
            'idempotency_key': 'live-op-replay-after-commit', 'expected_fingerprint': view['fingerprint']}
        first = live.request('POST', path + '/operations', value=request)
        self.assertEqual(first[0], 202, first[2])
        oid = first[2]['operation_id']
        self.assertEqual(live.service.wait_for(oid, timeout=90)['state'], 'SUCCEEDED')
        before = byte_snapshot(Path(self.temp.name))
        live.close()
        live = self.live = LiveServer(self.temp.name)
        live.ready()
        replay = live.request('POST', path + '/operations', value=request)
        self.assertEqual(replay[0], 202, replay[2])
        self.assertEqual(replay[2], {'operation_id': oid, 'state': 'SUCCEEDED'})
        stale = live.request('POST', path + '/operations', value={**request, 'idempotency_key': 'new-stale-operation-key'})
        self.assertEqual(stale[0], 409)
        changed = {**request, 'expected_fingerprint': live.request('GET', path)[2]['project']['fingerprint']}
        self.assertEqual(live.request('POST', path + '/operations', value=changed)[0], 409)
        self.assertEqual(before, byte_snapshot(Path(self.temp.name)))

    def test_real_connection_limit_without_login(self):
        live = self.live
        sockets = []
        try:
            for _ in range(36):
                conn = socket.create_connection(('127.0.0.1', live.port), timeout=2)
                conn.sendall(b'GET /health HTTP/1.1\r\n')
                sockets.append(conn)
            deadline = time.monotonic() + 3
            while not live.server.in_connection_overflow and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue(live.server.in_connection_overflow)
            self.assertLessEqual(len(live.server._map), live.server.adj.connection_limit)
            self.assertEqual(live.server.adj.connection_limit, 32)
        finally:
            for conn in sockets:
                conn.close()
        live.ready()
        self.assertEqual(live.request('GET', '/api/projects')[0], 200)



@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS and HAS_PLAYWRIGHT, 'Real Edge/Waitress required')
class BrowserImportAcceptance(unittest.TestCase):
    def test_foreign_origin_browser_form_fetch_and_frame_are_denied(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        from playwright.sync_api import sync_playwright, expect
        class ForeignPage(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body>Foreign local origin</body></html>')
            def log_message(self, *args):
                pass
        with tempfile.TemporaryDirectory(prefix='lw04-origin-') as directory:
            live = LiveServer(directory)
            foreign = ThreadingHTTPServer(('127.0.0.1', 0), ForeignPage)
            thread = threading.Thread(target=foreign.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(channel='msedge', headless=True)
                    try:
                        page = browser.new_page()
                        page.set_default_timeout(10000)
                        page.set_default_navigation_timeout(10000)
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        before = byte_snapshot(Path(directory))
                        page.goto(f'http://127.0.0.1:{foreign.server_port}')
                        # CORS failures do not emit Playwright's ordinary response
                        # event. CDP records the actual HTTP status before CORS hides it.
                        network = page.context.new_cdp_session(page)
                        network.send('Network.enable')
                        urls, statuses = {}, {}
                        network.on('Network.requestWillBeSent', lambda e: urls.update({e['requestId']: e['request']['url']}))
                        network.on('Network.responseReceivedExtraInfo', lambda e: statuses.update({e['requestId']: e['statusCode']}))
                        outcome = page.evaluate('''async origin => {
                              try { await fetch(origin + '/api/intakes', {method:'POST', credentials:'include', signal:AbortSignal.timeout(5000),
                                headers:{'Content-Type':'text/plain'}, body:JSON.stringify({project_name:'attack',
                                  no_documentation:true,idempotency_key:'foreign-browser-create'})}); return 'readable'; }
                              catch (_) { return 'blocked'; }
                            }''', live.origin)
                        page.wait_for_timeout(300)
                        denied = [status for rid, status in statuses.items()
                                  if urls.get(rid) == live.origin + '/api/intakes']
                        self.assertEqual(denied, [403])
                        self.assertEqual(outcome, 'blocked')
                        with page.expect_response(lambda r: r.url == live.origin + '/api/intakes') as response:
                            page.evaluate('''origin => {
                              const target=document.createElement('iframe'); target.name='attack-target';
                              document.body.append(target);
                              const f=document.createElement('form'); f.method='POST'; f.action=origin+'/api/intakes';
                              f.target='attack-target';
                              document.body.append(f); f.submit();
                            }''', live.origin)
                        self.assertEqual(response.value.status, 403)
                        page.evaluate('''origin => { const f=document.createElement('iframe');
                          f.src=origin+'/'; document.body.append(f); }''', live.origin)
                        page.wait_for_timeout(500)
                        self.assertFalse(any(frame.url == live.origin + '/' for frame in page.frames[1:]))
                        self.assertEqual(before, byte_snapshot(Path(directory)))
                    finally:
                        browser.close()
            finally:
                foreign.shutdown()
                foreign.server_close()
                thread.join(timeout=3)
                live.close()

    def test_ui_upload_preview_duplicate_replace_and_no_documentation(self):
        from playwright.sync_api import sync_playwright, expect
        with tempfile.TemporaryDirectory(prefix='lw0405-browser-') as directory:
            live = LiveServer(directory)
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL', 'msedge'), headless=True)
                    try:
                        page = browser.new_page()
                        requests, errors = [], []
                        page.on('request', lambda request: requests.append(request.url))
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.on('dialog', lambda dialog: dialog.accept())
                        page.goto(live.origin + '/')
                        expect(page.locator('#connection-state')).to_have_text('Сервер готов')
                        self.assertNotIn('#', page.url)
                        page.locator('[data-screen="documents"]').click()
                        page.locator('#new-project-name').fill('Браузерная приёмка')
                        page.locator('#create-intake').click()
                        expect(page.locator('#source-summary')).to_contain_text('Revision 0')
                        expect(page.get_by_role('button', name='Проверить опрос', exact=True, include_hidden=True)).to_be_enabled()
                        data = archive([('Раздел/Требования.md', b'<img src="https://invalid.example/" onerror="window.__injected=1">'),
                                        ('diagram.svg', b'<svg/>')])
                        file = {'name': 'Документы.zip', 'mimeType': 'application/zip', 'buffer': data}
                        for revision, mode in ((1, 'append'), (1, 'append'), (2, 'replace')):
                            if mode == 'replace':
                                file = {'name': 'Новые.md', 'mimeType': 'text/markdown', 'buffer': '# Новое'.encode()}
                            page.locator('#source-import-mode').select_option(mode)
                            page.locator('#source-files').set_input_files(file)
                            expect(page.locator('#upload-sources')).to_be_enabled()
                            page.locator('#upload-sources').click()
                            expect(page.locator('#upload-result')).to_contain_text(f'ревизия: {revision}', timeout=20000)
                            expect(page.locator('#source-summary')).to_contain_text(f'Revision {revision}')
                            expect(page.get_by_role('button', name='Проверить опрос', exact=True, include_hidden=True)).to_be_enabled()
                            page.locator('#source-list button').first.click()
                            expect(page.locator('#source-preview')).not_to_be_empty()
                            self.assertEqual(page.locator('img, iframe, script:not([src])').count(), 0)
                            self.assertIsNone(page.evaluate('window.__injected'))
                        expect(page.locator('#confirm-no-docs')).to_be_enabled()
                        page.locator('#confirm-no-docs').click()
                        expect(page.locator('#source-summary')).to_contain_text('NONE')
                        before = byte_snapshot(Path(directory))
                        page.reload(wait_until='networkidle')
                        self.assertEqual(before, byte_snapshot(Path(directory)))
                        self.assertTrue(all(url.startswith(live.origin + '/') for url in requests))
                        self.assertFalse(errors, errors)
                    finally:
                        browser.close()
            finally:
                live.close()


if __name__ == '__main__':
    unittest.main()

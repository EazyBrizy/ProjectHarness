"""PH-LW-05 actual Flask multipart/security tests (SKIP if Flask unavailable)."""
from __future__ import annotations
from importlib.util import find_spec
from io import BytesIO
from pathlib import Path
import json
import tempfile
import unittest

from project_harness.local_web_service import LocalWebService
from project_harness.local_web_http import LocalWebAuth

HAS_FLASK = find_spec('flask') is not None


@unittest.skipUnless(HAS_FLASK, 'Flask 3.1.3 unavailable: real HTTP multipart security NOT RUN')
class SourceHttpSecurity(unittest.TestCase):
    def setUp(self):
        from project_harness.local_web_http import create_app
        self.temp = tempfile.TemporaryDirectory(prefix='ph-lw05-http-')
        self.addCleanup(self.temp.cleanup)
        self.service = LocalWebService(Path(self.temp.name) / 'app')
        self.addCleanup(self.service.close)
        self.auth = LocalWebAuth()
        self.port = 54931
        self.origin = 'http://127.0.0.1:54931'
        self.app = create_app(self.service, port=self.port, auth=self.auth)
        self.client = self.app.test_client()
        self.host = {'Host': '127.0.0.1:54931', 'Origin': self.origin}
        token = self.auth.issue_bootstrap()
        response = self.client.post('/api/session/bootstrap', json={'token': token}, headers=self.host)
        self.assertEqual(response.status_code, 200)
        self.csrf = response.json['csrf']
        self.secure = {**self.host, 'X-CSRF-Token': self.csrf}
        created = self.client.post('/api/intakes', headers=self.secure,
                 json={'project_name': 'Демо PH-LW-05', 'no_documentation': False,
                       'idempotency_key': 'http-create-intake-key-12'})
        self.assertEqual(created.status_code, 201, created.json)
        self.pid = created.json['project_id']

    def _upload(self, name='requirements.md', data=b'# Doc', *, headers=None, fields=None):
        base = self.service.get_status(self.pid)
        row = self.service.list_sources(self.pid)
        payload = {'mode': 'append', 'expected_fingerprint': base['fingerprint'],
                   'expected_source_revision': str(row['source_revision']),
                   'files': (BytesIO(data), name)}
        if fields:
            payload.update(fields)
        return self.client.post(f'/api/projects/{self.pid}/sources/upload',
                headers=self.secure if headers is None else headers, data=payload,
                content_type='multipart/form-data')

    def test_auth_upload_list_preview_and_replay(self):
        unauth = self.app.test_client().get(f'/api/projects/{self.pid}/sources', headers=self.host)
        self.assertEqual(unauth.status_code, 401)
        self.assertEqual(self._upload(headers=self.host).status_code, 403)
        self.assertEqual(self._upload(headers={**self.secure, 'Host': 'localhost:54931'}).status_code, 403)
        self.assertEqual(self._upload(headers={**self.secure, 'Origin': 'null'}).status_code, 403)
        post = self._upload(data=b'<img src=x onerror=alert(1)>')
        self.assertEqual(post.status_code, 200, post.json)
        self.assertEqual(post.json['accepted_count'], 1)
        data = self.client.get(f'/api/projects/{self.pid}/sources', headers=self.host)
        self.assertEqual(data.status_code, 200)
        self.assertEqual(data.json['source_revision'], 1)
        self.assertNotIn(str(self.temp.name), json.dumps(data.json))
        doc = data.json['documents'][0]['document_ref']
        preview = self.client.get(f'/api/projects/{self.pid}/documents/{doc}/preview', headers=self.host)
        self.assertEqual(preview.status_code, 200)
        self.assertIn('<img', preview.json['preview_text'])
        self.assertEqual(preview.json['rendering'], 'ESCAPED_PLAIN_TEXT')
        same = self._upload(data=b'<img src=x onerror=alert(1)>')
        self.assertEqual(same.status_code, 200)
        self.assertEqual(same.json['status'], 'UNCHANGED')

    def test_malformed_upload_rejected_and_unknown_fields(self):
        for fields in ({'injected_path': '/etc/passwd'}, {'expected_source_revision': '-1'},
                       {'expected_fingerprint': 'sha256:' + '0'*64}):
            result = self._upload(fields=fields)
            self.assertIn(result.status_code, (400, 409), result.json)
        reject = self._upload(name='../evil.md')
        self.assertIn(reject.status_code, (400, 409))
        self.assertEqual(self.client.get(f'/api/projects/{self.pid}/sources',
                          headers=self.host).json['source_revision'], 0)
        missing = self.app.test_client().post('/api/intakes', headers=self.host,
                            json={'project_name': 'Insecure', 'no_documentation': True,
                                  'idempotency_key': 'unauth-create-intake-1'})
        self.assertEqual(missing.status_code, 401)

    def test_duplicate_multipart_scalar_fields_are_rejected(self):
        from werkzeug.datastructures import MultiDict
        before = self.service.get_status(self.pid)['fingerprint']
        for field, duplicate in (('mode', 'replace'), ('expected_source_revision', '1'),
                                  ('expected_fingerprint', 'sha256:' + '0'*64)):
            with self.subTest(field=field):
                payload = MultiDict([('mode', 'append'), ('expected_fingerprint', before),
                                     ('expected_source_revision', '0'), (field, duplicate),
                                     ('files', (BytesIO(b'# valid'), 'doc.md'))])
                result = self.client.post(f'/api/projects/{self.pid}/sources/upload',
                           headers=self.secure, data=payload, content_type='multipart/form-data')
                self.assertEqual(result.status_code, 400, result.json)
                self.assertEqual(self.service.list_sources(self.pid)['source_revision'], 0)
                self.assertEqual(self.service.get_status(self.pid)['fingerprint'], before)

    def test_documentation_none_after_import_explicit_and_no_external_requests(self):
        self.assertEqual(self._upload().status_code, 200)
        view = self.service.get_status(self.pid)
        choice = self.client.post(f'/api/projects/{self.pid}/sources/no-documentation',
                    headers=self.secure, json={'expected_fingerprint': view['fingerprint'],
                        'expected_source_revision': 1})
        self.assertEqual(choice.status_code, 200, choice.json)
        self.assertEqual(self.client.get(f'/api/projects/{self.pid}/sources',
                        headers=self.host).json['documents'], [])
        self.assertEqual(self.client.get(f'/api/projects/{self.pid}/sources',
                        headers=self.host).json['documentation_choice'], 'NONE')
        for method in ('get', 'post'):
            client = self.app.test_client()
            result = getattr(client, method)(f'/api/projects/{self.pid}/sources/recover',
                              headers=self.host, json={'confirm': True} if method == 'post' else None)
            self.assertIn(result.status_code, (401, 405))


if __name__ == '__main__':
    unittest.main()

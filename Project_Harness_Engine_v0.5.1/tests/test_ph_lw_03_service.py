"""PH-LW-03 application service: real core, durable boundaries, no HTTP mocks."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from project_harness.errors import ValidationFailure
from project_harness.hashing import sha256_file
from project_harness.intake import start_intake, check_intake
from project_harness.local_web_drafts import DRAFT_FIELDS, draft_input_digest, update_provisional_draft
from project_harness.local_web_service import LocalWebService, OperationRequest
from project_harness.operation_guard import project_operation_guard
from project_harness.serialization import load_data
from project_harness.runtime import next_task
from tests.test_engine import prepare_demo

ROOT = Path(__file__).resolve().parents[1]


def byte_snapshot(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


class LocalWebServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='lw03-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.service = LocalWebService(self.base / 'app-data')
        self.addCleanup(self.service.close)

    def workspace(self, *, approved=False):
        if approved:
            ws, _, _ = prepare_demo(self.base / 'fixture')
        else:
            ws = self.base / 'workspace'
            start_intake(ws, project_name='Без документации', mode='GREENFIELD')
        return ws, self.service.register_existing(ws, kind='workspace')

    def project(self):
        _, _, root = prepare_demo(self.base / 'fixture')
        return root, self.service.register_existing(root, kind='project')

    def request(self, pid, action, *, payload=None, key='key-unique-00000001', fingerprint=None):
        return OperationRequest(pid, action, payload if payload is not None else {}, key,
                                fingerprint or self.service.get_status(pid)['fingerprint'])

    def run_operation(self, req):
        first = self.service.submit(req)
        return self.service.wait_for(first['operation_id'], timeout=90)

    def test_01_status_provisional_is_read_only_even_with_pending_input(self):
        root, pid = self.workspace()
        old = byte_snapshot(root)
        views = [self.service.get_status(pid) for _ in range(3)]
        self.assertEqual(byte_snapshot(root), old)
        self.assertTrue(all(x['core_status'] == 'WAITING_INPUT' for x in views))
        self.assertTrue(all(x['required_user_action'] for x in views))
        self.assertEqual(views[0]['fingerprint'], views[-1]['fingerprint'])
        self.assertEqual(len(views[0]['available_actions']), 27)
        self.assertEqual(len({x['id'] for x in views[0]['available_actions']}), 27)
        self.assertFalse(next(a for a in views[0]['available_actions'] if a['action'] == 'execute-current')['enabled'])
        self.assertTrue(next(a for a in views[0]['available_actions'] if a['action'] == 'update-draft')['enabled'])

    def test_02_project_status_is_byte_identical_with_stage_refs(self):
        root, pid = self.project()
        old = byte_snapshot(root)
        status = self.service.get_status(pid)
        self.assertEqual(byte_snapshot(root), old)
        self.assertEqual(status['core_status'], 'ACTIVE')
        self.assertTrue(status['refs']['stage_plan_ref'])
        self.assertTrue(status['refs']['gate_ref'])
        self.assertTrue(status['refs']['active_run']['run_ref'])
        self.assertIn('next', [x['action'] for x in status['available_actions']])

    def test_03_check_intake_WAITING_INPUT_is_not_internal_error_and_replay(self):
        root, pid = self.workspace()
        req = self.request(pid, 'check-intake')
        record = self.run_operation(req)
        self.assertEqual(record['state'], 'SUCCEEDED', record['error'])
        self.assertEqual(record['result']['core_status'], 'WAITING_INPUT')
        self.assertEqual(self.service.submit(req)['operation_id'], record['operation_id'])
        self.assertEqual(self.service.submit(req)['state'], 'SUCCEEDED')
        self.assertEqual(record['receipt']['core_outcome'], 'CONFIRMED_COMMITTED')

    def test_04_update_draft_invalidates_existing_approvals_atomically(self):
        root, pid = self.workspace(approved=True)
        before = load_data(root / 'PROJECT_INPUT.yaml')
        self.assertTrue(all(x['approved'] for x in before['approvals'].values()))
        view = self.service.get_status(pid)
        patch = {'project.primary_outcome': 'Новый результат с независимым review'}
        req = self.request(pid, 'update-draft', payload={'patch': patch,
                  'expected_input_digest': view['refs']['input_digest']})
        rec = self.run_operation(req)
        self.assertEqual(rec['state'], 'SUCCEEDED', rec['error'])
        after = load_data(root / 'PROJECT_INPUT.yaml')
        self.assertEqual(after['project']['primary_outcome'], patch['project.primary_outcome'])
        self.assertTrue(all(x == {'approved': False, 'actor': None, 'approved_at': None, 'notes': None}
                            for x in after['approvals'].values()))
        self.assertEqual(self.service.get_status(pid)['core_status'], 'WAITING_DECISION')
        self.assertNotEqual(self.service.get_status(pid)['fingerprint'], view['fingerprint'])
        self.assertEqual(rec['result']['refs']['approvals_invalidated'], True)
        self.assertNotIn('patch', json.dumps(rec, ensure_ascii=False))

    def test_05_unknown_field_sensitive_execution_and_unregistered_path_rejected_prewrite(self):
        root, pid = self.workspace()
        old = byte_snapshot(root)
        view = self.service.get_status(pid)
        for field in ('execution.mode', 'approvals.project_definition.approved', 'project.slug',
                      'project.mode', 'project.documentation.normative_sources'):
            with self.subTest(field=field):
                with self.assertRaises(ValidationFailure):
                    update_provisional_draft(root, {field: 'LOCAL_AUTOMATIC'},
                                            expected_input_digest=view['refs']['input_digest'])
        for raw in ('/etc/passwd', '../outside', 'C:\\Other', 'another-project'):
            with self.subTest(raw=raw):
                req = self.request(pid, 'check-intake', payload={'root': raw},
                                   key='path-attempt-test-001')
                with self.assertRaises(ValidationFailure):
                    self.service.submit(req)
        with self.assertRaises(ValidationFailure):
            self.service.submit(self.request(pid, 'execute-current'))
        with self.assertRaises(ValidationFailure):
            self.service.submit(self.request(pid, 'anything-unlisted'))
        with self.assertRaises(ValidationFailure):
            self.service.get_operation(pid, 'LWO-' + 'A'*32)
        self.assertEqual(byte_snapshot(root), old)

    def test_06_stale_fingerprint_after_cli_mutation_rejected_before_draft(self):
        root, pid = self.workspace()
        view = self.service.get_status(pid)
        req = self.request(pid, 'update-draft', payload={'patch': {'project.primary_outcome': 'outcome'},
                  'expected_input_digest': view['refs']['input_digest']}, fingerprint=view['fingerprint'])
        update_provisional_draft(root, {'project.primary_outcome': 'changed-by-external-api'},
                                 expected_input_digest=view['refs']['input_digest'])  # real public API change
        last = self.run_operation(req)
        self.assertEqual(last['state'], 'FAILED')
        self.assertEqual(last['error']['code'], 'STALE_FINGERPRINT')
        self.assertNotEqual(load_data(root/'PROJECT_INPUT.yaml')['project']['primary_outcome'], 'outcome')

    def test_07_duplicate_next_two_service_instances_same_key_no_second_run(self):
        root, pid = self.project()
        req = self.request(pid, 'next')
        with LocalWebService(self.base / 'app-data') as other:
            first = self.service.submit(req)
            same = other.submit(req)
            self.assertEqual(same['operation_id'], first['operation_id'])
            done = self.service.wait_for(first['operation_id'], timeout=60)
            self.assertEqual(done['state'], 'SUCCEEDED', done['error'])
            self.assertEqual(other.submit(req)['state'], 'SUCCEEDED')
            active = self.service.get_status(pid)['refs']['active_run']['run_ref']
            self.assertEqual(done['result']['refs']['run_ref'], active)
            self.assertEqual(len(list((root / '.harness/runtime/RUN_PLANS').glob('*.yaml'))), 1)
        with self.assertRaisesRegex(ValidationFailure, 'OPERATION_CONFLICT'):
            self.service.submit(OperationRequest(pid, 'validate-project', {}, req.idempotency_key, req.expected_fingerprint))

    def test_08_real_second_process_and_cli_cannot_bypass_lock(self):
        root, pid = self.project()
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(ROOT/'src'), str(ROOT))),
               'PYTHONDONTWRITEBYTECODE': '1'}
        cmd = [sys.executable, '-B', 'project-harness.py', 'next', '--project', str(root)]
        with project_operation_guard(root):
            cli = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(cli.returncode, 0, cli.stdout)
            body = json.loads(cli.stdout)
            self.assertIn('OPERATION_CONFLICT', body.get('message', '') + str(body.get('details', '')))
            from concurrent.futures import ThreadPoolExecutor
            with LocalWebService(self.base / 'app-data') as other, ThreadPoolExecutor(max_workers=1) as pool:
                with self.assertRaisesRegex(ValidationFailure, 'OPERATION_CONFLICT'):
                    pool.submit(other.get_status, pid).result(timeout=10)
        self.assertEqual(self.service.get_status(pid)['core_status'], 'ACTIVE')

    def test_09_new_operation_does_not_run_from_stale_snapshot_after_next(self):
        root, pid = self.project()
        view = self.service.get_status(pid)
        req = self.request(pid, 'verify', fingerprint=view['fingerprint'], key='verify-stale-test-001')
        # A real external API edit is visible to the subsequent service mutation.
        from project_harness.serialization import write_data
        path = root / '.harness/state/CURRENT_STATE.yaml'
        data = load_data(path)
        data['state']['updated_at'] = '2026-11-02T03:00:00Z'
        write_data(path, data)
        rec = self.run_operation(req)
        self.assertEqual(rec['state'], 'FAILED')
        self.assertEqual(rec['error']['code'], 'STALE_FINGERPRINT')

    def test_10_crash_after_atomic_draft_write_before_ui_result_reconciles(self):
        root, pid = self.workspace()
        view = self.service.get_status(pid)
        req = self.request(pid, 'update-draft', payload={'patch': {'project.primary_outcome': 'Значение'},
                  'expected_input_digest': view['refs']['input_digest']}, key='crash-draft-after-commit-01')
        original = self.service._save_op
        tripped = [False]
        def save(op):
            if op['state'] == 'SUCCEEDED' and not tripped[0]:
                tripped[0] = True
                raise OSError('fault injection after kernel commit')
            return original(op)
        with mock.patch.object(self.service, '_save_op', side_effect=save):
            saved = self.run_operation(req)
        self.assertTrue(tripped[0]); self.assertEqual(saved['state'], 'BLOCKED')
        resumed = self.service.reconcile_operation(pid, saved['operation_id'])
        self.assertEqual(resumed['state'], 'SUCCEEDED', resumed)
        self.assertEqual(resumed['phase'], 'RECONCILED_FROM_CORE')
        self.assertEqual(resumed['receipt']['core_outcome'], 'CONFIRMED_COMMITTED')
        self.assertEqual(load_data(root / 'PROJECT_INPUT.yaml')['project']['primary_outcome'], 'Значение')

    def test_11_prepare_is_real_core_zip_in_app_owned_folder_duplicate_no_overwrite(self):
        root, pid = self.workspace(approved=True)
        req = self.request(pid, 'prepare', key='prepared-once-manual-001')
        rec = self.run_operation(req)
        self.assertEqual(rec['state'], 'SUCCEEDED', rec['error'])
        self.assertEqual(rec['result']['core_status'], 'READY_FOR_CODEX')
        archive = self.service.app_data / 'artifacts' / rec['operation_id'] / 'handoff.zip'
        self.assertTrue(archive.is_file())
        from project_harness.validation import validate_handoff
        self.assertEqual(validate_handoff(archive)['status'], 'PASS')
        old_sha = sha256_file(archive)
        self.assertEqual(self.service.submit(req)['operation_id'], rec['operation_id'])
        self.assertEqual(sha256_file(archive), old_sha)

    def test_12_crash_after_handoff_publish_recovers_from_valid_exact_artifact(self):
        root, pid = self.workspace(approved=True)
        req = self.request(pid, 'prepare', key='crash-prepare-publish-00001')
        original = self.service._save_op
        broken = [False]
        def save(op):
            if op['state'] == 'SUCCEEDED' and not broken[0]:
                broken[0] = True
                raise OSError('fault after prepared handoff')
            return original(op)
        with mock.patch.object(self.service, '_save_op', side_effect=save):
            rec = self.run_operation(req)
        self.assertEqual(rec['state'], 'BLOCKED', rec)
        reconciled = self.service.reconcile_operation(pid, rec['operation_id'])
        self.assertEqual(reconciled['state'], 'SUCCEEDED', reconciled)
        self.assertEqual(reconciled['result']['artifact_ref'], rec['operation_id'])

    def test_13_queued_durable_request_on_reconnect_not_replayed(self):
        root, pid = self.workspace()
        req = self.request(pid, 'check-intake', key='queued-not-replayed-0001')
        opid = LocalWebService._operation_id(req)
        digest = self.service._hash({'action': req.action, 'payload': req.payload,
                                     'fingerprint': req.expected_fingerprint})
        rec = {'operation_id': opid, 'project_id': pid, 'action': req.action,
               'request_digest': digest, 'expected_fingerprint': req.expected_fingerprint,
               'created_at': '2026-11-02T00:00:00Z', 'updated_at': '2026-11-02T00:00:00Z',
               'started_at': None, 'finished_at': None, 'state': 'QUEUED', 'phase': 'QUEUED',
               'core_before': None, 'core_after': None, 'expected_draft_after': None,
               'result': None, 'error': None, 'receipt': self.service._receipt(req, opid, digest)}
        self.service._save_op(rec)
        before = byte_snapshot(root)
        with LocalWebService(self.base / 'app-data') as reconnected:
            self.assertEqual(reconnected.get_operation(pid, opid)['state'], 'QUEUED')
            status = reconnected.reconcile_operation(pid, opid)
        self.assertEqual(status['state'], 'INTERRUPTED')
        self.assertEqual(status['receipt']['core_outcome'], 'CONFIRMED_REJECTED')
        self.assertEqual(byte_snapshot(root), before)

    def test_14_crash_after_next_commit_cannot_claim_other_run_as_own(self):
        root, pid = self.project()
        req = self.request(pid, 'next', key='crash-next-ambiguous-0001')
        original = self.service._save_op
        tripped = [False]

        def fail_after_core_commit(op):
            if op['state'] == 'SUCCEEDED' and not tripped[0]:
                tripped[0] = True
                raise OSError('fault after core created Run; receipt not committed')
            return original(op)

        with mock.patch.object(self.service, '_save_op', side_effect=fail_after_core_commit):
            rec = self.run_operation(req)
        self.assertTrue(tripped[0])
        self.assertEqual(rec['state'], 'BLOCKED')
        run_ref_before = self.service.get_status(pid)['refs']['active_run']['run_ref']
        reconciled = self.service.reconcile_operation(pid, rec['operation_id'])
        self.assertEqual(reconciled['state'], 'BLOCKED')
        self.assertEqual(reconciled['error']['code'], 'AMBIGUOUS_COMMIT')
        self.assertEqual(reconciled['receipt']['core_outcome'], 'UNKNOWN_RECONCILE')
        self.assertEqual(run_ref_before, self.service.get_status(pid)['refs']['active_run']['run_ref'])

    @unittest.skipUnless(os.name == 'nt', 'Real Windows 11 x64/NTFS process + CLI test is mandatory on Windows stand')
    def test_15_real_windows_two_process_ntfs_security(self):
        root, pid = self.project()
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(ROOT/'src'), str(ROOT))),
               'PYTHONDONTWRITEBYTECODE': '1'}
        cmd = [sys.executable, '-B', 'project-harness.py', 'next', '--project', str(root)]
        before = byte_snapshot(root)
        with project_operation_guard(root):
            cli = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(cli.returncode, 0, cli.stdout)
            body = json.loads(cli.stdout)
            self.assertIn('OPERATION_CONFLICT', body.get('message', '') + str(body.get('details', '')))
        self.assertEqual(byte_snapshot(root), before)
        self.assertEqual(self.service.get_status(pid)['core_status'], 'ACTIVE')


if __name__ == '__main__':
    unittest.main()

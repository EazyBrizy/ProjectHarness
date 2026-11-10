"""PH-051-10: real migration, host-crash rollback/commit, orphan and cleanup boundaries.

Podman control is an explicitly mocked *host transport*, not an OS-isolation
attestation. A real rootless Podman security matrix belongs to PH-051-11/12.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import os
import tempfile
import unittest
from unittest import mock

from project_harness.hashing import sha256_file
from project_harness.migration import migrate_project, _migration_marker, _migration_recover
from project_harness.project_input import DEFAULT_EXECUTION_POLICY, EXECUTION_POLICY_MIGRATION_ID
from project_harness.runtime import (automatic_run_phase, execute_current, resume_blocked,
                                     project_status, block_current)
from project_harness.execution_roots import (finalize_execution_root, quarantine_orphan_execution_roots,
                                              _runtime_run_root)
from project_harness.sandbox.podman_rootless import (RootlessPodmanRunner, _PROJECT_LABEL,
                                                      _RUN_LABEL, _project_owner)
from project_harness.serialization import load_data, write_data
from project_harness.util import utc_now
from project_harness.validation import V050_REGISTRY_VERSIONS, validate_project_directory
from project_harness.workspace import check_control_plane, record_phase_boundary
from tests.test_engine import prepare_demo
from tests.test_ph_051_05_codex_adapter import install_profiles, local_profile
from tests.test_ph_051_09_automatic_runtime import HEALTH, SimulatedPodman


def downgrade_to_v050(root: Path) -> dict[str, bytes]:
    """Synthetic v0.5.0 fixture with matching registry lock and signed Run."""
    lock_path = root / '.harness/config/PROJECT_LOCK.yaml'
    lock_doc = load_data(lock_path)
    lock = lock_doc['project_lock']
    for name, revision in V050_REGISTRY_VERSIONS.items():
        path = root / '.harness/registries' / (name + '.yaml')
        registry = load_data(path)
        registry['registry']['version'] = revision
        write_data(path, registry)
        lock['registry_versions'][name] = revision
        lock['registry_digests'][name] = 'sha256:' + sha256_file(path)
    lock['harness_distribution'] = '0.5.0'
    lock['schema_version'] = 6
    lock.pop('execution', None)
    lock.pop('execution_profile_bindings', None)
    lock['migrations_applied'] = [item for item in lock['migrations_applied']
                                  if item != EXECUTION_POLICY_MIGRATION_ID]
    write_data(lock_path, lock_doc)
    project_path = root / '.harness/config/PROJECT.yaml'
    project = load_data(project_path)
    project['project']['harness_schema_version'] = 6
    write_data(project_path, project)
    accepted = root / '.harness/state/PROJECT_INPUT_ACCEPTED.yaml'
    raw = load_data(accepted)
    raw['schema_version'] = 3
    raw.pop('execution', None)
    write_data(accepted, raw)
    active = load_data(root / '.harness/state/CURRENT_STATE.yaml')['state'].get('active_run')
    if active:
        record_phase_boundary(root, active, phase='FIXTURE_V050',
                              kernel_written_paths=[], recorded_at=utc_now())
    assert validate_project_directory(root)['status'] == 'PASS'
    historic = [accepted]
    historic += sorted((root / '.harness/stages/ACCEPTANCE').glob('*.yaml'))
    historic += sorted((root / '.harness/runtime/RUNS').glob('*.yaml'))
    historic += sorted((root / '.harness/stages/PLANS').glob('*.yaml'))
    historic += sorted((root / '.harness/stages/GATES').glob('*.yaml'))
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in historic}


class V051MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ph05110-mig-')
        self.addCleanup(self.tmp.cleanup)
        self.root = prepare_demo(Path(self.tmp.name))[2]
        self.immutable = downgrade_to_v050(self.root)

    def assert_immutable(self):
        for path, value in self.immutable.items():
            self.assertEqual((self.root / path).read_bytes(), value, path)

    def test_01_real_v050_to_manual_v051_preserves_accepted_history_and_stage(self):
        before_stage = (self.root / '.harness/stages/STAGE_STATE.yaml').read_bytes()
        before_run = load_data(self.root / '.harness/state/CURRENT_STATE.yaml')['state']['active_run']['run_ref']
        result = migrate_project(self.root)
        self.assertEqual(result['status'], 'MIGRATED')
        lock = load_data(self.root / '.harness/config/PROJECT_LOCK.yaml')['project_lock']
        self.assertEqual(lock['execution'], DEFAULT_EXECUTION_POLICY)
        self.assertEqual(lock['schema_version'], 7)
        self.assertEqual(lock['harness_distribution'], '0.5.1')
        self.assertEqual(lock['execution_profile_bindings']['adapter'], {'ref': None, 'digest': None})
        self.assertIn(EXECUTION_POLICY_MIGRATION_ID, lock['migrations_applied'])
        self.assertEqual((self.root / '.harness/stages/STAGE_STATE.yaml').read_bytes(), before_stage)
        self.assertEqual(load_data(self.root / '.harness/state/CURRENT_STATE.yaml')['state']['active_run']['run_ref'], before_run)
        self.assert_immutable()
        self.assertEqual(validate_project_directory(self.root)['status'], 'PASS')
        self.assertEqual(check_control_plane(self.root,
            load_data(self.root / '.harness/state/CURRENT_STATE.yaml')['state']['active_run'])['status'], 'PASS')
        self.assertEqual((self.root / '.harness/engine/project_harness/resources/VERSION').read_text().strip(), '0.5.1-WIP')

    def test_02_idempotent_replay_preserves_every_byte(self):
        migrate_project(self.root)
        lock_file = self.root / '.harness/config/PROJECT_LOCK.yaml'
        report = self.root / '.harness/reports' / (EXECUTION_POLICY_MIGRATION_ID + '.yaml')
        prior = (lock_file.read_bytes(), report.read_bytes())
        replay = migrate_project(self.root)
        self.assertEqual(replay['status'], 'NO_ACTION')
        self.assertEqual(replay['migration_id'], EXECUTION_POLICY_MIGRATION_ID)
        self.assertEqual(prior, (lock_file.read_bytes(), report.read_bytes()))
        self.assert_immutable()

    def test_03_interrupt_after_old_rename_restores_exact_old_root(self):
        import project_harness.migration as migration
        def crash(point):
            if point == 'AFTER_OLD_RENAME':
                raise KeyboardInterrupt('simulate crash')
        with mock.patch.object(migration, '_v051_migration_fault', side_effect=crash):
            with self.assertRaises(KeyboardInterrupt):
                migrate_project(self.root)
        self.assertFalse(self.root.exists())
        self.assertTrue(_migration_marker(self.root).exists())
        self.assertEqual(_migration_recover(self.root), 'ROLLED_BACK')
        self.assert_immutable()
        self.assertEqual(load_data(self.root / '.harness/config/PROJECT_LOCK.yaml')['project_lock']['schema_version'], 6)
        self.assertEqual(migrate_project(self.root)['status'], 'MIGRATED')
        self.assertEqual(validate_project_directory(self.root)['status'], 'PASS')

    def test_04_interrupt_after_new_rename_retains_committed_new(self):
        import project_harness.migration as migration
        with mock.patch.object(migration, '_v051_migration_fault', side_effect=lambda name: (
             (_ for _ in ()).throw(KeyboardInterrupt('crash')) if name == 'AFTER_NEW_RENAME' else None)):
            with self.assertRaises(KeyboardInterrupt):
                migrate_project(self.root)
        self.assertTrue(self.root.is_dir())
        self.assertEqual(_migration_recover(self.root), 'COMMITTED')
        self.assertEqual(migrate_project(self.root)['status'], 'NO_ACTION')
        self.assert_immutable()

    def test_05_invalid_historical_control_rejected_without_migration(self):
        p = self.root / '.harness/config/PROJECT_LOCK.yaml'
        altered = load_data(p)
        altered['project_lock']['registry_digests']['contracts'] = 'sha256:' + '0'*64
        write_data(p, altered)
        changed = p.read_bytes()
        with self.assertRaises(Exception):
            migrate_project(self.root)
        self.assertEqual(p.read_bytes(), changed)
        self.assertFalse(_migration_marker(self.root).exists())
        self.assert_immutable()


class V051RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='ph05110-run-')
        self.addCleanup(self.tmp.cleanup)
        home = Path(self.tmp.name)
        self.project = prepare_demo(home / 'source')[2]
        self.runtime = home / 'trusted-runtime'
        self.runtime.mkdir(mode=0o700)
        self.active = load_data(self.project / '.harness/state/CURRENT_STATE.yaml')['state']['active_run']
        self.run_ref = self.active['run_ref']
        install_profiles(self.project, adp=local_profile())
        record_phase_boundary(self.project, self.active, phase='V051_PROFILE_ACTIVATION',
                              kernel_written_paths=[], recorded_at=utc_now())

    def test_06_missing_podman_interrupted_run_is_fail_closed_not_reexecuted(self):
        record_phase_boundary(self.project, self.active, phase='AUTO_RUNNING',
                              kernel_written_paths=[], recorded_at=utc_now())
        with mock.patch.object(RootlessPodmanRunner, 'project_orphan_containers',
                               return_value={'status':'BLOCKED', 'reason_code':'SANDBOX_UNAVAILABLE'}), \
             mock.patch.object(RootlessPodmanRunner, 'run', side_effect=AssertionError('host fallback')) as runner:
            result = execute_current(self.project, runtime_root=self.runtime)
        self.assertEqual(result['reason_code'], 'SANDBOX_UNAVAILABLE')
        self.assertEqual(result['run_status'], 'RUNNING')
        runner.assert_not_called()
        self.assertEqual(automatic_run_phase(self.project, self.active)['status'], 'RUNNING')

    def test_07_orphan_run_quarantined_blocked_then_new_retry_exact_run(self):
        project_id = load_data(self.project / '.harness/config/PROJECT.yaml')['project']['id']
        root = self.runtime / project_id / 'executions' / self.run_ref
        root.mkdir(parents=True, mode=0o700)
        (root / 'agent-result.json').write_text('{"status":"COMPLETED"}')
        record_phase_boundary(self.project, self.active, phase='AUTO_RUNNING',
                              kernel_written_paths=[], recorded_at=utc_now())
        with mock.patch.object(RootlessPodmanRunner, 'project_orphan_containers',
                               return_value={'status':'PASS', 'orphan_count':1, 'stopped_run_refs':[self.run_ref]}), \
             mock.patch.object(RootlessPodmanRunner, 'run', side_effect=AssertionError('must not re-run')) as runner:
            outcome = execute_current(self.project, runtime_root=self.runtime)
        self.assertEqual(outcome['status'], 'BLOCKED', outcome)
        self.assertEqual(outcome['cleanup'], 'QUARANTINED')
        self.assertEqual(outcome['reason_code'], 'EXECUTOR_UNAVAILABLE')
        runner.assert_not_called()
        self.assertFalse(root.exists())
        self.assertTrue(list((self.runtime / project_id / 'quarantine').iterdir()))
        old = (self.project / '.harness/runtime/RUNS' / (self.run_ref + '.yaml')).read_bytes()
        self.assertEqual(load_data(self.project / '.harness/runtime/RUNS' / (self.run_ref + '.yaml'))['run']['execution_origin'], 'LOCAL_AUTOMATIC')
        self.assertEqual(validate_project_directory(self.project)['status'], 'PASS')
        self.assertEqual(execute_current(self.project, runtime_root=self.runtime)['status'], 'BLOCKED')
        self.assertEqual((self.project / '.harness/runtime/RUNS' / (self.run_ref + '.yaml')).read_bytes(), old)
        new = resume_blocked(self.project, resolution='Orphan terminated and result untrusted; new attempt')
        self.assertNotEqual(new['next']['run_ref'], self.run_ref)
        self.assertEqual((self.project / '.harness/runtime/RUNS' / (self.run_ref + '.yaml')).read_bytes(), old)

    def test_08_success_cleanup_no_residual_disposable_and_apply_idempotent(self):
        sim = SimulatedPodman()
        with mock.patch.object(RootlessPodmanRunner, 'doctor', return_value=deepcopy(HEALTH)), \
             mock.patch.object(RootlessPodmanRunner, 'run', autospec=True, side_effect=sim.run):
            output = execute_current(self.project, runtime_root=self.runtime)
        self.assertEqual(output['status'], 'SUCCEEDED', output)
        self.assertEqual(output['cleanup'], 'CLEANED', output)
        result = load_data(self.project / '.harness/runtime/CLEANUP_REPORTS' / (self.run_ref + '.yaml'))['execution_cleanup']
        self.assertEqual(result['status'], 'CLEANED')
        project_id = load_data(self.project / '.harness/config/PROJECT.yaml')['project']['id']
        self.assertFalse((self.runtime / project_id / 'executions' / self.run_ref).exists())
        before = (self.project / '.harness/evidence' / (output['apply_evidence_ref'] + '.yaml')).read_bytes()
        replay = execute_current(self.project, runtime_root=self.runtime)
        self.assertTrue(replay['idempotent'])
        self.assertEqual((self.project / '.harness/evidence' / (output['apply_evidence_ref'] + '.yaml')).read_bytes(), before)

    def test_09_cleanup_failure_does_not_turn_verified_run_into_failure(self):
        sim = SimulatedPodman()
        with mock.patch.object(RootlessPodmanRunner, 'doctor', return_value=deepcopy(HEALTH)), \
             mock.patch.object(RootlessPodmanRunner, 'run', autospec=True, side_effect=sim.run), \
             mock.patch('project_harness.runtime.finalize_execution_root',
                        return_value={'status':'CLEANUP_FAILED', 'quarantined':True}):
            output = execute_current(self.project, runtime_root=self.runtime)
        self.assertEqual(output['status'], 'SUCCEEDED', output)
        self.assertEqual(output['cleanup'], 'CLEANUP_FAILED')
        self.assertEqual(validate_project_directory(self.project)['status'], 'PASS')

    def test_15_crash_after_verified_apply_recovers_cleanup_without_redispatch(self):
        # The product was committed, but the host died before cleanup receipt.
        # Re-entry must inspect containers, retire root, never launch the agent
        # again, and never replace Apply Evidence or Accepted Stage history.
        sim = SimulatedPodman()
        with mock.patch.object(RootlessPodmanRunner, 'doctor', return_value=deepcopy(HEALTH)), \
             mock.patch.object(RootlessPodmanRunner, 'run', autospec=True, side_effect=sim.run), \
             mock.patch('project_harness.runtime._cleanup_automatic_attempt',
                        side_effect=KeyboardInterrupt('post-commit process death')):
            with self.assertRaises(KeyboardInterrupt):
                execute_current(self.project, runtime_root=self.runtime)
        self.assertEqual(automatic_run_phase(self.project, self.active)['phase'], 'AUTO_VERIFIED')
        from project_harness.apply import _evidence_id
        evidence = self.project / '.harness/evidence' / (_evidence_id(self.run_ref) + '.yaml')
        committed = evidence.read_bytes()
        project_id = load_data(self.project / '.harness/config/PROJECT.yaml')['project']['id']
        run_root = self.runtime / project_id / 'executions' / self.run_ref
        self.assertTrue(run_root.is_dir())
        with mock.patch.object(RootlessPodmanRunner, 'project_orphan_containers',
                               return_value={'status': 'PASS', 'orphan_count': 0}), \
             mock.patch.object(RootlessPodmanRunner, 'run', side_effect=AssertionError('must not dispatch')) as runner:
            replay = execute_current(self.project, runtime_root=self.runtime)
        self.assertEqual(replay['status'], 'SUCCEEDED', replay)
        self.assertEqual(replay['cleanup'], 'CLEANED', replay)
        self.assertTrue(replay['idempotent'])
        runner.assert_not_called()
        self.assertFalse(run_root.exists())
        self.assertEqual(evidence.read_bytes(), committed)
        self.assertEqual(validate_project_directory(self.project)['status'], 'PASS')

    def test_16_post_commit_cleanup_without_podman_blocks_only_cleanup(self):
        sim = SimulatedPodman()
        with mock.patch.object(RootlessPodmanRunner, 'doctor', return_value=deepcopy(HEALTH)), \
             mock.patch.object(RootlessPodmanRunner, 'run', autospec=True, side_effect=sim.run), \
             mock.patch('project_harness.runtime._cleanup_automatic_attempt',
                        side_effect=KeyboardInterrupt('post-commit crash')):
            with self.assertRaises(KeyboardInterrupt):
                execute_current(self.project, runtime_root=self.runtime)
        with mock.patch.object(RootlessPodmanRunner, 'project_orphan_containers',
                               return_value={'status': 'BLOCKED', 'reason_code': 'SANDBOX_UNAVAILABLE'}):
            outcome = execute_current(self.project, runtime_root=self.runtime)
        self.assertEqual(outcome['status'], 'BLOCKED')
        self.assertEqual(outcome['run_status'], 'SUCCEEDED')
        self.assertEqual(outcome['reason_code'], 'SANDBOX_UNAVAILABLE')
        self.assertEqual(automatic_run_phase(self.project, self.active)['phase'], 'AUTO_VERIFIED')
        self.assertEqual(validate_project_directory(self.project)['status'], 'PASS')

    def test_10_retirement_refuses_unsafe_symlink_without_touching_destination(self):
        project_id = load_data(self.project / '.harness/config/PROJECT.yaml')['project']['id']
        root = self.runtime / project_id / 'executions' / self.run_ref
        root.parent.mkdir(parents=True, mode=0o700)
        external = Path(self.tmp.name) / 'outside.txt'
        external.write_text('DO NOT DELETE')
        root.symlink_to(external)
        result = finalize_execution_root(self.project, self.runtime, run_ref=self.run_ref)
        self.assertEqual(result['status'], 'CLEANUP_FAILED')
        self.assertEqual(external.read_text(), 'DO NOT DELETE')
        self.assertTrue(root.is_symlink())

    def test_11_stale_roots_quarantined_without_using_partial_result(self):
        project_id = load_data(self.project / '.harness/config/PROJECT.yaml')['project']['id']
        stale = self.runtime / project_id / 'executions' / 'RUN-STALE-001'
        stale.mkdir(parents=True)
        (stale / 'agent-result.json').write_text('untrusted')
        data = quarantine_orphan_execution_roots(self.project, self.runtime)
        self.assertEqual(data['status'], 'PASS', data)
        self.assertEqual(data['quarantined'], ['RUN-STALE-001'])
        self.assertFalse(stale.exists())
        self.assertTrue(list((self.runtime / project_id / 'quarantine').iterdir()))


class V051PodmanLabelsTests(unittest.TestCase):
    def test_12_run_labels_are_bound_without_host_paths_or_secrets(self):
        from tests.test_ph_051_03_rootless_podman import profile, dirs
        from project_harness.sandbox.profiles import validate_sandbox_profile
        with tempfile.TemporaryDirectory() as d:
            mounts = dirs(Path(d))
            p = validate_sandbox_profile(profile())
            argv = RootlessPodmanRunner._command(p, mounts, podman='/usr/bin/podman',
                name='ph-05103-12345678901234567890', executable='codex', argv=['exec'],
                uid=1001, gid=1001, project_owner='a'*64, run_ref='RUN-TEST-001')
        labels = [argv[i+1] for i, flag in enumerate(argv[:-1]) if flag == '--label']
        self.assertIn(f'{_PROJECT_LABEL}=' + 'a'*64, labels)
        self.assertIn(f'{_RUN_LABEL}=RUN-TEST-001', labels)
        self.assertFalse(any('/tmp/' in value for value in labels))

    def test_13_podman_refuses_foreign_or_unbound_container_identity(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            fake = RootlessPodmanRunner()
            result = {'termination_reason':'EXITED', 'exit_code':0,
                      'stdout': json.dumps([{'Id':'f'*64, 'Names':'ph-05103-'+'a'*20,
                          'Labels': {'io.project-harness.sandbox':'PH-051-03',
                                     _PROJECT_LABEL:'0'*64, _RUN_LABEL:'RUN-TEST-001'}}])}
            with mock.patch.object(fake, '_podman', return_value='/usr/bin/podman'), \
                 mock.patch('os.geteuid', return_value=1001), \
                 mock.patch.object(fake, '_control', return_value=result) as ctl:
                status = fake.project_orphan_containers(root)
            self.assertEqual(status['status'], 'BLOCKED')
            self.assertEqual(status['reason_code'], 'SANDBOX_POLICY_FAILURE')
            self.assertEqual(ctl.call_count, 1)

    def test_17_unproven_podman_cleanup_is_never_isolation_verified(self):
        from tests.test_ph_051_03_rootless_podman import profile, dirs, request
        with tempfile.TemporaryDirectory() as temp:
            bindings = dirs(Path(temp))
            runner = RootlessPodmanRunner(configured_executable='codex')
            with mock.patch.object(runner, 'doctor', return_value=deepcopy(HEALTH)), \
                 mock.patch.object(runner, '_podman', return_value='/usr/bin/podman'), \
                 mock.patch.object(runner, '_spawn', return_value={
                     'termination_reason': 'TIMED_OUT', 'exit_code': None,
                     'cleanup_status': 'FAILED', 'stdout': '', 'stderr': ''}):
                result = runner.run(request(bindings))
        self.assertFalse(result['isolation_verified'])
        self.assertEqual(result['reason_code'], 'SANDBOX_UNAVAILABLE')

    def test_14_reaps_verified_exact_run_only_via_bounded_podman(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            owner = _project_owner(root)
            entry = {'Id':'f'*64, 'Names':'ph-05103-'+'a'*20,
                     'Labels': {'io.project-harness.sandbox':'PH-051-03',
                                _PROJECT_LABEL:owner, _RUN_LABEL:'RUN-TEST-001'}}
            def ctl(podman, args, **kwargs):
                if args[0] == 'ps':
                    return {'termination_reason':'EXITED','exit_code':0,'stdout':json.dumps([entry])}
                if args[:2] == ['container','exists']:
                    return {'termination_reason':'EXITED', 'exit_code':1}
                return {'termination_reason':'EXITED', 'exit_code':0}
            runner=RootlessPodmanRunner()
            with mock.patch.object(runner,'_podman', return_value='/usr/bin/podman'), \
                 mock.patch('os.geteuid', return_value=1001), \
                 mock.patch.object(runner, '_control', side_effect=ctl) as call:
                result=runner.project_orphan_containers(root)
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['stopped_run_refs'], ['RUN-TEST-001'])
            self.assertEqual(call.call_count, 4)


if __name__ == '__main__':
    unittest.main()

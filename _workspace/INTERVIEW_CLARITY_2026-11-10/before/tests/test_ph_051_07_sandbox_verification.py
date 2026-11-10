"""PH-051-07: bounded independent sandbox verification regressions."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from project_harness.sandbox.verification import verify_disposable
from project_harness.workspace import snapshot_product
from tests.test_ph_051_03_rootless_podman import profile


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.project = self.base / 'canonical'
        self.project.mkdir()
        self.execution = self.base / 'execution'
        for name in ('product','control','output'):
            (self.execution / name).mkdir(parents=True)
        self.product = self.execution / 'product'
        (self.product / 'a.txt').write_text('old')
        self.baseline = snapshot_product(self.product)
        (self.project / 'a.txt').write_text('old')
        (self.product / 'a.txt').write_text('new')
        self.task = {'scope': {'write': ['a.txt'], 'forbidden': ['.harness/**']},
                     'verification': {'commands': [{'argv': ['python3','-c','print(1)']}],
                                      'expected_paths': ['a.txt']}}

    def check(self, runner=None):
        return verify_disposable(canonical_project_root=self.project, execution_root=self.execution,
                                 sandbox_profile=profile(), task_contract=self.task,
                                 baseline_files=self.baseline, runner=runner)

    def test_agent_completed_cannot_override_failing_independent_check(self):
        class Fake:
            def run(self, request):
                self.request = request
                return {'isolation_verified':True,'termination_reason':'EXITED','exit_code':1}
        fake = Fake()
        result = self.check(fake)
        self.assertEqual(result['reason_code'], 'VERIFICATION_FAILED')
        self.assertFalse(result['apply_allowed'])
        self.assertNotIn('run_context', fake.request)
        self.assertEqual(fake.request['network_mode'], 'NONE')
        self.assertEqual((self.product / 'a.txt').read_text(), 'new')

    def test_success_is_only_task_proof_not_apply_or_gate_acceptance(self):
        class Fake:
            def run(self, request):
                return {'isolation_verified': True, 'termination_reason':'EXITED', 'exit_code':0}
        result = self.check(Fake())
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['apply_allowed'])
        self.assertEqual(result['verified_subjects'], ['RUNTIME_TASK_VERIFICATION'])

    def test_wrong_path_blocks_before_command(self):
        self.task['scope']['write'] = ['other.txt']
        class Never:
            def run(self, request):
                raise AssertionError('must not invoke')
        self.assertEqual(self.check(Never())['reason_code'], 'SCOPE_VIOLATION')

    def test_no_verification_command_blocks(self):
        self.task['verification']['commands'] = []
        self.assertEqual(self.check()['status'], 'FAIL')

    def test_no_host_command_execution_when_sandbox_unavailable(self):
        class Unavailable:
            def run(self, request):
                return {'status':'BLOCKED','reason_code':'SANDBOX_UNAVAILABLE'}
        with patch('subprocess.run', side_effect=AssertionError('host execution forbidden')):
            self.assertEqual(self.check(Unavailable())['reason_code'], 'VERIFICATION_FAILED')

    def test_verifier_modifying_files_fails(self):
        class Mutate:
            def run(inner, request):
                (self.product / 'a.txt').write_text('unexpected')
                return {'isolation_verified':True,'termination_reason':'EXITED','exit_code':0}
        self.assertEqual(self.check(Mutate())['status'], 'FAIL')

    def test_changed_canonical_baseline_rejects_before_launch(self):
        (self.project / 'a.txt').write_text('drift')
        class Never:
            def run(self, request):
                raise AssertionError('stale candidate cannot start verification')
        self.assertEqual(self.check(Never())['reason_code'], 'BASELINE_CHANGED')

    def test_canonical_change_during_verifier_rejects(self):
        class Drift:
            def run(inner, request):
                (self.project / 'a.txt').write_text('drift')
                return {'isolation_verified': True, 'termination_reason': 'EXITED', 'exit_code': 0}
        self.assertEqual(self.check(Drift())['reason_code'], 'BASELINE_CHANGED')

    def test_no_unapproved_network_or_implicit_secrets(self):
        p = profile()
        p['sandbox_profile']['network_mode'] = 'EXPLICIT_APPROVED_EGRESS'
        result = verify_disposable(canonical_project_root=self.project,execution_root=self.execution,
                                    sandbox_profile=p,task_contract=self.task,baseline_files=self.baseline)
        self.assertEqual(result['reason_code'], 'NETWORK_NOT_APPROVED')


if __name__ == '__main__':
    unittest.main()

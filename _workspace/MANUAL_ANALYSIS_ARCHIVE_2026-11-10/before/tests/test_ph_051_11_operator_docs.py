"""PH-051-11 operator docs/profile sample and source manifest regression.

These tests intentionally do not attest rootless Linux sandbox isolation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from project_harness.cli import build_parser
from project_harness.executors.codex_cli_local import _profile as validate_adp
from project_harness.project_input import _validate_schema_node, DEFAULT_EXECUTION_POLICY
from project_harness.sandbox.profiles import validate_sandbox_profile
from project_harness.serialization import load_data
from project_harness.validation import _manifest_check

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs/Project_Harness_Documentation_v0.5.1'


class OperatorDocsContractTests(unittest.TestCase):
    def test_01_examples_exact_schema_and_runtime_profile_validation(self):
        for name, schema_name, verifier in (
            ('adapter_codex_cli_local.v0.5.1.example.yaml', 'executor_profile.schema.json', validate_adp),
            ('sandbox_rootless_podman.v0.5.1.example.yaml', 'sandbox_profile.schema.json', validate_sandbox_profile),
        ):
            with self.subTest(name=name):
                record = load_data(ROOT / 'examples' / name)
                schema = json.loads((ROOT / 'schemas' / schema_name).read_text())
                self.assertEqual(_validate_schema_node(record, schema, schema), [])
                self.assertTrue(verifier(record))
                self.assertEqual((ROOT / 'examples' / name).read_bytes(),
                                 (DOCS / '10_Contracts/examples' / name).read_bytes())

    def test_02_safe_default_and_all_samples_synced(self):
        example = load_data(ROOT / 'examples/execution_policy_manual.v0.5.1.example.yaml')
        self.assertEqual(example, {'execution': DEFAULT_EXECUTION_POLICY})
        for f in (DOCS / '10_Contracts/examples').glob('*'):
            self.assertEqual(f.read_bytes(), (ROOT / 'examples' / f.name).read_bytes())
        negative = (ROOT / 'examples/egress_request_REJECTED.v0.5.1.example.yaml').read_text()
        self.assertIn('NOT A VALID GOVERNANCE APPROVAL', negative)

    def test_03_current_cli_flags_and_docs_names(self):
        parser = build_parser()
        for cmd in ('executor-doctor', 'execute-current'):
            args = parser.parse_args([cmd, '--project', '/tmp/project', '--network', 'NONE',
                                     '--adapter-profile', 'ADP-CODEX-CLI-LOCAL-001@1'])
            self.assertEqual(args.command, cmd)
            self.assertEqual(args.network, 'NONE')
            self.assertIsNone(args.approval)
        self.assertIn('migrate-project', parser.format_help())
        self.assertIn('--allow-command-execution',
                      next(action for action in parser._subparsers._group_actions).choices['verify'].format_help())
        for p in (
            DOCS / '05_Updates/14_Operator_Runbook_v0.5.1_WIP.md',
            DOCS / '05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md',
            ROOT / 'templates/GPT_PREPARATION_INSTRUCTIONS.md',
            ROOT / 'MANUAL_INSTALL.md',
        ):
            self.assertTrue(p.is_file(), p)
            text = p.read_text()
            self.assertIn('MANUAL_HANDOFF' if 'GPT_PREPARATION' in p.name else 'Podman' if '15_Podman' in p.name else '0.5.1', text)
        self.assertEqual((ROOT / 'templates/GPT_PREPARATION_INSTRUCTIONS.md').read_bytes(),
                         (ROOT / 'src/project_harness/resources/templates/GPT_PREPARATION_INSTRUCTIONS.md').read_bytes())

    def test_04_nested_manifest_is_included_and_bound_by_distribution_manifest(self):
        with tempfile.TemporaryDirectory(prefix='ph05111-manifest-') as t:
            root = Path(t)
            nested = root / 'docs/MANIFEST.sha256'
            nested.parent.mkdir()
            nested.write_text('nested-manifest-record\n')
            root_manifest = root / 'MANIFEST.sha256'
            digest = hashlib.sha256(nested.read_bytes()).hexdigest()
            root_manifest.write_text(f'{digest}  docs/MANIFEST.sha256\n')
            good, details = _manifest_check(root)
            self.assertTrue(good, details)
            nested.write_text('tampered\n')
            good, details = _manifest_check(root)
            self.assertFalse(good)
            self.assertEqual(details['mismatched'], ['docs/MANIFEST.sha256'])

    def test_05_security_matrix_makes_no_mock_attestation_claim(self):
        text = (DOCS / '05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md').read_text()
        self.assertIn('NOT TESTED', text)
        self.assertIn('test_19_real_rootless_doctor_and_container_run', text)
        self.assertIn('Podman', text)
        self.assertIn('NO GO', text)

if __name__ == '__main__':
    unittest.main()

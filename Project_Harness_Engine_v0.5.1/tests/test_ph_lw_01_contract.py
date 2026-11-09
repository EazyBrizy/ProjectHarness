"""PH-LW-01 strictly additive contract verification, never Web/Windows E2E evidence."""
from __future__ import annotations
import argparse
from copy import deepcopy
from importlib import import_module, resources
import hashlib
import json
from pathlib import Path
import platform
import re
import unittest
import zipfile

from project_harness.cli import build_parser
from project_harness.project_input import GREENFIELD_APPROVALS, BROWNFIELD_APPROVALS, validate_project_input
from project_harness.resources import distribution_root

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'local_web'
PKG = resources.files('project_harness').joinpath('resources/local_web')


def package_json(name: str) -> dict:
    with PKG.joinpath(name).open('r', encoding='utf-8') as f:
        return json.load(f)


class PHLW01ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = package_json('control_map_v1.json')['commands']
        cls.meta = package_json('metadata_v1.json')
        cls.fixture = WEB / 'fixtures'

    def test_01_exact_26_cli_commands_with_no_invented_api(self):
        parser = build_parser()
        choices = {}
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                choices = action.choices
                break
        # PH-LW-04 adds a *launcher* CLI, not a core operation in the
        # frozen 26-action PH-LW-01 application-service control map.
        # The explicit PH-LW-09 intake adds two typed CLI surfaces. Keep the
        # original 26 controls exact; reject every unlisted extra command.
        extensions = {'task-manual-context':'manual_evidence_context',
                      'record-task-manual-evidence':'record_manual_evidence'}
        self.assertEqual(len(choices), 29)
        for command, api in extensions.items():
            self.assertIn(command, choices)
            self.assertTrue(callable(getattr(import_module('project_harness.task_manual_evidence'),api)))
            arguments = {a.dest:a for a in choices[command]._actions}
            self.assertTrue(arguments['project'].required)
        self.assertTrue(any(a.dest=='input' and a.required for a in choices['record-task-manual-evidence']._actions))
        self.assertTrue(any(a.dest=='confirm' and a.default is False for a in choices['record-task-manual-evidence']._actions))
        self.assertIn('ui', choices)
        self.assertEqual({x['cli'] for x in self.map}, set(choices) - {'ui'} - set(extensions))
        self.assertEqual({x['id'] for x in self.map}, {f'LW-C{i:02d}' for i in range(1, 27)})
        self.assertEqual(len({x['test_id'] for x in self.map}) >= 10, True)
        for item in self.map:
            self.assertRegex(item['test_id'], r'^LW-E(0[1-9]|[12][0-9]|3[0-6])$')
            for required in ('screen','action','module','python_api','semantics','consent','exact_context','preconditions','expected_state','next_action','test_id'):
                self.assertTrue(item[required], f"{item['cli']} missing {required}")

    def test_02_python_apis_actual_public_and_unavailable_demo(self):
        for item in self.map:
            if item['cli'] == 'demo':
                self.assertFalse(item['public_python_api'])
                self.assertEqual(item['semantics'], 'UNAVAILABLE_WRAPPER')
                self.assertEqual(item['http_method'], 'DISABLED')
            else:
                self.assertTrue(item['public_python_api'], item['cli'])
                fn = getattr(import_module('project_harness.' + item['module']), item['python_api'])
                self.assertTrue(callable(fn), item['cli'])

    def test_03_no_mutations_on_GET_and_unsafe_routes_classified(self):
        snapshot = {x['cli'] for x in self.map if x['http_method'] == 'GET'}
        self.assertEqual(snapshot, {'status','stage-status'})
        for item in self.map:
            if item['semantics'] in ('MUTATION','WRITE_APP_ARTIFACT','WRITE_CORE_ASSESSMENT','EXPLICIT_DIAGNOSTIC','READ_DIAGNOSTIC'):
                self.assertEqual(item['http_method'], 'POST', item['cli'])
            self.assertFalse(item['semantics']=='MUTATION' and item['consent']=='NONE')
        for name in ('next','check-intake','prepare','verify','complete','accept-stage','level-up'):
            self.assertEqual(next(x for x in self.map if x['cli']==name)['http_method'], 'POST')
        self.assertEqual(next(x for x in self.map if x['cli']=='execute-current')['semantics'], 'DISABLED')

    def test_04_intake_approvals_distinct_and_manual_draft(self):
        self.assertEqual(GREENFIELD_APPROVALS, ['project_definition','architecture_baseline','technology_baseline','codex_handoff'])
        self.assertEqual(BROWNFIELD_APPROVALS, ['project_definition','brownfield_baseline','architecture_baseline','technology_baseline','codex_handoff'])
        candidate=json.loads((self.fixture/'no_doc_unapproved_project_input_v4.json').read_text())
        self.assertEqual(candidate['execution'], dict(mode='MANUAL_HANDOFF',adapter_profile_ref=None,sandbox_profile_ref=None,network_mode='NONE',completion_policy='EXPLICIT_AFTER_VERIFICATION'))
        self.assertEqual(set(candidate['approvals']),set(GREENFIELD_APPROVALS))
        self.assertTrue(all(a == {'approved':False,'actor':None,'approved_at':None,'notes':None} for a in candidate['approvals'].values()))
        self.assertNotEqual(validate_project_input(candidate,require_approvals=True)['status'], 'READY_FOR_HANDOFF')

    def test_05_strict_shell_schemas_and_untrusted_rejection(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema optional; core minimal wheel dependencies=[]')
        exchange=package_json('gpt_exchange_reply_v1.schema.json')
        receipt=package_json('operation_receipt_v1.schema.json')
        for schema in (exchange,receipt):
            jsonschema.Draft202012Validator.check_schema(schema)
            self.assertFalse(schema['additionalProperties'])
        good=json.loads((self.fixture/'gpt_reply_draft_only_positive.json').read_text())
        self.assertEqual(list(jsonschema.Draft202012Validator(exchange).iter_errors(good)),[])
        bad=json.loads((self.fixture/'gpt_reply_untrusted_reject.json').read_text())
        self.assertTrue(list(jsonschema.Draft202012Validator(exchange).iter_errors(bad)))
        for k,sub in (('export_sha256','sha256:broken'),('kind','STAGE_APPROVAL'),('envelope_version',2)):
            trial=deepcopy(good);trial[k]=sub
            self.assertTrue(list(jsonschema.Draft202012Validator(exchange).iter_errors(trial)),k)
        # Model approval is not valid signed intake; even if envelope is syntactically fixed
        # the imported core draft MUST be constrained to all approvals=False/manual mode.
        bad_draft=deepcopy(good)
        bad_draft['project_input_draft']['approvals']['project_definition']['approved']=True
        self.assertFalse(all(not x['approved'] for x in bad_draft['project_input_draft']['approvals'].values()))
        self.assertEqual(receipt['properties']['core_outcome']['enum'],['NOT_STARTED','PENDING','CONFIRMED_COMMITTED','CONFIRMED_REJECTED','UNKNOWN_RECONCILE'])

    def test_06_fixture_inventory_and_no_fake_prod_evidence(self):
        self.assertIn('prove Stage Gate', (self.fixture/'brownfield_existing_repository/README.md').read_text())
        with zipfile.ZipFile(self.fixture/'greenfield_nested_md.zip') as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(sum(n.casefold().endswith('.md') for n in z.namelist()),2)
            self.assertIn('ОТКЛОНЕНО.txt', '\n'.join(z.namelist()))
            self.assertTrue(all(not n.startswith('/') and '..' not in n.split('/') for n in z.namelist()))
        recipe=json.loads((self.fixture/'advanced_state_recipe.json').read_text())
        self.assertEqual(recipe['status'], 'TEST_ONLY_RECIPE_NOT_PREGENERATED_APPROVAL')
        self.assertTrue((ROOT/'tests/ph_f06_fixtures.py').exists())
        self.assertTrue((ROOT/'tests/maintenance_fixtures.py').exists())
        self.assertIn('--test-only-synthetic-approval', (self.fixture/'generate_advanced_state.py').read_text())

    def test_07_pinned_web_dependencies_only_not_imported_into_core(self):
        lock=(WEB/'requirements-web-win_amd64-cp314.lock').read_text()
        inventory=json.loads((WEB/'wheel_inventory_v1.json').read_text())
        self.assertEqual(len(inventory['packages']),10)
        self.assertIn('--require-hashes',lock)
        self.assertIn('MARKUPSAFE'.lower(),lock)
        self.assertTrue(inventory['status'].startswith('PINNED_'))
        for p in inventory['packages']:
            self.assertRegex(p['sha256'],r'^[a-f0-9]{64}$')
            self.assertIn(f"{p['name']}=={p['version']} --hash=sha256:{p['sha256']}",lock)
        pyproject=(ROOT/'pyproject.toml').read_text()
        self.assertIn('dependencies = []',pyproject)
        self.assertIn('resources/local_web/*.json',pyproject)
        init=(ROOT/'src/project_harness/__init__.py').read_text()
        self.assertNotIn('flask',init.lower())
        self.assertNotIn('waitress',init.lower())

    def test_08_provenance_locked_and_release_verdict_separate(self):
        self.assertEqual(self.meta['base_lineage'],'PH-051-11-WIP-NOT-RELEASED')
        self.assertNotEqual(self.meta['source_engine_zip_sha256'],self.meta['expected_ph05112_engine_zip_sha256'])
        self.assertNotEqual(self.meta['source_docs_zip_sha256'],self.meta['expected_ph05112_docs_zip_sha256'])
        self.assertEqual(self.meta['automatic_executor_release_status'],'NO-GO')
        self.assertEqual(self.meta['platform_candidate'],'Windows 11 x64 NTFS per-user')
        self.assertEqual(self.meta['local_web_manual_release_status'], 'NO-GO')
        self.assertEqual(self.meta['platform_acceptance']['report'], 'PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md')
        script=(WEB/'ci_ph_lw_01_windows.ps1').read_text()
        self.assertIn("$env:OS -ne 'Windows_NT'",script)
        self.assertIn('Get-Volume',script)
        self.assertIn('NOT RUN',script)
        self.assertIn('full_regression',script)

    def test_09_additive_resources_available_in_distribution(self):
        for filename in ('control_map_v1.json','metadata_v1.json','gpt_exchange_reply_v1.schema.json','operation_receipt_v1.schema.json'):
            self.assertTrue(PKG.joinpath(filename).is_file(),filename)
            self.assertEqual(PKG.joinpath(filename).read_bytes(), (ROOT/'src/project_harness/resources/local_web'/filename).read_bytes())


if __name__ == '__main__':
    unittest.main()

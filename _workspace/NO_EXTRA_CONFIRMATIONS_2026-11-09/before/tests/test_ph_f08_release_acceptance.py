"""PH-F08 release-only acceptance checks over the actual public CLI.

These use synthetic, explicitly pre-approved fixture decisions, not inferred user
consent or an agent shortcut. Full Stage/Gate/Brownfield/fault coverage is also
exercised by the existing PH-F01..PH-F06 and transaction test modules.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from project_harness.serialization import load_data, write_data
from project_harness.stages import product_baseline_revision
from tests.ph_f06_fixtures import cli, prepared, accept, plan, harness_snapshot, history_snapshot, assert_preserved
from tests.test_engine import load_fixture


class PHF08ReleaseAcceptanceTests(unittest.TestCase):
    def test_i01_minimal_greenfield_waiting_decision_to_exact_first_jit(self):
        with tempfile.TemporaryDirectory(prefix='phf08-greenfield-') as t:
            base = Path(t)
            value = load_fixture()
            value['project']['documentation']['availability'] = 'NONE'
            value['project']['documentation']['normative_sources'] = []
            value['implementation']['target_level'] = 'UNSURE'
            source = base / 'PROJECT_INPUT.json'
            write_data(source, value)
            ws = base / 'intake'
            cli('start-intake', '--workspace', ws, '--project-name', value['project']['name'],
                '--mode', 'GREENFIELD', '--input', source, codes=(0, 3))
            waiting = cli('check-intake', '--workspace', ws, codes=(0, 3))
            self.assertEqual(waiting['status'], 'WAITING_DECISION')
            self.assertEqual(load_data(ws / 'SOURCE_INVENTORY.yaml')['source_inventory']['sources'], [])
            # Fixture's four distinct approvals are previously supplied test data.
            reviewed = load_data(ws / 'PROJECT_INPUT.yaml')
            self.assertEqual(len([k for k, v in reviewed['approvals'].items() if v.get('approved') is True]), 4)
            reviewed['implementation']['target_level'] = 'MVP'
            write_data(ws / 'PROJECT_INPUT.yaml', reviewed)
            self.assertEqual(cli('check-intake', '--workspace', ws)['status'], 'READY_FOR_HANDOFF')
            handoff, root = base / 'handoff.zip', base / 'project'
            compiled = cli('prepare', '--workspace', ws, '--output', handoff, '--keep-directory', root)
            self.assertEqual(compiled['status'], 'READY_FOR_CODEX')
            self.assertTrue(zipfile.is_zipfile(handoff))
            self.assertIsNone(zipfile.ZipFile(handoff).testzip())
            self.assertEqual(cli('validate-handoff', '--project', handoff)['status'], 'PASS')
            self.assertEqual(cli('validate-project', '--project', root)['status'], 'PASS')
            with zipfile.ZipFile(handoff) as archive:
                bundles = [n for n in archive.namelist() if '/prompts/BUNDLES_BY_RUN/' in n and n.endswith('.yaml')]
            self.assertEqual(len(bundles), 1)
            first = cli('next', '--project', root)
            self.assertEqual(first['status'], 'READY_FOR_CODEX')
            self.assertEqual(first['implementation_stage'], 'PROTOTYPE')
            self.assertEqual(first['target_implementation_level'], 'MVP')
            repeat = cli('next', '--project', root)
            self.assertEqual(repeat['run_ref'], first['run_ref'])
            self.assertEqual(len(list((root / '.harness/prompts/BUNDLES_BY_RUN').glob('*.yaml'))), 1)

    def test_i03_i12_prototype_alpha_planning_exact_replay_and_stale_rejection(self):
        with tempfile.TemporaryDirectory(prefix='phf08-planning-') as t:
            base = Path(t)
            root = prepared(base / 'build')
            accepted = accept(root, base / 'prototype-records', 'PROTOTYPE')
            self.assertEqual(accepted['highest_accepted_level'], 'PROTOTYPE')
            self.assertEqual(cli('next', '--project', root)['status'], 'STAGE_PLANNING_REQUIRED')
            before_history = history_snapshot(root)
            draft = base / 'alpha-plan.json'
            cli('prepare-active-stage-plan', '--project', root, '--output', draft)
            stale = base / 'stale-alpha-plan.json'
            shutil.copyfile(draft, stale)
            applied = cli('plan-active-stage', '--project', root, '--plan', draft)
            self.assertEqual(applied['status'], 'STAGE_PLANNED')
            self.assertEqual(applied['active_stage'], 'ALPHA')
            self.assertEqual(applied['first_jit']['status'], 'READY_FOR_CODEX')
            first = cli('next', '--project', root)
            self.assertEqual(first['implementation_stage'], 'ALPHA')
            snapshot = harness_snapshot(root)
            replay = cli('plan-active-stage', '--project', root, '--plan', draft)
            self.assertTrue(replay['idempotent'])
            self.assertEqual(harness_snapshot(root), snapshot)
            # Distinct record with the same reviewed contents cannot create a
            # second stage revision or Task after the first successful commit.
            rejected = cli('plan-active-stage', '--project', root, '--plan', stale, codes=(0, 2, 3))
            self.assertTrue(rejected.get('idempotent') or rejected.get('status') in {'VALIDATION_FAILED', 'STALE'})
            self.assertEqual(harness_snapshot(root), snapshot)
            assert_preserved(root, before_history)
            self.assertEqual(cli('validate-project', '--project', root)['status'], 'PASS')


if __name__ == '__main__':
    unittest.main()

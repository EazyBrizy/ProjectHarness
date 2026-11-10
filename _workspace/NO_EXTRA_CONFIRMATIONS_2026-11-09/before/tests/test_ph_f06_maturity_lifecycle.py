"""PH-F06: public-CLI maturity, Brownfield and maintenance integration."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from project_harness.resources import distribution_root
from project_harness.serialization import load_data, write_data
from project_harness.stages import product_baseline_revision
from tests.maintenance_fixtures import maintenance_plan_document
from tests.ph_f06_fixtures import (ACTOR, AT, LEVELS, accept, assert_preserved, baseline_record, cli,
    complete_task, harness_snapshot, history_snapshot, level_up_record, plan, prepared, supplied_evidence)


class PHF06MaturityLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='phf06-')
        cls.base = Path(cls.temp.name)
        cls.prototype = prepared(cls.base / 'proto')
        accept(cls.prototype, cls.base / 'proto-records', 'PROTOTYPE')
        cls.mvp = cls.base / 'mvp'
        shutil.copytree(cls.prototype, cls.mvp)
        cls.boundaries = []
        for level in LEVELS[1:]:
            previous = history_snapshot(cls.mvp)
            planned = plan(cls.mvp, cls.base / 'mvp-records', level)
            result = accept(cls.mvp, cls.base / 'mvp-records', level)
            assert_preserved(cls.mvp, previous)
            cls.boundaries.append((level, planned, result))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def copy(self, source: Path, name: str) -> Path:
        root = self.base / name
        shutil.copytree(source, root)
        return root

    def test_01_greenfield_all_four_stages_have_verified_immutable_acceptances(self):
        self.assertEqual(cli('next', '--project', self.mvp)['status'], 'TARGET_LEVEL_REACHED')
        reports = [load_data(p)['stage_acceptance'] for p in (self.mvp / '.harness/stages/ACCEPTANCE').glob('*.yaml')]
        self.assertEqual({r['level'] for r in reports}, set(LEVELS))
        self.assertTrue(all(r['acceptance_method'] == 'EXECUTED_STAGE_WORK' and r['evidence_bindings'] for r in reports))
        for level, planned, result in self.boundaries:
            self.assertEqual(planned['active_stage'], level)
            self.assertEqual(planned['first_jit']['status'], 'READY_FOR_CODEX')
            self.assertEqual(result['accepted_levels'], [level])
        self.assertEqual(cli('validate-project', '--project', self.mvp)['status'], 'PASS')

    def test_02_maintenance_complete_level_up_release_and_idempotent_replay(self):
        root = self.copy(self.mvp, 'maintenance-release')
        before = history_snapshot(root)
        state_before = (root / '.harness/stages/STAGE_STATE.yaml').read_bytes()
        path = self.base / 'maintenance.json'
        write_data(path, maintenance_plan_document(root, suffix='PHF06', task_count=2))
        started = cli('start-maintenance', '--project', root, '--plan', path)
        self.assertEqual(started['route'], 'MAINTAIN_CURRENT_STAGE')
        conflicting = self.base / 'maintenance-other.json'
        write_data(conflicting, maintenance_plan_document(root, suffix='CONCURRENT'))
        snapshot = harness_snapshot(root)
        cli('start-maintenance', '--project', root, '--plan', conflicting, codes=(2,))
        self.assertEqual(snapshot, harness_snapshot(root))
        up = level_up_record(self.base / 'after-maintenance-up.json', 'RELEASE', 'AFTER-MAINT')
        cli('level-up', '--project', root, '--target', 'RELEASE', '--approval', up, codes=(2,))
        self.assertEqual(snapshot, harness_snapshot(root))
        for index in range(2):
            nxt = cli('next', '--project', root)
            self.assertEqual(nxt['maintenance_route'], 'MAINTAIN_CURRENT_STAGE')
            with (root / 'README.md').open('a') as f:
                f.write(f'\nMaintenance correction {index}: keep local single-user operating boundary.\n')
            final = complete_task(root, f'Maintenance correction {index}')
        self.assertEqual(final['maintenance']['status'], 'MAINTENANCE_COMPLETED')
        self.assertEqual(state_before, (root / '.harness/stages/STAGE_STATE.yaml').read_bytes())
        self.assertEqual(cli('next', '--project', root)['status'], 'TARGET_LEVEL_REACHED')
        assert_preserved(root, before)
        before = history_snapshot(root)
        result = cli('level-up', '--project', root, '--target', 'RELEASE', '--approval', up)
        self.assertEqual(result['active_stage'], 'RELEASE')
        self.assertEqual(cli('next', '--project', root)['status'], 'STAGE_PLANNING_REQUIRED')
        snapshot = harness_snapshot(root)
        replay = cli('level-up', '--project', root, '--target', 'RELEASE', '--approval', up)
        self.assertTrue(replay['idempotent'])
        self.assertEqual(snapshot, harness_snapshot(root))
        status = cli('stage-status', '--project', root)
        self.assertEqual(status['target_level'], 'RELEASE')
        self.assertEqual(load_data(root / '.harness/config/PROJECT.yaml')['project']['target_implementation_level'], 'RELEASE')
        self.assertEqual(load_data(root / '.harness/state/CURRENT_STATE.yaml')['state']['target_implementation_level'], 'RELEASE')
        self.assertEqual(load_data(root / '.harness/state/PROJECT_INPUT_ACCEPTED.yaml')['implementation']['target_level'], 'MVP')
        result = plan(root, self.base / 'release-records', 'RELEASE')
        self.assertEqual(result['first_jit']['status'], 'READY_FOR_CODEX')
        assert_preserved(root, before)
        self.assertEqual(cli('validate-project', '--project', root)['status'], 'PASS')

    def test_03_lower_equal_targets_noop_and_skip_rejected_without_history_changes(self):
        root = self.copy(self.mvp, 'noop')
        for level in ('PROTOTYPE', 'MVP'):
            path = level_up_record(self.base / f'noop-{level}.json', level, f'NOOP-{level}')
            before = harness_snapshot(root)
            result = cli('level-up', '--project', root, '--target', level, '--approval', path)
            self.assertFalse(result['changed'])
            self.assertEqual(before, harness_snapshot(root))
        root = self.copy(self.prototype, 'skip')
        path = self.base / 'skip.json'
        write_data(path, {'stage_approval': {'id': 'DEC-PHF06-SKIP', 'approved': True, 'actor': ACTOR, 'approved_at': AT,
            'level': 'BETA', 'acceptance_method': 'EXECUTED_STAGE_WORK', 'baseline_revision': product_baseline_revision(root)}})
        before = harness_snapshot(root)
        cli('accept-stage', '--project', root, '--level', 'BETA', '--approval', path, codes=(2,))
        self.assertEqual(before, harness_snapshot(root))

    def test_04_new_level_up_cannot_reset_an_unfinished_cycle_or_active_run(self):
        root = self.copy(self.prototype, 'unfinished')
        up = level_up_record(self.base / 'unfinished-up.json', 'RELEASE', 'UNFINISHED')
        for planned in (False, True):
            if planned:
                plan(root, self.base / 'unfinished-records', 'ALPHA')
            before = harness_snapshot(root)
            result = cli('level-up', '--project', root, '--target', 'RELEASE', '--approval', up, codes=(2,))
            self.assertEqual(result['status'], 'VALIDATION_FAILED')
            self.assertEqual(before, harness_snapshot(root))


class PHF06BrownfieldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phf06-brownfield-')
        self.base = Path(self.temp.name)
        self.root = prepared(self.base / 'build', brownfield=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_05_supplied_proofs_survive_assessment_then_sequential_baseline_reports_and_planner(self):
        root = self.root
        source = self.base / 'proofs.json'
        bodies = supplied_evidence(root, source, ('PROTOTYPE', 'ALPHA'))
        product = product_baseline_revision(root)
        previous = cli('stage-status', '--project', root)['highest_accepted_level']
        result = cli('assess-maturity', '--workspace', root, '--evidence', source)
        self.assertEqual(result['highest_satisfied_candidate_level'], 'ALPHA')
        self.assertEqual(cli('stage-status', '--project', root)['highest_accepted_level'], previous)
        self.assertEqual(product_baseline_revision(root), product)
        for body in bodies:
            imported = load_data(root / f".harness/evidence/{body['id']}.yaml")['verification_evidence']
            self.assertEqual(imported, body)
        approval = baseline_record(root, self.base / 'baseline.json', result, ('PROTOTYPE', 'ALPHA'), bodies, 'TWO')
        accepted = cli('accept-stage', '--project', root, '--level', 'ALPHA', '--approval', approval)
        self.assertEqual(accepted['accepted_levels'], ['PROTOTYPE', 'ALPHA'])
        self.assertEqual(len(accepted['acceptance_refs']), 2)
        for ref in accepted['acceptance_refs']:
            report = load_data(root / f'.harness/stages/ACCEPTANCE/{ref}.yaml')['stage_acceptance']
            self.assertEqual(report['assessment_ref'], result['assessment_ref'])
            self.assertEqual(report['acceptance_method'], 'SATISFIED_BY_BASELINE')
        history = history_snapshot(root)
        self.assertTrue(cli('accept-stage', '--project', root, '--level', 'ALPHA', '--approval', approval)['idempotent'])
        plan(root, self.base / 'beta-records', 'BETA')
        assert_preserved(root, history)
        self.assertEqual(cli('validate-project', '--project', root)['status'], 'PASS')

    def test_06_readme_beta_missing_execution_evidence_do_not_accept_or_run_commands(self):
        root = self.root
        product = product_baseline_revision(root)
        history = history_snapshot(root)
        runs = sorted((root / '.harness/runtime/RUNS').glob('*'))
        result = cli('assess-maturity', '--workspace', root)
        self.assertEqual(result['highest_satisfied_candidate_level'], 'NONE')
        self.assertEqual(cli('stage-status', '--project', root)['highest_accepted_level'], 'NONE')
        report = load_data(Path(result['assessment_path']))['maturity_assessment']
        core = next(x for x in report['criteria_results']['PROTOTYPE'] if x['criterion_ref'] == 'PROTOTYPE_CORE_FLOW')
        self.assertEqual(core['status'], 'UNKNOWN')
        self.assertEqual(product_baseline_revision(root), product)
        self.assertEqual(sorted((root / '.harness/runtime/RUNS').glob('*')), runs)
        assert_preserved(root, history)

    def test_07_stale_tree_and_exact_assessment_digest_never_mutate_acceptance(self):
        root = self.root
        source = self.base / 'proofs.json'
        bodies = supplied_evidence(root, source, ('PROTOTYPE',))
        assessment = cli('assess-maturity', '--workspace', root, '--evidence', source)
        with (root / 'README.md').open('a') as f:
            f.write('\nChanged after assessment.\n')
        approval = baseline_record(root, self.base / 'stale.json', assessment, ('PROTOTYPE',), bodies, 'STALE')
        before = harness_snapshot(root, exclude_assessments=True)
        result = cli('accept-stage', '--project', root, '--level', 'PROTOTYPE', '--approval', approval)
        self.assertEqual(result['status'], 'STALE')
        self.assertEqual(before, harness_snapshot(root, exclude_assessments=True))
        record = load_data(approval)
        record['stage_approval']['assessment_digest'] = 'sha256:' + '0' * 64
        write_data(approval, record)
        before = harness_snapshot(root)
        cli('accept-stage', '--project', root, '--level', 'PROTOTYPE', '--approval', approval, codes=(2,))
        self.assertEqual(before, harness_snapshot(root))

    def test_08_baseline_acceptance_cannot_bypass_concurrent_maintenance(self):
        root = self.root
        source = self.base / 'all-proof.json'
        bodies = supplied_evidence(root, source, ('PROTOTYPE', 'ALPHA'))
        assessment = cli('assess-maturity', '--workspace', root, '--evidence', source)
        approval = baseline_record(root, self.base / 'proto-baseline.json', assessment, ('PROTOTYPE',), bodies, 'PROTO')
        cli('accept-stage', '--project', root, '--level', 'PROTOTYPE', '--approval', approval)
        assessment = cli('assess-maturity', '--workspace', root, '--evidence', source)
        approval = baseline_record(root, self.base / 'alpha-baseline.json', assessment, ('ALPHA',), bodies, 'ALPHA')
        maintenance = self.base / 'maintenance.json'
        write_data(maintenance, maintenance_plan_document(root, suffix='BROWN-CONCURRENT'))
        cli('start-maintenance', '--project', root, '--plan', maintenance)
        before = harness_snapshot(root)
        cli('accept-stage', '--project', root, '--level', 'ALPHA', '--approval', approval, codes=(2,))
        self.assertEqual(before, harness_snapshot(root))


    def test_10_clean_read_only_assessment_keeps_reserved_run_executable(self):
        root = self.root
        before = cli('next', '--project', root)
        product = product_baseline_revision(root)
        for _ in range(2):
            assessment = cli('assess-maturity', '--workspace', root)
            self.assertEqual(assessment['highest_satisfied_candidate_level'], 'NONE')
            self.assertEqual(product_baseline_revision(root), product)
        after = cli('next', '--project', root)
        self.assertEqual(before['run_ref'], after['run_ref'])
        result = complete_task(root, 'Existing product independently verified after read-only assessment')
        self.assertIn('next', result)
        self.assertEqual(cli('validate-project', '--project', root)['status'], 'PASS')

    def test_11_assessment_never_launders_preexisting_control_plane_tampering(self):
        root = self.root
        index = load_data(root / '.harness/tasks/INDEX.yaml')['task_index']
        path = root / index['current'][index['order'][0]]
        task = load_data(path)
        task['task']['purpose'] = 'Unauthorized control-plane edit before read-only assessment'
        write_data(path, task)
        cli('assess-maturity', '--workspace', root)
        result = cli('verify', '--project', root, '--allow-command-execution', codes=(3,))
        self.assertEqual(result['reason'], 'SAFETY_VIOLATION')
        self.assertEqual(result['commands'], [])

    def test_12_normalized_proof_tamper_or_generic_pass_rejected_before_import(self):
        root = self.root
        source = self.base / 'proofs.json'
        bodies = supplied_evidence(root, source, ('PROTOTYPE',))
        for corrupt in ('semantic', 'source', 'not_applicable'):
            values = deepcopy(bodies)
            if corrupt == 'semantic':
                values[-1]['details'] = {}
            elif corrupt == 'source':
                values[-1]['source_bindings'][0]['sha256'] = 'sha256:' + '0' * 64
            else:
                values[-1]['status'] = 'NOT_APPLICABLE'
                values[-1].pop('rationale', None)
                values[-1].pop('validator', None)
            write_data(source, {'evidence': values})
            before = harness_snapshot(root)
            cli('assess-maturity', '--workspace', root, '--evidence', source, codes=(2,))
            self.assertEqual(before, harness_snapshot(root))

    def test_13_stale_normalized_reimport_keeps_immutable_fact_and_downgrades_assessment(self):
        root = self.root
        source = self.base / 'proofs.json'
        bodies = supplied_evidence(root, source, ('PROTOTYPE',))
        first = cli('assess-maturity', '--workspace', root, '--evidence', source)
        self.assertEqual(first['highest_satisfied_candidate_level'], 'PROTOTYPE')
        history = history_snapshot(root)
        with (root / 'README.md').open('a') as f:
            f.write('\nNew product baseline; old proofs must remain stale.\n')
        second = cli('assess-maturity', '--workspace', root, '--evidence', source)
        self.assertEqual(second['status'], 'STALE')
        self.assertEqual(second['highest_satisfied_candidate_level'], 'NONE')
        assert_preserved(root, history)



class PHF06MigrationTests(unittest.TestCase):
    def test_09_migration_restart_preserves_historical_completed_runs(self):
        with tempfile.TemporaryDirectory(prefix='phf06-migration-') as temp:
            base = Path(temp)
            fixture = distribution_root() / 'fixtures/legacy_v0.4.1_completed_handoff.zip'
            with zipfile.ZipFile(fixture) as archive:
                archive.extractall(base)
            roots = list(base.rglob('CURRENT_STATE.yaml'))
            self.assertEqual(len(roots), 1)
            root = roots[0].parents[2]
            runs = {p.relative_to(root).as_posix(): p.read_bytes() for p in (root / '.harness/runtime/RUNS').glob('*.yaml')}
            self.assertTrue(runs)
            result = cli('migrate-project', '--project', root, codes=(0, 3))
            self.assertIn(result['status'], {'MIGRATED', 'WAITING_INPUT', 'WAITING_DECISION'})
            # Migration has an explicit approved input when a historical fixture
            # has no target. Never patch legacy state to make it pass.
            if result['status'] != 'MIGRATED':
                from project_harness.project_input import migrate_project_input
                inp = base / 'approved-input.json'
                data, _ = migrate_project_input(load_data(root / '.harness/state/PROJECT_INPUT_ACCEPTED.yaml'))
                data['implementation']['target_level'] = 'MVP'
                write_data(inp, data)
                result = cli('migrate-project', '--project', root, '--input', inp)
            self.assertEqual(cli('validate-project', '--project', root)['status'], 'PASS')
            cli('next', '--project', root, codes=(0, 3))
            cli('migrate-project', '--project', root)
            self.assertEqual(runs, {p: (root / p).read_bytes() for p in runs})

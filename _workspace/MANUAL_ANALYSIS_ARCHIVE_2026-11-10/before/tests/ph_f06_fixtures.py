"""PH-F06 operator fixtures: public CLI transitions and supplied operator evidence records only.

The external agent and accountable reviewer are deterministic TEST actors. These
bounded local-CLI sources exercise governance; they do not certify deployment,
security or production suitability of another project. No state/indices/Run/Gate
or Acceptance Report is edited by the fixture.
"""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from project_harness.cli import main
from project_harness.evidence import gate_proof_methods, normalized_evidence_body
from project_harness.hashing import sha256_file
from project_harness.registry import implementation_level_model
from project_harness.serialization import load_data, write_data
from project_harness.stages import product_baseline_revision
from tests.test_engine import load_fixture, add_brownfield_approval, implement_first_task, implement_second_task, write_agent_result
from tests.ph_f06_product_checks import install_checks

ACTOR = 'ACT-PHF06-REVIEWER-001'
AT = '2026-10-24T10:00:00Z'
LEVELS = ('PROTOTYPE', 'ALPHA', 'BETA', 'MVP')


def cli(*argv: object, codes: tuple[int, ...] = (0,)) -> dict:
    args = [str(a) for a in argv]
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(args)
    result = json.loads(out.getvalue())
    log = os.environ.get('PH_F06_CLI_LOG')
    if log:
        with Path(log).open('a', encoding='utf-8') as f:
            f.write(json.dumps({'argv': args, 'exit_code': code, 'result': result}, ensure_ascii=False) + '\n')
    if code not in codes:
        raise AssertionError({'argv': args, 'exit_code': code, 'result': result})
    return result


def prepared(base: Path, *, brownfield: bool = False, target: str = 'MVP') -> Path:
    base.mkdir(parents=True, exist_ok=True)
    data = load_fixture()
    data['implementation']['target_level'] = target
    args: list[object] = []
    if brownfield:
        data['project']['mode'] = 'BROWNFIELD'
        data['brownfield']['baseline_summary'] = 'Existing local task CLI, not a maturity claim.'
        add_brownfield_approval(data)
        data['implementation']['claimed_current_level'] = 'BETA'
        repository = base / 'repository'
        repository.mkdir()
        (repository / 'README.md').write_text('# Claimed beta\nA label is not verified maturity.\n', encoding='utf8')
        implement_first_task(repository)
        implement_second_task(repository)
        install_checks(repository)
        args = ['--repository', repository]
    inp = base / 'input.json'
    write_data(inp, data)
    ws = base / 'intake'
    cli('start-intake', '--workspace', ws, '--project-name', data['project']['name'],
        '--mode', data['project']['mode'], '--input', inp, *args)
    assert cli('check-intake', '--workspace', ws)['status'] == 'READY_FOR_HANDOFF'
    root = base / 'project'
    result = cli('prepare', '--workspace', ws, '--output', base / 'handoff.zip', '--keep-directory', root)
    assert result['status'] == 'READY_FOR_CODEX'
    assert cli('validate-handoff', '--project', base / 'handoff.zip')['status'] == 'PASS'
    return root


def proof(root: Path, subject: str, kind: str, *, mapping: str = 'criterion_refs') -> dict:
    """Supply one exact-baseline source, never clone a runtime PASS report."""
    token = re.sub(r'[^A-Z0-9-]', '-', subject.upper()) + '-' + product_baseline_revision(root)[-12:].upper()
    evidence_id, source_ref = f'EVD-PHF06-{token}', f'SRC-PHF06-{token}'
    method = gate_proof_methods(kind)[0]
    source_rel = f'.harness/operator/SOURCES/{token}.' + ('md' if method == 'DOCUMENT_REVIEW' else 'json')
    source = root / source_rel
    source.parent.mkdir(parents=True, exist_ok=True)
    checks = [f'Fixture reviewer evaluated {subject} for the bounded local single-user task CLI.']
    semantic = {'subject_ref': subject, 'kind': kind, 'method': method, 'status': 'PASS',
                'coverage': f'{subject}: bounded local CLI fixture; no remote deployment or production certification.',
                'source_ref': source_ref, 'checked_items': checks}
    source_type = {'DOCUMENT_REVIEW': 'OPERATOR_SUPPLIED_DOCUMENT', 'EXECUTED_TEST': 'INDEPENDENT_TEST_EXECUTION',
                   'OPERATOR_VERIFICATION': 'INDEPENDENT_OPERATOR_REVIEW', 'EXTERNAL_SOURCE': 'EXTERNAL_EVIDENCE_IMPORT'}[method]
    provenance = {'source_type': source_type, 'source_ref': source_ref, 'producer': 'PH_F06_TEST_OPERATOR', 'actor': ACTOR}
    if method == 'DOCUMENT_REVIEW':
        source.write_text(f'''# {subject} / {kind}

This reviewed test-fixture record covers the single-user local task CLI only.
Architecture: task_cli.py defines the parsing, storage and command component
boundaries. The store is a local JSON file selected by --data; add, list and done
are the accepted public commands. Run command: python task_cli.py --data tasks.json list.
Known limitations: no network service, concurrency or production authorization.
Permitted environment: isolated local test directory, synthetic data only.
The fixture operator owns backup of the JSON file, restoration before retry,
manual stderr/exit-code inspection and support by reproducing the command.
No external deployment, compliance audit or general production readiness is claimed.
For {subject}, this source is a bounded operator review input, not an automatic
conclusion from the Engine's generic verification report.
''', encoding='utf8')
    elif method == 'EXECUTED_TEST':
        # Independent selected real test with explicit scope. This is a fixture
        # input to test binding/lifecycle, not proof of all production properties.
        test_ref = 'test_core_cli_contract'
        if 'PERFORMANCE' in subject or 'CAPACITY' in subject:
            test_ref = 'test_bounded_performance_baseline'
        elif 'MONITOR' in subject or 'ERROR' in subject:
            test_ref = 'test_errors_edge_cases_and_operator_alert'
        elif 'RECOVERY' in subject or 'BACKUP' in subject or 'ROLLBACK' in subject:
            test_ref = 'test_backup_restore_rollback_and_data_lifecycle'
        elif 'REGRESSION' in subject or 'CRITICAL_TEST' in subject:
            test_ref = 'test_declared_release_regression'
        elif 'INTEGRATION' in subject or 'PERSISTENCE' in subject:
            test_ref = 'test_real_persistence_and_configuration'
        elif 'DEPLOYMENT' in subject:
            test_ref = 'test_reproducible_local_install'
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-t', 'tests', '-p', 'test_phf06_product.py', '-k', test_ref]
        run = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=25, check=False)
        if run.returncode or 'Ran 1 test' not in run.stdout + run.stderr:
            raise AssertionError({'subject': subject, 'command': command, 'stderr': run.stderr})
        semantic['test_ref'] = test_ref
        write_data(source, {'test_execution': {'subject_ref': subject, 'test_ref': test_ref, 'status': 'PASS',
                   'exit_code': run.returncode, 'command': command, 'checks': checks, 'output': run.stdout + run.stderr}})
    elif method == 'OPERATOR_VERIFICATION':
        write_data(source, {'operator_verification': {'subject_ref': subject, 'status': 'PASS', 'actor': ACTOR,
                   'checks': checks, 'rationale': 'Explicit synthetic test-operator conclusion, not auto-approval.'}})
    else:
        provenance['details'] = {'issuer': 'PH-F06-FIXTURE', 'origin': 'fixture://PH-F06/source'}
        write_data(source, {'external_evidence': {'subject_ref': subject, 'status': 'PASS', 'issuer': 'PH-F06-FIXTURE', 'checks': checks}})
    body = normalized_evidence_body(evidence_id=evidence_id, kind=kind, status='PASS', provenance=provenance,
            base_revision=product_baseline_revision(root), criterion_refs=[subject] if mapping == 'criterion_refs' else [],
            outcome_refs=[subject] if mapping == 'outcome_refs' else [], profile_control_refs=[subject] if mapping == 'profile_control_refs' else [],
            source_bindings=[{'ref': source_ref, 'path': source_rel, 'sha256': f'sha256:{sha256_file(source)}'}],
            created_at=AT, rationale=f'PH-F06 supplied fixture review for {subject}.', validator=ACTOR,
            details={'semantic_proof': semantic})
    return body


def submit_gate_sources(root: Path, draft: dict, record_path: Path) -> None:
    bodies = []
    for collection, field, mapping in [('level_criteria', 'criterion_ref', 'criterion_refs'),
                                       ('hard_constraints', 'constraint_ref', 'criterion_refs'),
                                       ('required_outcomes', 'outcome_ref', 'outcome_refs'),
                                       ('profile_controls', 'control_ref', 'profile_control_refs')]:
        for item in draft[collection]:
            bodies.append(proof(root, item[field], (item.get('required_evidence_kinds') or ['REVIEW_RECORD'])[0], mapping=mapping))
    write_data(record_path, {'evidence': bodies})
    cli('assess-maturity', '--workspace', root, '--evidence', record_path)


def complete_task(root: Path, summary: str) -> dict:
    context = cli('task-manual-context', '--project', root)
    if context['binding']['checks']:
        missing = cli('verify', '--project', root, '--allow-command-execution', codes=(3,))
        assert missing['status'] == 'BLOCKED' and missing['gates']['manual_checks'] == 'BLOCKED', missing
        # Independent TEST reviewer actually exercises the product and inspects
        # the exact product sources. It supplies Task proof BEFORE verification;
        # later Stage proof/approval remains a separate public workflow.
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_phf06_product.py']
        checked = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=60)
        assert checked.returncode == 0 and re.search(r'Ran [1-9]\d* tests?', checked.stdout+checked.stderr), checked.stderr
        for path in ('README.md','task_cli.py','tests/test_phf06_product.py'):
            assert (root/path).read_text('utf-8').strip(), path
        document = {**context['binding'], 'reviewer':ACTOR, 'checks':[
            {'index':index,'check':check,'status':'PASS',
             'observation':f'Independent fixture reviewer evaluated {check}. Read README, CLI implementation and acceptance tests. Actual product checks: {checked.stdout}{checked.stderr}. Bounded local CLI only; Stage criterion proof remains separate.',
             'sources':[{'path':path,'sha256':'sha256:'+context['product_files'][path]['sha256']} for path in ('README.md','task_cli.py','tests/test_phf06_product.py')]}
            for index,check in enumerate(context['binding']['checks'])]}
        review_path = root.parent / 'task-review.json'
        write_data(review_path,document)
        received = cli('record-task-manual-evidence','--project',root,'--input',review_path,'--confirm')
        assert received['review_status']=='PASS', received
    verification = cli('verify', '--project', root, '--allow-command-execution')
    assert verification['status'] == 'PASS', verification
    result_path = write_agent_result(root, verification, summary)
    return cli('complete', '--project', root, '--result', result_path, codes=(0, 3))


def reach_gate(root: Path, records: Path, level: str) -> Path:
    records.mkdir(parents=True, exist_ok=True)
    for _ in range(35):
        nxt = cli('next', '--project', root, codes=(0, 3))
        if nxt['status'] != 'READY_FOR_CODEX':
            break
        task_ref = nxt['task_ref'].split('@')[0]
        index = load_data(root / '.harness/tasks/INDEX.yaml')['task_index']
        task = load_data(root / index['current'][task_ref])['task']
        assert task['implementation_stage'] == level
        if not task.get('stage_acceptance_preparation'):
            if level == 'PROTOTYPE' and not (root / 'task_cli.py').exists():
                implement_first_task(root)
            elif level == 'PROTOTYPE' and 'def complete_task(' not in (root / 'task_cli.py').read_text():
                implement_second_task(root)
                install_checks(root)
            else:
                with (root / 'README.md').open('a', encoding='utf8') as f:
                    f.write(f"\n## {level} bounded review\n{task['purpose']}\n")
        complete_task(root, f'External fixture agent completed {task_ref}')
    else:
        raise AssertionError('Task route did not terminate within the bounded active Stage')
    assert nxt['status'] in {'BLOCKED', 'VERIFYING'}, nxt
    path = records / f'{level}-approval.json'
    cli('prepare-stage-approval', '--project', root, '--output', path, '--force')
    submit_gate_sources(root, load_data(path)['stage_approval'], records / f'{level}-sources.json')
    if nxt['status'] == 'BLOCKED':
        assert cli('resume-stage-gate', '--project', root)['status'] == 'VERIFYING'
    cli('prepare-stage-approval', '--project', root, '--output', path, '--force')
    document = load_data(path)
    record = document['stage_approval']
    candidates: dict[str, str] = {}
    for candidate in record['evidence_candidates']:
        for subject in candidate['compatible_subject_refs']:
            candidates[subject] = candidate['ref']
    for field, key in [('criteria_results', 'criterion_ref'), ('hard_constraint_results', 'constraint_ref'),
                       ('outcome_results', 'outcome_ref'), ('profile_control_results', 'control_ref')]:
        for item in record[field]:
            item.update(status='PASS', evidence_refs=[candidates[item[key]]],
                        rationale='Explicit fixture operator review of the exact-bound source.', validator=ACTOR)
    record.update(record_state='APPROVED', id=f'DEC-PHF06-{level}-ACCEPT', approved=True, actor=ACTOR,
                  approved_at=AT, known_limitations=['Synthetic local CLI integration fixture; not production certification.'],
                  next_stage_gaps=['Review the next active stage within accepted scope.'], notes='PH-F06 public CLI exercise')
    record['permitted_use']['status'] = 'CONFIRMED'
    write_data(path, document)
    return path


def accept(root: Path, records: Path, level: str) -> dict:
    path = reach_gate(root, records, level)
    result = cli('accept-stage', '--project', root, '--level', level, '--approval', path)
    assert result['highest_accepted_level'] == level, result
    assert cli('validate-project', '--project', root)['status'] == 'PASS'
    return result


def plan(root: Path, records: Path, level: str) -> dict:
    records.mkdir(parents=True, exist_ok=True)
    path = records / f'{level}-plan.json'
    cli('prepare-active-stage-plan', '--project', root, '--output', path, '--force')
    result = cli('plan-active-stage', '--project', root, '--plan', path)
    assert result['first_jit']['status'] == 'READY_FOR_CODEX', result
    assert result['active_stage'] == level
    return result


def level_up_record(path: Path, target: str, suffix: str) -> Path:
    write_data(path, {'level_up_approval': {'id': f'DEC-PHF06-UP-{suffix}', 'approved': True,
               'actor': ACTOR, 'approved_at': AT, 'target_level': target, 'rationale': 'Explicit new bounded target cycle.'}})
    return path


def gate_requirements(root: Path, level: str) -> dict[str, list[str]]:
    model = implementation_level_model()
    result = {s: model['criteria'][s]['required_evidence_kinds'] for s in model['profiles'][level]['criteria_refs']}
    index = load_data(root / '.harness/stages/GATES/INDEX.yaml')['stage_gate_index']
    gate = load_data(root / index['current'][index['by_level'][level]])['stage_gate']
    result.update({item['key']: item['required_evidence_kinds'] for item in gate.get('hard_constraint_overrides') or []})
    return result


def baseline_record(root: Path, path: Path, assessment: dict, levels: tuple[str, ...], bodies: list[dict], suffix: str) -> Path:
    by_subject = {s: body['id'] for body in bodies for s in body['criterion_refs']}
    model = implementation_level_model()
    level_records = {}
    for level in levels:
        level_records[level] = {'criteria_results': [{'criterion_ref': ref, 'status': 'PASS', 'evidence_refs': [by_subject[ref]],
            'rationale': 'Explicit supplied exact-subject fixture proof.', 'validator': ACTOR} for ref in gate_requirements(root, level)],
            'evidence_refs': [], 'permitted_use': {'users': ['DEVELOPER'], 'environments': ['LOCAL'], 'data_classes': ['PUBLIC'], 'data_constraints': ['SYNTHETIC_ONLY']},
            'known_limitations': ['Test fixture only.'], 'next_stage_gaps': ['Review only the next active stage.']}
    write_data(path, {'stage_approval': {'id': f'DEC-PHF06-BASELINE-{suffix}', 'approved': True, 'actor': ACTOR, 'approved_at': AT,
        'level': levels[-1], 'acceptance_method': 'SATISFIED_BY_BASELINE', 'baseline_revision': product_baseline_revision(root),
        'assessment_ref': assessment['assessment_ref'], 'assessment_digest': assessment['assessment_digest'], 'levels': level_records}})
    return path


def supplied_evidence(root: Path, path: Path, levels: tuple[str, ...]) -> list[dict]:
    model = implementation_level_model()
    subjects = {subject: kinds for level in levels for subject, kinds in gate_requirements(root, level).items()}
    bodies = [proof(root, subject, kinds[0]) for subject, kinds in subjects.items()]
    write_data(path, {'evidence': bodies})
    return bodies


def harness_snapshot(root: Path, *, exclude_assessments: bool = False) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in (root / '.harness').rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and not (exclude_assessments and 'ASSESSMENTS' in p.parts)}


def history_snapshot(root: Path) -> dict[str, str]:
    files = [root / '.harness/state/PROJECT_INPUT_ACCEPTED.yaml']
    for name in ('stages/ACCEPTANCE', 'stages/STATE_HISTORY', 'stages/PLANS', 'stages/GATES', 'runtime/RUNS', 'runtime/TASK_REPORTS', 'evidence'):
        files.extend(p for p in (root / '.harness' / name).glob('*.yaml') if p.name != 'INDEX.yaml')
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in files if p.is_file()}


def assert_preserved(root: Path, before: dict[str, str]) -> None:
    for relative, digest in before.items():
        assert (root / relative).is_file() and sha256_file(root / relative) == digest, relative

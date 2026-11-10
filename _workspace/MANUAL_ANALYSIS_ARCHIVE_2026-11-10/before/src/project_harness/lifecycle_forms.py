"""Read-only public preparations for Local Web lifecycle forms (PH-LW-10).

These projections never accept a Stage, execute repository commands, or write
canonical records. The existing public mutators remain authoritative.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
from .errors import ValidationFailure
from .hashing import sha256_file
from .serialization import load_data
from .platform_fs import ensure_native_path
from .stages import canonical_levels, load_stage_state, stage_status


def assert_manual(root: Path, *, workspace: bool = False) -> None:
    path = root / ('PROJECT_INPUT.yaml' if workspace else '.harness/state/PROJECT_INPUT_ACCEPTED.yaml')
    value = load_data(path)
    if (value.get('execution') or {}).get('mode', 'MANUAL_HANDOFF') != 'MANUAL_HANDOFF':
        raise ValidationFailure('AUTOMATIC_DISABLED')
    if not workspace:
        lock = load_data(root / '.harness/config/PROJECT_LOCK.yaml')['project_lock']
        if (lock.get('execution') or {}).get('mode', 'MANUAL_HANDOFF') != 'MANUAL_HANDOFF':
            raise ValidationFailure('AUTOMATIC_DISABLED')
        from .runtime import automatic_run_phase
        active = load_data(root / '.harness/state/CURRENT_STATE.yaml')['state'].get('active_run')
        if active and automatic_run_phase(root, active): raise ValidationFailure('AUTOMATIC_DISABLED')


def lifecycle_overview(root: Path) -> dict:
    from .stage_gate_lifecycle import missing_gate_evidence_items
    from .maintenance import active_maintenance
    status = stage_status(root)
    readiness = missing_gate_evidence_items(root)
    history = []
    for folder, envelope in [('stages/ACCEPTANCE', 'stage_acceptance'), ('stages/ACCEPTANCE_REPORTS', 'stage_acceptance')]:
        for p in sorted((root / '.harness' / folder).glob('*.yaml')):
            record = load_data(p).get(envelope)
            if record:
                history.append({'record': record, 'sha256': sha256_file(p)})
    record_history = {}
    for folder in ('runtime/RUNS', 'runtime/TASK_REPORTS', 'evidence'):
        paths = sorted((root / '.harness' / folder).glob('*.yaml'))
        if len(paths) > 1000: raise ValidationFailure('Lifecycle history exceeds 1000 records per category')
        rows = []
        for path in paths:
            if path.stat().st_size > 8 * 1024 * 1024: raise ValidationFailure('Lifecycle history record too large')
            doc = load_data(path)
            body = next(iter(doc.values())) if len(doc) == 1 else doc
            if not isinstance(body, dict): continue
            rows.append({'path': path.relative_to(root).as_posix(), 'digest': 'sha256:' + sha256_file(path),
                **{k: v for k, v in body.items() if k in {'id','revision','status','run_ref','task_ref','level',
                    'implementation_stage','baseline_revision','kind','evidence_refs','criterion_refs','outcome_refs'}}})
        record_history[folder] = rows
    return {'status': status, 'definitions': readiness['definitions'], 'record_history': record_history,
            'missing_subjects': readiness['missing_items'], 'evidence_candidates': readiness['candidates'],
            'maintenance': active_maintenance(root), 'acceptance_history': history,
            'stage_state': load_stage_state(root)}


def repository_binding(workspace: Path) -> dict | None:
    """Bind both the recorded inventory AND the current read-only source tree."""
    p = workspace / 'REPOSITORY_INVENTORY.yaml'
    if not p.is_file():
        return None
    from .inventory import build_repository_inventory
    original = load_data(p)['repository_inventory']
    state = load_data(workspace / 'STATE.yaml')['state']
    repository = Path(state.get('effective_repository_path') or original['repository_path'])
    ensure_native_path(repository, tree=True)
    current = build_repository_inventory(repository, session_ref=original['session_ref'])['repository_inventory']
    keys = ('repository_revision', 'tree_digest', 'file_count')
    return {'inventory_ref': f"{original['id']}@{original['revision']}", 'inventory_digest': 'sha256:' + sha256_file(p),
            'selected_repository': str(repository), 'recorded': {k: original[k] for k in keys},
            'current': {k: current[k] for k in keys}, 'read_only': True,
            'stale': any(original[k] != current[k] for k in keys)}


def assessment_overview(workspace: Path) -> dict:
    binding = repository_binding(workspace)
    records = []
    paths = ([workspace / 'MATURITY_ASSESSMENT.yaml'] if (workspace / 'MATURITY_ASSESSMENT.yaml').is_file() else [])
    paths += sorted((workspace / '.harness/stages/ASSESSMENTS').glob('VAL-*MATURITY*@*.yaml'))
    for p in paths:
        value = load_data(p).get('maturity_assessment')
        if value:
            records.append({'ref': f"{value['id']}@{value['revision']}", 'digest': 'sha256:' + sha256_file(p), 'record': value})
    return {'repository': binding, 'assessments': records, 'baseline_approval_required': True}


def maintenance_draft(root: Path, *, suffix: str) -> dict:
    """Unsigned form model; the existing schema accepts only the signed plan."""
    from .maintenance import _project_context, _assert_start_idle
    ctx = _project_context(root)
    _assert_start_idle(root, ctx)
    stage = ctx['stage']; level = stage['highest_accepted_level']; token = ctx['project']['id_token']
    if level not in canonical_levels():
        raise ValidationFailure('Maintenance requires a formally accepted level')
    wp_id = f'WP-{token}-MAINT-{suffix}'
    task = {'id': f'TSK-{token}-MAINT-{suffix}-001', 'title': '', 'type': 'DOCUMENT', 'priority': 'NORMAL',
            'purpose': '', 'expected_result': '', 'implementation_stage': level, 'product_changing': True,
            'future_stage_work': 'FORBIDDEN', 'depends_on_tasks': [], 'requirement_refs': [], 'constraint_refs': [],
            'architecture_refs': [], 'produces_artifacts': [], 'scope': {'read': [], 'write': [],
                'forbidden': ['CODEX_START.md', 'PROJECT.md', 'ARCHITECTURE.md', 'TECHNOLOGY.md']},
            'route': {'primary_skill_ref': 'SKL-UNIVERSAL-DOCUMENT@1', 'supporting_skill_refs': [],
                      'required_capabilities': ['FILESYSTEM_READ', 'FILESYSTEM_WRITE']},
            'prompt_spec_ref': 'PSP-IMPLEMENT@1', 'verification': {'commands': [], 'expected_paths': [],
                'manual_checks': [], 'timeout_seconds': 300, 'allow_manual': True},
            'documentation': {'source_refs': [], 'impact': 'REVIEW_REQUIRED', 'required_updates': []},
            'acceptance_criteria': [], 'rollback': {'strategy': 'RESTORE_PRE_RUN_SNAPSHOT'}}
    return {'maintenance_plan': {'schema_version': 1, 'schema_ref': 'SCHEMA-MAINTENANCE-PLAN@1',
        'record_kind': 'MAINTENANCE_PLAN', 'id': f'RQP-{token}-MAINT-{suffix}', 'revision': 1,
        'status': 'DRAFT', 'route': 'MAINTAIN_CURRENT_STAGE', 'highest_accepted_level': level,
        'implementation_stage': level, 'target_level': stage['target_level'], 'last_acceptance_ref': stage['last_acceptance_ref'],
        'accepted_scope_ref': ctx['definition']['scope_ref'], 'objective': '', 'rationale': '',
        'decision': {'id': f'DEC-{token}-MAINT-{suffix}', 'kind': 'MAINTAIN_CURRENT_STAGE',
                     'approved': False, 'actor': None, 'approved_at': None},
        'scope_boundary': {'future_stage_work': 'FORBIDDEN', 'future_stage_refs': []},
        'work_package': {'id': wp_id, 'title': '', 'objective': '', 'implementation_stage': level, 'tasks': [task]},
        'verification_constraints': {'independent_verification_required': True, 'completion_requires_pass': True},
        'rollback_constraints': {'automatic_rollback': False, 'strategy': 'RESTORE_PRE_RUN_SNAPSHOT'},
        'cancel_constraints': {'before_product_change_only': True,
                               'completed_product_change_action': 'REQUIRE_COMPLETION_OR_GOVERNED_COMPENSATION'}}}


def maintenance_cancel_draft(root: Path, *, suffix: str) -> dict:
    from .maintenance import active_maintenance
    current = active_maintenance(root)
    if current is None:
        raise ValidationFailure('No active maintenance')
    stage = load_stage_state(root)
    token = load_data(root / '.harness/config/PROJECT.yaml')['project']['id_token']
    return {'maintenance_cancel_approval': {'schema_version': 1, 'schema_ref': 'SCHEMA-MAINTENANCE-CANCEL-APPROVAL@1',
        'record_kind': 'MAINTENANCE_CANCEL_APPROVAL', 'id': f'DEC-{token}-MAINT-CANCEL-{suffix}', 'revision': 1,
        'kind': 'CANCEL_MAINTENANCE', 'approved': False, 'actor': None, 'approved_at': None,
        'maintenance_plan_ref': current['plan_ref'], 'work_package_ref': current['work_package_ref'],
        'highest_accepted_level': stage['highest_accepted_level'], 'target_level': stage['target_level'],
        'last_acceptance_ref': stage['last_acceptance_ref'], 'rationale': '', 'cancel_mode': 'PRE_PRODUCT_CHANGE_ONLY'}}


def migration_preview(root: Path) -> dict:
    from .validation import validate_handoff_directory, ENGINE_VERSION, SCHEMA_VERSION, V050_ENGINE_VERSION, V050_SCHEMA_VERSION, LEGACY_ENGINE_VERSION, LEGACY_SCHEMA_VERSION
    from .migration import _load_migration_input
    recovery = migration_recovery_context(root)
    if recovery:
        return {'status': 'RECOVERY_REQUIRED', 'supported': False, 'recovery': recovery,
                'default_execution': 'MANUAL_HANDOFF', 'limitations': ['Explicit migrate_project recovery must validate the journal and restore or retain the committed tree; no GET repair.']}
    lock = load_data(root / '.harness/config/PROJECT_LOCK.yaml')['project_lock']
    version = (lock.get('harness_distribution'), lock.get('schema_version'))
    supported = version in {(ENGINE_VERSION, SCHEMA_VERSION), (V050_ENGINE_VERSION, V050_SCHEMA_VERSION), (LEGACY_ENGINE_VERSION, LEGACY_SCHEMA_VERSION)}
    validation = validate_handoff_directory(root, check_manifest=False, check_control_plane_state=False)
    candidate = None; input_error = None
    if version == (LEGACY_ENGINE_VERSION, LEGACY_SCHEMA_VERSION):
        try:
            candidate, _, _ = _load_migration_input(root, None)
        except ValidationFailure as exc:
            input_error = exc.message
    return {'source_engine': version[0], 'source_schema': version[1], 'target_engine': ENGINE_VERSION,
        'target_schema': SCHEMA_VERSION, 'supported': supported and validation['status'] == 'PASS',
        'validation': validation, 'input_document': candidate, 'input_error': input_error,
        'default_execution': 'MANUAL_HANDOFF', 'limitations': ['Immutable accepted inputs, completed Runs and Stage reports are preserved.',
        'Migration does not accept maturity or enable automatic execution.', 'Unsupported or invalid projects require diagnosis; no automatic repair.']}


def migration_recovery_context(root: Path) -> dict | None:
    from .migration import _migration_marker
    marker = _migration_marker(root)
    if not marker.exists(): return None
    ensure_native_path(marker, file_ok=True)
    if not marker.is_file() or marker.stat().st_nlink != 1 or marker.stat().st_size > 32768:
        raise ValidationFailure('Unsafe migration recovery marker')
    raw = load_data(marker)
    if (not isinstance(raw, dict) or set(raw) != {'root','staged','backup','phase'} or raw['root'] != root.name
            or raw['phase'] not in {'PREPARED','COMMITTED'}):
        raise ValidationFailure('Invalid migration recovery marker; no repair')
    trees = {}
    for name in (raw['staged'], raw['backup']):
        if not isinstance(name, str) or not name.startswith('.' + root.name + '.ph05110-') or any(x in name for x in ('/','\\','..')):
            raise ValidationFailure('Invalid migration storage name')
        folder = root.parent / name
        ensure_native_path(folder, tree=True)
        trees[name] = {p.relative_to(folder).as_posix(): sha256_file(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    ensure_native_path(root, tree=True)
    return {'marker_digest': 'sha256:' + sha256_file(marker), 'phase': raw['phase'],
            'root_present': root.is_dir(), 'storage_hashes': trees,
            'root_hashes': {p.relative_to(root).as_posix(): sha256_file(p) for p in sorted(root.rglob('*')) if p.is_file()}}


def assert_migration_manual(root: Path) -> None:
    """Reject automatic policy before recovery, including an absent live tree."""
    from .migration import _migration_marker
    context = migration_recovery_context(root)
    if context is None: raise ValidationFailure('No pending migration')
    marker = load_data(_migration_marker(root))
    candidates = [root, root.parent / marker['backup'], root.parent / marker['staged']]
    checked = False
    for candidate in candidates:
        if (candidate / '.harness/config/PROJECT_LOCK.yaml').is_file():
            assert_manual(candidate); checked = True
    if not checked: raise ValidationFailure('No verifiable manual migration tree')


def form_schema(name: str) -> dict:
    from .resources import distribution_root
    allowed = {'stage_approval', 'active_stage_plan_review', 'maintenance_plan', 'maintenance_cancel_approval', 'project_input'}
    if name not in allowed:
        raise ValidationFailure('Unknown lifecycle schema')
    return json.loads((distribution_root() / 'schemas' / (name + '.schema.json')).read_text('utf-8'))

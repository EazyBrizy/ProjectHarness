"""Typed lifecycle adapters; app-owned drafts, existing public kernel APIs."""
from __future__ import annotations
from copy import deepcopy
import re
from pathlib import Path
from .errors import ValidationFailure, HarnessError
from .operation_guard import project_operation_guard
from .serialization import load_data, write_data
from .platform_fs import ensure_native_path
from .util import utc_now
from . import lifecycle_forms as forms

PREPARE = {'prepare-stage-approval': 'accept-stage', 'prepare-active-stage-plan': 'plan-active-stage',
           'prepare-level-up': 'level-up', 'prepare-maintenance': 'start-maintenance',
           'prepare-maintenance-cancel': 'cancel-maintenance', 'prepare-migration': 'migrate-project'}
APPLY = set(PREPARE.values())
ACTIONS = {**{k: {'kind': 'project', 'fields': frozenset(), 'id': 'LW-LIFECYCLE'} for k in PREPARE},
           **{k: {'kind': 'project', 'fields': frozenset({'draft_id', 'document', 'actor', 'confirmed', 'rationale'}), 'id': 'LW-LIFECYCLE'} for k in APPLY},
           'resume-stage-gate': {'kind': 'project', 'fields': frozenset({'confirmed'}), 'id': 'LW-C20'},
           'recover-migration': {'kind': 'migration', 'fields': frozenset({'confirmed'}), 'id': 'LW-C07'},
           'assess-maturity': {'kind': 'workspace', 'fields': frozenset({'confirmed'}), 'id': 'LW-C21'}}
SCHEMAS = {'accept-stage': 'stage_approval', 'plan-active-stage': 'active_stage_plan_review',
           'start-maintenance': 'maintenance_plan', 'cancel-maintenance': 'maintenance_cancel_approval'}


def compatible(action, kind):
    if action in {'prepare-migration', 'migrate-project', 'recover-migration'}: return kind in {'project', 'migration'}
    if action == 'assess-maturity': return kind in {'project', 'workspace'}
    return kind == 'project'


def view(service, project_id):
    root, kind = service._registered(project_id)
    with project_operation_guard(root):
        result = {'project_id': project_id, 'kind': kind, 'fingerprint': service.core_fingerprint(root, kind)}
        if kind != 'workspace' and forms.migration_recovery_context(root):
            result['migration'] = forms.migration_preview(root)
        elif kind == 'workspace':
            result.update(forms.assessment_overview(root))
        elif kind == 'migration':
            result['migration'] = forms.migration_preview(root)
        else:
            result.update(forms.lifecycle_overview(root))
        result['automatic_executor'] = 'DISABLED'
        return result


def directory(service, opid):
    service._path(opid)  # strict opaque ID validation
    path = service.app_data / 'artifacts' / opid
    ensure_native_path(path, tree=True)
    return path


def read_draft(service, project_id, opid):
    op = service.get_operation(project_id, opid)
    if op['action'] not in PREPARE or op['state'] != 'SUCCEEDED':
        raise ValidationFailure('Lifecycle draft is not a completed owned preparation')
    path = directory(service, opid) / 'form.json'
    if not path.is_file() or path.stat().st_nlink != 1 or path.stat().st_size > 512 * 1024:
        raise ValidationFailure('Lifecycle draft unavailable')
    value = load_data(path)
    if value.get('project_id') != project_id or value.get('digest') != service._hash({k: v for k, v in value.items() if k != 'digest'}):
        raise ValidationFailure('Lifecycle draft integrity failure')
    schema = forms.form_schema(SCHEMAS[value['action']]) if value['action'] in SCHEMAS else None
    if value['action'] == 'migrate-project':
        input_schema = forms.form_schema('project_input')
        schema = {'type': 'object', '$defs': input_schema['$defs'], 'properties': {'migration': {'type': 'object',
                  'properties': {'input_document': input_schema}}}}
    return {**value, 'schema': schema}


def prepare(service, project_id, opid, action):
    from .stages import prepare_stage_approval, load_stage_state
    from .active_stage_planning import prepare_active_stage_plan
    root, kind = service._registered(project_id)
    if action != 'prepare-migration': forms.assert_manual(root)
    path = directory(service, opid); path.mkdir(exist_ok=False, mode=0o700)
    suffix = opid.removeprefix('LWO-')
    output = path / 'draft.json'
    if action == 'prepare-stage-approval':
        prepare_stage_approval(root, output); document = load_data(output)
    elif action == 'prepare-active-stage-plan':
        prepare_active_stage_plan(root, output); document = load_data(output)
    elif action == 'prepare-maintenance': document = forms.maintenance_draft(root, suffix=suffix)
    elif action == 'prepare-maintenance-cancel': document = forms.maintenance_cancel_draft(root, suffix=suffix)
    elif action == 'prepare-level-up':
        stage = load_stage_state(root)
        document = {'level_up_approval': {'id': 'DEC-LW-LEVEL-' + suffix, 'approved': False, 'actor': None,
            'approved_at': None, 'target_level': stage['target_level']}}
    elif action == 'prepare-migration': document = {'migration': forms.migration_preview(root)}
    else: raise ValidationFailure('Unknown lifecycle preparation')
    value = {'project_id': project_id, 'draft_id': opid, 'action': PREPARE[action],
             'fingerprint': service.core_fingerprint(root, kind), 'document': document}
    value['digest'] = service._hash(value)
    write_data(path / 'form.json', value)
    return {'status': 'DRAFT_PREPARED', 'draft_id': opid, 'action': value['action']}


def sign_document(action, document, original, actor, *, suffix, timestamp, rationale):
    if not isinstance(actor, str) or not re.fullmatch(r'ACT-[A-Z0-9](?:[A-Z0-9._:-]*[A-Z0-9])?', actor) or len(actor) > 160:
        raise ValidationFailure('Formal actor must be an ACT reference (up to 160 characters)')
    if not isinstance(document, dict) or set(document) != set(original):
        raise ValidationFailure('Lifecycle document envelope mismatch')
    value = deepcopy(document); key = next(iter(original)); body = value[key]; old = original[key]
    if not isinstance(body, dict): raise ValidationFailure('Lifecycle document must be an object')
    # Exact server-prepared context is never editable, including by advanced import.
    editable = {
        'accept-stage': {'outcome_results', 'criteria_results', 'hard_constraint_results', 'profile_control_results',
                         'evidence_refs', 'known_limitations', 'next_stage_gaps', 'notes', 'permitted_use'},
        'plan-active-stage': {'work_packages', 'review'},
        'start-maintenance': {'objective', 'rationale', 'work_package'},
        'cancel-maintenance': {'rationale'}, 'level-up': {'target_level'},
    }[action]
    if set(body) != set(old) or any(body[k] != old[k] for k in old if k not in editable):
        raise ValidationFailure('Exact lifecycle context or formal fields changed; prepare a new draft')
    formal = {'approved': True, 'actor': actor, 'approved_at': timestamp}
    if action == 'accept-stage':
        body.update(formal, id='DEC-LW-STAGE-' + suffix, record_state='APPROVED')
        from .stage_approvals import validate_stage_approval_document
        validate_stage_approval_document(value)
    elif action == 'plan-active-stage':
        # Unedited work requires review, but no invented formal Decision.
        # Changed work must use the existing exact planning Decision contract.
        if body['review'] != old['review']:
            raise ValidationFailure('Review binding is server-owned; scope changes need separate governance')
        if body['work_packages'] != old['work_packages']:
            if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 4000:
                raise ValidationFailure('Edited plan needs an explicit review rationale')
            body['review']['decision'] = {'id': f"DEC-{body['id'].removeprefix('RQP-')}-REVIEW",
                'kind': 'ACTIVE_STAGE_PLAN_REVIEW', 'rationale': rationale, **formal}
        from .active_stage_planning import validate_active_stage_plan_document
        validate_active_stage_plan_document(value)
    elif action == 'start-maintenance':
        body['status'] = 'APPROVED'; body['decision'].update(formal)
        from .maintenance import validate_maintenance_plan_document
        validate_maintenance_plan_document(value)
    elif action == 'cancel-maintenance':
        body.update(formal)
        from .maintenance import validate_maintenance_cancel_document
        validate_maintenance_cancel_document(value)
    else:
        if body['target_level'] not in forms.canonical_levels(): raise ValidationFailure('Unknown level-up target')
        body.update(formal)
    return value


def execute(service, project_id, opid, action, payload):
    root, kind = service._registered(project_id)
    if not compatible(action, kind) or set(payload) != ACTIONS[action]['fields']:
        raise ValidationFailure('Lifecycle action/fields invalid')
    if action in PREPARE: return prepare(service, project_id, opid, action)
    if payload.get('confirmed') is not True: raise ValidationFailure('Separate lifecycle confirmation required')
    if action == 'recover-migration':
        if not forms.migration_recovery_context(root): raise ValidationFailure('No pending migration recovery')
        forms.assert_migration_manual(root)
        from .migration import migrate_project
        result = migrate_project(root)
        forms.assert_manual(root)
        service.register_existing(root, kind='project')
        return result
    if action not in {'migrate-project'}: forms.assert_manual(root, workspace=kind == 'workspace')
    if action == 'resume-stage-gate':
        from .stage_gate_lifecycle import resume_stage_gate
        return resume_stage_gate(root)
    if action == 'assess-maturity':
        if kind == 'workspace':
            binding = forms.repository_binding(root)
            if not binding or binding['stale']: raise ValidationFailure('STALE_REPOSITORY: refresh the selected source through a new intake')
        from .stages import assess_maturity
        result = assess_maturity(root)
        if kind == 'workspace' and forms.repository_binding(root)['stale']:
            raise ValidationFailure('STALE_REPOSITORY: repository changed during assessment; baseline approval prohibited')
        return result
    draft = read_draft(service, project_id, payload['draft_id'])
    if draft['action'] != action or draft['fingerprint'] != service.core_fingerprint(root, kind):
        raise ValidationFailure('STALE_FINGERPRINT: lifecycle draft changed')
    out = directory(service, opid); out.mkdir(exist_ok=False, mode=0o700)
    if action == 'migrate-project':
        document = payload['document']
        if not isinstance(document, dict) or set(document) != {'migration'} or not isinstance(document['migration'], dict):
            raise ValidationFailure('Migration envelope invalid')
        original = draft['document']['migration']; submitted = document['migration']
        if set(submitted) != set(original) or any(submitted[k] != original[k] for k in original if k != 'input_document'):
            raise ValidationFailure('Migration preview changed')
        preview = forms.migration_preview(root)
        if not preview['supported']: raise ValidationFailure('Unsupported or invalid migration source', preview['validation'])
        forms.assert_manual(root)
        candidate = submitted['input_document']; input_path = None
        if original['input_document'] is None and candidate is not None:
            raise ValidationFailure('This migration cannot replace immutable accepted input')
        if candidate is not None:
            from .project_input import validate_project_input, DEFAULT_EXECUTION_POLICY
            readiness = validate_project_input(candidate, require_approvals=True)
            if readiness['status'] != 'READY_FOR_HANDOFF' or candidate.get('execution') != DEFAULT_EXECUTION_POLICY:
                raise ValidationFailure('Migration needs exact approved MANUAL_HANDOFF input', readiness)
            input_path = out / 'migration-input.json'; write_data(input_path, candidate)
        from .migration import migrate_project
        result = migrate_project(root, input_path=input_path)
        service.register_existing(root, kind='project')
        return result
    document = sign_document(action, payload['document'], draft['document'], payload['actor'],
                             suffix=payload['draft_id'].removeprefix('LWO-'), timestamp=utc_now(), rationale=payload['rationale'])
    record = out / 'reviewed.json'; write_data(record, document)
    write_data(out / 'review-binding.json', {'project_id': project_id, 'action': action,
        'document_digest': service._hash(document)})
    from .stages import accept_stage, level_up
    from .active_stage_planning import plan_active_stage
    from .maintenance import start_maintenance, cancel_maintenance
    if action == 'accept-stage': return accept_stage(root, document['stage_approval']['level'], record)
    if action == 'plan-active-stage': return plan_active_stage(root, record)
    if action == 'level-up': return level_up(root, document['level_up_approval']['target_level'], record)
    if action == 'start-maintenance': return start_maintenance(root, record)
    if action == 'cancel-maintenance': return cancel_maintenance(root, record)
    raise ValidationFailure('Unknown lifecycle action')


def reconcile(service, project_id, operation):
    """Resolve only an exact committed kernel transaction; never replay a command."""
    from .stage_transactions import committed_stage_transaction_result, digest_value as stage_transaction_digest
    root, _ = service._registered(project_id)
    action = operation['action']; path = directory(service, operation['operation_id'])
    if not (path / 'review-binding.json').is_file(): return None
    binding = load_data(path / 'review-binding.json'); document = load_data(path / 'reviewed.json')
    if binding != {'project_id': project_id, 'action': action, 'document_digest': service._hash(document)}:
        raise ValidationFailure('Lifecycle reviewed document integrity failure')
    body = next(iter(document.values()))
    if action in {'accept-stage', 'level-up'}:
        kind = 'ACCEPT_STAGE' if action == 'accept-stage' else 'LEVEL_UP'
        key = 'level' if action == 'accept-stage' else 'target_level'
        tid = "STX-" + body['id'].removeprefix('DEC-')
        digest = stage_transaction_digest({'operation_kind': kind, key: body[key], 'approval': body})
    elif action == 'plan-active-stage':
        from .active_stage_planning import digest_value
        kind = 'PLAN_ACTIVE_STAGE'; tid = 'STX-PLAN-' + body['id'].removeprefix('RQP-'); digest = digest_value(document)
    elif action in {'start-maintenance','cancel-maintenance'}:
        kind = 'START_MAINTENANCE' if action == 'start-maintenance' else 'CANCEL_MAINTENANCE'
        decision = body['decision']['id'] if action == 'start-maintenance' else body['id']
        tid = 'STX-' + decision.removeprefix('DEC-'); digest = stage_transaction_digest(document)
    else: return None
    result = committed_stage_transaction_result(root, transaction_id=tid, operation_kind=kind, request_digest=digest)
    return {'core_status': result.get('status', 'COMMITTED'), 'lifecycle': result} if result else None

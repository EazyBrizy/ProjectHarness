"""Public provisional approval API; PROJECT_INPUT@4 and Stage contracts unchanged.

The caller supplies a server-created companion intent, after validating its
source/review binding under the operation guard. Only this API writes input.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path

from .errors import ValidationFailure
from .local_web_drafts import draft_input_digest
from .local_web_exchange_contract import digest, bytes_digest
from .operation_guard import guarded_mutation
from .platform_fs import ensure_native_path
from .project_input import approvals_for_mode, project_input_schema_issues, validate_project_input, DEFAULT_EXECUTION_POLICY
from .serialization import load_data, pretty_json, write_data


def approval_candidate(workspace: Path, *, subject: str, decision: str, actor: str,
                       timestamp: str, comment: str, expected_input_digest: str) -> dict:
    """Read-only validation and deterministic single-file proposal."""
    ensure_native_path(workspace, tree=True)
    if draft_input_digest(workspace) != expected_input_digest:
        raise ValidationFailure('STALE_FINGERPRINT: approval input changed')
    value = load_data(workspace / 'PROJECT_INPUT.yaml')
    if value.get('execution') != DEFAULT_EXECUTION_POLICY:
        raise ValidationFailure('MANUAL_ONLY')
    if project_input_schema_issues(value, relaxed=True):
        raise ValidationFailure('APPROVAL_INPUT_SCHEMA_INVALID')
    order = approvals_for_mode(value['project']['mode'])
    if (not isinstance(decision, str) or decision not in {'APPROVE', 'REWORK', 'INVALIDATE'}
            or not isinstance(subject, str) or subject not in order):
        raise ValidationFailure('APPROVAL_SUBJECT_INVALID')
    if (not isinstance(actor, str) or not actor.strip() or len(actor) > 120
            or any(ord(c) < 32 or ord(c) == 127 for c in actor)
            or not isinstance(comment, str) or len(comment) > 2000
            or (decision == 'REWORK' and not comment.strip())):
        raise ValidationFailure('APPROVAL_FIELDS_INVALID')
    try:
        if not timestamp.endswith('Z') or datetime.fromisoformat(timestamp).tzinfo is None:
            raise ValueError()
    except (AttributeError, ValueError):
        raise ValidationFailure('APPROVAL_TIMESTAMP_INVALID') from None
    candidate = deepcopy(value)
    reset = []
    if decision == 'APPROVE':
        ready = validate_project_input(value, require_approvals=False)
        if ready['status'] != 'READY_FOR_HANDOFF':
            raise ValidationFailure('APPROVAL_SUBJECT_INCOMPLETE', ready)
        index = order.index(subject)
        if (value['approvals'][subject]['approved'] or
                any(not value['approvals'][key]['approved'] for key in order[:index]) or
                any(value['approvals'][key]['approved'] for key in order[index+1:])):
            raise ValidationFailure('APPROVAL_SEQUENCE_INVALID')
        candidate['approvals'][subject] = {'approved': True, 'actor': actor,
            'approved_at': timestamp, 'notes': comment or None}
    else:
        # Rework invalidates this decision and its dependent later decisions,
        # never earlier independent confirmations or accepted Project history.
        reset = order if decision == 'INVALIDATE' else order[order.index(subject):]
        for key in reset:
            candidate['approvals'][key] = {'approved': False, 'actor': None,
                'approved_at': None, 'notes': comment if key == subject else None}
    if project_input_schema_issues(candidate, relaxed=True):
        raise ValidationFailure('APPROVAL_RESULT_SCHEMA_INVALID')
    return {'candidate': candidate, 'before_digest': expected_input_digest,
        'after_digest': bytes_digest(pretty_json(candidate).encode('utf-8')),
        'reset_subjects': [key for key in reset if value['approvals'][key]['approved']]}


@guarded_mutation
def apply_provisional_approval(workspace: Path, intent: dict) -> dict:
    """Verify exact companion intent before writing actual schema fields.

    Receipt hashes are audit consistency checks, not signatures or identity.
    The HTTP/service layer does not write canonical input itself.
    """
    if intent.get('version') != 1 or intent.get('intent_digest') != digest(
            {k: v for k, v in intent.items() if k != 'intent_digest'}):
        raise ValidationFailure('APPROVAL_RECEIPT_INVALID')
    proposal = approval_candidate(workspace, subject=intent['subject'], decision=intent['decision'],
        actor=intent['actor'], timestamp=intent['timestamp'], comment=intent['comment'],
        expected_input_digest=intent['binding']['input_revision'])
    if proposal['after_digest'] != intent['after_digest']:
        raise ValidationFailure('APPROVAL_RECEIPT_MISMATCH')
    write_data(workspace / 'PROJECT_INPUT.yaml', proposal['candidate'])
    if draft_input_digest(workspace) != intent['after_digest']:
        raise ValidationFailure('APPROVAL_WRITE_INTEGRITY_FAILED')
    return {k: v for k, v in proposal.items() if k != 'candidate'}

"""Exact-bound, immutable operator review of Task manual checks (PH-LW-09).

This is Task evidence only: no Stage mappings, approvals or agent assertions.
"""
from __future__ import annotations
import json
from pathlib import Path
from .errors import ValidationFailure
from .operation_guard import guarded_mutation, project_operation_guard
from .serialization import canonical_json_bytes, write_data
from .workspace import snapshot_product, record_phase_boundary, scan_protected_control_plane
from .evidence import normalized_evidence_body, write_normalized_evidence
from .util import utc_now

MAX_BYTES = 256 * 1024


def parse_document(raw: bytes) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES:
        raise ValidationFailure('MANUAL_EVIDENCE_INVALID: limit 256 KiB')
    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj: raise ValueError('duplicate key')
            obj[k] = v
        return obj
    def constant(v): raise ValueError('nonfinite constant')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ValidationFailure('MANUAL_EVIDENCE_INVALID: strict JSON') from exc
    if not isinstance(value, dict): raise ValidationFailure('MANUAL_EVIDENCE_INVALID: object required')
    return value


def _context(root, active):
    from . import manual_tasks as tasks
    plan = tasks._plan(root, active)
    checks = plan['manual_checks']
    if len(checks) > 100 or any(not isinstance(x, str) or not 0 < len(x) <= 4000 for x in checks):
        raise ValidationFailure('MANUAL_EVIDENCE_INVALID: check budget')
    return {'schema_version': 1, 'record_kind': 'TASK_MANUAL_EVIDENCE',
        'task_ref': active['task_ref'], 'run_ref': active['run_ref'],
        'binding_digest': tasks.digest(tasks._binding(root, active)), 'plan_digest': plan['digest'],
        'checks': checks}


def manual_evidence_context(root: Path) -> dict:
    from . import manual_tasks as tasks
    with project_operation_guard(root):
        active = tasks._active(root)
        context = _context(root, active)
        return {'binding': context, 'product_files': snapshot_product(root),
            'evidence': evaluate_manual_evidence(root, active)}


def _text(value, label, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or '\x00' in value:
        raise ValidationFailure('MANUAL_EVIDENCE_INVALID: '+label)


def _validate(root, active, document):
    from . import manual_tasks as tasks
    context = _context(root, active)
    fields = {'schema_version','record_kind','task_ref','run_ref','binding_digest','plan_digest','reviewer','checks'}
    if not isinstance(document, dict) or set(document) != fields:
        raise ValidationFailure('MANUAL_EVIDENCE_INVALID: exact fields required')
    if type(document['schema_version']) is not int:
        raise ValidationFailure('MANUAL_EVIDENCE_INVALID: version type')
    if any(document[k] != v for k, v in context.items() if k != 'checks'):
        raise ValidationFailure('MANUAL_EVIDENCE_STALE: exact Task/Run/baseline/plan required')
    task = tasks.runtime._trusted_task(root, active)
    if not context['checks'] or task['verification'].get('allow_manual') is not True:
        raise ValidationFailure('MANUAL_EVIDENCE_DISABLED: no permitted manual checks')
    _text(document['reviewer'], 'reviewer', 200)
    reviews = document['checks']
    if not isinstance(reviews, list) or len(reviews) != len(context['checks']):
        raise ValidationFailure('MANUAL_EVIDENCE_INVALID: every check required')
    product = snapshot_product(root)
    for index, (review, check) in enumerate(zip(reviews, context['checks'])):
        if not isinstance(review, dict) or set(review) != {'index','check','status','observation','sources'}:
            raise ValidationFailure('MANUAL_EVIDENCE_INVALID: check fields')
        if type(review['index']) is not int or review['index'] != index or review['check'] != check:
            raise ValidationFailure('MANUAL_EVIDENCE_INVALID: exact ordered checks required')
        if review['status'] not in ('PASS','FAIL'):
            raise ValidationFailure('MANUAL_EVIDENCE_INVALID: explicit PASS or FAIL required')
        _text(review['observation'], 'observation', 4000)
        sources = review['sources']
        if not isinstance(sources, list) or not 1 <= len(sources) <= 32:
            raise ValidationFailure('MANUAL_EVIDENCE_INVALID: 1..32 inspected product sources required')
        seen = set()
        for source in sources:
            if not isinstance(source, dict) or set(source) != {'path','sha256'} or not isinstance(source['path'], str):
                raise ValidationFailure('MANUAL_EVIDENCE_INVALID: source fields')
            path = source['path']
            if path in seen or path not in product or source['sha256'] != 'sha256:'+product[path]['sha256']:
                raise ValidationFailure('MANUAL_EVIDENCE_STALE: source must match exact product file/digest')
            seen.add(path)
    return context


def _paths(active):
    ref = 'EVD-MANUAL-'+active['run_ref'].removeprefix('RUN-')
    return '.harness/runtime/TASK_MANUAL_EVIDENCE/'+active['run_ref']+'.json', '.harness/evidence/'+ref+'.yaml', ref


@guarded_mutation
def record_manual_evidence(root: Path, document: dict, *, confirmed: bool = False) -> dict:
    from . import manual_tasks as tasks
    if confirmed is not True: raise ValidationFailure('MANUAL_EVIDENCE_CONSENT_REQUIRED')
    # Bound encoding/shape before any canonical write. Reparse detached input.
    try: document = parse_document(canonical_json_bytes(document))
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValidationFailure('MANUAL_EVIDENCE_INVALID') from exc
    active = tasks._active(root)
    _validate(root, active, document)
    relative, evidence_path, ref = _paths(active)
    request_digest = tasks.digest(document)
    if (root/relative).exists():
        existing = tasks._read(root, relative)
        if existing.get('request_digest') != request_digest:
            raise ValidationFailure('MANUAL_EVIDENCE_CHANGED: use block/resume for a new review')
        evaluated = evaluate_manual_evidence(root, active)
        if evaluated['status'] not in ('PASS','FAIL'): raise ValidationFailure('MANUAL_EVIDENCE_STALE')
        return {'status':'MANUAL_EVIDENCE_RECEIVED','evidence_ref':ref,'review_status':evaluated['status']}
    at = utc_now()
    status = 'PASS' if all(x['status']=='PASS' for x in document['checks']) else 'FAIL'
    receipt = {'schema':'TASK_MANUAL_EVIDENCE_RECEIPT_V1','request_digest':request_digest,
        'document':document,'received_at':at,'evidence_ref':ref}
    from .stages import product_baseline_revision
    from .hashing import sha256_file
    protected = scan_protected_control_plane(root, exclude_paths={relative,evidence_path})
    write_data(root/relative, receipt)
    body = normalized_evidence_body(evidence_id=ref, kind='REVIEW_RECORD', status=status,
        provenance={'source_type':'INDEPENDENT_OPERATOR_REVIEW','source_ref':ref,'producer':'PROJECT_HARNESS_TASK_MANUAL_INTAKE','actor':document['reviewer']},
        base_revision=product_baseline_revision(root), criterion_refs=[], outcome_refs=[], profile_control_refs=['RUNTIME_TASK_MANUAL_REVIEW'],
        source_bindings=[{'ref':ref,'path':relative,'sha256':'sha256:'+sha256_file(root/relative)}],
        created_at=at, task_ref=active['task_ref'], run_ref=active['run_ref'], validator=document['reviewer'],
        rationale='Explicit operator observations for every exact Task manual check.',
        details={'task_manual_evidence':document})
    write_normalized_evidence(root, body)
    # Product/control races must never be blessed by the new phase boundary.
    _validate(root, active, document)
    if (scan_protected_control_plane(root, exclude_paths={relative,evidence_path}) != protected or
        tasks._read(root,relative) != receipt or tasks._read(root,evidence_path) != {'verification_evidence':body}):
        raise ValidationFailure('MANUAL_EVIDENCE_CHANGED: publication interrupted; inspect canonical state')
    record_phase_boundary(root, active, phase='TASK_MANUAL_EVIDENCE_RECEIVED',
        kernel_written_paths=[relative,evidence_path], recorded_at=at)
    return {'status':'MANUAL_EVIDENCE_RECEIVED','evidence_ref':ref,'review_status':status}


def evaluate_manual_evidence(root: Path, active: dict) -> dict:
    """Read-only gate evaluation; absence, stale or malformed proof stays BLOCKED."""
    from . import manual_tasks as tasks
    checks = tasks.runtime._trusted_task(root, active).get('verification',{}).get('manual_checks') or []
    if not checks: return {'status':'PASS','evidence_ref':None,'reason':'NO_MANUAL_CHECKS'}
    relative, evidence_path, ref = _paths(active)
    if not (root/relative).exists(): return {'status':'BLOCKED','evidence_ref':None,'reason':'MANUAL_EVIDENCE_REQUIRED'}
    try:
        receipt = tasks._read(root,relative)
        if set(receipt) != {'schema','request_digest','document','received_at','evidence_ref'} or receipt['schema'] != 'TASK_MANUAL_EVIDENCE_RECEIPT_V1' or receipt['evidence_ref'] != ref:
            raise ValidationFailure('MANUAL_EVIDENCE_INVALID')
        document = receipt['document']; _validate(root, active, document)
        if tasks.digest(document) != receipt['request_digest']: raise ValidationFailure('MANUAL_EVIDENCE_CHANGED')
        body = tasks._read(root,evidence_path)['verification_evidence']
        from .evidence import validate_normalized_evidence_document
        validate_normalized_evidence_document(root, {'verification_evidence':body})
        from .hashing import sha256_file
        from .stages import product_baseline_revision
        status = 'PASS' if all(x['status']=='PASS' for x in document['checks']) else 'FAIL'
        if (body['status'] != status or body['task_ref'] != active['task_ref'] or body['run_ref'] != active['run_ref'] or
            body['base_revision'] != product_baseline_revision(root) or body['validator'] != document['reviewer'] or
            body['provenance'] != {'source_type':'INDEPENDENT_OPERATOR_REVIEW','source_ref':ref,'producer':'PROJECT_HARNESS_TASK_MANUAL_INTAKE','actor':document['reviewer']} or
            body['details'] != {'task_manual_evidence':document} or body['kind'] != 'REVIEW_RECORD' or
            body['source_bindings'] != [{'ref':ref,'path':relative,'sha256':'sha256:'+sha256_file(root/relative)}] or
            any(body[k] for k in ('criterion_refs','outcome_refs')) or body['profile_control_refs'] != ['RUNTIME_TASK_MANUAL_REVIEW']):
            raise ValidationFailure('MANUAL_EVIDENCE_CHANGED')
        return {'status':status,'evidence_ref':ref,'reviewer':document['reviewer'],'checks':document['checks']}
    except (ValidationFailure, KeyError, TypeError, ValueError, OSError) as exc:
        return {'status':'BLOCKED','evidence_ref':ref,'reason':str(exc)}

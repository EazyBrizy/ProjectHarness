"""PH-LW-05: bounded application-service operations for source provenance.

These helpers are bound to LocalWebService by explicit forwarding methods, not
through the generic operation dispatcher. Incoming HTTP payloads never include
filesystem paths, and imports are never recognized as executable instructions.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
from typing import Any, BinaryIO, Iterable

from .errors import ValidationFailure, SafetyViolation
from .intake import start_intake, refresh_intake_sources
from .local_web_drafts import draft_input_digest
from .local_web_imports import (build_snapshot, source_state, read_preview, _private_directory,
                                _snapshot, _active_state)
from .local_web_source_refresh import pending_refresh, recover_source_refresh
from .operation_guard import project_operation_guard
from .platform_fs import ensure_native_path, _native_io_path
from .serialization import load_data, write_data, canonical_json_bytes
from .util import utc_now

_NAME = re.compile(r'^[^\x00-\x1f\x7f]{1,120}$')
_IDEMPOTENCY = re.compile(r'^[a-zA-Z0-9_.:-]{16,160}$')


def _managed(service: Any, root: Path, kind: str) -> Path:
    if kind != 'workspace':
        raise ValidationFailure('SOURCE_IMPORT_AFTER_PREPARATION_UNSUPPORTED')
    managed_root = service.app_data.parent / (service.app_data.name + '-workspaces')
    if (root.name != 'intake' or root.parent.parent != managed_root or
            not root.parent.name.startswith('session-') or root.is_symlink() or
            root.parent.is_symlink()):
        raise ValidationFailure('SOURCE_IMPORT_REQUIRES_LOCAL_WEB_WORKSPACE')
    imports = root.parent / 'imports'
    ensure_native_path(imports)
    if imports.is_symlink() or not imports.is_dir():
        raise ValidationFailure('SOURCE_IMPORTS_UNAVAILABLE')
    return imports


def _check_prepared(service: Any, pid: str) -> None:
    from .local_web_exchange import assert_no_pending_exchange
    root, _ = service._registered(pid)
    assert_no_pending_exchange(root)
    from .local_web_preparation import _record_path
    if _record_path(service, pid).exists():
        raise ValidationFailure('SOURCE_REFRESH_AFTER_PREPARE_UNSUPPORTED')
    # A successful prepare is immutable.  Source mutation cannot silently
    # invalidate the previously accepted handoff or the Project Instance.
    for file in (service.app_data / 'operations').glob('LWO-*.json'):
        rec = service._load_op(file.stem)
        if rec['project_id'] == pid and rec['action'] == 'prepare' and rec['state'] in ('RUNNING', 'SUCCEEDED', 'BLOCKED'):
            raise ValidationFailure('SOURCE_REFRESH_AFTER_PREPARE_UNSUPPORTED')


def create_intake(service: Any, *, project_name: str, idempotency_key: str,
                  no_documentation: bool = False) -> dict[str, Any]:
    if (not isinstance(project_name, str) or not _NAME.fullmatch(project_name) or
            not project_name.strip() or '\\' in project_name or '/' in project_name or
            not isinstance(no_documentation, bool) or
            not isinstance(idempotency_key, str) or not _IDEMPOTENCY.fullmatch(idempotency_key)):
        raise ValidationFailure('NEW_INTAKE_FIELDS_INVALID')
    request = {'project_name': project_name.strip(), 'no_documentation': no_documentation}
    request_sha = hashlib.sha256(canonical_json_bytes(request)).hexdigest()
    key = hashlib.sha256(idempotency_key.encode('utf-8')).hexdigest().upper()
    parent = _private_directory(service.app_data.parent / (service.app_data.name + '-workspaces'))
    session = parent / ('session-' + key[:24])
    receipt_dir = _private_directory(service.app_data / 'intake_requests')
    receipt = receipt_dir / (key + '.json')
    with project_operation_guard(service.app_data):
        if receipt.is_file() and not receipt.is_symlink():
            record = load_data(receipt)
            if record.get('request_sha') != request_sha:
                raise ValidationFailure('OPERATION_CONFLICT: intake key reused for different data')
            root, kind = service._registered(record['project_id'])
            _managed(service, root, kind)
            return {'project_id': record['project_id'], 'source_revision':
                    source_state(root.parent / 'imports')['revision'], 'replayed': True}
        if session.exists():
            # Crash-safe resumption only if a completed matching catalog record
            # exists; never force-delete a potentially live provisional input.
            catalog = service._catalog()['projects']
            for project_id, item in catalog.items():
                if item.get('root') == str(session / 'intake') and item.get('kind') == 'workspace':
                    if (session / 'creation_request.json').is_file() and not (session / 'creation_request.json').is_symlink():
                        if load_data(session / 'creation_request.json').get('request_sha') == request_sha:
                            write_data(receipt, {'request_sha': request_sha, 'project_id': project_id})
                            return {'project_id': project_id, 'source_revision':
                                    source_state(session / 'imports')['revision'], 'replayed': True}
            raise ValidationFailure('INCOMPLETE_INTAKE_CREATION_REQUIRES_OPERATOR_REVIEW')
        _private_directory(session)
        try:
            _private_directory(session / 'imports')
            root = session / 'intake'
            start_intake(root, project_name=request['project_name'], mode='GREENFIELD', sources=(), force=False)
            if no_documentation:
                refresh_intake_sources(root, snapshot_ref=None, expected_revision=0,
                                      expected_input_digest=draft_input_digest(root),
                                      explicit_no_documentation=True)
            write_data(session / 'creation_request.json', {'request_sha': request_sha})
            project_id = service.register_existing(root, kind='workspace')
            write_data(receipt, {'request_sha': request_sha, 'project_id': project_id})
        except BaseException:
            # This deterministic workspace is not registered until successful
            # start_intake. Keep it for operator diagnosis if registration itself
            # committed before a fault; never erase an unknown committed project.
            if not any(item.get('root') == str(session / 'intake')
                       for item in service._catalog()['projects'].values()):
                shutil.rmtree(session)
            raise
    return {'project_id': project_id, 'source_revision': 1 if no_documentation else 0,
            'replayed': False, 'status': 'DOCUMENTATION_NONE_CONFIRMED' if no_documentation else 'AWAITING_DOCUMENTS'}


def upload_sources(service: Any, pid: str, uploads: Iterable[tuple[str, BinaryIO]], *,
                   mode: str, expected_fingerprint: str, expected_source_revision: int) -> dict[str, Any]:
    root, kind = service._registered(pid)
    imports_root = _managed(service, root, kind)
    with project_operation_guard(root):
        if pending_refresh(root):
            raise ValidationFailure('SOURCE_RECOVERY_REQUIRED')
        if service.core_fingerprint(root, kind) != expected_fingerprint:
            raise ValidationFailure('STALE_FINGERPRINT: refresh status and retry')
        state = source_state(imports_root)
        if type(expected_source_revision) is not int or state['revision'] != expected_source_revision:
            raise ValidationFailure('STALE_SOURCE_REVISION')
        _check_prepared(service, pid)
        incoming = build_snapshot(imports_root, uploads, mode=mode, expected_revision=state['revision'])
        if incoming['unchanged']:
            return {'status': 'UNCHANGED', 'project_id': pid, 'source_revision': state['revision'],
                    'snapshot_ref': state['active_snapshot'], 'accepted_count': 0,
                    'skipped_count': len(incoming['skipped']), 'rejected_count': 0,
                    'accepted': [], 'skipped': incoming['skipped'], 'analysis_status': 'NOT_ANALYZED'}
        try:
            outcome = refresh_intake_sources(root, snapshot_ref=incoming['snapshot_ref'],
                    expected_revision=state['revision'], expected_input_digest=draft_input_digest(root))
        except BaseException:
            # Newly validated but *unpublished-to-workspace* snapshot is
            # disposable; a still-pending transaction must retain it.
            if not pending_refresh(root) and _active_state(imports_root)['active_snapshot'] != incoming['snapshot_ref']:
                directory = imports_root / 'snapshots' / incoming['snapshot_ref']
                if _native_io_path(directory).is_dir() and not _native_io_path(directory).is_symlink():
                    shutil.rmtree(_native_io_path(directory))
            raise
        return {'status': outcome['status'], 'project_id': pid,
                'source_revision': outcome['source_revision'], 'snapshot_ref': incoming['snapshot_ref'],
                'accepted_count': len(incoming['accepted']), 'skipped_count': len(incoming['skipped']),
                'rejected_count': 0, 'accepted': incoming['accepted'], 'skipped': incoming['skipped'],
                'analysis_status': 'NOT_ANALYZED'}


def select_no_documentation(service: Any, pid: str, *, expected_fingerprint: str,
                             expected_source_revision: int) -> dict[str, Any]:
    root, kind = service._registered(pid)
    imports_root = _managed(service, root, kind)
    with project_operation_guard(root):
        if pending_refresh(root):
            raise ValidationFailure('SOURCE_RECOVERY_REQUIRED')
        if service.core_fingerprint(root, kind) != expected_fingerprint:
            raise ValidationFailure('STALE_FINGERPRINT')
        state = source_state(imports_root)
        if type(expected_source_revision) is not int or state['revision'] != expected_source_revision:
            raise ValidationFailure('STALE_SOURCE_REVISION')
        _check_prepared(service, pid)
        if state['documentation_choice'] == 'NONE':
            return {'status': 'UNCHANGED', 'source_revision': state['revision'], 'analysis_status': 'NOT_ANALYZED'}
        outcome = refresh_intake_sources(root, snapshot_ref=None,
                   expected_revision=state['revision'], expected_input_digest=draft_input_digest(root),
                   explicit_no_documentation=True)
        return {'status': outcome['status'], 'source_revision': outcome['source_revision'],
                'analysis_status': 'NOT_ANALYZED'}


def list_sources(service: Any, pid: str) -> dict[str, Any]:
    root, kind = service._registered(pid)
    imports_root = _managed(service, root, kind)
    with project_operation_guard(root):
        if pending_refresh(root):
            raise ValidationFailure('SOURCE_RECOVERY_REQUIRED')
        state = source_state(imports_root)
        return {'project_id': pid, 'source_revision': state['revision'],
                'snapshot_ref': state.get('active_snapshot'),
                'documentation_choice': state.get('documentation_choice'),
                'analysis_status': 'NOT_ANALYZED', 'sources': state['sources'],
                'documents': state['documents'], 'skipped': state['skipped']}


def preview(service: Any, pid: str, doc_ref: str) -> dict[str, Any]:
    root, kind = service._registered(pid)
    imports_root = _managed(service, root, kind)
    with project_operation_guard(root):
        if pending_refresh(root):
            raise ValidationFailure('SOURCE_RECOVERY_REQUIRED')
        return read_preview(imports_root, doc_ref)


def recover(service: Any, pid: str) -> dict[str, Any]:
    root, kind = service._registered(pid)
    _managed(service, root, kind)
    with project_operation_guard(root):
        return recover_source_refresh(root)

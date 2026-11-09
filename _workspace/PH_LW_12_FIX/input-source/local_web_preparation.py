"""PH-LW-08 preparation orchestration; companion records are not core states."""
from __future__ import annotations

from importlib import resources
import json
import os
from pathlib import Path
import re
import time
from secrets import token_hex

from .compiler import prepare_handoff
from .errors import ValidationFailure
from .hashing import sha256_file
from .local_web_approvals import review as approval_review, _sources
from .local_web_exchange import _load, assert_no_pending_exchange
from .local_web_exchange_contract import digest, KEY
from .materialization import (check_new_destination, directory_identity, inspect_initial_handoff,
                              publish_project_directory, verify_published_project, handoff_tree_digest)
from .operation_guard import project_operation_guard
from .platform_fs import ensure_native_path, safe_relative, _native_io_path
from .project_input import DEFAULT_EXECUTION_POLICY
from .serialization import load_data, write_data
from .util import utc_now

TARGET = re.compile(r'^LWT-[A-F0-9]{32}$')


def _write_record(path, record):
    """Bounded retry of atomic journal replacement, never of a core operation.

    Windows Python read handles briefly deny delete sharing during GET polling.
    A persistent lock/access failure still propagates for explicit recovery.
    """
    for attempt in range(11):
        try:
            write_data(path, record)
            return
        except PermissionError as exc:
            if os.name != 'nt' or exc.winerror not in {5, 32, 33} or attempt == 10:
                raise
            time.sleep(0.05)


def _save(path, record):
    record = {k: v for k, v in record.items() if k != 'record_digest'}
    _write_record(path, {**record, 'record_digest': digest(record)})


def _checkpoint(name):
    """Fault-injection seam, inert in production (no environment switch)."""


def _store(service):
    path = service.app_data / 'preparations'
    ensure_native_path(path, tree=True)
    return path


def _record_path(service, pid):
    service._registered(pid)
    return _store(service) / (pid + '.json')


def _binding(service, pid):
    root, kind = service._registered(pid)
    if kind != 'workspace':
        raise ValidationFailure('PREPARATION_PROVISIONAL_ONLY')
    assert_no_pending_exchange(root)
    review = approval_review(service, pid)
    value = load_data(root / 'PROJECT_INPUT.yaml')
    if (value.get('execution') != DEFAULT_EXECUTION_POLICY or
            review['readiness']['status'] != 'READY_FOR_HANDOFF' or review['recovery_required'] or
            review['unbound_approvals'] or not all(row['approved'] for row in review['subjects']) or
            not review['subject_complete']):
        raise ValidationFailure('PREPARATION_APPROVALS_REQUIRED: нужны все актуальные отдельные согласования')
    metadata = json.loads(resources.files('project_harness').joinpath('resources/local_web/metadata_v1.json').read_text('utf-8'))
    return {'workspace': str(root), 'input_revision': review['binding']['input_revision'],
            'sources': _sources(root), 'approval_revision': digest([review['actor'], review['subjects']]),
            'receipts': [r['receipt_id'] for r in review['subjects']],
            'engine_build_digest': metadata['engine_build_digest'],
            'local_web_build_id': metadata['local_web_build_id']}


def _assert_binding(service, pid, binding):
    if _binding(service, pid) != binding:
        raise ValidationFailure('STALE_PREPARATION: input, sources, approvals или engine build изменились')


def _excluded(service):
    from .resources import distribution_root
    roots = [service.app_data, service.app_data.parent / (service.app_data.name + '-workspaces')]
    roots += [Path(item['root']) for item in service._catalog()['projects'].values()]
    roots.append(Path(__file__).resolve().parent)
    roots.append(distribution_root())
    return tuple(roots)


def _target(service, pid, target_id):
    if not isinstance(target_id, str) or not TARGET.fullmatch(target_id):
        raise ValidationFailure('TARGET_INVALID')
    target = _load(_store(service) / (target_id + '.json'))
    if target['project_id'] != pid:
        raise ValidationFailure('TARGET_OWNERSHIP: папка принадлежит другой intake session')
    if Path(target['destination']).parent != service.projects_directory:
        raise ValidationFailure('TARGET_ROOT_CHANGED: подтвердите текущий корень проектов')
    if directory_identity(service.projects_directory) != target['parent_identity']:
        raise ValidationFailure('TARGET_PARENT_CHANGED')
    return target


def get_preparation(service, pid):
    """Read-only reconnect. Never compile, validate, rename or register on GET."""
    root, kind = service._registered(pid)
    if kind != 'workspace':
        raise ValidationFailure('PREPARATION_PROVISIONAL_ONLY')
    record_path = _record_path(service, pid)
    # Atomic companion snapshots remain readable while the worker holds the
    # canonical mutation fence. No inference/validation from partial core files.
    if record_path.exists():
        record = _load(record_path)
        op = service.get_operation(pid, record['operation_id'])
        return {'project_id': pid, 'phase': record['phase'], 'operation_id': record['operation_id'],
                'operation_state': op['state'], 'destination': record['destination'],
                'result': record.get('result'), 'error': op.get('error'),
                'next_action': 'OPEN_PROJECT' if record.get('result') and op['state'] == 'SUCCEEDED' else 'RECOVER_PREPARATION'}
    with project_operation_guard(root):
        try:
            binding = _binding(service, pid)
            ready, reason = True, None
        except ValidationFailure as exc:
            binding, ready, reason = None, False, exc.message
        return {'project_id': pid, 'phase': 'NOT_STARTED', 'ready': ready, 'reason': reason,
                'parent_directory': str(service.projects_directory),
                'binding_digest': digest(binding) if binding else None,
                'expected_fingerprint': service.core_fingerprint(root, kind),
                'next_action': 'CONFIRM_NEW_DIRECTORY' if ready else 'COMPLETE_APPROVALS'}


def confirm_target(service, pid, *, folder_name, binding_digest, expected_fingerprint, confirm):
    """Bounded folder name under trusted local root; no raw HTTP path gateway."""
    if (confirm is not True or not isinstance(folder_name, str) or not 1 <= len(folder_name) <= 80
            or folder_name.startswith('.') or '/' in folder_name or '\\' in folder_name):
        raise ValidationFailure('TARGET_INVALID: подтвердите имя новой папки (до 80 символов)')
    safe_relative(folder_name, field='folder_name', windows=True)
    root, kind = service._registered(pid)
    with project_operation_guard(root):
        binding = _binding(service, pid)
        if digest(binding) != binding_digest or service.core_fingerprint(root, kind) != expected_fingerprint:
            raise ValidationFailure('STALE_PREPARATION: перечитайте согласования')
        if _record_path(service, pid).exists():
            raise ValidationFailure('PREPARATION_ALREADY_STARTED: используйте сохранённый результат или восстановление')
        parent = service.projects_directory
        ensure_native_path(parent)
        destination = check_new_destination(parent / folder_name, excluded=_excluded(service))
        # Creation is an explicit POST. Merely reading a proposal creates nothing.
        parent.mkdir(parents=True, exist_ok=True)
        path = _store(service)
        path.mkdir(mode=0o700, exist_ok=True)
        if len(list(path.glob('LWT-*.json'))) >= 256:
            raise ValidationFailure('TARGET_STORAGE_LIMIT')
        target_id = 'LWT-' + digest([pid, str(destination), binding]).split(':')[1][:32].upper()
        record = {'version': 1, 'target_id': target_id, 'project_id': pid, 'destination': str(destination),
                  'parent_identity': directory_identity(parent), 'binding': binding,
                  'expected_fingerprint': expected_fingerprint, 'confirmed_at': utc_now()}
        existing = path / (target_id + '.json')
        if not existing.exists():
            _save(existing, record)
        return {'target_id': target_id, 'destination': str(destination), 'binding_digest': digest(binding),
                'expected_fingerprint': expected_fingerprint}


def submit_preparation(service, pid, *, target_id, binding_digest, expected_fingerprint, idempotency_key):
    from .local_web_service import OperationRequest
    if not isinstance(idempotency_key, str) or not KEY.fullmatch(idempotency_key):
        raise ValidationFailure('IDEMPOTENCY_KEY_INVALID')
    root, _ = service._registered(pid)
    with project_operation_guard(root):
        target = _target(service, pid, target_id)
        _assert_binding(service, pid, target['binding'])
        if digest(target['binding']) != binding_digest or target['expected_fingerprint'] != expected_fingerprint:
            raise ValidationFailure('STALE_PREPARATION')
        request = OperationRequest(pid, 'publish-project', {'target_id': target_id, 'binding_digest': binding_digest},
                                   idempotency_key, expected_fingerprint)
        request_id = service._operation_id(request)
        if service._path(request_id).exists():
            previous = service._load_op(request_id)
            expected = service._hash({'action':request.action,'payload':request.payload,'fingerprint':expected_fingerprint})
            if previous['request_digest'] != expected:
                raise ValidationFailure('OPERATION_CONFLICT: idempotency key относится к другому запросу')
        path = _record_path(service, pid)
        if path.exists():
            record = _load(path)
            if record['target_id'] != target_id or record['binding'] != target['binding']:
                raise ValidationFailure('PREPARATION_REPLAY_CONFLICT: другой input или destination')
            if record.get('result'):
                verify_published_project(Path(record['destination']), record['initial'])
                read_preparation_artifact(service, pid, record['operation_id'])
            return service.get_operation(pid, record['operation_id'])
        check_new_destination(Path(target['destination']), excluded=_excluded(service))
    return service.submit(request)


def execute_preparation(service, pid, opid, payload):
    """Worker holds the shared workspace fence. Only public core APIs mutate it."""
    target = _target(service, pid, payload['target_id'])
    _assert_binding(service, pid, target['binding'])
    if digest(target['binding']) != payload['binding_digest']:
        raise ValidationFailure('STALE_PREPARATION')
    path = _record_path(service, pid)
    if path.exists():
        prior = _load(path)
        if prior['target_id'] != target['target_id'] or prior['binding'] != target['binding']:
            raise ValidationFailure('PREPARATION_REPLAY_CONFLICT')
        if prior.get('result'):
            verify_published_project(Path(prior['destination']), prior['initial'])
            read_preparation_artifact(service, pid, prior['operation_id'])
            return prior['result']
        raise ValidationFailure('PREPARATION_RECOVERY_REQUIRED: продолжите сохранённую операцию')
    destination = check_new_destination(Path(target['destination']), excluded=_excluded(service))
    stage = destination.parent / ('.harness-preparation-' + token_hex(16))
    record = {'version': 1, 'project_id': pid, 'operation_id': opid, 'target_id': target['target_id'],
              'binding': target['binding'], 'destination': str(destination), 'staging': str(stage),
              'phase': 'INTENT', 'created_at': utc_now()}
    _save(path, record)
    return _continue(service, record)


def _continue(service, record):
    pid = record['project_id']
    _target(service, pid, record['target_id'])
    _assert_binding(service, pid, record['binding'])
    path = _record_path(service, pid)
    stage, destination = Path(record['staging']), Path(record['destination'])
    if stage.parent != destination.parent or not re.fullmatch(r'\.harness-preparation-[a-f0-9]{32}', stage.name):
        raise ValidationFailure('STAGING_INVALID')
    ensure_native_path(stage, tree=True)
    directory, archive = stage / 'project', stage / 'handoff.zip'
    if record['phase'] == 'INTENT':
        check_new_destination(destination, excluded=_excluded(service))
        # Unknown staging is never claimed or deleted after a mkdir interruption.
        if stage.exists():
            owner = _load(stage / 'owner.json')
            if (owner['operation_id'] != record['operation_id'] or owner['project_id'] != pid or
                    {p.name for p in stage.iterdir()} != {'owner.json'}):
                raise ValidationFailure('STAGING_OWNERSHIP')
        else:
            stage.mkdir(mode=0o700, exist_ok=False)
            _save(stage / 'owner.json', {'operation_id': record['operation_id'], 'project_id': pid})
        record['phase'] = 'STAGING'
        _save(path, record)
    owner = _load(stage / 'owner.json')
    if owner['operation_id'] != record['operation_id'] or owner['project_id'] != pid:
        raise ValidationFailure('STAGING_OWNERSHIP')
    if record['phase'] == 'STAGING':
        if directory.exists() or archive.exists():
            raise ValidationFailure('OUTPUT_COLLISION: compiler получает только новые staging paths')
        _checkpoint('before_compile')
        _assert_binding(service, pid, record['binding'])
        record['phase'] = 'COMPILING'
        _save(path, record)
        prepare_handoff(Path(record['binding']['workspace']), archive, keep_directory=directory)
        _checkpoint('after_compile')
    if record['phase'] == 'COMPILING':
        if not directory.is_dir() or not archive.is_file():
            raise ValidationFailure('INCOMPLETE_COMPILE: staging сохранён; требуется диагностика, повтор compiler запрещён')
        _checkpoint('before_validation')
        record['initial'] = inspect_initial_handoff(directory, archive)
        _checkpoint('after_validation')
        record['phase'] = 'VALIDATED'
        _save(path, record)
    if record['phase'] in {'VALIDATED', 'PUBLISHING'}:
        _assert_binding(service, pid, record['binding'])
        if directory.exists() and (handoff_tree_digest(directory) != record['initial']['tree_digest'] or
                'sha256:' + sha256_file(archive) != record['initial']['zip_sha256'] or
                directory_identity(directory) != record['initial']['directory_identity']):
            raise ValidationFailure('STAGING_CHANGED')
        if record['phase'] == 'VALIDATED':
            # Check immutable artifacts again before the durable rename intent.
            if (handoff_tree_digest(directory) != record['initial']['tree_digest'] or
                    'sha256:' + sha256_file(archive) != record['initial']['zip_sha256'] or
                    directory_identity(directory) != record['initial']['directory_identity']):
                raise ValidationFailure('STAGING_CHANGED')
            record['phase'] = 'PUBLISHING'
            _save(path, record)
        _checkpoint('before_rename')
        if destination.exists():
            if directory.exists():
                raise ValidationFailure('DESTINATION_EXISTS: чужая папка сохранена')
            verify_published_project(destination, record['initial'])
        else:
            publish_project_directory(directory, destination, identity=record['initial']['directory_identity'])
        _checkpoint('after_rename')
        record['phase'] = 'PUBLISHED'
        _save(path, record)
    if record['phase'] == 'PUBLISHED':
        with project_operation_guard(destination):
            verify_published_project(destination, record['initial'])
            if 'sha256:' + sha256_file(archive) != record['initial']['zip_sha256']:
                raise ValidationFailure('PREPARATION_ARTIFACT_CHANGED')
            _checkpoint('before_catalog')
            registered = service.register_existing(destination, kind='project')
            _checkpoint('after_catalog')
            from .runtime import project_status
            from .stages import stage_status
            current, stage_status_value = project_status(destination), stage_status(destination)
            record['result'] = {'status': 'READY_FOR_CODEX', 'published_project_id': registered,
                'artifact_ref': record['operation_id'], 'destination': str(destination),
                **{k: record['initial'][k] for k in ('zip_sha256', 'first_task_ref', 'first_run_ref', 'initial_validation')},
                'current_validation': 'PASS', 'active_stage': stage_status_value['active_stage'],
                'target_level': stage_status_value['target_level'], 'current_task': current['current_task']}
            record['phase'] = 'COMPLETE'
            _save(path, record)
    _checkpoint('after_result')
    read_preparation_artifact(service, pid, record['operation_id'])
    return record['result']


def recover_preparation(service, pid, *, confirm):
    if confirm is not True:
        raise ValidationFailure('CONFIRM_REQUIRED')
    root, _ = service._registered(pid)
    with project_operation_guard(root):
        record = _load(_record_path(service, pid))
        _assert_binding(service, pid, record['binding'])
        # If compilation died before producing both outputs, an explicit
        # recovery may compile into a NEW owned staging. The partial directory
        # is retained, never passed back to destructive keep_directory.
        stage = Path(record['staging'])
        if record['phase'] == 'COMPILING' and (not (stage / 'project').is_dir() or not (stage / 'handoff.zip').is_file()):
            ensure_native_path(stage, tree=True)
            owner = _load(stage / 'owner.json')
            if owner['project_id'] != pid or owner['operation_id'] != record['operation_id']:
                raise ValidationFailure('STAGING_OWNERSHIP')
            abandoned = record.get('abandoned_staging', [])
            if len(abandoned) >= 3:
                raise ValidationFailure('INCOMPLETE_COMPILE: исчерпаны три явные попытки')
            record['abandoned_staging'] = abandoned + [str(stage)]
            record['staging'] = str(stage.parent / ('.harness-preparation-' + token_hex(16)))
            record['phase'] = 'INTENT'
            _save(_record_path(service, pid), record)
        result = _continue(service, record)
        verify_published_project(Path(record['destination']), record['initial'])
        op = service.get_operation(pid, record['operation_id'])
        op.update(state='SUCCEEDED', phase='RECONCILED_FROM_PUBLICATION', result=result,
                  core_after=service.core_fingerprint(root, 'workspace'), error=None, finished_at=utc_now())
        op['receipt']['core_outcome'] = 'CONFIRMED_COMMITTED'
        service._save_op(op)
        return op


def read_preparation_artifact(service, pid, opid, *, prompt=False):
    record = _load(_record_path(service, pid))
    if record['operation_id'] != opid or record['phase'] != 'COMPLETE':
        raise ValidationFailure('PREPARATION_ARTIFACT_OWNERSHIP')
    if prompt:
        destination = Path(record['destination'])
        if directory_identity(destination) != record['initial']['directory_identity']:
            raise ValidationFailure('PUBLISHED_IDENTITY_CHANGED')
        path = destination / safe_relative(record['initial']['first_prompt'], field='first_prompt', windows=True)
        expected, limit = record['initial']['prompt_sha256'], 1024 * 1024
    else:
        path = Path(record['staging']) / 'handoff.zip'
        expected, limit = record['initial']['zip_sha256'], 128 * 1024 * 1024
    ensure_native_path(path, file_ok=True)
    io_path = _native_io_path(path)
    if io_path.is_symlink() or not io_path.is_file() or io_path.stat().st_nlink != 1 or io_path.stat().st_size > limit:
        raise ValidationFailure('PREPARATION_ARTIFACT_INVALID')
    data = io_path.read_bytes()
    import hashlib
    if len(data) > limit or 'sha256:' + hashlib.sha256(data).hexdigest() != expected:
        raise ValidationFailure('PREPARATION_ARTIFACT_CHANGED')
    return data


def open_prepared_folder(service, pid, *, confirm):
    if confirm is not True:
        raise ValidationFailure('CONFIRM_REQUIRED')
    record = _load(_record_path(service, pid))
    if record['phase'] != 'COMPLETE':
        raise ValidationFailure('PROJECT_NOT_PUBLISHED')
    destination = Path(record['destination'])
    registered, kind = service._registered(record['result']['published_project_id'])
    if registered != destination or kind != 'project' or directory_identity(destination) != record['initial']['directory_identity']:
        raise ValidationFailure('PUBLISHED_IDENTITY_CHANGED')
    if os.name != 'nt':
        raise ValidationFailure('OPEN_FOLDER_PLATFORM_UNSUPPORTED')
    os.startfile(str(registered), 'explore')  # Exact registered directory, no shell command/string interpolation.
    return {'status': 'OPEN_REQUESTED'}

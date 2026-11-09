"""PH-LW-05: governed source refresh for a *provisional* intake workspace.

The imports root is a sibling, not within the intake workspace.  This is a
bounded, recoverable multi-file update; it does not impersonate a Stage
transaction or re-run start_intake(force=True).  GET callers never recover.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import shutil
import stat
import tempfile
from uuid import uuid4
from typing import Any

from .platform_fs import _native_io_path, native_walk
from .errors import SafetyViolation, ValidationFailure
from .hashing import sha256_file
from .inventory import build_source_inventory
from .local_web_imports import _active_state, _private_directory, _snapshot, sources_for_intake, verify_snapshot
from .local_web_drafts import draft_input_digest
from .platform_fs import ensure_native_path
from .project_input import project_input_schema_issues, questions_for, validate_project_input
from .serialization import load_data, pretty_json, atomic_write_text, write_data
from .util import utc_now

_FILES = ('PROJECT_INPUT.yaml', 'SOURCE_INVENTORY.yaml', 'QUESTIONS.yaml',
          'QUESTIONS.md', 'READINESS.json', 'SESSION.yaml', 'STATE.yaml')


def _source_digest(directory: Path) -> str | None:
    if not _native_io_path(directory).exists():
        return None
    if _native_io_path(directory).is_symlink() or not _native_io_path(directory).is_dir():
        raise SafetyViolation('SOURCE_TREE_NOT_DIRECTORY')
    entries = []
    for current, dirs, files in native_walk(directory, followlinks=False):
        rel = Path(current).relative_to(directory)
        for name in sorted(dirs):
            item = Path(current) / name
            if _native_io_path(item).is_symlink() or bool(getattr(_native_io_path(item), 'is_junction', lambda: False)()):
                raise SafetyViolation('SOURCE_TREE_LINK')
            entries.append((str(rel / name).replace('\\', '/'), 'dir'))
        for name in sorted(files):
            item = Path(current) / name
            if _native_io_path(item).is_symlink() or not _native_io_path(item).is_file() or not stat.S_ISREG(_native_io_path(item).stat().st_mode):
                raise SafetyViolation('SOURCE_TREE_SPECIAL_FILE')
            entries.append((str(rel / name).replace('\\', '/'), sha256_file(item)))
    return 'sha256:' + hashlib.sha256(pretty_json(entries).encode('utf-8')).hexdigest()


def _restore_bytes(target: Path, data: bytes) -> None:
    target = _native_io_path(target)
    fd, name = tempfile.mkstemp(prefix='.source-restore-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data); output.flush(); os.fsync(output.fileno())
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)



def _imports(workspace: Path) -> Path:
    workspace = Path(workspace).expanduser()
    ensure_native_path(workspace, tree=True)
    if _native_io_path(workspace).is_symlink() or workspace.name != 'intake':
        raise ValidationFailure('SOURCE_REFRESH_REQUIRES_MANAGED_INTAKE')
    directory = workspace.parent / 'imports'
    if _native_io_path(directory).is_symlink() or not _native_io_path(directory).is_dir() or directory.resolve() == workspace.resolve():
        raise ValidationFailure('SOURCE_IMPORTS_NOT_MANAGED')
    if os.name != 'nt' and _native_io_path(directory).stat().st_mode & 0o077:
        raise SafetyViolation('SOURCE_IMPORTS_NOT_PRIVATE')
    return directory


def pending_refresh(workspace: Path) -> bool:
    imports_root = _imports(workspace)
    marker = imports_root / 'pending.json'
    if _native_io_path(marker).is_symlink():
        raise SafetyViolation('SOURCE_TRANSACTION_SYMLINK')
    return _native_io_path(marker).exists()


def _digest(path: Path) -> str | None:
    if _native_io_path(path).is_symlink():
        raise SafetyViolation('SOURCE_TRANSACTION_SYMLINK')
    return 'sha256:' + sha256_file(path) if _native_io_path(path).is_file() else None


def _remove_tree(path: Path) -> None:
    if _native_io_path(path).exists():
        if _native_io_path(path).is_symlink():
            raise SafetyViolation('SOURCE_TRANSACTION_SYMLINK')
        shutil.rmtree(_native_io_path(path))


def recover_source_refresh(workspace: Path) -> dict[str, Any]:
    """Explicit MUTATING recovery. Must be invoked under project_operation_guard.

    After a crash, either the entire verified new state is kept, or old
    canonical bytes and old sources are restored from immutable transaction
    backups.  A damaged recovery journal fails closed (no guessed success).
    """
    workspace = Path(workspace).resolve(strict=True)
    imports_root = _imports(workspace)
    marker = imports_root / 'pending.json'
    if not _native_io_path(marker).exists():
        return {'status': 'CLEAN'}
    if _native_io_path(marker).is_symlink():
        raise SafetyViolation('SOURCE_TRANSACTION_SYMLINK')
    rec = load_data(marker)
    if (not isinstance(rec, dict) or set(rec) != {'version', 'id', 'old', 'new', 'source_old', 'source_new', 'ledger_old', 'ledger_new', 'old_source_digest', 'new_source_digest'}
            or rec['version'] != 1 or not isinstance(rec['id'], str)
            or not rec['id'].startswith('TX-') or len(rec['id']) != 35
            or set(rec['old']) != set(_FILES) or set(rec['new']) != set(_FILES)):
        raise ValidationFailure('SOURCE_TRANSACTION_JOURNAL_INVALID')
    txn = imports_root / 'transactions' / rec['id']
    if _native_io_path(txn).is_symlink() or not _native_io_path(txn).is_dir():
        raise ValidationFailure('SOURCE_TRANSACTION_BACKUPS_MISSING')
    for name in _FILES:
        if rec['old'][name] is not None and _digest(txn / 'old' / name) != rec['old'][name]:
            raise ValidationFailure('SOURCE_TRANSACTION_BACKUP_CORRUPT')
    source_back = txn / 'old' / 'sources'
    source_new = txn / 'new' / 'sources'
    old_exists = rec['source_old']
    if not isinstance(old_exists, bool) or rec['source_new'] is not True:
        raise ValidationFailure('SOURCE_TRANSACTION_JOURNAL_INVALID')
    latest = (all(_digest(workspace / name) == rec['new'][name] for name in _FILES)
              and _digest(imports_root / 'state.json') == rec['ledger_new']
              and _source_digest(workspace / 'sources') == rec['new_source_digest'])
    if latest:
        _remove_tree(txn)
        _native_io_path(marker).unlink()
        return {'status': 'COMMITTED_RECOVERED'}
    # Never overwrite a pre-existing/unrelated path: this is the exact
    # operation's own workspace, whose journal was written before mutation.
    if old_exists:
        if _native_io_path(source_back).is_dir() and not _native_io_path(source_back).is_symlink():
            _remove_tree(workspace / 'sources')
            os.replace(_native_io_path(source_back), _native_io_path(workspace / 'sources'))
        elif _source_digest(workspace / 'sources') != rec['old_source_digest']:
            raise ValidationFailure('SOURCE_TRANSACTION_SOURCES_BACKUP_MISSING')
    else:
        _remove_tree(workspace / 'sources')
    for name in _FILES:
        expected = rec['old'][name]
        target = workspace / name
        if expected is None:
            _native_io_path(target).unlink(missing_ok=True)
        else:
            if _native_io_path(target).is_symlink():
                raise SafetyViolation('SOURCE_TRANSACTION_CANONICAL_LINK')
            old_data = (_native_io_path(txn / 'old' / name)).read_bytes()
            if 'sha256:' + hashlib.sha256(old_data).hexdigest() != expected:
                raise ValidationFailure('SOURCE_TRANSACTION_BACKUP_CORRUPT')
            # atomic_write_text preserves full pre-transaction JSON/text bytes.
            _restore_bytes(target, old_data)
            if _digest(target) != expected:
                raise ValidationFailure('SOURCE_TRANSACTION_ROLLBACK_FAILED')
    ledger_backup = txn / 'old' / 'state.json'
    if rec['ledger_old'] is None:
        (_native_io_path(imports_root / 'state.json')).unlink(missing_ok=True)
    elif _digest(ledger_backup) == rec['ledger_old']:
        _restore_bytes(imports_root / 'state.json', _native_io_path(ledger_backup).read_bytes())
    else:
        raise ValidationFailure('SOURCE_TRANSACTION_LEDGER_BACKUP_CORRUPT')
    if _digest(imports_root / 'state.json') != rec['ledger_old']:
        raise ValidationFailure('SOURCE_TRANSACTION_ROLLBACK_FAILED')
    _remove_tree(txn)
    _native_io_path(marker).unlink()
    return {'status': 'ROLLED_BACK_RECOVERED'}


def _prepare_sources(workspace: Path, staging: Path, imports_root: Path, snapshot_ref: str | None) -> tuple[list[Path], list[str]]:
    source_dir = staging / 'new' / 'sources'
    _native_io_path(source_dir).mkdir(parents=True, mode=0o700, exist_ok=False)
    result = []; names = []
    if snapshot_ref is not None:
        from .local_web_imports import copy_verified_document, _member
        current = verify_snapshot(imports_root, snapshot_ref)
        for entry in current['record']['sources']:
            name = entry['safe_storage_name'] + ('.md' if entry['format'] == 'MD' else '')
            dest = source_dir / name
            related = [doc for doc in current['record']['documents']
                       if doc['source_ref'] == entry['source_ref']]
            if not related:
                raise ValidationFailure('SOURCE_SNAPSHOT_WITHOUT_DOCUMENTS')
            if entry['format'] == 'MD':
                if len(related) != 1:
                    raise ValidationFailure('SOURCE_SNAPSHOT_INVALID')
                file = related[0]
                copy_verified_document(current['directory'], file['storage_relative_path'], file['sha256'], dest)
            elif entry['format'] == 'ZIP':
                _native_io_path(dest).mkdir(mode=0o700, exist_ok=False)
                for doc in related:
                    parts = _member(doc['source_relative_path'])
                    target = dest.joinpath(*parts)
                    _native_io_path(target.parent).mkdir(parents=True, mode=0o700, exist_ok=True)
                    copy_verified_document(current['directory'], doc['storage_relative_path'], doc['sha256'], target)
            else:
                raise ValidationFailure('SOURCE_SNAPSHOT_INVALID')
            names.append(name)
            result.append(dest)
    return result, names


def refresh_intake_sources(workspace: Path, *, snapshot_ref: str | None,
                           expected_revision: int, expected_input_digest: str,
                           explicit_no_documentation: bool = False) -> dict[str, Any]:
    """Public bounded API, fenced by the existing outer guarded_mutation wrapper.

    It never updates PROJECT_INPUT_ACCEPTED or a Project Instance.  The caller
    must also reject service-owned prepare artifacts before invoking it.
    """
    workspace = Path(workspace).expanduser().resolve(strict=True)
    imports_root = _imports(workspace)
    if pending_refresh(workspace):
        recovery = recover_source_refresh(workspace)
        raise ValidationFailure('SOURCE_REFRESH_RECOVERED_RETRY_WITH_CURRENT_FINGERPRINT', recovery)
    state = _active_state(imports_root)
    if state['revision'] != expected_revision:
        raise ValidationFailure('STALE_SOURCE_REVISION')
    if draft_input_digest(workspace) != expected_input_digest:
        raise ValidationFailure('STALE_FINGERPRINT: PROJECT_INPUT changed')
    if snapshot_ref is None and not explicit_no_documentation:
        raise ValidationFailure('SOURCE_SNAPSHOT_REQUIRED')
    if snapshot_ref is not None and explicit_no_documentation:
        raise ValidationFailure('SOURCE_MODE_CONFLICT')
    if snapshot_ref is not None:
        loaded = verify_snapshot(imports_root, snapshot_ref)
        if loaded['record']['revision'] != expected_revision + 1:
            raise ValidationFailure('STALE_SOURCE_REVISION')
        new_digest = loaded['digest']
        new_revision = loaded['record']['revision']
    else:
        new_digest = None
        new_revision = expected_revision + 1
    current = load_data(workspace / 'PROJECT_INPUT.yaml')
    if not isinstance(current, dict) or not isinstance(current.get('approvals'), dict):
        raise ValidationFailure('INVALID_INTAKE_WORKSPACE')
    session = load_data(workspace / 'SESSION.yaml')
    state_doc = load_data(workspace / 'STATE.yaml')
    if not isinstance(session.get('session'), dict) or not isinstance(state_doc.get('state'), dict):
        raise ValidationFailure('INVALID_INTAKE_SESSION')
    if (_native_io_path(workspace / '.harness/state/PROJECT_INPUT_ACCEPTED.yaml')).exists():
        raise ValidationFailure('SOURCE_REFRESH_AFTER_ACCEPTANCE_UNSUPPORTED')
    tx_id = 'TX-' + uuid4().hex.upper()
    tx_root = _private_directory(imports_root / 'transactions') / tx_id
    _private_directory(tx_root)
    _private_directory(tx_root / 'new')
    _private_directory(tx_root / 'old')
    try:
        new_paths, names = _prepare_sources(workspace, tx_root, imports_root, snapshot_ref)
        inventory = build_source_inventory(new_paths, session_ref=session['session']['id'])
        for source in inventory['source_inventory']['sources']:
            source['path'] = str(workspace / 'sources' / source['name'])
        inventory['source_inventory']['revision'] = new_revision
        input_after = deepcopy(current)
        docs = input_after['project']['documentation']
        docs['availability'] = 'NONE' if explicit_no_documentation else 'PROVIDED'
        # Source inventory is factual; declaring an imported file *normative* is a
        # semantic GPT/user decision, never made by the importer.
        docs['normative_sources'] = []
        docs['notes'] = ('Пользователь подтвердил отсутствие документации.' if explicit_no_documentation
                         else 'Документы импортированы; семантический анализ ещё не выполнен.')
        input_after['metadata']['generated_at'] = None
        for approval in input_after['approvals'].values():
            if not isinstance(approval, dict) or set(approval) != {'approved','actor','approved_at','notes'}:
                raise ValidationFailure('INVALID_DRAFT_APPROVAL')
            approval.update({'approved': False, 'actor': None, 'approved_at': None, 'notes': None})
        issues = project_input_schema_issues(input_after, relaxed=True)
        if issues:
            raise ValidationFailure('SOURCE_REFRESH_INPUT_SCHEMA_INVALID', issues[:5])
        readiness = validate_project_input(input_after, require_approvals=True)
        if readiness['status'] == 'INVALID':
            raise ValidationFailure('SOURCE_REFRESH_INPUT_INVALID', readiness['errors'][:5])
        from .intake import _questions_markdown
        questions = questions_for(input_after)
        now = utc_now()
        questionnaire = {'questionnaire_session': state_doc['state']['questionnaire_ref'],
                         'question_budget': {'target': 10, 'hard_limit_before_draft': 15, 'asked': len(questions)},
                         'questions': questions}
        new_session = deepcopy(session)
        new_session['session']['revision'] = int(session['session'].get('revision', 1)) + 1
        new_session['session']['source_import_revision'] = new_revision
        new_session['session']['source_snapshot_ref'] = snapshot_ref
        new_session['session']['source_analysis_status'] = 'NOT_ANALYZED'
        new_session['session']['status'] = readiness['status']
        new_session['session']['updated_at'] = now
        new_state = deepcopy(state_doc)
        new_state['state']['source_paths'] = [str(workspace / 'sources' / name) for name in names]
        new_state['state']['source_import_revision'] = new_revision
        new_state['state']['source_snapshot_ref'] = snapshot_ref
        new_state['state']['source_analysis_status'] = 'NOT_ANALYZED'
        new_state['state']['prior_answers_require_source_review'] = True
        new_state['state']['status'] = readiness['status']
        new_state['state']['updated_at'] = now
        new_state['state']['next_route'] = {
            'WAITING_INPUT': 'ANSWER_QUESTIONS', 'WAITING_DECISION': 'APPROVE_BASELINES',
            'READY_FOR_HANDOFF': 'PREPARE_CODEX_HANDOFF', 'INVALID': 'FIX_INPUT',
        }.get(readiness['status'], 'FIX_INPUT')
        proposals = {'PROJECT_INPUT.yaml': pretty_json(input_after),
                     'SOURCE_INVENTORY.yaml': pretty_json(inventory),
                     'QUESTIONS.yaml': pretty_json(questionnaire),
                     'QUESTIONS.md': _questions_markdown(questions, readiness),
                     'READINESS.json': pretty_json(readiness),
                     'SESSION.yaml': pretty_json(new_session),
                     'STATE.yaml': pretty_json(new_state)}
        for name, content in proposals.items():
            atomic_write_text(tx_root / 'new' / name, content)
        ledger_after = {'version': 1, 'revision': new_revision, 'active_snapshot': snapshot_ref,
                        'snapshot_digest': new_digest,
                        'documentation_choice': 'NONE' if explicit_no_documentation else 'PROVIDED',
                        'analysis_status': 'NOT_ANALYZED', 'answers_source_review_required': True}
        atomic_write_text(tx_root / 'new' / 'state.json', pretty_json(ledger_after))
        files = {name: _digest(workspace / name) for name in _FILES}
        after = {name: _digest(tx_root / 'new' / name) for name in _FILES}
        for name in _FILES:
            if files[name] is not None:
                shutil.copyfile(_native_io_path(workspace / name), _native_io_path(tx_root / 'old' / name))
        old_ledger = imports_root / 'state.json'
        if _native_io_path(old_ledger).exists():
            shutil.copyfile(_native_io_path(old_ledger), _native_io_path(tx_root / 'old' / 'state.json'))
        receipt = {'version': 1, 'id': tx_id, 'old': files, 'new': after,
                   'source_old': (_native_io_path(workspace / 'sources')).exists(), 'source_new': True,
                   'old_source_digest': _source_digest(workspace / 'sources'),
                   'new_source_digest': _source_digest(tx_root / 'new' / 'sources'),
                   'ledger_old': _digest(imports_root / 'state.json'),
                   'ledger_new': _digest(tx_root / 'new' / 'state.json')}
        write_data(imports_root / 'pending.json', receipt)  # durable intent before replace
        try:
            if (_native_io_path(workspace / 'sources')).exists():
                os.replace(_native_io_path(workspace / 'sources'), _native_io_path(tx_root / 'old' / 'sources'))
            os.replace(_native_io_path(tx_root / 'new' / 'sources'), _native_io_path(workspace / 'sources'))
            for name in _FILES:
                os.replace(_native_io_path(tx_root / 'new' / name), _native_io_path(workspace / name))
            os.replace(_native_io_path(tx_root / 'new' / 'state.json'), _native_io_path(imports_root / 'state.json'))
            if any(_digest(workspace / name) != after[name] for name in _FILES):
                raise ValidationFailure('SOURCE_REFRESH_WRITE_INTEGRITY_ERROR')
        except BaseException:
            recover_source_refresh(workspace)
            raise
        (_native_io_path(imports_root / 'pending.json')).unlink()
        _remove_tree(tx_root)
        return {'status': 'IMPORTED_NOT_ANALYZED' if not explicit_no_documentation else 'DOCUMENTATION_NONE_CONFIRMED',
                'source_revision': new_revision, 'snapshot_ref': snapshot_ref,
                'accepted': len(inventory['source_inventory']['sources']),
                'readiness_status': readiness['status'], 'approvals_invalidated': True,
                'prior_answers_require_source_review': True}
    finally:
        if not (_native_io_path(imports_root / 'pending.json')).exists() and _native_io_path(tx_root).exists():
            _remove_tree(tx_root)

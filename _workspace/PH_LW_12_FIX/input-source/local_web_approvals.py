"""PH-LW-07: explicit local decisions, bounded companion receipts and recovery.

GET is read-only. Receipts bind local actions, not identity/signatures. Only
provisional input is changed, through the public approval API under its lock.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .intake import check_intake
from .local_web_approval_core import approval_candidate, apply_provisional_approval
from .local_web_drafts import draft_input_digest
from .local_web_exchange import _save, _load, _source_binding
from .local_web_exchange_contract import ExchangeError, digest, KEY, unapproved
from .local_web_imports import source_state, _private_directory
from .local_web_source_refresh import pending_refresh, _source_digest
from .local_web_sources_service import _check_prepared
from .operation_guard import project_operation_guard
from .platform_fs import ensure_native_path
from .project_input import approvals_for_mode, validate_project_input, DEFAULT_EXECUTION_POLICY
from .serialization import load_data, pretty_json

STORE = '.local-web-approvals'
LABELS = {'project_definition': 'Project Definition', 'brownfield_baseline': 'Brownfield Baseline',
          'architecture_baseline': 'Architecture', 'technology_baseline': 'Technology', 'codex_handoff': 'Codex Handoff'}


def assert_no_pending_approval(root: Path) -> None:
    if (root / STORE / 'pending.json').exists():
        raise ExchangeError('APPROVAL_RECOVERY_REQUIRED', 'Прерванное согласование требует явной сверки; изменения заблокированы.')


def _root(service, pid):
    root, kind = service._registered(pid)
    if kind != 'workspace' or (root / '.harness').exists():
        raise ExchangeError('PROVISIONAL_ONLY', 'Согласования доступны только для provisional intake, не accepted Project Instance.')
    if load_data(root / 'PROJECT_INPUT.yaml').get('execution') != DEFAULT_EXECUTION_POLICY:
        raise ExchangeError('MANUAL_ONLY', 'Согласования Local Web поддерживают только MANUAL_HANDOFF с network NONE.')
    store = root / STORE
    ensure_native_path(store, tree=True)
    return root, store


def _sources(root):
    source = load_data(root / 'SOURCE_INVENTORY.yaml')['source_inventory']
    data = {'source_revision': source['revision'], 'source_inventory_digest': digest(source)}
    data['source_tree_digest'] = _source_digest(root / 'sources')
    imports = root.parent / 'imports'
    if root.name == 'intake' and imports.is_dir():
        data.update(_source_binding(source_state(imports)))
    repo = root / 'REPOSITORY_INVENTORY.yaml'
    data['repository_inventory_digest'] = digest(load_data(repo)) if repo.exists() else None
    if repo.exists():
        from .inventory import build_repository_inventory
        inventory = load_data(repo)['repository_inventory']
        repository = Path(inventory['repository_path'])
        ensure_native_path(repository, tree=True)
        live = build_repository_inventory(repository, session_ref=inventory['session_ref'])
        data['repository_tree_digest'] = live['repository_inventory']['tree_digest']
        data['repository_baseline_matches'] = data['repository_tree_digest'] == inventory['tree_digest']
    return data


def _context(root):
    value = load_data(root / 'PROJECT_INPUT.yaml')
    sources = _sources(root)
    return value, sources, digest({'input': unapproved(value), 'sources': sources})


def _records(store):
    paths = sorted(store.glob('LWA-*.json'))
    if len(paths) > 256:
        raise ExchangeError('APPROVAL_STORAGE_LIMIT', 'Достигнут лимит 256 решений; история сохранена.')
    return sorted((_load(p) for p in paths), key=lambda r: r['sequence'])


def rework_requests(root):
    """Read-only unresolved operator comments; no invented core statuses."""
    latest = {}
    for row in _records(root / STORE):
        if row['decision'] in {'APPROVE', 'REWORK'}:
            latest[row['subject']] = row
    return [{'subject': row['subject'], 'comment': row['comment'], 'receipt_id': row['receipt_id']}
            for row in latest.values() if row['decision'] == 'REWORK']


def _subject(root, value, name, sources):
    common = {'project_name': value['project']['name'], 'mode': value['project']['mode'],
              'implementation': value['implementation'], 'sources': sources}
    if name == 'project_definition':
        content = {'project': value['project'], 'profile': value['profile']}
    elif name == 'architecture_baseline':
        content = {'architecture': value['architecture'], 'constraints': value['project']['constraints']}
    elif name == 'technology_baseline':
        content = {'technology': value['technology'], 'skills': value['skills']}
    elif name == 'brownfield_baseline':
        repo = root / 'REPOSITORY_INVENTORY.yaml'
        inventory = load_data(repo)['repository_inventory'] if repo.exists() else {}
        content = {'brownfield': value['brownfield'], 'evidence_context': {k: v for k, v in inventory.items()
            if k not in {'repository_path', 'candidate_commands'}},
            'obligations': 'Baseline inventory прочитан без запуска команд. Claimed level не является accepted level; Stage evidence и acceptance отдельны.'}
    else:
        content = {'draft': {k: v for k, v in value.items() if k != 'approvals'}, 'obligations': [
            'Передать согласованный scope, ограничения, architecture и technology без расширения target.',
            'MANUAL_HANDOFF; automatic executor выключен. Отдельные Stage decisions и semantic evidence обязательны.',
            'Детальные Task/JIT только active Stage; accepted history сохраняется.',
            'Подготовка Project Instance ожидает PH-LW-08; сейчас проект не создаётся.']}
    return {**common, **content}


def _review(service, pid, root, store):
    value, sources, context = _context(root)
    records = _records(store)
    actor = _load(store / 'actor.json')['actor'] if (store / 'actor.json').exists() else None
    order = approvals_for_mode(value['project']['mode'])
    ready = validate_project_input(value, require_approvals=True)
    complete = validate_project_input(value, require_approvals=False)['status'] == 'READY_FOR_HANDOFF'
    if value['project']['mode'] in {'BROWNFIELD', 'HYBRID'}:
        complete = complete and sources.get('repository_baseline_matches') is True
    rows, invalidations, unbound = [], [], []
    for name in order:
        content = _subject(root, value, name, sources)
        subject_digest = digest(content)
        past = [r for r in records if r['subject'] == name and r['decision'] == 'APPROVE']
        receipt = next((r for r in reversed(past) if r['content_digest'] == context
            and r['subject_digest'] == subject_digest and value['approvals'][name] == r['canonical_approval']), None)
        approved = value['approvals'][name]['approved']
        if approved and receipt is None:
            unbound.append(name)
        if past and (receipt is None or not approved):
            prior = past[-1]
            reason = 'SOURCE_CHANGED' if prior['sources'] != sources else (
                'MATERIAL_DRAFT_CHANGE' if prior['content_digest'] != context else 'REWORK_OR_EXTERNAL_APPROVAL_CHANGE')
            invalidations.append({'subject': name, 'reason': reason, 'previous_receipt': prior['receipt_id']})
        rows.append({'subject': name, 'label': LABELS[name], 'content': content,
            'subject_digest': subject_digest, 'approved': approved and receipt is not None,
            'receipt_id': receipt['receipt_id'] if receipt else None})
    pending = (store / 'pending.json').exists()
    next_subject = next((row['subject'] for row in rows if not row['approved']), None)
    binding = {**sources, 'input_revision': draft_input_digest(root),
               'fingerprint': service.core_fingerprint(root, 'workspace')}
    result = {'version': 1, 'project_id': pid, 'actor': actor, 'binding': binding,
        'content_digest': context, 'subjects': rows, 'next_subject': next_subject,
        'readiness': ready, 'subject_complete': complete, 'unbound_approvals': unbound,
        'invalidations': invalidations, 'recovery_required': pending, 'receipts': records,
        'rework_requests': rework_requests(root),
        'next_action': 'RECOVER_APPROVAL' if pending else 'REVIEW_STALE_APPROVALS' if unbound else
            'ANSWER_QUESTIONS' if not complete else 'SET_ACTOR' if not actor else
            'CONFIRM_' + next_subject.upper() if next_subject else 'PREPARATION_PENDING_PH_LW_08'}
    result['review_digest'] = digest({k: result[k] for k in ('version', 'project_id', 'actor', 'binding',
        'content_digest', 'subjects', 'next_subject', 'unbound_approvals', 'recovery_required')})
    return result


def review(service, pid):
    root, store = _root(service, pid)
    with project_operation_guard(root):
        return _review(service, pid, root, store)


def _admit(service, pid, root):
    _check_prepared(service, pid)
    if root.name == 'intake' and (root.parent / 'imports').is_dir() and pending_refresh(root):
        raise ExchangeError('SOURCE_RECOVERY_REQUIRED', 'Сначала восстановите источники.')
    # Companion state is bounded, preserved on limit and never silently pruned.
    store = root / STORE
    if len(_records(store)) >= 256 or sum(p.stat().st_size for p in store.rglob('*') if p.is_file()) > 16 * 1024 * 1024:
        raise ExchangeError('APPROVAL_STORAGE_LIMIT', 'Хранилище решений заполнено; история сохранена.')


def set_actor(service, pid, *, actor, expected_fingerprint):
    root, store = _root(service, pid)
    if (not isinstance(actor, str) or not actor.strip() or len(actor) > 120
            or any(ord(c) < 32 or ord(c) == 127 for c in actor)):
        raise ExchangeError('ACTOR_INVALID', 'Укажите имя оператора, от 1 до 120 символов.')
    actor = actor.strip()
    with project_operation_guard(root):
        path = store / 'actor.json'
        if path.exists():
            record = _load(path)
            if record['actor'] != actor:
                raise ExchangeError('ACTOR_CONFLICT', 'Оператор уже задан для этой intake session.')
            return record
        _admit(service, pid, root)
        if expected_fingerprint != service.core_fingerprint(root, 'workspace'):
            raise ExchangeError('STALE_APPROVAL', 'Форма оператора устарела; перечитайте draft.')
        _private_directory(store)
        _save(path, {'version': 1, 'actor': actor, 'created_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')})
        return _load(path)


def _finish(root, store, intent):
    path = store / (intent['receipt_id'] + '.json')
    if path.exists():
        receipt = _load(path)
        if receipt['intent_digest'] != intent['intent_digest']:
            raise ExchangeError('APPROVAL_RECOVERY_AMBIGUOUS', 'Receipt не совпал с intent.')
    else:
        # Projections are refreshed only after a successful canonical commit.
        checked = check_intake(root)
        value = load_data(root / 'PROJECT_INPUT.yaml')
        receipt = {**intent, 'state': 'COMMITTED', 'readiness_status': checked['status'],
            'canonical_approval': value['approvals'].get(intent['subject']),
            'next_action': 'PREPARATION_PENDING_PH_LW_08' if checked['status'] == 'READY_FOR_HANDOFF' else 'CONTINUE_INTAKE'}
        _save(path, receipt)
        receipt = _load(path)
    (store / 'pending.json').unlink()
    return receipt


def decide(service, pid, *, subject, decision, comment, review_digest, subject_digest,
           expected_fingerprint, idempotency_key, confirm):
    root, store = _root(service, pid)
    if not isinstance(idempotency_key, str) or not KEY.fullmatch(idempotency_key) or confirm is not True:
        raise ExchangeError('EXPLICIT_DECISION_REQUIRED', 'Нужны отдельное подтверждение и корректный ключ повтора.')
    request_digest = digest([subject, decision, comment, review_digest, subject_digest, expected_fingerprint, confirm])
    receipt_id = 'LWA-' + digest([pid, idempotency_key]).split(':')[1][:32].upper()
    with project_operation_guard(root):
        path = store / (receipt_id + '.json')
        if path.exists():
            prior = _load(path)
            if prior['request_digest'] != request_digest:
                raise ExchangeError('APPROVAL_REPLAY_CONFLICT', 'Ключ уже связан с другим решением.')
            return prior
        _admit(service, pid, root)
        view = _review(service, pid, root, store)
        if view['review_digest'] != review_digest or view['binding']['fingerprint'] != expected_fingerprint:
            raise ExchangeError('STALE_APPROVAL', 'Содержание, источники или оператор изменились; перечитайте согласование.')
        if not view['actor']:
            raise ExchangeError('ACTOR_REQUIRED', 'Сначала явно задайте оператора.')
        row = next((r for r in view['subjects'] if r['subject'] == subject), None)
        if row is None or row['subject_digest'] != subject_digest:
            raise ExchangeError('SUBJECT_MISMATCH', 'Digest утверждаемого предмета не совпал.')
        if not isinstance(decision, str) or decision not in {'APPROVE', 'REWORK', 'INVALIDATE'}:
            raise ExchangeError('DECISION_INVALID', 'Неизвестное решение.')
        if view['unbound_approvals'] and decision != 'INVALIDATE':
            raise ExchangeError('STALE_APPROVAL_BINDING', 'Текущие approval fields не связаны с действительными receipts; требуется явный сброс.')
        if decision == 'INVALIDATE' and not view['unbound_approvals']:
            raise ExchangeError('INVALIDATION_NOT_REQUIRED', 'Несвязанных approvals нет.')
        if decision == 'APPROVE' and (not view['subject_complete'] or view['next_subject'] != subject):
            raise ExchangeError('APPROVAL_NOT_READY', 'Заполните material fields и соблюдайте порядок отдельных решений.')
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        proposal = approval_candidate(root, subject=subject, decision=decision, actor=view['actor'],
            timestamp=timestamp, comment=comment, expected_input_digest=view['binding']['input_revision'])
        intent = {'version': 1, 'project_id': pid, 'receipt_id': receipt_id,
            'sequence': len(view['receipts']) + 1, 'request_digest': request_digest,
            'subject': subject, 'decision': decision, 'actor': view['actor'], 'timestamp': timestamp,
            'comment': comment, 'binding': view['binding'], 'review_digest': review_digest,
            'content_digest': view['content_digest'], 'sources': _sources(root),
            'subject_digest': subject_digest, 'subject_content': row['content'],
            'after_digest': proposal['after_digest'], 'reset_subjects': proposal['reset_subjects']}
        intent['intent_digest'] = digest(intent)
        size = len(pretty_json(intent).encode('utf-8'))
        stored = sum(p.stat().st_size for p in store.rglob('*') if p.is_file())
        if size > 2 * 1024 * 1024 or stored + 2 * size + 8192 > 16 * 1024 * 1024:
            raise ExchangeError('APPROVAL_STORAGE_LIMIT', 'Предмет согласования слишком велик.')
        _private_directory(store)
        _save(store / 'pending.json', intent)
        apply_provisional_approval(root, intent)
        return _finish(root, store, intent)


def recover(service, pid):
    root, store = _root(service, pid)
    with project_operation_guard(root):
        marker = store / 'pending.json'
        if not marker.exists():
            return {'status': 'CLEAN'}
        intent = {k: v for k, v in _load(marker).items() if k != 'record_digest'}
        if (intent.get('project_id') != pid or intent.get('intent_digest') != digest(
                {k: v for k, v in intent.items() if k != 'intent_digest'}) or _sources(root) != intent['sources']):
            raise ExchangeError('APPROVAL_RECOVERY_AMBIGUOUS', 'Источники или intent изменились. Автоповтор запрещён.')
        actual = draft_input_digest(root)
        if actual == intent['after_digest']:
            return {'status': 'COMMITTED_RECOVERED', 'receipt': _finish(root, store, intent)}
        if actual == intent['binding']['input_revision'] and not (store / (intent['receipt_id'] + '.json')).exists():
            marker.unlink()
            return {'status': 'NOT_COMMITTED'}
        raise ExchangeError('APPROVAL_RECOVERY_AMBIGUOUS', 'Draft не совпал ни с before, ни с after. Требуется диагностика.')

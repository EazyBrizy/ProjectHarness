"""PH-LW-06 draft-only JSON boundary; no YAML, execution or approval parsing."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from importlib import resources
import json
import math
import re
from typing import Any

from .errors import ValidationFailure
from .local_web_drafts import DRAFT_FIELDS
from .project_input import project_input_schema_issues, _validate_schema_node
from .serialization import canonical_json_bytes

REPLY_MAX = 512 * 1024
JSON_DEPTH_MAX = 24
JSON_NODES_MAX = 30000
PACK_MAX = 20 * 1024 * 1024
PART_MAX = 256 * 1024
EXPORTS_MAX = 32
STORAGE_MAX = 64 * 1024 * 1024
EXCHANGE_ID = re.compile(r'^LWX-[A-F0-9]{32}$')
IMPORT_ID = re.compile(r'^LWI-[A-F0-9]{32}$')
KEY = re.compile(r'^[a-zA-Z0-9_.:-]{16,160}$')


class ExchangeError(ValidationFailure):
    """Only server-authored messages/paths may enter a repair prompt."""
    def __init__(self, code: str, message: str, errors: list[dict] | None = None):
        super().__init__(message)
        self.exchange_code = code
        self.errors = errors or []

    def public(self) -> dict:
        return {'code': self.exchange_code, 'message_ru': self.message,
                'next_action_ru': 'Проверьте ошибки, исправьте ответ или подготовьте новый пакет.',
                'validation_errors': self.errors}


def digest(value: Any) -> str:
    return 'sha256:' + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def bytes_digest(value: bytes) -> str:
    return 'sha256:' + hashlib.sha256(value).hexdigest()


def bounded_json(text: str) -> dict:
    if not isinstance(text, str):
        raise ExchangeError('JSON_REQUIRED', 'Вставьте JSON текст ответа GPT.')
    try:
        data = text.encode('utf-8', 'strict')
    except UnicodeError as exc:
        raise ExchangeError('JSON_INVALID', 'Ответ содержит недопустимый Unicode.') from exc
    if len(data) > REPLY_MAX:
        raise ExchangeError('REPLY_TOO_LARGE', 'Ответ превышает 512 KiB; уменьшите draft и повторите.')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('nonfinite')
    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError, RecursionError) as exc:
        raise ExchangeError('JSON_INVALID', 'Требуется один JSON object без повторяющихся ключей, NaN и Markdown fences.') from exc
    nodes = 0
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if depth > JSON_DEPTH_MAX or nodes > JSON_NODES_MAX:
            raise ExchangeError('JSON_COMPLEXITY_LIMIT', 'JSON превышает глубину 24 или 30000 узлов.')
        if isinstance(item, float) and not math.isfinite(item):
            raise ExchangeError('JSON_INVALID', 'JSON не допускает бесконечные числа.')
        if isinstance(item, dict):
            stack.extend((v, depth + 1) for v in item.values())
        elif isinstance(item, list):
            stack.extend((v, depth + 1) for v in item)
    if not isinstance(value, dict):
        raise ExchangeError('JSON_REQUIRED', 'Корень ответа должен быть JSON object.')
    return value


def schema_errors(issues: list[dict]) -> list[dict]:
    # Core messages can echo input values or keys. Report exact location and
    # keyword, never values, host environment, raw reply or paths in repair.
    out = []
    for item in issues[:20]:
        path = item.get('path', '$')
        safe = path if re.fullmatch(r'[A-Za-z0-9_.$\[\]-]{1,200}', path) else '$.<invalid-key>'
        out.append({'path': safe, 'keyword': item['keyword']})
    return out


def semantic_errors(candidate: dict, errors: list[str]) -> list[dict]:
    """Exact failing rule/location without echoing arbitrary model text."""
    result = []
    from .project_input import _task_key
    for error in errors[:20]:
        path, rule = '$.project_input_draft', 'semantic-validation'
        if error.startswith('Unknown profile.ref'):
            path, rule = 'profile.ref', 'registered-profile-required'
        elif 'skill resolution' in error or error.startswith('skills.resolutions'):
            path, rule = 'skills.resolutions', 'active-skill-resolution-required'
        elif 'claimed_current_level' in error:
            path, rule = 'implementation.claimed_current_level', 'mode-compatible-level-required'
        elif 'cycle' in error.lower() or 'depend' in error.lower():
            path, rule = 'planning.work_packages', 'valid-acyclic-task-dependencies-required'
        for wi, wp in enumerate(candidate.get('planning', {}).get('work_packages') or [], 1):
            for ti, task in enumerate(wp.get('tasks') or [], 1):
                key = _task_key(task, wi, ti)
                if error.startswith('Task ' + key + ':'):
                    path = f'planning.work_packages[{wi-1}].tasks[{ti-1}]'
                    if 'verification needs' in error:
                        path += '.verification'; rule = 'commands-or-expected-paths-or-manual-checks-required'
                    elif 'declared write scope' in error:
                        path += '.scope.write'; rule = 'non-verify-task-write-scope-required'
                    elif 'unknown capabilities' in error:
                        path += '.route.required_capabilities'; rule = 'registered-capabilities-required'
                    elif 'scope.' in error:
                        path += '.scope'; rule = 'safe-relative-product-path-required'
        result.append({'path': path, 'keyword': rule})
    return result or [{'path': '$.project_input_draft', 'keyword': 'semantic-validation'}]


def validate_envelope(value: dict) -> None:
    version = value.get('envelope_version')
    if type(version) is not int or version not in (2, 3, 4):
        raise ExchangeError('EXCHANGE_SCHEMA_INVALID', 'Поддерживаются ответы LOCAL_WEB_GPT_DRAFT_ONLY@2, @3 и @4.')
    schema = json.loads(resources.files('project_harness').joinpath(
        f'resources/local_web/gpt_exchange_reply_v{version}.schema.json').read_text('utf-8'))
    issues = _validate_schema_node(value, schema, schema)
    if issues:
        raise ExchangeError('EXCHANGE_SCHEMA_INVALID', f'Ответ не соответствует LOCAL_WEB_GPT_DRAFT_ONLY@{version}.', schema_errors(issues))


def get_field(value: dict, field: str) -> Any:
    for part in field.split('.'):
        value = value[part]
    return value


def set_field(value: dict, field: str, item: Any) -> None:
    parts = field.split('.')
    for part in parts[:-1]:
        value = value[part]
    value[parts[-1]] = deepcopy(item)


def unapproved(value: dict) -> dict:
    result = deepcopy(value)
    for receipt in result['approvals'].values():
        receipt.update(approved=False, actor=None, approved_at=None, notes=None)
    return result


def draft_patch(original: dict, incoming: dict, *, allow_target_choice: bool = False) -> dict:
    # Explain forged approvals before generic schema errors (e.g. absent actor
    # timestamp), so the user is not prompted to "repair" a forged approval.
    if incoming.get('approvals') != unapproved(original)['approvals']:
        raise ExchangeError('APPROVAL_FORGERY', 'GPT не может задавать approvals или actor. Все approval records должны быть pending: false/null.')
    issues = [issue for issue in project_input_schema_issues(incoming)
              if issue['keyword'] not in {'minItems', 'minLength'}]
    if issues:
        raise ExchangeError('DRAFT_SCHEMA_INVALID', 'PROJECT_INPUT@4 draft содержит неверные или недостающие поля.', schema_errors(issues))
    # Approval copies, even from a formerly approved export, never authorize.
    def check_nested(item, path=''):
        if isinstance(item, dict):
            for key, child in item.items():
                if not path and key == 'approvals':
                    continue
                if key in {'approved', 'actor', 'approved_at', 'trusted_evidence', 'highest_accepted_level',
                           'active_stage', 'server_path', 'project_root', 'workspace_root'}:
                    raise ExchangeError('PROTECTED_DRAFT_FIELDS', 'Draft содержит управляющее поле, actor или trusted evidence вне разрешённого контракта.')
                if key in {'cwd', 'expected_paths', 'read_paths'}:
                    values = child if isinstance(child, list) else [child]
                    for value in values:
                        if isinstance(value, str) and (re.match(r'^(?:[A-Za-z]:|[/\\])', value) or
                                                       '..' in re.split(r'[/\\]', value)):
                            raise ExchangeError('DRAFT_PATH_INVALID', 'Task draft может ссылаться только на относительные пути продукта.')
                check_nested(child, path + '.' + key)
        elif isinstance(item, list):
            for child in item:
                check_nested(child, path)
    check_nested(incoming)
    expected = unapproved(original)
    patch = {}
    for field in sorted(DRAFT_FIELDS):
        item = get_field(incoming, field)
        set_field(expected, field, item)
        if item != get_field(original, field):
            patch[field] = deepcopy(item)
    if incoming != expected:
        raise ExchangeError('PROTECTED_DRAFT_FIELDS', 'Ответ изменяет защищённые metadata, project identity, sources или execution. Скопируйте их из export без изменений.')
    chosen_target = original['implementation']['target_level']
    if not allow_target_choice and chosen_target is not None and incoming['implementation']['target_level'] != chosen_target:
        raise ExchangeError('TARGET_DECISION_REQUIRED', 'GPT не может заменить выбранный target или UNSURE. Измените target отдельным ответом в форме.')
    return patch


def reject_secrets(text: str) -> None:
    # Defense in depth, not a DLP guarantee. The explicit per-item classification
    # and permission declaration are mandatory even when these patterns miss.
    patterns = (r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----', r'\bsk-[A-Za-z0-9_-]{20,}',
                r'\bgh[pousr]_[A-Za-z0-9]{20,}', r'\bAKIA[A-Z0-9]{16}\b',
                r'(?i)\b(?:password|api[_-]?key|secret[_-]?key|access[_-]?token)["\']?\s*[:=]\s*["\']?[^\s"\'<>]{8,}')
    if any(re.search(pattern, text) for pattern in patterns):
        raise ExchangeError('SECRET_DETECTED', 'Экспорт заблокирован: обнаружен возможный секрет. Подготовьте разрешённый обезличенный источник.')


def repair_prompt(error: ExchangeError, exchange_id: str | None) -> str:
    ident = exchange_id if isinstance(exchange_id, str) and EXCHANGE_ID.fullmatch(exchange_id) else '(use the original export ID)'
    return ('Repair the JSON reply using the envelope_version in the original pack, export ' + ident + '.\n'
            'Keep all exact bindings from the original pack. No approvals, actor, evidence or execution changes. '
            'Return one bounded JSON object, not YAML or a code fence. Preserve unknowns; do not invent defaults.\n'
            + json.dumps({'code': error.exchange_code, 'errors': error.errors}, ensure_ascii=False) + '\n'
            + error.message)[:8192]

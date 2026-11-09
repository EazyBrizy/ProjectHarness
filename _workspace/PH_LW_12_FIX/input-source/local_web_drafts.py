"""PH-LW-03: public, bounded provisional-intake update API.

Not an approval endpoint.  A material draft change atomically resets all draft
approvals; no UI route is ever permitted to write PROJECT_INPUT.yaml directly.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .errors import ValidationFailure
from .hashing import sha256_bytes, sha256_file
from .operation_guard import guarded_mutation
from .project_input import project_input_schema_issues, validate_project_input
from .serialization import load_data, pretty_json, write_data
from .platform_fs import ensure_native_path

# Leaf paths only.  These are semantic draft fields, *not* permissions to edit
# metadata/identity/source records/approvals/execution or arbitrary YAML keys.
DRAFT_FIELDS = frozenset(('''
project.problem_statement project.primary_outcome project.users project.scale.initial
project.scale.growth project.connectivity project.platforms
project.deployment.target project.deployment.environment project.data.categories
project.data.sensitivity project.data.storage project.integrations
project.scope.in project.scope.out project.constraints.mandatory
project.constraints.forbidden project.constraints.non_functional
project.success_criteria project.assumptions project.unknowns project.ambiguity_mode
implementation.target_level implementation.claimed_current_level
profile.ref profile.rationale architecture.summary architecture.style
architecture.components architecture.interfaces architecture.data_flow
architecture.quality_attributes architecture.decisions architecture.risks
technology.selections technology.build_commands technology.test_commands
technology.lint_commands skills.resolutions planning.work_packages
brownfield.baseline_summary brownfield.known_defects brownfield.known_gaps
brownfield.technical_debt brownfield.documentation_conflicts
''').split())


def draft_input_digest(workspace: Path) -> str:
    path = Path(workspace) / 'PROJECT_INPUT.yaml'
    if not path.is_file() or path.is_symlink():
        raise ValidationFailure('Не найден черновик PROJECT_INPUT.yaml', 'Зарегистрируйте intake workspace')
    return 'sha256:' + sha256_file(path)


def preview_draft_update(workspace: Path, patch: dict[str, Any], *, expected_input_digest: str) -> dict[str, Any]:
    """Prepare an exact result digest; no writes, no approval or core mutation."""
    ensure_native_path(workspace, tree=True)
    path = Path(workspace) / 'PROJECT_INPUT.yaml'
    if not isinstance(patch, dict) or not patch or len(patch) > 48:
        raise ValidationFailure('Требуется непустой ограниченный набор полей черновика', 'patch')
    unknown = sorted(set(patch) - DRAFT_FIELDS)
    if unknown:
        raise ValidationFailure('Поле черновика не разрешено', unknown)
    if any(not isinstance(k, str) for k in patch):
        raise ValidationFailure('Пути полей черновика должны быть строками')
    if any(len(str(k)) > 120 for k in patch):
        raise ValidationFailure('Имя поля слишком длинное')
    current_digest = draft_input_digest(workspace)
    if expected_input_digest != current_digest:
        raise ValidationFailure('STALE_FINGERPRINT: черновик уже изменён', {'expected': expected_input_digest, 'current': current_digest})
    original = load_data(path)
    if not isinstance(original, dict) or not isinstance(original.get('approvals'), dict):
        raise ValidationFailure('Некорректный provisional PROJECT_INPUT')
    candidate = deepcopy(original)
    for key, value in patch.items():
        current = candidate
        parts = key.split('.')
        for part in parts[:-1]:
            current = current.get(part)
            if not isinstance(current, dict):
                raise ValidationFailure('Структура черновика не соответствует разрешённым полям', key)
        if parts[-1] not in current:
            raise ValidationFailure('Недопустимое поле черновика', key)
        current[parts[-1]] = deepcopy(value)
    changed = candidate != original
    if changed:
        for receipt in candidate['approvals'].values():
            if not isinstance(receipt, dict) or set(receipt) != {'approved', 'actor', 'approved_at', 'notes'}:
                raise ValidationFailure('Невалидная структура approvals в черновике')
            receipt.update({'approved': False, 'actor': None, 'approved_at': None, 'notes': None})
    issues = project_input_schema_issues(candidate, relaxed=True)
    if issues:
        raise ValidationFailure('Нарушена строгая схема черновика', {'schema_errors': issues[:20]})
    readiness = validate_project_input(candidate, require_approvals=True)
    if readiness['status'] == 'INVALID':
        raise ValidationFailure('Недопустимые значения PROJECT_INPUT', {'errors': readiness['errors'][:20]})
    data = pretty_json(candidate).encode('utf-8')
    if len(data) > 2_000_000:
        raise ValidationFailure('Черновик превышает допустимый размер')
    return {
        'candidate': candidate,
        'before_digest': current_digest,
        'after_digest': 'sha256:' + sha256_bytes(data),
        'changed': changed,
        'changed_fields': sorted(patch),
        'approvals_invalidated': changed,
        'readiness_status': readiness['status'],
        'missing_approvals': readiness['missing_approvals'],
    }


@guarded_mutation
def update_provisional_draft(workspace: Path, patch: dict[str, Any], *, expected_input_digest: str) -> dict[str, Any]:
    """Atomic single-file draft commit. Other intake projections update via explicit check-intake."""
    proposal = preview_draft_update(workspace, patch, expected_input_digest=expected_input_digest)
    if proposal['changed']:
        write_data(Path(workspace) / 'PROJECT_INPUT.yaml', proposal['candidate'])
    actual = draft_input_digest(workspace)
    if actual != proposal['after_digest']:
        raise ValidationFailure('DRAFT_WRITE_INTEGRITY_FAILED', {'expected': proposal['after_digest'], 'actual': actual})
    return {key: value for key, value in proposal.items() if key != 'candidate'}

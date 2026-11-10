from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .errors import ValidationFailure
from .registry import allowed_capabilities, implementation_level_model, known_profiles, load_registries
from .hashing import sha256_file
from .serialization import load_data
from .resources import distribution_root
from .util import deep_get, ensure_relative_pattern, nonempty, slugify, unique_preserve

PROJECT_INPUT_SCHEMA_VERSION = 4
PROJECT_INPUT_SCHEMA_ID = "SCHEMA-PROJECT-PREPARATION-INPUT@4"
EXECUTION_POLICY_MIGRATION_ID = "MIG-ENGINE-0.5.0-TO-0.5.1"

DEFAULT_EXECUTION_POLICY = {
    "mode": "MANUAL_HANDOFF",
    "adapter_profile_ref": None,
    "sandbox_profile_ref": None,
    "network_mode": "NONE",
    "completion_policy": "EXPLICIT_AFTER_VERIFICATION",
}

PROJECT_INPUT_MIGRATION_ID = "MIG-ENGINE-0.4.1-TO-0.5.0"
LEGACY_PROJECT_INPUT_MIGRATION_ID = "MIG-ENGINE-0.4.0-TO-0.4.1"
CANONICAL_IMPLEMENTATION_LEVELS = ("PROTOTYPE", "ALPHA", "BETA", "MVP", "RELEASE")
TARGET_IMPLEMENTATION_INPUT_VALUES = set(CANONICAL_IMPLEMENTATION_LEVELS) | {"UNSURE"}
CLAIMED_IMPLEMENTATION_INPUT_VALUES = set(CANONICAL_IMPLEMENTATION_LEVELS) | {"NONE", "UNKNOWN"}

DOCUMENTATION_AVAILABILITY = {"PROVIDED", "PARTIAL", "NONE", "UNKNOWN"}
PROJECT_MODES = {"GREENFIELD", "BROWNFIELD", "HYBRID"}
CONNECTIVITY = {"ONLINE_ONLY", "LIMITED_OFFLINE", "OFFLINE_FIRST", "UNKNOWN"}
DATA_SENSITIVITY_CLASSES = {
    "PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "SECRET", "REGULATED",
}
DATA_SENSITIVITY_INPUT_VALUES = DATA_SENSITIVITY_CLASSES | {"UNKNOWN"}
INPUT_SENSITIVITY_VALUES = DATA_SENSITIVITY_INPUT_VALUES
# Backward-compatible import name used by early integrations.
SENSITIVITY = INPUT_SENSITIVITY_VALUES
AMBIGUITY_MODES = {"PRAGMATIC", "STRICT"}
SKILL_ACTIONS = {"REUSE", "CONFIGURE", "TASK_ONLY"}
TASK_TYPES = {"DESIGN", "IMPLEMENT", "TEST", "DOCUMENT", "INTEGRATE", "VERIFY", "MIGRATE", "REFACTOR", "FIX"}
FORBIDDEN_ACCOUNTING_KEYS = {
    "provider_billing", "provider_cost", "billing_account", "token_ledger",
    "token_usage", "token_count", "input_tokens", "output_tokens", "cost_estimate",
}

GREENFIELD_APPROVALS = [
    "project_definition",
    "architecture_baseline",
    "technology_baseline",
    "codex_handoff",
]
BROWNFIELD_APPROVALS = [
    "project_definition",
    "brownfield_baseline",
    "architecture_baseline",
    "technology_baseline",
    "codex_handoff",
]
# Public compatibility alias. Conditional validation uses approvals_for_mode().
APPROVALS = GREENFIELD_APPROVALS

QUESTION_BANK: list[dict[str, Any]] = [
    {
        "id": "QST-DOCUMENTATION-001",
        "field": "project.documentation.availability",
        "text": "Есть ли документация, ТЗ, требования, схемы, ADR, README или другие материалы проекта? Какие из них нормативны?",
        "why_asked": "Документы определяют исходную базу вопросов, но не становятся принятой истиной без подтверждения.",
        "materiality": "MATERIAL",
        "options": ["PROVIDED", "PARTIAL", "NONE", "UNKNOWN"],
    },
    {
        "id": "QST-OUTCOME-001",
        "field": "project.primary_outcome",
        "text": "Какой первый проверяемый пользовательский результат должен дать проект?",
        "why_asked": "Результат задаёт границу первой версии и причинный порядок работ.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-IMPLEMENTATION-TARGET-001",
        "field": "implementation.target_level",
        "text": "Какой целевой уровень реализации требуется для текущего цикла проекта?",
        "why_asked": "Target level задаёт глубину реализации и последовательный Stage Path, но не расширяет утверждённый product scope.",
        "materiality": "MATERIAL",
        "options": ["PROTOTYPE", "ALPHA", "BETA", "MVP", "RELEASE", "UNSURE"],
        "unknown_note": "UNSURE — состояние решения, а не уровень; до planning требуется подтвердить canonical value.",
    },
    {
        "id": "QST-IMPLEMENTATION-CLAIMED-001",
        "field": "implementation.claimed_current_level",
        "text": "Какой уровень реализации вы считаете текущим?",
        "why_asked": "Для brownfield/hybrid это только пользовательская claim; assessment хранит observed и accepted maturity отдельно.",
        "materiality": "MATERIAL",
        "options": ["PROTOTYPE", "ALPHA", "BETA", "MVP", "RELEASE", "UNKNOWN"],
        "applies_to_modes": ["BROWNFIELD", "HYBRID"],
    },
    {
        "id": "QST-USERS-001",
        "field": "project.users",
        "text": "Кто основные пользователи и какую задачу они решают?",
        "why_asked": "Пользователи влияют на интерфейсы, доступ, масштаб и критерии приёмки.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-SCALE-001",
        "field": "project.scale.initial",
        "text": "Какой ожидается первоначальный масштаб: пользователи, данные и частота операций?",
        "why_asked": "Масштаб ограничивает архитектурные и технологические решения.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-CONNECTIVITY-001",
        "field": "project.connectivity",
        "text": "Должна ли система работать без интернета?",
        "why_asked": "Ответ влияет на хранение, синхронизацию и внешние зависимости.",
        "materiality": "MATERIAL",
        "options": ["ONLINE_ONLY", "LIMITED_OFFLINE", "OFFLINE_FIRST", "UNKNOWN"],
    },
    {
        "id": "QST-PLATFORM-001",
        "field": "project.platforms",
        "text": "На каких платформах и в какой среде будет запускаться проект?",
        "why_asked": "Платформа определяет runtime, packaging и deployment baseline.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-DATA-001",
        "field": "project.data.sensitivity",
        "text": "Какие данные обрабатываются и насколько они чувствительны?",
        "why_asked": "Категория данных влияет на хранение, доступ, журналирование и ограничения.",
        "materiality": "MATERIAL",
        "options": ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "SECRET", "REGULATED", "UNKNOWN"],
        "unknown_note": "UNKNOWN — временный ответ; до handoff требуется определить класс или явно принять консервативный класс.",
    },
    {
        "id": "QST-INTEGRATIONS-001",
        "field": "project.integrations",
        "text": "Какие внешние системы, API или форматы необходимо интегрировать?",
        "why_asked": "Интеграции создают контракты, permissions и проверяемые зависимости.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-CONSTRAINTS-001",
        "field": "project.constraints",
        "text": "Какие технологии, условия или действия обязательны либо запрещены?",
        "why_asked": "Явные ограничения предотвращают скрытую смену стека или небезопасные решения.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-SUCCESS-001",
        "field": "project.success_criteria",
        "text": "По каким проверяемым критериям будет принято первое решение?",
        "why_asked": "Критерии становятся требованиями и Verification Profiles.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-SCOPE-001",
        "field": "project.scope",
        "text": "Что входит и что явно не входит в первую версию?",
        "why_asked": "Scope предотвращает неконтролируемое расширение Work Packages.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-ARCHITECTURE-001",
        "field": "architecture.summary",
        "text": "Какая архитектурная граница и основные компоненты предлагаются?",
        "why_asked": "Codex не должен самостоятельно перепроектировать material architecture.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-TECHNOLOGY-001",
        "field": "technology.selections",
        "text": "Какие технологии и версии принимаются как baseline?",
        "why_asked": "Stack должен быть принят до зависимого bootstrap и task compilation.",
        "materiality": "MATERIAL",
    },
    {
        "id": "QST-PLAN-001",
        "field": "planning.work_packages",
        "text": "На какие минимальные Work Packages и атомарные задачи разбивается первый результат?",
        "why_asked": "Handoff требует причинный DAG и одну текущую READY задачу.",
        "materiality": "MATERIAL",
    },
]

REQUIRED_NONEMPTY = [
    "project.name",
    "project.mode",
    "project.documentation.availability",
    "project.problem_statement",
    "project.primary_outcome",
    "implementation.target_level",
    "project.users",
    "project.scale.initial",
    "project.connectivity",
    "project.platforms",
    "project.deployment.target",
    "project.data.sensitivity",
    "project.success_criteria",
    "project.scope.in",
    "profile.ref",
    "architecture.summary",
    "architecture.style",
    "architecture.components",
    "technology.selections",
    "planning.work_packages",
]
REQUIRED_PRESENT = [
    "project.documentation.normative_sources",
    "project.integrations",
    "project.scope.out",
    "project.constraints.mandatory",
    "project.constraints.forbidden",
    "project.constraints.non_functional",
    "project.assumptions",
    "project.unknowns",
]


def approvals_for_mode(mode: str | None) -> list[str]:
    return BROWNFIELD_APPROVALS if str(mode or "").upper() in {"BROWNFIELD", "HYBRID"} else GREENFIELD_APPROVALS


def _approval_template() -> dict[str, Any]:
    return {"approved": False, "actor": None, "approved_at": None, "notes": None}


def project_input_template(name: str, mode: str, source_names: list[str]) -> dict[str, Any]:
    mode = mode.upper()
    if mode not in PROJECT_MODES:
        raise ValidationFailure("Unsupported project mode", mode)
    return {
        "schema_version": PROJECT_INPUT_SCHEMA_VERSION,
        "metadata": {
            "prepared_by": "BROWSER_GPT",
            "generated_at": None,
            "notes": "Fill semantic fields after documentation analysis and user interview.",
        },
        "project": {
            "name": name,
            "slug": slugify(name),
            "mode": mode,
            "documentation": {
                "availability": "PROVIDED" if source_names else None,
                "normative_sources": source_names,
                "notes": None,
            },
            "problem_statement": None,
            "primary_outcome": None,
            "users": [],
            "scale": {"initial": None, "growth": None},
            "connectivity": None,
            "platforms": [],
            "deployment": {"target": None, "environment": None},
            "data": {"categories": [], "sensitivity": None, "storage": None},
            "integrations": [],
            "scope": {"in": [], "out": []},
            "constraints": {"mandatory": [], "forbidden": [], "non_functional": []},
            "success_criteria": [],
            "assumptions": [],
            "unknowns": [],
            "ambiguity_mode": "PRAGMATIC",
        },
        "implementation": {
            "target_level": None,
            "claimed_current_level": "NONE" if mode == "GREENFIELD" else "UNKNOWN",
        },
        "execution": deepcopy(DEFAULT_EXECUTION_POLICY),
        "profile": {"ref": None, "rationale": None},
        "architecture": {
            "summary": None,
            "style": None,
            "components": [],
            "interfaces": [],
            "data_flow": [],
            "quality_attributes": [],
            "decisions": [],
            "risks": [],
        },
        "technology": {
            "selections": [],
            "build_commands": [],
            "test_commands": [],
            "lint_commands": [],
        },
        "skills": {
            "resolutions": [
                {
                    "workflow": "bounded implementation",
                    "action": "REUSE",
                    "skill_ref": "SKL-UNIVERSAL-IMPLEMENT@3",
                    "configuration": {},
                    "rationale": "Core implementation skill supplied by the distribution.",
                }
            ]
        },
        "planning": {"work_packages": []},
        "brownfield": {
            "baseline_summary": None,
            "known_defects": [],
            "known_gaps": [],
            "technical_debt": [],
            "documentation_conflicts": [],
        },
        "approvals": {key: _approval_template() for key in approvals_for_mode(mode)},
    }


def _has_path(value: dict[str, Any], dotted: str) -> bool:
    current: Any = value
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def missing_fields(value: dict[str, Any]) -> list[str]:
    missing = [path for path in REQUIRED_NONEMPTY if not nonempty(deep_get(value, path))]
    missing.extend(path for path in REQUIRED_PRESENT if not _has_path(value, path))
    for field in ("project.data.sensitivity", "project.connectivity", "project.documentation.availability"):
        if deep_get(value, field) == "UNKNOWN":
            missing.append(field)
    # An explicit unresolved material question is not a completed definition.
    # Strings and unclassified questions are conservative; only an explicit
    # blocking=False makes a recorded uncertainty non-blocking.
    unknowns = deep_get(value, "project.unknowns", [])
    if isinstance(unknowns, list) and any(
        isinstance(item, str) and bool(item.strip()) or
        isinstance(item, dict) and item.get("blocking") is not False
        for item in unknowns
    ):
        missing.append("project.unknowns")
    mode = str(deep_get(value, "project.mode", "")).upper()
    if mode in {"BROWNFIELD", "HYBRID"}:
        if not nonempty(deep_get(value, "brownfield.baseline_summary")):
            missing.append("brownfield.baseline_summary")
        if not nonempty(deep_get(value, "implementation.claimed_current_level")):
            missing.append("implementation.claimed_current_level")
    return unique_preserve(missing)


def questions_for(value: dict[str, Any]) -> list[dict[str, Any]]:
    missing = set(missing_fields(value))
    questions: list[dict[str, Any]] = []
    mode = str(deep_get(value, "project.mode", "")).upper()
    for question in QUESTION_BANK:
        applies_to_modes = question.get("applies_to_modes")
        if applies_to_modes and mode not in applies_to_modes:
            continue
        field = question["field"]
        current = deep_get(value, field)
        unresolved_decision = (
            (field in {"project.data.sensitivity", "project.connectivity", "project.documentation.availability"} and current == "UNKNOWN")
            or (field == "implementation.target_level" and current == "UNSURE")
        )
        should_include = (
            question["id"] == "QST-DOCUMENTATION-001"
            or field in missing
            or any(item.startswith(field + ".") for item in missing)
            or unresolved_decision
            or (field == "implementation.claimed_current_level" and mode in {"BROWNFIELD", "HYBRID"})
        )
        if should_include:
            q = deepcopy(question)
            q["current_value"] = current
            q["status"] = "OPEN" if unresolved_decision or field in missing or any(
                item.startswith(field + ".") for item in missing) or not nonempty(current) else "ANSWERED"
            questions.append(q)
    for index, unknown in enumerate(value.get("project", {}).get("unknowns") or []):
        if isinstance(unknown, dict) and unknown.get("blocking") is False:
            continue
        question_text = unknown if isinstance(unknown, str) else unknown.get("question") if isinstance(unknown, dict) else None
        if question_text:
            questions.append({"id": f"QST-UNKNOWN-{index + 1:03d}", "field": "project.unknowns",
                              "text": question_text, "why_asked": "Незакрытый material gap в черновике.",
                              "materiality": "MATERIAL", "current_value": unknown, "status": "OPEN"})
    return questions


def _walk_keys(value: Any, prefix: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            dotted = f"{prefix}.{key}" if prefix else str(key)
            yield dotted
            yield from _walk_keys(child, dotted)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_keys(child, f"{prefix}[{index}]")


def _task_key(task: dict[str, Any], wp_index: int, task_index: int) -> str:
    value = task.get("key") or task.get("id") or task.get("title")
    if not nonempty(value):
        return f"wp{wp_index}.task{task_index}"
    return str(value)


def _validate_dag(tasks: list[tuple[str, dict[str, Any]]]) -> list[str]:
    errors: list[str] = []
    keys = [key for key, _ in tasks]
    if len(set(keys)) != len(keys):
        errors.append("Task keys/IDs/titles must be unique across the plan")
        return errors
    known = set(keys)
    deps: dict[str, list[str]] = {}
    for key, task in tasks:
        raw = task.get("depends_on") or task.get("depends_on_tasks") or []
        dep_list = [str(item) for item in raw]
        unknown = [item for item in dep_list if item not in known]
        if unknown:
            errors.append(f"Task {key} has unknown dependencies: {unknown}")
        if key in dep_list:
            errors.append(f"Task {key} depends on itself")
        deps[key] = dep_list
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, trail: list[str]) -> None:
        if node in visiting:
            errors.append("Task dependency cycle: " + " -> ".join(trail + [node]))
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in deps.get(node, []):
            if dep in known:
                visit(dep, trail + [node])
        visiting.remove(node)
        visited.add(node)

    for key in keys:
        visit(key, [])
    return errors


def _schema_path() -> Path:
    return distribution_root() / "schemas/project_input.schema.json"


def load_project_input_schema() -> dict[str, Any]:
    path = _schema_path()
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationFailure("Cannot load PROJECT_INPUT schema", {"path": str(path), "error": str(exc)}) from exc
    if schema.get("$id") != PROJECT_INPUT_SCHEMA_ID:
        raise ValidationFailure("Unexpected PROJECT_INPUT schema id", schema.get("$id"))
    return schema


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _format_path(path: str) -> str:
    return path or "$"


def _schema_issue(path: str, keyword: str, message: str) -> dict[str, str]:
    return {"path": _format_path(path), "keyword": keyword, "message": message}


def _resolve_schema_ref(root_schema: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValidationFailure("Only internal PROJECT_INPUT schema refs are supported", ref)
    current: Any = root_schema
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise ValidationFailure("Broken PROJECT_INPUT schema ref", ref)
        current = current[token]
    if not isinstance(current, dict):
        raise ValidationFailure("PROJECT_INPUT schema ref does not resolve to an object", ref)
    return current


def _valid_datetime(value: str) -> bool:
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        datetime.fromisoformat(normalized)
        return "T" in value
    except ValueError:
        return False


def _validate_schema_node(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    *,
    path: str = "",
    relaxed: bool = False,
) -> list[dict[str, str]]:
    if "$ref" in schema:
        return _validate_schema_node(value, _resolve_schema_ref(root_schema, str(schema["$ref"])), root_schema, path=path, relaxed=relaxed)

    issues: list[dict[str, str]] = []

    if "oneOf" in schema:
        if relaxed and value is None:
            return issues
        variants = [
            _validate_schema_node(value, item, root_schema, path=path, relaxed=relaxed)
            for item in schema.get("oneOf") or []
        ]
        valid = [candidate for candidate in variants if not candidate]
        if len(valid) != 1:
            if not valid and variants:
                best = min(variants, key=len)
                issues.extend(best)
            issues.append(_schema_issue(path, "oneOf", "value does not match exactly one allowed shape"))
            return issues

    if "not" in schema:
        rejected = _validate_schema_node(value, schema["not"], root_schema, path=path, relaxed=relaxed)
        if not rejected:
            issues.append(_schema_issue(path, "not", "value matches a forbidden shape"))
    if "anyOf" in schema:
        variants = [
            _validate_schema_node(value, item, root_schema, path=path, relaxed=relaxed)
            for item in schema.get("anyOf") or []
        ]
        if not any(not candidate for candidate in variants):
            if variants:
                issues.extend(min(variants, key=len))
            issues.append(_schema_issue(path, "anyOf", "value does not match an allowed shape"))
            return issues

    expected_types = schema.get("type")
    if expected_types is not None:
        allowed_types = [expected_types] if isinstance(expected_types, str) else list(expected_types)
        if relaxed and value is None and "null" not in allowed_types:
            return issues
        if not any(_json_type_matches(value, str(expected)) for expected in allowed_types):
            issues.append(_schema_issue(path, "type", f"expected {allowed_types}, got {type(value).__name__}"))
            return issues

    if "const" in schema and value != schema["const"]:
        issues.append(_schema_issue(path, "const", f"expected constant {schema['const']!r}"))
    if "enum" in schema and value not in schema["enum"]:
        if not (relaxed and value is None):
            issues.append(_schema_issue(path, "enum", f"value {value!r} is not in the controlled set"))

    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        if not relaxed:
            for key in schema.get("required") or []:
                if key not in value:
                    child_path = f"{path}.{key}" if path else str(key)
                    issues.append(_schema_issue(child_path, "required", "required property is missing"))
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    child_path = f"{path}.{key}" if path else str(key)
                    issues.append(_schema_issue(child_path, "additionalProperties", "unknown property is not allowed"))
        for key, child_schema in properties.items():
            if key in value:
                child_path = f"{path}.{key}" if path else key
                issues.extend(_validate_schema_node(value[key], child_schema, root_schema, path=child_path, relaxed=relaxed))

    if isinstance(value, list):
        minimum = schema.get("minItems")
        if not relaxed and isinstance(minimum, int) and len(value) < minimum:
            issues.append(_schema_issue(path, "minItems", f"at least {minimum} item(s) required"))
        maximum = schema.get("maxItems")
        if isinstance(maximum, int) and len(value) > maximum:
            issues.append(_schema_issue(path, "maxItems", f"at most {maximum} item(s) allowed"))
        if schema.get("uniqueItems") and len({json.dumps(v,sort_keys=True,default=str) for v in value}) != len(value):
            issues.append(_schema_issue(path, "uniqueItems", "duplicate list item is not allowed"))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, child in enumerate(value):
                child_path = f"{path}[{index}]"
                issues.extend(_validate_schema_node(child, item_schema, root_schema, path=child_path, relaxed=relaxed))

    if isinstance(value, str):
        minimum = schema.get("minLength")
        if not relaxed and isinstance(minimum, int) and len(value) < minimum:
            issues.append(_schema_issue(path, "minLength", f"string must contain at least {minimum} character(s)"))
        maximum = schema.get("maxLength")
        if isinstance(maximum, int) and len(value) > maximum:
            issues.append(_schema_issue(path, "maxLength", f"string must be at most {maximum} characters"))
        pattern = schema.get("pattern")
        if pattern and value and re.search(str(pattern), value) is None:
            issues.append(_schema_issue(path, "pattern", f"value does not match {pattern}"))
        if schema.get("format") == "date-time" and value and not _valid_datetime(value):
            issues.append(_schema_issue(path, "format", "invalid date-time value"))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "maximum" in schema and value > schema["maximum"]:
            issues.append(_schema_issue(path, "maximum", f"value exceeds maximum {schema['maximum']}"))
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            issues.append(_schema_issue(path, "exclusiveMinimum", f"value must be greater than {schema['exclusiveMinimum']}"))
        if "minimum" in schema and value < schema["minimum"]:
            issues.append(_schema_issue(path, "minimum", f"value must be >= {schema['minimum']}"))
        if "maximum" in schema and value > schema["maximum"]:
            issues.append(_schema_issue(path, "maximum", f"value must be <= {schema['maximum']}"))

    for item in schema.get("allOf") or []:
        issues.extend(_validate_schema_node(value, item, root_schema, path=path, relaxed=relaxed))

    condition = schema.get("if")
    if isinstance(condition, dict):
        condition_issues = _validate_schema_node(value, condition, root_schema, path=path, relaxed=False)
        branch = schema.get("then") if not condition_issues else schema.get("else")
        if isinstance(branch, dict):
            issues.extend(_validate_schema_node(value, branch, root_schema, path=path, relaxed=relaxed))

    return issues


def project_input_schema_issues(value: Any, *, relaxed: bool = False) -> list[dict[str, str]]:
    schema = load_project_input_schema()
    return _validate_schema_node(value, schema, schema, relaxed=relaxed)


def _unknown_properties(value: Any) -> list[str]:
    return sorted({
        issue["path"]
        for issue in project_input_schema_issues(value, relaxed=True)
        if issue["keyword"] == "additionalProperties"
    })


def migrate_project_input(value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(value, dict):
        raise ValidationFailure("Project input must be an object")
    migrated = deepcopy(value)
    from_version = migrated.get("schema_version")
    actions: list[str] = []

    if from_version == 1:
        migrated["schema_version"] = 2
        actions.append("schema_version:1->2")
        mode = str(deep_get(migrated, "project.mode", "")).upper()
        approvals = migrated.get("approvals")
        if not isinstance(approvals, dict):
            approvals = {}
            migrated["approvals"] = approvals
        if mode in {"BROWNFIELD", "HYBRID"} and "brownfield_baseline" not in approvals:
            ordered: dict[str, Any] = {}
            for key, item in approvals.items():
                ordered[key] = item
                if key == "project_definition":
                    ordered["brownfield_baseline"] = _approval_template()
            if "brownfield_baseline" not in ordered:
                ordered["brownfield_baseline"] = _approval_template()
            migrated["approvals"] = ordered
            actions.append("approvals.brownfield_baseline:added-unapproved")
        from_intermediate = 2
    else:
        from_intermediate = from_version

    if from_intermediate == 2:
        mode = str(deep_get(migrated, "project.mode", "")).upper()
        implementation = migrated.get("implementation")
        if not isinstance(implementation, dict):
            implementation = {}
            migrated["implementation"] = implementation
        if "target_level" not in implementation:
            implementation["target_level"] = None
            actions.append("implementation.target_level:added-null")
        if "claimed_current_level" not in implementation:
            implementation["claimed_current_level"] = "NONE" if mode == "GREENFIELD" else "UNKNOWN"
            actions.append(
                "implementation.claimed_current_level:added-" + str(implementation["claimed_current_level"])
            )
        migrated["schema_version"] = 3
        actions.append("schema_version:2->3")
        from_intermediate = 3
    if from_intermediate == 3:
        # A v3 record cannot opt into execution: intake may already have
        # merged a v4 template that contributes the *exact* safe manual default.
        # Any other execution value in a v3 envelope must be rejected.
        if "execution" in migrated and migrated["execution"] != DEFAULT_EXECUTION_POLICY:
            raise ValidationFailure(
                "Legacy PROJECT_INPUT cannot opt into execution; review and resubmit as schema_version 4"
            )
        # v3 is a historical accepted format. Normalize to the manual default
        # in-memory only; never rewrite an accepted historical file.
        migrated["execution"] = deepcopy(DEFAULT_EXECUTION_POLICY)
        actions.append("execution:added-manual-default")
        migrated["schema_version"] = 4
        actions.append("schema_version:3->4")
    elif from_intermediate == PROJECT_INPUT_SCHEMA_VERSION:
        pass
    else:
        raise ValidationFailure(
            "Unsupported PROJECT_INPUT schema_version",
            {"actual": from_version, "supported": [1, 2, 3, PROJECT_INPUT_SCHEMA_VERSION]},
        )

    unknown = _unknown_properties(migrated)
    status = "MIGRATED" if actions else "NO_ACTION"
    report = {
        "migration_id": EXECUTION_POLICY_MIGRATION_ID if from_version in {3, 4} else PROJECT_INPUT_MIGRATION_ID,
        "execution_policy_migration_id": EXECUTION_POLICY_MIGRATION_ID if from_version in {1, 2, 3} else None,
        "predecessor_migration_id": LEGACY_PROJECT_INPUT_MIGRATION_ID if from_version == 1 else None,
        "status": status,
        "from_schema_version": from_version,
        "to_schema_version": PROJECT_INPUT_SCHEMA_VERSION,
        "actions": actions,
        "unknown_properties": unknown,
        "requires_manual_correction": bool(unknown),
    }
    return migrated, report


def _schema_issue_messages(issues: list[dict[str, str]]) -> list[str]:
    return [f"{item['path']}: {item['message']} [{item['keyword']}]" for item in issues]


def recommend_implementation_level(value: dict[str, Any]) -> dict[str, str]:
    """Provide a non-binding recommendation; it never changes target_level."""
    deployment = str(deep_get(value, "project.deployment.target", "") or "").lower()
    outcome = str(deep_get(value, "project.primary_outcome", "") or "").lower()
    text = f"{deployment} {outcome}"
    if any(token in text for token in ("production", "prod", "боев", "реальн")):
        level = "MVP"
        rationale = "Описание явно ориентировано на production/use by real users; требуется подтвердить Production MVP или выбрать иной уровень."
    elif any(token in text for token in ("pilot", "пилот", "customer trial", "ограниченн")):
        level = "BETA"
        rationale = "Описание похоже на ограниченный pilot; требуется подтвердить Beta или выбрать иной уровень."
    elif any(token in text for token in ("internal", "внутрен", "developer", "разработ")):
        level = "ALPHA"
        rationale = "Описание ориентировано на внутреннее использование; требуется подтвердить Alpha или выбрать иной уровень."
    else:
        level = "PROTOTYPE"
        rationale = "Недостаточно evidence для более высокой глубины; консервативная рекомендация — начать с Prototype и явно подтвердить target."
    return {"recommended_level": level, "rationale": rationale, "requires_confirmation": "true"}


def exact_execution_profile_bindings(project_root: Path, policy: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    """Read-only, exact path/ref/digest binding; no profile activation or CLI invocation.

    This accepts only project-local, revisioned profile records; it never
    falls back to latest/globs or distribution-level profile guesses.
    """
    problems = execution_policy_issues(policy)
    if problems:
        raise ValidationFailure("Unsafe execution policy", problems)
    empty = {"adapter": {"ref": None, "digest": None}, "sandbox": {"ref": None, "digest": None}}
    if policy["mode"] == "MANUAL_HANDOFF":
        return empty
    bindings: dict[str, dict[str, str | None]] = {}
    profiles: dict[str, dict[str, Any]] = {}
    for alias, kind, folder, prefix, schema_name in (
        ("adapter", "agent_adapter_profile", "ADAPTERS", "ADP", "executor_profile.schema.json"),
        ("sandbox", "sandbox_profile", "SANDBOXES", "SBX", "sandbox_profile.schema.json"),
    ):
        ref = policy[f"{alias}_profile_ref"]
        assert isinstance(ref, str)  # guaranteed by execution_policy_issues
        profile_id, number = ref.rsplit("@", 1)
        path = (project_root / ".harness" / "config" / folder / f"{profile_id}@{number}.yaml")
        # Untrusted directory components must never use symlink escapes.
        try:
            path.resolve(strict=True).relative_to(project_root.resolve(strict=True))
        except (ValueError, FileNotFoundError, OSError) as exc:
            raise ValidationFailure("Exact execution profile is missing or escapes project", ref) from exc
        if not path.is_file() or path.is_symlink():
            raise ValidationFailure("Execution profile must be a regular project-local record", ref)
        record = load_data(path)
        if not isinstance(record, dict):
            raise ValidationFailure("Invalid execution profile record", ref)
        schema = json.loads((distribution_root() / "schemas" / schema_name).read_text(encoding="utf-8"))
        issues = _validate_schema_node(record, schema, schema)
        if issues:
            raise ValidationFailure("Execution profile does not satisfy strict schema", {"ref": ref, "errors": issues})
        profile = record[kind]
        if profile["id"] != profile_id or type(profile["revision"]) is not int or profile["revision"] != int(number):
            raise ValidationFailure("Execution profile identity/revision mismatch", ref)
        if profile["status"] != "ACTIVE":
            raise ValidationFailure("Only ACTIVE execution profiles can be bound", {"ref": ref, "status": profile["status"]})
        profiles[alias] = profile
        bindings[alias] = {"ref": ref, "digest": "sha256:" + sha256_file(path)}
    # Match exact local ADP to exact SBX; none of these checks run a process.
    if profiles["adapter"]["sandbox_profile_ref"] != policy["sandbox_profile_ref"]:
        raise ValidationFailure("Adapter sandbox binding mismatch")
    if (policy["network_mode"] == "NONE" and profiles["sandbox"]["network_mode"] != "NONE"):
        raise ValidationFailure("Network policy cannot be widened by sandbox profile")
    return bindings


def execution_policy_issues(policy: Any) -> list[str]:
    """Fail closed on unsafe execution intent, independent of optional JSON-schema tooling."""
    if not isinstance(policy, dict):
        return ["execution must be an object"]
    errors: list[str] = []
    expected = set(DEFAULT_EXECUTION_POLICY)
    missing = expected - set(policy)
    extra = set(policy) - expected
    if missing:
        errors.append(f"execution missing required fields {sorted(missing)}")
    if extra:
        errors.append(f"execution unknown/forbidden fields {sorted(extra)}")
    mode = policy.get("mode")
    if mode not in {"MANUAL_HANDOFF", "LOCAL_AUTOMATIC"}:
        errors.append("execution.mode must be MANUAL_HANDOFF or LOCAL_AUTOMATIC")
    if policy.get("network_mode") not in {"NONE", "EXPLICIT_APPROVED_EGRESS"}:
        errors.append("execution.network_mode is not allowed")
    if policy.get("completion_policy") not in {"EXPLICIT_AFTER_VERIFICATION", "AUTO_AFTER_PASS"}:
        errors.append("execution.completion_policy is not allowed")
    for name, prefix in (("adapter_profile_ref", "ADP"), ("sandbox_profile_ref", "SBX")):
        ref = policy.get(name)
        if ref is not None and (not isinstance(ref, str) or re.fullmatch(
                rf"{prefix}-[A-Z0-9][A-Z0-9-]*@[1-9][0-9]*", ref) is None):
            errors.append(f"execution.{name} must be an exact revisioned {prefix} ref or null")
    if mode == "MANUAL_HANDOFF":
        for name, value in DEFAULT_EXECUTION_POLICY.items():
            if policy.get(name) != value:
                errors.append(f"execution.{name} cannot override the safe manual default")
    elif mode == "LOCAL_AUTOMATIC":
        for name in ("adapter_profile_ref", "sandbox_profile_ref"):
            if not isinstance(policy.get(name), str) or not policy[name]:
                errors.append(f"execution.{name} is mandatory for LOCAL_AUTOMATIC")
    return errors


def validate_project_input(value: Any, *, require_approvals: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationFailure("Project input must be an object")
    errors: list[str] = []
    warnings: list[str] = []
    try:
        candidate, migration = migrate_project_input(value)
    except ValidationFailure as exc:
        return {
            "status": "INVALID",
            "missing_fields": [],
            "missing_approvals": [],
            "errors": [exc.message],
            "warnings": [],
            "schema_errors": [],
            "migration": {"migration_id": PROJECT_INPUT_MIGRATION_ID, "status": "FAILED", "details": exc.details},
            "task_count": 0,
            "work_package_count": 0,
        }

    schema_issues = project_input_schema_issues(candidate, relaxed=True)
    errors.extend(_schema_issue_messages(schema_issues))
    errors.extend(execution_policy_issues(candidate.get("execution")))
    missing = missing_fields(candidate)

    mode = str(deep_get(candidate, "project.mode", "")).upper()
    docs = deep_get(candidate, "project.documentation.availability")
    connectivity = deep_get(candidate, "project.connectivity")
    sensitivity = deep_get(candidate, "project.data.sensitivity")
    ambiguity = deep_get(candidate, "project.ambiguity_mode")
    # The strict schema already checks these values. These semantic messages remain
    # explicit for callers that render readiness without examining schema keywords.
    if mode and mode not in PROJECT_MODES:
        errors.append(f"project.mode must be one of {sorted(PROJECT_MODES)}")
    if docs and docs not in DOCUMENTATION_AVAILABILITY:
        errors.append(f"documentation availability must be one of {sorted(DOCUMENTATION_AVAILABILITY)}")
    if connectivity and connectivity not in CONNECTIVITY:
        errors.append(f"project.connectivity must be one of {sorted(CONNECTIVITY)}")
    if sensitivity and sensitivity not in INPUT_SENSITIVITY_VALUES:
        errors.append(f"project.data.sensitivity must be one of {sorted(INPUT_SENSITIVITY_VALUES)}")
    if ambiguity and ambiguity not in AMBIGUITY_MODES:
        errors.append(f"project.ambiguity_mode must be one of {sorted(AMBIGUITY_MODES)}")

    target_level = deep_get(candidate, "implementation.target_level")
    claimed_level = deep_get(candidate, "implementation.claimed_current_level")
    if target_level is not None and target_level not in TARGET_IMPLEMENTATION_INPUT_VALUES:
        errors.append(
            f"implementation.target_level must be one of {list(CANONICAL_IMPLEMENTATION_LEVELS)} or UNSURE during intake"
        )
    if claimed_level is not None and claimed_level not in CLAIMED_IMPLEMENTATION_INPUT_VALUES:
        errors.append(
            f"implementation.claimed_current_level must be one of {sorted(CLAIMED_IMPLEMENTATION_INPUT_VALUES)}"
        )
    if mode == "GREENFIELD" and claimed_level not in {None, "NONE"}:
        errors.append("Greenfield implementation.claimed_current_level must be NONE")
    if mode in {"BROWNFIELD", "HYBRID"} and claimed_level == "NONE":
        errors.append("Brownfield/Hybrid claimed_current_level cannot be NONE; use UNKNOWN when not known")
    try:
        registry_levels = tuple(implementation_level_model(registries=None)["order"])
        if registry_levels != CANONICAL_IMPLEMENTATION_LEVELS:
            errors.append(f"Implementation level registry order mismatch: {registry_levels}")
    except ValidationFailure as exc:
        errors.append(f"Implementation level registry invalid: {exc.message}")
    if sensitivity == "UNKNOWN":
        warnings.append(
            "project.data.sensitivity=UNKNOWN is a temporary epistemic state; choose a canonical class before handoff"
        )

    registries = load_registries()
    profile = deep_get(candidate, "profile.ref")
    profiles = known_profiles(registries)
    if profile and profile not in profiles:
        errors.append(f"Unknown profile.ref {profile}; allowed={sorted(profiles)}")

    capability_values = allowed_capabilities(registries)
    resolutions = deep_get(candidate, "skills.resolutions", []) or []
    if not isinstance(resolutions, list) or not resolutions:
        errors.append("At least one skill resolution is required")
    else:
        for index, resolution in enumerate(resolutions):
            if not isinstance(resolution, dict):
                errors.append(f"skills.resolutions[{index}] must be an object")
                continue
            action = resolution.get("action")
            if action not in SKILL_ACTIONS:
                errors.append(
                    f"skills.resolutions[{index}].action must be one of {sorted(SKILL_ACTIONS)}; "
                    "CREATE/EXTEND authoring is outside the Core runtime"
                )
            if action != "TASK_ONLY" and not nonempty(resolution.get("skill_ref")):
                errors.append(f"skills.resolutions[{index}].skill_ref is required")

    work_packages = deep_get(candidate, "planning.work_packages", []) or []
    tasks: list[tuple[str, dict[str, Any]]] = []
    if work_packages and not isinstance(work_packages, list):
        errors.append("planning.work_packages must be a list")
        work_packages = []
    for wp_index, wp in enumerate(work_packages, 1):
        if not isinstance(wp, dict):
            errors.append(f"work_packages[{wp_index}] must be an object")
            continue
        for field in ("title", "objective", "tasks"):
            if not nonempty(wp.get(field)):
                errors.append(f"work_packages[{wp_index}].{field} is required")
        raw_tasks = wp.get("tasks") or []
        if not isinstance(raw_tasks, list):
            errors.append(f"work_packages[{wp_index}].tasks must be a list")
            continue
        for task_index, task in enumerate(raw_tasks, 1):
            if not isinstance(task, dict):
                errors.append(f"work_packages[{wp_index}].tasks[{task_index}] must be an object")
                continue
            key = _task_key(task, wp_index, task_index)
            tasks.append((key, task))
            for field in ("title", "type", "purpose", "expected_result", "scope", "acceptance_criteria", "verification"):
                if not nonempty(task.get(field)):
                    errors.append(f"Task {key}: {field} is required")
            task_type = str(task.get("type", "")).upper()
            if task_type and task_type not in TASK_TYPES:
                errors.append(f"Task {key}: type must be one of {sorted(TASK_TYPES)}")
            scope = task.get("scope") or {}
            if not isinstance(scope, dict):
                errors.append(f"Task {key}: scope must be an object")
            else:
                for group in ("read", "write", "forbidden"):
                    items = scope.get(group, [])
                    if not isinstance(items, list):
                        errors.append(f"Task {key}: scope.{group} must be a list")
                        continue
                    for pattern in items:
                        try:
                            ensure_relative_pattern(str(pattern), field=f"scope.{group}")
                        except Exception as exc:
                            errors.append(f"Task {key}: {exc}")
                if task_type not in {"VERIFY"} and not scope.get("write"):
                    errors.append(f"Task {key}: non-VERIFY task needs a declared write scope")
            route = task.get("route") or {}
            if not isinstance(route, dict):
                errors.append(f"Task {key}: route must be an object")
                route = {}
            required_caps = route.get("required_capabilities") or []
            if not isinstance(required_caps, list):
                errors.append(f"Task {key}: route.required_capabilities must be a list")
                required_caps = []
            unknown_caps = [cap for cap in required_caps if cap not in capability_values]
            if unknown_caps:
                errors.append(f"Task {key}: unknown capabilities {unknown_caps}")
            verification = task.get("verification") or {}
            if not isinstance(verification, dict):
                errors.append(f"Task {key}: verification must be an object")
            elif not (
                verification.get("commands")
                or verification.get("expected_paths")
                or verification.get("manual_checks")
            ):
                errors.append(f"Task {key}: verification needs commands, expected_paths, or manual_checks")

    errors.extend(_validate_dag(tasks))
    if work_packages and not tasks:
        errors.append("At least one atomic task is required")

    for key_path in _walk_keys(candidate):
        leaf = key_path.rsplit(".", 1)[-1]
        leaf = re.sub(r"^.*\]", "", leaf)
        if leaf in FORBIDDEN_ACCOUNTING_KEYS:
            errors.append(f"Forbidden provider accounting field: {key_path}")

    approvals_missing: list[str] = []
    for key in approvals_for_mode(mode):
        item = deep_get(candidate, f"approvals.{key}")
        if not isinstance(item, dict) or item.get("approved") is not True:
            approvals_missing.append(key)
        else:
            if not nonempty(item.get("actor")):
                errors.append(f"approvals.{key}.actor is required when approved")
            if not nonempty(item.get("approved_at")):
                errors.append(f"approvals.{key}.approved_at is required when approved")

    if require_approvals and approvals_missing:
        warnings.append("Explicit approvals are still required: " + ", ".join(approvals_missing))

    errors = unique_preserve(errors)
    warnings = unique_preserve(warnings)
    recommendation = recommend_implementation_level(candidate) if target_level == "UNSURE" else None
    status = "READY_FOR_HANDOFF"
    if errors:
        status = "INVALID"
    elif target_level == "UNSURE":
        status = "WAITING_DECISION"
    elif missing:
        status = "WAITING_INPUT"
    elif target_level not in CANONICAL_IMPLEMENTATION_LEVELS:
        status = "WAITING_INPUT"
    elif require_approvals and approvals_missing:
        status = "WAITING_DECISION"
    return {
        "status": status,
        "schema_id": PROJECT_INPUT_SCHEMA_ID,
        "schema_version": PROJECT_INPUT_SCHEMA_VERSION,
        "missing_fields": missing,
        "missing_approvals": approvals_missing,
        "errors": errors,
        "warnings": warnings,
        "implementation_recommendation": recommendation,
        "schema_errors": schema_issues,
        "migration": migration,
        "task_count": len(tasks),
        "work_package_count": len(work_packages) if isinstance(work_packages, list) else 0,
    }

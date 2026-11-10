from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
from typing import Any, Iterable

from .operation_guard import guarded_mutation
from .errors import SafetyViolation, ValidationFailure
from .inventory import build_repository_inventory, build_source_inventory
from .project_input import (
    migrate_project_input,
    project_input_template,
    questions_for,
    validate_project_input,
)
from .safety import inspect_zip, repository_source_to_directory
from .serialization import load_data, write_data, atomic_write_text
from .util import id_token, slugify, utc_now
from .platform_fs import ensure_native_path, _native_io_path, native_resolve, native_iterdir


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def _copy_source(path: Path, destination: Path) -> Path:
    path = native_resolve(path.expanduser())
    _native_io_path(destination.parent).mkdir(parents=True, exist_ok=True)
    if _native_io_path(path).is_dir():
        if _native_io_path(destination).exists():
            shutil.rmtree(_native_io_path(destination))
        shutil.copytree(
            _native_io_path(path),
            _native_io_path(destination),
            symlinks=False,
            ignore=shutil.ignore_patterns(".git", ".harness", "node_modules", ".venv", "__pycache__"),
        )
    else:
        shutil.copy2(_native_io_path(path), _native_io_path(destination))
    return destination


def _questions_markdown(questions: list[dict[str, Any]], readiness: dict[str, Any]) -> str:
    lines = [
        "# Стартовые вопросы Project Harness",
        "",
        "Первый вопрос всегда относится к документации. Browser GPT должен сначала проанализировать доступные материалы, затем не повторять уже достоверно отвеченные вопросы.",
        "",
        f"Текущий статус: **{readiness['status']}**",
        "",
    ]
    open_questions = [q for q in questions if q.get("status") == "OPEN"]
    for index, q in enumerate(questions, 1):
        lines.extend(
            [
                f"## {index}. {q['text']}",
                "",
                f"- ID: `{q['id']}`",
                f"- Поле: `{q['field']}`",
                f"- Почему важно: {q['why_asked']}",
                f"- Материальность: `{q['materiality']}`",
                f"- Статус: `{q['status']}`",
            ]
        )
        if q.get("options"):
            lines.append("- Варианты: " + ", ".join(f"`{item}`" for item in q["options"]))
        if q.get("unknown_note"):
            lines.append(f"- Примечание: {q['unknown_note']}")
        if q.get("current_value") not in (None, "", [], {}):
            lines.append(f"- Текущее значение: `{q['current_value']}`")
        lines.append("")
    lines.extend(
        [
            "## Правило завершения",
            "",
            f"Открытых вопросов: **{len(open_questions)}**.",
            "После заполнения `PROJECT_INPUT.yaml` выполните `check-intake`. Material approvals задаются отдельно и не выводятся автоматически из ответов.",
            "Для Brownfield/Hybrid требуется отдельное подтверждение `approvals.brownfield_baseline` между Project Definition и Architecture/Technology gates.",
            "",
        ]
    )
    return "\n".join(lines)


@guarded_mutation
def start_intake(
    workspace: Path,
    *,
    project_name: str,
    mode: str,
    sources: Iterable[Path] = (),
    repository: Path | None = None,
    initial_input: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    sources = tuple(sources)
    ensure_native_path(workspace, tree=True)
    for candidate in sources:
        ensure_native_path(candidate, tree=True, file_ok=True)
    if initial_input:
        ensure_native_path(initial_input, file_ok=True)
    if repository:
        ensure_native_path(repository, tree=True, file_ok=True)
    workspace = native_resolve(workspace.expanduser())
    mode = mode.upper()
    source_paths = [native_resolve(Path(item).expanduser()) for item in sources]
    initial_input_path = native_resolve(initial_input.expanduser()) if initial_input else None
    # Intake is an external workspace. Never erase a supplied source or recursively
    # copy a workspace into itself (including through a parent directory).
    protected_paths = [*source_paths, *([initial_input_path] if initial_input_path else [])]
    if repository is not None:
        protected_paths.append(native_resolve(repository.expanduser()))
    for protected in protected_paths:
        if protected == workspace or workspace in protected.parents or protected in workspace.parents:
            raise SafetyViolation(
                "Intake workspace must be disjoint from sources, initial input and repository",
                {"workspace": str(workspace), "protected": str(protected)},
            )
    if mode not in {"GREENFIELD", "BROWNFIELD", "HYBRID"}:
        raise ValidationFailure("Unsupported project mode", mode)
    if mode in {"BROWNFIELD", "HYBRID"} and repository is None:
        raise ValidationFailure("Brownfield/Hybrid intake requires --repository")
    if repository is not None:
        repository = native_resolve(repository.expanduser())
        # A provisional workspace must not be placed inside a directory repository.
        # A ZIP repository is an immutable file, so a sibling workspace is safe and
        # is the normal browser-upload layout.
        if _native_io_path(repository).is_dir():
            try:
                workspace.relative_to(repository)
            except ValueError:
                pass
            else:
                raise SafetyViolation(
                    "Provisional intake workspace must be outside the target repository",
                    {"workspace": str(workspace), "repository": str(repository)},
                )
    # Inspect portable ZIP names/CRC before creating or --force deleting the
    # workspace. Windows reserved names and case aliases must fail pre-write.
    for candidate in [*source_paths, *([repository] if repository is not None else [])]:
        if _native_io_path(candidate).is_file() and candidate.suffix.lower() == '.zip':
            inspect_zip(candidate)
    if _native_io_path(workspace).exists() and any(native_iterdir(workspace)) and not force:
        project_input_path = workspace / "PROJECT_INPUT.yaml"
        if _native_io_path(project_input_path).exists():
            return check_intake(workspace)
        raise ValidationFailure("Workspace is not empty; use --force to replace it", str(workspace))
    if force and _native_io_path(workspace).exists():
        shutil.rmtree(_native_io_path(workspace))
    _native_io_path(workspace).mkdir(parents=True, exist_ok=True)

    token = id_token(slugify(project_name))
    session_ref = f"SES-{token}-001"
    questionnaire_ref = f"QNS-{token}-001"
    created_at = utc_now()

    copied_sources: list[Path] = []
    source_dir = workspace / "sources"
    for index, source in enumerate(source_paths, 1):
        if not _native_io_path(source).exists():
            raise ValidationFailure("Project source does not exist", str(source))
        copied_sources.append(_copy_source(source, source_dir / f"{index:03d}-{source.name}"))
    source_inventory = build_source_inventory(copied_sources, session_ref=session_ref)
    write_data(workspace / "SOURCE_INVENTORY.yaml", source_inventory)

    effective_repository: Path | None = None
    repository_inventory: dict[str, Any] | None = None
    if repository is not None:
        effective_repository = repository_source_to_directory(repository, workspace / ".cache")
        repository_inventory = build_repository_inventory(effective_repository, session_ref=session_ref)
        write_data(workspace / "REPOSITORY_INVENTORY.yaml", repository_inventory)

    template = project_input_template(
        project_name,
        mode,
        [path.name for path in copied_sources],
    )
    if initial_input:
        loaded = load_data(native_resolve(initial_input.expanduser()))
        if not isinstance(loaded, dict):
            raise ValidationFailure("Initial input must be an object")
        template = _deep_merge(template, loaded)
    template["project"]["name"] = project_name
    template["project"]["slug"] = slugify(project_name)
    template["project"]["mode"] = mode
    template, migration = migrate_project_input(template)
    write_data(workspace / "PROJECT_INPUT.yaml", template)
    write_data(workspace / "MIGRATION_REPORT.json", {"migration_report": migration})

    readiness = validate_project_input(template, require_approvals=True)
    questions = questions_for(template)
    write_data(
        workspace / "QUESTIONS.yaml",
        {
            "questionnaire_session": questionnaire_ref,
            "question_budget": {"target": 10, "hard_limit_before_draft": 15, "asked": len(questions)},
            "questions": questions,
        },
    )
    atomic_write_text(workspace / "QUESTIONS.md", _questions_markdown(questions, readiness))
    write_data(workspace / "READINESS.json", readiness)
    session = {
        "session": {
            "id": session_ref,
            "revision": 1,
            "mode": mode,
            "status": readiness["status"],
            "created_at": created_at,
            "updated_at": created_at,
            "provisional_workspace": str(workspace),
            "source_inventory_ref": source_inventory["source_inventory"]["id"],
            "questionnaire_session_ref": questionnaire_ref,
            "repository_ref": str(repository) if repository else None,
        }
    }
    write_data(workspace / "SESSION.yaml", session)
    write_data(
        workspace / "STATE.yaml",
        {
            "state": {
                "status": readiness["status"],
                "session_ref": session_ref,
                "questionnaire_ref": questionnaire_ref,
                "project_input": str(workspace / "PROJECT_INPUT.yaml"),
                "source_paths": [str(path) for path in copied_sources],
                "repository_source": str(repository) if repository else None,
                "effective_repository_path": str(effective_repository) if effective_repository else None,
                "repository_tree_digest": (
                    repository_inventory["repository_inventory"]["tree_digest"]
                    if repository_inventory
                    else None
                ),
                "next_route": {
                    "WAITING_INPUT": "ANSWER_QUESTIONS",
                    "WAITING_DECISION": "APPROVE_BASELINES",
                    "READY_FOR_HANDOFF": "PREPARE_CODEX_HANDOFF",
                    "INVALID": "FIX_INPUT",
                }.get(readiness["status"], "FIX_INPUT"),
                "updated_at": created_at,
            }
        },
    )
    return {
        "status": readiness["status"],
        "workspace": str(workspace),
        "session_ref": session_ref,
        "questions_path": str(workspace / "QUESTIONS.md"),
        "project_input_path": str(workspace / "PROJECT_INPUT.yaml"),
        "readiness": readiness,
    }


@guarded_mutation
def check_intake(workspace: Path) -> dict[str, Any]:
    ensure_native_path(workspace, tree=True)
    workspace = native_resolve(workspace.expanduser())
    input_path = workspace / "PROJECT_INPUT.yaml"
    if not _native_io_path(input_path).exists():
        raise ValidationFailure("Not an intake workspace", str(workspace))
    value = load_data(input_path)
    value, migration = migrate_project_input(value)
    write_data(input_path, value)
    write_data(workspace / "MIGRATION_REPORT.json", {"migration_report": migration})
    readiness = validate_project_input(value, require_approvals=True)
    questions = questions_for(value)
    write_data(
        workspace / "QUESTIONS.yaml",
        {
            "questionnaire_session": load_data(workspace / "STATE.yaml")["state"]["questionnaire_ref"],
            "question_budget": {"target": 10, "hard_limit_before_draft": 15, "asked": len(questions)},
            "questions": questions,
        },
    )
    atomic_write_text(workspace / "QUESTIONS.md", _questions_markdown(questions, readiness))
    write_data(workspace / "READINESS.json", readiness)
    state_path = workspace / "STATE.yaml"
    state = load_data(state_path)
    state["state"]["status"] = readiness["status"]
    state["state"]["next_route"] = {
        "WAITING_INPUT": "ANSWER_QUESTIONS",
        "WAITING_DECISION": "APPROVE_BASELINES",
        "READY_FOR_HANDOFF": "PREPARE_CODEX_HANDOFF",
        "INVALID": "FIX_INPUT",
    }.get(readiness["status"], "FIX_INPUT")
    state["state"]["updated_at"] = utc_now()
    write_data(state_path, state)
    session_path = workspace / "SESSION.yaml"
    session = load_data(session_path)
    session["session"]["status"] = readiness["status"]
    session["session"]["updated_at"] = state["state"]["updated_at"]
    write_data(session_path, session)
    return {
        "status": readiness["status"],
        "workspace": str(workspace),
        "questions_path": str(workspace / "QUESTIONS.md"),
        "project_input_path": str(input_path),
        "readiness": readiness,
    }


@guarded_mutation
def refresh_intake_sources(workspace: Path, *, snapshot_ref: str | None,
                           expected_revision: int, expected_input_digest: str,
                           explicit_no_documentation: bool = False) -> dict[str, Any]:
    """PH-LW-05 public API: revision-bound, recoverable intake source refresh.

    Does not call start_intake(force=True), create approvals or modify an
    accepted Project Instance.  Imported files stay inert source materials.
    """
    from .local_web_source_refresh import refresh_intake_sources as _refresh
    return _refresh(workspace, snapshot_ref=snapshot_ref,
                    expected_revision=expected_revision, expected_input_digest=expected_input_digest,
                    explicit_no_documentation=explicit_no_documentation)

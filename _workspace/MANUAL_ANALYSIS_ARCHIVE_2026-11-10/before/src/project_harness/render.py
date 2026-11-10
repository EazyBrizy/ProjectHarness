from __future__ import annotations

from pathlib import Path
from typing import Any

from .serialization import atomic_write_text, load_data
from .stages import STAGE_PLAN_INDEX_PATH, load_current_target_level, load_stage_state


def _bullets(items: list[Any], *, empty: str = "Нет") -> str:
    if not items:
        return f"- {empty}"
    lines: list[str] = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("statement") or item.get("name") or item.get("title") or str(item)
        else:
            text = str(item)
        lines.append(f"- {text}")
    return "\n".join(lines)


def render_project_summary(root: Path, project_input: dict[str, Any] | None = None) -> None:
    """Render the human project summary with explicit historical/current targets."""
    root = root.expanduser().resolve()
    if project_input is None:
        project_input = load_data(root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml")
    project = project_input["project"]
    profile = project_input["profile"]
    initial_implementation = project_input["implementation"]
    implementation = load_stage_state(root)
    current_target = load_current_target_level(root, stage_state=implementation)

    project_md = f"""# {project['name']}

## Принятая цель

{project['problem_statement']}

## Первый проверяемый результат

{project['primary_outcome']}

## Профиль

`{profile['ref']}` — {profile.get('rationale') or 'принят пользователем'}

## Уровень реализации

- Current Stage: `{implementation['active_stage']}`
- Current Target Level: `{current_target}`
- Initial Accepted Target Level: `{initial_implementation['target_level']}`
- Claimed Current Level: `{implementation['claimed_current_level']}`
- Canonical current target: `.harness/stages/STAGE_STATE.yaml`; initial accepted target remains historical in `.harness/state/PROJECT_INPUT_ACCEPTED.yaml`.
- Правило: уровень меняет глубину реализации и проверки, но не расширяет принятый product scope.

## Пользователи

{_bullets(project.get('users') or [])}

## В scope

{_bullets(project['scope'].get('in') or [])}

## Вне scope

{_bullets(project['scope'].get('out') or [])}

## Критерии успеха

{_bullets(project.get('success_criteria') or [])}

## Ограничения

### Обязательные

{_bullets(project['constraints'].get('mandatory') or [])}

### Запрещённые

{_bullets(project['constraints'].get('forbidden') or [])}

### Нефункциональные

{_bullets(project['constraints'].get('non_functional') or [])}

## Допущения

{_bullets(project.get('assumptions') or [])}

## Неизвестные

{_bullets(project.get('unknowns') or [])}
"""
    atomic_write_text(root / "PROJECT.md", project_md)


def render_project_documents(root: Path, project_input: dict[str, Any], plan: dict[str, Any]) -> None:
    architecture = project_input["architecture"]
    technology = project_input["technology"]

    architecture_md = f"""# Architecture Baseline

**Статус:** ACCEPTED

## Summary

{architecture['summary']}

## Style

{architecture['style']}

## Components

{_bullets(architecture.get('components') or [])}

## Interfaces

{_bullets(architecture.get('interfaces') or [])}

## Data flow

{_bullets(architecture.get('data_flow') or [])}

## Quality attributes

{_bullets(architecture.get('quality_attributes') or [])}

## Material decisions

{_bullets(architecture.get('decisions') or [])}

## Risks

{_bullets(architecture.get('risks') or [])}
"""
    selections = []
    for item in technology.get("selections") or []:
        selections.append(
            f"- **{item.get('area', 'TECHNOLOGY')}**: {item.get('technology')} "
            f"{item.get('version_constraint') or ''} — {item.get('rationale') or ''}".rstrip()
        )
    technology_md = f"""# Technology Baseline

**Статус:** ACCEPTED

## Selections

{chr(10).join(selections) if selections else '- Нет'}

## Build commands

{_command_bullets(technology.get('build_commands') or [])}

## Test commands

{_command_bullets(technology.get('test_commands') or [])}

## Lint commands

{_command_bullets(technology.get('lint_commands') or [])}
"""
    render_project_summary(root, project_input)
    atomic_write_text(root / "ARCHITECTURE.md", architecture_md)
    atomic_write_text(root / "TECHNOLOGY.md", technology_md)
    render_roadmap(root, plan)


def _command_bullets(commands: list[Any]) -> str:
    if not commands:
        return "- Нет"
    output = []
    for command in commands:
        if isinstance(command, dict):
            argv = command.get("argv") or command.get("command")
        else:
            argv = command
        if isinstance(argv, list):
            text = " ".join(str(item) for item in argv)
        else:
            text = str(argv)
        output.append(f"- `{text}`")
    return "\n".join(output)


def render_roadmap(root: Path, plan: dict[str, Any] | None = None) -> None:
    if plan is None:
        index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
        wp_index = load_data(root / ".harness/work-packages/INDEX.yaml")["work_package_index"]
        work_packages: list[dict[str, Any]] = []
        for wp_id in wp_index["order"]:
            wp_path = root / wp_index["current"][wp_id]
            wp = load_data(wp_path)["work_package"]
            wp["tasks"] = []
            for task_id in wp.get("mandatory_task_refs", []):
                task_path = root / index["current"][task_id]
                wp["tasks"].append(load_data(task_path)["task"])
            work_packages.append(wp)
    else:
        work_packages = plan["work_packages"]
    implementation = load_stage_state(root)
    current_target = load_current_target_level(root, stage_state=implementation)
    lines = [
        "# Roadmap",
        "",
        f"- Current Stage: `{implementation['active_stage']}`",
        f"- Target Level: `{current_target}`",
        f"- Highest Accepted Level: `{implementation['highest_accepted_level']}`",
        "",
        "Harness Core использует один активный task; зависимости остаются причинным DAG. Атомарная работа разрешена только для Current Stage.",
        "",
        "## Active-stage detailed work",
        "",
    ]
    for wp in work_packages:
        lines.extend([f"### {wp['id']} — {wp['title']}", "", f"**Stage:** `{wp.get('implementation_stage', implementation['active_stage'])}`", f"**Статус:** `{wp.get('status', 'PLANNED')}`", "", wp["objective"], ""])
        for task in wp.get("tasks") or []:
            deps = ", ".join(task.get("depends_on_tasks") or []) or "нет"
            lines.extend(
                [
                    f"- `{task['id']}` — **{task.get('status', 'PLANNED')}** — {task['title']}",
                    f"  - depends on: {deps}",
                    f"  - expected: {task['expected_result']}",
                ]
            )
        lines.append("")
    plan_index_path = root / STAGE_PLAN_INDEX_PATH
    if plan_index_path.exists():
        stage_index = load_data(plan_index_path).get("stage_plan_index") or {}
        lines.extend(["## Deferred work", "", "Future Stage Plans are outlines only and are recomputed after the previous Stage is accepted.", ""])
        for stage_id in stage_index.get("order") or []:
            rel = (stage_index.get("current") or {}).get(stage_id)
            if not rel:
                continue
            stage = load_data(root / rel).get("stage_plan") or {}
            if stage.get("level") == implementation["active_stage"]:
                continue
            lines.extend(
                [
                    f"### {stage.get('level')} — `{stage.get('status')}`",
                    "",
                    *[f"- {item.get('title')}: {item.get('outcome')}" for item in stage.get("work_package_outlines") or []],
                    *[f"- Deferred: {item}" for item in stage.get("deferred_to_next_stage") or []],
                    "",
                ]
            )
    atomic_write_text(root / "ROADMAP.md", "\n".join(lines).rstrip() + "\n")


def render_status(root: Path) -> None:
    state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
    implementation = load_stage_state(root)
    current_target = load_current_target_level(root, stage_state=implementation)
    next_task = state.get("current_task_ref")
    active_run = state.get("active_run") or {}
    lines = [
        "# Project Harness Status",
        "",
        f"- Project status: `{state.get('project_status')}`",
        f"- Handoff status: `{state.get('handoff_status')}`",
        f"- Current Stage: `{implementation.get('active_stage')}`",
        f"- Target Level: `{current_target}`",
        f"- Highest Accepted Level: `{implementation.get('highest_accepted_level')}`",
        f"- Observed Candidate Level: `{implementation.get('observed_candidate_level')}`",
        f"- Permitted Use: `{(implementation.get('permitted_use') or {}).get('status', 'UNCONFIRMED')}`",
        f"- Current task: `{next_task or 'NONE'}`",
        f"- Active run: `{active_run.get('run_ref') or 'NONE'}`",
        f"- Next route: `{state.get('next_route')}`",
        f"- Completed tasks: {len(state.get('completed_task_refs') or [])}",
        f"- Blocked tasks: {len(state.get('blocked_task_refs') or [])}",
        "",
        "Machine state: `.harness/state/CURRENT_STATE.yaml`.",
    ]
    atomic_write_text(root / "STATUS.md", "\n".join(lines) + "\n")

from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ValidationFailure
from .hashing import sha256_bytes
from .maintenance import MAINTENANCE_ROUTE, execution_stage
from .project_input import PROJECT_INPUT_MIGRATION_ID
from .render import render_status
from .serialization import canonical_json_bytes, load_data, write_data, atomic_write_text
from .stages import load_stage_state
from .util import ENGINE_VERSION, SCHEMA_VERSION, utc_now
from .workspace import record_phase_boundary, write_snapshot


def _load_task(root: Path, task_id: str) -> tuple[dict[str, Any], str]:
    index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
    rel = index["current"].get(task_id)
    if not rel:
        raise ValidationFailure("Task is not present in index", task_id)
    task = load_data(root / rel)["task"]
    return task, rel


def _load_entity(root: Path, rel: str, key: str) -> dict[str, Any]:
    value = load_data(root / rel)
    if not isinstance(value, dict) or not isinstance(value.get(key), dict):
        raise ValidationFailure("Invalid canonical entity", {"path": rel, "key": key})
    return value[key]


def _format_list(items: list[Any], *, default: str = "- none") -> str:
    if not items:
        return default
    output: list[str] = []
    for item in items:
        if isinstance(item, dict):
            text = item.get("statement") or item.get("title") or item.get("name") or str(item)
        else:
            text = str(item)
        output.append(f"- {text}")
    return "\n".join(output)


def _format_commands(commands: list[Any]) -> str:
    if not commands:
        return "- no automatic command; follow manual checks"
    output: list[str] = []
    for item in commands:
        if isinstance(item, dict):
            argv = item.get("argv") or item.get("command")
            cwd = item.get("cwd", ".")
        else:
            argv = item
            cwd = "."
        text = " ".join(str(part) for part in argv) if isinstance(argv, list) else str(argv)
        output.append(f"- `{text}` (cwd `{cwd}`)")
    return "\n".join(output)


def _maintenance_binding(value: dict[str, Any]) -> dict[str, Any]:
    route = value.get("maintenance_route")
    if route is None:
        return {}
    return {
        "maintenance_route": route,
        "maintenance_plan_ref": value.get("maintenance_plan_ref"),
    }


def _prompt_text(
    task: dict[str, Any],
    project_definition: dict[str, Any],
    architecture: dict[str, Any],
    technology: dict[str, Any],
    run_ref: str,
    target_level: str,
) -> str:
    scope = task["scope"]
    verification = task["verification"]
    documentation = task.get("documentation") or {}
    acceptance = task.get("acceptance_criteria") or []
    dependencies = task.get("depends_on_tasks") or []
    result_path = f".harness/runtime/AGENT_RESULTS/{run_ref}.json"
    maintenance_fence = (
        f"MAINTENANCE_ROUTE: {task['maintenance_route']}\n"
        f"MAINTENANCE_PLAN_REF: {task['maintenance_plan_ref']}\n"
        "ACCEPTED_MATURITY_CHANGE: FORBIDDEN\n"
        if task.get("maintenance_route") is not None
        else ""
    )
    return f"""# Codex execution bundle — {task['id']}

## Role

Act as the bounded implementation executor for Project Harness. Implement only the current atomic task. Do not redesign accepted baselines, choose another task, or broaden scope silently.

## Current task

- Task: `{task['id']}@{task['revision']}`
- Run reservation: `{run_ref}`
- Title: {task['title']}
- Type: `{task['type']}`
- Purpose: {task['purpose']}
- Expected result: {task['expected_result']}
- Dependencies already satisfied: {', '.join(dependencies) if dependencies else 'none'}

## Implementation-stage fence

CURRENT_IMPLEMENTATION_STAGE: {task['implementation_stage']}
TARGET_IMPLEMENTATION_LEVEL: {target_level}
{maintenance_fence}
Реализуй только требования текущей стадии и Task Contract.
Не добавляй Alpha/Beta/MVP/Release механизмы без прямого hard constraint.
Все полезные будущие улучшения запиши в Next Stage Gap Backlog, но не реализуй.

## Project outcome

{project_definition['problem_statement']}

## Accepted architecture

- Style: {architecture['style']}
- Summary: {architecture.get('summary') or ''}

## Accepted technology selections

{_format_list([f"{item.get('area')}: {item.get('technology')} {item.get('version_constraint') or ''}" for item in technology.get('selections') or []])}

## Acceptance criteria

{_format_list(acceptance)}

## Filesystem scope

### Read

{_format_list(scope.get('read') or [])}

### Write

{_format_list(scope.get('write') or [])}

### Forbidden

{_format_list(scope.get('forbidden') or [])}

Never edit `.harness/` or generated Harness root views manually. `PROJECT_CONTROL_WRITE` is prohibited except for the bounded protocol exception that permits one regular JSON file at the exact Agent Task Result path shown below. Symlinks, hardlinks, alternate Run IDs, and any other control-plane write are forbidden.

## Documentation impact

- Impact: `{documentation.get('impact', 'NONE')}`
- Required updates:
{_format_list(documentation.get('required_updates') or [])}

## Verification

Commands:
{_format_commands(verification.get('commands') or [])}

Expected paths:
{_format_list(verification.get('expected_paths') or [])}

Manual checks:
{_format_list(verification.get('manual_checks') or [])}

After implementation run independent Harness verification:

```bash
python .harness/engine/project-harness.py verify --project . --allow-command-execution
```

## Required result contract

Write JSON to `{result_path}` with this shape:

```json
{{
  "schema_version": 1,
  "task_ref": "{task['id']}@{task['revision']}",
  "run_ref": "{run_ref}",
  "status": "COMPLETED",
  "summary": "what was implemented",
  "changes": {{"added": [], "modified": [], "deleted": []}},
  "commands": [],
  "tests": [],
  "evidence": [],
  "blockers": [],
  "stage_scope_violations": [],
  "notes": []
}}
```

Then complete the transition:

```bash
python .harness/engine/project-harness.py complete --project . --result {result_path}
```

If a material ambiguity or blocked dependency appears, do not improvise. Use:

```bash
python .harness/engine/project-harness.py block --project . --reason "<precise blocker>" --option "<safe recovery option>"
```
"""


def ensure_current_project_contract(root: Path) -> None:
    lock_path = root / ".harness/config/PROJECT_LOCK.yaml"
    value = load_data(lock_path)
    lock = value.get("project_lock") if isinstance(value, dict) else None
    if not isinstance(lock, dict):
        raise ValidationFailure("Project lock envelope is invalid", str(lock_path))
    current = lock.get("harness_distribution") == ENGINE_VERSION and lock.get("schema_version") == SCHEMA_VERSION
    legacy_manual = lock.get("harness_distribution") == "0.5.0" and lock.get("schema_version") == 6
    if legacy_manual:
        policy = lock.get("execution")
        if policy is not None and policy != {
            "mode": "MANUAL_HANDOFF", "adapter_profile_ref": None,
            "sandbox_profile_ref": None, "network_mode": "NONE",
            "completion_policy": "EXPLICIT_AFTER_VERIFICATION",
        }:
            raise ValidationFailure("v0.5.0 lock cannot authorize automatic execution")
    migrated = PROJECT_INPUT_MIGRATION_ID in set(lock.get("migrations_applied") or [])
    if not (current or legacy_manual) or not migrated:
        raise ValidationFailure(
            "A new Run requires project migration to the current contract",
            {
                "actual_engine": lock.get("harness_distribution"),
                "actual_schema": lock.get("schema_version"),
                "required_engine": ENGINE_VERSION,
                "required_schema": SCHEMA_VERSION,
                "required_migration": PROJECT_INPUT_MIGRATION_ID,
                "command": "project-harness migrate-project --project .",
            },
        )


def reserve_run(root: Path, task_id: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    ensure_current_project_contract(root)
    implementation = load_stage_state(root)
    state_path = root / ".harness/state/CURRENT_STATE.yaml"
    state_doc = load_data(state_path)
    state = state_doc["state"]
    task_id = task_id or state.get("current_task_ref")
    if not task_id:
        raise ValidationFailure("No current task is available")
    task, task_rel = _load_task(root, task_id)
    task_stage = task.get("implementation_stage")
    active_stage = execution_stage(root)
    if task_stage != active_stage:
        raise ValidationFailure(
            "STAGE_SCOPE_VIOLATION: task does not belong to the current executable route stage",
            {
                "classification": "STAGE_SCOPE_VIOLATION",
                "task": task_id,
                "task_stage": task_stage,
                "execution_stage": active_stage,
                "canonical_active_stage": implementation["active_stage"],
            },
        )
    maintenance_route = task.get("maintenance_route")
    if maintenance_route is not None and maintenance_route != MAINTENANCE_ROUTE:
        raise ValidationFailure("Task contains an unknown maintenance route", maintenance_route)
    active = state.get("active_run")
    if isinstance(active, dict) and active.get("task_ref", "").split("@")[0] == task_id:
        return {
            "status": "READY_FOR_CODEX",
            "task_ref": active["task_ref"],
            "run_ref": active["run_ref"],
            "prompt_bundle_path": active["prompt_bundle_path"],
            "prompt_markdown_path": active["prompt_markdown_path"],
            "implementation_stage": active_stage,
            "target_implementation_level": implementation["target_level"],
            **_maintenance_binding(active),
            "idempotent": True,
        }
    if task.get("status") != "READY":
        raise ValidationFailure("Task is not READY", {"task": task_id, "status": task.get("status")})
    project = load_data(root / ".harness/config/PROJECT.yaml")["project"]
    token = project["id_token"]
    attempts = state.setdefault("attempts", {})
    attempt_no = int(attempts.get(task_id, 0)) + 1
    attempts[task_id] = attempt_no
    sequence = int(task.get("sequence", 0)) // 10 or 1
    run_ref = f"RUN-{token}-{sequence:03d}-A{attempt_no}"
    run_plan_ref = f"RNP-{token}-{sequence:03d}-A{attempt_no}"
    bundle_ref = f"CPB-{token}-{sequence:03d}-A{attempt_no}"
    context_packet_ref = f"CPK-{token}-{sequence:03d}-A{attempt_no}"
    grant_ref = f"CGR-{token}-{sequence:03d}-A{attempt_no}"
    snapshot_ref = f"SNP-{token}-{sequence:03d}-A{attempt_no}"
    allowed_result_path = f".harness/runtime/AGENT_RESULTS/{run_ref}.json"
    operation_journal_path = f".harness/runtime/OPERATION_JOURNAL/{run_ref}.yaml"

    entity_paths = state["entity_paths"]
    project_definition = _load_entity(root, entity_paths["project_definition"], "project_definition")
    architecture = _load_entity(root, entity_paths["architecture_baseline"], "architecture_baseline")
    technology = _load_entity(root, entity_paths["technology_baseline"], "technology_baseline")
    task_ref = f"{task['id']}@{task['revision']}"
    generated_at = utc_now()

    context_packet = {
        "context_packet": {
            "id": context_packet_ref,
            "task_ref": task_ref,
            "implementation_stage": active_stage,
            **_maintenance_binding(task),
            "run_ref": run_ref,
            "context_plan_ref": task["context_plan_ref"],
            "project_definition_ref": project["project_definition_ref"],
            "architecture_baseline_ref": project["architecture_baseline_ref"],
            "technology_baseline_ref": project["technology_baseline_ref"],
            "selected_paths": task.get("context", {}).get("read_paths", []),
            "source_refs": task.get("documentation", {}).get("source_refs", []),
            "previous_task_reports": list(state.get("task_report_refs") or []),
            "generated_at": generated_at,
            "status": "BOUND",
        }
    }
    context_path = root / f".harness/context/PACKETS_BY_RUN/{context_packet_ref}.yaml"
    write_data(context_path, context_packet)

    grant = {
        "capability_grant": {
            "id": grant_ref,
            "task_ref": task_ref,
            "run_ref": run_ref,
            "implementation_stage": active_stage,
            **_maintenance_binding(task),
            "capabilities": task["route"]["required_capabilities"],
            "scope": task["scope"],
            "prohibited_operations": [
                "GIT_PUSH",
                "DEPLOY",
                "RELEASE_PUBLISH",
                "HARNESS_DISTRIBUTION_WRITE",
                "PROJECT_CONTROL_WRITE",
            ],
            "protocol_exceptions": [
                {
                    "operation": "PROJECT_CONTROL_WRITE",
                    "path": allowed_result_path,
                    "constraints": [
                        "EXACT_ACTIVE_RUN_ID",
                        "REGULAR_FILE_ONLY",
                        "NO_SYMLINK_OR_HARDLINK",
                        "MAX_BYTES:1048576",
                        "SCHEMA:SCHEMA-AGENT-TASK-RESULT@1",
                    ],
                }
            ],
            "issued_at": generated_at,
            "status": "ACTIVE",
        }
    }
    grant_path = root / f".harness/runtime/CAPABILITY_GRANTS/{grant_ref}.yaml"
    write_data(grant_path, grant)

    prompt = _prompt_text(
        task,
        project_definition,
        architecture,
        technology,
        run_ref,
        implementation["target_level"],
    )
    prompt_hash = sha256_bytes(prompt.encode("utf-8"))
    bundle = {
        "compiled_prompt_bundle": {
            "id": bundle_ref,
            "prompt_plan_ref": task["prompt_plan_ref"],
            "task_ref": task_ref,
            "implementation_stage": active_stage,
            **_maintenance_binding(task),
            "target_implementation_level": implementation["target_level"],
            "run_ref": run_ref,
            "adapter_profile_ref": "ADP-CODEX@1",
            "context_packet_refs": [context_packet_ref],
            "capability_grant_refs": [grant_ref],
            "output_schema_ref": "SCHEMA-AGENT-TASK-RESULT@1",
            "allowed_agent_output_path": allowed_result_path,
            "prompt_text_sha256": f"sha256:{prompt_hash}",
            "compilation_hash": f"sha256:{sha256_bytes(canonical_json_bytes({'task': task, 'context': context_packet, 'grant': grant}))}",
            "compiled_at": generated_at,
            "status": "COMPILED",
        }
    }
    bundle_path = root / f".harness/prompts/BUNDLES_BY_RUN/{bundle_ref}.yaml"
    prompt_md_path = root / f".harness/prompts/BUNDLES_BY_RUN/{bundle_ref}.md"
    write_data(bundle_path, bundle)
    atomic_write_text(prompt_md_path, prompt)

    snapshot_path = root / f".harness/runtime/SNAPSHOTS/{snapshot_ref}.yaml"
    wp_id = str(task["work_package_ref"]).split("@")[0]
    wp_index = load_data(root / ".harness/work-packages/INDEX.yaml").get("work_package_index") or {}
    wp_rel = (wp_index.get("current") or {}).get(wp_id)
    if not wp_rel:
        raise ValidationFailure("Task Work Package is absent from the current index", wp_id)
    current_wp = load_data(root / str(wp_rel)).get("work_package") or {}
    work_package_ref = f"{current_wp.get('id')}@{current_wp.get('revision')}"
    run_plan = {
        "run_plan": {
            "id": run_plan_ref,
            "task_ref": task_ref,
            "work_package_ref": work_package_ref,
            "implementation_stage": active_stage,
            **_maintenance_binding(task),
            "base_revisions": {
                "project": project["project_definition_ref"],
                "repository_snapshot": snapshot_ref,
            },
            "prompt_bundle_ref": bundle_ref,
            "context_packet_ref": context_packet_ref,
            "adapter_ref": "ADP-CODEX@1",
            "capability_grant_refs": [grant_ref],
            "verification_profile_ref": task["verification_profile_ref"],
            "allowed_agent_output_path": allowed_result_path,
            "idempotency_key": f"sha256:{sha256_bytes(canonical_json_bytes({'task': task_ref, 'attempt': attempt_no, 'snapshot': snapshot_ref}))}",
            "status": "READY",
        }
    }
    run_plan_path = root / f".harness/runtime/RUN_PLANS/{run_plan_ref}@1.yaml"
    write_data(run_plan_path, run_plan)

    active_run = {
        "run_ref": run_ref,
        "run_plan_ref": run_plan_ref,
        "run_plan_path": run_plan_path.relative_to(root).as_posix(),
        "task_ref": task_ref,
        "implementation_stage": active_stage,
        **_maintenance_binding(task),
        "target_implementation_level": implementation["target_level"],
        "attempt_no": attempt_no,
        "prompt_bundle_ref": bundle_ref,
        "prompt_bundle_path": bundle_path.relative_to(root).as_posix(),
        "prompt_markdown_path": prompt_md_path.relative_to(root).as_posix(),
        "context_packet_ref": context_packet_ref,
        "context_packet_path": context_path.relative_to(root).as_posix(),
        "capability_grant_ref": grant_ref,
        "capability_grant_path": grant_path.relative_to(root).as_posix(),
        "snapshot_ref": snapshot_ref,
        "snapshot_path": snapshot_path.relative_to(root).as_posix(),
        "allowed_agent_output_path": allowed_result_path,
        "operation_journal_path": operation_journal_path,
        "control_plane_phase": "RUN_RESERVED",
        "verification_report_ref": None,
        "verification_report_path": None,
        "verification_evidence_ref": None,
        "verification_evidence_path": None,
    }
    state["active_run"] = active_run
    state["next_route"] = "EXECUTE_CURRENT_TASK_WITH_CODEX"
    state["updated_at"] = generated_at
    write_data(state_path, state_doc)

    next_task_path = root / ".harness/state/NEXT_TASK.yaml"
    write_data(
        next_task_path,
        {
            "next_task": {
                "task_ref": task_ref,
                "implementation_stage": active_stage,
                **_maintenance_binding(task),
                "target_implementation_level": implementation["target_level"],
                "run_ref": run_ref,
                "task_path": task_rel,
                "prompt_bundle_path": bundle_path.relative_to(root).as_posix(),
                "prompt_markdown_path": prompt_md_path.relative_to(root).as_posix(),
                "result_path": allowed_result_path,
                "next_command": "python .harness/engine/project-harness.py verify --project . --allow-command-execution",
                "status": "READY_FOR_CODEX",
            }
        },
    )
    render_status(root)

    # The snapshot is written only after all reservation artifacts exist. Its
    # self path and journal path are explicit expected protocol anchors.
    write_snapshot(
        snapshot_path,
        root,
        task_ref=task_ref,
        run_ref=run_ref,
        allowed_agent_output_path=allowed_result_path,
        operation_journal_path=operation_journal_path,
        trusted_task=task,
        implementation_stage=active_stage,
        maintenance_route=maintenance_route,
        maintenance_plan_ref=task.get("maintenance_plan_ref"),
    )
    record_phase_boundary(
        root,
        active_run,
        phase="RUN_RESERVED",
        kernel_written_paths=[
            context_path.relative_to(root).as_posix(),
            grant_path.relative_to(root).as_posix(),
            bundle_path.relative_to(root).as_posix(),
            prompt_md_path.relative_to(root).as_posix(),
            run_plan_path.relative_to(root).as_posix(),
            snapshot_path.relative_to(root).as_posix(),
            state_path.relative_to(root).as_posix(),
            next_task_path.relative_to(root).as_posix(),
            "STATUS.md",
        ],
        recorded_at=generated_at,
    )
    return {
        "status": "READY_FOR_CODEX",
        "task_ref": task_ref,
        "run_ref": run_ref,
        "implementation_stage": active_stage,
        "target_implementation_level": implementation["target_level"],
        **_maintenance_binding(task),
        "prompt_bundle_path": bundle_path.relative_to(root).as_posix(),
        "prompt_markdown_path": prompt_md_path.relative_to(root).as_posix(),
        "idempotent": False,
    }

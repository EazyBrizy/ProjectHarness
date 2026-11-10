from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import os
import re
import shutil
import tempfile
import json
import uuid
from typing import Any

from .operation_guard import guarded_mutation
from .compiler import _copy_runtime
from .errors import ValidationFailure, WaitingDecision, WaitingInput
from .hashing import sha256_bytes, sha256_file
from .planner import normalize_plan
from .project_input import (
    PROJECT_INPUT_MIGRATION_ID, EXECUTION_POLICY_MIGRATION_ID, DEFAULT_EXECUTION_POLICY,
    migrate_project_input,
    validate_project_input,
)
from .prompting import reserve_run
from .registry import REGISTRY_NAMES, registry_lock
from .render import render_project_documents, render_roadmap, render_status
from .resources import distribution_root
from .serialization import append_jsonl, canonical_json_bytes, load_data, write_data, atomic_write_text
from .stages import assess_maturity, create_initial_stage_artifacts
from .util import ENGINE_VERSION, SCHEMA_VERSION, utc_now
from .validation import (LEGACY_ENGINE_VERSION, LEGACY_SCHEMA_VERSION, V050_ENGINE_VERSION,
                         V050_SCHEMA_VERSION, validate_handoff_directory)

MIGRATION_REPORT_PATH = f".harness/reports/{PROJECT_INPUT_MIGRATION_ID}.yaml"
V051_MIGRATION_REPORT_PATH = f".harness/reports/{EXECUTION_POLICY_MIGRATION_ID}.yaml"


def _approval_template() -> dict[str, Any]:
    return {"approved": False, "actor": None, "approved_at": None, "notes": None}


def _comparison_view(value: dict[str, Any]) -> dict[str, Any]:
    """Remove only fields v0.5.0 explicitly permits migration input to add."""
    normalized = deepcopy(value)
    normalized.pop("implementation", None)
    approvals = normalized.setdefault("approvals", {})
    if isinstance(approvals, dict) and "brownfield_baseline" in approvals:
        approvals["brownfield_baseline"] = _approval_template()
    return normalized


def _load_migration_input(
    root: Path,
    supplied_input: Path | None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    accepted_path = root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml"
    if not accepted_path.exists():
        raise ValidationFailure("Accepted PROJECT_INPUT is missing", str(accepted_path))

    stored_raw = load_data(accepted_path)
    stored, stored_report = migrate_project_input(stored_raw)
    candidate = stored
    source = accepted_path.relative_to(root).as_posix()

    if supplied_input is not None:
        supplied_path = supplied_input.expanduser().resolve()
        supplied_raw = load_data(supplied_path)
        supplied, supplied_report = migrate_project_input(supplied_raw)
        if _comparison_view(supplied) != _comparison_view(stored):
            raise ValidationFailure(
                "Migration input may only set implementation fields and formalize brownfield_baseline approval",
                {
                    "accepted_input": str(accepted_path),
                    "supplied_input": str(supplied_path),
                    "stored_migration": stored_report,
                    "supplied_migration": supplied_report,
                },
            )
        candidate = supplied
        source = str(supplied_path)

    return candidate, stored_report, source


def _assert_project_identity(root: Path, candidate: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    project_path = root / ".harness/config/PROJECT.yaml"
    lock_path = root / ".harness/config/PROJECT_LOCK.yaml"
    try:
        project_doc = load_data(project_path)
        lock_doc = load_data(lock_path)
        project = project_doc["project"]
        lock_doc["project_lock"]
    except Exception as exc:
        raise ValidationFailure("Project configuration or lock is invalid", str(exc)) from exc

    candidate_project = candidate.get("project") if isinstance(candidate, dict) else None
    if not isinstance(candidate_project, dict):
        raise ValidationFailure("PROJECT_INPUT.project is invalid")
    expected = {"slug": project.get("id"), "mode": project.get("lifecycle_mode")}
    actual = {"slug": candidate_project.get("slug"), "mode": candidate_project.get("mode")}
    if actual != expected:
        raise ValidationFailure(
            "Migration input does not identify the existing project",
            {"expected": expected, "actual": actual},
        )
    return project_doc, lock_doc


def _copy_current_registries(root: Path) -> tuple[dict[str, int], dict[str, str]]:
    distribution = distribution_root()
    target = root / ".harness/registries"
    target.mkdir(parents=True, exist_ok=True)
    for name in REGISTRY_NAMES:
        shutil.copy2(distribution / "registries" / f"{name}.yaml", target / f"{name}.yaml")
    return registry_lock(distribution)


def _split_ref(ref: str, *, field: str) -> tuple[str, int]:
    if "@" not in ref:
        raise ValidationFailure(f"{field} must be a revisioned ref", ref)
    entity_id, raw_revision = ref.rsplit("@", 1)
    try:
        revision = int(raw_revision)
    except ValueError as exc:
        raise ValidationFailure(f"{field} has an invalid revision", ref) from exc
    return entity_id, revision


def _next_revision_path(folder: str, entity_id: str, revision: int) -> str:
    return f"{folder}/{entity_id}@{revision}.yaml"


def _write_revised_reference_artifact(
    root: Path,
    *,
    old_ref: str,
    folder: str,
    envelope: str,
    task_ref: str,
    stage: str,
    migrated_at: str,
    status: str | None = None,
) -> tuple[str, str]:
    entity_id, old_revision = _split_ref(old_ref, field=f"{envelope}_ref")
    old_path = root / f"{folder}/{old_ref}.yaml"
    value = load_data(old_path)
    entity = value.get(envelope) if isinstance(value, dict) else None
    if not isinstance(entity, dict):
        raise ValidationFailure(f"Legacy {envelope} envelope is invalid", str(old_path))
    revised = deepcopy(entity)
    revised["revision"] = old_revision + 1
    revised["previous_revision_ref"] = old_ref
    revised["task_ref"] = task_ref
    revised["implementation_stage"] = stage
    revised["updated_at"] = migrated_at
    if status is not None:
        revised["status"] = status
    new_ref = f"{entity_id}@{revised['revision']}"
    new_rel = _next_revision_path(folder, entity_id, int(revised["revision"]))
    if (root / new_rel).exists():
        raise ValidationFailure("Migration revision already exists unexpectedly", new_rel)
    write_data(root / new_rel, {envelope: revised})
    return new_ref, new_rel


def _migrate_current_revisions(root: Path, migrated_at: str) -> dict[str, Any]:
    """Create v0.5 current revisions without rewriting v0.4.1 history."""
    task_index_path = root / ".harness/tasks/INDEX.yaml"
    wp_index_path = root / ".harness/work-packages/INDEX.yaml"
    task_index_doc = load_data(task_index_path)
    wp_index_doc = load_data(wp_index_path)
    task_index = task_index_doc.get("task_index") if isinstance(task_index_doc, dict) else None
    wp_index = wp_index_doc.get("work_package_index") if isinstance(wp_index_doc, dict) else None
    if not isinstance(task_index, dict) or not isinstance(task_index.get("current"), dict):
        raise ValidationFailure("Task index is invalid", str(task_index_path))
    if not isinstance(wp_index, dict) or not isinstance(wp_index.get("current"), dict):
        raise ValidationFailure("Work Package index is invalid", str(wp_index_path))

    stage = "PROTOTYPE"
    task_mappings: list[dict[str, Any]] = []
    wp_mappings: list[dict[str, Any]] = []
    auxiliary_mappings: list[dict[str, Any]] = []
    completed_ref_map: dict[str, str] = {}

    # Precompute the new Task refs so all auxiliary plans can refer to the exact
    # current Task revision while historical files remain untouched.
    task_specs: dict[str, tuple[str, dict[str, Any], str]] = {}
    for task_id in task_index.get("order") or []:
        rel = (task_index.get("current") or {}).get(task_id)
        if not rel:
            raise ValidationFailure("Task index current path is missing", task_id)
        task = load_data(root / str(rel)).get("task") or {}
        if task.get("id") != task_id or not isinstance(task.get("revision"), int):
            raise ValidationFailure("Current legacy Task is invalid", str(rel))
        old_ref = f"{task_id}@{task['revision']}"
        new_ref = f"{task_id}@{int(task['revision']) + 1}"
        task_specs[task_id] = (old_ref, task, new_ref)

    for task_id in task_index.get("order") or []:
        old_ref, task, new_ref = task_specs[task_id]
        revised = deepcopy(task)
        revised["revision"] = int(task["revision"]) + 1
        revised["previous_revision_ref"] = old_ref
        revised["implementation_stage"] = stage
        revised["updated_at"] = migrated_at
        if revised.get("status") == "COMPLETED":
            revised["status"] = "DONE"

        prompt_ref, prompt_rel = _write_revised_reference_artifact(
            root,
            old_ref=str(task["prompt_plan_ref"]),
            folder=".harness/prompts/PLANS",
            envelope="prompt_plan",
            task_ref=new_ref,
            stage=stage,
            migrated_at=migrated_at,
        )
        context_ref, context_rel = _write_revised_reference_artifact(
            root,
            old_ref=str(task["context_plan_ref"]),
            folder=".harness/context/PLANS",
            envelope="context_plan",
            task_ref=new_ref,
            stage=stage,
            migrated_at=migrated_at,
        )
        verification_ref, verification_rel = _write_revised_reference_artifact(
            root,
            old_ref=str(task["verification_profile_ref"]),
            folder=".harness/verification/PROFILES",
            envelope="verification_profile",
            task_ref=new_ref,
            stage=stage,
            migrated_at=migrated_at,
        )
        revised["prompt_plan_ref"] = prompt_ref
        revised["context_plan_ref"] = context_ref
        revised["verification_profile_ref"] = verification_ref

        # Refresh resolved prompt inputs after the exact current Task refs are known.
        prompt_doc = load_data(root / prompt_rel)
        prompt = prompt_doc["prompt_plan"]
        prompt.setdefault("resolved_inputs", {})["context_plan_ref"] = context_ref
        prompt["resolved_inputs"]["task_hash"] = (
            "sha256:" + sha256_bytes(canonical_json_bytes(revised))
        )
        write_data(root / prompt_rel, prompt_doc)

        new_rel = _next_revision_path(".harness/tasks", task_id, int(revised["revision"]))
        if (root / new_rel).exists():
            raise ValidationFailure("Canonical migration Task revision already exists unexpectedly", new_rel)
        write_data(root / new_rel, {"task": revised})
        task_index["current"][task_id] = new_rel
        completed_ref_map[old_ref] = new_ref
        task_mappings.append(
            {
                "entity": "task",
                "legacy_ref": old_ref,
                "canonical_ref": new_ref,
                "legacy_file_rewritten": False,
                "status": revised.get("status"),
            }
        )
        auxiliary_mappings.extend(
            [
                {"entity": "prompt_plan", "legacy_ref": task["prompt_plan_ref"], "canonical_ref": prompt_ref, "path": prompt_rel},
                {"entity": "context_plan", "legacy_ref": task["context_plan_ref"], "canonical_ref": context_ref, "path": context_rel},
                {"entity": "verification_profile", "legacy_ref": task["verification_profile_ref"], "canonical_ref": verification_ref, "path": verification_rel},
            ]
        )

    for wp_id in wp_index.get("order") or []:
        rel = (wp_index.get("current") or {}).get(wp_id)
        if not rel:
            raise ValidationFailure("Work Package index current path is missing", wp_id)
        wp = load_data(root / str(rel)).get("work_package") or {}
        if wp.get("id") != wp_id or not isinstance(wp.get("revision"), int):
            raise ValidationFailure("Current legacy Work Package is invalid", str(rel))
        old_ref = f"{wp_id}@{wp['revision']}"
        revised = deepcopy(wp)
        revised["revision"] = int(wp["revision"]) + 1
        revised["previous_revision_ref"] = old_ref
        revised["implementation_stage"] = stage
        revised["updated_at"] = migrated_at

        dag_ref = revised.get("dependency_graph_ref")
        if dag_ref:
            dag_id, dag_revision = _split_ref(str(dag_ref), field="dependency_graph_ref")
            dag_path = root / f".harness/dags/{dag_ref}.yaml"
            dag_doc = load_data(dag_path)
            dag = dag_doc.get("dependency_graph") if isinstance(dag_doc, dict) else None
            if not isinstance(dag, dict):
                raise ValidationFailure("Legacy dependency graph is invalid", str(dag_path))
            new_dag = deepcopy(dag)
            new_dag["revision"] = dag_revision + 1
            new_dag["previous_revision_ref"] = str(dag_ref)
            new_dag["implementation_stage"] = stage
            new_dag["updated_at"] = migrated_at
            new_dag_ref = f"{dag_id}@{new_dag['revision']}"
            new_dag_rel = f".harness/dags/{new_dag_ref}.yaml"
            write_data(root / new_dag_rel, {"dependency_graph": new_dag})
            revised["dependency_graph_ref"] = new_dag_ref
            auxiliary_mappings.append(
                {"entity": "dependency_graph", "legacy_ref": dag_ref, "canonical_ref": new_dag_ref, "path": new_dag_rel}
            )

        new_ref = f"{wp_id}@{revised['revision']}"
        new_rel = _next_revision_path(".harness/work-packages", wp_id, int(revised["revision"]))
        if (root / new_rel).exists():
            raise ValidationFailure("Canonical migration Work Package revision already exists unexpectedly", new_rel)
        write_data(root / new_rel, {"work_package": revised})
        wp_index["current"][wp_id] = new_rel
        wp_mappings.append(
            {"entity": "work_package", "legacy_ref": old_ref, "canonical_ref": new_ref, "legacy_file_rewritten": False, "status": revised.get("status")}
        )

    write_data(task_index_path, task_index_doc)
    write_data(wp_index_path, wp_index_doc)

    state_path = root / ".harness/state/CURRENT_STATE.yaml"
    state_doc = load_data(state_path)
    state = state_doc.get("state") if isinstance(state_doc, dict) else None
    if not isinstance(state, dict):
        raise ValidationFailure("Current state envelope is invalid", str(state_path))
    state["completed_task_refs"] = [
        completed_ref_map.get(str(ref), str(ref)) for ref in (state.get("completed_task_refs") or [])
    ]
    state["updated_at"] = migrated_at
    write_data(state_path, state_doc)

    current_wp_refs = []
    for wp_id in wp_index.get("order") or []:
        wp = load_data(root / wp_index["current"][wp_id])["work_package"]
        current_wp_refs.append(f"{wp['id']}@{wp['revision']}")
    return {
        "task_mappings": task_mappings,
        "work_package_mappings": wp_mappings,
        "auxiliary_mappings": auxiliary_mappings,
        "current_work_package_refs": current_wp_refs,
    }


def _cancel_unexecuted_active_run(root: Path, migrated_at: str) -> dict[str, Any] | None:
    state_path = root / ".harness/state/CURRENT_STATE.yaml"
    state_doc = load_data(state_path)
    state = state_doc.get("state") if isinstance(state_doc, dict) else None
    if not isinstance(state, dict):
        raise ValidationFailure("Current state envelope is invalid", str(state_path))
    active = state.get("active_run")
    if not isinstance(active, dict):
        return None
    result_path = root / str(active.get("allowed_agent_output_path") or "")
    if active.get("verification_report_ref") or (str(active.get("allowed_agent_output_path") or "") and result_path.exists()):
        raise ValidationFailure(
            "Migration cannot replace a Run that already has agent or verification output",
            {
                "active_run": active.get("run_ref"),
                "required_route": "COMPLETE_BLOCK_OR_CANCEL_ACTIVE_RUN_BEFORE_MIGRATION",
            },
        )
    run_ref = str(active.get("run_ref") or "")
    if not run_ref:
        raise ValidationFailure("Legacy active_run is missing run_ref")
    run_path = root / f".harness/runtime/RUNS/{run_ref}.yaml"
    if not run_path.exists():
        write_data(
            run_path,
            {
                "run": {
                    "id": run_ref,
                    "task_ref": active.get("task_ref"),
                    "implementation_stage": "PROTOTYPE",
                    "attempt_no": active.get("attempt_no"),
                    "run_plan_ref": active.get("run_plan_ref"),
                    "status": "CANCELLED",
                    "cancellation_reason": "MIGRATION_RECOMPILE_WITH_STAGE_FENCE",
                    "compensation_status": "NOT_REQUIRED",
                    "completed_at": migrated_at,
                }
            },
        )
    state["active_run"] = None
    state["updated_at"] = migrated_at
    write_data(state_path, state_doc)
    return {
        "run_ref": run_ref,
        "status": "CANCELLED",
        "reason": "MIGRATION_RECOMPILE_WITH_STAGE_FENCE",
        "historical_prompt_bundle_rewritten": False,
    }


def _scope_refs(root: Path) -> list[str]:
    refs: list[str] = []
    for path in sorted((root / ".harness/canonical/REQUIREMENTS").glob("REQ-*@*.yaml")):
        requirement = load_data(path).get("requirement") or {}
        if requirement.get("id") and requirement.get("revision"):
            refs.append(f"{requirement['id']}@{requirement['revision']}")
    return refs


def _all_tasks_done(root: Path) -> tuple[bool, bool]:
    index = load_data(root / ".harness/tasks/INDEX.yaml").get("task_index") or {}
    statuses: list[str] = []
    for task_id in index.get("order") or []:
        task = load_data(root / index["current"][task_id]).get("task") or {}
        statuses.append(str(task.get("status")))
    return bool(statuses) and all(status in {"DONE", "SUPERSEDED"} for status in statuses), any(
        status in {"DONE", "SUPERSEDED"} for status in statuses
    )


def _first_incomplete_task(root: Path) -> str | None:
    index = load_data(root / ".harness/tasks/INDEX.yaml").get("task_index") or {}
    completed: set[str] = set()
    for task_id in index.get("order") or []:
        task = load_data(root / index["current"][task_id]).get("task") or {}
        if task.get("status") in {"DONE", "SUPERSEDED"}:
            completed.add(task_id)
    for task_id in index.get("order") or []:
        task = load_data(root / index["current"][task_id]).get("task") or {}
        if task.get("status") in {"DONE", "SUPERSEDED", "BLOCKED"}:
            continue
        dependencies = set(task.get("depends_on_tasks") or [])
        if dependencies <= completed:
            return task_id
    return None


def _ensure_task_ready(root: Path, task_id: str, migrated_at: str) -> str:
    index_path = root / ".harness/tasks/INDEX.yaml"
    index_doc = load_data(index_path)
    index = index_doc["task_index"]
    rel = index["current"][task_id]
    task_doc = load_data(root / rel)
    task = task_doc["task"]
    if task.get("status") == "READY":
        return f"{task['id']}@{task['revision']}"
    if task.get("status") != "PLANNED":
        raise ValidationFailure("Next migrated Task is not runnable", {"task": task_id, "status": task.get("status")})
    revised = deepcopy(task)
    revised["revision"] = int(task["revision"]) + 1
    revised["previous_revision_ref"] = f"{task['id']}@{task['revision']}"
    revised["status"] = "READY"
    revised["ready_at"] = migrated_at
    revised["updated_at"] = migrated_at
    new_rel = f".harness/tasks/{revised['id']}@{revised['revision']}.yaml"
    write_data(root / new_rel, {"task": revised})
    index["current"][task_id] = new_rel
    write_data(index_path, index_doc)
    return f"{revised['id']}@{revised['revision']}"


def _update_human_views(root: Path, migrated_at: str) -> list[str]:
    changed: list[str] = []
    summary_path = root / "HANDOFF_SUMMARY.md"
    if summary_path.exists():
        text = summary_path.read_text(encoding="utf-8")
        updated = re.sub(r"(?m)^- Engine: `[^`]+`$", f"- Engine: `{ENGINE_VERSION}`", text)
        marker = f"- Contract migration: `{PROJECT_INPUT_MIGRATION_ID}` at `{migrated_at}`"
        if marker not in updated:
            updated = updated.rstrip() + "\n" + marker + "\n"
        if updated != text:
            atomic_write_text(summary_path, updated)
            changed.append("HANDOFF_SUMMARY.md")

    code_start = root / "CODEX_START.md"
    if code_start.exists():
        text = code_start.read_text(encoding="utf-8")
        note = (
            "\n## v0.5.0 migration note\n\n"
            "This mutable project was migrated from v0.4.1. Historical Runs and revisions remain immutable; "
            "only the active implementation stage may receive new atomic work. Use `stage-status` and "
            "`validate-project` before continuing. The original `MANIFEST.sha256` remains the initial-handoff baseline.\n"
        )
        if "## v0.5.0 migration note" not in text:
            atomic_write_text(code_start, text.rstrip() + note)
            changed.append("CODEX_START.md")
    return changed


def _project_relative_assessment_result(root: Path, result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return result
    normalized = deepcopy(result)
    raw_path = normalized.get("assessment_path")
    if raw_path:
        path = Path(str(raw_path))
        try:
            normalized["assessment_path"] = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            normalized["assessment_path"] = str(raw_path)
    return normalized


def _migrate_project_copy(root: Path, *, input_path: Path | None) -> dict[str, Any]:
    lock_path = root / ".harness/config/PROJECT_LOCK.yaml"
    state_path = root / ".harness/state/CURRENT_STATE.yaml"
    candidate, input_migration, input_source = _load_migration_input(root, input_path)
    project_doc, lock_doc = _assert_project_identity(root, candidate)
    readiness = validate_project_input(candidate, require_approvals=True)
    if readiness["status"] == "WAITING_INPUT":
        raise WaitingInput("Project target implementation level is required before migration", readiness)
    if readiness["status"] == "WAITING_DECISION":
        raise WaitingDecision("Explicit project or target-level decision is required before migration", readiness)
    if readiness["status"] != "READY_FOR_HANDOFF":
        raise ValidationFailure("Project input cannot be migrated", readiness)

    migrated_at = utc_now()
    project = project_doc["project"]
    target = candidate["implementation"]["target_level"]
    legacy_lock_digest = f"sha256:{sha256_file(lock_path)}"
    accepted_input_path = root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml"
    legacy_input_digest = f"sha256:{sha256_file(accepted_input_path)}"

    cancelled_run = _cancel_unexecuted_active_run(root, migrated_at)
    mappings = _migrate_current_revisions(root, migrated_at)
    versions, digests = _copy_current_registries(root)
    _copy_runtime(root)

    implementation = create_initial_stage_artifacts(
        root,
        candidate,
        token=str(project["id_token"]),
        baseline_ref=str(project["project_definition_ref"]),
        scope_refs=_scope_refs(root),
        work_package_refs=mappings["current_work_package_refs"],
    )

    project["harness_schema_version"] = SCHEMA_VERSION
    project["target_implementation_level"] = target
    project["stage_state_ref"] = ".harness/stages/STAGE_STATE.yaml"
    project["updated_at"] = migrated_at
    write_data(root / ".harness/config/PROJECT.yaml", project_doc)
    write_data(accepted_input_path, candidate)

    lock = lock_doc["project_lock"]
    migrations = list(lock.get("migrations_applied") or [])
    if PROJECT_INPUT_MIGRATION_ID not in migrations:
        migrations.append(PROJECT_INPUT_MIGRATION_ID)
    lock.update(
        {
            "harness_distribution": ENGINE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "registry_versions": versions,
            "registry_digests": digests,
            "migrations_applied": migrations,
            "migrated_from": LEGACY_ENGINE_VERSION,
            "migrated_from_schema_version": LEGACY_SCHEMA_VERSION,
            "migrated_at": migrated_at,
        }
    )
    write_data(lock_path, lock_doc)

    all_done, has_completed_history = _all_tasks_done(root)
    state_doc = load_data(state_path)
    state = state_doc["state"]
    state["active_stage"] = implementation["active_stage"]
    state["target_implementation_level"] = target
    state["active_run"] = None
    state["updated_at"] = migrated_at

    assessment_result: dict[str, Any] | None = None
    next_result: dict[str, Any] | None = None
    reserve_task_id: str | None = None
    if all_done:
        state["project_status"] = "ACTIVE"
        state["current_task_ref"] = None
        state["next_route"] = "REVIEW_MATURITY_ASSESSMENT"
        state["handoff_status"] = "MIGRATED_BASELINE_REVIEW_REQUIRED"
        write_data(state_path, state_doc)
        write_data(
            root / ".harness/state/NEXT_TASK.yaml",
            {
                "next_task": {
                    "status": "MATURITY_REVIEW_REQUIRED",
                    "task_ref": None,
                    "run_ref": None,
                    "active_stage": implementation["active_stage"],
                    "target_implementation_level": target,
                    "next_route": "REVIEW_MATURITY_ASSESSMENT",
                }
            },
        )
        assessment_result = _project_relative_assessment_result(root, assess_maturity(root))
    else:
        current_task = state.get("current_task_ref") or _first_incomplete_task(root)
        if not current_task:
            raise ValidationFailure("Migrated project has incomplete work but no runnable Task")
        _ensure_task_ready(root, str(current_task), migrated_at)
        state["project_status"] = "ACTIVE"
        state["current_task_ref"] = str(current_task)
        state["next_route"] = "RECOMPILE_ACTIVE_STAGE_RUN"
        state["handoff_status"] = "MIGRATED_ACTIVE_STAGE_READY"
        write_data(state_path, state_doc)
        if has_completed_history:
            assessment_result = _project_relative_assessment_result(root, assess_maturity(root))
        reserve_task_id = str(current_task)

    plan = normalize_plan(candidate, str(project["id_token"]))
    render_project_documents(root, candidate, plan)
    render_roadmap(root)
    render_status(root)
    human_views = _update_human_views(root, migrated_at)

    report = {
        "migration_report": {
            "id": PROJECT_INPUT_MIGRATION_ID,
            "status": "COMPLETED",
            "project_ref": project.get("id"),
            "from": {"engine": LEGACY_ENGINE_VERSION, "schema_version": LEGACY_SCHEMA_VERSION},
            "to": {"engine": ENGINE_VERSION, "schema_version": SCHEMA_VERSION},
            "migrated_at": migrated_at,
            "input_source": input_source,
            "input_migration": input_migration,
            "target_implementation_level": target,
            "active_stage": implementation["active_stage"],
            "stage_path": implementation["stage_path"],
            "legacy_lock_digest": legacy_lock_digest,
            "legacy_input_digest": legacy_input_digest,
            "historical_task_files_rewritten": False,
            "historical_work_package_files_rewritten": False,
            "historical_run_files_rewritten": False,
            "task_revisions": mappings["task_mappings"],
            "work_package_revisions": mappings["work_package_mappings"],
            "auxiliary_revisions": mappings["auxiliary_mappings"],
            "cancelled_unexecuted_run": cancelled_run,
            "completed_history_detected": has_completed_history,
            "all_tasks_completed": all_done,
            "provisional_assessment": assessment_result,
            "new_active_run": (
                {"status": "RESERVED_AFTER_MIGRATION_RECORD_COMMIT", "task_id": reserve_task_id}
                if reserve_task_id else None
            ),
            "human_views_updated": human_views,
            "manifest_policy": "PRESERVE_INITIAL_HANDOFF_MANIFEST; VALIDATE_MUTABLE_STATE_WITH_VALIDATE_PROJECT",
        }
    }
    write_data(root / MIGRATION_REPORT_PATH, report)
    append_jsonl(
        root / ".harness/events/EVENTS.jsonl",
        {
            "type": "PROJECT_MIGRATED",
            "migration_id": PROJECT_INPUT_MIGRATION_ID,
            "from_engine": LEGACY_ENGINE_VERSION,
            "to_engine": ENGINE_VERSION,
            "target_implementation_level": target,
            "active_stage": implementation["active_stage"],
            "at": migrated_at,
        },
    )

    # Reserve only after every migration-owned mutable artifact is committed. The
    # new Run snapshot therefore seals the complete migrated baseline.
    if reserve_task_id:
        next_result = reserve_run(root, reserve_task_id)

    validation = validate_handoff_directory(root, check_manifest=False, check_control_plane_state=True)
    if validation["status"] != "PASS":
        raise ValidationFailure("Migrated project failed v0.5.0 validation", validation["errors"])
    return {
        "status": "MIGRATED",
        "migration_id": PROJECT_INPUT_MIGRATION_ID,
        "project": str(root),
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
        "target_implementation_level": target,
        "active_stage": implementation["active_stage"],
        "stage_path": implementation["stage_path"],
        "report_path": MIGRATION_REPORT_PATH,
        "cancelled_unexecuted_run": cancelled_run,
        "provisional_assessment": assessment_result,
        "new_active_run": next_result,
        "validation_status": validation["status"],
    }



# PH-051-10: v0.5.0 -> v0.5.1 is a *project-instance* migration, not
# PROJECT_INPUT@3 -> @4 input normalization. Accepted user input and all
# existing Stage/Run evidence remain byte-for-byte historical.
# The stable sibling marker makes the two directory renames recoverable even
# after SIGKILL/power loss. No agent can access this host-only migration path.
def _migration_marker(root: Path) -> Path:
    return root.parent / f".{root.name}.ph05110-migration.json"


def _migration_sync_dir(path: Path) -> None:
    from .stage_transactions import _fsync_directory
    _fsync_directory(path)


def _migration_persist_marker(marker: Path, data: dict[str, str]) -> None:
    from .serialization import atomic_write_text
    atomic_write_text(marker, json.dumps(data, sort_keys=True) + "\n")
    _migration_sync_dir(marker.parent)


def _migration_sync_staged_tree(root: Path) -> None:
    """Durably stage all project bytes before exposing the swap journal.

    A directory rename is atomic at one parent but does not itself persist the
    bytes it points to. The full copy must survive a host crash *before* the
    first canonical rename, or recovery could expose a partially persisted new
    tree. Do not follow symlinks or special files in the staged project.
    """
    import stat
    for base, folders, files in os.walk(root, topdown=False, followlinks=False):
        directory = Path(base)
        for name in files:
            item = directory / name
            info = item.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValidationFailure("Unsafe migration staging file", str(item))
            # Windows _commit/FlushFileBuffers needs a write-capable handle.
            # Only the private staged copy is opened; failed flush still aborts
            # before the journal and first canonical rename.
            flags = (os.O_RDWR if os.name == 'nt' else os.O_RDONLY) | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(item, flags)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        for name in folders:
            info = (directory / name).lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise ValidationFailure("Unsafe migration staging directory", str(directory / name))
        _migration_sync_dir(directory)


def _migration_remove_storage(root: Path, storage: Path) -> None:
    """Remove only an owned migration sibling, including copied NTFS read-only files.

    Never clear attributes on the canonical source. ACL/sharing failures still
    propagate; this only permits removal of private staging/backup copies.
    """
    from .platform_fs import ensure_native_path
    import stat
    ensure_native_path(storage, tree=True)
    target = storage.resolve()
    expected = rf"\.{re.escape(root.name)}\.ph05110-(?:staged|backup)-[0-9a-f]{{32}}"
    if (storage.is_symlink() or target.parent != root.parent.resolve()
            or re.fullmatch(expected, storage.name) is None):
        raise ValidationFailure("Refuse cleanup outside owned migration storage", str(storage))
    if os.name == 'nt':
        for directory, _, files in os.walk(target, followlinks=False):
            for name in files:
                item = Path(directory) / name
                info = item.lstat()
                if getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_READONLY:
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                        raise ValidationFailure("Refuse attribute changes on linked migration storage", str(item))
                    item.chmod(info.st_mode | stat.S_IWRITE)
    shutil.rmtree(target)


def _migration_recover(root: Path) -> str | None:
    """Recover interrupted sibling swap; never guess ownership of other paths.

    Before new root is installed restore the original. Once the complete new
    directory is installed and marked by its migration ID, keep it instead.
    """
    marker = _migration_marker(root)
    if not marker.exists() and not marker.is_symlink():
        return None
    if marker.is_symlink() or not marker.is_file():
        raise ValidationFailure("Unsafe v0.5.1 migration journal")
    try:
        raw = json.loads(marker.read_text(encoding="utf-8"))
        if (not isinstance(raw, dict) or raw.get("root") != root.name or
                set(raw) != {"root", "staged", "backup", "phase"} or
                raw.get("phase") not in {"PREPARED", "COMMITTED"}):
            raise ValueError("Invalid migration marker")
        names = (raw["staged"], raw["backup"])
        if any(not isinstance(name, str) or not name.startswith(f".{root.name}.ph05110-") or
               "/" in name or "\\" in name or ".." in name for name in names) or names[0] == names[1]:
            raise ValueError("Invalid migration storage names")
    except (OSError, ValueError, TypeError) as exc:
        raise ValidationFailure("Corrupt v0.5.1 migration journal") from exc
    staged, backup = (root.parent / name for name in names)
    for item in (root, staged, backup):
        if item.is_symlink():
            raise ValidationFailure("Migration recovery refuses symlink", str(item))
    is_new = False
    if root.is_dir():
        try:
            lock = load_data(root / ".harness/config/PROJECT_LOCK.yaml")["project_lock"]
            is_new = (lock.get("harness_distribution") == ENGINE_VERSION and
                      lock.get("schema_version") == SCHEMA_VERSION and
                      EXECUTION_POLICY_MIGRATION_ID in (lock.get("migrations_applied") or []))
        except (KeyError, TypeError, ValidationFailure):
            pass
    if is_new:
        # A swapped-in directory is a complete tree, not a partially updated
        # collection of individual canonical files. Never revert post-commit.
        outcome = "COMMITTED"
    elif backup.is_dir() and not root.exists():
        os.replace(backup, root)
        _migration_sync_dir(root.parent)
        outcome = "ROLLED_BACK"
    elif root.is_dir() and not backup.exists():
        outcome = "ROLLED_BACK"  # failure before the first rename
    else:
        raise ValidationFailure("Migration needs inspection; refuse mixed or ambiguous root state")
    if staged.is_dir():
        _migration_remove_storage(root, staged)
    if backup.is_dir():
        _migration_remove_storage(root, backup)
    marker.unlink()
    _migration_sync_dir(root.parent)
    return outcome


def _migrate_v050_copy(root: Path) -> dict[str, Any]:
    from .workspace import check_control_plane, record_phase_boundary
    from .validation import validate_project_directory
    from .registry import REGISTRY_NAMES
    root = root.resolve(strict=True)
    accepted = root / ".harness/state/PROJECT_INPUT_ACCEPTED.yaml"
    immutable = [accepted]
    immutable += sorted((root / ".harness/stages/ACCEPTANCE").glob("*.yaml"))
    immutable += sorted((root / ".harness/runtime/RUNS").glob("*.yaml"))
    immutable += sorted((root / ".harness/stages/PLANS").glob("*.yaml"))
    immutable += sorted((root / ".harness/stages/GATES").glob("*.yaml"))
    immutable_hashes = {str(path.relative_to(root)): sha256_file(path) for path in immutable}
    old_lock_path = root / ".harness/config/PROJECT_LOCK.yaml"
    lock_doc = load_data(old_lock_path)
    lock = lock_doc["project_lock"]
    if (lock.get("harness_distribution"), lock.get("schema_version")) != (V050_ENGINE_VERSION, V050_SCHEMA_VERSION):
        raise ValidationFailure("Only a v0.5.0/6 Project Instance can use this migration")
    state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
    active = state.get("active_run")
    if isinstance(active, dict) and check_control_plane(root, active)["status"] != "PASS":
        raise ValidationFailure("Current manual Run is not protected by a valid control-plane snapshot")
    # Do not transform the accepted v0.5.0 input or reinterpret a former Run.
    versions, digests = _copy_current_registries(root)
    _copy_runtime(root)
    project_path = root / ".harness/config/PROJECT.yaml"
    project_doc = load_data(project_path)
    project_doc["project"]["harness_schema_version"] = SCHEMA_VERSION
    write_data(project_path, project_doc)
    prior = list(lock.get("migrations_applied") or [])
    if EXECUTION_POLICY_MIGRATION_ID in prior:
        raise ValidationFailure("v0.5.1 migration identifier already present in v0.5.0 lock")
    now = utc_now()
    lock.update({
        "harness_distribution": ENGINE_VERSION, "schema_version": SCHEMA_VERSION,
        "registry_versions": versions, "registry_digests": digests,
        "execution": deepcopy(DEFAULT_EXECUTION_POLICY),
        "execution_profile_bindings": {
            "adapter": {"ref": None, "digest": None},
            "sandbox": {"ref": None, "digest": None},
        },
        "migrations_applied": [*prior, EXECUTION_POLICY_MIGRATION_ID],
        "migration_0_5_1_at": now,
    })
    write_data(old_lock_path, lock_doc)
    report = {
        "id": EXECUTION_POLICY_MIGRATION_ID,
        "source_version": V050_ENGINE_VERSION, "target_version": ENGINE_VERSION,
        "applied_at": now, "execution_policy": deepcopy(DEFAULT_EXECUTION_POLICY),
        "immutable_record_count": len(immutable_hashes),
        "immutable_history_digest": f"sha256:{sha256_bytes(canonical_json_bytes(immutable_hashes))}",
        "prior_migrations": prior, "status": "COMPLETED",
    }
    report_path = root / V051_MIGRATION_REPORT_PATH
    if report_path.exists() or report_path.is_symlink():
        raise ValidationFailure("Migration report collision", V051_MIGRATION_REPORT_PATH)
    write_data(report_path, {"migration_report": report})
    if isinstance(active, dict):
        # The migration is a trusted kernel operation; re-seal the *existing*
        # manual Run after updating .harness engine/registry/lock. Its source
        # Run, Task and snapshot refs remain unchanged.
        record_phase_boundary(root, active, phase="ENGINE_V051_MANUAL_MIGRATION",
                              kernel_written_paths=[V051_MIGRATION_REPORT_PATH,
                                  ".harness/config/PROJECT_LOCK.yaml",
                                  ".harness/config/PROJECT.yaml"], recorded_at=now)
    if {str(path.relative_to(root)): sha256_file(path) for path in immutable} != immutable_hashes:
        raise ValidationFailure("v0.5.0 immutable history changed during migration")
    validated = validate_project_directory(root)
    if validated["status"] != "PASS":
        raise ValidationFailure("Migrated project did not pass v0.5.1 project validation", validated.get("errors"))
    return {"status": "MIGRATED", "migration_id": EXECUTION_POLICY_MIGRATION_ID,
            "engine_version": ENGINE_VERSION, "schema_version": SCHEMA_VERSION,
            "execution": deepcopy(DEFAULT_EXECUTION_POLICY),
            "immutable_record_count": len(immutable_hashes), "validation_status": "PASS"}


def _migrate_from_v050(root: Path) -> dict[str, Any]:
    """Crash-recoverable whole-instance swap; no in-place partial migration."""
    from .validation import validate_project_directory
    recovered = _migration_recover(root)
    if not root.is_dir() or root.is_symlink():
        raise ValidationFailure("Migration project directory unavailable", str(root))
    lock = load_data(root / ".harness/config/PROJECT_LOCK.yaml")["project_lock"]
    if (lock.get("harness_distribution"), lock.get("schema_version")) == (ENGINE_VERSION, SCHEMA_VERSION):
        if EXECUTION_POLICY_MIGRATION_ID not in (lock.get("migrations_applied") or []):
            raise ValidationFailure("Current project does not carry exact v0.5.1 migration metadata")
        validation = validate_project_directory(root)
        if validation["status"] != "PASS":
            raise ValidationFailure("Already migrated project failed validation", validation.get("errors"))
        return {"status": "NO_ACTION", "migration_id": EXECUTION_POLICY_MIGRATION_ID,
                "project": str(root), "recovered": recovered, "validation_status": "PASS"}
    if (lock.get("harness_distribution"), lock.get("schema_version")) != (V050_ENGINE_VERSION, V050_SCHEMA_VERSION):
        raise ValidationFailure("Not a compatible v0.5.0 Project Instance")
    preflight = validate_project_directory(root)
    if preflight["status"] != "PASS":
        raise ValidationFailure("Existing v0.5.0 project failed preflight", preflight.get("errors"))
    token = uuid.uuid4().hex
    staged = root.parent / f".{root.name}.ph05110-staged-{token}"
    backup = root.parent / f".{root.name}.ph05110-backup-{token}"
    marker = _migration_marker(root)
    if marker.exists() or marker.is_symlink() or staged.exists() or backup.exists():
        raise ValidationFailure("Concurrent/interrupted v0.5.1 migration storage collision")
    marker_written = False
    try:
        shutil.copytree(root, staged, copy_function=shutil.copy2,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache"))
        result = _migrate_v050_copy(staged)
        _migration_sync_staged_tree(staged)
        _migration_sync_dir(root.parent)
        _migration_persist_marker(marker, {"root": root.name, "staged": staged.name,
                                           "backup": backup.name, "phase": "PREPARED"})
        marker_written = True
        os.replace(root, backup)
        _migration_sync_dir(root.parent)
        _v051_migration_fault("AFTER_OLD_RENAME")
        os.replace(staged, root)
        _migration_sync_dir(root.parent)
        _v051_migration_fault("AFTER_NEW_RENAME")
        _migration_persist_marker(marker, {"root": root.name, "staged": staged.name,
                                           "backup": backup.name, "phase": "COMMITTED"})
        _migration_recover(root)
        return {**result, "project": str(root), "recovered": recovered}
    except Exception:
        if marker_written:
            _migration_recover(root)
        elif staged.is_dir():
            _migration_remove_storage(root, staged)
        raise


def _v051_migration_fault(phase: str) -> None:
    """Patchable fault point for deterministic interrupted-swap tests."""
    del phase


@guarded_mutation
def migrate_project(root: Path, *, input_path: Path | None = None) -> dict[str, Any]:
    """Migrate a compatible v0.4.1 or v0.5.0 project via a validated sibling.

    v0.5.0->v0.5.1 additionally journals its whole-directory swap and recovers
    pre/post commit interruptions without rewriting accepted history.
    """
    # Recover interrupted v0.5.1 migration even if an interrupted rename
    # temporarily left <root> absent. Keep the old v0.4.1 route unchanged.
    root = root.expanduser().absolute()
    if _migration_marker(root).exists() or not root.exists():
        _migration_recover(root)
    if root.is_symlink():
        raise ValidationFailure("Project migration rejects symlink root", str(root))
    root = root.resolve()
    lock_path = root / ".harness/config/PROJECT_LOCK.yaml"
    state_path = root / ".harness/state/CURRENT_STATE.yaml"
    if not lock_path.exists() or not state_path.exists():
        raise ValidationFailure("Project Harness project files are missing", str(root))

    lock_doc = load_data(lock_path)
    lock = lock_doc.get("project_lock") if isinstance(lock_doc, dict) else None
    if not isinstance(lock, dict):
        raise ValidationFailure("Project lock envelope is invalid")

    v051 = (lock.get("harness_distribution") == ENGINE_VERSION and lock.get("schema_version") == SCHEMA_VERSION)
    v050 = (lock.get("harness_distribution") == V050_ENGINE_VERSION and lock.get("schema_version") == V050_SCHEMA_VERSION)
    if v050 or (v051 and EXECUTION_POLICY_MIGRATION_ID in (lock.get("migrations_applied") or [])
                and (root / V051_MIGRATION_REPORT_PATH).is_file()):
        if input_path is not None:
            raise ValidationFailure("v0.5.0 to v0.5.1 migration cannot replace immutable accepted input")
        return _migrate_from_v050(root)
    current = v051
    already_applied = PROJECT_INPUT_MIGRATION_ID in set(lock.get("migrations_applied") or [])
    if current and already_applied:
        validation = validate_handoff_directory(root, check_manifest=False, check_control_plane_state=True)
        if validation["status"] != "PASS":
            raise ValidationFailure(
                "Project records the v0.5.0 migration but does not conform to the current contract",
                validation["errors"],
            )
        return {
            "status": "NO_ACTION",
            "migration_id": PROJECT_INPUT_MIGRATION_ID,
            "project": str(root),
            "engine_version": ENGINE_VERSION,
            "schema_version": SCHEMA_VERSION,
            "validation_status": validation["status"],
        }
    if lock.get("harness_distribution") != LEGACY_ENGINE_VERSION or lock.get("schema_version") != LEGACY_SCHEMA_VERSION:
        raise ValidationFailure(
            "Unsupported project migration source",
            {
                "actual": {"engine": lock.get("harness_distribution"), "schema": lock.get("schema_version")},
                "supported": {"engine": LEGACY_ENGINE_VERSION, "schema": LEGACY_SCHEMA_VERSION},
            },
        )

    preflight = validate_handoff_directory(root, check_manifest=False, check_control_plane_state=False)
    if preflight["status"] != "PASS":
        raise ValidationFailure("Legacy project failed v0.4.1 compatibility validation", preflight["errors"])

    # Resolve and validate migration input before the potentially expensive copy.
    candidate, _, _ = _load_migration_input(root, input_path)
    readiness = validate_project_input(candidate, require_approvals=True)
    if readiness["status"] == "WAITING_INPUT":
        raise WaitingInput("Project target implementation level is required before migration", readiness)
    if readiness["status"] == "WAITING_DECISION":
        raise WaitingDecision("Explicit target or baseline approval is required before migration", readiness)
    if readiness["status"] != "READY_FOR_HANDOFF":
        raise ValidationFailure("Project input cannot be migrated", readiness)

    transaction_parent = Path(tempfile.mkdtemp(prefix=f".{root.name}.v050-migration-", dir=root.parent))
    staged_root = transaction_parent / root.name
    backup_root = root.parent / f".{root.name}.v041-backup-{os.getpid()}"
    try:
        shutil.copytree(
            root,
            staged_root,
            copy_function=shutil.copy2,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache", ".mypy_cache", ".ruff_cache"),
        )
        result = _migrate_project_copy(staged_root, input_path=input_path)
        if backup_root.exists():
            shutil.rmtree(backup_root)
        os.replace(root, backup_root)
        try:
            os.replace(staged_root, root)
        except Exception:
            os.replace(backup_root, root)
            raise
        shutil.rmtree(backup_root)
        result["project"] = str(root)
        assessment = result.get("provisional_assessment")
        if isinstance(assessment, dict) and assessment.get("assessment_path"):
            assessment_path = Path(str(assessment["assessment_path"]))
            if assessment_path.is_absolute():
                assessment_path = assessment_path.relative_to(staged_root)
            assessment["assessment_path"] = str(root / assessment_path)
        return result
    finally:
        if transaction_parent.exists():
            shutil.rmtree(transaction_parent, ignore_errors=True)
        if backup_root.exists() and not root.exists():
            os.replace(backup_root, root)
        elif backup_root.exists():
            shutil.rmtree(backup_root, ignore_errors=True)

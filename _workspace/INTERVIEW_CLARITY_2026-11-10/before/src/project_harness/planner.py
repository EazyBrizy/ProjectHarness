from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from .errors import ValidationFailure
from .stages import stage_path
from .util import id_token, nonempty, unique_preserve


def _item_key(item: dict[str, Any], fallback: str) -> str:
    for field in ("key", "id", "title"):
        if nonempty(item.get(field)):
            return str(item[field])
    return fallback


def normalize_plan(project_input: dict[str, Any], project_token: str) -> dict[str, Any]:
    target_level = str(project_input["implementation"]["target_level"])
    stages = stage_path(target_level)
    active_stage = stages[0]
    work_packages_in = project_input["planning"]["work_packages"]
    work_packages: list[dict[str, Any]] = []
    task_key_to_id: dict[str, str] = {}
    task_title_to_id: dict[str, str] = {}
    tasks_flat: list[dict[str, Any]] = []
    global_index = 0

    # First pass: stable IDs and aliases.
    for wp_index, raw_wp in enumerate(work_packages_in, 1):
        wp = deepcopy(raw_wp)
        wp_key = _item_key(wp, f"wp-{wp_index}")
        raw_wp_id = str(wp.get("id") or "")
        wp_id = raw_wp_id if raw_wp_id.startswith("WP-") else f"WP-{project_token}-{wp_index:03d}"
        wp["id"] = wp_id
        wp["key"] = wp_key
        supplied_wp_stage = wp.get("implementation_stage")
        if supplied_wp_stage not in {None, active_stage}:
            raise ValidationFailure(
                "Initial detailed Work Packages may belong only to the active implementation stage",
                {"work_package": wp_id, "supplied": supplied_wp_stage, "active_stage": active_stage},
            )
        wp["implementation_stage"] = active_stage
        normalized_tasks: list[dict[str, Any]] = []
        for task_index, raw_task in enumerate(wp.get("tasks") or [], 1):
            global_index += 1
            task = deepcopy(raw_task)
            key = _item_key(task, f"wp{wp_index}.task{task_index}")
            raw_task_id = str(task.get("id") or "")
            task_id = raw_task_id if raw_task_id.startswith("TSK-") else f"TSK-{project_token}-{global_index:03d}"
            if key in task_key_to_id or task.get("title") in task_title_to_id:
                raise ValidationFailure("Task keys and titles must be unique", {"task": key})
            task["id"] = task_id
            task["key"] = key
            task["work_package_ref"] = wp_id
            task["original_index"] = global_index
            supplied_task_stage = task.get("implementation_stage")
            if supplied_task_stage not in {None, active_stage}:
                raise ValidationFailure(
                    "Initial atomic Tasks may belong only to the active implementation stage",
                    {"task": task_id, "supplied": supplied_task_stage, "active_stage": active_stage},
                )
            task["implementation_stage"] = active_stage
            task_key_to_id[key] = task_id
            task_key_to_id[task_id] = task_id
            task_title_to_id[str(task.get("title"))] = task_id
            normalized_tasks.append(task)
            tasks_flat.append(task)
        wp["tasks"] = normalized_tasks
        work_packages.append(wp)

    # Second pass: resolve dependency aliases and enrich task contracts.
    for task in tasks_flat:
        raw_deps = task.get("depends_on") or task.get("depends_on_tasks") or []
        deps: list[str] = []
        for raw in raw_deps:
            alias = str(raw)
            resolved = task_key_to_id.get(alias) or task_title_to_id.get(alias)
            if not resolved:
                raise ValidationFailure("Unknown task dependency", {"task": task["id"], "dependency": alias})
            deps.append(resolved)
        task["depends_on_tasks"] = unique_preserve(deps)
        task.pop("depends_on", None)

    order = topological_order(tasks_flat)
    order_index = {task_id: idx for idx, task_id in enumerate(order)}
    tasks_flat.sort(key=lambda task: order_index[task["id"]])

    for position, task in enumerate(tasks_flat):
        task["sequence"] = (position + 1) * 10
        task["status"] = "READY" if position == 0 else "PLANNED"

    tasks_by_wp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for task in tasks_flat:
        tasks_by_wp[task["work_package_ref"]].append(task)
    for wp in work_packages:
        wp["tasks"] = tasks_by_wp[wp["id"]]
        wp["mandatory_task_refs"] = [task["id"] for task in wp["tasks"]]
        wp["status"] = "READY" if wp["tasks"] and wp["tasks"][0]["id"] == order[0] else "PLANNED"

    return {
        "target_level": target_level,
        "active_stage": active_stage,
        "stage_path": stages,
        "work_packages": work_packages,
        "tasks": tasks_flat,
        "task_order": order,
        "task_aliases": {**task_key_to_id, **task_title_to_id},
    }


def topological_order(tasks: list[dict[str, Any]]) -> list[str]:
    by_id = {task["id"]: task for task in tasks}
    permanent: set[str] = set()
    temporary: set[str] = set()
    result: list[str] = []

    def visit(task_id: str, trail: list[str]) -> None:
        if task_id in permanent:
            return
        if task_id in temporary:
            raise ValidationFailure("Task DAG contains a cycle", trail + [task_id])
        temporary.add(task_id)
        for dep in by_id[task_id].get("depends_on_tasks", []):
            if dep not in by_id:
                raise ValidationFailure("Task dependency is absent", {"task": task_id, "dependency": dep})
            visit(dep, trail + [task_id])
        temporary.remove(task_id)
        permanent.add(task_id)
        result.append(task_id)

    # Stable source order resolves otherwise-independent tasks.
    for task in sorted(tasks, key=lambda item: item.get("original_index", 0)):
        visit(task["id"], [])
    return result

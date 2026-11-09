from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .errors import ValidationFailure
from .evidence import (
    classify_evidence_document,
    normalize_evidence_bindings,
    validate_recorded_gate_evidence,
)
from .hashing import parse_manifest, sha256_file, tree_entries
from .planner import topological_order
from .registry import EXPECTED_REGISTRY_VERSIONS, REGISTRY_NAMES, load_registries, validate_implementation_levels
from .resources import distribution_root
from .safety import detect_single_root, inspect_zip, safe_extract_zip
from .platform_fs import ensure_native_path, _native_io_path, native_glob
from .serialization import load_data
from .maintenance import active_maintenance, validate_maintenance_artifacts
from .stage_transactions import recover_stage_transactions, validate_stage_transaction_journals
from .stages import (
    STAGE_GATE_INDEX_PATH,
    STAGE_PLAN_INDEX_PATH,
    STAGE_STATE_PATH,
    load_current_target_level,
    load_stage_state,
    _current_stage_gate_context,
    next_level,
    runtime_continuation,
    validate_stage_acceptance,
    validate_stage_cross_references,
    validate_stage_gate,
    validate_stage_plan,
    validate_stage_state,
)
from .util import ENGINE_VERSION, SCHEMA_VERSION
from .workspace import check_control_plane

FORBIDDEN_ACCOUNTING_KEYS = {
    "provider_billing", "provider_cost", "billing_account", "token_ledger",
    "token_usage", "token_count", "input_tokens", "output_tokens", "cost_estimate",
}
V050_ENGINE_VERSION = "0.5.0"
V050_SCHEMA_VERSION = 6
V050_REGISTRY_VERSIONS = {
    "id_prefixes": 2, "project_profiles": 1, "statuses": 5,
    "request_routing": 2, "capabilities": 1, "contracts": 5,
    "implementation_levels": 1,
}
LEGACY_ENGINE_VERSION = "0.4.1"
LEGACY_SCHEMA_VERSION = 5
LEGACY_REGISTRY_VERSIONS = {
    "id_prefixes": 1,
    "project_profiles": 1,
    "statuses": 4,
    "request_routing": 2,
    "capabilities": 1,
    "contracts": 3,
}
LEGACY_REGISTRY_NAMES = tuple(LEGACY_REGISTRY_VERSIONS)
LEGACY_MIGRATION_ID = "MIG-ENGINE-0.4.1-TO-0.5.0"
OPERATION_JOURNAL_PREFIX = ".harness/runtime/OPERATION_JOURNAL/"


def _check(name: str, ok: bool, details: Any) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "details": details}


def _walk(value: Any, path: str = ""):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            next_path = f"{path}.{key}" if path else str(key)
            yield from _walk(child, next_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _manifest_check(root: Path) -> tuple[bool, dict[str, Any]]:
    path = root / "MANIFEST.sha256"
    if not _native_io_path(path).exists():
        return False, {"missing": "MANIFEST.sha256"}
    expected = parse_manifest(path)
    actual_paths: dict[str, Path] = {}
    for candidate in tree_entries(
        root,
        exclude_dirs={"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"},
        # Ignore only this distribution's root manifest. A nested, embedded
        # documentation MANIFEST.sha256 is itself a hashed release artifact.
        exclude_files=set(),
    ):
        if candidate == path:
            continue
        rel = candidate.relative_to(root).as_posix()
        if candidate.suffix.lower() in {".pyc", ".pyo"} or rel.startswith(OPERATION_JOURNAL_PREFIX):
            continue
        actual_paths[rel] = candidate
    missing = sorted(set(expected) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(expected))
    mismatched = sorted(
        rel for rel in set(expected) & set(actual_paths)
        if sha256_file(actual_paths[rel]) != expected[rel]
    )
    return not missing and not extra and not mismatched, {
        "entries": len(expected),
        "missing": missing,
        "extra": extra,
        "mismatched": mismatched,
        "excluded_runtime_records": [OPERATION_JOURNAL_PREFIX + "*"],
    }


def _resource_copy_check(root: Path) -> tuple[bool, dict[str, Any]]:
    embedded = root / "src/project_harness/resources"
    if not _native_io_path(embedded).is_dir():
        return True, {"layout": "installed", "checked": 0, "errors": []}
    errors: list[str] = []
    checked = 0
    for folder in ("registries", "schemas", "templates", "fixtures", "skills"):
        source_dir = root / folder
        embedded_dir = embedded / folder
        source_files = {
            path.relative_to(source_dir).as_posix(): path
            for path in native_glob(source_dir, "*", recursive=True) if _native_io_path(path).is_file() and path.suffix.lower() not in {".pyc", ".pyo"}
        }
        embedded_files = {
            path.relative_to(embedded_dir).as_posix(): path
            for path in native_glob(embedded_dir, "*", recursive=True) if _native_io_path(path).is_file() and path.suffix.lower() not in {".pyc", ".pyo"}
        } if _native_io_path(embedded_dir).is_dir() else {}
        for rel in sorted(set(source_files) | set(embedded_files)):
            checked += 1
            if rel not in source_files:
                errors.append(f"{folder}/{rel}: embedded-only")
            elif rel not in embedded_files:
                errors.append(f"{folder}/{rel}: source-only")
            elif sha256_file(source_files[rel]) != sha256_file(embedded_files[rel]):
                errors.append(f"{folder}/{rel}: digest mismatch")
    version_source = root / "VERSION"
    version_embedded = embedded / "VERSION"
    if _native_io_path(version_source).exists() and _native_io_path(version_embedded).exists():
        checked += 1
        if sha256_file(version_source) != sha256_file(version_embedded):
            errors.append("VERSION: source/embedded digest mismatch")
    return not errors, {"layout": "source", "checked": checked, "errors": errors}


def doctor(root: Path | None = None, *, check_manifest: bool = True) -> dict[str, Any]:
    root = (root or distribution_root()).resolve()
    checks: list[dict[str, Any]] = []
    try:
        registries = load_registries(root)
        checks.append(_check("Canonical registries", True, {name: registries[name]["registry"]["version"] for name in REGISTRY_NAMES}))
    except Exception as exc:
        checks.append(_check("Canonical registries", False, str(exc)))
    schema_errors: list[str] = []
    schema_count = 0
    for path in sorted(native_glob(root / "schemas", "*.json")):
        schema_count += 1
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict) or value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                schema_errors.append(f"{path.name}: missing Draft 2020-12 declaration")
        except Exception as exc:
            schema_errors.append(f"{path.name}: {exc}")
    checks.append(_check("Bundled schemas", not schema_errors and schema_count >= 3, {"count": schema_count, "errors": schema_errors}))
    skill_errors: list[str] = []
    skills = list(native_glob(root / "skills", "SKL-*.yaml"))
    for path in skills:
        try:
            skill = load_data(path)["skill"]
            if skill.get("status") != "ACTIVE":
                skill_errors.append(f"{path.name}: status={skill.get('status')}")
        except Exception as exc:
            skill_errors.append(f"{path.name}: {exc}")
    checks.append(_check("Seed ACTIVE skills", not skill_errors and bool(skills), {"count": len(skills), "errors": skill_errors}))
    if (_native_io_path(root / "src/project_harness/cli.py")).exists():
        required = ["project-harness.py", "src/project_harness/cli.py", "templates/GPT_PREPARATION_INSTRUCTIONS.md"]
    else:
        required = ["templates/GPT_PREPARATION_INSTRUCTIONS.md", "fixtures/demo_project_input.json"]
    missing = [item for item in required if not (_native_io_path(root / item)).exists()]
    checks.append(_check("Entry points and browser preparation template", not missing, {"missing": missing, "layout": "source" if (_native_io_path(root / "src")).exists() else "installed"}))
    resources_ok, resource_details = _resource_copy_check(root)
    checks.append(_check("Source and embedded resources", resources_ok, resource_details))
    if check_manifest and (_native_io_path(root / "MANIFEST.sha256")).exists():
        ok, details = _manifest_check(root)
        checks.append(_check("Distribution manifest", ok, details))
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {"version": ENGINE_VERSION, "schema_version": SCHEMA_VERSION, "status": status, "root": str(root), "checks": checks}


def _load_handoff_registries(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    statuses = load_data(root / ".harness/registries/statuses.yaml")
    contracts = load_data(root / ".harness/registries/contracts.yaml")
    status_registry = statuses.get("registry") if isinstance(statuses, dict) else None
    contract_registry = contracts.get("registry") if isinstance(contracts, dict) else None
    if not isinstance(status_registry, dict) or not isinstance(contract_registry, dict):
        raise ValidationFailure("Handoff status/contracts registry envelope is invalid")
    return status_registry, contract_registry


def _status_allowed(groups: dict[str, Any], group: str, status: Any) -> bool:
    return isinstance(status, str) and status in set(groups.get(group) or [])


def _legacy_status_allowed(
    *,
    entity: str,
    status: Any,
    rel: str,
    compatibility_mode: bool,
    migrated_legacy: bool,
    current_task_paths: set[str],
    completed_at: Any,
    lock_created_at: Any,
) -> tuple[bool, str | None]:
    if status != "COMPLETED" or entity not in {"task", "run"}:
        return False, None
    target = "DONE" if entity == "task" else "SUCCEEDED"
    if compatibility_mode:
        return True, target
    if not migrated_legacy:
        return False, None
    # A migrated v0.4.1 handoff may retain immutable pre-migration history, but
    # a current Task revision or a newly completed Run never receives the map.
    if entity == "task" and rel not in current_task_paths:
        if completed_at and lock_created_at and str(completed_at) <= str(lock_created_at):
            return True, target
    if entity == "run" and completed_at and lock_created_at and str(completed_at) <= str(lock_created_at):
        return True, target
    return False, None


def _validate_entity_statuses(
    root: Path,
    *,
    groups: dict[str, Any],
    compatibility_mode: bool,
    migrated_legacy: bool,
    lock_created_at: Any,
) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    mappings: list[dict[str, Any]] = []
    task_index_path = root / ".harness/tasks/INDEX.yaml"
    current_task_paths: set[str] = set()
    if _native_io_path(task_index_path).exists():
        try:
            current_task_paths = set(load_data(task_index_path)["task_index"].get("current", {}).values())
        except Exception:
            pass

    specs = [
        (root / ".harness/tasks", "TSK-*@*.yaml", "task", "task"),
        (root / ".harness/runtime/RUNS", "RUN-*.yaml", "run", "run"),
        (root / ".harness/work-packages", "WP-*@*.yaml", "work_package", "work_package"),
        (root / ".harness/canonical/DECISIONS", "DEC-*@*.yaml", "decision", "decision"),
    ]
    for base, pattern, envelope, group in specs:
        if not _native_io_path(base).exists():
            continue
        for path in sorted(native_glob(base, pattern)):
            rel = path.relative_to(root).as_posix()
            try:
                value = load_data(path)
                entity = value.get(envelope) if isinstance(value, dict) else None
                if not isinstance(entity, dict):
                    errors.append(f"{rel}: missing {envelope} envelope")
                    continue
                status = entity.get("status")
                if _status_allowed(groups, group, status):
                    continue
                if compatibility_mode and envelope == "decision" and status in {"ACCEPTED", "REJECTED", "SUPERSEDED"}:
                    # v0.4.0 persisted Decision records before registering their
                    # lifecycle group in statuses.yaml.
                    continue
                allowed, interpreted = _legacy_status_allowed(
                    entity=envelope,
                    status=status,
                    rel=rel,
                    compatibility_mode=compatibility_mode,
                    migrated_legacy=migrated_legacy,
                    current_task_paths=current_task_paths,
                    completed_at=entity.get("completed_at"),
                    lock_created_at=lock_created_at,
                )
                if allowed:
                    mappings.append({
                        "path": rel,
                        "entity": envelope,
                        "id": entity.get("id"),
                        "legacy_status": "COMPLETED",
                        "interpreted_as": interpreted,
                        "file_rewritten": False,
                    })
                else:
                    errors.append(f"{rel}: {envelope}.status={status!r} is not in registry.{group}")
            except Exception as exc:
                errors.append(f"{rel}: {exc}")

    result_schema_path = root / ".harness/engine/project_harness/resources/schemas/agent_task_result.schema.json"
    result_statuses = {"COMPLETED", "BLOCKED", "FAILED"}
    if _native_io_path(result_schema_path).exists():
        try:
            schema = json.loads(_native_io_path(result_schema_path).read_text(encoding="utf-8"))
            result_statuses = set(schema["properties"]["status"]["enum"])
        except Exception as exc:
            errors.append(f"{result_schema_path.relative_to(root)}: cannot read Agent Result enum: {exc}")
    results_dir = root / ".harness/runtime/AGENT_RESULTS"
    if _native_io_path(results_dir).exists():
        for path in sorted(native_glob(results_dir, "*.json")):
            rel = path.relative_to(root).as_posix()
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                if value.get("status") not in result_statuses:
                    errors.append(f"{rel}: Agent Result status={value.get('status')!r} is invalid")
            except Exception as exc:
                errors.append(f"{rel}: {exc}")
    return errors, mappings


def _validate_decisions_and_brownfield(
    root: Path,
    *,
    project: dict[str, Any],
    status_groups: dict[str, Any],
    contract_registry: dict[str, Any],
    compatibility_mode: bool,
    migrated_legacy: bool,
) -> tuple[bool, dict[str, Any]]:
    errors: list[str] = []
    decision_contract = (contract_registry.get("entities") or {}).get("decision")
    expected_contract = {
        "id_prefix": "DEC",
        "persistence": "PERSISTENT",
        "lifecycle": "decision",
        "storage_path": ".harness/canonical/DECISIONS/{id}@{revision}.yaml",
        "revision_policy": "IMMUTABLE",
    }
    legacy_contract_gap = False
    if not isinstance(decision_contract, dict):
        if compatibility_mode:
            legacy_contract_gap = True
        else:
            errors.append("decision contract is not registered")
    else:
        for key, expected in expected_contract.items():
            if decision_contract.get(key) != expected:
                errors.append(f"decision contract {key}={decision_contract.get(key)!r}, expected {expected!r}")

    decisions: dict[str, dict[str, Any]] = {}
    for path in sorted(native_glob(root / ".harness/canonical/DECISIONS", "DEC-*@*.yaml")):
        rel = path.relative_to(root).as_posix()
        try:
            value = load_data(path).get("decision")
            if not isinstance(value, dict):
                errors.append(f"{rel}: missing decision envelope")
                continue
            expected_name = f"{value.get('id')}@{value.get('revision')}.yaml"
            if path.name != expected_name:
                errors.append(f"{rel}: storage path does not match immutable decision id/revision")
            decision_status = value.get("status")
            if not _status_allowed(status_groups, "decision", decision_status):
                if not (compatibility_mode and decision_status in {"ACCEPTED", "REJECTED", "SUPERSEDED"}):
                    errors.append(f"{rel}: invalid decision status {decision_status!r}")
            decisions[str(value.get("id"))] = value
        except Exception as exc:
            errors.append(f"{rel}: {exc}")

    mode = project.get("lifecycle_mode")
    baselines = list(native_glob(root / ".harness/canonical/DEFINITION/BROWNFIELD", "BFB-*@*.yaml"))
    legacy_brownfield_approval_gap = False
    legacy_brownfield_revisions: list[str] = []
    if mode in {"BROWNFIELD", "HYBRID"}:
        if not baselines:
            errors.append("Brownfield/Hybrid project has no accepted Brownfield Baseline")
        parsed_baselines: list[tuple[Path, dict[str, Any]]] = []
        for path in baselines:
            try:
                bfb = load_data(path).get("brownfield_baseline")
                if isinstance(bfb, dict):
                    parsed_baselines.append((path, bfb))
            except Exception:
                pass
        latest_revision_by_id: dict[str, int] = {}
        for _path, bfb in parsed_baselines:
            baseline_id = str(bfb.get("id"))
            latest_revision_by_id[baseline_id] = max(latest_revision_by_id.get(baseline_id, 0), int(bfb.get("revision", 0)))
        for path in baselines:
            rel = path.relative_to(root).as_posix()
            try:
                bfb = load_data(path).get("brownfield_baseline")
                if not isinstance(bfb, dict):
                    errors.append(f"{rel}: invalid Brownfield Baseline envelope")
                    continue
                decision_id = bfb.get("accepted_by")
                accepted_at = bfb.get("accepted_at")
                if compatibility_mode and (not decision_id or not accepted_at):
                    legacy_brownfield_approval_gap = True
                    continue
                is_historical_migrated = (
                    migrated_legacy
                    and int(bfb.get("revision", 0)) < latest_revision_by_id.get(str(bfb.get("id")), 0)
                )
                if is_historical_migrated and (not decision_id or not accepted_at):
                    legacy_brownfield_revisions.append(rel)
                    continue
                decision = decisions.get(str(decision_id))
                if not decision:
                    errors.append(f"{rel}: accepted_by does not resolve to an immutable Decision")
                    continue
                if decision.get("kind") != "BROWNFIELD_BASELINE_APPROVAL":
                    errors.append(f"{rel}: accepted_by Decision has wrong kind")
                if decision.get("subject_ref") != f"{bfb.get('id')}@{bfb.get('revision')}":
                    errors.append(f"{rel}: Decision subject_ref does not reference this baseline")
                if decision.get("approved_at") != accepted_at:
                    errors.append(f"{rel}: accepted_at differs from Decision approved_at")
                if not decision.get("actor"):
                    errors.append(f"{rel}: Decision actor is missing")
            except Exception as exc:
                errors.append(f"{rel}: {exc}")
    elif baselines:
        errors.append("Greenfield project unexpectedly contains a Brownfield Baseline")
    return not errors, {
        "decisions": len(decisions),
        "brownfield_baselines": len(baselines),
        "legacy_contract_gap": legacy_contract_gap,
        "legacy_brownfield_approval_gap": legacy_brownfield_approval_gap,
        "legacy_brownfield_revisions": legacy_brownfield_revisions,
        "errors": errors,
    }


def _validate_stage_artifacts(
    root: Path,
    *,
    project: dict[str, Any],
    project_state: dict[str, Any],
    status_groups: dict[str, Any],
    contract_registry: dict[str, Any],
    migrated_legacy: bool = False,
) -> tuple[bool, dict[str, Any]]:
    errors: list[str] = []
    expected_contracts = {
        "stage_state": {
            "id_prefix": None,
            "persistence": "PERSISTENT",
            "lifecycle": "VERSIONED_CONFIG",
            "storage_path": ".harness/stages/STAGE_STATE.yaml",
            "revision_policy": "VERSIONED_CONFIG",
        },
        "stage_plan": {
            "id_prefix": "STG",
            "persistence": "PERSISTENT",
            "lifecycle": "implementation_stage",
            "storage_path": ".harness/stages/PLANS/{id}@{revision}.yaml",
            "revision_policy": "VERSIONED",
        },
        "stage_gate": {
            "id_prefix": "GATE",
            "persistence": "PERSISTENT",
            "lifecycle": "verification",
            "storage_path": ".harness/stages/GATES/{id}@{revision}.yaml",
            "revision_policy": "VERSIONED",
        },
        "stage_acceptance": {
            "id_prefix": "VAL",
            "persistence": "PERSISTENT",
            "lifecycle": "IMMUTABLE_RECORD",
            "storage_path": ".harness/stages/ACCEPTANCE/{id}@{revision}.yaml",
            "revision_policy": "IMMUTABLE",
        },
        "maturity_assessment": {
            "id_prefix": "VAL",
            "persistence": "PERSISTENT",
            "lifecycle": "IMMUTABLE_RECORD",
            "storage_path": ".harness/stages/ASSESSMENTS/{id}@{revision}.yaml",
            "revision_policy": "IMMUTABLE",
        },
        "verification_evidence": {
            "id_prefix": "EVD",
            "persistence": "PERSISTENT",
            "lifecycle": "IMMUTABLE_RECORD",
            "storage_path": ".harness/evidence/{id}.yaml",
            "revision_policy": "IMMUTABLE",
        },
    }
    entities = contract_registry.get("entities") or {}
    for name, expected in expected_contracts.items():
        actual = entities.get(name)
        if not isinstance(actual, dict):
            errors.append(f"{name}: contract is not registered")
            continue
        for field, value in expected.items():
            if actual.get(field) != value:
                errors.append(f"{name}.{field}={actual.get(field)!r}, expected {value!r}")

    try:
        level_registry = load_data(root / ".harness/registries/implementation_levels.yaml")
        validate_implementation_levels(level_registry)
    except Exception as exc:
        errors.append(f"implementation level registry: {exc}")

    try:
        state_doc = load_data(root / STAGE_STATE_PATH)
        validate_stage_state(state_doc)
        implementation = state_doc["implementation"]
    except Exception as exc:
        errors.append(f"Stage State: {exc}")
        return False, {"errors": errors}

    canonical_target = load_current_target_level(root, stage_state=implementation)
    # PROJECT_INPUT_ACCEPTED is immutable intake history. Only the two mutable
    # projections below must equal the canonical current-cycle target in Stage State.
    if project.get("target_implementation_level") != canonical_target:
        errors.append("PROJECT.target_implementation_level differs from canonical Stage State target")
    if project.get("stage_state_ref") != STAGE_STATE_PATH.as_posix():
        errors.append("PROJECT.stage_state_ref is not canonical")
    if project_state.get("active_stage") != implementation.get("active_stage"):
        errors.append("CURRENT_STATE.active_stage differs from Stage State")
    if project_state.get("target_implementation_level") != canonical_target:
        errors.append("CURRENT_STATE.target_implementation_level differs from canonical Stage State target")
    if not _status_allowed(status_groups, "project_execution", project_state.get("project_status")):
        errors.append(f"CURRENT_STATE.project_status={project_state.get('project_status')!r} is not in project_execution")

    try:
        cross = validate_stage_cross_references(root)
        errors.extend(cross.get("errors") or [])
    except Exception as exc:
        cross = {"status": "FAIL", "errors": [str(exc)]}
        errors.append(f"Stage cross references: {exc}")

    artifact_counts = {"plans": 0, "gates": 0, "acceptances": 0, "assessments": 0, "evidence_normalized": 0, "evidence_legacy": 0, "evidence_apply": 0}
    for path in sorted(native_glob(root / ".harness/stages/PLANS", "STG-*@*.yaml")):
        artifact_counts["plans"] += 1
        try:
            value = load_data(path)
            validate_stage_plan(value)
            entity = value["stage_plan"]
            if path.name != f"{entity['id']}@{entity['revision']}.yaml":
                errors.append(f"{path.relative_to(root)}: Stage Plan filename mismatch")
            if not _status_allowed(status_groups, "implementation_stage", entity.get("status")):
                errors.append(f"{path.relative_to(root)}: invalid Stage Plan status")
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    for path in sorted(native_glob(root / ".harness/stages/GATES", "GATE-*@*.yaml")):
        artifact_counts["gates"] += 1
        try:
            value = load_data(path)
            entity = value.get("stage_gate") if isinstance(value, dict) else None
            validate_stage_gate(value, require_closure=isinstance(entity, dict) and entity.get("status") == "ACCEPTED")
            entity = value["stage_gate"]
            if path.name != f"{entity['id']}@{entity['revision']}.yaml":
                errors.append(f"{path.relative_to(root)}: Stage Gate filename mismatch")
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")

    for path in sorted(native_glob(root / ".harness/evidence", "*.yaml")):
        rel = path.relative_to(root).as_posix()
        try:
            document = load_data(path)
            if isinstance(document, dict) and "apply_evidence" in document:
                # v0.5.1 Apply Evidence has its own strict @1 schema and
                # envelope; it is NOT Stage Gate `verification_evidence`.
                # It must be validated, not silently skipped or incorrectly
                # rejected as legacy Gate evidence.
                from .project_input import _validate_schema_node
                from .resources import resource_path
                schema = json.loads(resource_path("schemas", "apply_evidence.schema.json").read_text(encoding="utf-8"))
                issues = _validate_schema_node(document, schema, schema)
                body = document.get("apply_evidence")
                if issues or not isinstance(body, dict) or path.name != str(body.get("id")) + ".yaml":
                    errors.append(f"{rel}: invalid exact Apply Evidence contract or ID/path binding")
                else:
                    artifact_counts["evidence_apply"] += 1
                continue
            classification = classify_evidence_document(root, document, verify_sources=True)
            kind = classification.get("classification")
            if kind == "NORMALIZED":
                artifact_counts["evidence_normalized"] += 1
                body = classification["body"]
                if path.name != f"{body['id']}.yaml":
                    errors.append(f"{rel}: normalized evidence filename does not match internal id/ref")
            elif kind == "LEGACY":
                artifact_counts["evidence_legacy"] += 1
            else:
                errors.append(f"{rel}: invalid normalized evidence: {classification.get('error')}")
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
    accepted_levels: list[str] = []
    for path in sorted(native_glob(root / ".harness/stages/ACCEPTANCE", "VAL-*@*.yaml")):
        artifact_counts["acceptances"] += 1
        try:
            value = load_data(path)
            validate_stage_acceptance(value)
            entity = value["stage_acceptance"]
            accepted_levels.append(str(entity["level"]))
            if path.name != f"{entity['id']}@{entity['revision']}.yaml":
                errors.append(f"{path.relative_to(root)}: immutable acceptance filename mismatch")
            decision_id = str(entity["decision_ref"]).split("@")[0]
            if not list(native_glob(root / ".harness/canonical/DECISIONS", f"{decision_id}@*.yaml")):
                errors.append(f"{path.relative_to(root)}: referenced Decision is missing")

            gate_ref = entity.get("gate_ref")
            if not isinstance(gate_ref, str) or "@" not in gate_ref:
                raise ValidationFailure("Stage Acceptance Report gate_ref is missing or not revisioned", gate_ref)
            gate_id, raw_revision = gate_ref.rsplit("@", 1)
            if not raw_revision.isdigit() or int(raw_revision) < 1 or gate_ref != f"{gate_id}@{int(raw_revision)}":
                raise ValidationFailure("Stage Acceptance Report gate_ref is not canonical", gate_ref)
            gate_path = root / f".harness/stages/GATES/{gate_id}@{int(raw_revision)}.yaml"
            if _native_io_path(gate_path).is_symlink() or not _native_io_path(gate_path).is_file():
                raise ValidationFailure("Stage Acceptance Report referenced Gate is missing", gate_ref)
            gate_doc = load_data(gate_path)
            gate = gate_doc.get("stage_gate") if isinstance(gate_doc, dict) else None
            if not isinstance(gate, dict):
                raise ValidationFailure("Referenced accepted Gate envelope is invalid", gate_ref)
            validate_stage_gate(gate_doc, require_closure=True)
            if gate.get("status") != "ACCEPTED":
                raise ValidationFailure("Stage Acceptance Report references a non-accepted Gate", gate_ref)
            if gate.get("level") != entity.get("level"):
                raise ValidationFailure("Stage Acceptance Report level differs from accepted Gate", gate_ref)
            if gate.get("base_revision") != entity.get("baseline_revision"):
                raise ValidationFailure("Stage Acceptance Report baseline differs from accepted Gate", gate_ref)
            if sorted(gate.get("evidence_refs") or []) != sorted(entity.get("evidence_refs") or []):
                raise ValidationFailure("Stage Acceptance Report evidence_refs differ from accepted Gate", gate_ref)
            gate_bindings = normalize_evidence_bindings(gate.get("evidence_bindings"))
            report_bindings = normalize_evidence_bindings(entity.get("evidence_bindings"))
            if gate_bindings != report_bindings:
                raise ValidationFailure("Stage Acceptance Report evidence bindings differ from accepted Gate", gate_ref)
            current_bindings = validate_recorded_gate_evidence(
                root,
                level=str(gate["level"]),
                criteria_results=gate.get("criteria_results"),
                global_evidence_refs=gate.get("evidence_refs") or [],
                base_revision=str(gate["base_revision"]),
                overrides=gate.get("hard_constraint_overrides") or [],
                recorded_bindings=gate_bindings,
            )
            if current_bindings != report_bindings:
                raise ValidationFailure("Stage Acceptance Report evidence snapshot no longer resolves", gate_ref)
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    for path in sorted(native_glob(root / ".harness/stages/ASSESSMENTS", "VAL-*@*.yaml")):
        artifact_counts["assessments"] += 1
        try:
            value = load_data(path)
            assessment = value.get("maturity_assessment") if isinstance(value, dict) else None
            if not isinstance(assessment, dict):
                raise ValidationFailure("Maturity Assessment envelope is invalid")
            required = {
                "id", "revision", "repository_revision", "claimed_current_level",
                "observed_candidate_level", "highest_satisfied_candidate_level",
                "previous_highest_accepted_level", "proposed_active_stage", "target_level",
                "confidence", "dimensions", "blocking_gaps", "recommended_route",
            }
            missing = sorted(required - set(assessment))
            if missing:
                raise ValidationFailure("Maturity Assessment is missing fields", missing)
            if not isinstance(assessment.get("revision"), int) or assessment["revision"] < 1:
                raise ValidationFailure("Maturity Assessment revision must be a positive integer")
            if path.name != f"{assessment['id']}@{assessment['revision']}.yaml":
                errors.append(f"{path.relative_to(root)}: immutable assessment filename mismatch")
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")

    canonical_ids = {
        str(item.get("id"))
        for item in (level_registry.get("registry") or {}).get("levels", [])
        if isinstance(item, dict)
    }

    # A v0.4.1 -> v0.5.0 migration preserves immutable historical revisions.
    # Current logical revisions must carry implementation_stage; legacy historical
    # files may retain their original schema and are never silently rewritten.
    current_stage_paths: set[str] = set()
    try:
        task_index = load_data(root / ".harness/tasks/INDEX.yaml").get("task_index") or {}
        wp_index = load_data(root / ".harness/work-packages/INDEX.yaml").get("work_package_index") or {}
        current_stage_paths.update(str(rel) for rel in (task_index.get("current") or {}).values())
        current_stage_paths.update(str(rel) for rel in (wp_index.get("current") or {}).values())
        for rel in (task_index.get("current") or {}).values():
            task = load_data(root / str(rel)).get("task") or {}
            for field, folder in (
                ("prompt_plan_ref", ".harness/prompts/PLANS"),
                ("context_plan_ref", ".harness/context/PLANS"),
                ("verification_profile_ref", ".harness/verification/PROFILES"),
            ):
                ref = task.get(field)
                if ref:
                    current_stage_paths.add(f"{folder}/{ref}.yaml")
        for rel in (wp_index.get("current") or {}).values():
            wp = load_data(root / str(rel)).get("work_package") or {}
            ref = wp.get("dependency_graph_ref")
            if ref:
                current_stage_paths.add(f".harness/dags/{ref}.yaml")
        active_run = project_state.get("active_run") or {}
        if active_run.get("run_plan_path"):
            current_stage_paths.add(str(active_run["run_plan_path"]))
    except Exception as exc:
        errors.append(f"current implementation-stage reference inventory: {exc}")

    field_specs = [
        (root / ".harness/tasks", "TSK-*@*.yaml", "task"),
        (root / ".harness/work-packages", "WP-*@*.yaml", "work_package"),
        (root / ".harness/prompts/PLANS", "PPL-*@*.yaml", "prompt_plan"),
        (root / ".harness/context/PLANS", "CTX-*@*.yaml", "context_plan"),
        (root / ".harness/verification/PROFILES", "VFP-*@*.yaml", "verification_profile"),
        (root / ".harness/dags", "DAG-*@*.yaml", "dependency_graph"),
        (root / ".harness/runtime/RUN_PLANS", "RNP-*@*.yaml", "run_plan"),
    ]
    for base, pattern, envelope in field_specs:
        for path in sorted(native_glob(base, pattern)):
            try:
                entity = load_data(path).get(envelope)
                stage = entity.get("implementation_stage") if isinstance(entity, dict) else None
                rel = path.relative_to(root).as_posix()
                historical_legacy = migrated_legacy and rel not in current_stage_paths and stage is None
                if stage not in canonical_ids and not historical_legacy:
                    errors.append(f"{rel}: implementation_stage is missing or invalid")
            except Exception as exc:
                errors.append(f"{path.relative_to(root)}: {exc}")

    accepted_set = set(accepted_levels)
    if len(accepted_set) != len(accepted_levels):
        errors.append(f"Duplicate Stage Acceptance reports by level: {accepted_levels}")
    ordered_acceptances = [level for level in implementation["stage_path"] if level in accepted_set]
    expected_acceptance_order = implementation["stage_path"][:len(accepted_set)]
    if accepted_levels and ordered_acceptances != expected_acceptance_order:
        errors.append(f"Stage Acceptance sequence is not a canonical prefix: {ordered_acceptances}")
    return not errors, {
        "target_level": implementation.get("target_level"),
        "active_stage": implementation.get("active_stage"),
        "highest_accepted_level": implementation.get("highest_accepted_level"),
        "artifact_counts": artifact_counts,
        "cross_references": cross,
        "errors": errors,
    }


def validate_handoff_directory(
    root: Path,
    *,
    check_manifest: bool = True,
    check_control_plane_state: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    checks: list[dict[str, Any]] = []
    legacy_status_mappings: list[dict[str, Any]] = []
    required = [
        "CODEX_START.md", "AGENTS.md", "HANDOFF_SUMMARY.md", "PROJECT.md", "ARCHITECTURE.md", "TECHNOLOGY.md", "ROADMAP.md", "STATUS.md",
        ".harness/config/PROJECT.yaml", ".harness/config/PROJECT_LOCK.yaml",
        ".harness/state/CURRENT_STATE.yaml", ".harness/state/NEXT_TASK.yaml",
        ".harness/tasks/INDEX.yaml", ".harness/work-packages/INDEX.yaml",
        ".harness/skills/registry.yaml", ".harness/engine/project-harness.py",
    ]
    missing = [item for item in required if not (_native_io_path(root / item)).exists()]
    checks.append(_check("Required handoff artifacts", not missing, {"missing": missing}))

    symlinks = [p.relative_to(root).as_posix() for p in native_glob(root, "*", recursive=True) if _native_io_path(p).is_symlink()]
    checks.append(_check("No symlinks", not symlinks, {"symlinks": symlinks}))

    parse_errors: list[str] = []
    parsed_values: list[tuple[str, Any]] = []
    for path in sorted(native_glob(root, "*", recursive=True)):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(OPERATION_JOURNAL_PREFIX):
            # Journal integrity is checked by the control-plane protocol below.
            continue
        if _native_io_path(path).is_file() and path.suffix.lower() in {".yaml", ".yml", ".json"}:
            try:
                value = load_data(path)
                parsed_values.append((rel, value))
            except Exception as exc:
                parse_errors.append(f"{rel}: {exc}")
    checks.append(_check("Machine-readable files parse", not parse_errors, {"parsed": len(parsed_values), "errors": parse_errors[:20]}))

    compatibility_mode = False
    migrated_legacy = False
    if not missing:
        project = load_data(root / ".harness/config/PROJECT.yaml")["project"]
        lock = load_data(root / ".harness/config/PROJECT_LOCK.yaml")["project_lock"]
        engine = lock.get("harness_distribution")
        schema = lock.get("schema_version")
        compatibility_mode = engine == LEGACY_ENGINE_VERSION and schema == LEGACY_SCHEMA_VERSION
        v050_compatibility = engine == V050_ENGINE_VERSION and schema == V050_SCHEMA_VERSION
        current_mode = engine == ENGINE_VERSION and schema == SCHEMA_VERSION
        migrated_legacy = (
            LEGACY_MIGRATION_ID in set(lock.get("migrations_applied") or [])
            and lock.get("migrated_from") == LEGACY_ENGINE_VERSION
        )
        legacy_cutoff = lock.get("migrated_at") if migrated_legacy else lock.get("created_at")
        checks.append(_check(
            "Engine/schema lock",
            current_mode or compatibility_mode or v050_compatibility,
            {
                "engine": engine,
                "schema": schema,
                "mode": ("LEGACY_V0.4.1_COMPATIBILITY" if compatibility_mode
                         else "V0.5.0_MANUAL_COMPATIBILITY" if v050_compatibility
                         else "CURRENT" if current_mode else "UNSUPPORTED"),
                "expected_current": {"engine": ENGINE_VERSION, "schema": SCHEMA_VERSION},
            },
        ))
        if current_mode or v050_compatibility:
            stage_required = [
                STAGE_STATE_PATH.as_posix(),
                STAGE_PLAN_INDEX_PATH.as_posix(),
                STAGE_GATE_INDEX_PATH.as_posix(),
                ".harness/registries/implementation_levels.yaml",
            ]
            stage_missing = [item for item in stage_required if not (_native_io_path(root / item)).exists()]
            checks.append(_check("Required implementation-stage artifacts", not stage_missing, {"missing": stage_missing}))

        version_errors: list[str] = []
        digest_errors: list[str] = []
        expected_versions = (LEGACY_REGISTRY_VERSIONS if compatibility_mode else
                             V050_REGISTRY_VERSIONS if v050_compatibility else EXPECTED_REGISTRY_VERSIONS)
        registry_names = LEGACY_REGISTRY_NAMES if compatibility_mode else REGISTRY_NAMES
        for name in registry_names:
            expected_version = expected_versions[name]
            actual_version = (lock.get("registry_versions") or {}).get(name)
            if actual_version != expected_version:
                version_errors.append(f"{name}: {actual_version} != {expected_version}")
            path = root / ".harness/registries" / f"{name}.yaml"
            try:
                file_version = load_data(path)["registry"].get("version") if _native_io_path(path).exists() else None
            except Exception:
                file_version = None
            if file_version != actual_version:
                version_errors.append(f"{name}: registry file version {file_version} != lock {actual_version}")
            expected_digest = (lock.get("registry_digests") or {}).get(name)
            actual_digest = f"sha256:{sha256_file(path)}" if _native_io_path(path).exists() else None
            if expected_digest != actual_digest:
                digest_errors.append(f"{name}: digest mismatch")
        checks.append(_check("Exact registry versions", not version_errors, {"errors": version_errors, "compatibility_mode": compatibility_mode}))
        checks.append(_check("Exact registry digests", not digest_errors, {"errors": digest_errors}))

        try:
            status_registry, contract_registry = _load_handoff_registries(root)
            groups = status_registry.get("groups") or {}
            status_errors, legacy_status_mappings = _validate_entity_statuses(
                root,
                groups=groups,
                compatibility_mode=compatibility_mode,
                migrated_legacy=migrated_legacy,
                lock_created_at=legacy_cutoff,
            )
            checks.append(_check("Registry-driven entity statuses", not status_errors, {"errors": status_errors, "legacy_status_mappings": legacy_status_mappings}))
            decision_ok, decision_details = _validate_decisions_and_brownfield(
                root,
                project=project,
                status_groups=groups,
                contract_registry=contract_registry,
                compatibility_mode=compatibility_mode,
                migrated_legacy=migrated_legacy,
            )
            checks.append(_check("Decision contract and Brownfield approval", decision_ok, decision_details))
            if current_mode or v050_compatibility:
                stage_ok, stage_details = _validate_stage_artifacts(
                    root,
                    project=project,
                    project_state=load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"],
                    status_groups=groups,
                    contract_registry=contract_registry,
                    migrated_legacy=migrated_legacy,
                )
                checks.append(_check("Implementation Stage contracts and invariants", stage_ok, stage_details))
        except Exception as exc:
            checks.append(_check("Registry-driven entity statuses", False, {"errors": [str(exc)], "legacy_status_mappings": []}))
            checks.append(_check("Decision contract and Brownfield approval", False, {"errors": [str(exc)]}))
            if current_mode or v050_compatibility:
                checks.append(_check("Implementation Stage contracts and invariants", False, {"errors": [str(exc)]}))

        task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
        tasks: list[dict[str, Any]] = []
        task_errors: list[str] = []
        for task_id in task_index.get("order") or []:
            rel = (task_index.get("current") or {}).get(task_id)
            if not rel or not (_native_io_path(root / rel)).exists():
                task_errors.append(f"{task_id}: missing current path")
                continue
            task = load_data(root / rel).get("task")
            if not isinstance(task, dict) or task.get("id") != task_id:
                task_errors.append(f"{task_id}: invalid entity")
                continue
            tasks.append(task)
        try:
            computed_order = topological_order(tasks)
        except Exception as exc:
            computed_order = []
            task_errors.append(str(exc))
        if computed_order and computed_order != task_index.get("order"):
            task_errors.append(f"task order mismatch: {computed_order}")
        checks.append(_check("Task index and causal DAG", not task_errors and bool(tasks), {"tasks": len(tasks), "errors": task_errors}))

        state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
        active = state.get("active_run") or {}
        current = state.get("current_task_ref")
        project_status = state.get("project_status")
        active_errors: list[str] = []
        if current and current not in (task_index.get("current") or {}):
            active_errors.append("current task absent from index")
        if active:
            required_active_fields = ["run_ref", "task_ref", "prompt_bundle_path", "prompt_markdown_path", "snapshot_path"]
            if not compatibility_mode:
                required_active_fields.extend(["allowed_agent_output_path", "operation_journal_path", "control_plane_phase"])
            for field in required_active_fields:
                if not active.get(field):
                    active_errors.append(f"active_run.{field} missing")
            path_fields = ["prompt_bundle_path", "prompt_markdown_path", "snapshot_path"]
            if not compatibility_mode:
                path_fields.append("operation_journal_path")
            for field in path_fields:
                if active.get(field) and not (_native_io_path(root / active[field])).exists():
                    active_errors.append(f"missing {active[field]}")
            if not compatibility_mode:
                expected_result = f".harness/runtime/AGENT_RESULTS/{active.get('run_ref')}.json"
                if active.get("allowed_agent_output_path") != expected_result:
                    active_errors.append("active_run.allowed_agent_output_path is not the exact Run channel")
        if project_status == "TARGET_LEVEL_REACHED":
            if current is not None:
                active_errors.append("target-reached project must not have current_task_ref")
            if active:
                active_errors.append("target-reached project must not have active_run")
        elif compatibility_mode and project_status == "COMPLETED":
            if current is not None:
                active_errors.append("legacy completed project must not have current_task_ref")
            if active:
                active_errors.append("legacy completed project must not have active_run")
        elif project_status == "BLOCKED" or (state.get("open_blocker_refs") and not active):
            gate_blocked = state.get("next_route") == "RESOLVE_STAGE_GATE"
            if gate_blocked:
                if current is not None:
                    active_errors.append("Gate-blocked project must not retain current_task_ref")
                blocker_kinds: list[str] = []
                for raw_ref in state.get("open_blocker_refs") or []:
                    blocker_id = str(raw_ref).split("@", 1)[0]
                    revisions = sorted(native_glob(root / ".harness/blockers", f"{blocker_id}@*.yaml"))
                    if revisions:
                        blocker = load_data(revisions[-1]).get("blocker") or {}
                        blocker_kinds.append(str(blocker.get("kind") or ""))
                if "STAGE_GATE_BLOCKER" not in blocker_kinds:
                    active_errors.append("Gate-blocked project requires an OPEN STAGE_GATE_BLOCKER")
            elif not current:
                active_errors.append("execution-blocked project must retain current_task_ref")
            if active:
                active_errors.append("blocked project must not retain active_run")
            if not state.get("open_blocker_refs"):
                active_errors.append("blocked project requires an OPEN blocker")
        else:
            stage_boundary_routes = {
                "STAGE_GATE_REVIEW",
                "PLAN_ACTIVE_STAGE",
                "REVIEW_MATURITY_ASSESSMENT",
                "TARGET_ALREADY_REACHED",
                "EVALUATE_STAGE_GATE_READINESS",
            }
            ready_task_routes = {"COMPILE_NEXT_READY_TASK", "STAGE_ACCEPTANCE_PREPARATION"}
            if not active and not (
                (current is None and state.get("next_route") in stage_boundary_routes)
                or (current is not None and state.get("next_route") in ready_task_routes)
            ):
                active_errors.append("active project requires active_run, a READY current task route, or an explicit Stage boundary route")
        checks.append(_check("Current task and runtime state", not active_errors, {"project_status": project_status, "current_task": current, "run": active.get("run_ref"), "errors": active_errors}))

        if check_control_plane_state and active and not compatibility_mode:
            invariant = check_control_plane(root, active, allow_missing_agent_result=True)
            checks.append(_check("Protected control-plane phase boundary", invariant.get("status") == "PASS", invariant))

        bundles = list(native_glob(root / ".harness/prompts/BUNDLES_BY_RUN", "CPB-*.yaml"))
        bundle_refs = []
        bundle_errors: list[str] = []
        for path in bundles:
            bundle = load_data(path).get("compiled_prompt_bundle")
            if not isinstance(bundle, dict):
                bundle_errors.append(path.name)
                continue
            bundle_refs.append(bundle.get("id"))
            task_id = str(bundle.get("task_ref", "")).split("@")[0]
            if task_id not in (task_index.get("current") or {}):
                bundle_errors.append(f"{path.name}: unknown task")
            if current_mode:
                active_bundle_path = str((state.get("active_run") or {}).get("prompt_bundle_path") or "")
                rel = path.relative_to(root).as_posix()
                stage = bundle.get("implementation_stage")
                historical_legacy = migrated_legacy and rel != active_bundle_path and stage is None
                if not historical_legacy:
                    if stage not in {"PROTOTYPE", "ALPHA", "BETA", "MVP", "RELEASE"}:
                        bundle_errors.append(f"{path.name}: implementation_stage missing or invalid")
                    md_path = path.with_suffix(".md")
                    if not _native_io_path(md_path).exists():
                        bundle_errors.append(f"{path.name}: prompt markdown is missing")
                    else:
                        prompt = _native_io_path(md_path).read_text(encoding="utf-8")
                        # Prompt bundles are immutable Run history. After a level-up, an old
                        # bundle remains valid against the target level captured in that bundle,
                        # not the project's newly approved target.
                        expected_target = bundle.get("target_implementation_level")
                        if expected_target not in {"PROTOTYPE", "ALPHA", "BETA", "MVP", "RELEASE"}:
                            bundle_errors.append(f"{path.name}: target_implementation_level missing or invalid")
                        if f"CURRENT_IMPLEMENTATION_STAGE: {stage}" not in prompt:
                            bundle_errors.append(f"{path.name}: current-stage fence is missing")
                        if f"TARGET_IMPLEMENTATION_LEVEL: {expected_target}" not in prompt:
                            bundle_errors.append(f"{path.name}: target-level fence is missing")
        initial_result = root / ".harness/state/HANDOFF_RESULT.json"
        if _native_io_path(initial_result).exists():
            handoff = load_data(initial_result)
            if (handoff.get("future_compiled_prompt_count") == 0
                    and not state.get("completed_task_refs")
                    and (not current_mode or load_stage_state(root)["highest_accepted_level"] == "NONE")):
                counted_bundles = bundles
                if migrated_legacy:
                    counted_bundles = [
                        path for path in bundles
                        if (load_data(path).get("compiled_prompt_bundle") or {}).get("implementation_stage")
                    ]
                if len(counted_bundles) != 1:
                    bundle_errors.append(
                        f"initial/current stage must contain exactly one stage-aware compiled bundle, found {len(counted_bundles)}"
                    )
        checks.append(_check("JIT prompt bundles", not bundle_errors and bool(bundles), {"count": len(bundles), "refs": bundle_refs, "errors": bundle_errors}))

        skill_index = load_data(root / ".harness/skills/registry.yaml").get("skill_registry_index")
        skill_errors: list[str] = []
        if not isinstance(skill_index, dict) or skill_index.get("generated") is not True:
            skill_errors.append("registry is not marked generated")
        else:
            available = {item.get("ref"): item for item in skill_index.get("available") or []}
            for ref in lock.get("skill_refs") or []:
                item = available.get(ref)
                if not item or item.get("status") != "ACTIVE":
                    skill_errors.append(f"locked skill is not ACTIVE: {ref}")
        checks.append(_check("Project skill resolution index", not skill_errors, {"errors": skill_errors}))

        mode = project.get("lifecycle_mode")
        if mode in {"BROWNFIELD", "HYBRID"}:
            portfolio_path = root / ".harness/work-packages/ROUTE_PORTFOLIO/INDEX.yaml"
            routes: list[str] = []
            if _native_io_path(portfolio_path).exists():
                refs = load_data(portfolio_path)["brownfield_route_portfolio"].get("route_refs") or []
                for ref in refs:
                    path = root / f".harness/work-packages/ROUTE_PORTFOLIO/{str(ref).split('@')[0]}@1.yaml"
                    if _native_io_path(path).exists():
                        routes.append(load_data(path)["brownfield_route_item"]["route"])
            expected_routes = {"CONTINUE_DEVELOPMENT", "FIX_KNOWN_BUGS", "IMPROVE_PROJECT", "STABILIZE_BASELINE"}
            checks.append(_check("Brownfield route portfolio", set(routes) == expected_routes, {"routes": routes}))

    forbidden_hits: list[str] = []
    for rel, value in parsed_values:
        for path, _child in _walk(value):
            leaf = path.replace("]", "").split(".")[-1].split("[")[0]
            if leaf in FORBIDDEN_ACCOUNTING_KEYS:
                forbidden_hits.append(f"{rel}:{path}")
    checks.append(_check("Provider accounting remains excluded", not forbidden_hits, {"hits": forbidden_hits}))

    if check_manifest:
        ok, details = _manifest_check(root)
        checks.append(_check("Handoff manifest", ok, details))

    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    return {
        "status": status,
        "root": str(root),
        "compatibility_mode": "V0.4.1" if compatibility_mode else None,
        "legacy_status_mappings": legacy_status_mappings,
        "checks": checks,
        "errors": [item for item in checks if item["status"] == "FAIL"],
    }


def validate_handoff(path: Path) -> dict[str, Any]:
    ensure_native_path(path, tree=True, file_ok=True)
    path = path.expanduser().resolve()
    if _native_io_path(path).is_dir():
        return validate_handoff_directory(path, check_manifest=True, check_control_plane_state=True)
    if path.suffix.lower() != ".zip":
        raise ValidationFailure("Handoff must be a directory or ZIP archive", str(path))
    inspect_zip(path)
    with tempfile.TemporaryDirectory(prefix="project-harness-validate-") as temp_name:
        destination = Path(temp_name)
        safe_extract_zip(path, destination)
        root = detect_single_root(destination)
        result = validate_handoff_directory(root, check_manifest=True, check_control_plane_state=True)
        result["archive"] = str(path)
        result["archive_sha256"] = f"sha256:{sha256_file(path)}"
        return result


def validate_runtime_reachability(root: Path) -> dict[str, Any]:
    """PH-F04: reject persisted dead ends and inconsistent boundary data.

    A human review or an external safety prerequisite is *not* itself a
    reachability failure. A route with no public operation and no explicit
    prerequisite is. This validation does not reserve Runs or mutate history.
    """
    root = root.expanduser().resolve()
    errors: list[str] = []
    details: dict[str, Any] = {}
    if not (_native_io_path(root / STAGE_STATE_PATH)).is_file():
        try:
            lock = load_data(root / ".harness/config/PROJECT_LOCK.yaml")["project_lock"]
            if lock.get("harness_distribution") == LEGACY_ENGINE_VERSION and lock.get("schema_version") == LEGACY_SCHEMA_VERSION:
                return {"status": "PASS", "compatibility_mode": "LEGACY_V0.4.1_COMPATIBILITY",
                        "checked": False, "reason": "Pre-migration Stage runtime does not exist; legacy structural validation is authoritative.", "errors": []}
        except Exception:
            pass
        return {"status": "FAIL", "errors": ["Prepared v0.5.0 project is missing canonical Stage State"]}
    try:
        stage = load_stage_state(root)
        current_context = _current_stage_gate_context(root)
        state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
        next_doc = load_data(root / ".harness/state/NEXT_TASK.yaml")
        next_projection = next_doc.get("next_task") if isinstance(next_doc, dict) else None
        if not isinstance(next_projection, dict):
            raise ValidationFailure("NEXT_TASK must have a next_task object")
        task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
        maintenance = active_maintenance(root)
        status, route = state.get("project_status"), state.get("next_route")
        active_run = state.get("active_run")
        task_id = state.get("current_task_ref")
        execution_level = maintenance["implementation_stage"] if maintenance else stage["active_stage"]
        plan, gate = current_context["plan"], current_context["gate"]
        plan_status, gate_status = plan.get("status"), gate.get("status")
        next_operator = runtime_continuation(root, state, context=current_context)
        details.update({
            "project_status": status, "next_route": route, "active_stage": stage["active_stage"],
            "execution_stage": execution_level, "stage_plan_ref": current_context["plan_ref"],
            "gate_ref": current_context["gate_ref"], "stage_plan_status": plan_status,
            "gate_status": gate_status, "current_task_ref": task_id,
            "continuation": next_operator, "maintenance_route": maintenance.get("maintenance_route") if maintenance else None,
        })
        # CLI command existence is checked against the actual CLI parser rather
        # than assuming a route string names an implemented operation.
        from .cli import build_parser
        import argparse
        parser = build_parser()
        commands: set[str] = set()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                commands.update(action.choices)
        for field in ("command", "follow_up_command", "optional_command"):
            command = next_operator.get(field)
            if command is None:
                continue
            parts = command.split()
            if len(parts) < 2 or parts[0] != "project-harness" or parts[1] not in commands:
                errors.append(f"{field} points to an unimplemented CLI action: {command}")
        if next_operator["route"] == "INVALID_RUNTIME_ROUTE":
            errors.append(f"No supported continuation for {status}/{route}: {next_operator['reason']}")
        if not next_operator.get("command") and not next_operator.get("external_prerequisite") and status != "TARGET_LEVEL_REACHED":
            errors.append(f"{status}/{route} has neither a public CLI continuation nor a concrete external prerequisite")
        if state.get("active_stage") != stage["active_stage"]:
            errors.append("CURRENT_STATE active_stage differs from canonical Stage State")
        if state.get("target_implementation_level") != stage["target_level"]:
            errors.append("CURRENT_STATE target differs from canonical Stage State")
        accepted = stage["highest_accepted_level"]
        if accepted not in {"NONE", "UNKNOWN"}:
            expected = stage.get("last_acceptance_ref")
            if not isinstance(expected, str) or not expected.rpartition("@")[2].isdigit() or int(expected.rpartition("@")[2]) < 1 or not expected.rpartition("@")[0]:
                errors.append("Accepted Stage requires an exact last_acceptance_ref")
            else:
                path = root / f".harness/stages/ACCEPTANCE/{expected}.yaml"
                report_doc = load_data(path) if _native_io_path(path).is_file() and not _native_io_path(path).is_symlink() else None
                report = report_doc.get("stage_acceptance") if isinstance(report_doc, dict) else None
                if not isinstance(report, dict) or f"{report.get('id')}@{report.get('revision')}" != expected or report.get("level") != accepted or report.get("status") != "PASS":
                    errors.append("Last Stage Acceptance ref/level/report are not exact-bound")
            if status != "TARGET_LEVEL_REACHED" and not maintenance and next_level(accepted) != stage["active_stage"]:
                errors.append("Nonterminal active Stage is not the immediate successor of accepted maturity")
        if status == "TARGET_LEVEL_REACHED":
            if accepted != stage["target_level"]:
                errors.append("TARGET_LEVEL_REACHED without accepted canonical target")
            if route != "TARGET_ALREADY_REACHED":
                errors.append("Target-reached state has a nonterminal next_route")
            if task_id is not None or active_run is not None or maintenance is not None:
                errors.append("Target-reached state cannot have an open Task, Run, or maintenance")
            if plan_status != "ACCEPTED" or gate_status != "ACCEPTED":
                errors.append("Target-reached active Stage Plan/Gate must be ACCEPTED")
        if status == "ACTIVE" and route == "PLAN_ACTIVE_STAGE":
            if task_id is not None or active_run is not None or maintenance is not None:
                errors.append("Stage planning must be idle, without active Task/Run/maintenance")
            if plan_status != "ACTIVE" or gate_status != "ACTIVE":
                errors.append("Stage planning requires the exact current ACTIVE Plan and Gate")
            if not plan.get("review_required") or plan.get("detailed_work_package_refs"):
                errors.append("Stage planning requires an undetailed, review-required current Stage Plan")
            if gate.get("required_work_package_refs") or gate.get("critical_blocker_refs"):
                errors.append("Stage planning Gate contains unfinished work or critical blockers")
            if accepted in {"NONE", "UNKNOWN"} or next_level(accepted) != stage["active_stage"]:
                errors.append("Stage planning requires an accepted immediate predecessor")
        if status == "ACTIVE" and route == "STAGE_GATE_REVIEW":
            if task_id is not None or active_run is not None or maintenance is not None:
                errors.append("Stage Gate review must not have a current Task/Run/maintenance")
            if plan_status != "VERIFYING" or gate_status != "VERIFYING":
                errors.append("Gate-review route requires matching VERIFYING current Plan/Gate")
            if state.get("open_blocker_refs") or state.get("blocked_task_refs"):
                errors.append("VERIFYING Gate cannot retain OPEN critical/Task blockers")
        if status == "ACTIVE" and route == "REVIEW_MATURITY_ASSESSMENT":
            if task_id is not None or active_run is not None or maintenance is not None:
                errors.append("Maturity review must not reserve any current Task/Run/maintenance")
        if status == "ACTIVE" and route == "EVALUATE_STAGE_GATE_READINESS":
            if task_id is not None or active_run is not None or maintenance is not None:
                errors.append("Gate-readiness recovery must have completed the last Task")
            if plan_status != "ACTIVE" or gate_status != "ACTIVE":
                errors.append("Gate-readiness recovery requires ACTIVE Plan and Gate")
        open_refs = state.get("open_blocker_refs") or []
        if status == "BLOCKED":
            if active_run is not None or not open_refs:
                errors.append("BLOCKED requires an open blocker and no active Run")
            if route == "RESOLVE_STAGE_GATE":
                if task_id is not None or plan_status != "BLOCKED" or gate_status != "BLOCKED":
                    errors.append("Stage Gate blocker requires empty Task and BLOCKED Plan/Gate")
            elif route in {"RESOLVE_BLOCKER_OR_CHANGE_SCOPE", "RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN"}:
                if task_id is None:
                    errors.append("Ordinary/safety blocker must retain the affected Task")
            # Exact, numeric latest blocker revision; a stale/forged ref cannot
            # close a failed Gate or mask a different OPEN Task blocker.
            for ref in open_refs:
                blocker_id = str(ref).split("@", 1)[0]
                matches = []
                for path in native_glob(root / ".harness/blockers", f"{blocker_id}@*.yaml"):
                    suffix = path.stem.removeprefix(blocker_id + "@")
                    if suffix.isdigit() and int(suffix) > 0:
                        matches.append((int(suffix), path))
                if not matches:
                    errors.append(f"Missing OPEN blocker {ref}")
                    continue
                number, path = max(matches, key=lambda item: item[0])
                blocker = load_data(path).get("blocker") or {}
                if blocker.get("id") != blocker_id or blocker.get("revision") != number or blocker.get("status") != "OPEN":
                    errors.append(f"Blocker {ref} is not the latest OPEN revision")
                if route == "RESOLVE_STAGE_GATE":
                    if blocker.get("kind") != "STAGE_GATE_BLOCKER" or blocker.get("level") != stage["active_stage"]:
                        errors.append(f"Gate blocker {ref} does not match current Stage/kind")
                elif blocker.get("kind") == "STAGE_GATE_BLOCKER":
                    errors.append(f"Stage Gate blocker {ref} is incorrectly routed as an ordinary Task blocker")
        elif open_refs or state.get("blocked_task_refs"):
            errors.append("Non-BLOCKED state retains OPEN blocker references")
        if task_id is not None:
            rel = (task_index.get("current") or {}).get(str(task_id))
            task = load_data(root / rel).get("task") if isinstance(rel, str) and (_native_io_path(root / rel)).is_file() else None
            if not isinstance(task, dict) or task.get("id") != task_id:
                errors.append("Current Task is missing or mismatched in Task index")
            else:
                if task_id not in (state.get("task_order") or []):
                    errors.append("Current Task is absent from scheduler task_order")
                if task.get("implementation_stage") != execution_level:
                    errors.append("Current Task is outside the executable Stage fence")
                if maintenance:
                    if task.get("maintenance_route") != "MAINTAIN_CURRENT_STAGE" or task.get("maintenance_plan_ref") != maintenance.get("plan_ref"):
                        errors.append("Current maintenance Task lacks exact active plan binding")
                elif task.get("maintenance_route") is not None:
                    errors.append("Current ordinary Task carries maintenance route")
                task_status = task.get("status")
                if status == "BLOCKED" and task_status != "BLOCKED":
                    errors.append("Blocked project current Task is not BLOCKED")
                elif status == "ACTIVE" and task_status != "READY":
                    errors.append("Executable Task must be READY, not future/terminal/unplanned")
                if status == "ACTIVE" and active_run is None:
                    allowed = {"COMPILE_FIRST_READY_TASK", "COMPILE_NEXT_READY_TASK", "COMPILE_RESUMED_TASK", "STAGE_ACCEPTANCE_PREPARATION", "MAINTAIN_CURRENT_STAGE"}
                    if route not in allowed:
                        errors.append("Unreserved READY Task has no supported next/JIT route")
                    completed = {str(ref).split("@", 1)[0] for ref in state.get("completed_task_refs") or []}
                    if not set(task.get("depends_on_tasks") or []).issubset(completed):
                        errors.append("Current Task has unresolved DAG dependencies")
                if status == "ACTIVE" and not maintenance and plan_status != "ACTIVE":
                    errors.append("Ordinary Task execution requires ACTIVE current Stage Plan")
            if isinstance(active_run, dict):
                if str(active_run.get("task_ref") or "").split("@", 1)[0] != task_id:
                    errors.append("Active Run task_ref does not match current Task")
                if active_run.get("implementation_stage") != execution_level:
                    errors.append("Active Run violates executable Stage fence")
                if route == "COMPLETE_TASK":
                    if active_run.get("control_plane_phase") != "VERIFIED" or not active_run.get("verification_report_path"):
                        errors.append("Completion route lacks a verified Run/report")
                    else:
                        report_path = root / active_run["verification_report_path"]
                        report_doc = load_data(report_path) if _native_io_path(report_path).is_file() else None
                        # Runtime verification is stored in the legacy
                        # `validation_report` envelope (not `verification_report`).
                        verification = report_doc.get("validation_report") if isinstance(report_doc, dict) else None
                        if not isinstance(verification, dict) or verification.get("status") != "PASS":
                            errors.append("Completion route has no actual PASS verification report")
                        else:
                            from .runtime import automatic_run_phase
                            automatic = automatic_run_phase(root, active_run)
                            if automatic is not None:
                                apply_ref = active_run.get("automatic_apply_evidence_ref")
                                apply_path = (root / ".harness/evidence" / (str(apply_ref) + ".yaml"))
                                if (automatic.get("phase") != "AUTO_VERIFIED" or
                                        verification.get("verification_backend") != "SANDBOXED" or
                                        verification.get("run_ref") != active_run.get("run_ref") or
                                        not isinstance(apply_ref, str) or not apply_ref.startswith("EVD-APPLY-") or
                                        not _native_io_path(apply_path).is_file() or _native_io_path(apply_path).is_symlink() or
                                        (load_data(apply_path).get("apply_evidence") or {}).get("run_ref") != str(active_run["run_ref"]) + "@1"):
                                    errors.append("Automatic completion lacks exact SANDBOXED proof, Run binding or committed Apply Evidence")
        elif active_run is not None:
            errors.append("Active Run exists without a current Task")
        if task_id is None and status == "ACTIVE" and route not in {
            "PLAN_ACTIVE_STAGE", "STAGE_GATE_REVIEW", "REVIEW_MATURITY_ASSESSMENT", "EVALUATE_STAGE_GATE_READINESS"
        }:
            errors.append("Empty current Task is not at a supported Stage boundary")
        # Check NEXT_TASK boundary projections, but do not require next_route
        # equality while an active Run is independently verified: the immutable
        # initial JIT NEXT_TASK projection intentionally still names its bundle.
        if task_id is None and status in {"ACTIVE", "TARGET_LEVEL_REACHED"}:
            if next_projection.get("task_ref") is not None or next_projection.get("next_route") != route:
                errors.append("NEXT_TASK boundary projection differs from persisted current route")
    except Exception as exc:
        errors.append(f"Runtime reachability inspection failed: {exc}")
    details["errors"] = errors
    return {"status": "PASS" if not errors else "FAIL", **details}


def validate_project_directory(root: Path) -> dict[str, Any]:
    """Recover and validate mutable post-handoff state without the baseline manifest."""
    ensure_native_path(root, tree=True)
    root = root.expanduser().resolve()
    recovery: dict[str, Any] | None = None
    recovery_error: dict[str, Any] | None = None
    try:
        recovery = recover_stage_transactions(root)
    except Exception as exc:
        recovery_error = {
            "error": str(exc),
            "details": getattr(exc, "details", None),
        }

    result = validate_handoff_directory(
        root,
        check_manifest=False,
        check_control_plane_state=True,
    )
    if recovery_error is None:
        transaction_validation = validate_stage_transaction_journals(root)
        transaction_details = {
            "recovery": recovery,
            "validation": transaction_validation,
        }
        transaction_ok = transaction_validation.get("status") == "PASS"
    else:
        transaction_details = {
            "recovery": {"status": "FAIL", **recovery_error},
            "validation": None,
        }
        transaction_ok = False
    result.setdefault("checks", []).append(
        _check("Stage transaction journals and crash recovery", transaction_ok, transaction_details)
    )
    runtime_validation = validate_runtime_reachability(root)
    result["checks"].append(
        _check("Persisted runtime continuation and Stage boundary reachability", runtime_validation["status"] == "PASS", runtime_validation)
    )
    maintenance_validation = validate_maintenance_artifacts(root)
    result["checks"].append(
        _check(
            "Governed same-level maintenance artifacts",
            maintenance_validation.get("status") == "PASS",
            maintenance_validation,
        )
    )
    result["status"] = "PASS" if all(item.get("status") == "PASS" for item in result["checks"]) else "FAIL"
    result["errors"] = [item for item in result["checks"] if item.get("status") == "FAIL"]
    result["stage_transaction_recovery"] = transaction_details
    return result

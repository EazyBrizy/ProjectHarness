from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import ValidationFailure
from .hashing import sha256_file
from .resources import distribution_root
from .serialization import load_data

REGISTRY_NAMES = (
    "id_prefixes",
    "project_profiles",
    "statuses",
    "request_routing",
    "capabilities",
    "contracts",
    "implementation_levels",
)
EXPECTED_REGISTRY_VERSIONS = {
    "id_prefixes": 3,
    "project_profiles": 1,
    "statuses": 6,
    "request_routing": 2,
    "capabilities": 1,
    "contracts": 6,
    "implementation_levels": 1,
}


def validate_implementation_levels(value: dict[str, Any]) -> dict[str, Any]:
    """Validate the canonical sequential implementation-level graph."""
    registry = value.get("registry") if isinstance(value, dict) else None
    if not isinstance(registry, dict):
        raise ValidationFailure("Implementation level registry envelope is invalid")
    if registry.get("id") != "REG-IMPLEMENTATION-LEVELS":
        raise ValidationFailure("Unexpected implementation level registry id", registry.get("id"))
    if registry.get("progression_policy") != "SEQUENTIAL":
        raise ValidationFailure("Implementation level progression must be SEQUENTIAL")

    levels = registry.get("levels")
    profiles = registry.get("criteria_profiles")
    criteria = registry.get("criteria")
    dimensions = set(registry.get("dimensions") or [])
    if not isinstance(levels, list) or not levels:
        raise ValidationFailure("Implementation level registry has no levels")
    if not isinstance(profiles, dict) or not isinstance(criteria, dict):
        raise ValidationFailure("Implementation level criteria profiles/definitions are invalid")

    errors: list[str] = []
    ids: list[str] = []
    ordinals: list[int] = []
    by_id: dict[str, dict[str, Any]] = {}
    for item in levels:
        if not isinstance(item, dict):
            errors.append("level entry must be an object")
            continue
        level_id = str(item.get("id") or "")
        ordinal = item.get("ordinal")
        if not level_id:
            errors.append("level id is required")
            continue
        ids.append(level_id)
        by_id[level_id] = item
        if not isinstance(ordinal, int):
            errors.append(f"{level_id}: ordinal must be integer")
        else:
            ordinals.append(ordinal)
        profile_ref = item.get("criteria_profile")
        if profile_ref not in profiles:
            errors.append(f"{level_id}: missing criteria profile {profile_ref!r}")

    if len(ids) != len(set(ids)):
        errors.append("level ids must be unique")
    if len(ordinals) != len(set(ordinals)):
        errors.append("level ordinals must be unique")
    starts = [item for item in levels if not item.get("previous")]
    ends = [item for item in levels if not item.get("next")]
    if len(starts) != 1:
        errors.append(f"expected one initial level, found {len(starts)}")
    if len(ends) != 1:
        errors.append(f"expected one final level, found {len(ends)}")

    for level_id, item in by_id.items():
        previous = item.get("previous")
        nxt = item.get("next")
        if previous:
            if previous not in by_id:
                errors.append(f"{level_id}: previous={previous} is unknown")
            elif by_id[previous].get("next") != level_id:
                errors.append(f"{level_id}: previous/next link is inconsistent")
        if nxt:
            if nxt not in by_id:
                errors.append(f"{level_id}: next={nxt} is unknown")
            elif by_id[nxt].get("previous") != level_id:
                errors.append(f"{level_id}: next/previous link is inconsistent")

    visited: list[str] = []
    if len(starts) == 1:
        current = starts[0].get("id")
        while current:
            if current in visited:
                errors.append("implementation level graph contains a cycle")
                break
            visited.append(str(current))
            current = by_id.get(str(current), {}).get("next")
        if set(visited) != set(ids):
            errors.append("implementation level graph is disconnected")
        if visited and [by_id[item].get("ordinal") for item in visited] != sorted(ordinals):
            errors.append("implementation level ordinals do not follow progression order")

    for profile_id, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"criteria profile {profile_id} must be an object")
            continue
        refs = profile.get("criteria_refs")
        mandatory_dimensions = profile.get("mandatory_dimensions")
        if not isinstance(refs, list) or not refs:
            errors.append(f"criteria profile {profile_id} has no criteria_refs")
            continue
        if not isinstance(mandatory_dimensions, list):
            errors.append(f"criteria profile {profile_id} mandatory_dimensions must be an array")
            mandatory_dimensions = []
        for dimension in mandatory_dimensions:
            if dimension not in dimensions:
                errors.append(f"criteria profile {profile_id} uses unknown dimension {dimension}")
        for ref in refs:
            criterion = criteria.get(ref)
            if not isinstance(criterion, dict):
                errors.append(f"criteria profile {profile_id} has dangling criterion {ref}")
                continue
            if criterion.get("level") != profile_id:
                errors.append(f"criterion {ref} level does not match profile {profile_id}")
            if criterion.get("dimension") not in dimensions:
                errors.append(f"criterion {ref} has unknown dimension {criterion.get('dimension')}")
            evidence = criterion.get("required_evidence_kinds")
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"criterion {ref} has no required evidence kinds")

    canonical = ["PROTOTYPE", "ALPHA", "BETA", "MVP", "RELEASE"]
    if visited and visited != canonical:
        errors.append(f"canonical level order must be {canonical}, got {visited}")
    if errors:
        raise ValidationFailure("Implementation level registry validation failed", errors)
    return {
        "order": visited,
        "initial": visited[0],
        "final": visited[-1],
        "ordinals": {level_id: by_id[level_id]["ordinal"] for level_id in visited},
    }


def load_registries(root: Path | None = None) -> dict[str, dict[str, Any]]:
    base = (root or distribution_root()) / "registries"
    values: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for name in REGISTRY_NAMES:
        path = base / f"{name}.yaml"
        if not path.exists():
            errors.append(f"missing {path}")
            continue
        value = load_data(path)
        if not isinstance(value, dict) or not isinstance(value.get("registry"), dict):
            errors.append(f"invalid registry envelope: {path}")
            continue
        actual = value["registry"].get("version")
        expected = EXPECTED_REGISTRY_VERSIONS[name]
        if actual != expected:
            errors.append(f"{name}: expected version {expected}, got {actual}")
        values[name] = value
    embedded = (root or distribution_root()) / "src/project_harness/resources/registries"
    if embedded.is_dir():
        for name in REGISTRY_NAMES:
            source_path = base / f"{name}.yaml"
            embedded_path = embedded / f"{name}.yaml"
            if not embedded_path.exists():
                errors.append(f"missing embedded registry copy: {embedded_path}")
            elif source_path.exists() and sha256_file(source_path) != sha256_file(embedded_path):
                errors.append(f"{name}: source/embedded registry digest mismatch")
    if not errors and "implementation_levels" in values:
        try:
            validate_implementation_levels(values["implementation_levels"])
        except ValidationFailure as exc:
            details = exc.details if isinstance(exc.details, list) else [exc.details or exc.message]
            errors.extend(str(item) for item in details)
    if not errors:
        ids = {e.get("prefix"): e for e in values["id_prefixes"]["registry"].get("entries", [])}
        if ids.get("SBX") != {"prefix": "SBX", "entity": "OS-level Sandbox Profile", "schema_key": "sandbox_profile", "status": "ACTIVE"}:
            errors.append("SBX ID prefix must be a dedicated sandbox_profile")
        groups = values["statuses"]["registry"].get("groups", {})
        if groups.get("sandbox_profile") != ["DRAFT", "VALIDATED", "ACTIVE", "SUSPENDED", "DEPRECATED", "RETIRED"]:
            errors.append("sandbox_profile lifecycle must have normative statuses")
        entities = values["contracts"]["registry"].get("entities", {})
        expected = {
            "sandbox_profile": ("SBX", "sandbox_profile", ".harness/config/SANDBOXES/{id}@{revision}.yaml", "VERSIONED"),
            "execution_result": ("ART", "IMMUTABLE_RECORD", ".harness/runtime/EXECUTION_RESULTS/{id}.yaml", "IMMUTABLE"),
            "apply_evidence": ("EVD", "IMMUTABLE_RECORD", ".harness/evidence/{id}.yaml", "IMMUTABLE"),
        }
        for kind, (prefix, lifecycle, path, policy) in expected.items():
            entity = entities.get(kind, {})
            if (entity.get("id_prefix"), entity.get("lifecycle"), entity.get("storage_path"), entity.get("revision_policy")) != (prefix, lifecycle, path, policy):
                errors.append(f"{kind}: normative persistence contract mismatch")
        if entities.get("agent_adapter_profile", {}).get("id_prefix") != "ADP":
            errors.append("Existing ADP executor contract must be preserved")
    if errors:
        raise ValidationFailure("Registry validation failed", errors)
    return values


def registry_lock(root: Path | None = None) -> tuple[dict[str, int], dict[str, str]]:
    base = (root or distribution_root()) / "registries"
    load_registries(root)
    versions = dict(EXPECTED_REGISTRY_VERSIONS)
    digests = {
        name: f"sha256:{sha256_file(base / f'{name}.yaml')}"
        for name in REGISTRY_NAMES
    }
    return versions, digests


def allowed_capabilities(registries: dict[str, dict[str, Any]]) -> set[str]:
    entries = registries["capabilities"]["registry"].get("entries") or []
    return {str(entry["key"]) for entry in entries}


def known_profiles(registries: dict[str, dict[str, Any]]) -> set[str]:
    entries = registries["project_profiles"]["registry"].get("entries") or []
    refs = set()
    for entry in entries:
        ref = entry.get("id") or entry.get("ref")
        if not ref and entry.get("key"):
            ref = "PRF-" + str(entry["key"]).replace("_", "-")
        version = entry.get("version", 1)
        if ref:
            refs.add(f"{ref}@{version}")
    return refs


def implementation_level_model(registries: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    values = registries or load_registries()
    registry = values["implementation_levels"]["registry"]
    model = validate_implementation_levels(values["implementation_levels"])
    model.update({
        "levels": {item["id"]: item for item in registry["levels"]},
        "profiles": registry["criteria_profiles"],
        "criteria": registry["criteria"],
        "dimensions": registry["dimensions"],
    })
    return model


def canonical_implementation_levels() -> tuple[str, ...]:
    return tuple(implementation_level_model()["order"])

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .platform_fs import _native_io_path, native_resolve, native_iterdir
from .errors import ValidationFailure
from .hashing import sha256_file
from .registry import validate_implementation_levels
from .resources import distribution_root
from .serialization import canonical_json_bytes, load_data, write_data
from .util import nonempty, resolve_inside

EVIDENCE_SCHEMA_VERSION = 1
EVIDENCE_REF_PATTERN = re.compile(
    r"^EVD-[A-Z0-9](?:[A-Z0-9._:-]*[A-Z0-9])?$"
)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
TREE_REVISION_PATTERN = re.compile(r"^tree:sha256:[0-9a-f]{64}$")
EVIDENCE_STATUSES = {
    "PASS",
    "FAIL",
    "BLOCKED",
    "PARTIAL",
    "UNKNOWN",
    "NOT_APPLICABLE",
}
POSITIVE_GATE_EVIDENCE_STATUSES = {"PASS"}

_REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "id",
    "ref",
    "kind",
    "status",
    "provenance",
    "base_revision",
    "criterion_refs",
    "outcome_refs",
    "profile_control_refs",
    "source_bindings",
    "created_at",
}
_OPTIONAL_EVIDENCE_FIELDS = {
    "task_ref",
    "run_ref",
    "report_refs",
    "rationale",
    "validator",
    "details",
}
_REQUIRED_PROVENANCE_FIELDS = {"source_type", "source_ref", "producer"}
_OPTIONAL_PROVENANCE_FIELDS = {"actor", "tool_version", "details"}
_REQUIRED_SOURCE_BINDING_FIELDS = {"ref", "sha256"}
_OPTIONAL_SOURCE_BINDING_FIELDS = {"path", "media_type"}


def parse_evidence_ref(value: Any) -> str:
    if not isinstance(value, str) or EVIDENCE_REF_PATTERN.fullmatch(value) is None:
        raise ValidationFailure(
            "Evidence ref must be one exact canonical EVD-* identifier",
            value,
        )
    if value.strip() != value:
        raise ValidationFailure("Evidence ref is not canonical", value)
    return value


def _project_registry_path(root: Path, name: str) -> Path:
    project_copy = root / f".harness/registries/{name}.yaml"
    if _native_io_path(project_copy).is_file():
        return project_copy
    return distribution_root() / f"registries/{name}.yaml"


def _implementation_registry(root: Path) -> dict[str, Any]:
    path = _project_registry_path(root, "implementation_levels")
    value = load_data(path)
    validate_implementation_levels(value)
    registry = value.get("registry") if isinstance(value, dict) else None
    if not isinstance(registry, dict):
        raise ValidationFailure("Implementation Level Registry envelope is invalid", str(path))
    return registry


def allowed_evidence_kinds(root: Path) -> set[str]:
    registry = _implementation_registry(root)
    kinds = registry.get("evidence_kinds")
    if not isinstance(kinds, list) or not kinds or any(not nonempty(item) for item in kinds):
        raise ValidationFailure("Implementation Level Registry evidence_kinds is invalid")
    values = {str(item) for item in kinds}
    if len(values) != len(kinds):
        raise ValidationFailure("Implementation Level Registry evidence_kinds contains duplicates")
    return values


def gate_subject_requirements(
    root: Path,
    level: str,
    overrides: list[dict[str, Any]] | None = None,
) -> dict[str, set[str]]:
    registry = _implementation_registry(root)
    profiles = registry.get("criteria_profiles") or {}
    criteria = registry.get("criteria") or {}
    profile = profiles.get(level)
    if not isinstance(profile, dict):
        raise ValidationFailure("Gate level has no criteria profile", level)
    requirements: dict[str, set[str]] = {}
    for raw_ref in profile.get("criteria_refs") or []:
        ref = str(raw_ref)
        criterion = criteria.get(ref)
        if not isinstance(criterion, dict):
            raise ValidationFailure("Gate criterion is absent from the registry", ref)
        kinds = {str(item) for item in (criterion.get("required_evidence_kinds") or [])}
        if not kinds:
            raise ValidationFailure("Gate criterion has no required_evidence_kinds", ref)
        requirements[ref] = kinds
    for raw in overrides or []:
        if not isinstance(raw, dict) or not nonempty(raw.get("key")):
            raise ValidationFailure("Hard-constraint override is invalid", raw)
        ref = str(raw["key"])
        kinds = {str(item) for item in (raw.get("required_evidence_kinds") or [])}
        if not kinds:
            raise ValidationFailure("Hard-constraint override has no required_evidence_kinds", ref)
        if ref in requirements:
            raise ValidationFailure("Duplicate Gate subject ref", ref)
        requirements[ref] = kinds
    allowed = allowed_evidence_kinds(root)
    invalid = {
        ref: sorted(kinds - allowed)
        for ref, kinds in requirements.items()
        if kinds - allowed
    }
    if invalid:
        raise ValidationFailure("Gate requirements use unregistered evidence kinds", invalid)
    return requirements


def _canonical_storage_contract(root: Path) -> dict[str, Any]:
    path = _project_registry_path(root, "contracts")
    value = load_data(path)
    registry = value.get("registry") if isinstance(value, dict) else None
    entity = (registry.get("entities") or {}).get("verification_evidence") if isinstance(registry, dict) else None
    expected = {
        "id_prefix": "EVD",
        "persistence": "PERSISTENT",
        "lifecycle": "IMMUTABLE_RECORD",
        "storage_path": ".harness/evidence/{id}.yaml",
        "revision_policy": "IMMUTABLE",
    }
    if not isinstance(entity, dict) or any(entity.get(key) != expected_value for key, expected_value in expected.items()):
        raise ValidationFailure(
            "Verification evidence canonical storage contract is invalid",
            {"path": str(path), "expected": expected, "actual": entity},
        )
    return entity


def canonical_evidence_relative_path(root: Path, evidence_ref: Any) -> str:
    ref = parse_evidence_ref(evidence_ref)
    contract = _canonical_storage_contract(root)
    relative = str(contract["storage_path"]).format(id=ref)
    expected = f".harness/evidence/{ref}.yaml"
    if relative != expected:
        raise ValidationFailure("Evidence storage path did not resolve exactly", {"ref": ref, "path": relative})
    return relative


def _validate_created_at(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationFailure("Normalized evidence created_at must be non-empty")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationFailure("Normalized evidence created_at must be ISO-8601", value) from exc
    if parsed.tzinfo is None:
        raise ValidationFailure("Normalized evidence created_at must include a timezone", value)
    return value


def _validate_string_array(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValidationFailure(f"Normalized evidence {field} must be an array of non-empty strings")
    normalized = [str(item) for item in value]
    if len(normalized) != len(set(normalized)):
        raise ValidationFailure(f"Normalized evidence {field} contains duplicates", normalized)
    return normalized


def _validate_provenance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationFailure("Normalized evidence provenance must be an object")
    missing = sorted(_REQUIRED_PROVENANCE_FIELDS - set(value))
    unknown = sorted(set(value) - _REQUIRED_PROVENANCE_FIELDS - _OPTIONAL_PROVENANCE_FIELDS)
    if missing or unknown:
        raise ValidationFailure("Normalized evidence provenance contract mismatch", {"missing": missing, "unknown": unknown})
    empty = [field for field in _REQUIRED_PROVENANCE_FIELDS if not nonempty(value.get(field))]
    if empty:
        raise ValidationFailure("Normalized evidence provenance is incomplete", empty)
    for field in ("actor", "tool_version"):
        if field in value and value[field] is not None and not nonempty(value[field]):
            raise ValidationFailure("Normalized evidence provenance optional string is empty", field)
    if "details" in value and value["details"] is not None and not isinstance(value["details"], dict):
        raise ValidationFailure("Normalized evidence provenance.details must be an object")
    return deepcopy(value)


def _validate_source_bindings(root: Path, value: Any, *, verify_sources: bool) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ValidationFailure("Normalized evidence source_bindings must be a non-empty array")
    normalized: list[dict[str, Any]] = []
    refs: list[str] = []
    for index, raw in enumerate(value, 1):
        if not isinstance(raw, dict):
            raise ValidationFailure("Evidence source binding must be an object", index)
        missing = sorted(_REQUIRED_SOURCE_BINDING_FIELDS - set(raw))
        unknown = sorted(set(raw) - _REQUIRED_SOURCE_BINDING_FIELDS - _OPTIONAL_SOURCE_BINDING_FIELDS)
        if missing or unknown:
            raise ValidationFailure(
                "Evidence source binding contract mismatch",
                {"index": index, "missing": missing, "unknown": unknown},
            )
        if not nonempty(raw.get("ref")):
            raise ValidationFailure("Evidence source binding ref is empty", index)
        digest = raw.get("sha256")
        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            raise ValidationFailure("Evidence source binding sha256 is not canonical", {"index": index, "sha256": digest})
        binding = deepcopy(raw)
        refs.append(str(binding["ref"]))
        if "media_type" in binding and binding["media_type"] is not None and not nonempty(binding["media_type"]):
            raise ValidationFailure("Evidence source binding media_type is empty", index)
        if "path" in binding:
            path_value = binding["path"]
            if not isinstance(path_value, str) or not path_value.strip():
                raise ValidationFailure("Evidence source binding path is empty", index)
            pure = PurePosixPath(path_value)
            if pure.is_absolute() or ".." in pure.parts or path_value != pure.as_posix():
                raise ValidationFailure("Evidence source binding path must be canonical project-local POSIX path", path_value)
            if verify_sources:
                full = resolve_inside(root, path_value)
                if _native_io_path(full).is_symlink() or not _native_io_path(full).is_file():
                    raise ValidationFailure("Evidence bound source artifact is missing or not a regular file", path_value)
                actual = f"sha256:{sha256_file(full)}"
                if actual != digest:
                    raise ValidationFailure(
                        "Evidence bound source artifact digest mismatch",
                        {"path": path_value, "expected": digest, "actual": actual},
                    )
        normalized.append(binding)
    if len(refs) != len(set(refs)):
        raise ValidationFailure("Normalized evidence source_bindings contain duplicate refs", refs)
    return normalized


def validate_normalized_evidence_document(
    root: Path,
    value: Any,
    *,
    expected_ref: str | None = None,
    verify_sources: bool = True,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"verification_evidence"}:
        raise ValidationFailure("Normalized evidence envelope must be exactly verification_evidence")
    body = value.get("verification_evidence")
    if not isinstance(body, dict):
        raise ValidationFailure("Normalized evidence body is invalid")
    missing = sorted(_REQUIRED_EVIDENCE_FIELDS - set(body))
    unknown = sorted(set(body) - _REQUIRED_EVIDENCE_FIELDS - _OPTIONAL_EVIDENCE_FIELDS)
    if missing or unknown:
        raise ValidationFailure("Normalized evidence contract mismatch", {"missing": missing, "unknown": unknown})
    if body.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise ValidationFailure("Unsupported normalized evidence schema_version", body.get("schema_version"))
    evidence_id = parse_evidence_ref(body.get("id"))
    evidence_ref = parse_evidence_ref(body.get("ref"))
    if evidence_id != evidence_ref:
        raise ValidationFailure("Normalized evidence id and ref must be identical", {"id": evidence_id, "ref": evidence_ref})
    if expected_ref is not None and evidence_ref != parse_evidence_ref(expected_ref):
        raise ValidationFailure(
            "Evidence internal id/ref does not match requested ref",
            {"requested": expected_ref, "id": evidence_id, "ref": evidence_ref},
        )
    kind = body.get("kind")
    if kind not in allowed_evidence_kinds(root):
        raise ValidationFailure("Normalized evidence kind is not registered", kind)
    status = body.get("status")
    if status not in EVIDENCE_STATUSES:
        raise ValidationFailure("Normalized evidence status is invalid", status)
    provenance = _validate_provenance(body.get("provenance"))
    base_revision = body.get("base_revision")
    if not isinstance(base_revision, str) or TREE_REVISION_PATTERN.fullmatch(base_revision) is None:
        raise ValidationFailure("Normalized evidence base_revision must be an exact product tree digest", base_revision)
    criterion_refs = _validate_string_array(body.get("criterion_refs"), "criterion_refs")
    outcome_refs = _validate_string_array(body.get("outcome_refs"), "outcome_refs")
    profile_control_refs = _validate_string_array(body.get("profile_control_refs"), "profile_control_refs")
    if not (criterion_refs or outcome_refs or profile_control_refs):
        raise ValidationFailure("Normalized evidence must map to at least one criterion/outcome/profile control")
    source_bindings = _validate_source_bindings(root, body.get("source_bindings"), verify_sources=verify_sources)
    if str(provenance["source_ref"]) not in {str(item["ref"]) for item in source_bindings}:
        raise ValidationFailure(
            "Evidence provenance.source_ref is not bound by source_bindings",
            provenance.get("source_ref"),
        )
    _validate_created_at(body.get("created_at"))
    for field in ("task_ref", "run_ref", "rationale", "validator"):
        if field in body and body[field] is not None and not nonempty(body[field]):
            raise ValidationFailure("Normalized evidence optional string is empty", field)
    if "report_refs" in body:
        _validate_string_array(body["report_refs"], "report_refs")
    if "details" in body and body["details"] is not None and not isinstance(body["details"], dict):
        raise ValidationFailure("Normalized evidence details must be an object")
    return deepcopy(body)


def classify_evidence_document(root: Path, value: Any, *, verify_sources: bool = False) -> dict[str, Any]:
    body = value.get("verification_evidence") if isinstance(value, dict) else None
    if not isinstance(body, dict):
        return {"classification": "INVALID", "error": "verification_evidence envelope/body is absent"}
    if "schema_version" not in body:
        return {"classification": "LEGACY", "body": deepcopy(body)}
    if body.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        return {
            "classification": "INVALID_NORMALIZED",
            "body": deepcopy(body),
            "error": f"Unsupported normalized evidence schema_version: {body.get('schema_version')!r}",
        }
    try:
        normalized = validate_normalized_evidence_document(root, value, verify_sources=verify_sources)
    except Exception as exc:
        return {
            "classification": "INVALID_NORMALIZED",
            "body": deepcopy(body),
            "error": str(exc),
            "details": getattr(exc, "details", None),
        }
    return {"classification": "NORMALIZED", "body": normalized}


def _duplicate_artifact_paths(root: Path, ref: str, expected_path: Path) -> list[str]:
    duplicates: list[str] = []
    evidence_dir = root / ".harness/evidence"
    if not _native_io_path(evidence_dir).is_dir():
        return duplicates
    for candidate in sorted(native_iterdir(evidence_dir)):
        if candidate == expected_path or _native_io_path(candidate).is_symlink() or not _native_io_path(candidate).is_file():
            continue
        try:
            value = load_data(candidate)
        except Exception:
            continue
        body = value.get("verification_evidence") if isinstance(value, dict) else None
        if isinstance(body, dict) and (body.get("id") == ref or body.get("ref") == ref):
            duplicates.append(candidate.relative_to(root).as_posix())
    return duplicates


def resolve_evidence_artifact(
    root: Path,
    evidence_ref: Any,
    *,
    verify_sources: bool = True,
) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    ref = parse_evidence_ref(evidence_ref)
    relative = canonical_evidence_relative_path(root, ref)
    path = root / relative
    if _native_io_path(path).is_symlink() or not _native_io_path(path).is_file():
        raise ValidationFailure("Referenced evidence artifact is absent at the exact canonical path", ref)
    duplicates = _duplicate_artifact_paths(root, ref, path)
    if duplicates:
        raise ValidationFailure(
            "Duplicate evidence artifact claims the same immutable id/ref",
            {"ref": ref, "canonical_path": relative, "duplicates": duplicates},
        )
    document = load_data(path)
    classification = classify_evidence_document(root, document, verify_sources=verify_sources)
    if classification["classification"] == "LEGACY":
        raise ValidationFailure(
            "Legacy evidence is readable but not Gate-eligible without normalization",
            ref,
        )
    if classification["classification"] != "NORMALIZED":
        raise ValidationFailure(
            "Referenced evidence is not a valid normalized Gate artifact",
            {"ref": ref, "classification": classification["classification"], "error": classification.get("error")},
        )
    body = validate_normalized_evidence_document(
        root,
        document,
        expected_ref=ref,
        verify_sources=verify_sources,
    )
    return {
        "ref": ref,
        "path": relative,
        "sha256": f"sha256:{sha256_file(path)}",
        "body": body,
    }


def write_normalized_evidence(root: Path, body: dict[str, Any]) -> dict[str, Any]:
    root = native_resolve(root.expanduser())
    document = {"verification_evidence": deepcopy(body)}
    normalized = validate_normalized_evidence_document(root, document, verify_sources=True)
    relative = canonical_evidence_relative_path(root, normalized["ref"])
    path = root / relative
    if _native_io_path(path).exists():
        if _native_io_path(path).is_symlink() or not _native_io_path(path).is_file():
            raise ValidationFailure("Immutable evidence path already exists but is not a regular file", relative)
        existing = load_data(path)
        if canonical_json_bytes(existing) != canonical_json_bytes(document):
            raise ValidationFailure("Immutable evidence artifact already exists with different content", normalized["ref"])
        return resolve_evidence_artifact(root, normalized["ref"], verify_sources=True)
    write_data(path, document)
    return resolve_evidence_artifact(root, normalized["ref"], verify_sources=True)


def evidence_binding_view(resolved: dict[str, Any]) -> dict[str, str]:
    return {
        "ref": str(resolved["ref"]),
        "path": str(resolved["path"]),
        "sha256": str(resolved["sha256"]),
    }


def normalize_evidence_bindings(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ValidationFailure("evidence_bindings must be a non-empty array")
    normalized: list[dict[str, str]] = []
    refs: list[str] = []
    for index, raw in enumerate(value, 1):
        if not isinstance(raw, dict) or set(raw) != {"ref", "path", "sha256"}:
            raise ValidationFailure("Evidence binding must contain exactly ref/path/sha256", index)
        ref = parse_evidence_ref(raw.get("ref"))
        path = raw.get("path")
        digest = raw.get("sha256")
        if path != f".harness/evidence/{ref}.yaml":
            raise ValidationFailure("Evidence binding path is not canonical", {"ref": ref, "path": path})
        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            raise ValidationFailure("Evidence binding digest is not canonical", {"ref": ref, "sha256": digest})
        refs.append(ref)
        normalized.append({"ref": ref, "path": str(path), "sha256": digest})
    if len(refs) != len(set(refs)):
        raise ValidationFailure("evidence_bindings contains duplicate refs", refs)
    return sorted(normalized, key=lambda item: item["ref"])


def _normalize_ref_list(value: Any, *, field: str, allow_empty: bool = True) -> list[str]:
    if value is None:
        value = []
    if not isinstance(value, list):
        raise ValidationFailure(f"{field} must be an array")
    refs = [parse_evidence_ref(item) for item in value]
    if len(refs) != len(set(refs)):
        raise ValidationFailure(f"{field} contains duplicate evidence refs", refs)
    if not allow_empty and not refs:
        raise ValidationFailure(f"{field} must be non-empty")
    return refs


# PH-F02: positive Gate evidence is subject-specific, not a promotion of a
# generic PASS report. No source type can substitute for an operator's formal
# Gate decision. Integrity (path/digest) is only one of these checks.
_DOCUMENT_PROOF_KINDS = {
    "ARCHITECTURE_RECORD", "LIMITATIONS_RECORD", "PERMITTED_USE_RECORD",
    "START_INSTRUCTIONS", "TRACEABILITY_RECORD", "CONTRACT_RECORD",
    "OPERATIONS_RECORD", "SECURITY_RECORD", "CONFIGURATION",
    "MIGRATION_RECORD", "DEPLOYMENT_RECORD", "CHANGE_RECORD",
    "REPOSITORY_ARTIFACT", "TEST_SOURCE", "RECOVERY_RECORD",
    "ROLLBACK_RECORD", "SUPPORT_RECORD", "OWNERSHIP_RECORD",
    "DATA_LIFECYCLE_RECORD", "COMPATIBILITY_RECORD", "RELEASE_RECORD",
    "BUILD_PROVENANCE", "USER_DOCUMENTATION", "DEFECT_REGISTER",
}
_VERIFICATION_PROOF_KINDS = {
    "TEST_REPORT", "MANUAL_VERIFICATION", "PERFORMANCE_REPORT",
    "RELIABILITY_REPORT", "INTEGRATION_EVIDENCE", "MONITORING_EVIDENCE",
}
_OPERATOR_PROOF_KINDS = {"REVIEW_RECORD", "USER_ACCEPTANCE", "APPROVAL_RECORD"}
_PROOF_METHODS = {"EXECUTED_TEST", "DOCUMENT_REVIEW", "OPERATOR_VERIFICATION", "EXTERNAL_SOURCE"}
# A modest kind-specific document contract: checks structure, not correctness.
# The latter remains explicitly subject to the human Stage approval.
_DOCUMENT_TERMS = {
    "ARCHITECTURE_RECORD": ("architecture", "component", "boundar"),
    "START_INSTRUCTIONS": ("run", "command"),
    "LIMITATIONS_RECORD": ("limitation", "known"),
    "PERMITTED_USE_RECORD": ("permitted", "environment", "data"),
}


def gate_proof_methods(kind: str) -> tuple[str, ...]:
    if kind == "EXTERNAL_EVIDENCE":
        return ("EXTERNAL_SOURCE",)
    if kind == "MANUAL_VERIFICATION":
        return ("OPERATOR_VERIFICATION",)
    if kind in _VERIFICATION_PROOF_KINDS:
        return ("EXECUTED_TEST",)
    if kind in _OPERATOR_PROOF_KINDS:
        return ("OPERATOR_VERIFICATION",)
    return ("DOCUMENT_REVIEW",)


def _proof_source_document(root: Path, binding: dict[str, Any], subject_ref: str) -> tuple[str, Any]:
    path = binding.get("path")
    if not isinstance(path, str) or path.startswith((".harness/runtime/", ".harness/reports/", ".harness/evidence/")):
        raise ValidationFailure("Gate proof requires an actual subject-specific source artifact", subject_ref)
    full = resolve_inside(root, path)
    if _native_io_path(full).is_symlink() or not _native_io_path(full).is_file() or f"sha256:{sha256_file(full)}" != binding.get("sha256"):
        raise ValidationFailure("Gate proof source has been removed or altered", {"subject": subject_ref, "path": path})
    if _native_io_path(full).stat().st_size > 2_000_000:
        raise ValidationFailure("Gate proof source exceeds the supported small-document limit", path)
    if full.suffix.lower() in {".yaml", ".yml", ".json"}:
        return path, load_data(full)
    if full.suffix.lower() not in {".md", ".rst", ".txt", ".py", ".toml"}:
        raise ValidationFailure("Gate proof document has unsupported type", path)
    return path, _native_io_path(full).read_text(encoding="utf-8")


def validate_semantic_gate_proof(root: Path, body: dict[str, Any], *, subject_ref: str) -> None:
    """Require exact, reviewable semantic proof for *each* positive Gate subject.

    Tests/verification must name and substantiate a concrete check; documents
    must bind an actual product source; external evidence needs independent
    provenance. A human still determines whether that evidence is sufficient.
    """
    kind = str(body.get("kind") or "")
    provenance = body.get("provenance") or {}
    source_type = str(provenance.get("source_type") or "")
    if kind == "USER_CLAIM" or source_type in {
        "STAGE_ACCEPTANCE_PREPARATION_VERIFICATION", "USER_CLAIM", "USER_DECLARATION"
    }:
        raise ValidationFailure("A generic PASS or user claim is not subject-specific Gate proof", subject_ref)
    proof = (body.get("details") or {}).get("semantic_proof")
    if not isinstance(proof, dict):
        raise ValidationFailure("PASS Gate evidence requires an explicit semantic_proof contract", {"subject": subject_ref, "kind": kind})
    allowed_fields = {"subject_ref", "kind", "status", "method", "coverage", "source_ref", "checked_items", "test_ref"}
    if set(proof) - allowed_fields or any(proof.get(k) != v for k, v in {
        "subject_ref": subject_ref, "kind": kind, "status": "PASS"
    }.items()):
        raise ValidationFailure("Semantic proof is not exact-bound to this Gate subject", subject_ref)
    method = proof.get("method")
    if method not in _PROOF_METHODS or method not in gate_proof_methods(kind):
        raise ValidationFailure("Semantic proof method is incompatible with the evidence kind", {"subject": subject_ref, "kind": kind, "method": method})
    coverage = proof.get("coverage")
    checks = proof.get("checked_items")
    if not isinstance(coverage, str) or len(coverage.strip()) < 12 or not isinstance(checks, list) or not checks or any(
        not isinstance(item, str) or len(item.strip()) < 8 for item in checks
    ):
        raise ValidationFailure("Semantic proof needs specific coverage and performed checks", subject_ref)
    source_ref = proof.get("source_ref")
    binding = next((b for b in (body.get("source_bindings") or []) if b.get("ref") == source_ref), None)
    if binding is None or not isinstance(binding.get("path"), str):
        raise ValidationFailure("Semantic proof source_ref must identify a digest-bound concrete source", subject_ref)
    source_path, source = _proof_source_document(root, binding, subject_ref)

    if method == "DOCUMENT_REVIEW":
        if source_path.startswith(".harness/") and not (
            source_path.startswith(".harness/operator/SOURCES/")
            and source_type == "OPERATOR_SUPPLIED_DOCUMENT"
            and isinstance(provenance.get("actor"), str) and provenance["actor"].strip()
        ):
            raise ValidationFailure("Document proof must bind a product/document artifact or an operator-supplied reviewed document", subject_ref)
        if not isinstance(source, str) or len(source.strip()) < 60:
            raise ValidationFailure("Document proof source is empty or lacks substantive content", subject_ref)
        lower = source.casefold()
        missing = [term for term in _DOCUMENT_TERMS.get(kind, ()) if term not in lower]
        if missing:
            raise ValidationFailure("Document proof does not satisfy the kind-specific minimum contract", {"kind": kind, "path": source_path, "missing": missing})
        if "test_ref" in proof:
            raise ValidationFailure("Document proof must not use a test_ref", subject_ref)
    elif method == "EXECUTED_TEST":
        test_ref = proof.get("test_ref")
        if not isinstance(test_ref, str) or len(test_ref.strip()) < 8:
            raise ValidationFailure("Executed test evidence needs a specific test_ref", subject_ref)
        record = source.get("test_execution") if isinstance(source, dict) else None
        if not isinstance(record, dict) or any(record.get(k) != v for k, v in {
            "subject_ref": subject_ref, "test_ref": test_ref, "status": "PASS", "exit_code": 0
        }.items()):
            raise ValidationFailure("Executed test source has no exact PASS test result for the subject", subject_ref)
        argv = record.get("command")
        if not isinstance(argv, list) or not argv or any(not isinstance(v, str) or not v for v in argv):
            raise ValidationFailure("Executed test source has no concrete command", subject_ref)
        # Generic suites, py_compile, and test discovery do not certify a
        # named criterion. The source must identify a selected test invocation.
        if test_ref not in " ".join(argv) or any("py_compile" in v for v in argv):
            raise ValidationFailure("Generic verification does not establish per-subject executed-test coverage", subject_ref)
        recorded_checks = record.get("checks")
        if not isinstance(recorded_checks, list) or not recorded_checks or not set(checks).issubset(set(recorded_checks)):
            raise ValidationFailure("Executed test source does not substantiate the claimed checks", subject_ref)
        if source_type not in {"INDEPENDENT_TEST_EXECUTION", "PROJECT_HARNESS_SUBJECT_TEST"}:
            raise ValidationFailure("Executed test provenance is not a subject-specific test producer", subject_ref)
    elif method == "OPERATOR_VERIFICATION":
        record = source.get("operator_verification") if isinstance(source, dict) else None
        if not isinstance(record, dict) or record.get("subject_ref") != subject_ref or record.get("status") != "PASS":
            raise ValidationFailure("Operator verification source has no exact reviewed subject result", subject_ref)
        if not isinstance(record.get("actor"), str) or not record["actor"].strip() or record.get("actor") != provenance.get("actor"):
            raise ValidationFailure("Operator verification requires a named accountable actor", subject_ref)
        if not set(checks).issubset(set(record.get("checks") or [])):
            raise ValidationFailure("Operator verification does not substantiate the checked items", subject_ref)
        if source_type not in {"INDEPENDENT_OPERATOR_REVIEW", "PROJECT_HARNESS_OPERATOR_REVIEW"}:
            raise ValidationFailure("Operator verification provenance is not a subject-specific review", subject_ref)
    elif method == "EXTERNAL_SOURCE":
        if source_type != "EXTERNAL_EVIDENCE_IMPORT":
            raise ValidationFailure("External evidence requires an independently supplied source", subject_ref)
        ext = provenance.get("details") or {}
        if not isinstance(ext, dict) or not all(isinstance(ext.get(k), str) and ext[k].strip() for k in ("issuer", "origin")):
            raise ValidationFailure("External evidence must identify its issuer and origin", subject_ref)
        if isinstance(source, str):
            if len(source.strip()) < 60:
                raise ValidationFailure("External evidence source is not substantive", subject_ref)
        elif isinstance(source, dict):
            record = source.get("external_evidence")
            if not isinstance(record, dict) or record.get("subject_ref") != subject_ref or record.get("status") != "PASS" or record.get("issuer") != ext["issuer"]:
                raise ValidationFailure("External evidence source does not substantiate the subject and issuer", subject_ref)
        else:
            raise ValidationFailure("External evidence has an unsupported source format", subject_ref)
        if "test_ref" in proof:
            raise ValidationFailure("External evidence must not use a test_ref", subject_ref)

def validate_gate_evidence_closure(
    root: Path,
    *,
    level: str,
    criteria_results: Any,
    global_evidence_refs: Any,
    base_revision: str,
    overrides: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    root = native_resolve(root.expanduser())
    if not isinstance(base_revision, str) or TREE_REVISION_PATTERN.fullmatch(base_revision) is None:
        raise ValidationFailure("Gate evidence validation requires an exact product-tree baseline", base_revision)
    requirements = gate_subject_requirements(root, level, overrides)
    if not isinstance(criteria_results, list):
        raise ValidationFailure("Gate criteria_results must be an array")
    by_ref: dict[str, dict[str, Any]] = {}
    for item in criteria_results:
        if not isinstance(item, dict) or not nonempty(item.get("criterion_ref")):
            raise ValidationFailure("Gate criterion result is invalid", item)
        criterion_ref = str(item["criterion_ref"])
        if criterion_ref in by_ref:
            raise ValidationFailure("Gate criteria_results contains duplicate criterion_ref", criterion_ref)
        by_ref[criterion_ref] = item
    missing = sorted(set(requirements) - set(by_ref))
    extra = sorted(set(by_ref) - set(requirements))
    if missing or extra:
        raise ValidationFailure("Gate criteria_results do not match exact mandatory subjects", {"missing": missing, "extra": extra})

    resolved: dict[str, dict[str, Any]] = {}

    def resolve(ref: str) -> dict[str, Any]:
        item = resolved.get(ref)
        if item is None:
            item = resolve_evidence_artifact(root, ref, verify_sources=True)
            resolved[ref] = item
        return item

    for criterion_ref, requirement_kinds in requirements.items():
        result = by_ref[criterion_ref]
        status = result.get("status")
        refs = _normalize_ref_list(
            result.get("evidence_refs"),
            field=f"criteria_results[{criterion_ref}].evidence_refs",
            allow_empty=status != "PASS",
        )
        if status == "NOT_APPLICABLE":
            if refs:
                raise ValidationFailure("NOT_APPLICABLE criterion must not claim closing evidence", criterion_ref)
            continue
        if status != "PASS":
            raise ValidationFailure("Mandatory Gate subject is not formally PASS/NOT_APPLICABLE", {"criterion": criterion_ref, "status": status})
        for ref in refs:
            artifact = resolve(ref)
            body = artifact["body"]
            if body.get("status") not in POSITIVE_GATE_EVIDENCE_STATUSES:
                raise ValidationFailure(
                    "Evidence status cannot close a mandatory Gate item",
                    {"criterion": criterion_ref, "ref": ref, "status": body.get("status")},
                )
            if body.get("kind") == "USER_CLAIM":
                raise ValidationFailure(
                    "USER_CLAIM cannot close a mandatory Gate item without corroboration",
                    {"criterion": criterion_ref, "ref": ref},
                )
            if body.get("base_revision") != base_revision:
                raise ValidationFailure(
                    "Evidence base_revision is stale for this Gate baseline",
                    {"criterion": criterion_ref, "ref": ref, "expected": base_revision, "actual": body.get("base_revision")},
                )
            if criterion_ref not in body.get("criterion_refs", []):
                raise ValidationFailure(
                    "Evidence does not map the requested Gate criterion",
                    {"criterion": criterion_ref, "ref": ref, "criterion_refs": body.get("criterion_refs")},
                )
            if body.get("kind") not in requirement_kinds:
                raise ValidationFailure(
                    "Evidence kind does not satisfy the Gate subject required_evidence_kinds",
                    {"criterion": criterion_ref, "ref": ref, "kind": body.get("kind"), "required": sorted(requirement_kinds)},
                )
            validate_semantic_gate_proof(root, body, subject_ref=criterion_ref)

    global_refs = _normalize_ref_list(global_evidence_refs, field="Gate/global evidence_refs")
    for ref in global_refs:
        artifact = resolve(ref)
        body = artifact["body"]
        if body.get("status") not in POSITIVE_GATE_EVIDENCE_STATUSES:
            raise ValidationFailure(
                "Global Gate evidence must have a positive closing status",
                {"ref": ref, "status": body.get("status")},
            )
        if body.get("kind") == "USER_CLAIM":
            raise ValidationFailure("USER_CLAIM cannot be global Gate-closing evidence without corroboration", ref)
        if body.get("base_revision") != base_revision:
            raise ValidationFailure(
                "Global Gate evidence is stale for this baseline",
                {"ref": ref, "expected": base_revision, "actual": body.get("base_revision")},
            )
        mapped_subjects = [
            subject
            for subject, required_kinds in requirements.items()
            if subject in body.get("criterion_refs", []) and body.get("kind") in required_kinds
        ]
        for subject in mapped_subjects:
            validate_semantic_gate_proof(root, body, subject_ref=subject)
        if not mapped_subjects:
            raise ValidationFailure(
                "Global Gate evidence does not map a current mandatory subject with a permitted kind",
                {
                    "ref": ref,
                    "kind": body.get("kind"),
                    "criterion_refs": body.get("criterion_refs"),
                    "note": "Outcome/profile-control materialization is not part of this contract revision.",
                },
            )

    if not resolved:
        raise ValidationFailure("Stage acceptance requires at least one resolved evidence artifact")
    return sorted((evidence_binding_view(item) for item in resolved.values()), key=lambda item: item["ref"])


def validate_recorded_gate_evidence(
    root: Path,
    *,
    level: str,
    criteria_results: Any,
    global_evidence_refs: Any,
    base_revision: str,
    overrides: list[dict[str, Any]] | None,
    recorded_bindings: Any,
) -> list[dict[str, str]]:
    current = validate_gate_evidence_closure(
        root,
        level=level,
        criteria_results=criteria_results,
        global_evidence_refs=global_evidence_refs,
        base_revision=base_revision,
        overrides=overrides,
    )
    recorded = normalize_evidence_bindings(recorded_bindings)
    if current != recorded:
        raise ValidationFailure(
            "Accepted Gate evidence binding changed after acceptance",
            {"recorded": recorded, "current": current},
        )
    return current


def normalized_evidence_body(
    *,
    evidence_id: str,
    kind: str,
    status: str,
    provenance: dict[str, Any],
    base_revision: str,
    criterion_refs: list[str] | None,
    outcome_refs: list[str] | None,
    profile_control_refs: list[str] | None,
    source_bindings: list[dict[str, Any]],
    created_at: str,
    task_ref: str | None = None,
    run_ref: str | None = None,
    report_refs: list[str] | None = None,
    rationale: str | None = None,
    validator: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "id": parse_evidence_ref(evidence_id),
        "ref": parse_evidence_ref(evidence_id),
        "kind": kind,
        "status": status,
        "provenance": deepcopy(provenance),
        "base_revision": base_revision,
        "criterion_refs": list(criterion_refs or []),
        "outcome_refs": list(outcome_refs or []),
        "profile_control_refs": list(profile_control_refs or []),
        "source_bindings": deepcopy(source_bindings),
        "created_at": created_at,
    }
    optional = {
        "task_ref": task_ref,
        "run_ref": run_ref,
        "report_refs": list(report_refs or []) if report_refs is not None else None,
        "rationale": rationale,
        "validator": validator,
        "details": deepcopy(details) if details is not None else None,
    }
    for key, value in optional.items():
        if value is not None:
            body[key] = value
    return body

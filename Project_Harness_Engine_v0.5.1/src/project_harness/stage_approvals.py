from __future__ import annotations
from copy import deepcopy
import json
from typing import Any
from .errors import ValidationFailure
from .project_input import _validate_schema_node
from .resources import distribution_root

STAGE_APPROVAL_SCHEMA_ID = "SCHEMA-STAGE-APPROVAL@1"
STAGE_APPROVAL_SCHEMA_VERSION = 1

def load_stage_approval_schema() -> dict[str, Any]:
    path = distribution_root() / "schemas/stage_approval.schema.json"
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationFailure("Cannot load Stage approval schema", {"path": str(path), "error": str(exc)}) from exc
    if schema.get("$id") != STAGE_APPROVAL_SCHEMA_ID:
        raise ValidationFailure("Unexpected Stage approval schema id", schema.get("$id"))
    return schema

def stage_approval_schema_issues(value: Any) -> list[dict[str, str]]:
    schema = load_stage_approval_schema()
    return _validate_schema_node(value, schema, schema)

def validate_stage_approval_document(value: Any) -> dict[str, Any]:
    issues = stage_approval_schema_issues(value)
    if issues:
        raise ValidationFailure("Stage approval schema validation failed", issues)
    body = value.get("stage_approval") if isinstance(value, dict) else None
    if not isinstance(body, dict):
        raise ValidationFailure("Stage approval envelope is invalid")
    return deepcopy(body)

def is_strict_stage_approval(record: Any) -> bool:
    return isinstance(record, dict) and record.get("schema_version") == 1 and record.get("schema_ref") == STAGE_APPROVAL_SCHEMA_ID and record.get("record_kind") == "STAGE_APPROVAL"

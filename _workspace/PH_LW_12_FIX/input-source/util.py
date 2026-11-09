from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable

from .errors import SafetyViolation, ValidationFailure
from .platform_fs import safe_relative

ENGINE_VERSION = "0.5.1"
SCHEMA_VERSION = 7


def utc_now() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        dt = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str, *, fallback: str = "project") -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:64] or fallback


def id_token(slug: str) -> str:
    token = re.sub(r"[^A-Z0-9]+", "-", slug.upper()).strip("-")
    return token[:40] or "PROJECT"


def deep_get(value: dict[str, Any], dotted: str, default: Any = None) -> Any:
    current: Any = value
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def deep_set(value: dict[str, Any], dotted: str, new_value: Any) -> None:
    current = value
    parts = dotted.split(".")
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = new_value


def nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def ensure_relative_pattern(pattern: str, *, field: str = "path") -> str:
    pattern = pattern.replace("\\", "/").strip()
    if not pattern:
        raise ValidationFailure(f"Empty {field} pattern")
    p = PurePosixPath(pattern)
    if p.is_absolute() or ".." in p.parts:
        raise SafetyViolation(f"Unsafe {field} pattern", pattern)
    if pattern.startswith(".harness/") or pattern == ".harness":
        raise SafetyViolation(f"Product scope cannot target .harness", pattern)
    return pattern


def resolve_inside(root: Path, relative: str | Path) -> Path:
    rel = safe_relative(relative, field="relative")
    if rel.is_absolute() or ".." in rel.parts:
        raise SafetyViolation("Unsafe relative path", str(relative))
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise SafetyViolation("Path escapes root", str(relative)) from exc
    return candidate


def unique_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out

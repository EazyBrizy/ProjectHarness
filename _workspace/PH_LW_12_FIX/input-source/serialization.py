from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .errors import ValidationFailure
from .platform_fs import _native_io_path

try:  # Optional. The distribution itself emits JSON, which is valid YAML 1.2.
    import yaml  # type: ignore
except Exception:  # pragma: no cover - exercised in minimal environments
    yaml = None


def load_data(path: Path) -> Any:
    try:
        text = _native_io_path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationFailure(f"Cannot read {path}", str(exc)) from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if yaml is None:
            raise ValidationFailure(
                f"{path} is not JSON and PyYAML is unavailable",
                "Use JSON syntax (valid YAML 1.2) or install PyYAML.",
            )
        try:
            return yaml.safe_load(text)
        except Exception as exc:
            raise ValidationFailure(f"Cannot parse {path}", str(exc)) from exc


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def atomic_write_text(path: Path, text: str) -> None:
    path = _native_io_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def write_data(path: Path, value: Any) -> None:
    """Write human-readable JSON to .json or .yaml; JSON is valid YAML 1.2."""
    atomic_write_text(path, pretty_json(value))


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())

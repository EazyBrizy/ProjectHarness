from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import zipfile

from .errors import ValidationFailure
from .platform_fs import ensure_native_path


def _zip_time(timestamp: str | None) -> tuple[int, int, int, int, int, int]:
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            dt = datetime(1980, 1, 1, tzinfo=timezone.utc)
    else:
        dt = datetime(1980, 1, 1, tzinfo=timezone.utc)
    if dt.year < 1980:
        dt = dt.replace(year=1980)
    return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def zip_directory(root: Path, output: Path, *, timestamp: str | None = None) -> None:
    ensure_native_path(root, tree=True)
    ensure_native_path(output.parent)
    root = root.resolve()
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    stamp = _zip_time(timestamp)
    handoff_lock = root / ".harness/config/PROJECT_LOCK.yaml"
    stage_state = root / ".harness/stages/STAGE_STATE.yaml"
    if handoff_lock.exists() and not stage_state.exists():
        raise ValidationFailure("Stage-aware handoff is missing canonical Stage State", str(stage_state))
    try:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for current, dirs, files in os.walk(root):
                # Execution bindings are project-local metadata, never part of
                # handoff/export. Raw execution roots live outside this tree.
                relative_dir = Path(current).relative_to(root).as_posix()
                dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not
                                 (relative_dir == ".harness/runtime" and d == "EXECUTION_BINDINGS"))
                base = Path(current)
                for name in sorted(files):
                    path = base / name
                    if path.is_symlink() or name.endswith((".pyc", ".pyo")):
                        continue
                    rel = Path(root.name) / path.relative_to(root)
                    info = zipfile.ZipInfo(rel.as_posix(), date_time=stamp)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = (0o100644 & 0xFFFF) << 16
                    zf.writestr(info, path.read_bytes())
            bad = zf.testzip()
            if bad:
                raise ValidationFailure("Created ZIP failed CRC", bad)
            if handoff_lock.exists():
                required = f"{root.name}/.harness/stages/STAGE_STATE.yaml"
                if required not in set(zf.namelist()):
                    raise ValidationFailure("Created ZIP omitted canonical Stage State", required)
    except OSError as exc:
        raise ValidationFailure("Cannot create ZIP archive", str(exc)) from exc

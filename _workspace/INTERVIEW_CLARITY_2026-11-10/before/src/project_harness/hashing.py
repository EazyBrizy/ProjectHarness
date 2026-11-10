from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable
from .platform_fs import _native_io_path, native_walk


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with _native_io_path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_entries(
    root: Path,
    *,
    exclude_dirs: set[str] | None = None,
    exclude_files: set[str] | None = None,
) -> list[Path]:
    exclude_dirs = exclude_dirs or set()
    exclude_files = exclude_files or set()
    paths: list[Path] = []
    for current, dirs, files in native_walk(root):
        dirs[:] = sorted(d for d in dirs if d not in exclude_dirs)
        base = Path(current)
        for name in sorted(files):
            path = base / name
            rel = path.relative_to(root).as_posix()
            if name in exclude_files or rel in exclude_files:
                continue
            if _native_io_path(path).is_symlink():
                continue
            paths.append(path)
    return paths


def tree_hash(root: Path, paths: Iterable[Path] | None = None) -> str:
    h = hashlib.sha256()
    selected = list(paths) if paths is not None else tree_entries(root)
    for path in sorted(selected, key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(_native_io_path(path).read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def build_manifest(root: Path, *, manifest_name: str = "MANIFEST.sha256") -> str:
    lines: list[str] = []
    for path in tree_entries(
        root,
        exclude_dirs={"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"},
        exclude_files={manifest_name},
    ):
        if path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        rel = path.relative_to(root).as_posix()
        # Operation journals are mutable, chained runtime records. They are
        # validated by the control-plane phase protocol rather than the static
        # handoff/distribution manifest.
        if rel.startswith(".harness/runtime/OPERATION_JOURNAL/"):
            continue
        lines.append(f"{sha256_file(path)}  {rel}")
    return "\n".join(lines) + ("\n" if lines else "")


def parse_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw in _native_io_path(path).read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, sep, rel = raw.partition("  ")
        if not sep:
            continue
        entries[rel] = digest
    return entries

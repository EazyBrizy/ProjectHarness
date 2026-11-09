from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import zipfile
from typing import Any, Iterable

from .platform_fs import _native_io_path
from .errors import ValidationFailure
from .hashing import sha256_file, tree_entries, tree_hash
from .safety import DEFAULT_EXCLUDED_DIRS, inspect_zip
from .util import utc_now

TEXT_EXTENSIONS = {
    ".md", ".txt", ".rst", ".adoc", ".pdf", ".docx", ".odt",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".xml",
}
LANGUAGE_BY_EXTENSION = {
    ".py": "Python",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".fs": "F#",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".swift": "Swift",
    ".dart": "Dart",
    ".scala": "Scala",
    ".sh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
}
BUILD_FILES = {
    "pyproject.toml": "Python/pyproject",
    "setup.py": "Python/setuptools",
    "requirements.txt": "Python/pip",
    "package.json": "Node/package.json",
    "pnpm-lock.yaml": "Node/pnpm",
    "yarn.lock": "Node/yarn",
    "package-lock.json": "Node/npm",
    "go.mod": "Go/modules",
    "Cargo.toml": "Rust/Cargo",
    "pom.xml": "Java/Maven",
    "build.gradle": "Java/Gradle",
    "build.gradle.kts": "Kotlin/Gradle",
    "Gemfile": "Ruby/Bundler",
    "composer.json": "PHP/Composer",
    "Makefile": "Make",
    "CMakeLists.txt": "CMake",
    "Dockerfile": "Docker",
}
DOC_NAMES = {"readme.md", "agents.md", "contributing.md", "architecture.md", "design.md"}
MAX_INVENTORY_FILES = 20_000


def _kind(path: Path) -> str:
    if path.suffix.lower() in {".zip", ".tar", ".gz", ".tgz"}:
        return "ARCHIVE"
    if path.suffix.lower() == ".pdf":
        return "PDF"
    if path.suffix.lower() in {".docx", ".odt"}:
        return "DOCUMENT"
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return "TEXT_DOCUMENT"
    if path.suffix.lower() in LANGUAGE_BY_EXTENSION:
        return "SOURCE_CODE"
    return "FILE"


def _directory_files(root: Path) -> list[Path]:
    paths = tree_entries(root, exclude_dirs=DEFAULT_EXCLUDED_DIRS)
    if len(paths) > MAX_INVENTORY_FILES:
        raise ValidationFailure(
            "Source tree exceeds inventory safety limit",
            {"root": str(root), "files": len(paths), "limit": MAX_INVENTORY_FILES},
        )
    return paths


def inventory_source(path: Path, ordinal: int) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not _native_io_path(path).exists():
        raise ValidationFailure("Source does not exist", str(path))
    source_id = f"SRC-INPUT-{ordinal:03d}"
    if _native_io_path(path).is_dir():
        files = _directory_files(path)
        return {
            "ref": source_id,
            "kind": "DIRECTORY",
            "name": path.name,
            "path": str(path),
            "trust": "PROJECT_SUPPLIED",
            "authority": "UNKNOWN",
            "revision": f"sha256:{tree_hash(path, files)}",
            "readability": "PASS",
            "file_count": len(files),
            "total_bytes": sum(_native_io_path(p).stat().st_size for p in files),
            "sample_paths": [p.relative_to(path).as_posix() for p in files[:100]],
        }
    if path.suffix.lower() == ".zip":
        infos = inspect_zip(path)
        return {
            "ref": source_id,
            "kind": "ARCHIVE",
            "name": path.name,
            "path": str(path),
            "trust": "PROJECT_SUPPLIED",
            "authority": "UNKNOWN",
            "revision": f"sha256:{sha256_file(path)}",
            "readability": "PASS",
            "file_count": sum(not info.is_dir() for info in infos),
            "total_bytes": sum(info.file_size for info in infos if not info.is_dir()),
            "sample_paths": [info.filename for info in infos if not info.is_dir()][:100],
        }
    return {
        "ref": source_id,
        "kind": _kind(path),
        "name": path.name,
        "path": str(path),
        "trust": "PROJECT_SUPPLIED",
        "authority": "UNKNOWN",
        "revision": f"sha256:{sha256_file(path)}",
        "readability": "PASS",
        "file_count": 1,
        "total_bytes": _native_io_path(path).stat().st_size,
    }


def build_source_inventory(paths: Iterable[Path], *, session_ref: str) -> dict[str, Any]:
    sources = [inventory_source(path, index) for index, path in enumerate(paths, 1)]
    return {
        "source_inventory": {
            "id": f"SIV-{session_ref.removeprefix('SES-')}",
            "revision": 1,
            "session_ref": session_ref,
            "created_at": utc_now(),
            "sources": sources,
            "conflicts": [],
            "missing_material_dimensions": [],
        }
    }


def _git_revision(root: Path) -> str | None:
    """Read HEAD without launching Git or any repository command."""
    git_entry = root / ".git"
    if git_entry.is_file():
        try:
            text = git_entry.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not text.startswith("gitdir:"):
            return None
        git_dir = Path(text.split(":", 1)[1].strip())
        if not git_dir.is_absolute():
            git_dir = (root / git_dir).resolve()
    elif git_entry.is_dir():
        git_dir = git_entry
    else:
        return None
    head = git_dir / "HEAD"
    try:
        value = head.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if value and not value.startswith("ref:"):
        return value
    if not value.startswith("ref:"):
        return None
    ref = value.split(":", 1)[1].strip()
    loose = git_dir / ref
    try:
        revision = loose.read_text(encoding="utf-8").strip()
        if revision:
            return revision
    except OSError:
        pass
    packed = git_dir / "packed-refs"
    try:
        for line in packed.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith(("#", "^")):
                continue
            revision, packed_ref = line.split(" ", 1)
            if packed_ref.strip() == ref:
                return revision.strip()
    except (OSError, ValueError):
        pass
    return None


def _package_scripts(root: Path) -> dict[str, str]:
    package_json = root / "package.json"
    if not package_json.is_file():
        return {}
    try:
        value = json.loads(package_json.read_text(encoding="utf-8"))
        scripts = value.get("scripts") if isinstance(value, dict) else None
        if isinstance(scripts, dict):
            return {str(k): str(v) for k, v in scripts.items()}
    except Exception:
        pass
    return {}


def _infer_commands(root: Path, build_markers: list[str]) -> dict[str, list[list[str]]]:
    commands: dict[str, list[list[str]]] = {"build": [], "test": [], "lint": []}
    names = {Path(item).name for item in build_markers}
    if "pyproject.toml" in names or "setup.py" in names or "requirements.txt" in names:
        commands["test"].append(["python", "-m", "pytest"])
    scripts = _package_scripts(root)
    package_manager = "npm"
    if "pnpm-lock.yaml" in names:
        package_manager = "pnpm"
    elif "yarn.lock" in names:
        package_manager = "yarn"
    for kind, script in (("build", "build"), ("test", "test"), ("lint", "lint")):
        if script in scripts:
            commands[kind].append([package_manager, "run", script])
    if "go.mod" in names:
        commands["test"].append(["go", "test", "./..."])
    if "Cargo.toml" in names:
        commands["test"].append(["cargo", "test"])
    return commands


def build_repository_inventory(root: Path, *, session_ref: str) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not root.is_dir():
        raise ValidationFailure("Repository inventory requires a directory", str(root))
    files = _directory_files(root)
    language_counts: Counter[str] = Counter()
    build_markers: list[str] = []
    test_paths: list[str] = []
    documentation_paths: list[str] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        language = LANGUAGE_BY_EXTENSION.get(path.suffix.lower())
        if language:
            language_counts[language] += 1
        if path.name in BUILD_FILES:
            build_markers.append(rel)
        lower_parts = [part.lower() for part in path.relative_to(root).parts]
        if any(part in {"test", "tests", "spec", "specs", "__tests__"} for part in lower_parts):
            test_paths.append(rel)
        if path.name.lower() in DOC_NAMES or "docs" in lower_parts:
            documentation_paths.append(rel)
    revision = _git_revision(root)
    tree_digest = tree_hash(root, files)
    return {
        "repository_inventory": {
            "id": f"RIV-{session_ref.removeprefix('SES-')}",
            "revision": 1,
            "session_ref": session_ref,
            "repository_path": str(root),
            "repository_revision": f"git:{revision}" if revision else f"sha256:{tree_digest}",
            "tree_digest": f"sha256:{tree_digest}",
            "file_count": len(files),
            "total_bytes": sum(path.stat().st_size for path in files),
            "languages": [
                {"name": name, "file_count": count}
                for name, count in language_counts.most_common()
            ],
            "build_markers": sorted(build_markers),
            "test_paths": sorted(test_paths)[:500],
            "documentation_paths": sorted(documentation_paths)[:500],
            "candidate_commands": _infer_commands(root, build_markers),
            "inventory_mode": "READ_ONLY",
            "created_at": utc_now(),
        }
    }

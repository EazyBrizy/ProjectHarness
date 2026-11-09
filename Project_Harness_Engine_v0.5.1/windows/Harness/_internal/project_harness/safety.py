from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

from .platform_fs import _native_io_path, native_walk, native_resolve, native_iterdir
from .errors import SafetyViolation, ValidationFailure
from .platform_fs import safe_relative, ensure_native_path

DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".harness",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
}
DEFAULT_EXCLUDED_FILES = {".DS_Store"}


def _safe_zip_member(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    # ZIP is portable: a path valid on Linux must not alias a Windows device,
    # alternate data stream or case-normalized sibling on extraction.
    safe_relative(normalized.rstrip('/'), field="ZIP entry", windows=True)
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise SafetyViolation("Unsafe ZIP entry", name)
    # Drive-letter paths are not absolute to PurePosixPath.
    if ":" in path.parts[0]:
        raise SafetyViolation("Unsafe ZIP entry", name)
    return path


def inspect_zip(path: Path) -> list[zipfile.ZipInfo]:
    try:
        with zipfile.ZipFile(_native_io_path(path)) as zf:
            infos = zf.infolist()
            seen: set[str] = set()
            for info in infos:
                member = _safe_zip_member(info.filename)
                key = member.as_posix().casefold()
                if key in seen:
                    raise SafetyViolation("ZIP_CASE_COLLISION_OR_DUPLICATE", info.filename)
                seen.add(key)
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise SafetyViolation("ZIP symlinks are not allowed", info.filename)
            bad = zf.testzip()
            if bad:
                raise ValidationFailure("ZIP CRC validation failed", bad)
            return infos
    except zipfile.BadZipFile as exc:
        raise ValidationFailure("Invalid ZIP archive", str(path)) from exc


def safe_extract_zip(path: Path, destination: Path) -> None:
    ensure_native_path(destination, tree=True)
    infos = inspect_zip(path)  # Full CRC and path collision check BEFORE any write.
    _native_io_path(destination).mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(_native_io_path(path)) as zf:
        for info in infos:
            member = _safe_zip_member(info.filename)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise SafetyViolation("ZIP symlinks are not allowed", info.filename)
            target = native_resolve(destination / Path(*member.parts))
            try:
                target.relative_to(native_resolve(destination))
            except ValueError as exc:
                raise SafetyViolation("ZIP entry escapes destination", info.filename) from exc
            if info.is_dir():
                _native_io_path(target).mkdir(parents=True, exist_ok=True)
                continue
            _native_io_path(target.parent).mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, _native_io_path(target).open("wb") as dst:
                shutil.copyfileobj(src, dst)


def detect_single_root(directory: Path) -> Path:
    children = [p for p in native_iterdir(directory) if p.name not in {"__MACOSX", ".DS_Store"}]
    if len(children) == 1 and _native_io_path(children[0]).is_dir():
        return children[0]
    return directory


def copy_tree_filtered(
    source: Path,
    destination: Path,
    *,
    excluded_dirs: set[str] | None = None,
    excluded_files: set[str] | None = None,
) -> None:
    excluded_dirs = DEFAULT_EXCLUDED_DIRS if excluded_dirs is None else excluded_dirs
    excluded_files = DEFAULT_EXCLUDED_FILES if excluded_files is None else excluded_files
    source = source.resolve()
    _native_io_path(destination).mkdir(parents=True, exist_ok=True)
    for current, dirs, files in native_walk(source):
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in excluded_dirs and not (_native_io_path(Path(current) / d)).is_symlink()
        )
        base = Path(current)
        rel_dir = base.relative_to(source)
        target_dir = destination / rel_dir
        _native_io_path(target_dir).mkdir(parents=True, exist_ok=True)
        for name in sorted(files):
            if name in excluded_files:
                continue
            src = base / name
            if _native_io_path(src).is_symlink():
                continue
            dst = target_dir / name
            shutil.copy2(_native_io_path(src), _native_io_path(dst))


def repository_source_to_directory(source: Path, temporary_root: Path) -> Path:
    source = source.expanduser().resolve()
    if source.is_dir():
        return source
    if source.is_file() and source.suffix.lower() == ".zip":
        extracted = temporary_root / "repository-extracted"
        safe_extract_zip(source, extracted)
        return detect_single_root(extracted)
    raise ValidationFailure(
        "Repository source must be a directory or ZIP archive",
        str(source),
    )

# PH-051-04: source-only product snapshot for an isolated per-Run execution root.
# In particular, this is not copytree(): no link, device, fifo or source inode
# may become a writable object shared with the canonical repository.
def copy_disposable_product(source: Path, destination: Path) -> None:
    """Copy only canonical product files into a *new*, empty directory.

    Open source files relative to walked directory descriptors with O_NOFOLLOW.
    This prevents an attacker replacing the final component with a symlink
    between enumeration and open; directory descriptors pin traversed parents.
    A special file is rejected rather than read (FIFO reads can hang).
    """
    if not destination.is_dir() or any(destination.iterdir()):
        raise SafetyViolation("Disposable product destination must be empty", str(destination))
    source = source.resolve(strict=True)
    for current, dirs, files, directory_fd in os.fwalk(source, follow_symlinks=False):
        base = Path(current)
        rel_dir = base.relative_to(source)
        if rel_dir == Path("."):
            excluded_dirs = EXCLUDED_PRODUCT_ROOT_DIRS
            excluded_files = EXCLUDED_PRODUCT_ROOT_FILES
        else:
            excluded_dirs = {"__pycache__", ".pytest_cache", ".harness"}
            excluded_files = {".DS_Store"}
        kept_dirs = []
        for name in sorted(dirs):
            if name in excluded_dirs:
                continue
            info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                continue
            if not stat.S_ISDIR(info.st_mode):
                raise SafetyViolation("Unsafe source product directory", str(rel_dir / name))
            kept_dirs.append(name)
            target_dir = destination / rel_dir / name
            target_dir.mkdir(mode=0o755, parents=True, exist_ok=False)
        dirs[:] = kept_dirs
        for name in sorted(files):
            if name in excluded_files:
                continue
            info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                continue  # link targets, even inside the tree, never enter the snapshot
            if not stat.S_ISREG(info.st_mode):
                raise SafetyViolation("Special product files cannot be snapshotted", str(rel_dir / name))
            if info.st_nlink != 1:
                raise SafetyViolation("Product hardlinks could alias private control/outside files", str(rel_dir / name))
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            try:
                fd = os.open(name, flags, dir_fd=directory_fd)
            except OSError as exc:
                raise SafetyViolation("Cannot safely open product source", str(rel_dir / name)) from exc
            target = destination / rel_dir / name
            try:
                opened = os.fstat(fd)
                if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                        or opened.st_ino != info.st_ino or opened.st_dev != info.st_dev):
                    raise SafetyViolation("Product source changed or linked during snapshot", str(rel_dir / name))
                with os.fdopen(fd, "rb") as src:
                    fd = -1
                    with target.open("xb") as dst:
                        shutil.copyfileobj(src, dst)
                        dst.flush()
                        os.fsync(dst.fileno())
                target.chmod(0o755 if (opened.st_mode & 0o111) else 0o644)
            finally:
                if fd >= 0:
                    os.close(fd)


# Mirror the product-plane definition from workspace.snapshot_product without
# changing historical v0.5.0 snapshot semantics. Nested .harness is never
# copied; any mismatch is caught by the canonical digest equality check.
EXCLUDED_PRODUCT_ROOT_DIRS = {".harness", ".git", "node_modules", ".venv", "venv", "__pycache__"}
EXCLUDED_PRODUCT_ROOT_FILES = {
    ".DS_Store", "AGENTS.md", "CODEX_START.md", "HANDOFF_SUMMARY.md",
    "PROJECT.md", "ARCHITECTURE.md", "TECHNOLOGY.md", "ROADMAP.md",
    "STATUS.md", "MANIFEST.sha256", "VALIDATION_REPORT.json",
}


def safe_disposable_baseline_revision(root: Path) -> str:
    """Compute canonical-compatible tree digest without ever reading specials.

    File descriptors are opened from a pinned root with O_NOFOLLOW and
    O_NONBLOCK at each component. Untrusted FIFOs/symlinks cannot block or
    redirect the hashing process. The exclusion policy matches the v0.5.0
    canonical snapshot for ordinary product trees.
    """
    import hashlib

    root = root.resolve(strict=True)
    names: list[str] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        base = Path(current)
        if base == root:
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_PRODUCT_ROOT_DIRS and
                             not (base / d).is_symlink())
            excluded_files = EXCLUDED_PRODUCT_ROOT_FILES
        else:
            dirs[:] = sorted(d for d in dirs if d not in {"__pycache__", ".pytest_cache"} and
                             not (base / d).is_symlink())
            excluded_files = {".DS_Store"}
        for name in files:
            if name not in excluded_files and not (base / name).is_symlink():
                names.append((base / name).relative_to(root).as_posix())

    digest = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    for relative in sorted(names):
        parts = relative.split("/")
        directory_fd = os.open(root, directory_flags)
        try:
            for component in parts[:-1]:
                next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
                os.close(directory_fd)
                directory_fd = next_fd
            fd = os.open(parts[-1], flags, dir_fd=directory_fd)
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode):
                    raise SafetyViolation("Non-regular canonical product path", relative)
                digest.update(relative.encode("utf-8") + b"\0")
                with os.fdopen(fd, "rb", closefd=False) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                digest.update(b"\0")
                after = os.fstat(fd)
                if (before.st_ino, before.st_dev, before.st_size, before.st_mtime_ns) != (
                    after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns
                ):
                    raise ValidationFailure("BASELINE_CHANGED: source file modified during digest", relative)
            finally:
                os.close(fd)
        except OSError as exc:
            raise SafetyViolation("Cannot safely hash product file", relative) from exc
        finally:
            os.close(directory_fd)
    return "tree:sha256:" + digest.hexdigest()


# PH-051-06: exact-value secret checks shared by result/log normalization and
# future PH-051-08 *changed-file* gate. Not a generalized DLP heuristic.
def scan_exact_secret(value: object, secrets: dict[str, str] | object) -> bool:
    """Detect supplied literal secret values, including JSON-escaped strings.

    Never expose matching tokens in exceptions or returned artifacts.
    """
    if not isinstance(secrets, dict) or not secrets:
        return False
    tokens = tuple(s for s in secrets.values() if isinstance(s, str) and s)
    if not tokens:
        return False
    if isinstance(value, str):
        return any(token in value for token in tokens)
    if isinstance(value, bytes):
        return any(token.encode("utf-8") in value for token in tokens)
    if isinstance(value, dict):
        return any(scan_exact_secret(k, secrets) or scan_exact_secret(v, secrets)
                   for k, v in value.items())
    if isinstance(value, (tuple, list)):
        return any(scan_exact_secret(item, secrets) for item in value)
    return False


def redact_exact_secrets(value: str, secrets: dict[str, str] | object) -> str:
    """Redact all literal values; longer matches first prevents partial echo."""
    if not isinstance(value, str):
        raise ValueError("log must be decoded text")
    if not isinstance(secrets, dict):
        return value
    for secret in sorted({s for s in secrets.values() if isinstance(s, str) and s},
                         key=lambda s: (-len(s), s)):
        value = value.replace(secret, "[REDACTED]")
    return value


def scan_changed_product_secrets(product_root: Path, changed_paths: list[str],
                                 secrets: dict[str, str]) -> list[str]:
    """Read-only exact scan helper for PH-051-08 before apply.

    Rejects special files, links, path escapes and ambiguous names. Returns
    only path names, never bytes/secret values. This does not apply any diff.
    """
    root = Path(product_root).resolve(strict=True)
    if not root.is_dir():
        raise SafetyViolation("Product scan root must be a directory")
    leaks = []
    for name in changed_paths:
        if (not isinstance(name, str) or not name or "\\" in name or "\x00" in name or
                name.startswith("/") or any(part in ("", ".", "..") for part in name.split("/"))):
            raise SafetyViolation("Unsafe changed product path")
        if name == ".harness" or name.startswith(".harness/"):
            raise SafetyViolation("Changed product must not target control-plane path", name)
        directory = root
        for part in name.split("/")[:-1]:
            directory /= part
            info = directory.lstat()
            if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode):
                raise SafetyViolation("Changed path parent is not a regular directory", name)
        path = directory / name.split("/")[-1]
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise SafetyViolation("Unsafe changed product file", name)
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) |
                     getattr(os, "O_NONBLOCK", 0))
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1 or (
                opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                raise SafetyViolation("Changed product inode is unstable", name)
            # Bound per-file memory via streaming with overlap for cross-chunk
            # exact values. This is *not* an authorized write-set validator.
            overlap = max((len(x.encode("utf-8")) for x in secrets.values() if x), default=1) - 1
            carry = b""
            found = False
            while chunk := os.read(fd, 65536):
                content = carry + chunk
                if scan_exact_secret(content, secrets):
                    found = True
                carry = content[-overlap:] if overlap else b""
            if found:
                leaks.append(name)
        finally:
            os.close(fd)
    return leaks

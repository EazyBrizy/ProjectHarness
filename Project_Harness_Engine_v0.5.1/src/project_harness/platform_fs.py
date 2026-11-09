"""PH-LW-02: bounded, native Windows manual/control-plane filesystem boundary.

Windows manual mode uses ordinary local NTFS paths, **not** POSIX emulation.
The rootless Podman/atomic product apply backend remains Linux-only. These
helpers do not translate canonical references or rewrite historical filenames.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import tempfile
from typing import Iterator

from .errors import SafetyViolation, ValidationFailure

_WINDOWS_DEVICE = re.compile(r"(?i)^(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?$")
_WINDOWS_BAD_CHARS = set('<>:"|?*')


def _windows_component(name: str, *, field: str) -> None:
    if (not name or name in {".", ".."} or name.endswith((".", " "))
            or _WINDOWS_DEVICE.fullmatch(name)
            or any(ord(char) < 32 or char in _WINDOWS_BAD_CHARS for char in name)):
        raise SafetyViolation("WINDOWS_UNSUPPORTED_PATH_COMPONENT", {"field": field, "component": name})


def safe_relative(value: str | Path, *, field: str, windows: bool | None = None) -> Path:
    """Validate a stored relative ref; never silently normalize its bytes/case.

    Windows syntax is checked on all platforms so ZIP/control refs created on
    Linux cannot become drive/UNC/device paths upon later Windows extraction.
    """
    raw = str(value)
    w = PureWindowsPath(raw)
    if (not raw or '\x00' in raw or w.drive or w.root or raw.startswith(('/', '\\'))
            or raw.endswith(('/', '\\'))):
        raise SafetyViolation("Unsafe relative path (drive, root, or device)", {"field": field, "path": raw})
    parts = raw.replace('\\', '/').split('/')
    if not parts or any(part in ('', '..') for part in parts):
        raise SafetyViolation("Unsafe relative path (empty/traversal component)", {"field": field, "path": raw})
    is_windows = os.name == 'nt' if windows is None else windows
    if is_windows:
        for part in parts:
            if part != '.':
                _windows_component(part, field=field)
    elif ':' in parts[0]:
        # NTFS alternate streams and drive syntax must never masquerade as refs.
        raise SafetyViolation("Unsafe relative drive/stream syntax", {"field": field, "path": raw})
    return Path(value)


def assert_windows_root_form(value: str | Path) -> None:
    """Reject device namespaces, UNC/network and drive-relative roots.

    Only ordinary fully-qualified drive paths (e.g. C:\\Users\\...)
    are a supported native Windows project/workspace root.
    """
    raw = str(value)
    parsed = PureWindowsPath(raw)
    if (raw.startswith(('\\\\', '//')) or not re.fullmatch(r'[A-Za-z]:', parsed.drive)
            or not parsed.is_absolute()):
        raise SafetyViolation("WINDOWS_UNSUPPORTED_ROOT: use a local absolute drive path, not UNC/device/drive-relative", raw)
    for part in parsed.parts[1:]:
        if part not in {'.', '..'}:
            _windows_component(part, field='root')


def _native_io_path(path: Path) -> Path:
    """Private Win32 IO spelling; public paths/refs remain ordinary paths.

    This does not admit device/UNC input: validate the ordinary spelling first.
    Callers must retain their normal ownership/reparse/admission checks. Never
    persist or return this spelling, or change a process/system path policy.
    """
    path = Path(path).expanduser()
    if os.name != 'nt':
        return path
    assert_windows_root_form(Path(os.path.abspath(path)))
    return Path('\\\\?\\' + os.path.abspath(path))


def native_walk(root: Path, **options):
    """Walk through Win32 extended IO, yielding ordinary logical paths."""
    io_root = _native_io_path(root)
    for current, directories, names in os.walk(io_root, **options):
        yield root / Path(current).relative_to(io_root), directories, names


def native_glob(root: Path, pattern: str, *, recursive: bool = False):
    io_root = _native_io_path(root)
    iterator = io_root.rglob(pattern) if recursive else io_root.glob(pattern)
    for path in iterator:
        yield root / path.relative_to(io_root)


def native_iterdir(root: Path):
    """Enumerate with extended IO while keeping ordinary logical paths."""
    for child in _native_io_path(root).iterdir():
        yield root / child.name


def native_resolve(path: Path, *, strict: bool = False) -> Path:
    """Resolve an admitted local path without leaking a Win32 IO spelling.

    Reparse/namespace checks precede resolution, including for missing paths.
    Lock keys, catalog roots and returned refs retain their ordinary spelling.
    """
    path=Path(path).expanduser()
    ensure_native_path(path,file_ok=True)
    resolved=_native_io_path(path).resolve(strict=strict)
    if os.name=='nt':
        resolved=Path(str(resolved).removeprefix('\\\\?\\'))
        assert_windows_root_form(resolved)
    return resolved


def _is_link_or_junction(path: Path) -> bool:
    path = _native_io_path(path)
    return path.is_symlink() or bool(getattr(path, 'is_junction', lambda: False)())


def assert_windows_tree(root: Path) -> None:
    """Detect real case-insensitive aliases and reparse paths before mutation.

    Only called on Windows. A project with conflicting names, special files or
    junctions is unsupported; never rename records to make the tree fit.
    """
    if not _native_io_path(root).exists():
        return
    if _is_link_or_junction(root) or not _native_io_path(root).is_dir():
        raise SafetyViolation("WINDOWS_UNSUPPORTED_ROOT: not an ordinary directory", str(root))
    for current, dirs, files in native_walk(root, followlinks=False):
        seen: dict[str, str] = {}
        for name in [*dirs, *files]:
            _windows_component(name, field=str(current))
            folded = name.casefold()
            if folded in seen:
                raise SafetyViolation("WINDOWS_CASE_COLLISION", {"parent": str(current), "names": [seen[folded], name]})
            seen[folded] = name
            candidate = Path(current) / name
            if _is_link_or_junction(candidate):
                raise SafetyViolation("WINDOWS_REPARSE_POINT_UNSUPPORTED", str(candidate))
            if _native_io_path(candidate).is_file():
                info = _native_io_path(candidate).stat()
                if not stat.S_ISREG(info.st_mode):
                    raise SafetyViolation("WINDOWS_SPECIAL_FILE_UNSUPPORTED", str(candidate))
        # os.walk itself will handle normal child directories without following links.


def ensure_native_path(path: Path, *, tree: bool = False, file_ok: bool = False) -> Path:
    """Preflight a user-selected path BEFORE Path.resolve or any file writes.

    Windows disallows UNC/device roots and symlink/junction ancestors. Linux
    historical semantics are unchanged. A missing destination may be checked.
    """
    path = Path(path).expanduser()
    if os.name != 'nt':
        return path
    parsed = PureWindowsPath(str(path))
    if not parsed.drive and not parsed.root:
        path = Path(os.path.abspath(path))
    assert_windows_root_form(path)
    current = path
    while not _native_io_path(current).exists() and current != current.parent:
        current = current.parent
    if _is_link_or_junction(current):
        raise SafetyViolation("WINDOWS_REPARSE_POINT_UNSUPPORTED", str(current))
    # Check the existing ancestors (including drive root) without resolving
    # untrusted junctions. No write is performed in this function.
    for parent in [current, *current.parents]:
        if _is_link_or_junction(parent):
            raise SafetyViolation("WINDOWS_REPARSE_POINT_UNSUPPORTED", str(parent))
    io_path = _native_io_path(path)
    if io_path.exists() and not io_path.is_dir() and not (file_ok and io_path.is_file()):
        raise SafetyViolation("WINDOWS_UNSUPPORTED_ROOT: expected ordinary directory", str(path))
    if tree and io_path.is_dir():
        assert_windows_tree(path)
    return path


def ensure_writable_target(path: Path) -> None:
    """Reject a known Windows read-only target before a Stage write set starts.

    ACL/sharing violations are additionally enforced by the OS at replace time;
    they are NOT misclassified as successful writes.
    """
    if os.name != 'nt' or not _native_io_path(path).exists():
        return
    info = _native_io_path(path).stat()
    readonly = getattr(stat, 'FILE_ATTRIBUTE_READONLY', 0x1)
    if (getattr(info, 'st_file_attributes', 0) & readonly) or not (info.st_mode & stat.S_IWRITE):
        raise ValidationFailure("WINDOWS_READ_ONLY_TARGET", str(path))


@contextmanager
def stage_project_lock(project: Path) -> Iterator[None]:
    """Real cross-process lock: flock on Unix, Win32 byte-range lock on Windows.

    This lock is held across Stage journal preparation, canonical replacements,
    reconcile and commit. It lives in a user temporary directory, never in an
    agent mount or the canonical project tree. Contention fails closed.
    """
    canonical = native_resolve(project)
    ensure_native_path(canonical)
    parent = Path(tempfile.gettempdir()) / 'project-harness-stage-locks'
    parent.mkdir(mode=0o700, exist_ok=True)
    if parent.is_symlink() or not parent.is_dir():
        raise SafetyViolation("Unsafe Stage lock directory", str(parent))
    if os.name != 'nt' and parent.stat().st_mode & 0o077:
        raise SafetyViolation("Stage lock directory must be private", str(parent))
    name = hashlib.sha256(os.path.normcase(str(canonical)).encode('utf-8')).hexdigest() + '.lock'
    fd = os.open(parent / name, os.O_RDWR | os.O_CREAT | getattr(os, 'O_CLOEXEC', 0), 0o600)
    locked = False
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise SafetyViolation("Unsafe Stage lock file", name)
        if os.name == 'nt':
            import msvcrt  # Native Windows OS-level lock, never a no-op.
            if not info.st_size:
                os.write(fd, b'\0')
                os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValidationFailure("STAGE_TRANSACTION_LOCKED: another process holds the Windows lock", str(canonical)) from exc
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValidationFailure("STAGE_TRANSACTION_LOCKED: another process holds the lock", str(canonical)) from exc
        locked = True
        yield
    finally:
        if locked:
            if os.name == 'nt':
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

"""PH-LW-03: outer, cross-process fence for public manual mutations.

Lock order is always operation fence -> existing Stage transaction lock.  Each
thread may re-enter its own fence (public API composition) but a *different*
thread/process cannot: flock / msvcrt are actual OS locks, not a browser flag.
No lock files are created in the canonical product or control plane.
"""
from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import threading
from typing import Callable, Iterator, TypeVar

from .errors import SafetyViolation, ValidationFailure
from .platform_fs import ensure_native_path, native_resolve

_T = TypeVar('_T')
_local = threading.local()


@contextmanager
def project_operation_guard(root: Path) -> Iterator[None]:
    """Fail-closed, reentrant *per thread* lock, shared by CLI and Local Web.

    The existing Stage-specific lock is a distinct inner lock.  All public
    mutators acquire this outer guard before any Stage transaction; no code
    must acquire the Stage lock and then call an unguarded public operation.
    """
    ensure_native_path(Path(root))
    canonical = native_resolve(root)
    if canonical.is_symlink():
        raise SafetyViolation('Operation root cannot be a symlink', str(canonical))
    key = hashlib.sha256(os.path.normcase(str(canonical)).encode('utf-8')).hexdigest()
    held = getattr(_local, 'held', None)
    if held is None or getattr(_local, 'pid', None) != os.getpid():
        held = {}
        _local.held = held
        _local.pid = os.getpid()
    if key in held:
        held[key] += 1
        try:
            yield
        finally:
            held[key] -= 1
        return

    locks_dir = Path(tempfile.gettempdir()) / 'project-harness-operation-locks'
    locks_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if locks_dir.is_symlink() or not locks_dir.is_dir():
        raise SafetyViolation('Unsafe operation lock directory', str(locks_dir))
    if os.name != 'nt' and (locks_dir.stat().st_mode & 0o077):
        raise SafetyViolation('Operation lock directory must be private', str(locks_dir))
    fd = os.open(locks_dir / (key + '.lock'), os.O_RDWR | os.O_CREAT | getattr(os, 'O_CLOEXEC', 0), 0o600)
    locked = False
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise SafetyViolation('Unsafe operation lock file', key)
        if os.name == 'nt':
            import msvcrt
            if not info.st_size:
                os.write(fd, b'\0')
                os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValidationFailure('OPERATION_CONFLICT: operation already running for project', key) from exc
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValidationFailure('OPERATION_CONFLICT: operation already running for project', key) from exc
        locked = True
        held[key] = 1
        try:
            yield
        finally:
            del held[key]
    finally:
        try:
            if locked:
                if os.name == 'nt':
                    import msvcrt
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def guarded_mutation(function: Callable[..., _T]) -> Callable[..., _T]:
    """Guard a public API whose first positional argument is a root/workspace."""
    @wraps(function)
    def wrapper(root: Path, *args: object, **kwargs: object) -> _T:
        with project_operation_guard(Path(root)):
            return function(root, *args, **kwargs)
    return wrapper

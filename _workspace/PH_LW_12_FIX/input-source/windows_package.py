"""PH-LW-11 exact frozen inventory and staged per-user activation.

The installer verifies the payload with its compiled hashes BEFORE executing
this helper. Hash manifests detect corruption; unsigned builds are not signed.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid
import stat

from .errors import ValidationFailure
from .platform_fs import ensure_native_path
from .serialization import write_data

INVENTORY = 'PACKAGE_FILES.json'
OWNER = 'HARNESS_INSTALL_ROOT.json'


def _io_path(root: Path) -> Path:
    # Only after validating an ordinary absolute local path. This private IO
    # representation does not permit users to submit device/UNC paths.
    return Path('\\\\?\\' + str(root.absolute())) if os.name == 'nt' else root


def _checked_io_tree(root: Path) -> Path:
    ensure_native_path(root)
    io = _io_path(root)
    if io.exists():
        # Check each child before os.walk can descend into it. Do not traverse
        # an untrusted junction first, even for read-only inventory discovery.
        for current, directories, names in os.walk(io, followlinks=False):
            for path in [Path(current), *(Path(current)/name for name in directories + names)]:
                attributes = getattr(path.lstat(), 'st_file_attributes', 0)
                if path.is_symlink() or attributes & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400):
                    raise ValidationFailure('Installer reparse path rejected')
    return io


def verify_bundle(root: Path):
    root = _checked_io_tree(root)
    data = json.loads((root / INVENTORY).read_text('utf-8'))
    if (set(data) != {'format', 'build_id', 'files'} or data['format'] != 1
            or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', data['build_id'])
            or not isinstance(data['files'], dict) or not data['files']):
        raise ValidationFailure('Invalid frozen inventory')
    actual = {p.relative_to(root).as_posix(): p for p in root.rglob('*') if p.is_file()}
    if set(actual) != set(data['files']) | {INVENTORY}:
        raise ValidationFailure('Frozen file set mismatch')
    for name, digest in data['files'].items():
        if (not isinstance(digest, str) or hashlib.sha256(actual[name].read_bytes()).hexdigest() != digest
                or actual[name].stat().st_nlink != 1):
            raise ValidationFailure('Frozen file integrity mismatch', name)
    return data


def activate(payload: Path, destination: Path):
    """Copy into a new owned staging tree, verify, rename, then switch pointer.

    Interruption leaves either old current.json or a complete new version.
    Unknown directories and interrupted stages are never recursively deleted.
    """
    from .operation_guard import project_operation_guard
    _checked_io_tree(destination)
    info = verify_bundle(payload)
    destination = destination.absolute()
    if destination == payload or destination in payload.parents or payload in destination.parents:
        raise ValidationFailure('Install destination overlaps payload')
    if destination.exists() and not (destination / OWNER).exists() and any(destination.iterdir()):
        raise ValidationFailure('Destination is not an owned Harness application directory')
    destination.mkdir(parents=True, exist_ok=True)
    with project_operation_guard(destination):
        owner = destination / OWNER
        expected = {'format': 1, 'owner': 'ProjectHarnessInstaller'}
        if owner.exists() and json.loads(owner.read_text('utf-8')) != expected:
            raise ValidationFailure('Install ownership mismatch')
        if not owner.exists():
            write_data(owner, expected)
        required = sum(p.stat().st_size for p in payload.rglob('*') if p.is_file()) + 16 * 1024 * 1024
        if shutil.disk_usage(destination).free < required:
            raise ValidationFailure('INSTALL_DISK_FULL: current version preserved')
        versions = destination / 'versions'; versions.mkdir(exist_ok=True)
        version = versions / info['build_id']
        if version.exists():
            if verify_bundle(version) != info:
                raise ValidationFailure('Existing version differs; live files are never overwritten')
        else:
            stage = destination / ('staging-' + uuid.uuid4().hex)
            write_data(destination / 'install-journal.json',
                       {'state': 'COPYING', 'stage': stage.name, 'build_id': info['build_id']})
            shutil.copytree(_io_path(payload), _io_path(stage))
            verify_bundle(stage)
            # Same volume, destination absent; no replace of a live version.
            stage.rename(version)
        write_data(destination / 'current.json', {'format': 1, 'build_id': info['build_id']})
        write_data(destination / 'install-journal.json', {'state': 'COMMITTED', 'build_id': info['build_id']})
        return version


def frozen_main():
    """Fixed launcher/installer modes; never treat this EXE as Python."""
    import ctypes
    root = Path(sys.executable).resolve().parent
    try:
        verify_bundle(root)
        args = sys.argv[1:]
        if args[:1] == ['--install-payload'] and len(args) == 2:
            activate(root, Path(args[1]))
            return 0
        if args == ['--check-package']:
            return 0
        if args == ['--doctor']:
            from .validation import doctor
            return 0 if doctor()['status'] == 'PASS' else 1
        if args not in ([], ['--no-browser']):
            raise ValidationFailure('Harness.exe is a Local Web launcher, not a Python interpreter')
        from .local_web_launcher import run_local_web
        return run_local_web(open_browser=not args)
    except Exception:
        # Do not print exception details: they can include user paths or secrets.
        if not sys.argv[1:]:
            ctypes.windll.user32.MessageBoxW(None,
                'Harness не запущен: целостность комплекта или безопасное локальное соединение '
                'не подтверждены. Повторите установку из проверенного installer. '
                'Существующие проекты и процессы не изменены.', 'Project Harness', 0x10)
        return 1

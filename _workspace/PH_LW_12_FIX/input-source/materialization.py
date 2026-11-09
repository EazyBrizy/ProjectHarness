"""Public PH-LW-08 helpers: verify compiler outputs and publish without clobber.

No planner/state edits. Publication is native Windows only; the compiler and
validators retain their existing portable APIs. All paths here are trusted
server-owned paths, never HTTP paths.
"""
from __future__ import annotations

import os
import hashlib
from pathlib import Path
import zipfile

from .errors import ValidationFailure
from .hashing import sha256_file
from .operation_guard import project_operation_guard
from .platform_fs import ensure_native_path, ensure_writable_target, safe_relative, _native_io_path, native_glob
from .serialization import load_data
from .validation import validate_handoff, validate_project_directory


def directory_identity(path: Path) -> list[int]:
    ensure_native_path(path, tree=True)
    info = path.stat()
    return [info.st_dev, info.st_ino]


def handoff_tree_digest(path: Path) -> str:
    ensure_native_path(path, tree=True)
    entries = [f'{sha256_file(p)}  {p.relative_to(path).as_posix()}'
               for p in sorted(native_glob(path, '*', recursive=True)) if _native_io_path(p).is_file()]
    return 'sha256:' + hashlib.sha256(('\n'.join(entries) + '\n').encode()).hexdigest()


def check_new_destination(path: Path, *, excluded: tuple[Path, ...] = ()) -> Path:
    """Read-only admission. Existing empty folders are also collisions."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValidationFailure('DESTINATION_INVALID: требуется новая абсолютная локальная папка')
    ensure_native_path(path)
    if path.is_symlink() or path.exists():
        raise ValidationFailure('DESTINATION_EXISTS: выберите новое имя; существующая папка сохранена')
    canonical = path.resolve()
    for other in excluded:
        other = other.resolve()
        if canonical == other or canonical in other.parents or other in canonical.parents:
            raise ValidationFailure('DESTINATION_COLLISION: папка пересекается с рабочими данными')
    parent = path.parent
    while not parent.exists():
        parent = parent.parent
    ensure_writable_target(parent)
    if not parent.is_dir():
        raise ValidationFailure('DESTINATION_PARENT_INVALID')
    return canonical


def inspect_initial_handoff(directory: Path, archive: Path) -> dict:
    """Immutable initial validation; never use this on a working product."""
    for name, result in [('directory', validate_handoff(directory)),
                         ('zip', validate_handoff(archive)),
                         ('project', validate_project_directory(directory))]:
        if result.get('status') != 'PASS':
            raise ValidationFailure('INITIAL_VALIDATION_FAILED: ' + name, result)
    result = load_data(directory / '.harness/state/HANDOFF_RESULT.json')
    state = load_data(directory / '.harness/state/CURRENT_STATE.yaml')['state']
    active = state.get('active_run') or {}
    if (active.get('run_ref') != result['first_run_ref'] or active.get('task_ref') != result['first_task_ref'] or
            state['current_task_ref'] != result['first_task_ref'].split('@')[0]):
        raise ValidationFailure('FIRST_JIT_MISMATCH')
    # Two independently valid outputs are insufficient: ZIP must contain the
    # exact same compiler tree that is about to be published.
    with zipfile.ZipFile(archive) as zf:
        zipped = {name.split('/', 1)[1]: hashlib.sha256(zf.read(name)).hexdigest()
                  for name in zf.namelist() if not name.endswith('/')}
    actual = {p.relative_to(directory).as_posix(): sha256_file(p) for p in native_glob(directory, '*', recursive=True) if _native_io_path(p).is_file()}
    if zipped != actual:
        raise ValidationFailure('INITIAL_ZIP_DIRECTORY_MISMATCH')
    prompt = directory / safe_relative(result['first_prompt'], field='first_prompt', windows=True)
    return {'initial_validation': {'directory': 'PASS', 'zip': 'PASS', 'project': 'PASS'},
            'directory_identity': directory_identity(directory),
            'tree_digest': handoff_tree_digest(directory),
            'manifest_sha256': 'sha256:' + sha256_file(directory / 'MANIFEST.sha256'),
            'zip_sha256': 'sha256:' + sha256_file(archive),
            'first_task_ref': result['first_task_ref'], 'first_run_ref': result['first_run_ref'],
            'first_prompt': result['first_prompt'], 'prompt_sha256': 'sha256:' + sha256_file(prompt),
            'accepted_input_sha256': 'sha256:' + sha256_file(directory / '.harness/state/PROJECT_INPUT_ACCEPTED.yaml')}


def publish_project_directory(staged: Path, destination: Path, *, identity: list[int]) -> None:
    """Atomic Windows no-replace rename. Never rmtree, replace, copy or merge.

    Destination-volume staging is mandatory. A sharing violation leaves the
    staging intact for an explicit retry. Unsupported platforms fail closed.
    """
    with project_operation_guard(destination):
        check_new_destination(destination)
        if directory_identity(staged) != identity:
            raise ValidationFailure('STAGING_IDENTITY_CHANGED')
        if staged.stat().st_dev != destination.parent.stat().st_dev:
            raise ValidationFailure('CROSS_VOLUME_UNSUPPORTED: staging должен быть рядом с новой папкой')
        if os.name != 'nt':
            raise ValidationFailure('PUBLICATION_PLATFORM_UNSUPPORTED: требуется native Windows')
        # Windows os.rename raises FileExistsError even for an empty existing
        # destination. Unlike os.replace, it never overwrites another folder.
        os.rename(staged, destination)


def verify_published_project(destination: Path, initial: dict) -> dict:
    """Identity + accepted binding + MUTABLE validation, not initial manifest."""
    if directory_identity(destination) != initial['directory_identity']:
        raise ValidationFailure('PUBLISHED_IDENTITY_CHANGED: не подтверждён исходный каталог')
    accepted = destination / '.harness/state/PROJECT_INPUT_ACCEPTED.yaml'
    if 'sha256:' + sha256_file(accepted) != initial['accepted_input_sha256']:
        raise ValidationFailure('PUBLISHED_INPUT_CHANGED')
    result = validate_project_directory(destination)
    if result.get('status') != 'PASS':
        raise ValidationFailure('PROJECT_VALIDATION_FAILED', result)
    return result

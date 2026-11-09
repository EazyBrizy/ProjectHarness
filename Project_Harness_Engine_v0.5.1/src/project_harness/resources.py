from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

from .errors import ValidationFailure


def distribution_root() -> Path:
    if getattr(sys, 'frozen', False):
        # A frozen launcher never trusts CWD or a host resource override.
        root = Path(__file__).resolve().parent / 'resources'
        if not all((root / name).is_dir() for name in ('schemas', 'registries', 'templates', 'fixtures')):
            raise ValidationFailure('Frozen package resources are incomplete')
        return root
    override = os.environ.get("PROJECT_HARNESS_HOME")
    if override:
        root = Path(override).expanduser().resolve()
        if not root.exists():
            raise ValidationFailure("PROJECT_HARNESS_HOME does not exist", str(root))
        return root

    here = Path(__file__).resolve()
    # Source checkout/distribution: <root>/src/project_harness/resources.py
    source_root = here.parents[2]
    if all((source_root / name).is_dir() for name in ("registries", "schemas", "templates", "fixtures")):
        return source_root
    # Installed wheel: resources are bundled inside the package.
    package_root = here.parent / "resources"
    if package_root.is_dir():
        return package_root
    raise ValidationFailure("Cannot locate Project Harness distribution resources")


def resource_path(*parts: str) -> Path:
    root = distribution_root()
    path = root.joinpath(*parts)
    if not path.exists():
        raise ValidationFailure("Required distribution resource is missing", str(path))
    return path


def iter_registry_files() -> Iterable[Path]:
    return sorted((distribution_root() / "registries").glob("*.yaml"))

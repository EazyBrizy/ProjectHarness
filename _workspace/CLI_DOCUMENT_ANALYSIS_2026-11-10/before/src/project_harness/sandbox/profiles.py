"""PH-051-03 fail-closed sandbox profile and request boundary validation.

No third-party schema package is required at runtime. Contract mirrors were
introduced by PH-051-01 and are deliberately not modified in this package.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any


class SandboxPolicyError(ValueError):
    """Untrusted configuration cannot become a Podman CLI argument."""


_IMAGE = re.compile(r"[A-Za-z0-9._/-]+(?::[A-Za-z0-9._-]+)?@sha256:[a-f0-9]{64}\Z")
_ID = re.compile(r"SBX-[A-Z0-9][A-Z0-9-]*\Z")
_BINARY = re.compile(r"(?:[A-Za-z0-9_-]+|/[A-Za-z0-9_./-]+)\Z")
_FIELDS = frozenset({
    "id", "revision", "status", "backend", "image", "network_mode",
    "root_filesystem", "run_as_non_root", "drop_all_capabilities",
    "no_new_privileges", "writable_mounts", "limits",
})
_LIMIT_FIELDS = frozenset({"timeout_seconds", "memory_mb", "cpu_count", "pids", "output_bytes"})
_MAX = {"timeout_seconds": (1, 86400), "memory_mb": (64, 1048576),
        "cpu_count": (0, 256), "pids": (1, 32768), "output_bytes": (1, 52428800)}


def validate_sandbox_profile(value: Any) -> dict[str, Any]:
    """Return strictly validated ACTIVE profile, no silent normalization."""
    if not isinstance(value, dict):
        raise SandboxPolicyError("sandbox profile must be an object")
    if set(value) == {"sandbox_profile"}:
        value = value["sandbox_profile"]
    if not isinstance(value, dict) or set(value) != _FIELDS:
        raise SandboxPolicyError("sandbox profile has missing/unknown fields")
    if not isinstance(value["id"], str) or not _ID.fullmatch(value["id"]):
        raise SandboxPolicyError("invalid SBX ID")
    if type(value["revision"]) is not int or value["revision"] < 1:
        raise SandboxPolicyError("revision must be a positive integer")
    if value["status"] != "ACTIVE" or value["backend"] != "ROOTLESS_PODMAN":
        raise SandboxPolicyError("only ACTIVE ROOTLESS_PODMAN is supported")
    if not isinstance(value["image"], str) or not _IMAGE.fullmatch(value["image"]):
        raise SandboxPolicyError("image must use an immutable @sha256: digest")
    if value["network_mode"] not in ("NONE", "EXPLICIT_APPROVED_EGRESS"):
        raise SandboxPolicyError("unsupported network_mode")
    if value["root_filesystem"] != "READ_ONLY":
        raise SandboxPolicyError("root filesystem must be read-only")
    for name in ("run_as_non_root", "drop_all_capabilities", "no_new_privileges"):
        if value[name] is not True:
            raise SandboxPolicyError(f"{name} must be true")
    if value["writable_mounts"] != ["/workspace/product", "/output", "/tmp"]:
        raise SandboxPolicyError("unexpected writable mounts")
    limits = value["limits"]
    if not isinstance(limits, dict) or set(limits) != _LIMIT_FIELDS:
        raise SandboxPolicyError("limits require exact normative fields")
    for key, (lo, hi) in _MAX.items():
        v = limits[key]
        if key == "cpu_count":
            if type(v) not in (int, float) or not lo < v <= hi:
                raise SandboxPolicyError("invalid cpu_count")
        elif type(v) is not int or not lo <= v <= hi:
            raise SandboxPolicyError(f"invalid {key}")
    return value


def validate_container_executable(value: Any) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= 256 or
            not _BINARY.fullmatch(value) or "//" in value or
            any(part in (".", "..") for part in value.split("/"))):
        raise SandboxPolicyError("container executable is not an exact binary name/path")
    if value.startswith("/") and not Path(value).is_absolute():
        raise SandboxPolicyError("invalid absolute executable")
    return value


def validate_argv(value: Any, executable: str) -> list[str]:
    """Allow only an already-normalized argv list for execution in container."""
    if (not isinstance(value, list) or not 1 <= len(value) <= 64 or
            value[0] != executable):
        raise SandboxPolicyError("argv must start with the configured executable")
    for arg in value:
        if (not isinstance(arg, str) or not 1 <= len(arg) <= 4096 or
                any(ord(ch) < 32 or ord(ch) == 127 for ch in arg)):
            raise SandboxPolicyError("argv contains invalid/oversized element")
    return list(value)


def _directory(value: Any, name: str) -> Path:
    if not isinstance(value, (str, Path)):
        raise SandboxPolicyError(f"{name} must be an absolute directory")
    raw = str(value)
    if (not raw.startswith("/") or len(raw) > 2048 or
            any(c in raw for c in (":", ",", "\x00", "\n", "\r")) or
            any(part in (".", "..") for part in raw.split("/")) or "//" in raw):
        raise SandboxPolicyError(f"unsafe {name} mount path")
    p = Path(raw)
    if p.is_symlink() or p.resolve(strict=True) != p or not p.is_dir():
        raise SandboxPolicyError(f"{name} is not a canonical real directory")
    return p


def _within(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def validate_execution_mounts(request: Any) -> dict[str, Path]:
    """PH-051-04 must create these dirs; this runner never copies product data.

    An independent execution root is mandatory, and cannot be the canonical
    project, any part of its control plane, or the operator's home.
    """
    if not isinstance(request, dict):
        raise SandboxPolicyError("sandbox request must be an object")
    names = ("execution_root", "canonical_project_root")
    if any(k not in request for k in names):
        raise SandboxPolicyError("execution root and canonical root binding are mandatory")
    paths = {name: _directory(request[name], name) for name in names}
    root, canonical = paths["execution_root"], paths["canonical_project_root"]
    if _within(root, canonical) or _within(canonical, root):
        raise SandboxPolicyError("execution root and canonical project must be disjoint")
    if any(part == ".harness" for part in root.parts):
        raise SandboxPolicyError("execution root may not be inside project control")
    home = Path.home().resolve()
    if root == home or _within(home, root):
        raise SandboxPolicyError("execution root cannot overlap host HOME")
    # No arbitrary mount sources. Each must be an exact real directory below
    # the specifically bound disposable execution root.
    for key, child in (("product_dir", "product"), ("control_dir", "control"), ("output_dir", "output")):
        expected = root / child
        actual = _directory(request.get(key), key)
        if actual != expected:
            raise SandboxPolicyError(f"{key} must equal {expected}")
        paths[key] = actual
    if not os.access(paths["product_dir"], os.W_OK | os.X_OK) or not os.access(paths["output_dir"], os.W_OK | os.X_OK):
        raise SandboxPolicyError("product/output mount host dirs must be writable")
    return paths

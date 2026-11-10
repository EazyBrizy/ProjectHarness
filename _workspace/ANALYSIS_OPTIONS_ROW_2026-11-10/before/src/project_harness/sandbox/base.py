"""Minimal sandbox contract; a health record is not an OS isolation proof."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SandboxRunner(Protocol):
    """Only trusted rootless Podman is permitted for automatic execution."""

    def doctor(self, profile: dict[str, Any]) -> dict[str, Any]: ...

    def run(self, request: dict[str, Any]) -> dict[str, Any]: ...

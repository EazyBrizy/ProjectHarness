"""Minimal PH-051-02 contract. Process management belongs to a trusted sandbox."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ExecutorAdapter(Protocol):
    """Executor input is prepared argv, never a host command or shell string."""

    def doctor(self, profile: dict[str, Any]) -> dict[str, Any]: ...

    def prepare_invocation(self, run_context: dict[str, Any]) -> list[str]: ...

    def execute(self, invocation: list[str], sandbox_request: dict[str, Any]) -> dict[str, Any]: ...

    def normalize_result(self, process_result: dict[str, Any], output_dir: Path) -> dict[str, Any]: ...


class SandboxTransport(Protocol):
    """Injected by a future trusted ROOTLESS_PODMAN runner; never a host subprocess.

    This structural type is *not* an isolation attestation. PH-051-03 must
    implement technical isolation, and runtime must inject only that backend.
    """

    def doctor(self, profile: dict[str, Any]) -> dict[str, Any]: ...

    def run(self, request: dict[str, Any]) -> dict[str, Any]: ...

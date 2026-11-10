from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HarnessError(Exception):
    """Structured error surfaced by every CLI entry point."""

    code: str
    message: str
    details: Any = None
    exit_code: int = 2

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class WaitingInput(HarnessError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__("WAITING_INPUT", message, details, 3)


class WaitingDecision(HarnessError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__("WAITING_DECISION", message, details, 3)


class ValidationFailure(HarnessError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__("VALIDATION_FAILED", message, details, 2)


class SafetyViolation(HarnessError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__("SAFETY_VIOLATION", message, details, 4)

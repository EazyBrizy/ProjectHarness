"""v0.5.1 WIP: sandbox-only executor protocol; no public automatic route."""

from .base import ExecutorAdapter
# Defer importing the adapter: Podman imports the result protocol and must
# remain importable independently of its consumer.
def __getattr__(name):
    if name == "CodexCliLocalAdapter":
        from .codex_cli_local import CodexCliLocalAdapter
        return CodexCliLocalAdapter
    raise AttributeError(name)

__all__ = ["ExecutorAdapter", "CodexCliLocalAdapter"]

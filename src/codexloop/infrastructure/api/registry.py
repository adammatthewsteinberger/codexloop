# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""Registry of generated ``codexloop api`` command paths (drift gate)."""

from __future__ import annotations

REGISTERED_COMMAND_PATHS: set[str] = set()


def register_command_path(path: str) -> None:
    REGISTERED_COMMAND_PATHS.add(path)


def clear_registry() -> None:
    REGISTERED_COMMAND_PATHS.clear()

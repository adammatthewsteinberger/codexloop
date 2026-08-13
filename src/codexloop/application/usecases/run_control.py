"""Use cases: enqueue operator control commands via a port."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from codexloop.domain.control import ControlCommand


class ControlInbox(Protocol):
    def enqueue(self, command: ControlCommand) -> Path: ...


def enqueue_control(inbox: ControlInbox, command: ControlCommand) -> Path:
    """Enqueue ``command`` and return the path written."""
    return inbox.enqueue(command)


__all__ = ["ControlInbox", "enqueue_control"]

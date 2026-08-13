"""Notifier — run a configured command, or record a no-op when unset."""

from __future__ import annotations

import shlex
import subprocess  # nosec B404 — argv list from operator config, never shell=True
from collections.abc import Sequence


class CommandNotifier:
    def __init__(self, command: str | Sequence[str] | None = None) -> None:
        self._command = command
        self.noop_notifications: list[tuple[str, str]] = []

    def notify(self, title: str, body: str) -> None:
        if not self._command:
            self.noop_notifications.append((title, body))
            return
        argv = shlex.split(self._command) if isinstance(self._command, str) else list(self._command)
        subprocess.run([*argv, title, body], check=False)  # nosec B603 — no shell; operator-configured argv

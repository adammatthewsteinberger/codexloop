# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""ProgressReporter — log-based adapter for operator-visible run events."""

from __future__ import annotations

from codexloop.application.ports import Logger
from codexloop.infrastructure.logging import StructlogAppLogger


class LoggingProgressReporter:
    def __init__(self, logger: Logger | None = None) -> None:
        self._logger: Logger = logger if logger is not None else StructlogAppLogger()

    def report(self, event: str, **detail: object) -> None:
        self._logger.info(event, **detail)

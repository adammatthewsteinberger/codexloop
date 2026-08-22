# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""Real Clock and Sleeper adapters. Test doubles live in tests/application/fakes.py."""

from __future__ import annotations

from datetime import UTC, datetime

import anyio

from codexloop.application.ports import Clock


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class AnyioSleeper:
    """Sleep the remaining delta via ``anyio.sleep``; past targets are a no-op."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock: Clock = clock if clock is not None else SystemClock()

    async def sleep_until(self, when: datetime) -> None:
        delay = (when - self._clock.now()).total_seconds()
        if delay > 0:
            await anyio.sleep(delay)

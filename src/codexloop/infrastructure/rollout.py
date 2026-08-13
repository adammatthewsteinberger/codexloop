"""Best-effort rollout-tail telemetry (confidence C, R5). Strictly read-only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from codexloop.domain.capacity import PlanWindows
from codexloop.infrastructure.agent.events import JsonlParser, RateLimitsUpdated

_DEFAULT_MAX_AGE = timedelta(minutes=10)


def read_rollout_rate_limits(
    *,
    codex_home: Path | None = None,
    max_age: timedelta = _DEFAULT_MAX_AGE,
    now: datetime | None = None,
) -> PlanWindows | None:
    """Return the newest contained rollout snapshot, or ``None``. Never raises."""
    try:
        return _read(codex_home=codex_home, max_age=max_age, now=now)
    except Exception:
        return None


def _read(
    *,
    codex_home: Path | None,
    max_age: timedelta,
    now: datetime | None,
) -> PlanWindows | None:
    home = Path.home() / ".codex" if codex_home is None else Path(codex_home)
    try:
        root = home.resolve()
    except OSError:
        return None
    if not root.is_dir():
        return None

    clock = now if now is not None else datetime.now(UTC)
    newest = _newest_contained_jsonl(root)
    if newest is None:
        return None
    if _is_stale(newest, now=clock, max_age=max_age):
        return None
    return _parse_file(newest, now=clock)


def _newest_contained_jsonl(root: Path) -> Path | None:
    newest: Path | None = None
    newest_mtime = float("-inf")
    try:
        matches = root.rglob("*.jsonl")
    except OSError:
        return None
    for path in matches:
        if not _contained(path, root):
            continue
        try:
            if not path.is_file():
                continue
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime >= newest_mtime:
            newest = path
            newest_mtime = mtime
    return newest


def _contained(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    try:
        return resolved.is_relative_to(root)
    except ValueError:
        return False


def _is_stale(path: Path, *, now: datetime, max_age: timedelta) -> bool:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return True
    return now - mtime > max_age


def _parse_file(path: Path, *, now: datetime) -> PlanWindows | None:
    parser = JsonlParser(now=now)
    last: PlanWindows | None = None
    found = False
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                event = parser.parse_line(line)
                if isinstance(event, RateLimitsUpdated):
                    last = event.plan_windows
                    found = True
    except (OSError, UnicodeDecodeError):
        return None
    return last if found else None

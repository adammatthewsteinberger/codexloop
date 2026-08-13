"""Composition root — the only module permitted to import every onion layer."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from codexloop.application.ports import AgentGateway
from codexloop.application.runner import RunnerContext
from codexloop.domain.budget import Budget
from codexloop.domain.control import ControlCommand, Stop
from codexloop.domain.errors import ConfigurationError
from codexloop.domain.session import ThreadRef
from codexloop.domain.waiting import AdaptiveWaitPolicy, WaitConfig
from codexloop.infrastructure.agent.argv import ExecOpts
from codexloop.infrastructure.agent.gateway import CodexExecGateway
from codexloop.infrastructure.agent.probe import ExecCapacityProbe
from codexloop.infrastructure.clock import AnyioSleeper, SystemClock
from codexloop.infrastructure.config import RunnerConfig, load_config
from codexloop.infrastructure.lock import AdvisoryFileLock
from codexloop.infrastructure.logging import configure_logging
from codexloop.infrastructure.rundir import RunDirectory, runs_root_for
from codexloop.infrastructure.state import FileRunStateStore

__all__ = [
    "DrainControl",
    "RunnerConfig",
    "build_runner",
    "current_drain",
    "list_run_records",
    "read_run_events",
    "read_run_record",
    "register_drain",
]

_ACTIVE_DRAIN: DrainControl | None = None


class DrainControl:
    """RunControl that surfaces SIGINT/SIGTERM as a domain ``Stop``."""

    def __init__(self) -> None:
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def poll(self) -> Sequence[ControlCommand]:
        if not self._stop:
            return []
        self._stop = False
        return [Stop()]


def current_drain() -> DrainControl | None:
    return _ACTIVE_DRAIN


def register_drain(control: DrainControl | None = None) -> DrainControl:
    """Install the process-wide drain. Pass a control to replace; omit to reuse."""
    global _ACTIVE_DRAIN
    if control is not None:
        _ACTIVE_DRAIN = control
        return control
    if _ACTIVE_DRAIN is None:
        _ACTIVE_DRAIN = DrainControl()
    return _ACTIVE_DRAIN


class _JsonThreadCatalog:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._threads: dict[str, ThreadRef] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        if not isinstance(raw, list):
            return
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                ref = ThreadRef(
                    thread_id=str(item["thread_id"]),
                    cwd=str(item["cwd"]),
                    started_at=datetime.fromisoformat(str(item["started_at"])),
                    model=str(item["model"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
            self._threads[ref.thread_id] = ref

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "thread_id": ref.thread_id,
                "cwd": ref.cwd,
                "started_at": ref.started_at.isoformat(),
                "model": ref.model,
            }
            for ref in self._threads.values()
        ]
        self._path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def list_threads(self) -> Sequence[ThreadRef]:
        return list(self._threads.values())

    def get(self, thread_id: str) -> ThreadRef | None:
        return self._threads.get(thread_id)

    def record(self, ref: ThreadRef) -> None:
        self._threads[ref.thread_id] = ref
        self._save()


def _select_gateway(transport: str, *, cwd: Path, config: RunnerConfig) -> AgentGateway:
    if transport == "app-server":
        raise ConfigurationError("app-server transport is not implemented")
    if transport != "exec":
        raise ConfigurationError(f"unknown transport {transport!r}")
    return CodexExecGateway(
        cwd=cwd,
        opts=ExecOpts(prompt="", model=config.model, add_dirs=config.add_dirs),
    )


def build_runner(
    config: RunnerConfig | None = None,
    *,
    transport: str = "exec",
    cwd: Path | None = None,
    flags: Mapping[str, object] | None = None,
    ensure_run: bool = True,
) -> RunnerContext:
    """Wire ports for one CLI invocation. ``cli/`` must not import infrastructure."""
    cwd = Path.cwd() if cwd is None else cwd
    if config is None:
        config = load_config(cwd=cwd, flags=flags)

    configure_logging(
        level=config.log_level,
        json_logs=config.json_logs,
        log_file=Path(config.log_file) if config.log_file else None,
    )

    runs_root = runs_root_for(cwd)
    rundir: RunDirectory | None = RunDirectory.create(runs_root) if ensure_run else None
    clock = SystemClock()
    drain = register_drain()

    def write_artifact(name: str, content: str) -> None:
        if rundir is None:
            return
        (rundir.root / name).write_text(content, encoding="utf-8")

    return RunnerContext(
        clock=clock,
        sleeper=AnyioSleeper(clock),
        gateway=_select_gateway(transport, cwd=cwd, config=config),
        probe=ExecCapacityProbe(cwd=cwd),
        store=FileRunStateStore(runs_root),
        control=drain,
        catalog=_JsonThreadCatalog(cwd / ".codexloop" / "threads.json"),
        lock=AdvisoryFileLock(cwd / ".codexloop" / "locks"),
        write_artifact=write_artifact,
        budget=Budget(max_turns=config.max_turns, max_dollars=None, max_wall_clock=None),
        wait_policy=AdaptiveWaitPolicy(WaitConfig()),
        max_wait=config.max_wait,
        run_id=rundir.run_id if rundir is not None else "anonymous",
        cwd=str(cwd),
        model=config.model,
    )


def list_run_records(cwd: Path | None = None) -> list[dict[str, Any]]:
    root = runs_root_for(Path.cwd() if cwd is None else cwd)
    if not root.is_dir():
        return []
    return [_record_from_dir(child) for child in sorted(root.iterdir()) if child.is_dir()]


def _latest_run_key(record: dict[str, Any]) -> datetime:
    meta = record.get("meta")
    if isinstance(meta, dict):
        raw = meta.get("started_at")
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw)
            except ValueError:
                pass
    try:
        return datetime.fromtimestamp(Path(str(record["root"])).stat().st_mtime, tz=UTC)
    except OSError:
        return datetime.min.replace(tzinfo=UTC)


def read_run_record(run_id: str | None = None, *, cwd: Path | None = None) -> dict[str, Any] | None:
    records = list_run_records(cwd)
    if not records:
        return None
    if run_id is None:
        return max(records, key=_latest_run_key)
    for record in records:
        if record["run_id"] == run_id:
            return record
    return None


def read_run_events(run_id: str | None = None, *, cwd: Path | None = None) -> str:
    record = read_run_record(run_id, cwd=cwd)
    if record is None:
        return ""
    events_path = Path(str(record["root"])) / "events.jsonl"
    if not events_path.is_file():
        return ""
    return events_path.read_text(encoding="utf-8")


def _record_from_dir(root: Path) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    state: dict[str, Any] = {}
    meta_path = root / "meta.json"
    state_path = root / "state.json"
    if meta_path.is_file():
        loaded = json.loads(meta_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            meta = loaded
    if state_path.is_file():
        loaded = json.loads(state_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            state = loaded
    return {"run_id": root.name, "root": str(root), "meta": meta, "state": state}

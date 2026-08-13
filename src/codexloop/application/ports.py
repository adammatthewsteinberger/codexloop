"""Application ports — Protocols implemented by infrastructure, never imported from it.

``application/`` knows the shape of a collaborator, never a concrete adapter.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from codexloop.application.dto import ProbeResult, TurnOutcome
from codexloop.domain.control import ControlCommand
from codexloop.domain.model_profile import ModelEffortProfile
from codexloop.domain.session import ThreadRef

__all__ = [
    "AgentGateway",
    "ApiGateway",
    "AuditLog",
    "CapacityProbe",
    "Clock",
    "Logger",
    "Notifier",
    "PermissionMode",
    "ProgressReporter",
    "RunControl",
    "RunEventSink",
    "RunResources",
    "RunSnapshotSink",
    "RunStateStore",
    "SavePointStore",
    "SessionLock",
    "Sleeper",
    "StateBus",
    "ThreadCatalog",
]


class PermissionMode(StrEnum):
    """Autonomy posture at the application boundary — not Codex CLI flag strings."""

    AUTONOMOUS = "autonomous"
    READ_ONLY = "read_only"
    FULL_ACCESS = "full_access"


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime: ...


@runtime_checkable
class Sleeper(Protocol):
    async def sleep_until(self, when: datetime) -> None: ...


@runtime_checkable
class AgentGateway(Protocol):
    """Vendor-agnostic agent session (exec and app-server adapters implement this)."""

    async def send_turn(self, prompt: str) -> TurnOutcome: ...
    async def close(self) -> None: ...
    async def set_profile(self, profile: ModelEffortProfile) -> None: ...
    async def set_permission_mode(self, mode: PermissionMode) -> None: ...
    async def set_cwd(self, path: str) -> None: ...
    async def set_session_resources(self, resources: Mapping[str, object]) -> None: ...
    def resolve_tool_approval(self, request_id: str, *, allow: bool, reason: str = "") -> bool: ...


@runtime_checkable
class CapacityProbe(Protocol):
    async def probe(self) -> ProbeResult: ...


@runtime_checkable
class ThreadCatalog(Protocol):
    """Our run registry keyed by ``thread_id``, not vendor session discovery."""

    def list_threads(self) -> Sequence[ThreadRef]: ...
    def get(self, thread_id: str) -> ThreadRef | None: ...
    def record(self, ref: ThreadRef) -> None: ...


@runtime_checkable
class ProgressReporter(Protocol):
    def report(self, event: str, **detail: object) -> None: ...


@runtime_checkable
class AuditLog(Protocol):
    def append(self, event_type: str, payload: Mapping[str, object]) -> None: ...


@runtime_checkable
class Notifier(Protocol):
    def notify(self, title: str, body: str) -> None: ...


@runtime_checkable
class Logger(Protocol):
    def bind(self, **kwargs: object) -> Logger: ...
    def info(self, event: str, **kwargs: object) -> None: ...
    def warning(self, event: str, **kwargs: object) -> None: ...
    def error(self, event: str, **kwargs: object) -> None: ...


@runtime_checkable
class RunStateStore(Protocol):
    def load(self, run_id: str) -> dict[str, object] | None: ...
    def save(self, run_id: str, state: Mapping[str, object]) -> None: ...


@runtime_checkable
class SessionLock(Protocol):
    def acquire(self, thread_id: str) -> bool: ...
    def release(self, thread_id: str) -> None: ...


@runtime_checkable
class RunControl(Protocol):
    def poll(self) -> Sequence[ControlCommand]: ...


@runtime_checkable
class RunEventSink(Protocol):
    def emit(self, event: Mapping[str, object]) -> None: ...


@runtime_checkable
class StateBus(Protocol):
    def publish(self, event_type: str, payload: Mapping[str, object]) -> None: ...
    def subscribe(self, callback: Callable[[str, Mapping[str, object]], None]) -> None: ...


@runtime_checkable
class SavePointStore(Protocol):
    def create(self, run_id: str, label: str) -> str: ...
    def list(self, run_id: str) -> Sequence[str]: ...
    def unwind(self, run_id: str, to: str) -> None: ...


@runtime_checkable
class RunSnapshotSink(Protocol):
    def write(self, snapshot: Mapping[str, object]) -> None: ...


@runtime_checkable
class ApiGateway(Protocol):
    def invoke(self, method_path: str, **kwargs: object) -> object: ...


@runtime_checkable
class RunResources(Protocol):
    """Placeholder for run-scoped attachments applied mid-run."""

    def as_payload(self) -> Mapping[str, object]: ...

# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""Backwards-compatible re-export of `application.interfaces`.

The Protocols moved into `application/interfaces/` so every seam lives in
one discoverable place, one module per collaborator family. This shim keeps
the old `from codexloop.application.ports import X` path working; new code
should import from `codexloop.application.interfaces`.
"""

from __future__ import annotations

from codexloop.application.interfaces import (
    AgentGateway,
    ApiGateway,
    AuditLog,
    CapacityProbe,
    Clock,
    ControlInbox,
    DoctorCheck,
    DoctorEnvironment,
    DoctorReport,
    Logger,
    Notifier,
    PermissionMode,
    ProgressReporter,
    RunControl,
    RunEventSink,
    RunResources,
    RunSnapshotSink,
    RunStateStore,
    SavePointStore,
    SessionLock,
    Sleeper,
    StateBus,
    ThreadCatalog,
)

__all__ = [
    "AgentGateway",
    "ApiGateway",
    "AuditLog",
    "CapacityProbe",
    "Clock",
    "ControlInbox",
    "DoctorCheck",
    "DoctorEnvironment",
    "DoctorReport",
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

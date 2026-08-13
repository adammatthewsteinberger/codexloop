"""SessionLock — advisory file lock keyed by thread id, with stale-pid break."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from codexloop.application.ports import Logger

_LOG = logging.getLogger(__name__)


class AdvisoryFileLock:
    def __init__(self, directory: Path, *, logger: Logger | None = None) -> None:
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)
        self._logger = logger

    def _path(self, thread_id: str) -> Path:
        return self._directory / f"{thread_id}.lock"

    def acquire(self, thread_id: str) -> bool:
        path = self._path(thread_id)
        if path.is_file():
            pid = _read_pid(path)
            if pid is not None and _pid_alive(pid):
                return False
            reason = "process is dead" if pid is not None else "invalid lockfile"
            self._log_stale(thread_id, pid, reason)
            path.unlink(missing_ok=True)
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        try:
            os.write(fd, f"{os.getpid()}\n".encode())
        finally:
            os.close(fd)
        return True

    def release(self, thread_id: str) -> None:
        self._path(thread_id).unlink(missing_ok=True)

    def _log_stale(self, thread_id: str, pid: int | None, reason: str) -> None:
        if self._logger is not None:
            self._logger.warning(
                "stale_lock_broken",
                thread_id=thread_id,
                pid=pid,
                reason=reason,
            )
            return
        _LOG.warning(
            "stale lock broken for thread %s (pid=%s): %s",
            thread_id,
            pid,
            reason,
        )


def _read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True

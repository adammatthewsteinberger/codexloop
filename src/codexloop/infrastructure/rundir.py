"""Per-run control directory layout under ``.codexloop/runs/<run_id>/``."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path


class RunDirectory:
    """Filesystem layout for one autonomous run's control plane."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.run_id = root.name
        self.meta_path = root / "meta.json"
        self.state_path = root / "state.json"
        self.events_path = root / "events.jsonl"
        self.inbox = root / "inbox"
        self.archive = root / "archive"

    @classmethod
    def create(cls, runs_root: Path, *, run_id: str | None = None) -> RunDirectory:
        if run_id is None:
            run_id = str(uuid.uuid4())
        directory = cls(runs_root / run_id)
        directory.ensure_layout()
        return directory

    def ensure_layout(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.inbox.mkdir(exist_ok=True)
        self.archive.mkdir(exist_ok=True)
        if not self.meta_path.is_file():
            meta = {
                "run_id": self.run_id,
                "pid": os.getpid(),
                "started_at": datetime.now(UTC).isoformat(),
            }
            self.meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        if not self.state_path.is_file():
            self.state_path.write_text("{}\n", encoding="utf-8")
        if not self.events_path.is_file():
            self.events_path.touch()


def runs_root_for(cwd: Path) -> Path:
    return cwd / ".codexloop" / "runs"

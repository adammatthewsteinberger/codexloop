# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""Tests for the Textual stream UI helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from codexloop.infrastructure.stream_ui import StreamUiApp


@pytest.mark.asyncio
async def test_stream_ui_mounts_missing_file(tmp_path: Path) -> None:
    app = StreamUiApp(tmp_path / "missing.jsonl")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#log") is not None


@pytest.mark.asyncio
async def test_stream_ui_mounts_existing_log(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"type":"turn.completed"}\n', encoding="utf-8")
    app = StreamUiApp(path)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#log") is not None

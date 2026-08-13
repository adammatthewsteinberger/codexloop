"""Unit tests for the scripted test-agent gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from codexloop.domain.completion import DEFAULT_DONE_MARKER
from codexloop.infrastructure.agent.scripted import (
    ALLOW_TEST_AGENT_ENV,
    TEST_AGENT_SCRIPT_ENV,
    load_agent_script,
    resolve_test_agent_from_env,
)


def test_script_without_allow_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script = tmp_path / "s.json"
    script.write_text('{"probes":[{}],"turns":[{"signals":{}}]}', encoding="utf-8")
    monkeypatch.setenv(TEST_AGENT_SCRIPT_ENV, str(script))
    monkeypatch.delenv(ALLOW_TEST_AGENT_ENV, raising=False)
    with pytest.raises(RuntimeError, match=ALLOW_TEST_AGENT_ENV):
        resolve_test_agent_from_env()


def test_resolve_loads_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    fixtures = Path(__file__).resolve().parents[1] / "live" / "fixtures" / "agent_scripts"
    monkeypatch.setenv(ALLOW_TEST_AGENT_ENV, "1")
    monkeypatch.setenv(TEST_AGENT_SCRIPT_ENV, str(fixtures / "done.json"))
    pair = resolve_test_agent_from_env()
    assert pair is not None
    gateway, probe = pair
    assert gateway is not None
    assert probe is not None


def test_load_done_script() -> None:
    fixtures = Path(__file__).resolve().parents[1] / "live" / "fixtures" / "agent_scripts"
    script = load_agent_script(fixtures / "done.json")
    assert len(script.turns) == 1
    assert script.turns[0].signals.final_message == DEFAULT_DONE_MARKER

"""Ops CLI: stop/prompt/capacity/doctor/savepoints and related commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from codexloop.application.usecases.doctor import DoctorCheck, DoctorReport
from codexloop.cli.app import app
from codexloop.domain.capacity import PlanWindows, RateLimitWindow
from codexloop.infrastructure.rundir import RunDirectory, runs_root_for

_RUNNER = CliRunner()

OPS = (
    "stop",
    "prompt",
    "capacity",
    "doctor",
    "watch",
    "savepoints",
    "unwind",
    "reset",
    "snapshot",
    "model",
    "effort",
    "approval",
    "sandbox",
    "cwd",
)


def _invoke(*args: str) -> object:
    return _RUNNER.invoke(app, list(args))


def _seed_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> RunDirectory:
    monkeypatch.chdir(tmp_path)
    return RunDirectory.create(runs_root_for(tmp_path))


def test_help_lists_ops_commands() -> None:
    result = _invoke("--help")
    assert result.exit_code == 0
    for name in OPS:
        assert name in result.output


@pytest.mark.parametrize("name", OPS)
def test_ops_command_help_renders(name: str) -> None:
    result = _invoke(name, "--help")
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_stop_writes_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rundir = _seed_run(tmp_path, monkeypatch)
    result = _invoke("stop")
    assert result.exit_code == 0
    files = list(rundir.inbox.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload == {"kind": "stop"}


def test_prompt_now_writes_inbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rundir = _seed_run(tmp_path, monkeypatch)
    result = _invoke("prompt", "hello", "--now")
    assert result.exit_code == 0
    files = list(rundir.inbox.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload == {"kind": "prompt", "text": "hello", "timing": "now"}


def test_capacity_says_unavailable_honestly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("codexloop.cli.commands.capacity.read_capacity_windows", lambda: None)
    result = _invoke("capacity")
    assert result.exit_code == 0
    assert "unavailable" in result.output.lower()


def test_capacity_prints_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    windows = PlanWindows(
        primary=RateLimitWindow(used_percent=10.0, window_minutes=300, resets_at=None),
        secondary=None,
        plan_type="plus",
        limit_reached=None,
    )
    monkeypatch.setattr(
        "codexloop.cli.commands.capacity.read_capacity_windows",
        lambda: windows,
    )
    result = _invoke("capacity")
    assert result.exit_code == 0
    assert "plus" in result.output
    assert "primary:" in result.output
    assert "secondary: unavailable" in result.output


def test_doctor_prints_auth_and_strategies(monkeypatch: pytest.MonkeyPatch) -> None:
    report = DoctorReport(
        checks=(
            DoctorCheck(name="codex-cli", passed=True, detail="ok"),
            DoctorCheck(name="auth-mode", passed=True, detail="active auth mode: api_key"),
        ),
        auth_mode="api_key",
        probe_strategies={"exec": True, "app-server": False, "rollout": True},
    )
    monkeypatch.setattr("codexloop.cli.commands.doctor.run_doctor_checks", lambda cwd=None: report)
    result = _invoke("doctor")
    assert result.exit_code == 0
    assert "auth_mode: api_key" in result.output
    assert "exec=live" in result.output
    assert "app-server=unavailable" in result.output


def test_doctor_exits_1_on_failed_check(monkeypatch: pytest.MonkeyPatch) -> None:
    report = DoctorReport(
        checks=(DoctorCheck(name="codex-cli", passed=False, detail="missing"),),
        auth_mode="none",
        probe_strategies={"exec": True},
    )
    monkeypatch.setattr("codexloop.cli.commands.doctor.run_doctor_checks", lambda cwd=None: report)
    result = _invoke("doctor")
    assert result.exit_code == 1


def test_model_queues_set_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rundir = _seed_run(tmp_path, monkeypatch)
    result = _invoke("model", "gpt-5")
    assert result.exit_code == 0
    payload = json.loads(next(rundir.inbox.glob("*.json")).read_text(encoding="utf-8"))
    assert payload == {"kind": "set_model", "model": "gpt-5"}


def test_watch_prints_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rundir = _seed_run(tmp_path, monkeypatch)
    rundir.state_path.write_text(json.dumps({"reason": "max_wait"}) + "\n", encoding="utf-8")
    result = _invoke("watch")
    assert result.exit_code == 0
    assert "max_wait" in result.output

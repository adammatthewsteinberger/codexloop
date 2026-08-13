"""Ops CLI: stop/prompt/capacity/doctor/savepoints and related commands."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from codexloop.application.usecases.doctor import DoctorCheck, DoctorReport
from codexloop.cli.app import app
from codexloop.domain.capacity import PlanWindows, RateLimitWindow
from codexloop.domain.savepoint import SavePointRef, UnwindResult
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


def test_effort_approval_sandbox_cwd_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rundir = _seed_run(tmp_path, monkeypatch)
    assert _invoke("effort", "high").exit_code == 0
    assert _invoke("approval", "never").exit_code == 0
    assert _invoke("sandbox", "workspace-write").exit_code == 0
    assert _invoke("cwd", "/tmp/work").exit_code == 0
    kinds = {json.loads(p.read_text(encoding="utf-8"))["kind"] for p in rundir.inbox.glob("*.json")}
    assert kinds == {"set_effort", "set_approval", "set_sandbox", "set_cwd"}


def test_prompt_requires_exactly_one_timing() -> None:
    result = _invoke("prompt", "hi")
    assert result.exit_code == 2
    result = _invoke("prompt", "hi", "--now", "--next-turn")
    assert result.exit_code == 2


def test_savepoints_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_run(tmp_path, monkeypatch)
    monkeypatch.setattr("codexloop.cli.commands.savepoints.list_savepoints", lambda run_id=None: [])
    result = _invoke("savepoints")
    assert result.exit_code == 0
    assert "no savepoints" in result.output


def test_savepoints_lists_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_run(tmp_path, monkeypatch)
    point = SavePointRef(
        n=2,
        sha="deadbeefdeadbeef",
        label="turn",
        ref="refs/codexloop/r/2",
        at=datetime(2026, 1, 1, tzinfo=UTC),
        plan_item=None,
        committed=False,
    )
    monkeypatch.setattr(
        "codexloop.cli.commands.savepoints.list_savepoints",
        lambda run_id=None: [point],
    )
    result = _invoke("savepoints")
    assert result.exit_code == 0
    assert "deadbeef" in result.output
    assert "ref-only" in result.output or "turn" in result.output


def test_unwind_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_run(tmp_path, monkeypatch)
    point = SavePointRef(
        n=1,
        sha="abc123",
        label="x",
        ref="refs/codexloop/r/1",
        at=datetime(2026, 1, 1, tzinfo=UTC),
        plan_item=None,
        committed=True,
    )
    monkeypatch.setattr(
        "codexloop.cli.commands.unwind.unwind_savepoint",
        lambda *a, **k: UnwindResult(to=point, backup_ref="refs/backup", restored_sha="abc123"),
    )
    result = _invoke("unwind", "1")
    assert result.exit_code == 0
    assert "restored" in result.output


def test_reset_and_snapshot_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_run(tmp_path, monkeypatch)

    class _Point:
        n = 1
        sha = "abc123456789"
        label = "reset"
        ref = "refs/codexloop/x/1"
        committed = True

    monkeypatch.setattr(
        "codexloop.cli.commands.reset.create_savepoint",
        lambda **kwargs: _Point(),
    )
    result = _invoke("reset")
    assert result.exit_code == 0
    assert "savepoint 1" in result.output

    monkeypatch.setattr(
        "codexloop.cli.commands.snapshot.take_snapshot",
        lambda **kwargs: Path("/tmp/snap"),
    )
    result = _invoke("snapshot", "named")
    assert result.exit_code == 0
    assert "snapshot" in result.output

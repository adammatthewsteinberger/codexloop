"""CLI contract: help/version, prompt flags, exit codes, and bootstrap wiring."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from codexloop.application.dto import RunResult
from codexloop.cli.app import app
from codexloop.domain.control import Stop

COMMANDS = ("run", "resume", "threads", "status", "logs", "runs", "prompt")
_RUNNER = CliRunner()


def _invoke(*args: str) -> object:
    return _RUNNER.invoke(app, list(args))


def test_version_prints_package_version() -> None:
    result = _invoke("--version")
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help_lists_every_command() -> None:
    result = _invoke("--help")
    assert result.exit_code == 0
    for name in COMMANDS:
        assert name in result.output


@pytest.mark.parametrize("name", COMMANDS)
def test_command_help_renders(name: str) -> None:
    result = _invoke(name, "--help")
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert name in result.output


def test_prompt_without_timing_flag_exits_2() -> None:
    result = _invoke("prompt", "hello")
    assert result.exit_code == 2
    assert "--now" in result.output or "--next-turn" in result.output


def test_prompt_with_both_timing_flags_exits_2() -> None:
    result = _invoke("prompt", "hello", "--now", "--next-turn")
    assert result.exit_code == 2
    assert "--now" in result.output or "--next-turn" in result.output


def test_prompt_with_now_exits_0() -> None:
    result = _invoke("prompt", "hello", "--now")
    assert result.exit_code == 0
    assert "queued" in result.output.lower()


def test_prompt_with_next_turn_exits_0() -> None:
    result = _invoke("prompt", "hello", "--next-turn")
    assert result.exit_code == 0
    assert "queued" in result.output.lower()


def test_run_without_plan_exits_2() -> None:
    result = _invoke("run")
    assert result.exit_code == 2
    assert "Missing" in result.output or "PLAN" in result.output.upper()


def _patch_run_plan(monkeypatch: pytest.MonkeyPatch, result: RunResult) -> None:
    async def fake_run_plan(ctx: object, selector: object, plan: str) -> RunResult:
        del ctx, selector, plan
        return result

    monkeypatch.setattr("codexloop.cli.commands.run.run_plan", fake_run_plan)


def test_done_exits_0(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] Add login\n", encoding="utf-8")
    _patch_run_plan(
        monkeypatch,
        RunResult(success=True, reason="done", turns=1, thread_id="thr_1"),
    )
    result = _invoke("run", str(plan))
    assert result.exit_code == 0


def test_failed_exits_1(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] Add login\n", encoding="utf-8")
    _patch_run_plan(
        monkeypatch,
        RunResult(success=False, reason="turns", turns=10, thread_id="thr_1"),
    )
    result = _invoke("run", str(plan))
    assert result.exit_code == 1


def test_soft_stop_exits_130(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] Add login\n", encoding="utf-8")
    _patch_run_plan(
        monkeypatch,
        RunResult(success=False, reason="stop", turns=1, thread_id="thr_1"),
    )
    result = _invoke("run", str(plan))
    assert result.exit_code == 130


def test_sysexit_mapping() -> None:
    from codexloop.cli.asyncio import sysexit_for

    assert sysexit_for(RunResult(True, "done", 1, "t")) == 0
    assert sysexit_for(RunResult(False, "turns", 3, "t")) == 1
    assert sysexit_for(RunResult(False, "stop", 1, "t")) == 130


def test_build_runner_gateway_satisfies_agent_gateway(tmp_path: Path) -> None:
    from codexloop.application.ports import AgentGateway
    from codexloop.bootstrap import RunnerConfig, build_runner

    ctx = build_runner(RunnerConfig(), cwd=tmp_path)
    assert isinstance(ctx.gateway, AgentGateway)


def test_build_runner_app_server_transport_not_implemented(tmp_path: Path) -> None:
    from codexloop.bootstrap import RunnerConfig, build_runner
    from codexloop.domain.errors import ConfigurationError

    with pytest.raises(ConfigurationError, match="not implemented"):
        build_runner(RunnerConfig(), transport="app-server", cwd=tmp_path)


def test_run_help_mentions_transport() -> None:
    result = _invoke("run", "--help")
    assert result.exit_code == 0
    assert "--transport" in result.output


def test_transport_app_server_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] Add login\n", encoding="utf-8")
    result = _invoke("run", "--transport", "app-server", str(plan))
    assert result.exit_code == 2
    assert "not implemented" in result.output.lower()


def test_drain_control_surfaces_stop() -> None:
    from codexloop.bootstrap import DrainControl

    control = DrainControl()
    assert list(control.poll()) == []
    control.request_stop()
    assert list(control.poll()) == [Stop()]
    assert list(control.poll()) == []


def test_threads_status_logs_runs_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name in ("threads", "status", "logs", "runs"):
        result = _invoke(name)
        assert result.exit_code == 0, result.output


def test_resume_without_thread_or_last_exits_2() -> None:
    result = _invoke("resume")
    assert result.exit_code == 2
    assert "thread" in result.output.lower() or "--last" in result.output


def test_resume_with_thread_and_last_exits_2() -> None:
    result = _invoke("resume", "thr_1", "--last")
    assert result.exit_code == 2
    assert "not both" in result.output.lower() or "--last" in result.output


def test_resume_thread_exits_0(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_resume(ctx: object, thread_id: str, plan: str = "") -> RunResult:
        del ctx, plan
        assert thread_id == "thr_1"
        return RunResult(success=True, reason="done", turns=2, thread_id=thread_id)

    monkeypatch.setattr("codexloop.cli.commands.resume.resume_thread", fake_resume)
    result = _invoke("resume", "thr_1")
    assert result.exit_code == 0


def test_resume_last_exits_0(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_run_plan(ctx: object, selector: object, plan: str) -> RunResult:
        del ctx, selector, plan
        return RunResult(success=True, reason="done", turns=1, thread_id="thr_last")

    monkeypatch.setattr("codexloop.cli.commands.resume.run_plan", fake_run_plan)
    result = _invoke("resume", "--last")
    assert result.exit_code == 0


def test_keyboard_interrupt_exits_130(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] Add login\n", encoding="utf-8")

    async def boom(ctx: object, selector: object, plan_text: str) -> RunResult:
        del ctx, selector, plan_text
        raise KeyboardInterrupt

    monkeypatch.setattr("codexloop.cli.commands.run.run_plan", boom)
    result = _invoke("run", str(plan))
    assert result.exit_code == 130


def test_unknown_transport_raises(tmp_path: Path) -> None:
    from codexloop.bootstrap import RunnerConfig, build_runner
    from codexloop.domain.errors import ConfigurationError

    with pytest.raises(ConfigurationError, match="unknown transport"):
        build_runner(RunnerConfig(), transport="pigeon", cwd=tmp_path)


def test_build_runner_sets_drain_and_records_threads(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from codexloop.application.usecases.list_threads import list_threads
    from codexloop.bootstrap import RunnerConfig, build_runner, current_drain
    from codexloop.cli.asyncio import _request_drain
    from codexloop.domain.session import ThreadRef

    ctx = build_runner(RunnerConfig(), cwd=tmp_path)
    drain = current_drain()
    assert drain is not None
    _request_drain()
    assert list(drain.poll()) == [Stop()]
    assert ctx.catalog is not None
    ctx.catalog.record(
        ThreadRef("thr_a", str(tmp_path), datetime(2026, 8, 13, tzinfo=UTC), "gpt-5")
    )
    assert list_threads(ctx)[0].thread_id == "thr_a"
    again = build_runner(RunnerConfig(), cwd=tmp_path, ensure_run=False)
    assert again.catalog is not None
    assert again.catalog.get("thr_a") is not None


def test_status_logs_runs_with_created_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from codexloop.bootstrap import RunnerConfig, build_runner

    monkeypatch.chdir(tmp_path)
    ctx = build_runner(RunnerConfig(), cwd=tmp_path)
    runs = _invoke("runs")
    assert runs.exit_code == 0
    assert ctx.run_id in runs.output
    status = _invoke("status")
    assert status.exit_code == 0
    assert ctx.run_id in status.output
    logs = _invoke("logs")
    assert logs.exit_code == 0
    by_id = _invoke("status", ctx.run_id)
    assert by_id.exit_code == 0
    assert ctx.run_id in by_id.output

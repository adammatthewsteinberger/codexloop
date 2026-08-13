"""CodexExecGateway: exec then resume-by-id, failed turns, idempotent close."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import pytest

from codexloop.application.dto import TurnOutcome
from codexloop.application.ports import AgentGateway, PermissionMode
from codexloop.domain.approval import ApprovalPolicy, SandboxMode
from codexloop.domain.model_profile import Effort, ModelEffortProfile
from codexloop.infrastructure.agent.events import JsonlParser, ThreadStarted
from codexloop.infrastructure.agent.gateway import CodexExecGateway
from codexloop.infrastructure.agent.process import ProcessResult, run_codex

JSONL = Path(__file__).resolve().parents[1] / "fixtures" / "jsonl"
CLEAN_THREAD_ID = "0199a213-81c0-7800-8aa1-bbab2a035a53"
QUOTA_THREAD_ID = "0199a213-81c0-7800-8aa1-bbab2a035a56"


def _env() -> dict[str, str]:
    return os.environ.copy()


class _ArgvSpy:
    def __init__(self) -> None:
        self.argvs: list[list[str]] = []
        self.cwds: list[str] = []

    async def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: str | Path,
        env: Mapping[str, str],
        timeout: float,
        max_line_bytes: int,
    ) -> ProcessResult:
        self.argvs.append(list(argv))
        self.cwds.append(os.fspath(cwd))
        return await run_codex(
            argv, cwd=cwd, env=env, timeout=timeout, max_line_bytes=max_line_bytes
        )


def _gateway(
    tmp_path: Path,
    *,
    run: Callable[..., object] | None = None,
) -> CodexExecGateway:
    return CodexExecGateway(
        cwd=tmp_path,
        env=_env(),
        run_codex=run,
        timeout=15.0,
        max_line_bytes=65_536,
    )


async def test_first_turn_is_exec_second_is_resume_by_captured_id(
    fake_codex_on_path: Path,
    configure_fake_codex: Callable[..., None],
    tmp_path: Path,
) -> None:
    configure_fake_codex(script=JSONL / "clean_completion.jsonl", mode="stream")
    spy = _ArgvSpy()
    gateway = _gateway(tmp_path, run=spy)

    first = await gateway.send_turn("first prompt")
    second = await gateway.send_turn("second prompt")

    assert isinstance(gateway, AgentGateway)
    assert first.signals is not None
    assert first.signals.completed is True
    assert first.exit_code == 0
    assert second.signals is not None
    assert second.exit_code == 0

    assert len(spy.argvs) == 2
    assert spy.argvs[0][:3] == ["codex", "exec", "--json"]
    assert "resume" not in spy.argvs[0]
    assert "--last" not in spy.argvs[0]
    assert spy.argvs[0][-1] == "first prompt"

    assert spy.argvs[1][:4] == ["codex", "exec", "resume", CLEAN_THREAD_ID]
    assert "--last" not in spy.argvs[1]
    assert spy.argvs[1][-1] == "second prompt"

    parser = JsonlParser()
    started = parser.parse_line(
        (JSONL / "clean_completion.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert isinstance(started, ThreadStarted)
    assert started.thread_id == CLEAN_THREAD_ID
    assert spy.argvs[1][3] == started.thread_id


async def test_close_is_idempotent(
    fake_codex_on_path: Path,
    tmp_path: Path,
) -> None:
    gateway = _gateway(tmp_path)
    await gateway.close()
    await gateway.close()


async def test_failed_turn_returns_turn_outcome_rather_than_raising(
    fake_codex_on_path: Path,
    configure_fake_codex: Callable[..., None],
    tmp_path: Path,
) -> None:
    configure_fake_codex(script=JSONL / "turn_failed_429_quota.jsonl", mode="exit_nonzero")
    spy = _ArgvSpy()
    gateway = _gateway(tmp_path, run=spy)

    outcome = await gateway.send_turn("do the thing")

    assert isinstance(outcome, TurnOutcome)
    assert outcome.signals is not None
    assert outcome.signals.failed is True
    assert outcome.signals.error_code == "insufficient_quota"
    assert outcome.exit_code == 2
    assert spy.argvs[0][:3] == ["codex", "exec", "--json"]
    second = await gateway.send_turn("retry")
    assert isinstance(second, TurnOutcome)
    assert spy.argvs[1][:4] == ["codex", "exec", "resume", QUOTA_THREAD_ID]
    assert "--last" not in spy.argvs[1]


async def test_set_profile_appears_on_next_exec_argv(
    fake_codex_on_path: Path,
    configure_fake_codex: Callable[..., None],
    tmp_path: Path,
) -> None:
    configure_fake_codex(script=JSONL / "clean_completion.jsonl", mode="stream")
    spy = _ArgvSpy()
    gateway = _gateway(tmp_path, run=spy)
    await gateway.set_profile(ModelEffortProfile.high("o3"))
    await gateway.send_turn("go")
    argv = spy.argvs[0]
    assert argv[argv.index("--model") + 1] == "o3"
    assert 'model_reasoning_effort="high"' in argv
    assert gateway._opts.model == "o3"
    assert gateway._opts.effort is Effort.HIGH


@pytest.mark.parametrize(
    ("mode", "approval", "sandbox"),
    [
        (PermissionMode.AUTONOMOUS, ApprovalPolicy.NEVER, SandboxMode.WORKSPACE_WRITE),
        (PermissionMode.READ_ONLY, ApprovalPolicy.NEVER, SandboxMode.READ_ONLY),
        (PermissionMode.FULL_ACCESS, ApprovalPolicy.NEVER, SandboxMode.DANGER_FULL_ACCESS),
    ],
)
async def test_set_permission_mode_maps_to_approval_and_sandbox(
    fake_codex_on_path: Path,
    configure_fake_codex: Callable[..., None],
    tmp_path: Path,
    mode: PermissionMode,
    approval: ApprovalPolicy,
    sandbox: SandboxMode,
) -> None:
    configure_fake_codex(script=JSONL / "clean_completion.jsonl", mode="stream")
    spy = _ArgvSpy()
    gateway = _gateway(tmp_path, run=spy)
    await gateway.set_permission_mode(mode)
    await gateway.send_turn("go")
    argv = spy.argvs[0]
    assert f'approval_policy="{approval.value}"' in argv
    assert f'sandbox_mode="{sandbox.value}"' in argv


async def test_set_cwd_is_passed_to_run_codex(
    fake_codex_on_path: Path,
    configure_fake_codex: Callable[..., None],
    tmp_path: Path,
) -> None:
    configure_fake_codex(script=JSONL / "clean_completion.jsonl", mode="stream")
    nested = tmp_path / "nested"
    nested.mkdir()
    spy = _ArgvSpy()
    gateway = _gateway(tmp_path, run=spy)
    await gateway.set_cwd(str(nested))
    await gateway.send_turn("go")
    assert spy.cwds == [str(nested)]


async def test_set_session_resources_add_dirs_and_ignores_invalid(
    fake_codex_on_path: Path,
    configure_fake_codex: Callable[..., None],
    tmp_path: Path,
) -> None:
    configure_fake_codex(script=JSONL / "clean_completion.jsonl", mode="stream")
    spy = _ArgvSpy()
    gateway = _gateway(tmp_path, run=spy)
    await gateway.set_session_resources({"add_dirs": 1})
    await gateway.set_session_resources({"add_dirs": ["ok", 2]})
    await gateway.set_session_resources({"other": ["x"]})
    assert gateway._opts.add_dirs == ()
    await gateway.set_session_resources({"add_dirs": ("/extra-a", "/extra-b")})
    await gateway.send_turn("go")
    argv = spy.argvs[0]
    assert argv.count("--add-dir") == 2
    assert "/extra-a" in argv
    assert "/extra-b" in argv


async def test_close_after_set_is_idempotent_and_keeps_settings(
    fake_codex_on_path: Path,
    configure_fake_codex: Callable[..., None],
    tmp_path: Path,
) -> None:
    configure_fake_codex(script=JSONL / "clean_completion.jsonl", mode="stream")
    spy = _ArgvSpy()
    gateway = _gateway(tmp_path, run=spy)
    await gateway.set_profile(ModelEffortProfile.low("gpt-5"))
    await gateway.set_permission_mode(PermissionMode.READ_ONLY)
    await gateway.close()
    await gateway.close()
    await gateway.send_turn("still works")
    argv = spy.argvs[0]
    assert argv[argv.index("--model") + 1] == "gpt-5"
    assert 'sandbox_mode="read-only"' in argv


def test_resolve_tool_approval_returns_allow_flag(tmp_path: Path) -> None:
    gateway = _gateway(tmp_path)
    assert gateway.resolve_tool_approval("req-1", allow=True, reason="ok") is True
    assert gateway.resolve_tool_approval("req-2", allow=False) is False


async def test_thread_started_without_id_does_not_record_and_stays_on_exec(
    fake_codex_on_path: Path,
    tmp_path: Path,
) -> None:
    async def _run(
        argv: Sequence[str],
        *,
        cwd: str | Path,
        env: Mapping[str, str],
        timeout: float,
        max_line_bytes: int,
    ) -> ProcessResult:
        del argv, cwd, env, timeout, max_line_bytes
        return ProcessResult(
            stdout_lines=[
                '{"type":"turn.started"}',
                '{"type":"thread.started","thread_id":""}',
                '{"type":"thread.started"}',
            ],
            stderr_tail="",
            exit_code=0,
            truncated_lines=0,
        )

    gateway = _gateway(tmp_path, run=_run)
    first = await gateway.send_turn("one")
    second = await gateway.send_turn("two")
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert gateway._thread_id is None

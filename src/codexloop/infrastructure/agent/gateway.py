"""``codex exec --json`` adapter implementing :class:`AgentGateway`."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, assert_never

from codexloop.application.dto import TokenUsage, TurnOutcome
from codexloop.application.ports import PermissionMode
from codexloop.domain.approval import ApprovalPolicy, SandboxMode
from codexloop.domain.model_profile import ModelEffortProfile
from codexloop.infrastructure.agent.argv import ExecOpts, build_exec_argv, build_resume_argv
from codexloop.infrastructure.agent.events import CodexEvent, JsonlParser, ThreadStarted, Usage
from codexloop.infrastructure.agent.process import ProcessResult
from codexloop.infrastructure.agent.process import run_codex as default_run_codex
from codexloop.infrastructure.agent.translate import to_turn_signals

_DEFAULT_TIMEOUT_S = 300.0
_DEFAULT_MAX_LINE_BYTES = 1_048_576


class RunCodex(Protocol):
    async def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: str | Path,
        env: Mapping[str, str],
        timeout: float,
        max_line_bytes: int,
    ) -> ProcessResult: ...


class CodexExecGateway:
    """One-shot ``codex exec`` / ``codex exec resume <thread_id>`` session.

    Records ``thread_id`` from the first ``thread.started`` event and resumes by
    that id thereafter — never ``--last``.
    """

    def __init__(
        self,
        *,
        cwd: str | Path,
        env: Mapping[str, str] | None = None,
        opts: ExecOpts | None = None,
        now: datetime | None = None,
        run_codex: RunCodex | None = None,
        timeout: float = _DEFAULT_TIMEOUT_S,
        max_line_bytes: int = _DEFAULT_MAX_LINE_BYTES,
    ) -> None:
        self._cwd = Path(cwd)
        self._env = dict(env) if env is not None else None
        self._opts = opts if opts is not None else ExecOpts(prompt="")
        self._now = now
        self._run_codex = run_codex if run_codex is not None else default_run_codex
        self._timeout = timeout
        self._max_line_bytes = max_line_bytes
        self._thread_id: str | None = None
        self._closed = False

    async def send_turn(self, prompt: str) -> TurnOutcome:
        opts = replace(self._opts, prompt=prompt)
        if self._thread_id is None:
            argv = build_exec_argv(opts)
        else:
            argv = build_resume_argv(self._thread_id, opts)
        env = self._env if self._env is not None else os.environ.copy()
        result = await self._run_codex(
            argv,
            cwd=self._cwd,
            env=env,
            timeout=self._timeout,
            max_line_bytes=self._max_line_bytes,
        )
        events = self._parse_lines(result.stdout_lines)
        self._record_thread_id(events)
        signals = to_turn_signals(
            events,
            exit_code=result.exit_code,
            stderr_tail=result.stderr_tail,
            now=self._now if self._now is not None else datetime.now(UTC),
        )
        return TurnOutcome(
            signals=signals,
            usage=_token_usage(signals.usage),
            exit_code=result.exit_code,
        )

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True

    async def set_profile(self, profile: ModelEffortProfile) -> None:
        self._opts = replace(self._opts, model=profile.model, effort=profile.effort)

    async def set_permission_mode(self, mode: PermissionMode) -> None:
        match mode:
            case PermissionMode.AUTONOMOUS:
                approval, sandbox = ApprovalPolicy.NEVER, SandboxMode.WORKSPACE_WRITE
            case PermissionMode.READ_ONLY:
                approval, sandbox = ApprovalPolicy.NEVER, SandboxMode.READ_ONLY
            case PermissionMode.FULL_ACCESS:
                approval, sandbox = ApprovalPolicy.NEVER, SandboxMode.DANGER_FULL_ACCESS
            case _:
                assert_never(mode)
        self._opts = replace(self._opts, approval=approval, sandbox=sandbox)

    async def set_cwd(self, path: str) -> None:
        self._cwd = Path(path)

    async def set_session_resources(self, resources: Mapping[str, object]) -> None:
        add_dirs = resources.get("add_dirs")
        if isinstance(add_dirs, list | tuple) and all(isinstance(item, str) for item in add_dirs):
            self._opts = replace(self._opts, add_dirs=tuple(add_dirs))

    def resolve_tool_approval(self, request_id: str, *, allow: bool, reason: str = "") -> bool:
        _ = request_id, reason
        return allow

    def _parse_lines(self, lines: Sequence[str]) -> list[CodexEvent | None]:
        parser = JsonlParser(now=self._now if self._now is not None else datetime.now(UTC))
        return [parser.parse_line(line) for line in lines]

    def _record_thread_id(self, events: Sequence[CodexEvent | None]) -> None:
        if self._thread_id is not None:
            return
        for event in events:
            if isinstance(event, ThreadStarted) and event.thread_id:
                self._thread_id = event.thread_id
                return


def _token_usage(usage: object | None) -> TokenUsage | None:
    if not isinstance(usage, Usage):
        return None
    return TokenUsage(
        input_tokens=usage.input_tokens or 0,
        cached_input_tokens=usage.cached_input_tokens or 0,
        output_tokens=usage.output_tokens or 0,
        reasoning_output_tokens=usage.reasoning_output_tokens or 0,
    )

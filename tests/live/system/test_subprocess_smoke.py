"""Thin subprocess smoke: real ``codexloop`` CLI + env-gated scripted agent."""

from __future__ import annotations

import os
import subprocess  # nosec B404 — fixed argv lists only
import sys
import threading
import time
from pathlib import Path

import pytest

from codexloop.infrastructure.agent.scripted import (
    ALLOW_TEST_AGENT_ENV,
    TEST_AGENT_SCRIPT_ENV,
)

pytestmark = pytest.mark.system

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "agent_scripts"
_DONE = _FIXTURES / "done.json"
_WAIT = _FIXTURES / "wait_long.json"
_OPS = (
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


def _env_with_script(script: Path) -> dict[str, str]:
    env = os.environ.copy()
    env[ALLOW_TEST_AGENT_ENV] = "1"
    env[TEST_AGENT_SCRIPT_ENV] = str(script)
    src = str(Path(__file__).resolve().parents[3] / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def _codexloop_bin() -> str:
    candidate = Path(sys.executable).parent / "codexloop"
    if candidate.is_file():
        return str(candidate)
    return "codexloop"


def _codexloop(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float = 60,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603
        [_codexloop_bin(), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_help_lists_ops_commands() -> None:
    result = _codexloop(["--help"], cwd=Path.cwd(), env=os.environ.copy())
    assert result.returncode == 0
    for cmd in _OPS:
        assert cmd in result.stdout


def test_script_without_allow_flag_is_hard_error(tmp_path: Path, git_sandbox: Path) -> None:
    del tmp_path
    plan = git_sandbox / "plan.md"
    plan.write_text("- [ ] x\n", encoding="utf-8")
    env = os.environ.copy()
    env.pop(ALLOW_TEST_AGENT_ENV, None)
    env[TEST_AGENT_SCRIPT_ENV] = str(_DONE)
    src = str(Path(__file__).resolve().parents[3] / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    result = _codexloop(["run", str(plan)], cwd=git_sandbox, env=env, timeout=15)
    assert result.returncode != 0
    combined = f"{result.stdout}\n{result.stderr}"
    assert ALLOW_TEST_AGENT_ENV in combined or "test-only" in combined.lower()


def test_subprocess_done_exits_0(git_sandbox: Path) -> None:
    plan = git_sandbox / "plan.md"
    plan.write_text("- [ ] x\n", encoding="utf-8")
    result = _codexloop(
        ["run", str(plan)],
        cwd=git_sandbox,
        env=_env_with_script(_DONE),
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_subprocess_stop_mid_wait_exits_130(git_sandbox: Path) -> None:
    plan = git_sandbox / "plan.md"
    plan.write_text("- [ ] x\n", encoding="utf-8")
    env = _env_with_script(_WAIT)
    proc = subprocess.Popen(  # nosec B603
        [_codexloop_bin(), "run", str(plan)],
        cwd=git_sandbox,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    def _stop_later() -> None:
        time.sleep(0.15)
        stop = _codexloop(["stop"], cwd=git_sandbox, env=env, timeout=10)
        assert stop.returncode == 0, stop.stdout + stop.stderr

    stopper = threading.Thread(target=_stop_later)
    stopper.start()
    try:
        stdout, stderr = proc.communicate(timeout=30)
    finally:
        stopper.join(timeout=5)
    assert proc.returncode == 130, stdout + stderr

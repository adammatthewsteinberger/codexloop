"""Doctor environment unit tests with injectable subprocess fakes."""

from __future__ import annotations

import subprocess
from pathlib import Path

from codexloop.infrastructure.doctor_env import CodexDoctorEnvironment


class _Proc:
    def __init__(self, code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.returncode = code
        self.stdout = stdout
        self.stderr = stderr


def test_doctor_reports_auth_mode_and_probe_strategies(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def which(name: str) -> str | None:
        return "/bin/codex" if name == "codex" else None

    def run(argv: list[str], *, timeout: float = 10) -> _Proc:
        del timeout
        calls.append(list(argv))
        if argv[1:] == ["--version"]:
            return _Proc(0, "codex-cli 0.50.0")
        if argv[1:] == ["login", "status"]:
            return _Proc(0, "logged in")
        if argv[1:] == ["exec", "--help"]:
            return _Proc(0, "Usage: --json --ephemeral -c key=value")
        return _Proc(1, "")

    env = CodexDoctorEnvironment(
        environ={"OPENAI_API_KEY": "sk-test"},
        which=which,
        run=run,  # type: ignore[arg-type]
        home=tmp_path,
        minimum_version=(0, 40, 0),
        app_server_live=lambda: False,
        rollout_live=lambda: True,
        mcp_servers=lambda: ("needs-oauth",),
    )
    (tmp_path / ".git").mkdir()
    report = env.diagnose(cwd=tmp_path)

    assert report.auth_mode == "api_key"
    assert report.probe_strategies == {
        "exec": True,
        "app-server": False,
        "rollout": True,
    }
    by_name = {c.name: c for c in report.checks}
    assert by_name["codex-cli"].passed is True
    assert by_name["login-status"].passed is True
    assert by_name["exec-flags"].passed is True
    assert by_name["mcp-oauth"].passed is False
    assert "needs-oauth" in by_name["mcp-oauth"].detail
    assert report.all_passed is False
    assert any(c[:2] == ["/bin/codex", "--version"] for c in calls)


def test_doctor_fails_when_codex_missing(tmp_path: Path) -> None:
    env = CodexDoctorEnvironment(
        environ={},
        which=lambda _name: None,
        run=lambda *_a, **_k: (_ for _ in ()).throw(subprocess.TimeoutExpired("x", 1)),
        home=tmp_path,
        mcp_servers=lambda: (),
    )
    report = env.diagnose(cwd=tmp_path)
    assert report.auth_mode == "none"
    assert any(c.name == "codex-cli" and not c.passed for c in report.checks)

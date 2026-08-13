"""Config precedence: flags > env > project toml > user toml > defaults."""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

from codexloop.infrastructure.config import RunnerConfig, load_config
from codexloop.infrastructure.notify import CommandNotifier

_USER_TOML = """\
model = "user-model"
max_turns = 10
json_logs = true
max_wait = "1h"
add_dirs = ["user-dir"]
"""

_PROJECT_TOML = """\
model = "project-model"
max_turns = 20
json_logs = false
max_wait = "2h"
add_dirs = ["project-dir"]
"""


def _write_configs(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "home"
    cwd = tmp_path / "cwd"
    (home / ".config" / "codexloop").mkdir(parents=True)
    (home / ".config" / "codexloop" / "codexloop.toml").write_text(_USER_TOML, encoding="utf-8")
    cwd.mkdir()
    (cwd / "codexloop.toml").write_text(_PROJECT_TOML, encoding="utf-8")
    return home, cwd


def test_defaults_when_nothing_is_set(tmp_path: Path) -> None:
    config = load_config(cwd=tmp_path, home=tmp_path, environ={})
    assert config == RunnerConfig()
    assert config.model == "gpt-5"
    assert config.max_turns == 100
    assert config.json_logs is False
    assert config.max_wait == timedelta(hours=24)
    assert config.add_dirs == ()


def test_user_toml_overrides_defaults(tmp_path: Path) -> None:
    home, cwd = _write_configs(tmp_path)
    (cwd / "codexloop.toml").unlink()
    config = load_config(cwd=cwd, home=home, environ={})
    assert config.model == "user-model"
    assert config.max_turns == 10
    assert config.json_logs is True
    assert config.max_wait == timedelta(hours=1)
    assert config.add_dirs == ("user-dir",)


def test_project_toml_overrides_user_toml(tmp_path: Path) -> None:
    home, cwd = _write_configs(tmp_path)
    config = load_config(cwd=cwd, home=home, environ={})
    assert config.model == "project-model"
    assert config.max_turns == 20
    assert config.json_logs is False
    assert config.max_wait == timedelta(hours=2)
    assert config.add_dirs == ("project-dir",)


def test_env_overrides_project_toml(tmp_path: Path) -> None:
    home, cwd = _write_configs(tmp_path)
    environ = {
        "CODEXLOOP_MODEL": "env-model",
        "CODEXLOOP_MAX_TURNS": "30",
        "CODEXLOOP_JSON_LOGS": "true",
        "CODEXLOOP_MAX_WAIT": "3h",
        "CODEXLOOP_ADD_DIRS": "env-a,env-b",
    }
    config = load_config(cwd=cwd, home=home, environ=environ)
    assert config.model == "env-model"
    assert config.max_turns == 30
    assert config.json_logs is True
    assert config.max_wait == timedelta(hours=3)
    assert config.add_dirs == ("env-a", "env-b")


def test_flags_override_env_and_files(tmp_path: Path) -> None:
    home, cwd = _write_configs(tmp_path)
    environ = {
        "CODEXLOOP_MODEL": "env-model",
        "CODEXLOOP_MAX_TURNS": "30",
        "CODEXLOOP_JSON_LOGS": "true",
        "CODEXLOOP_MAX_WAIT": "3h",
        "CODEXLOOP_ADD_DIRS": "env-a,env-b",
    }
    config = load_config(
        cwd=cwd,
        home=home,
        environ=environ,
        flags={
            "model": "flag-model",
            "max_turns": 40,
            "json_logs": False,
            "max_wait": timedelta(hours=4),
            "add_dirs": ["flag-dir"],
        },
    )
    assert config.model == "flag-model"
    assert config.max_turns == 40
    assert config.json_logs is False
    assert config.max_wait == timedelta(hours=4)
    assert config.add_dirs == ("flag-dir",)


def test_flag_none_values_are_ignored(tmp_path: Path) -> None:
    home, cwd = _write_configs(tmp_path)
    config = load_config(cwd=cwd, home=home, environ={}, flags={"model": None, "max_turns": None})
    assert config.model == "project-model"
    assert config.max_turns == 20


def test_unknown_toml_keys_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "codexloop.toml").write_text('not_a_field = "x"\nmax_turns = 7\n', encoding="utf-8")
    config = load_config(cwd=tmp_path, home=tmp_path, environ={})
    assert config.max_turns == 7


def test_command_notifier_records_noop_when_unset() -> None:
    notifier = CommandNotifier(None)
    notifier.notify("title", "body")
    assert notifier.noop_notifications == [("title", "body")]


def test_command_notifier_runs_configured_command(tmp_path: Path) -> None:
    marker = tmp_path / "notified.txt"
    script = tmp_path / "notify.py"
    script.write_text(
        "import sys\nfrom pathlib import Path\n"
        "Path(sys.argv[1]).write_text(f'{sys.argv[2]} {sys.argv[3]}')\n",
        encoding="utf-8",
    )
    notifier = CommandNotifier([sys.executable, str(script), str(marker)])
    notifier.notify("Hello", "World")
    assert marker.read_text(encoding="utf-8") == "Hello World"

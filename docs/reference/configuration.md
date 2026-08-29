# Configuration reference

`codexloop` reads runtime settings from four places, in this precedence
order (highest wins):

```
CLI flags  >  CODEXLOOP_* environment variables  >  ./codexloop.toml
           >  ~/.config/codexloop/codexloop.toml  >  built-in defaults
```

Every field below can be set via a TOML file **or** its environment
variable. A CLI flag, where one exists, always overrides both — see the
[CLI reference](cli.md) for the per-command flags (`--model`,
`--max-turns`, `--max-wait`, `--network-access`, `--log-level`,
`--log-file`, and the root `-v`/`-q` verbosity ladder).

## `codexloop.toml`

Two files are read and merged, project overriding user:

- `~/.config/codexloop/codexloop.toml` — user-wide defaults.
- `./codexloop.toml` — project-local overrides, read from the current
  working directory.

Only top-level keys matching a known setting are read; anything else in the
file is ignored. Example:

```toml
model = "gpt-5-codex"
max_turns = 200
max_wait = "6h"
network_access = false
add_dirs = ["../shared-lib", "../fixtures"]
log_level = "DEBUG"
notify_command = "terminal-notifier -title codexloop -message"
```

## Environment variables

Every setting is also readable as `CODEXLOOP_<FIELD>` (uppercased). All
env values arrive as strings and are coerced the same way a TOML scalar
would be.

| Variable | TOML key | Type | Default | Effect |
|---|---|---|---|---|
| `CODEXLOOP_MODEL` | `model` | string | none | Overrides the Codex model. Unset leaves model selection to the `codex` CLI's own default. |
| `CODEXLOOP_MAX_TURNS` | `max_turns` | int | `100` | Turn budget for a run before it stops on its own. |
| `CODEXLOOP_JSON_LOGS` | `json_logs` | bool | `false` | Emit structured JSON log lines instead of human-readable text. Accepts `1`/`true`/`yes`/`on` and `0`/`false`/`no`/`off` (case-insensitive). |
| `CODEXLOOP_MAX_WAIT` | `max_wait` | duration | `24h` | Longest a run will probe a capacity window before giving up. Accepts a bare number of seconds (`"3600"`) or a `1d2h3m4s`-style duration string — any subset of those four units, in that order. |
| `CODEXLOOP_ADD_DIRS` | `add_dirs` | list of strings | `()` (empty) | Extra directories granted to the Codex sandbox beyond the workspace root, passed through as one `--add-dir <path>` per entry. As an env var, a comma-separated string (`"../a,../b"`); as TOML, a native array. |
| `CODEXLOOP_NETWORK_ACCESS` | `network_access` | bool | `false` | Allows outbound command network access inside the `workspace-write` sandbox. Not a localhost-only allowlist — see the network-access warning in [README.md](https://github.com/adammatthewsteinberger/codexloop/blob/develop/README.md#quickstart). |
| `CODEXLOOP_LOG_LEVEL` | `log_level` | string | `"INFO"` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. Overridden by the root `-v`/`-q`/`--log-level` CLI flags when given. |
| `CODEXLOOP_LOG_FILE` | `log_file` | string or unset | none | Also write redacted JSON log lines to this path. |
| `CODEXLOOP_NOTIFY_COMMAND` | `notify_command` | string or unset | none | A shell-parsed command run as `<command> <title> <body>` (no shell, `shlex.split` then `subprocess.run` with an argv list) whenever the runner has a notification to raise — currently, quota exhaustion. Titles and bodies are redacted the same way logs are before they reach the command. Unset: notifications are recorded internally and otherwise silent. |

### Test-harness-only variables

`CODEXLOOP_ALLOW_TEST_AGENT` and `CODEXLOOP_TEST_AGENT_SCRIPT` activate a
JSON-scripted fake agent used by the system test harness (`pytest -m
system`). They are **not** part of the configuration surface above — no
`RunnerConfig` field backs them — and must never be set on an operator
machine running real work. See the callout in
[SECURITY.md](https://github.com/adammatthewsteinberger/codexloop/blob/develop/SECURITY.md).

## Precedence example

Given `~/.config/codexloop/codexloop.toml` with `max_turns = 50`, a project
`./codexloop.toml` with `max_turns = 80`, `CODEXLOOP_MAX_TURNS=120` in the
environment, and `codexloop run plan.md --max-turns 20` on the command
line, the effective value is **`20`** — the flag wins. Drop the flag and
the effective value is `120` (env beats both TOML files); drop the env var
too and it's `80` (project TOML beats user TOML).

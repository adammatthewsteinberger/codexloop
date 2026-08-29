# CLI reference

```bash
codexloop --help
```

Every command below also accepts these root-level options (declared in
`codexloop`'s top-level callback, so they must come *before* the
subcommand, e.g. `codexloop -v run plan.md`):

| Flag | Default | Meaning |
|---|---|---|
| `--version` | — | Print the installed `codexloop` version and exit. |
| `--verbose`, `-v` (repeatable) | `0` | More detail: `-v` debug, `-vv` also third-party libraries, `-vvv` full payloads. |
| `--quiet`, `-q` | `False` | Warnings and errors only. |
| `--log-level` | none | `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. Overrides `-v`. |
| `--log-file` | none | Also write redacted JSON lines to this file. |

Passing conflicting verbosity flags (e.g. `--quiet` with `--log-level`) exits
with an error and code `2`.

Every flag above, and several settings with no CLI flag at all
(`add_dirs`, `json_logs`, `notify_command`), can also be set via
`codexloop.toml` or a `CODEXLOOP_*` environment variable — see the
[Configuration reference](configuration.md) for the full list, file
locations, and precedence order.

Commands that queue a control change (`prompt`, `stop`, `wind-down`, `model`,
`effort`, `approval`, `sandbox`, `cwd`) all write into the target run's
control inbox and are picked up at that run's next control boundary — they
do not act immediately.

## Starting and resuming runs

### `run`

```bash
codexloop run <plan> [--run-id ID] [--transport exec|app-server] \
  [--model NAME] [--max-turns N] [--max-wait DURATION] \
  [--network-access / --no-network-access] [--stream-ui]
```

Drives a brand-new autonomous Codex session from a markdown work plan.

| Argument / Option | Default | Meaning |
|---|---|---|
| `plan` (argument, required) | — | Path to a markdown work plan. Must exist and be readable. |
| `--run-id` | generated | Name this run instead of generating an id, so a supervisor can attach mid-run. |
| `--transport` | `exec` | Agent transport: `exec` or `app-server`. |
| `--model` | none | Model name override. |
| `--max-turns` | none | Turn budget. |
| `--max-wait` | none | Max wait duration before giving up on a capacity window. |
| `--network-access` / `--no-network-access` | unset | Allow outbound command network access inside the `workspace-write` sandbox. Not limited to localhost — use only for trusted tasks. |
| `--stream-ui` | `False` | Open the Textual live view of the run's event log after it completes. |

Prints the rendered run outcome. Exits `2` with the error message if
`build_runner` rejects the flag combination (e.g. an invalid `--transport`).
Creates run state, logs, and control-inbox artifacts under
`.codexloop/runs/<run_id>/`.

### `resume`

```bash
codexloop resume <thread_id> [--transport exec|app-server]
codexloop resume --last [--transport exec|app-server]
```

Resumes an existing thread — either an explicit `thread_id` or, with
`--last`, the most recently used thread. Exactly one selection mode must be
given: exits `2` with `Specify a thread id or --last.` if neither is
supplied, and `2` with `Specify a thread id or --last, not both.` if both
are.

| Argument / Option | Default | Meaning |
|---|---|---|
| `thread_id` (argument, optional) | none | Thread id to resume. |
| `--last` | `False` | Resume the most recent thread. |
| `--transport` | `exec` | Agent transport: `exec` or `app-server`. |

### `threads`

```bash
codexloop threads
```

Lists **this product's run registry** — not vendor Codex sessions. Read-only;
no run directory is created for the listing itself.

## Watching and inspecting a run

### `status`

```bash
codexloop status [run_id]
```

Prints the persisted state for `run_id`, or the latest run if omitted.

### `logs`

```bash
codexloop logs [run_id]
```

Prints the `events.jsonl` event stream for `run_id`, or the latest run if
omitted.

### `runs`

```bash
codexloop runs
```

Lists every run directory under `.codexloop/runs/`.

### `watch`

```bash
codexloop watch [run_id] [--replay] [--follow | -f] [--interval SECONDS]
```

| Argument / Option | Default | Meaning |
|---|---|---|
| `run_id` (argument, optional) | latest | Run id to watch. |
| `--replay` | `False` | Open the Textual stream UI against the run's event log, instead of printing a state snapshot. |
| `--follow`, `-f` | `False` | Keep printing state whenever it changes, until the run exits. |
| `--interval` | `1.0` (min `0.1`) | Poll interval in seconds when `--follow` is set. |

Without any flags, prints one pretty-printed JSON state snapshot and exits
`1` with `no run state` if the run has never produced one. `--follow` polls
until the run is no longer live; it also exits `1` with `no run state` if it
never observes any state at all. `--replay` opens a blocking interactive
Textual TUI.

### `capacity`

```bash
codexloop capacity
```

Prints ChatGPT plan-window / rate-limit usage: `plan_type`, `limit_reached`,
and, for each of the `primary`/`secondary` windows, `used=<pct>% window=<min>m
resets_at=<iso timestamp|unknown>` — or `unavailable` for a window that isn't
tracked. Prints `plan windows unavailable` rather than guessing when nothing
is known yet.

### `doctor`

```bash
codexloop doctor [--cwd PATH]
```

Runs pre-flight environment checks: reports the detected `auth_mode`, the
availability of each probe strategy (`name=live` or `name=unavailable`), and
a list of named checks each marked `[ok]` or `[FAIL]` with detail. Exits `1`
if any check failed.

| Option | Default | Meaning |
|---|---|---|
| `--cwd` | current directory | Working directory to check. |

The checks, in the order they run:

| Check | Fails when | What a failure means |
|---|---|---|
| `codex-cli` | `codex` isn't on `PATH`, or its `--version` is below the minimum supported version | Install or upgrade the [Codex CLI](https://github.com/openai/codex). |
| `login-status` | `codex` is on `PATH` but `codex login status` exits non-zero | Run `codex login`, or set `OPENAI_API_KEY` / `CODEX_API_KEY` for API-key mode instead. |
| `exec-flags` | `codex exec --help` is missing one of the flags `codexloop` depends on (`--json`, `--ephemeral`, `-c`) | The installed `codex` build is too old or was built without these flags; upgrade it. |
| `auth-mode` | neither `OPENAI_API_KEY`/`CODEX_API_KEY` is set nor `~/.codex/auth.json` exists | No credentials are configured at all — pick API-key mode or `codex login`, never both. |
| `probe-strategies` | never fails on its own (`passed` is always `true`) | Informational: which capacity-probe strategies (`exec`, `app-server`, `rollout`) are currently live vs. unavailable. |
| `mcp-oauth` | one or more configured MCP servers require OAuth authorization that hasn't been completed | Authorize each named MCP server before starting an unattended run — an unattended run cannot complete an interactive OAuth flow if one is triggered mid-run. Passes trivially (with "no MCP OAuth servers named") when no MCP servers are configured. |
| `working-directory` | `--cwd` (or the current directory) is not inside a git repository | `codexloop` expects a git repository for save points and `unwind`; `cd` into one or run `git init`. |

## Mid-run control

These all target a run by `--run-id` (default: the current/most recent live
run) and queue a change for that run's next control boundary. Each exits `2`
on a `ConfigurationError` (e.g. no resolvable run) and otherwise prints
`queued → <path>`.

### `prompt`

```bash
codexloop prompt "<text>" (--now | --next-turn) [--run-id ID]
```

Queues operator input into the run. Exactly one of `--now` (apply at the
next control poll) or `--next-turn` (apply before the next turn) is
required — exits `2` with `Specify exactly one of --now or --next-turn.`
otherwise.

### `stop`

```bash
codexloop stop [--run-id ID]
```

Requests a graceful stop at the next control boundary.

### `wind-down`

```bash
codexloop wind-down [--run-id ID] [--reason TEXT]
```

Requests a graceful wind-down: the run finishes its current turn, writes a
handoff marker naming every artifact it produced, and **exits with code
75** — distinguishing "hand this run off elsewhere" from a plain failure or
an operator hard-stop. `--reason` defaults to `"operator request"`.

### `model`

```bash
codexloop model <model> [--run-id ID]
```

Queues a model change for the next control boundary.

### `effort`

```bash
codexloop effort <low|medium|high> [--run-id ID]
```

Queues an effort-level change. `effort` must be one of `low`, `medium`,
`high` (Codex `model_reasoning_effort`) — any other value exits `2`.

### `approval`

```bash
codexloop approval <never|on-request|on-failure|untrusted> [--run-id ID]
```

Queues an approval-policy change. Any value outside that set exits `2`.

### `sandbox`

```bash
codexloop sandbox <read-only|workspace-write|danger-full-access> [--run-id ID]
```

Queues a sandbox-mode change. Any value outside that set exits `2`.

### `cwd`

```bash
codexloop cwd <path> [--run-id ID]
```

Queues a working-directory change for the run.

## Save points and snapshots

### `savepoints`

```bash
codexloop savepoints [--run-id ID]
```

Lists numbered git save points for the run: `n`, short sha, `commit` or
`ref-only` kind, `label`, and `ref`. Prints `no savepoints` if there are
none.

### `reset`

```bash
codexloop reset [--run-id ID] [--label TEXT]
```

Records a savepoint of the current working tree — a commit if the tree is
dirty, or a ref-only tag if it's clean (`--label` defaults to `"reset"`).
Exits `1` with `not a git repository — no savepoint created` outside a git
repo.

### `unwind`

```bash
codexloop unwind <to> [--run-id ID] [--backup / --no-backup]
```

Hard-resets the worktree to a save point, identified by number, sha prefix,
or label (`--backup` defaults to `True`, keeping a backup ref). **Refuses
while the target run is live** — exits `2` with `unwind refuses while a run
is live` in that case, and also on an unresolvable `to` reference. This is a
destructive operation on the worktree.

### `snapshot`

```bash
codexloop snapshot [name] [--run-id ID] [--restore NAME]
```

Creates or restores a filesystem snapshot of the workspace (everything
except `.codexloop/`) for the run. Without `--restore`, creates a new
snapshot named `name` (default: a UTC timestamp, `YYYYMMDDTHHMMSSZ`).
`--restore NAME` restores that named snapshot instead. Exits `2` on a
missing run or missing snapshot.

## Generated REST surface

### `api`

```bash
codexloop api [--provider openai|azure|custom] [--base-url URL] <resource> <method> [flags]
```

`codexloop api` is a code-generated command tree — not hand-maintained —
mirroring the installed `openai` Python SDK's method surface one-to-one.
`chat.completions.create` on the SDK becomes `codexloop api chat completions
create`, and every leaf command gets both the SDK method's own parameters
and universal `--json`, `--json-file`, `--raw`, `--stream`, and
`--max-items` flags.

- `--provider` (default `openai`) selects which backend the request targets
  (`openai`, `azure`, or a `custom` OpenAI-compatible endpoint); an unknown
  value exits `2`.
- `--base-url` overrides the API base URL for the selected provider.
- Leaf commands exit `2` and print the error to stderr on any `ValueError`,
  `TypeError`, or `OSError` from the underlying call; otherwise they print
  the rendered response.

The generated surface is checked against `api_baseline.json`, a frozen
snapshot of the SDK's method count, method list, and local helpers. An SDK
upgrade that silently adds, removes, or renames methods fails this drift
check rather than shipping unnoticed — see the
[REST API surface guide](../guides/rest-api-surface.md) for how to refresh
the baseline deliberately.

```bash
codexloop api --help
codexloop api chat completions --help
```

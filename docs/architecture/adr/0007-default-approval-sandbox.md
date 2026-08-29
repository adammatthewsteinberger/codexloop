# ADR 0007 — Default never + workspace-write

## Status

Accepted

## Context

Codex's `approval_policy=never` disables all approval prompts and works with
*all* sandbox modes — the two settings are orthogonal. That is strictly
better than claudeloop's position, where autonomy required Claude Code's
`bypassPermissions`, a single setting that also dropped filesystem
confinement.

## Decision

The default is `approval_policy=never` **plus** `sandbox_mode=workspace-write`
— fully autonomous *and* confined to the workspace, applied via `-c` on every
`codex exec` invocation (see [ADR 0008](0008-policy-via-c-flags.md)).
`danger-full-access` remains reachable only behind an explicit, loudly-audited
opt-in that refuses to run as root and refuses outside a git repository or an
allowlisted directory — the container/VM case the vendor docs themselves
carve out. The supported way to widen scope for a task that needs extra
directories is `--add-folder` (the CLI's `--add-dir`), never a drop to full
access.

## Consequences

A normal run never needs to escalate past `workspace-write`, so the escalation
path simply does not arise on the golden path. When `danger-full-access` is
used deliberately, it emits a `WARNING`-level audit record naming the risk.
Risk if the defaults were ever to slip toward full-access is medium — a
sandbox escape becomes real — which is why the opt-in is loud rather than a
quiet flag.

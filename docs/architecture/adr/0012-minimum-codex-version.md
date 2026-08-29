# ADR 0012 — Minimum-supported `codex` version via doctor

## Status

Accepted

## Context

The Codex CLI moves fast: flags are added, deprecated, and removed within
months — `--full-auto` was deprecated and later removed, and scripts that
still pass it now error outright. Version drift is treated as a first-class
design constraint rather than an operational annoyance, because codexloop
depends on a specific set of documented flags (`--json`,
`--output-last-message`, `--output-schema`, `--ephemeral`, `-c`, `--model`,
`--add-dir`, `--skip-git-repo-check`) staying present and working the same
way.

## Decision

`codexloop doctor` asserts a pinned minimum `codex` version and runs the real
binary's `--help` to assert every depended-on flag actually exists, converting
a mid-run surprise into a pre-run failure. `codex --version` is recorded into
every audit log so a regression can be correlated with a specific CLI release
after the fact.

## Consequences

Versions above a known-good ceiling warn rather than hard-fail, since a newer
CLI is more likely to still work than an older, unpinned one. Risk is
medium — the CLI's pace of change means the pinned minimum and the flag list
both need ongoing maintenance — but the failure mode is a clean, actionable
`doctor` error before a run starts rather than a confusing mid-run crash.

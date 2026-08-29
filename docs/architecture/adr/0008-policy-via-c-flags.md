# ADR 0008 — All policy via `-c key=value`

## Status

Accepted

## Context

A reported production break drove this decision: `codex exec resume` does not
accept a bare `--sandbox` flag, only `codex exec` does. Building argv strings
per call site risks the class of bug where turn 1 is sandboxed correctly and
turn 2 silently runs unsandboxed, because the flag that worked on the first
invocation is silently rejected or ignored on the resume path.

## Decision

`infrastructure/agent/argv.py` is the **only** module that constructs a
`codex` command line. Every policy setting — approval policy, sandbox mode,
added directories — is expressed as `-c key=value`, which both `codex exec`
and `codex exec resume` accept identically. Never a bare `--sandbox` flag,
never `--full-auto` (deprecated, then removed from the CLI).

## Consequences

Three table-driven tests hold the line: the resume argv never contains a bare
`--sandbox`; no argv ever contains `--full-auto`; no argv ever invokes the
interactive TUI (i.e. `exec` or `app-server` is always present as the
subcommand). Risk if this were violated is medium — it is the exact bug class
reported in the wild — but a single code path makes the whole class of bug
structurally unreachable rather than merely tested against.

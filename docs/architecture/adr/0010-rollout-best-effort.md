# ADR 0010 — Rollout-file parsing is best-effort

## Status

Accepted

## Context

Codex persists per-session rollout JSONL under `$CODEX_HOME`, which carries
useful `token_count.rate_limits` events — but it is a private on-disk format
the vendor does not document as an API. This mirrors the claudeloop lesson
that globbing `~/.claude/projects/` was the single most fragile thing in that
project's legacy script.

## Decision

`infrastructure/rollout.py::read_rollout_rate_limits` tails the newest rollout
file as Strategy C — the last-resort enrichment layer of the capacity probe
(see [ADR 0005](0005-layered-capacity-probe.md)). It is read-only telemetry
only: never treated as session state, never the source of truth for
completion, and never a required input to a capacity decision. It is skipped
entirely, without error, when unavailable or stale.

## Consequences

When it does yield a `resets_at`, it converts a bounded probe loop into a
precisely scheduled wake-up; when it is absent (as it reportedly is in
exec-only sessions) the exec floor alone still produces a correct decision.
Risk is low — its blast radius is bounded by construction, since nothing
downstream treats it as authoritative.

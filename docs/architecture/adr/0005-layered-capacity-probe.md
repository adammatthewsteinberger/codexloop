# ADR 0005 — Layered capacity probe with exec floor

## Status

Accepted

## Context

The richest capacity signal — the `x-codex-*` headers Codex parses into a
`RateLimitSnapshot` with a 5-hour primary and weekly secondary window — is
exactly the one that cannot be counted on: under `codex exec` the payload is
reportedly always `null`, because the API does not return those headers for
non-interactive requests. A capacity decision must therefore never depend on
a confidence-C signal alone, and every classification path must terminate in
a defensible answer even if every optional telemetry source returns nothing.

## Decision

`infrastructure/capacity_probe.py::CompositeCapacityProbe` implements the
`CapacityProbe` port as three strategies in a strict preference order with a
guaranteed-available floor:

1. **App-server `account/rateLimits/read`** (Strategy B, preferred
   enrichment) — returns the window snapshot without spending a turn, behind
   a startup capability probe, never on the critical path.
2. **Rollout tail** (Strategy C, last resort) — tails the newest rollout
   JSONL under `$CODEX_HOME` for `token_count.rate_limits`; cheapest and most
   fragile, a private on-disk format that may be stale or absent.
3. **Exec probe** (Strategy A, the floor) — a minimal `--ephemeral
   --sandbox_mode=read-only` invocation that always runs and is always
   authoritative for the `outcome` (can we work right now?), regardless of
   whether B or C produced a `snapshot` (when will we be able to?).

`outcome` is always present; `snapshot` is always optional. B and C can each
be disabled independently by flag or env, and `codexloop doctor` reports
which strategies are live on the current machine.

## Consequences

The exec floor guarantees a correct capacity decision even with both
enrichment strategies disabled, erroring, or returning garbage — covered by a
probe-degradation contract test. Risk if this were wrong is medium: the
experimental app-server and undocumented rollout format may change or vanish
without notice, but because they only ever enrich and never gate, such a
change degrades precision (less precise wake scheduling) rather than
correctness.

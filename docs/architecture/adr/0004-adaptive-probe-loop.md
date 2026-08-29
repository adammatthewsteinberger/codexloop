# ADR 0004 — Adaptive probe loop, never a blind sleep

## Status

Accepted

## Context

A fixed-duration blind sleep can miss a credit top-up or a plan-window reset
that happens earlier than expected — and the richest signal for scheduling a
precise wake-up (`resets_at`) is not reliably available (see
[ADR 0005](0005-layered-capacity-probe.md)). The wait strategy therefore has
to be a loop of bounded probes, not one long sleep, for every capacity state,
not just the ones with a known deadline.

## Decision

`domain/waiting.py::AdaptiveWaitPolicy` returns the next instant to probe,
never a single sleep. Cadence and ceiling are keyed to the specific
`CapacityState`: `ThrottleExhausted` uses `Retry-After` as a floor plus
jitter; `WindowExhausted(resets_at)` wakes at
`min(resets_at + grace, now + window_probe_interval)`; states with no known
deadline (`WindowExhausted(None)`, `CreditsExhausted`) use a bounded cadence
between 120s and 600s, capped by `--max-wait`. `Clock` and `Sleeper`
(`application/interfaces/system.py`) are the only two ambient effects the run
loop touches, which is what lets `FakeClock`/`FakeSleeper` simulate a
multi-hour or multi-day wait in microseconds under test.

## Consequences

Hypothesis property tests assert the policy never returns a past instant,
never exceeds `--max-wait`, and always converges. Every probe result is
diffed against the previous state and the transition is logged explicitly, so
a recovery (top-up, window roll-over) is visible in the audit log rather than
inferred from work silently resuming. Risk if this were wrong is high — a
blind sleep would miss a credit top-up and waste the entire sleep duration.

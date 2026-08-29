# ADR 0003 — CreditsExhausted is structurally non-waitable

## Status

Accepted

## Context

An HTTP 429 from OpenAI hides two structurally different failures behind one
status code: `rate_limit_exceeded` (transient, waitable, sometimes carrying
`Retry-After`) and `insufficient_quota` / `credit_balance_exhausted` (billing,
**not** waitable — no reset exists because a human has to pay). OpenAI's own
rate-limit guidance says outright: "Don't retry quota, billing, or other
errors that require you to take action." This is the same shape as the
`credits_required` finding that reshaped claudeloop, and getting it right is
the entire reason this product exists.

## Decision

`CreditsExhausted` is a distinct member of the `CapacityState` ADT and
structurally has no `resets_at` field — a billing wall cannot carry a
fabricated deadline, so no future refactor can quietly attach one.
`domain/classify.py` checks billing markers (`insufficient_quota`,
`credit_balance_exhausted`, `usage_not_included`) **before** any throttle
match, so a body that happens to mention both cannot be read as waitable.

## Consequences

A capacity rejection always outranks a completion claim (a turn that both
looks done and was billing-rejected is classified as rejected, never as
`Complete`). A property test asserts that no input whose code or type is in
the non-waitable set can ever produce a waitable `CapacityState`. When
`CreditsExhausted` is hit, the wait policy still probes on a bounded cadence
(never a blind indefinite sleep, in case a top-up lands) and fires the
notifier immediately and loudly. Risk if this is ever wrong is **critical** —
it is the whole product's reason for existing.

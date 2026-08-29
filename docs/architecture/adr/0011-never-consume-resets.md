# ADR 0011 — Never auto-consume banked rate-limit resets

## Status

Accepted

## Context

The app-server surface exposes `account/rateLimitResetCredit/consume`, which
would spend a user's banked rate-limit reset credit. Doing so implicitly, as a
side effect of a routine capacity probe, would be surprising and irreversible
— the probe's whole job is to answer "can we work right now?" cheaply, not to
spend the user's resources on their behalf.

## Decision

codexloop never calls `account/rateLimitResetCredit/consume` under any
circumstance. There is no code path, flag, or configuration option that
triggers it — it is a deliberate non-behavior, not a default that could be
toggled on.

## Consequences

An operator's banked reset credit is never touched without an explicit action
outside codexloop. Risk is low in probability but the action would be
irreversible if it ever happened, which is exactly why it is enforced as an
absence of any call path rather than left to a runtime check.

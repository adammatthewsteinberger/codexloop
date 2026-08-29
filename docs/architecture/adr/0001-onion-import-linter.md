# ADR 0001 — Onion architecture enforced by import-linter

## Status

Accepted

## Context

Every hard call in this product — *is this waitable? how long do we wait? is
the work done?* — needs to be a pure function over value objects, because
that is the only way a 100% coverage floor on `domain/` is an honest signal
rather than a mocking exercise. Carried forward from the claudeloop blueprint,
where the onion layering already proved itself.

## Decision

`domain/` stays stdlib-only: no I/O, no async, no third-party imports.
`application/` depends only on `domain`; `infrastructure/` is the only layer
allowed to import `openai` or spawn `codex`; `cli/` and `bootstrap.py` sit on
top, with `bootstrap.py` the sole module permitted to import every layer.
`import-linter` enforces the layered contract (`cli` → `bootstrap` →
`application` → `domain`, `infrastructure` importable only by `bootstrap`) in
CI, plus a forbidden-import contract — backed by a grep-based test — asserting
no module anywhere imports `anthropic` or `claude_agent_sdk`, so a copy-paste
from the claudeloop blueprint cannot smuggle a wrong-vendor dependency back in.

## Consequences

A new file that violates the layering fails CI at the `lint-imports` step
before any test runs, not at review time. This is a proven, low-risk decision
— it is unchanged from claudeloop and only reconfirmed here.

# ADR 0002 — Subprocess `codex exec --json` over an SDK

## Status

Accepted

## Context

There is no official Python Codex SDK. The official SDK, `@openai/codex-sdk`,
is TypeScript — and it is itself a thin wrapper that shells out to the `codex`
binary, passing the API key to the child process as `CODEX_API_KEY`. Driving
`codex exec --json` as a subprocess is therefore not a workaround; it is *the
same integration the official SDK performs*, minus a Node runtime. This
inverts claudeloop's own ADR-0002 ("Agent SDK over subprocess"), which was
written for a different vendor whose Python SDK talks to the API directly.

## Decision

`infrastructure/agent/gateway.py` (`CodexExecGateway`) drives `codex exec
--json` as a subprocess and is the default, documented, stable transport
behind the `AgentGateway` port. No Python Codex SDK dependency exists or is
planned.

## Consequences

Because the inversion is deliberate rather than a silent divergence, it earns
its own ADR instead of looking like an oversight relative to claudeloop. The
abstract `AgentGateway` port means a future official Python SDK — if one ships
— could be adopted as a second adapter without changing any caller. Risk is
medium: if the vendor CLI's JSON contract shifts, `infrastructure/agent/translate.py`
absorbs the change, not the domain or application layers.

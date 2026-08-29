# ADR 0009 — App-server as optional second transport

## Status

Accepted

## Context

The Codex app-server's JSON-RPC protocol offers `turn/interrupt` and
`turn/steer` — a genuine mid-turn stop and the ability to inject a prompt into
a running turn — both strictly better than anything a subprocess transport
can do. But the protocol is experimental by the vendor's own label, so it must
never become a hard dependency.

## Decision

`AgentGateway` has two implementations behind one port: the exec transport
(default, documented, stable) and the app-server transport, selected via
`--transport app-server`. The app-server path is always gated by a startup
capability probe and falls back to the exec transport whenever the probe
fails, the method is absent, or it returns an unparseable shape. A shared
contract test suite runs the same behavioral assertions against both gateway
fakes so the two adapters cannot silently drift apart.

## Consequences

The system test matrix remains exec-primary; live app-server interrupt/steer
against production `codex` builds is exercised via a shim-backed adapter in
CI while the protocol is still experimental. Mid-run operator control
(`codexloop stop` / `prompt`) upgrades transparently to the richer app-server
primitives when that transport is active, and degrades to the exec-based
control plane otherwise. Risk is low — this is a purely additive capability;
the exec transport never depends on it.

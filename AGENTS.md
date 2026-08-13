# AGENTS.md — codexloop

Facts for coding agents (not procedures).

- Onion: domain (stdlib) → application → infrastructure → cli; only `bootstrap.py` spans layers.
- No `anthropic` / `claude-agent-sdk` / `claudeloop` anywhere under `src/`.
- `QuotaExhausted` has no reset field. Body-first classification. Never `--full-auto`. Never bare `codex`.
- Default pytest: `-m "not live and not system"`.
- Generated REST: `codexloop api` + `api_baseline.json` drift gate.
- App-server transport is optional and falls back to exec.

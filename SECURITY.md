# Security Policy

## Reporting a vulnerability

Email the maintainers privately. Do not open a public issue for secrets,
credential leaks, or sandbox escapes.

## Hardening notes

- Default sandbox is `workspace-write` with `approval_policy=never`.
- `danger-full-access` requires an explicit opt-in and refuses root / non-git cwd.
- Logs redact API keys and `auth.json` material.
- Never invoke bare `codex` or `--full-auto`.

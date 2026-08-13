# codexloop

Autonomous OpenAI Codex / GPT session runner. Same job as [claudeloop](https://github.com/adammatthewsteinberger/claudeloop): never block on a human, and never treat `insufficient_quota` / billing as a waitable `rate_limit_exceeded` window.

**Status:** package skeleton and quality gates are in place (`codexloop --version` works). Domain logic is not implemented yet; see the plans table.

## Plans

| Document | Purpose |
|---|---|
| [docs/plans/architecture-and-roadmap.md](docs/plans/architecture-and-roadmap.md) | Full design / transplant plan from claudeloop 0.5.4 |
| [docs/plans/research-notes.md](docs/plans/research-notes.md) | Vendor SDK/CLI capacity + autonomy research |
| [docs/plans/_shared-transplant-outline.md](docs/plans/_shared-transplant-outline.md) | Cross-product keep/swap + Global Constraints |
| [docs/superpowers/plans/2026-08-13-codexloop-implementation.md](docs/superpowers/plans/2026-08-13-codexloop-implementation.md) | Bite-sized TDD implementation plan |

## Naming

| Item | Value |
|---|---|
| PyPI / CLI | `codexloop` |
| Env prefix | `CODEXLOOP_*` |
| State dir | `.codexloop/` |
| Done marker | `CODEXLOOP_TASK_FULLY_COMPLETE` |

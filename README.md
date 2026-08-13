# codexloop

Autonomous OpenAI Codex / GPT session runner. Same job as
[claudeloop](https://github.com/adammatthewsteinberger/claudeloop): never block on
a human, and never treat `insufficient_quota` / billing as a waitable
`rate_limit_exceeded` window.

**Status:** M1–M5 implemented on `feat/m1-pure-core` (onion core, exec gateway,
capacity probes, control plane, generated REST CLI, optional app-server transport
with exec fallback). MIT-licensed; author Adam Matthew Steinberger.

## Install

```bash
pip install -e ".[dev]"
codexloop --version
codexloop doctor
```

## Quick start

```bash
codexloop run path/to/plan.md
codexloop watch --follow
codexloop stop
```

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

## License

MIT — see [LICENSE](LICENSE).

## Publishing

Releases go **TestPyPI → PyPI** via Trusted Publishing. See
[docs/publishing.md](docs/publishing.md).

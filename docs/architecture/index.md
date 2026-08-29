# Architecture

See [`project.mmd`](../project.mmd) for the full architecture map — every
layer's modules, the exec/app-server transports, the generated REST surface,
the control-plane files, the develop → main → TestPyPI/PyPI/OCI/Pages
release channels, and the PR-automation → merge-train → promote-to-main
control plane that governs how a PR actually reaches `develop` and `main`
(see [Contributing](../contributing.md#automated-merge-and-promotion-pipeline))
— rendered as a Mermaid diagram (GitHub and most Markdown viewers render
`.mmd`/```mermaid``` blocks natively; open the raw file or paste it into the
[Mermaid Live Editor](https://mermaid.live/) otherwise).

Strict onion:

- `domain/` — pure stdlib value objects and total functions
- `application/` — ports + runner orchestration
- `infrastructure/` — `codex` subprocess, app-server, OpenAI REST surface
- `cli/` — Typer
- `bootstrap.py` — only module that sees every layer

Contracts are enforced by `import-linter`. See ADRs in this section for
accepted decisions.

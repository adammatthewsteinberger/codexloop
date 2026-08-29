# Contributing

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
pre-commit install
```

## Tests

```bash
pytest                         # default: not live and not system
pytest -m system               # scripted system harness
pytest -m live                 # real Codex account (opt-in)
```

Coverage floors: whole package 100% (`pytest --cov=codexloop --cov-fail-under=100`).

## Commits

Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`).

## Publishing

See [Publishing](publishing.md) for the push-triggered `release.yml` flow:
`develop` → TestPyPI, `main` → PyPI, both via Trusted Publishing.

## Automated merge and promotion pipeline

Landing a PR and cutting a release are not manual git operations — both are
driven by a chain of GitHub Actions workflows in `.github/workflows/`:

1. **`provenance.yml`** (Provenance) — a required check on every branch and
   pull request that rejects commits missing the repository's provenance
   fingerprint (the server-side half of the local pre-push hook, which a
   clone can skip with `--no-verify` or simply never install).
2. **`pr-automation.yml`** (PR automation) — runs on every PR event and on
   completion of CI/Provenance. It re-evaluates the exact head commit,
   requests a Claude-based exact-head code-and-documentation review, and
   depending on outcome: opens a mirrored PR for forks before touching their
   branch, attempts a bounded automated repair of failing scans or review
   findings (this is the job that produces this very kind of fix), or
   resolves a materialized merge conflict. A local-model fallback review
   runs only when the primary review returns no verdict at all (API
   outage/credits), never to override a completed review's findings.
3. **`merge-train.yml`** (Merge train) — triggered by a green
   `PR automation / gate` check; auto-merges every currently-ready PR into
   `develop`.
4. **`promote-to-main.yml`** (Promote) — triggered by a successful merge
   train, a Monday cron backstop, or manual dispatch. Compares `develop` and
   `main` **by content** (not commit count), derives the release version,
   and opens or reuses a `develop` → `main` promotion pull request. Merging
   that PR is what publishes to PyPI (see [Publishing](publishing.md)).
5. **`automation-bootstrap.yml`** (Automation bootstrap) — an explicit,
   `workflow_dispatch`-only, admin-authorized escape hatch. It exists because
   privileged workflow files are loaded from the trusted base branch, so a PR
   that repairs a *broken* PR-automation pipeline cannot prove its own repair
   through that same pipeline. It independently re-verifies every
   deterministic gate (CI, CodeQL/API-drift, documentation, provenance,
   build, lint) on the exact head before performing a narrowly-scoped admin
   squash merge, confined to automation-core paths.

**Trust boundary:** steps 3–5 push, merge, or promote using
`secrets.AUTOMERGE_TOKEN` when present (a token with the elevated,
ruleset-satisfying permissions the default `GITHUB_TOKEN` lacks), falling
back to `GITHUB_TOKEN` otherwise. Anyone who can set that secret effectively
controls what reaches `main` and PyPI — see the CI/CD trust boundary entry
in [SECURITY.md](https://github.com/adammatthewsteinberger/codexloop/blob/develop/SECURITY.md#threat-model-briefly).
This is a repository/organization-level secret; `codexloop` itself never
reads or writes it at runtime.

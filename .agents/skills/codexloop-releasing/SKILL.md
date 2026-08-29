---
name: codexloop-releasing
description: vibey-gh dev-version stamping, gitflow (develop → main), push-triggered TestPyPI + PyPI publishing via release.yml. Use before cutting a release.
allowed-tools: Read Bash(git *)
---

# codexloop releasing

## Gitflow

```
develop (default branch) → main (releases)
```

1. Feature PRs squash into `develop`.
2. `develop` merge-commits into `main` when ready to release.
3. Every push to `develop` or `main` runs `.github/workflows/release.yml`
   (**Release**) and publishes directly — there is no standing release PR
   and no release-please.

## Workflows

- **`ci.yml`**: runs on every push. Tests, linting, type checks, per-layer
  coverage, import-linter, bandit, pip-audit.
- **`release.yml`** (**Release**): push-triggered on `develop` and `main`.
  - On `develop`: stamps a unique dev version with
    `vibey-gh version --dev "$GITHUB_RUN_NUMBER" --apply`, builds, and
    publishes straight to TestPyPI (Trusted Publishing, no token). A
    `verify-testpypi` job then installs that exact version and runs
    `codexloop --version`.
  - On `main`: builds from the version already committed in
    `pyproject.toml` and publishes straight to PyPI (Trusted Publishing).
  - A `realign` job (`main` only) runs `vibey-gh realign` to converge
    `develop` back onto `main`; it's a no-op, not a failure, when
    `AUTOMERGE_TOKEN` isn't configured.
- **`release-surfaces.yml`**: triggered by a successful **Release** run.
  Publishes an OCI package bundle to GitHub Packages and builds/deploys the
  ProperDocs site for that channel (`develop` or `main`) to GitHub Pages.

## Versioning

`vibey-gh` (pinned in `.vibey-gh.toml`) owns the version in
`pyproject.toml` and `src/codexloop/__init__.py`. There is no
`release-please-config.json` and no automated `CHANGELOG.md` generation —
`.vibey-gh.toml` explicitly retired release-please: "two systems deriving
versions and opening release pull requests against one branch is a race,
not redundancy."

## Before merging develop → main

1. All CI gates green on `develop`.
2. The `develop` push's **Release** run (TestPyPI publish + verify) succeeded.
3. `pyproject.toml`'s version is what you intend to ship — merging to `main`
   publishes it to PyPI immediately, with no review step in between.

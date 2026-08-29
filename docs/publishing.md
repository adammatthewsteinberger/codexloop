# Publishing

`codexloop` ships via [Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
(OIDC). No long-lived PyPI API tokens are stored in GitHub.

A single workflow, [`.github/workflows/release.yml`](https://github.com/adammatthewsteinberger/codexloop/blob/develop/.github/workflows/release.yml)
(named **Release**), drives both registries. It is push-triggered — there is
no standing release pull request and no separate release-please step.

## Environments

| GitHub Environment | Index | Branch |
|---|---|---|
| `testpypi` | https://test.pypi.org | **`develop`** |
| `pypi` | https://pypi.org | **`main`** |

Create them once (repo **Settings → Environments**) before the first upload.

## One-time Trusted Publisher setup

Do this **before** the first upload (pending publisher), signed in as the PyPI
owner account.

### TestPyPI

1. Open https://test.pypi.org/manage/account/publishing/
2. Add a pending publisher:
   - **PyPI Project Name:** `codexloop`
   - **Owner:** `adammatthewsteinberger`
   - **Repository name:** `codexloop`
   - **Workflow name:** `release.yml`
   - **Environment name:** `testpypi`

### PyPI

1. Open https://pypi.org/manage/account/publishing/
2. Add a pending publisher:
   - **PyPI Project Name:** `codexloop`
   - **Owner:** `adammatthewsteinberger`
   - **Repository name:** `codexloop`
   - **Workflow name:** `release.yml`
   - **Environment name:** `pypi`

## Release flow

```text
feature/* ──PR (squash)──► develop ──push──► TestPyPI
                              │
                              ▼ (merge commit, when ready to release)
                             main ──push──► PyPI
```

The **Release** workflow runs on every push to `develop` or `main` and takes
a different path per branch — the two are deliberately disjoint, since
publishing a final release version to TestPyPI first would make the PyPI
release depend on a second registry:

1. **Push to `develop`** — the `build` job installs `vibey-gh` and runs
   `vibey-gh version --dev "$GITHUB_RUN_NUMBER" --apply` to stamp a unique,
   pre-release dev version into `pyproject.toml` (sorts *before* the release
   it anticipates). It builds the sdist/wheel and the `testpypi` job uploads
   them straight to TestPyPI via Trusted Publishing — no manual step, no
   release PR. A `verify-testpypi` job then pip-installs that exact version
   from the index and runs `codexloop --version` to confirm it's live.
2. Smoke-install from TestPyPI if needed:
   `pip install -i https://test.pypi.org/simple/ --pre codexloop`.
3. `develop` → `main` (merge commit) is **not a manual step**. It is
   performed by [`.github/workflows/promote-to-main.yml`](https://github.com/adammatthewsteinberger/codexloop/blob/develop/.github/workflows/promote-to-main.yml)
   (workflow name **Promote**), triggered by a successful
   [`merge-train.yml`](https://github.com/adammatthewsteinberger/codexloop/blob/develop/.github/workflows/merge-train.yml)
   run, a Monday-morning cron backstop, or manual `workflow_dispatch`. It
   compares `develop` and `main` **by content** (not commit count) to decide
   whether there is anything to promote, derives the release version, and
   opens or reuses a `develop` → `main` promotion pull request; that PR's own
   scans, the `PR automation` gate, and a rebase merge then run
   asynchronously before it lands. Merging it is what actually cuts the
   release. This job needs an admin-scoped `AUTOMERGE_TOKEN` secret to push
   the version bump and merge past branch-protection rules a plain
   `GITHUB_TOKEN` cannot satisfy; without it, promotion falls back to a
   manual `git push --force-with-lease` by someone with `main` push rights.
   See [Automated merge and promotion pipeline](contributing.md#automated-merge-and-promotion-pipeline)
   for the rest of the pipeline that feeds into this step (PR-automation
   review/repair, the merge train, and the admin-only
   `automation-bootstrap.yml` escape hatch).
4. **Push to `main`** — the `build` job uses the version already committed
   in `pyproject.toml` (no dev stamping on `main`) and the `pypi` job
   publishes that build directly to PyPI via Trusted Publishing.
5. A final `realign` job (on `main` only) fast-forwards/rebases `develop`
   back onto `main` using `vibey-gh realign`, so the two branches converge
   after a release. It requires the same `AUTOMERGE_TOKEN` secret with admin
   permissions on `develop`'s ruleset; if that secret isn't set, the job
   logs a notice and exits 0 rather than failing the release — realignment
   is tidiness, not a gate, since promotion compares branches by content.

There is no release-please, no standing release pull request maintained by
hand, no `CHANGELOG.md` automation, and no manual `gh workflow run` step
required to cut a release — every release is an automated promotion PR
merging into `main`, not a human running `git merge`.

After **Release** succeeds, [`release-surfaces.yml`](https://github.com/adammatthewsteinberger/codexloop/blob/develop/.github/workflows/release-surfaces.yml)
runs automatically (`workflow_run` trigger) to publish two companion
surfaces per channel (`develop` and `main`): a versioned OCI package bundle
in GitHub Packages (`ghcr.io/<owner>/<repo>/python`) and a ProperDocs
documentation site under GitHub Pages
(`https://<owner>.github.io/<repo>/<channel>/`).

## Local dry-run (no upload)

```bash
python -m build
twine check --strict dist/*
```

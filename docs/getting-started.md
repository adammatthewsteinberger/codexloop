# Getting started

## Install

```bash
pipx install codexloop
```

From a clone (contributors):

```bash
pip install -e ".[dev,docs]"
```

## Preflight

```bash
codexloop doctor
codexloop capacity
```

## Writing a plan

`codexloop run` reads a markdown work plan and tracks progress against its
checkbox items. A line is recognized as an item when it matches
`- [ ] task` (or `* [ ]` / `+ [ ]`, and `[x]` / `[X]` for already-done items):

```markdown
# Add retry handling

- [ ] Read the current retry logic in `client.py`
- [ ] Add exponential backoff with jitter
- [x] Write unit tests for the backoff calculation
- [ ] Update the README
```

Everything else in the file (headings, prose, non-checkbox bullets) is
ignored for parsing purposes but is still passed to the model as context. A
plan needs **at least one checkbox item** — a plan file with none raises a
configuration error before any turn is sent, since there would be no
`remaining_work` to track or complete.

## Run a plan

```bash
codexloop run path/to/plan.md --max-turns 20
```

Default transport is `codex exec --json`. Optional `--transport app-server`
probes the experimental app-server and falls back to exec when unavailable.

!!! note "Roadmap"
    Live app-server interrupt/steer against production `codex` builds still
    tracks the experimental protocol; the shim-backed adapter is covered in CI.

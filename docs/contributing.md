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

Coverage floors: domain/app 100%, infrastructure ≥90%, cli ≥85%.

## Commits

Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`).

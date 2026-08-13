"""``codexloop watch`` — print current run state (one-shot)."""

from __future__ import annotations

import json

import typer

from codexloop.bootstrap import read_run_state


def watch(
    run_id: str | None = typer.Argument(None, help="Run id. Defaults to the latest run."),
) -> None:
    """Show a snapshot of persisted run state."""
    state = read_run_state(run_id)
    if not state:
        typer.echo("no run state")
        raise typer.Exit(1)
    typer.echo(json.dumps(state, indent=2, default=str))

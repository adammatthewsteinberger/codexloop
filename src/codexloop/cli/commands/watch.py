"""``codexloop watch`` — print current run state (one-shot) or replay events."""

from __future__ import annotations

import json

import typer

from codexloop.bootstrap import events_path_for_run, read_run_state, run_stream_ui_for_events


def watch(
    run_id: str | None = typer.Argument(None, help="Run id. Defaults to the latest run."),
    replay: bool = typer.Option(
        False,
        "--replay",
        help="Open the Textual stream UI against the run event log.",
    ),
) -> None:
    """Show a snapshot of persisted run state."""
    if replay:
        run_stream_ui_for_events(events_path_for_run(run_id))
        return
    state = read_run_state(run_id)
    if not state:
        typer.echo("no run state")
        raise typer.Exit(1)
    typer.echo(json.dumps(state, indent=2, default=str))

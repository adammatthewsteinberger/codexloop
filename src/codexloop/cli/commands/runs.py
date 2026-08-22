# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""``codexloop runs``."""

from __future__ import annotations

import typer

from codexloop.bootstrap import list_run_records
from codexloop.cli.render import render_runs


def runs() -> None:
    """List run directories under .codexloop/runs/."""
    typer.echo(render_runs(list_run_records()))

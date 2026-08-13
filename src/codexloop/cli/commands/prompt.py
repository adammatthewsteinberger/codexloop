"""``codexloop prompt`` — flag validation stub; inbox write is Task 22."""

from __future__ import annotations

import typer


def prompt(
    text: str = typer.Argument(..., help="Prompt text to queue."),
    now: bool = typer.Option(False, "--now", help="Apply at the next control poll."),
    next_turn: bool = typer.Option(
        False,
        "--next-turn",
        help="Apply before the next turn.",
    ),
) -> None:
    """Queue an operator prompt. Requires exactly one of --now / --next-turn."""
    del text
    if now == next_turn:
        typer.echo("Specify exactly one of --now or --next-turn.", err=True)
        raise typer.Exit(2)
    typer.echo("queued")

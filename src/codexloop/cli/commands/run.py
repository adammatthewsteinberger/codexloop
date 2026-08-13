"""``codexloop run <plan.md>``."""

from __future__ import annotations

from pathlib import Path

import typer

from codexloop.application.usecases.run_plan import run_plan
from codexloop.bootstrap import build_runner
from codexloop.cli.asyncio import async_command
from codexloop.cli.render import render_result
from codexloop.domain.session import PlanFile


@async_command
async def run(
    plan: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        help="Markdown work plan.",
    ),
    transport: str = typer.Option(
        "exec",
        "--transport",
        help="Agent transport: exec or app-server.",
    ),
    model: str | None = typer.Option(None, "--model", help="Model name."),
    max_turns: int | None = typer.Option(None, "--max-turns", help="Turn budget."),
    max_wait: str | None = typer.Option(None, "--max-wait", help="Max wait duration."),
) -> object:
    """Drive a new autonomous run from a markdown work plan."""
    flags: dict[str, object] = {
        "model": model,
        "max_turns": max_turns,
        "max_wait": max_wait,
    }
    ctx = build_runner(transport=transport, flags=flags)
    text = plan.read_text(encoding="utf-8")
    result = await run_plan(ctx, PlanFile(str(plan)), text)
    typer.echo(render_result(result))
    return result

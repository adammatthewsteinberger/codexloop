"""Typer root app and console-script entry point.

Registered in pyproject.toml as:
    [project.scripts]
    codexloop = "codexloop.cli.app:main"
"""

from __future__ import annotations

import typer

from codexloop import __version__
from codexloop.cli.commands.logs import logs
from codexloop.cli.commands.prompt import prompt
from codexloop.cli.commands.resume import resume
from codexloop.cli.commands.run import run
from codexloop.cli.commands.runs import runs
from codexloop.cli.commands.status import status
from codexloop.cli.commands.threads import threads

app = typer.Typer(
    name="codexloop",
    help=(
        "Onion-architected, autonomous OpenAI Codex session runner — never "
        "blocks on a human, distinguishes rate limits from exhausted credits, "
        "and resumes safely across usage windows."
    ),
    add_completion=False,
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"codexloop {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed codexloop version and exit.",
    ),
) -> None:
    del version


app.command()(run)
app.command()(resume)
app.command()(threads)
app.command()(status)
app.command()(logs)
app.command()(runs)
app.command()(prompt)


def main() -> None:
    app()


if __name__ == "__main__":
    main()

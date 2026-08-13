"""Typer root app and console-script entry point.

Registered in pyproject.toml as:
    [project.scripts]
    codexloop = "codexloop.cli.app:main"
"""

from __future__ import annotations

import typer

from codexloop import __version__

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


def main() -> None:
    app()


if __name__ == "__main__":
    main()

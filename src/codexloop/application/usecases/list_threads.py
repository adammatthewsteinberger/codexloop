# Made with ❤️ by [Vibey](https://adammatthewsteinberger.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://hire.adam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""Use case: list this product's run registry, not vendor sessions."""

from __future__ import annotations

from collections.abc import Sequence

from codexloop.application.runner import RunnerContext
from codexloop.domain.session import ThreadRef


def list_threads(ctx: RunnerContext) -> Sequence[ThreadRef]:
    if ctx.catalog is None:
        return ()
    return ctx.catalog.list_threads()

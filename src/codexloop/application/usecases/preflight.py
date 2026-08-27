# Made with ❤️ by [Vibey](https://adammatthewsteinberger.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://hire.adam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""Use case: probe capacity without spending a real turn."""

from __future__ import annotations

from codexloop.application.dto import ProbeResult
from codexloop.application.runner import RunnerContext


async def preflight(ctx: RunnerContext) -> ProbeResult:
    return await ctx.probe.probe()

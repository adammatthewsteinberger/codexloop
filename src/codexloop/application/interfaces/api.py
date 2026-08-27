# Made with ❤️ by [Vibey](https://adammatthewsteinberger.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://hire.adam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
"""The generated REST surface seam."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ApiGateway(Protocol):
    def invoke(self, method_path: str, **kwargs: object) -> object: ...

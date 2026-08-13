"""Extra coverage for API params helpers."""

from __future__ import annotations

import inspect

from openai import NotGiven, Omit

from codexloop.infrastructure.api.params import (
    build_call_kwargs,
    is_scalar_annotation,
    typer_type_for_annotation,
)

_OMIT = Omit()
_NOT_GIVEN = NotGiven()


def test_union_and_optional_normalization() -> None:
    assert is_scalar_annotation(int | None)
    assert is_scalar_annotation(str | Omit)
    assert typer_type_for_annotation("bool") is bool
    assert typer_type_for_annotation("float") is float


def test_build_call_kwargs_merges_scalars_and_skips_none() -> None:
    def sample(
        self,
        model: str,
        n: int | Omit = _OMIT,
        extra_headers: object | None = None,
    ) -> None:
        del self, model, n, extra_headers

    kwargs = build_call_kwargs(
        inspect.signature(sample),
        json_payload={"model": "gpt"},
        scalar_values={"n": None},
    )
    assert kwargs == {"model": "gpt"}


def test_not_given_default_is_omit_like() -> None:
    def sample(self, timeout: float | NotGiven = _NOT_GIVEN) -> None:
        del self, timeout

    kwargs = build_call_kwargs(
        inspect.signature(sample),
        json_payload={},
        scalar_values={"timeout": 1.5},
    )
    assert kwargs["timeout"] == 1.5

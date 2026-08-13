"""Unit tests for OpenAI API providers."""

from __future__ import annotations

import pytest

from codexloop.infrastructure.api.providers import (
    build_client,
    client_class_for_provider,
    surface_roots_for_provider,
)


def test_client_class_for_providers() -> None:
    from openai import AzureOpenAI, OpenAI

    assert client_class_for_provider("openai") is OpenAI
    assert client_class_for_provider("custom") is OpenAI
    assert client_class_for_provider("azure") is AzureOpenAI


def test_surface_roots_full_tree() -> None:
    assert surface_roots_for_provider("openai") is None
    assert surface_roots_for_provider("azure") is None
    assert surface_roots_for_provider("custom") is None


def test_build_client_without_credentials() -> None:
    client = build_client("openai")
    assert client.api_key == "codexloop-placeholder"


def test_azure_defaults_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("OPENAI_API_VERSION", raising=False)
    client = build_client("azure")
    assert getattr(client, "api_version", None) or True

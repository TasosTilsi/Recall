"""Tests for src/llm/provider.py — ProviderClient, _detect_sdk, validate_provider_startup.

All tests in this file are written before the implementation (TDD RED phase).
They will fail with ImportError until Task 2 creates src/llm/provider.py.
"""

import sys
from unittest.mock import AsyncMock, patch

import pytest

from src.llm.provider import _detect_sdk, validate_provider_startup


# ---------------------------------------------------------------------------
# _detect_sdk URL detection tests
# ---------------------------------------------------------------------------


def test_detect_sdk_by_url_localhost():
    """localhost URLs map to ollama SDK."""
    assert _detect_sdk("http://localhost:11434") == "ollama"


def test_detect_sdk_by_url_127_0_0_1():
    """127.0.0.1 URLs map to ollama SDK."""
    assert _detect_sdk("http://127.0.0.1:11434") == "ollama"


def test_detect_sdk_by_url_ollama_com():
    """ollama.com URLs map to ollama SDK."""
    assert _detect_sdk("https://ollama.com") == "ollama"


def test_detect_sdk_by_url_openai():
    """OpenAI API URL maps to openai SDK."""
    assert _detect_sdk("https://api.openai.com/v1") == "openai"


def test_detect_sdk_by_url_groq():
    """Groq API URL maps to openai SDK (OpenAI-compatible endpoint)."""
    assert _detect_sdk("https://api.groq.com/openai/v1") == "openai"


# ---------------------------------------------------------------------------
# validate_provider_startup tests
# ---------------------------------------------------------------------------


def _make_config(llm_mode="legacy", primary_url=None, primary_api_key=None):
    """Build a minimal LLMConfig for testing."""
    from src.llm.config import LLMConfig

    return LLMConfig(
        llm_mode=llm_mode,
        llm_primary_url=primary_url,
        llm_primary_api_key=primary_api_key,
    )


def test_startup_validation_noop_for_legacy():
    """validate_provider_startup() is a no-op when llm_mode == 'legacy'."""
    config = _make_config(llm_mode="legacy")

    with patch("sys.exit") as mock_exit:
        result = validate_provider_startup(config)

    assert result is None
    mock_exit.assert_not_called()


def test_startup_validation_fails_fast():
    """validate_provider_startup() calls sys.exit(1) when ping_primary returns (False, ...)."""
    from src.llm.provider import ProviderClient

    config = _make_config(
        llm_mode="provider",
        primary_url="https://api.openai.com/v1",
        primary_api_key="sk-bad-key",
    )

    with (
        patch.object(ProviderClient, "ping_primary", new=AsyncMock(return_value=(False, "401 Unauthorized"))),
        patch("sys.exit") as mock_exit,
    ):
        validate_provider_startup(config)

    mock_exit.assert_called_once_with(1)


def test_startup_validation_passes():
    """validate_provider_startup() returns None when ping_primary returns (True, '')."""
    from src.llm.provider import ProviderClient

    config = _make_config(
        llm_mode="provider",
        primary_url="https://api.openai.com/v1",
        primary_api_key="sk-good-key",
    )

    with (
        patch.object(ProviderClient, "ping_primary", new=AsyncMock(return_value=(True, ""))),
        patch("sys.exit") as mock_exit,
    ):
        result = validate_provider_startup(config)

    assert result is None
    mock_exit.assert_not_called()


# ---------------------------------------------------------------------------
# Adapter factory routing tests (Task 1 of Plan 13-02 — TDD RED)
# These will fail with ImportError until Task 2 adds make_llm_client/make_embedder
# ---------------------------------------------------------------------------


from src.graph.adapters import make_llm_client, make_embedder, OllamaLLMClient, OllamaEmbedder
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.embedder.openai import OpenAIEmbedder
from src.llm.config import LLMConfig


def _provider_config(primary_url, embed_url=None):
    """Build a LLMConfig in provider mode for factory tests."""
    return LLMConfig(
        llm_mode="provider",
        llm_primary_url=primary_url,
        llm_primary_api_key="sk-test",
        llm_primary_models=["gpt-4o-mini"],
        llm_embed_url=embed_url or primary_url,
        llm_embed_models=["text-embedding-3-small"],
    )


def _legacy_config():
    """Build a LLMConfig in legacy mode (all defaults)."""
    return LLMConfig()  # all defaults → llm_mode="legacy"


def test_make_llm_client_openai():
    """make_llm_client with openai-compatible URL returns OpenAIGenericClient."""
    config = _provider_config("https://api.openai.com/v1")
    client = make_llm_client(config)
    assert isinstance(client, OpenAIGenericClient)


def test_make_llm_client_legacy():
    """make_llm_client with legacy mode returns OllamaLLMClient."""
    config = _legacy_config()
    client = make_llm_client(config)
    assert isinstance(client, OllamaLLMClient)


def test_make_llm_client_ollama_url():
    """make_llm_client with localhost URL returns OllamaLLMClient even in provider mode."""
    config = _provider_config("http://localhost:11434")
    client = make_llm_client(config)
    assert isinstance(client, OllamaLLMClient)


def test_make_embedder_openai():
    """make_embedder with openai-compatible embed URL returns OpenAIEmbedder."""
    config = _provider_config("https://api.openai.com/v1", embed_url="https://api.openai.com/v1")
    embedder = make_embedder(config)
    assert isinstance(embedder, OpenAIEmbedder)


def test_make_embedder_legacy():
    """make_embedder with legacy mode returns OllamaEmbedder."""
    config = _legacy_config()
    embedder = make_embedder(config)
    assert isinstance(embedder, OllamaEmbedder)

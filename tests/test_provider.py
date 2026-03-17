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

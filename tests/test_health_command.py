"""Tests for health command provider rows (Phase 13 — PROV-03).

Tests _check_provider() returning correct rows based on llm_mode and ping results.
"""
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from src.cli.commands.health import _check_provider
from src.llm.config import LLMConfig


def _make_provider_config(
    primary_url="https://api.openai.com/v1",
    embed_url="https://api.openai.com/v1",
    fallback_url=None,
):
    """Helper: return LLMConfig in provider mode."""
    return LLMConfig(
        llm_mode="provider",
        llm_primary_url=primary_url,
        llm_primary_api_key="sk-test",
        llm_primary_models=["gpt-4o-mini"],
        llm_embed_url=embed_url,
        llm_embed_api_key="sk-test",
        llm_embed_models=["text-embedding-3-small"],
        llm_fallback_url=fallback_url,
        llm_fallback_models=["gemma2:9b"] if fallback_url else [],
    )


def _make_legacy_config():
    """Helper: return LLMConfig in legacy (Ollama) mode."""
    return LLMConfig(llm_mode="legacy")


# ---------------------------------------------------------------------------
# test_provider_rows_absent_when_legacy
# ---------------------------------------------------------------------------

def test_provider_rows_absent_when_legacy():
    """_check_provider() returns empty list when llm_mode == 'legacy'."""
    with patch("src.cli.commands.health.load_config", return_value=_make_legacy_config()):
        rows = _check_provider()
    assert rows == []


# ---------------------------------------------------------------------------
# test_provider_row_format_ok
# ---------------------------------------------------------------------------

def test_provider_row_format_ok():
    """_check_provider() returns Provider row with [OK] tag when ping succeeds."""
    with patch("src.cli.commands.health.load_config", return_value=_make_provider_config()):
        with patch("src.cli.commands.health.ProviderClient") as mock_pc_cls:
            mock_pc = MagicMock()
            mock_pc.ping_primary = AsyncMock(return_value=(True, ""))
            mock_pc.ping_embed = AsyncMock(return_value=(True, ""))
            mock_pc.primary_label.return_value = "openai/gpt-4o-mini @ api.openai.com"
            mock_pc.embed_label.return_value = "openai/text-embedding-3-small @ api.openai.com"
            mock_pc.fallback_label.return_value = None
            mock_pc_cls.return_value = mock_pc

            rows = _check_provider()

    assert any(r["name"] == "Provider" for r in rows)
    provider_row = next(r for r in rows if r["name"] == "Provider")
    assert "OK" in provider_row["detail"]
    assert "openai/gpt-4o-mini" in provider_row["detail"]
    assert provider_row["status"] == "ok"


# ---------------------------------------------------------------------------
# test_provider_row_format_unreachable
# ---------------------------------------------------------------------------

def test_provider_row_format_unreachable():
    """_check_provider() shows UNREACHABLE when ping fails."""
    with patch("src.cli.commands.health.load_config", return_value=_make_provider_config()):
        with patch("src.cli.commands.health.ProviderClient") as mock_pc_cls:
            mock_pc = MagicMock()
            mock_pc.ping_primary = AsyncMock(return_value=(False, "API key rejected (401)"))
            mock_pc.ping_embed = AsyncMock(return_value=(False, "API key rejected (401)"))
            mock_pc.primary_label.return_value = "openai/gpt-4o-mini @ api.openai.com"
            mock_pc.embed_label.return_value = "openai/text-embedding-3-small @ api.openai.com"
            mock_pc.fallback_label.return_value = None
            mock_pc_cls.return_value = mock_pc

            rows = _check_provider()

    provider_row = next(r for r in rows if r["name"] == "Provider")
    assert "UNREACHABLE" in provider_row["detail"]
    assert provider_row["status"] == "error"


# ---------------------------------------------------------------------------
# test_embed_row_present_when_configured
# ---------------------------------------------------------------------------

def test_embed_row_present_when_configured():
    """_check_provider() returns an Embed row when embed_url is configured."""
    with patch("src.cli.commands.health.load_config", return_value=_make_provider_config()):
        with patch("src.cli.commands.health.ProviderClient") as mock_pc_cls:
            mock_pc = MagicMock()
            mock_pc.ping_primary = AsyncMock(return_value=(True, ""))
            mock_pc.ping_embed = AsyncMock(return_value=(True, ""))
            mock_pc.primary_label.return_value = "openai/gpt-4o-mini @ api.openai.com"
            mock_pc.embed_label.return_value = "openai/text-embedding-3-small @ api.openai.com"
            mock_pc.fallback_label.return_value = None
            mock_pc_cls.return_value = mock_pc

            rows = _check_provider()

    assert any(r["name"] == "Embed" for r in rows)
    embed_row = next(r for r in rows if r["name"] == "Embed")
    assert "text-embedding-3-small" in embed_row["detail"]


# ---------------------------------------------------------------------------
# test_fallback_row_absent_when_not_configured
# ---------------------------------------------------------------------------

def test_fallback_row_absent_when_not_configured():
    """_check_provider() returns no Fallback row when llm_fallback_url is None."""
    with patch("src.cli.commands.health.load_config", return_value=_make_provider_config(fallback_url=None)):
        with patch("src.cli.commands.health.ProviderClient") as mock_pc_cls:
            mock_pc = MagicMock()
            mock_pc.ping_primary = AsyncMock(return_value=(True, ""))
            mock_pc.ping_embed = AsyncMock(return_value=(True, ""))
            mock_pc.primary_label.return_value = "openai/gpt-4o-mini @ api.openai.com"
            mock_pc.embed_label.return_value = "openai/text-embedding-3-small @ api.openai.com"
            mock_pc.fallback_label.return_value = None
            mock_pc_cls.return_value = mock_pc

            rows = _check_provider()

    assert not any(r["name"] == "Fallback" for r in rows)

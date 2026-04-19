"""Tests for src/llm/health.py v3.0 health check module."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.config import Config, LLMConfig, EmbeddingsConfig, DBConfig
from src.llm.client import LLMError, LLMResponse
from src.llm.health import HealthResult, check_health


def _cfg(provider: str, embeddings=None) -> Config:
    url = "http://localhost:11434" if provider == "ollama" else ""
    return Config(
        llm=LLMConfig(provider=provider, model="test-model", url=url, api_key=""),
        embeddings=embeddings,
        db=DBConfig(),
    )


def _emb_cfg():
    return EmbeddingsConfig(provider="ollama", model="nomic-embed-text",
                             url="http://localhost:11434", api_key="")


def _ok_response(provider="claude"):
    return LLMResponse(content="pong", provider=provider, model="test-model")


@pytest.mark.asyncio
async def test_health_claude_ok():
    """Test 1: check_health returns OK when mock chat() succeeds."""
    cfg = _cfg("claude")
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=_ok_response("claude"))
    mock_client.embed = AsyncMock(return_value=None)

    with patch("src.llm.health.make_llm_client", return_value=mock_client):
        result = await check_health(cfg)

    assert result.status == "OK"
    assert result.provider == "claude"
    assert result.embeddings_status == "not configured"
    assert result.error is None


@pytest.mark.asyncio
async def test_health_ollama_unreachable():
    """Test 2: UNREACHABLE when mock chat() raises LLMError. Must not raise."""
    cfg = _cfg("ollama")
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=LLMError("ollama unreachable at http://localhost:11434"))

    with patch("src.llm.health.make_llm_client", return_value=mock_client):
        result = await check_health(cfg)

    assert result.status == "UNREACHABLE"
    assert result.error is not None


@pytest.mark.asyncio
async def test_health_embeddings_ok():
    """Test 3: embeddings_status='OK' when mock embed() returns non-empty list."""
    cfg = _cfg("claude", embeddings=_emb_cfg())
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=_ok_response())
    mock_client.embed = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

    with patch("src.llm.health.make_llm_client", return_value=mock_client):
        result = await check_health(cfg)

    assert result.embeddings_status == "OK"
    assert result.embeddings_error is None


@pytest.mark.asyncio
async def test_health_embeddings_unreachable():
    """Test 4: embeddings_status='UNREACHABLE' when mock embed() raises LLMError."""
    cfg = _cfg("claude", embeddings=_emb_cfg())
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=_ok_response())
    mock_client.embed = AsyncMock(side_effect=LLMError("ollama embeddings unreachable"))

    with patch("src.llm.health.make_llm_client", return_value=mock_client):
        result = await check_health(cfg)

    assert result.embeddings_status == "UNREACHABLE"
    assert result.embeddings_error is not None


@pytest.mark.asyncio
async def test_health_no_embeddings():
    """Test 5: embeddings_status='not configured' when config.embeddings is None."""
    cfg = _cfg("claude")
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(return_value=_ok_response())

    with patch("src.llm.health.make_llm_client", return_value=mock_client):
        result = await check_health(cfg)

    assert result.embeddings_status == "not configured"


@pytest.mark.asyncio
async def test_health_timeout_applied():
    """Test 6: timeout of 5s applied — TimeoutError produces UNREACHABLE, not raise."""
    cfg = _cfg("claude")
    mock_client = AsyncMock()
    mock_client.chat = AsyncMock(side_effect=asyncio.TimeoutError())

    with patch("src.llm.health.make_llm_client", return_value=mock_client):
        # Must not raise — timeout captured as UNREACHABLE
        result = await check_health(cfg)

    assert result.status == "UNREACHABLE"

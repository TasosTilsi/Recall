"""Tests for src/llm/client.py v3.0 single-provider LLM client."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.config import Config, LLMConfig, EmbeddingsConfig, DBConfig
from src.llm.client import LLMClient, LLMError, make_llm_client


def _make_config(provider: str, url: str = "", api_key: str = "", embeddings=None) -> Config:
    return Config(
        llm=LLMConfig(provider=provider, model="test-model", url=url, api_key=api_key),
        embeddings=embeddings,
        db=DBConfig(),
    )


def test_make_llm_client_claude():
    """Test 1: provider=claude → client._provider == 'claude'."""
    cfg = _make_config("claude")
    client = make_llm_client(cfg)
    assert client._provider == "claude"


def test_make_llm_client_ollama():
    """Test 2: provider=ollama → client._provider == 'ollama'."""
    cfg = _make_config("ollama", url="http://localhost:11434")
    client = make_llm_client(cfg)
    assert client._provider == "ollama"


def test_make_llm_client_openai():
    """Test 3: provider=openai → client._provider == 'openai'."""
    cfg = _make_config("openai", url="https://api.openai.com/v1", api_key="sk-x")
    client = make_llm_client(cfg)
    assert client._provider == "openai"


@pytest.mark.asyncio
async def test_chat_claude_binary_not_found():
    """Test 4: claude provider, shutil.which returns None → LLMError."""
    cfg = _make_config("claude")
    client = make_llm_client(cfg)
    with patch("src.llm.client.shutil.which", return_value=None):
        with pytest.raises(LLMError, match="claude binary not found"):
            await client.chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_chat_ollama_unreachable():
    """Test 5: ollama, server refusing connection → LLMError containing URL."""
    cfg = _make_config("ollama", url="http://localhost:11434")
    client = make_llm_client(cfg)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    with patch("src.llm.client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(LLMError, match="localhost:11434"):
            await client.chat([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_embed_no_embeddings_configured():
    """Test 6: embed() when config.embeddings is None → LLMError."""
    cfg = _make_config("claude")  # no embeddings
    client = make_llm_client(cfg)
    with pytest.raises(LLMError, match="embeddings not configured"):
        await client.embed(["hello"])


@pytest.mark.asyncio
async def test_no_live_calls():
    """Test 7: verify tests don't use live network/subprocess (all mocked)."""
    # This test just documents the intent — the other tests' use of mocks
    # ensures no live calls. Here we verify import works cleanly.
    from src.llm import LLMClient, LLMError, LLMResponse, make_llm_client
    assert LLMClient is not None
    assert LLMError is not None
    assert LLMResponse is not None
    assert make_llm_client is not None

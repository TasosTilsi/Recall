"""Tests for ClaudeCliLLMClient — PERF-02 coverage."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.llm.claude_cli_client import ClaudeCliLLMClient, _claude_p, claude_cli_available


class TestClaudeCliAvailable:
    """Test claude_cli_available() detection."""

    def test_available_when_on_path(self):
        with patch("src.llm.claude_cli_client.shutil.which", return_value="/usr/bin/claude"):
            # Reset cached value
            import src.llm.claude_cli_client as mod
            mod._CLAUDE_AVAILABLE = None
            assert claude_cli_available() is True

    def test_unavailable_when_not_on_path(self):
        with patch("src.llm.claude_cli_client.shutil.which", return_value=None):
            import src.llm.claude_cli_client as mod
            mod._CLAUDE_AVAILABLE = None
            assert claude_cli_available() is False


class TestClaudePSubprocess:
    """Test _claude_p() subprocess invocation."""

    def test_successful_call(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(
            json.dumps({"result": "hello world", "type": "result"}).encode(),
            b"",
        ))
        with patch("src.llm.claude_cli_client.asyncio.create_subprocess_exec",
                   new_callable=AsyncMock, return_value=mock_proc):
            result = asyncio.run(_claude_p("test prompt"))
            assert result == "hello world"

    def test_nonzero_exit_raises(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error msg"))
        with patch("src.llm.claude_cli_client.asyncio.create_subprocess_exec",
                   new_callable=AsyncMock, return_value=mock_proc):
            with pytest.raises(RuntimeError, match="claude -p failed"):
                asyncio.run(_claude_p("test prompt"))


class TestClaudeCliLLMClient:
    """Test ClaudeCliLLMClient implements LLMClient ABC."""

    def test_is_subclass_of_llm_client(self):
        from graphiti_core.llm_client.client import LLMClient
        assert issubclass(ClaudeCliLLMClient, LLMClient)

    def test_can_instantiate(self):
        client = ClaudeCliLLMClient()
        assert client is not None

    def test_generate_response_returns_content(self):
        from graphiti_core.prompts.models import Message
        client = ClaudeCliLLMClient()
        with patch("src.llm.claude_cli_client._claude_p",
                   new_callable=AsyncMock, return_value="test response"):
            result = asyncio.run(client._generate_response(
                messages=[Message(role="user", content="hello")],
            ))
            assert result == {"content": "test response"}

    def test_generate_response_with_response_model(self):
        from graphiti_core.prompts.models import Message
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            value: int

        client = ClaudeCliLLMClient()
        with patch("src.llm.claude_cli_client._claude_p",
                   new_callable=AsyncMock,
                   return_value='{"name": "test", "value": 42}'):
            result = asyncio.run(client._generate_response(
                messages=[Message(role="user", content="hello")],
                response_model=TestModel,
            ))
            assert result == {"name": "test", "value": 42}

    def test_generate_response_strips_code_fences(self):
        from graphiti_core.prompts.models import Message
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str

        client = ClaudeCliLLMClient()
        with patch("src.llm.claude_cli_client._claude_p",
                   new_callable=AsyncMock,
                   return_value='```json\n{"name": "fenced"}\n```'):
            result = asyncio.run(client._generate_response(
                messages=[Message(role="user", content="hello")],
                response_model=TestModel,
            ))
            assert result == {"name": "fenced"}

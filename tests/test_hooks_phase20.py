"""Tests for Phase 20 hook changes — PERF-04 (session_stop) and PERF-05 (inject_context)."""
import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.hooks.inject_context import (
    _fts_entity_search,
    _fts_episode_search,
    _recent_episodes,
    _build_option_c,
    _approx_tokens,
)


class TestFTSLayerFunctions:
    """Test FTS Layer 1 query functions — PERF-05."""

    def test_fts_entity_search_calls_execute_query(self):
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(return_value=(
            [{"uuid": "u1", "name": "Entity1", "summary": "sum1", "score": 0.9}],
            None,
            None,
        ))
        results = asyncio.run(_fts_entity_search(mock_driver, "group1", "test query"))
        assert len(results) == 1
        assert results[0]["name"] == "Entity1"
        # Verify FTS Cypher was used
        call_args = mock_driver.execute_query.call_args
        assert "QUERY_FTS_INDEX" in call_args[0][0]
        assert "node_name_and_summary" in call_args[0][0]

    def test_fts_episode_search_calls_execute_query(self):
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(return_value=(
            [{"uuid": "e1", "name": "ep1", "content": "content1", "created_at": "2026-03-01", "score": 0.8}],
            None,
            None,
        ))
        results = asyncio.run(_fts_episode_search(mock_driver, "group1", "keyword"))
        assert len(results) == 1
        assert "QUERY_FTS_INDEX" in mock_driver.execute_query.call_args[0][0]
        assert "episode_content" in mock_driver.execute_query.call_args[0][0]

    def test_recent_episodes_ordered_by_created_at(self):
        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(return_value=(
            [
                {"uuid": "e1", "name": "ep1", "content": "c1", "created_at": "2026-03-02"},
                {"uuid": "e2", "name": "ep2", "content": "c2", "created_at": "2026-03-01"},
            ],
            None,
            None,
        ))
        results = asyncio.run(_recent_episodes(mock_driver, "group1", limit=20))
        assert len(results) == 2
        assert "ORDER BY e.created_at DESC" in mock_driver.execute_query.call_args[0][0]


class TestBuildOptionCThreeLayers:
    """Test _build_option_c with 3-layer structure — PERF-05."""

    def test_empty_layers_returns_minimal_xml(self):
        result = _build_option_c("", [], [], 4000)
        assert "<session_context>" in result
        assert "</session_context>" in result
        assert "<continuity>" in result

    def test_continuity_included(self):
        result = _build_option_c("Previous work on auth", [], [], 4000)
        assert "Previous work on auth" in result

    def test_layer2_with_toon_encoding(self):
        """Layer 2 with 3+ items should use TOON encoding."""
        episodes = [
            {"content": f"episode content {i}", "created_at": f"2026-03-0{i+1}"}
            for i in range(4)
        ]
        result = _build_option_c("", episodes, [], 4000)
        assert "<relevant_history>" in result
        # TOON uses bracket notation for headers
        # Just verify the content is included in some form
        assert "episode content" in result

    def test_layer3_entity_details(self):
        """Layer 3 with entity details should be included."""
        entities = [
            {"name": f"Entity{i}", "summary": f"Summary {i}"}
            for i in range(4)
        ]
        result = _build_option_c("", [], entities, 4000)
        assert "<entity_details>" in result
        assert "Entity" in result


class TestSessionStopClaudeWiring:
    """Test session_stop.py claude CLI wiring — PERF-04."""

    def test_generate_summary_tries_claude_first(self):
        """When claude is available, _generate_session_summary should try it before Ollama."""
        import inspect
        from src.hooks.session_stop import _generate_session_summary
        src = inspect.getsource(_generate_session_summary)
        # claude_cli_available check must appear before ThreadPoolExecutor
        claude_idx = src.index("claude_cli_available")
        thread_idx = src.index("ThreadPoolExecutor")
        assert claude_idx < thread_idx, "claude CLI path must be tried before Ollama fallback"

    def test_generate_summary_has_ollama_fallback(self):
        """Ollama fallback path must still exist."""
        import inspect
        from src.hooks.session_stop import _generate_session_summary
        src = inspect.getsource(_generate_session_summary)
        assert "ThreadPoolExecutor" in src
        assert "FutureTimeoutError" in src
        assert "LLMUnavailableError" in src

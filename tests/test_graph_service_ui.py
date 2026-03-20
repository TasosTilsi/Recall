"""Tests for new GraphService UI methods (Phase 14).

RED scaffold — all tests fail until Plan 02 adds the 5 new methods to service.py.

Covers: UI-03 (list_episodes, get_episode_detail),
        UI-04 (get_time_series_counts, get_top_connected_entities, get_retention_summary).
"""
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub real_ladybug so service.py can be imported without the native package
# ---------------------------------------------------------------------------
_lb_stub = ModuleType("real_ladybug")
_lb_stub.Database = object
_lb_stub.Connection = object
_lb_stub.AsyncConnection = object
sys.modules.setdefault("real_ladybug", _lb_stub)

from pathlib import Path  # noqa: E402 — must come after sys.modules patch

from src.graph.service import GraphService  # noqa: E402
from src.models import GraphScope  # noqa: E402


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_service(tmp_path):
    """GraphService with mocked driver that returns empty results by default.

    Bypasses __init__ to avoid real DB + LLM client creation. The driver's
    execute_query is an AsyncMock returning ([], None, None) by default.
    """
    service = GraphService.__new__(GraphService)
    service._graph_manager = MagicMock()
    mock_driver = MagicMock()
    mock_driver.execute_query = AsyncMock(return_value=([], None, None))
    service._graph_manager.get_driver.return_value = mock_driver
    # _resolve_db_path returns a path that EXISTS by default
    db_path = tmp_path / "graphiti.lbdb"
    db_path.mkdir()
    service._resolve_db_path = MagicMock(return_value=db_path)
    service._get_group_id = MagicMock(return_value="test-group-id")
    return service, mock_driver


@pytest.fixture
def mock_service_no_db(tmp_path):
    """GraphService where the DB path does NOT exist (empty-result path)."""
    service = GraphService.__new__(GraphService)
    service._graph_manager = MagicMock()
    mock_driver = MagicMock()
    mock_driver.execute_query = AsyncMock(return_value=([], None, None))
    service._graph_manager.get_driver.return_value = mock_driver
    # _resolve_db_path returns a path that does NOT exist
    service._resolve_db_path = MagicMock(return_value=tmp_path / "nonexistent.lbdb")
    service._get_group_id = MagicMock(return_value="test-group-id")
    return service, mock_driver


# ---------------------------------------------------------------------------
# TestListEpisodes
# ---------------------------------------------------------------------------


class TestListEpisodes:
    """Tests for GraphService.list_episodes()."""

    def test_happy_path_returns_episode_list(self, mock_service):
        """list_episodes returns list of dicts with correct keys when driver has data."""
        import asyncio

        service, mock_driver = mock_service
        fake_rows = [
            {
                "uuid": "ep-uuid-1",
                "name": "Session 2026-03-01",
                "source_description": "Claude session",
                "content": "Worked on Phase 12.",
                "created_at": "2026-03-01T10:00:00",
                "source": "message",
            }
        ]
        mock_driver.execute_query = AsyncMock(return_value=(fake_rows, None, None))

        result = asyncio.run(
            service.list_episodes(GraphScope.GLOBAL, None, limit=10)
        )

        assert isinstance(result, list)
        assert len(result) == 1
        row = result[0]
        for key in ("uuid", "name", "source_description", "content", "created_at", "source"):
            assert key in row, f"Missing key: {key}"
        assert row["uuid"] == "ep-uuid-1"
        assert row["name"] == "Session 2026-03-01"

    def test_returns_empty_when_db_not_exist(self, mock_service_no_db):
        """list_episodes returns [] when DB path does not exist."""
        import asyncio

        service, _ = mock_service_no_db
        result = asyncio.run(service.list_episodes(GraphScope.GLOBAL, None))
        assert result == []

    def test_does_not_call_get_graphiti(self, mock_service):
        """list_episodes never calls _get_graphiti()."""
        import asyncio

        service, _ = mock_service
        service._get_graphiti = AsyncMock(side_effect=AssertionError("_get_graphiti must not be called"))
        # Should not raise
        asyncio.run(service.list_episodes(GraphScope.GLOBAL, None))


# ---------------------------------------------------------------------------
# TestGetEpisodeDetail
# ---------------------------------------------------------------------------


class TestGetEpisodeDetail:
    """Tests for GraphService.get_episode_detail()."""

    def test_happy_path_returns_episode_dict(self, mock_service):
        """get_episode_detail returns dict with all episode fields + entities list."""
        import asyncio

        service, mock_driver = mock_service
        ep_row = [
            {
                "uuid": "ep-uuid-42",
                "name": "Episode 42",
                "source_description": "tool call",
                "content": "Long content here.",
                "created_at": "2026-03-10T08:00:00",
                "source": "tool_call",
            }
        ]
        entity_rows = [
            {"uuid": "ent-uuid-1", "name": "GraphService", "tags": ["Component"]}
        ]
        # First call returns episode, second call returns entity mentions
        mock_driver.execute_query = AsyncMock(
            side_effect=[(ep_row, None, None), (entity_rows, None, None)]
        )

        result = asyncio.run(
            service.get_episode_detail("ep-uuid-42", GraphScope.GLOBAL, None)
        )

        assert result is not None
        for key in ("uuid", "name", "source_description", "content", "created_at", "source", "entities"):
            assert key in result, f"Missing key: {key}"
        assert result["uuid"] == "ep-uuid-42"
        assert isinstance(result["entities"], list)
        assert result["entities"][0]["uuid"] == "ent-uuid-1"

    def test_returns_none_when_uuid_not_found(self, mock_service):
        """get_episode_detail returns None when episode UUID not in DB."""
        import asyncio

        service, mock_driver = mock_service
        mock_driver.execute_query = AsyncMock(return_value=([], None, None))

        result = asyncio.run(
            service.get_episode_detail("missing-uuid", GraphScope.GLOBAL, None)
        )
        assert result is None

    def test_returns_none_when_db_not_exist(self, mock_service_no_db):
        """get_episode_detail returns None when DB path does not exist."""
        import asyncio

        service, _ = mock_service_no_db
        result = asyncio.run(
            service.get_episode_detail("any-uuid", GraphScope.GLOBAL, None)
        )
        assert result is None

    def test_does_not_call_get_graphiti(self, mock_service):
        """get_episode_detail never calls _get_graphiti()."""
        import asyncio

        service, mock_driver = mock_service
        service._get_graphiti = AsyncMock(side_effect=AssertionError("_get_graphiti must not be called"))
        mock_driver.execute_query = AsyncMock(return_value=([], None, None))
        asyncio.run(service.get_episode_detail("ep-uuid", GraphScope.GLOBAL, None))


# ---------------------------------------------------------------------------
# TestGetTimeSeriesCounts
# ---------------------------------------------------------------------------


class TestGetTimeSeriesCounts:
    """Tests for GraphService.get_time_series_counts()."""

    def test_happy_path_returns_day_list(self, mock_service):
        """get_time_series_counts returns list of dicts with day/entity_count/edge_count/episode_count."""
        import asyncio

        service, mock_driver = mock_service
        entity_rows = [{"ts": "2026-03-10T08:00:00"}, {"ts": "2026-03-10T09:00:00"}]
        edge_rows = [{"ts": "2026-03-10T10:00:00"}]
        ep_rows = [{"ts": "2026-03-11T08:00:00"}]

        mock_driver.execute_query = AsyncMock(
            side_effect=[
                (entity_rows, None, None),
                (edge_rows, None, None),
                (ep_rows, None, None),
            ]
        )

        result = asyncio.run(
            service.get_time_series_counts(GraphScope.GLOBAL, None, days=30)
        )

        assert isinstance(result, list)
        assert len(result) > 0
        row = result[0]
        for key in ("day", "entity_count", "edge_count", "episode_count"):
            assert key in row, f"Missing key: {key}"
        # day format: YYYY-MM-DD
        assert len(row["day"]) == 10
        assert row["day"][4] == "-"

    def test_returns_empty_when_db_not_exist(self, mock_service_no_db):
        """get_time_series_counts returns [] when DB path does not exist."""
        import asyncio

        service, _ = mock_service_no_db
        result = asyncio.run(service.get_time_series_counts(GraphScope.GLOBAL, None))
        assert result == []

    def test_does_not_call_get_graphiti(self, mock_service):
        """get_time_series_counts never calls _get_graphiti()."""
        import asyncio

        service, mock_driver = mock_service
        service._get_graphiti = AsyncMock(side_effect=AssertionError("_get_graphiti must not be called"))
        mock_driver.execute_query = AsyncMock(return_value=([], None, None))
        asyncio.run(service.get_time_series_counts(GraphScope.GLOBAL, None))


# ---------------------------------------------------------------------------
# TestGetTopConnectedEntities
# ---------------------------------------------------------------------------


class TestGetTopConnectedEntities:
    """Tests for GraphService.get_top_connected_entities()."""

    def test_happy_path_returns_entity_list(self, mock_service):
        """get_top_connected_entities returns list of dicts with uuid/name/edge_count."""
        import asyncio

        service, mock_driver = mock_service
        fake_rows = [
            {"uuid": "ent-1", "name": "Alpha", "edge_count": 15},
            {"uuid": "ent-2", "name": "Beta", "edge_count": 7},
        ]
        mock_driver.execute_query = AsyncMock(return_value=(fake_rows, None, None))

        result = asyncio.run(
            service.get_top_connected_entities(GraphScope.GLOBAL, None, limit=10)
        )

        assert isinstance(result, list)
        assert len(result) == 2
        row = result[0]
        for key in ("uuid", "name", "edge_count"):
            assert key in row, f"Missing key: {key}"
        assert row["edge_count"] == 15
        assert isinstance(row["edge_count"], int)

    def test_returns_empty_when_db_not_exist(self, mock_service_no_db):
        """get_top_connected_entities returns [] when DB path does not exist."""
        import asyncio

        service, _ = mock_service_no_db
        result = asyncio.run(
            service.get_top_connected_entities(GraphScope.GLOBAL, None)
        )
        assert result == []

    def test_does_not_call_get_graphiti(self, mock_service):
        """get_top_connected_entities never calls _get_graphiti()."""
        import asyncio

        service, mock_driver = mock_service
        service._get_graphiti = AsyncMock(side_effect=AssertionError("_get_graphiti must not be called"))
        asyncio.run(service.get_top_connected_entities(GraphScope.GLOBAL, None))


# ---------------------------------------------------------------------------
# TestGetRetentionSummary
# ---------------------------------------------------------------------------


class TestGetRetentionSummary:
    """Tests for GraphService.get_retention_summary()."""

    def test_happy_path_returns_summary_dict(self, mock_service):
        """get_retention_summary returns dict with pinned/normal/stale/archived counts."""
        import asyncio

        service, mock_driver = mock_service
        uuid_rows = [{"uuid": "ent-1"}, {"uuid": "ent-2"}, {"uuid": "ent-3"}]
        mock_driver.execute_query = AsyncMock(return_value=(uuid_rows, None, None))

        with patch("src.retention.get_retention_manager") as mock_rm_getter:
            mock_rm = MagicMock()
            mock_rm.get_pin_state_uuids.return_value = {"ent-1"}
            mock_rm.get_archive_state_uuids.return_value = set()
            mock_rm.get_stale_uuids.return_value = []
            mock_rm_getter.return_value = mock_rm

            result = asyncio.run(
                service.get_retention_summary(GraphScope.GLOBAL, None)
            )

        assert isinstance(result, dict)
        for key in ("pinned", "normal", "stale", "archived"):
            assert key in result, f"Missing key: {key}"
        assert result["pinned"] == 1
        assert result["normal"] == 2
        assert result["stale"] == 0
        assert result["archived"] == 0

    def test_returns_zero_counts_when_db_not_exist(self, mock_service_no_db):
        """get_retention_summary returns all-zero dict when DB path does not exist."""
        import asyncio

        service, _ = mock_service_no_db
        result = asyncio.run(service.get_retention_summary(GraphScope.GLOBAL, None))
        assert result == {"pinned": 0, "normal": 0, "stale": 0, "archived": 0}

    def test_does_not_call_get_graphiti(self, mock_service):
        """get_retention_summary never calls _get_graphiti()."""
        import asyncio

        service, mock_driver = mock_service
        service._get_graphiti = AsyncMock(side_effect=AssertionError("_get_graphiti must not be called"))
        mock_driver.execute_query = AsyncMock(return_value=([], None, None))
        asyncio.run(service.get_retention_summary(GraphScope.GLOBAL, None))

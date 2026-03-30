"""Tests for GraphService retention-aware methods.

Covers:
- list_stale() — excludes pinned, excludes archived, filters by age, sorts by score ascending
- archive_nodes() — calls archive_node for each UUID, returns correct count
- list_entities() — post-filters archived nodes
- list_entities() — graceful fallback when retention DB unavailable
- search() — post-filters archived nodes

All async methods are tested via asyncio.run() (no pytest-asyncio required).

Patching strategy: lazy imports use `from src.retention import get_retention_manager`
inside each method body. Patching `src.retention.get_retention_manager` ensures the
mock is picked up when the lazy import executes.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.service import GraphService
from src.models import GraphScope


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(uuid: str, name: str, days_old: int = 100) -> MagicMock:
    """Return a mock EntityNode-like object."""
    entity = MagicMock()
    entity.uuid = uuid
    entity.name = name
    entity.created_at = datetime.now(timezone.utc) - timedelta(days=days_old)
    entity.labels = []
    entity.summary = f"Summary for {name}"
    return entity


def _make_retention_manager(
    archived: set | None = None,
    pinned: set | None = None,
    access_record: dict | None = None,
) -> MagicMock:
    rm = MagicMock()
    rm.get_archive_state_uuids.return_value = archived or set()
    rm.get_pin_state_uuids.return_value = pinned or set()
    rm.get_access_record.return_value = access_record or {"last_accessed_at": None, "access_count": 0}
    rm.archive_node.return_value = None
    rm.clear_archive.return_value = None
    rm.record_access.return_value = None
    return rm


def _make_service() -> GraphService:
    """Return a GraphService instance bypassing __init__."""
    svc = GraphService.__new__(GraphService)
    svc._graph_manager = MagicMock()
    svc._llm_client = MagicMock()
    svc._embedder = MagicMock()
    svc._cross_encoder = MagicMock()
    svc._graphiti_instances = {}
    return svc


# ---------------------------------------------------------------------------
# list_stale()
# ---------------------------------------------------------------------------

class TestListStale:
    def test_list_stale_excludes_archived_nodes(self):
        """Entities in archive_state are excluded from stale list."""
        service = _make_service()
        entities = [
            _make_entity("uuid-1", "Old Entity", days_old=200),
            _make_entity("uuid-2", "Archived Entity", days_old=200),
        ]
        retention = _make_retention_manager(archived={"uuid-2"})

        graphiti_mock = MagicMock()
        graphiti_mock._driver = MagicMock()

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.graph.service.load_config") as mock_cfg,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=entities)
            mock_cfg.return_value = MagicMock(retention_days=90)
            result = asyncio.run(service.list_stale(scope=GraphScope.GLOBAL, project_root=None))

        uuids = [r["uuid"] for r in result]
        assert "uuid-2" not in uuids, "Archived node must not appear in stale list"
        assert "uuid-1" in uuids

    def test_list_stale_excludes_pinned_nodes(self):
        """Entities in pin_state are excluded from stale list."""
        service = _make_service()
        entities = [
            _make_entity("uuid-1", "Old Entity", days_old=200),
            _make_entity("uuid-pinned", "Pinned Entity", days_old=200),
        ]
        retention = _make_retention_manager(pinned={"uuid-pinned"})

        graphiti_mock = MagicMock()
        graphiti_mock._driver = MagicMock()

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.graph.service.load_config") as mock_cfg,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=entities)
            mock_cfg.return_value = MagicMock(retention_days=90)
            result = asyncio.run(service.list_stale(scope=GraphScope.GLOBAL, project_root=None))

        uuids = [r["uuid"] for r in result]
        assert "uuid-pinned" not in uuids, "Pinned node must not appear in stale list"

    def test_list_stale_only_returns_nodes_older_than_retention_days(self):
        """Nodes younger than retention_days are excluded."""
        service = _make_service()
        entities = [
            _make_entity("uuid-old", "Old Entity", days_old=100),   # older than 90
            _make_entity("uuid-young", "Young Entity", days_old=10),  # younger than 90
        ]
        retention = _make_retention_manager()

        graphiti_mock = MagicMock()
        graphiti_mock._driver = MagicMock()

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.graph.service.load_config") as mock_cfg,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=entities)
            mock_cfg.return_value = MagicMock(retention_days=90)
            result = asyncio.run(service.list_stale(scope=GraphScope.GLOBAL, project_root=None))

        uuids = [r["uuid"] for r in result]
        assert "uuid-old" in uuids
        assert "uuid-young" not in uuids, "Young node must not appear in stale list"

    def test_list_stale_sorts_lowest_score_first(self):
        """Stale results are sorted ascending by score (most stale first)."""
        service = _make_service()
        now = datetime.now(timezone.utc)
        entity_never = _make_entity("uuid-never", "Never Accessed", days_old=200)
        entity_recent = _make_entity("uuid-recent", "Recently Accessed", days_old=200)

        retention = _make_retention_manager()

        def _get_access_record(uuid, scope):
            if uuid == "uuid-recent":
                return {"last_accessed_at": now - timedelta(days=1), "access_count": 5}
            return {"last_accessed_at": None, "access_count": 0}

        retention.get_access_record.side_effect = _get_access_record

        graphiti_mock = MagicMock()
        graphiti_mock._driver = MagicMock()

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.graph.service.load_config") as mock_cfg,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=[entity_never, entity_recent])
            mock_cfg.return_value = MagicMock(retention_days=90)
            result = asyncio.run(service.list_stale(scope=GraphScope.GLOBAL, project_root=None))

        assert len(result) == 2
        assert result[0]["score"] <= result[1]["score"], "Results must be sorted ascending by score"

    def test_list_stale_result_dict_contains_required_keys(self):
        """Each result dict has uuid, name, age_days, score."""
        service = _make_service()
        entities = [_make_entity("uuid-1", "Old One", days_old=150)]
        retention = _make_retention_manager()

        graphiti_mock = MagicMock()
        graphiti_mock._driver = MagicMock()

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.graph.service.load_config") as mock_cfg,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=entities)
            mock_cfg.return_value = MagicMock(retention_days=90)
            result = asyncio.run(service.list_stale(scope=GraphScope.GLOBAL, project_root=None))

        assert len(result) == 1
        item = result[0]
        assert "uuid" in item
        assert "name" in item
        assert "age_days" in item
        assert "score" in item


# ---------------------------------------------------------------------------
# archive_nodes()
# ---------------------------------------------------------------------------

class TestArchiveNodes:
    def test_archive_nodes_calls_archive_node_for_each_uuid(self):
        """archive_nodes calls retention.archive_node for each UUID."""
        service = _make_service()
        retention = _make_retention_manager()
        uuids = ["uuid-1", "uuid-2", "uuid-3"]

        with (
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            count = asyncio.run(
                service.archive_nodes(uuids=uuids, scope=GraphScope.GLOBAL, project_root=None)
            )

        assert count == 3
        assert retention.archive_node.call_count == 3
        # Collect called UUIDs (supporting both positional and keyword args)
        called_uuids = []
        for call in retention.archive_node.call_args_list:
            u = call.kwargs.get("uuid") if call.kwargs.get("uuid") else call.args[0]
            called_uuids.append(u)
        for u in uuids:
            assert u in called_uuids

    def test_archive_nodes_returns_correct_count(self):
        """archive_nodes returns the count of archived nodes."""
        service = _make_service()
        retention = _make_retention_manager()

        with (
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            count = asyncio.run(
                service.archive_nodes(uuids=["a", "b"], scope=GraphScope.GLOBAL, project_root=None)
            )

        assert count == 2

    def test_archive_nodes_empty_list_returns_zero(self):
        """archive_nodes with empty list returns 0."""
        service = _make_service()
        retention = _make_retention_manager()

        with (
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            count = asyncio.run(
                service.archive_nodes(uuids=[], scope=GraphScope.GLOBAL, project_root=None)
            )

        assert count == 0
        retention.archive_node.assert_not_called()


# ---------------------------------------------------------------------------
# list_entities() archived filtering
# ---------------------------------------------------------------------------

class TestListEntitiesArchiveFilter:
    def test_list_entities_filters_archived_uuid(self):
        """list_entities does not return entities whose UUID is in archive_state."""
        service = _make_service()
        entities = [
            _make_entity("uuid-visible", "Visible Entity", days_old=10),
            _make_entity("uuid-archived", "Archived Entity", days_old=10),
        ]

        graphiti_mock = MagicMock()
        graphiti_mock.driver = MagicMock()
        graphiti_mock.driver.execute_query = AsyncMock(return_value=([{"rel_count": 0}], None, None))

        retention = _make_retention_manager(archived={"uuid-archived"})

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=entities)
            result = asyncio.run(service.list_entities(scope=GraphScope.GLOBAL, project_root=None))

        names = [r["name"] for r in result]
        assert "Archived Entity" not in names
        assert "Visible Entity" in names

    def test_list_entities_returns_unfiltered_when_retention_unavailable(self):
        """list_entities returns full list (no crash) when retention DB raises exception."""
        service = _make_service()
        entities = [_make_entity("uuid-1", "Entity One", days_old=10)]

        graphiti_mock = MagicMock()
        graphiti_mock.driver = MagicMock()
        graphiti_mock.driver.execute_query = AsyncMock(return_value=([{"rel_count": 0}], None, None))

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.retention.get_retention_manager", side_effect=Exception("DB unavailable")),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=entities)
            # Must not raise
            result = asyncio.run(service.list_entities(scope=GraphScope.GLOBAL, project_root=None))

        assert len(result) == 1
        assert result[0]["name"] == "Entity One"


# ---------------------------------------------------------------------------
# search() archived filtering
# ---------------------------------------------------------------------------

class TestSearchArchiveFilter:
    def test_search_filters_archived_uuid(self):
        """search does not return results whose uuid is in archive_state."""
        service = _make_service()

        edge1 = MagicMock()
        edge1.fact = "fact1"
        edge1.name = "edge1"
        edge1.created_at = datetime.now(timezone.utc)
        edge1.uuid = "uuid-visible"

        edge2 = MagicMock()
        edge2.fact = "fact2"
        edge2.name = "edge2"
        edge2.created_at = datetime.now(timezone.utc)
        edge2.uuid = "uuid-archived"

        graphiti_mock = MagicMock()
        graphiti_mock.search = AsyncMock(return_value=[edge1, edge2])

        retention = _make_retention_manager(archived={"uuid-archived"})

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            result = asyncio.run(
                service.search(query="test", scope=GraphScope.GLOBAL, project_root=None)
            )

        names = [r["name"] for r in result]
        assert "edge2" not in names
        assert "edge1" in names

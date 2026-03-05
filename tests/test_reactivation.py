"""Tests for GraphService.add() reactivation of archived nodes.

When graphiti-core resolves a new episode to a previously archived entity,
the entity should be removed from archive_state and become visible again.

Covers:
- add() calls get_archive_state_uuids; when no archived UUIDs, skips entity query (fast path)
- add() when archived UUID matches a current entity: clear_archive is called for that UUID
- add() when archived UUID does NOT match any current entity: clear_archive is NOT called
- add() when reactivation block raises exception: add() still returns successfully

All async methods tested via asyncio.run() (no pytest-asyncio required).
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from src.graph.service import GraphService
from src.models import GraphScope


def _make_service() -> GraphService:
    """Return a GraphService instance bypassing __init__."""
    svc = GraphService.__new__(GraphService)
    svc._graph_manager = MagicMock()
    svc._llm_client = MagicMock()
    svc._embedder = MagicMock()
    svc._cross_encoder = MagicMock()
    svc._graphiti_instances = {}
    return svc


def _make_retention_manager(
    archived: set | None = None,
) -> MagicMock:
    rm = MagicMock()
    rm.get_archive_state_uuids.return_value = archived or set()
    rm.clear_archive.return_value = None
    return rm


def _make_entity(uuid: str, name: str) -> MagicMock:
    entity = MagicMock()
    entity.uuid = uuid
    entity.name = name
    return entity


def _make_graphiti_mock() -> MagicMock:
    """Return a mock Graphiti instance with add_episode patched."""
    g = MagicMock()
    g._driver = MagicMock()
    g.add_episode = AsyncMock(return_value=None)
    return g


# ---------------------------------------------------------------------------
# Reactivation fast path
# ---------------------------------------------------------------------------

class TestReactivationFastPath:
    def test_add_skips_entity_query_when_no_archived_uuids(self):
        """When archive_state is empty, EntityNode.get_by_group_ids is NOT called."""
        service = _make_service()
        retention = _make_retention_manager(archived=set())
        graphiti_mock = _make_graphiti_mock()

        with (
            patch.object(service, "_get_graphiti", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=[])
            asyncio.run(
                service.add(
                    content="Hello world",
                    scope=GraphScope.GLOBAL,
                    project_root=None,
                )
            )

        # Fast path: entity query must NOT be called
        MockEntityNode.get_by_group_ids.assert_not_called()

    def test_add_does_not_call_clear_archive_when_no_archived_uuids(self):
        """When archive_state is empty, clear_archive is never called."""
        service = _make_service()
        retention = _make_retention_manager(archived=set())
        graphiti_mock = _make_graphiti_mock()

        with (
            patch.object(service, "_get_graphiti", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=[])
            asyncio.run(
                service.add(
                    content="Hello world",
                    scope=GraphScope.GLOBAL,
                    project_root=None,
                )
            )

        retention.clear_archive.assert_not_called()


# ---------------------------------------------------------------------------
# Reactivation when archived entity is matched
# ---------------------------------------------------------------------------

class TestReactivationMatch:
    def test_add_calls_clear_archive_for_matching_archived_entity(self):
        """When a current entity UUID matches an archived UUID, clear_archive is called."""
        service = _make_service()
        retained_uuid = "uuid-archived-123"
        retention = _make_retention_manager(archived={retained_uuid})
        graphiti_mock = _make_graphiti_mock()

        current_entities = [
            _make_entity(retained_uuid, "Reactivated Entity"),
            _make_entity("uuid-other", "Other Entity"),
        ]

        with (
            patch.object(service, "_get_graphiti", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=current_entities)
            asyncio.run(
                service.add(
                    content="New info about reactivated entity",
                    scope=GraphScope.GLOBAL,
                    project_root=None,
                )
            )

        retention.clear_archive.assert_called_once()
        call_kwargs = retention.clear_archive.call_args
        args = call_kwargs.args
        kwargs = call_kwargs.kwargs
        called_uuid = kwargs.get("uuid") or args[0]
        assert called_uuid == retained_uuid

    def test_add_does_not_call_clear_archive_for_non_matching_archived_entity(self):
        """When archived UUID is NOT in current entities, clear_archive is NOT called."""
        service = _make_service()
        archived_uuid = "uuid-not-in-graph"
        retention = _make_retention_manager(archived={archived_uuid})
        graphiti_mock = _make_graphiti_mock()

        current_entities = [
            _make_entity("uuid-present-1", "Entity One"),
            _make_entity("uuid-present-2", "Entity Two"),
        ]

        with (
            patch.object(service, "_get_graphiti", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=current_entities)
            asyncio.run(
                service.add(
                    content="Some new content",
                    scope=GraphScope.GLOBAL,
                    project_root=None,
                )
            )

        retention.clear_archive.assert_not_called()


# ---------------------------------------------------------------------------
# Reactivation exception isolation
# ---------------------------------------------------------------------------

class TestReactivationExceptionIsolation:
    def test_add_returns_successfully_when_reactivation_block_raises(self):
        """add() returns a result dict even if the reactivation block raises an exception."""
        service = _make_service()
        graphiti_mock = _make_graphiti_mock()

        # Make get_archive_state_uuids raise to simulate DB failure
        retention = _make_retention_manager()
        retention.get_archive_state_uuids.side_effect = Exception("Retention DB failed")

        with (
            patch.object(service, "_get_graphiti", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.graph.service.EntityNode") as MockEntityNode,
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            MockEntityNode.get_by_group_ids = AsyncMock(return_value=[])
            # Must not raise — add() must return normally
            result = asyncio.run(
                service.add(
                    content="Content to add",
                    scope=GraphScope.GLOBAL,
                    project_root=None,
                )
            )

        assert isinstance(result, dict)
        assert "name" in result

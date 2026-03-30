"""Tests for GraphService.record_access() and get_entity() access instrumentation.

Covers:
- record_access() calls retention.record_access with correct scope_key
- record_access() exception in retention does not propagate to caller
- get_entity() calls record_access for each entity found
- get_entity() when no entities found: record_access is NOT called

All async methods tested via asyncio.run() (no pytest-asyncio required).
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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


def _make_retention_manager() -> MagicMock:
    rm = MagicMock()
    rm.record_access.return_value = None
    return rm


# ---------------------------------------------------------------------------
# record_access()
# ---------------------------------------------------------------------------

class TestRecordAccess:
    def test_record_access_calls_retention_with_correct_scope_key(self):
        """record_access passes correct uuid and scope_key to retention.record_access."""
        service = _make_service()
        retention = _make_retention_manager()

        with (
            patch.object(service, "_get_group_id", return_value="my-project"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            asyncio.run(
                service.record_access(
                    uuid="uuid-123",
                    scope=GraphScope.PROJECT,
                    project_root=None,
                )
            )

        retention.record_access.assert_called_once()
        call_kwargs = retention.record_access.call_args
        # Accept both positional and keyword calls
        args = call_kwargs.args
        kwargs = call_kwargs.kwargs
        called_uuid = kwargs.get("uuid") or args[0]
        called_scope = kwargs.get("scope") or args[1]
        assert called_uuid == "uuid-123"
        assert called_scope == "my-project"

    def test_record_access_exception_does_not_propagate(self):
        """If retention.record_access raises, the exception is swallowed."""
        service = _make_service()
        retention = _make_retention_manager()
        retention.record_access.side_effect = Exception("DB locked")

        with (
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            # Must not raise
            asyncio.run(
                service.record_access(uuid="uuid-x", scope=GraphScope.GLOBAL, project_root=None)
            )

    def test_record_access_global_scope_uses_global_scope_key(self):
        """record_access for GLOBAL scope uses 'global' as scope_key."""
        service = _make_service()
        retention = _make_retention_manager()

        with (
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            asyncio.run(
                service.record_access(uuid="uuid-abc", scope=GraphScope.GLOBAL, project_root=None)
            )

        call_kwargs = retention.record_access.call_args
        kwargs = call_kwargs.kwargs
        args = call_kwargs.args
        called_scope = kwargs.get("scope") or args[1]
        assert called_scope == "global"


# ---------------------------------------------------------------------------
# get_entity() access instrumentation
# ---------------------------------------------------------------------------

class TestGetEntityRecordAccess:
    def _make_driver_mock(self, entity_records: list, edge_records: list | None = None) -> MagicMock:
        """Build a driver mock that returns entity_records on first call, edge records on subsequent calls."""
        driver = MagicMock()
        call_count = {"n": 0}
        edge_records = edge_records or []

        async def execute_query(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return (entity_records, None, None)
            # Outgoing and incoming relationship queries
            return (edge_records, None, None)

        driver.execute_query = execute_query
        return driver

    def test_get_entity_calls_record_access_when_entity_found(self):
        """get_entity records access for each matched entity UUID."""
        service = _make_service()
        retention = _make_retention_manager()

        entity_record = {
            "uuid": "uuid-found",
            "name": "Test Entity",
            "group_id": "global",
            "labels": [],
            "created_at": datetime.now(timezone.utc),
            "summary": "A summary",
            "attributes": None,
        }
        driver = self._make_driver_mock(entity_records=[entity_record])

        graphiti_mock = MagicMock()
        graphiti_mock.driver = driver

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            result = asyncio.run(
                service.get_entity(name="Test Entity", scope=GraphScope.GLOBAL, project_root=None)
            )

        assert result is not None
        retention.record_access.assert_called_once()
        call_kwargs = retention.record_access.call_args
        args = call_kwargs.args
        kwargs = call_kwargs.kwargs
        called_uuid = kwargs.get("uuid") or args[0]
        assert called_uuid == "uuid-found"

    def test_get_entity_does_not_call_record_access_when_not_found(self):
        """get_entity does not call record_access when no entity is found."""
        service = _make_service()
        retention = _make_retention_manager()

        driver = self._make_driver_mock(entity_records=[])

        graphiti_mock = MagicMock()
        graphiti_mock.driver = driver

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            result = asyncio.run(
                service.get_entity(name="Nonexistent", scope=GraphScope.GLOBAL, project_root=None)
            )

        assert result is None
        retention.record_access.assert_not_called()

    def test_get_entity_record_access_exception_does_not_propagate(self):
        """get_entity returns the entity even if record_access raises."""
        service = _make_service()
        retention = _make_retention_manager()
        retention.record_access.side_effect = Exception("DB error")

        entity_record = {
            "uuid": "uuid-found",
            "name": "Test Entity",
            "group_id": "global",
            "labels": [],
            "created_at": datetime.now(timezone.utc),
            "summary": None,
            "attributes": None,
        }
        driver = self._make_driver_mock(entity_records=[entity_record])

        graphiti_mock = MagicMock()
        graphiti_mock.driver = driver

        with (
            patch.object(service, "_get_recall_instance", new_callable=AsyncMock, return_value=graphiti_mock),
            patch.object(service, "_get_group_id", return_value="global"),
            patch("src.retention.get_retention_manager", return_value=retention),
        ):
            # Must not raise — get_entity should still return the entity
            result = asyncio.run(
                service.get_entity(name="Test Entity", scope=GraphScope.GLOBAL, project_root=None)
            )

        assert result is not None
        assert result["name"] == "Test Entity"

"""Phase 19 integration tests — retention_status end-to-end pipeline.

Tests the full path: list_entities_readonly() -> /api/graph -> node shape
with mocked RetentionManager returning specific pin/archive states.

Covers: UI-03 requirement — retention_status field flows from service through
API to frontend node shape; archived entities remain in response; priority order
(Pinned > Archived > Stale > Normal); graceful fallback on exception.
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entity(uuid: str, name: str, retention_status: str = "Normal") -> dict:
    """Return a minimal entity dict matching list_entities_readonly() shape."""
    return {
        "uuid": uuid,
        "name": name,
        "tags": ["Entity"],
        "scope": "project",
        "summary": "",
        "created_at": None,
        "retention_status": retention_status,
    }


def _make_app_with_entities(entities: list[dict]):
    """Create a FastAPI TestClient with a mocked GraphService returning given entities."""
    from fastapi.testclient import TestClient
    from src.ui_server.app import create_app

    with patch("src.ui_server.app.GraphService") as mock_cls:
        mock_svc = MagicMock()
        mock_svc.list_entities_readonly = AsyncMock(return_value=entities)
        mock_svc.list_edges = AsyncMock(return_value=[])
        mock_svc.list_episodes = AsyncMock(return_value=[])
        mock_svc.get_time_series_counts = AsyncMock(return_value=[])
        mock_svc.get_top_connected_entities = AsyncMock(return_value=[])
        mock_svc.get_retention_summary = AsyncMock(
            return_value={"pinned": 0, "normal": 0, "stale": 0, "archived": 0}
        )
        mock_cls.return_value = mock_svc
        app = create_app(scope_label="project", static_dir=None)
        client = TestClient(app)
        yield client


# ---------------------------------------------------------------------------
# Test 1: All four statuses present in /api/graph
# ---------------------------------------------------------------------------


class TestApiGraphRetentionStatus:
    """GET /api/graph — retention_status on all nodes."""

    def test_api_graph_returns_retention_status_for_all_nodes(self):
        """Every node in /api/graph response has a retention_status field with correct value."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app

        entities = [
            _make_entity("uuid-pinned", "PinnedThing", "Pinned"),
            _make_entity("uuid-archived", "ArchivedThing", "Archived"),
            _make_entity("uuid-stale", "StaleThing", "Stale"),
            _make_entity("uuid-normal", "NormalThing", "Normal"),
        ]

        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=entities)
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/graph")

        assert resp.status_code == 200
        nodes = resp.json()["nodes"]
        assert len(nodes) == 4

        node_by_id = {n["id"]: n for n in nodes}
        assert node_by_id["uuid-pinned"]["retention_status"] == "Pinned"
        assert node_by_id["uuid-archived"]["retention_status"] == "Archived"
        assert node_by_id["uuid-stale"]["retention_status"] == "Stale"
        assert node_by_id["uuid-normal"]["retention_status"] == "Normal"

        # All nodes must have the field
        for node in nodes:
            assert "retention_status" in node, f"Node {node['id']} missing retention_status"

    # ---------------------------------------------------------------------------
    # Test 2: Archived entities are present (not excluded)
    # ---------------------------------------------------------------------------

    def test_api_graph_archived_entities_present(self):
        """Archived entities are NOT filtered out of /api/graph — they appear with retention_status='Archived'."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app

        archived_entity = _make_entity("uuid-archived-2", "OldDecision", "Archived")

        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=[archived_entity])
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/graph")

        assert resp.status_code == 200
        nodes = resp.json()["nodes"]
        assert len(nodes) == 1, "Archived entity must be included in /api/graph response"
        assert nodes[0]["id"] == "uuid-archived-2"
        assert nodes[0]["retention_status"] == "Archived"


# ---------------------------------------------------------------------------
# Test 3: Priority — Pinned wins over Archived
# ---------------------------------------------------------------------------


class TestRetentionStatusPriority:
    """retention_status priority: Pinned > Archived > Stale > Normal."""

    def test_retention_status_priority_pinned_over_archived(self):
        """If service returns retention_status='Pinned', node gets 'Pinned' (pinned wins over archived)."""
        import asyncio
        from pathlib import Path

        from src.graph.service import GraphService
        from src.models import GraphScope

        service = GraphService.__new__(GraphService)
        service._graph_manager = MagicMock()
        mock_driver = MagicMock()

        # Entity row from DB (no retention_status at this stage)
        fake_rows = [{
            "uuid": "both-pinned-and-archived",
            "name": "ComplexEntity",
            "tags": ["Decision"],
            "summary": "",
            "created_at": None,
        }]
        mock_driver.execute_query = AsyncMock(return_value=(fake_rows, None, None))
        service._graph_manager.get_driver.return_value = mock_driver

        # Create a real tmp db path
        import tempfile, os
        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "graphiti.lbdb"
        db_path.mkdir()
        service._resolve_db_path = MagicMock(return_value=db_path)
        service._get_group_id = MagicMock(return_value="test-group")

        # Mock retention: entity is BOTH pinned AND archived
        mock_retention = MagicMock()
        mock_retention.get_pin_state_uuids.return_value = {"both-pinned-and-archived"}
        mock_retention.get_archive_state_uuids.return_value = {"both-pinned-and-archived"}
        mock_retention.get_stale_uuids.return_value = set()

        with patch("src.graph.service.get_retention_manager", return_value=mock_retention):
            result = asyncio.run(
                service.list_entities_readonly(GraphScope.PROJECT, Path(tmpdir))
            )

        assert len(result) == 1
        # Pinned takes priority over Archived
        assert result[0]["retention_status"] == "Pinned", (
            f"Expected 'Pinned' (pinned wins), got '{result[0]['retention_status']}'"
        )


# ---------------------------------------------------------------------------
# Test 4: Fallback on exception — all entities get "Normal"
# ---------------------------------------------------------------------------


class TestRetentionStatusFallback:
    """retention_status defaults to 'Normal' when retention manager raises."""

    def test_retention_status_fallback_on_exception(self):
        """When get_retention_manager raises, all entities get retention_status='Normal'."""
        import asyncio
        import tempfile
        from pathlib import Path

        from src.graph.service import GraphService
        from src.models import GraphScope

        service = GraphService.__new__(GraphService)
        service._graph_manager = MagicMock()
        mock_driver = MagicMock()

        fake_rows = [
            {"uuid": "e1", "name": "Entity1", "tags": ["T"], "summary": "", "created_at": None},
            {"uuid": "e2", "name": "Entity2", "tags": ["T"], "summary": "", "created_at": None},
        ]
        mock_driver.execute_query = AsyncMock(return_value=(fake_rows, None, None))
        service._graph_manager.get_driver.return_value = mock_driver

        tmpdir = tempfile.mkdtemp()
        db_path = Path(tmpdir) / "graphiti.lbdb"
        db_path.mkdir()
        service._resolve_db_path = MagicMock(return_value=db_path)
        service._get_group_id = MagicMock(return_value="test-group")

        with patch("src.graph.service.get_retention_manager", side_effect=RuntimeError("DB unavailable")):
            result = asyncio.run(
                service.list_entities_readonly(GraphScope.PROJECT, Path(tmpdir))
            )

        assert len(result) == 2
        for entity in result:
            assert entity.get("retention_status") == "Normal", (
                f"Entity {entity['uuid']} should be 'Normal' on fallback, got '{entity.get('retention_status')}'"
            )


# ---------------------------------------------------------------------------
# Test 5: Dashboard endpoint unaffected by retention_status
# ---------------------------------------------------------------------------


class TestDashboardUnaffectedByRetentionStatus:
    """GET /api/dashboard — additive retention_status field doesn't break dashboard."""

    def test_dashboard_unaffected_by_retention_status(self):
        """GET /api/dashboard returns 200 even when entities have retention_status field."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app

        entities = [
            _make_entity("uuid-p", "PinnedEntity", "Pinned"),
            _make_entity("uuid-n", "NormalEntity", "Normal"),
        ]

        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=entities)
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_svc.list_episodes = AsyncMock(return_value=[])
            mock_svc.get_time_series_counts = AsyncMock(return_value=[])
            mock_svc.get_top_connected_entities = AsyncMock(return_value=[])
            mock_svc.get_retention_summary = AsyncMock(
                return_value={"pinned": 1, "normal": 1, "stale": 0, "archived": 0}
            )
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/dashboard")

        assert resp.status_code == 200
        data = resp.json()
        # Dashboard structure is intact
        assert "counts" in data
        assert "retention" in data
        # retention_status on entities is additive — dashboard ignores unknown keys
        assert data["counts"]["entities"] == 2

"""Tests for the FastAPI UI server (Phase 14 — 4-endpoint API).

Covers: UI-01 (routes exist and return correct shape), UI-02 (scope param works),
UI-03 (retention in entity detail), UI-04 (no direct kuzu/graphiti calls).
"""
import sys
import textwrap
from pathlib import Path
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


class TestGraphEndpoint:
    """GET /api/graph — lean nodes + edges for Sigma.js."""

    def test_graph_returns_nodes_and_edges(self):
        """GET /api/graph returns {nodes, edges} with correct keys."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=[])
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data  # NOT "links"
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_graph_node_shape(self):
        """Graph node has id, label, type, scope fields."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=[{
                "uuid": "abc123", "name": "MyEntity", "tags": ["Decision"],
                "scope": "project", "summary": "", "created_at": None,
            }])
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/graph")
        node = resp.json()["nodes"][0]
        assert node["id"] == "abc123"
        assert node["label"] == "MyEntity"
        assert node["type"] == "Decision"

    def test_graph_scope_param(self):
        """?scope=global routes to global scope."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=[])
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/graph?scope=global")
        assert resp.status_code == 200

    def test_graph_node_shape_includes_retention_status(self):
        """Graph node dict includes retention_status field."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=[
                {"uuid": "u1", "name": "E1", "tags": ["Decision"], "scope": "project", "retention_status": "Pinned"},
            ])
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/graph")
        node = resp.json()["nodes"][0]
        assert "retention_status" in node
        assert node["retention_status"] == "Pinned"


class TestDashboardEndpoint:
    """GET /api/dashboard — all chart data."""

    def test_dashboard_returns_all_keys(self):
        """GET /api/dashboard returns counts, time_series, top_entities, sources, entity_types, retention, recent_episodes."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=[])
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_svc.list_episodes = AsyncMock(return_value=[])
            mock_svc.get_time_series_counts = AsyncMock(return_value=[])
            mock_svc.get_top_connected_entities = AsyncMock(return_value=[])
            mock_svc.get_retention_summary = AsyncMock(return_value={"pinned": 0, "normal": 0, "stale": 0, "archived": 0})
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "counts" in data
        assert "time_series" in data
        assert "top_entities" in data
        assert "sources" in data
        assert "retention" in data
        assert "recent_episodes" in data

    def test_dashboard_counts_shape(self):
        """counts dict has entities, edges, episodes, deltas keys."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=[{"uuid": "x", "tags": ["T"], "created_at": None}])
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_svc.list_episodes = AsyncMock(return_value=[])
            mock_svc.get_time_series_counts = AsyncMock(return_value=[])
            mock_svc.get_top_connected_entities = AsyncMock(return_value=[])
            mock_svc.get_retention_summary = AsyncMock(return_value={"pinned": 0, "normal": 1, "stale": 0, "archived": 0})
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/dashboard")
        counts = resp.json()["counts"]
        assert "entities" in counts
        assert "edges" in counts
        assert "episodes" in counts
        assert "deltas" in counts


class TestDetailEndpoint:
    """GET /api/detail/:type/:id — full record."""

    def test_entity_detail_returns_correct_shape(self):
        """GET /api/detail/entity/{uuid} returns entity with uuid and name."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.get_entity_by_uuid = AsyncMock(return_value={
                "uuid": "test-uuid-123", "name": "TestEntity", "tags": ["Decision"], "summary": ""
            })
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/detail/entity/test-uuid-123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["uuid"] == "test-uuid-123"
        assert data["name"] == "TestEntity"

    def test_entity_detail_404_when_not_found(self):
        """GET /api/detail/entity/{uuid} returns 404 when entity missing."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.get_entity_by_uuid = AsyncMock(return_value=None)
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/detail/entity/nonexistent")
        assert resp.status_code == 404

    def test_episode_detail_returns_correct_shape(self):
        """GET /api/detail/episode/{uuid} returns episode with uuid and content."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.get_episode_detail = AsyncMock(return_value={
                "uuid": "ep-001", "name": "test-ep", "content": "some content",
                "source_description": "cli", "created_at": None, "source": "cli-add", "entities": []
            })
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/detail/episode/ep-001")
        assert resp.status_code == 200
        assert resp.json()["uuid"] == "ep-001"

    def test_unknown_type_returns_400(self):
        """GET /api/detail/unknown/{id} returns 400."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService"):
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/detail/unknown/123")
        assert resp.status_code == 400


class TestSearchEndpoint:
    """GET /api/search — unified search results."""

    def test_search_returns_grouped_results(self):
        """GET /api/search?q=test returns entities, relations, episodes keys."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_svc.list_entities_readonly = AsyncMock(return_value=[])
            mock_svc.list_edges = AsyncMock(return_value=[])
            mock_svc.list_episodes = AsyncMock(return_value=[])
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/search?q=test")
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert "relations" in data
        assert "episodes" in data

    def test_search_empty_query_returns_empty(self):
        """GET /api/search without q returns empty lists."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_svc = MagicMock()
            mock_cls.return_value = mock_svc
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/search?q=")
        assert resp.status_code == 200
        assert resp.json()["entities"] == []


class TestNoDirectKuzu:
    """UI-04: routes.py must not call the graphiti write path or import kuzu."""

    def test_routes_do_not_import_kuzu(self):
        """routes.py source does not contain 'import kuzu'."""
        import inspect
        import src.ui_server.routes as routes_module
        source = inspect.getsource(routes_module)
        assert "import kuzu" not in source

    def test_old_nodes_endpoint_does_not_exist(self):
        """GET /api/nodes/{uuid} returns 404 (old endpoint removed)."""
        from fastapi.testclient import TestClient
        from src.ui_server.app import create_app
        with patch("src.ui_server.app.GraphService") as mock_cls:
            mock_cls.return_value = MagicMock()
            app = create_app(scope_label="project", static_dir=None)
            resp = TestClient(app).get("/api/nodes/test-uuid")
        assert resp.status_code == 404


class TestAppFactory:
    """Tests for the create_app factory function."""

    def test_static_mount(self, tmp_path: Path):
        """create_app with a static_dir mounts StaticFiles at '/'."""
        from starlette.routing import Mount
        from src.ui_server.app import create_app
        (tmp_path / "index.html").write_text("<html><body>test</body></html>")
        app = create_app(scope_label="project", static_dir=tmp_path)
        mount_paths = [route.path for route in app.routes if isinstance(route, Mount)]
        assert "/" in mount_paths


class TestLLMConfigUI:
    """Tests for the [ui] section in LLMConfig / load_config()."""

    def test_ui_ports_from_toml(self, tmp_path: Path):
        """load_config() reads [ui] port from TOML file; api_port is backward-compat alias."""
        from src.llm.config import load_config

        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [ui]
            port = 9999
        """))

        config = load_config(config_path=config_file)

        assert config.ui_port == 9999
        assert not hasattr(config, "ui_api_port")  # removed in Phase 14-01

    def test_ui_port_backward_compat_api_port(self, tmp_path: Path):
        """load_config() maps old [ui] api_port -> ui_port for backward compat."""
        from src.llm.config import load_config

        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [ui]
            api_port = 8888
        """))

        config = load_config(config_path=config_file)
        assert config.ui_port == 8888

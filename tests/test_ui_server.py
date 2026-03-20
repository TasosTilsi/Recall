"""Tests for the FastAPI UI server and config extension.

RED scaffold (Plan 11-01) — all 4 tests fail with ImportError or AttributeError
until Plan 11-02 creates `src/ui_server/app.py` and Plan 11-02 extends LLMConfig.

Covers: UI-01 (FastAPI routes), UI-02 (port config from TOML).
"""
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestAPIRoutes:
    """Tests for the FastAPI graph data endpoints."""

    def test_graph_endpoint(self):
        """GET /api/graph returns JSON with 'nodes' and 'links' keys."""
        from fastapi.testclient import TestClient

        from src.ui_server.app import create_app  # noqa: F401 — intentional RED

        with patch("src.ui_server.app.GraphService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.list_entities.return_value = []
            mock_service.list_edges.return_value = []
            mock_service_cls.return_value = mock_service

            app = create_app(scope_label="project", static_dir=None)
            client = TestClient(app)
            response = client.get("/api/graph")

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "links" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["links"], list)

    def test_node_detail_endpoint(self):
        """GET /api/nodes/{uuid} returns JSON with 'id', 'name', 'entityType' keys."""
        from fastapi.testclient import TestClient

        from src.ui_server.app import create_app  # noqa: F401 — intentional RED

        with patch("src.ui_server.app.GraphService") as mock_service_cls:
            mock_service = MagicMock()
            mock_service.get_entity.return_value = {
                "uuid": "test-uuid-123",
                "name": "TestEntity",
                "labels": ["Decision"],
                "summary": "A test entity summary.",
            }
            mock_service_cls.return_value = mock_service

            app = create_app(scope_label="project", static_dir=None)
            client = TestClient(app)
            response = client.get("/api/nodes/test-uuid-123")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "name" in data
        assert "entityType" in data

    def test_node_detail_retention_fields(self):
        """GET /api/nodes/{uuid} returns retention metadata from get_access_record() + is_pinned().

        Regression test for INT-01: routes.py previously called nonexistent
        get_node_metadata() — retention fields were always pinned=False,
        accessCount=0, lastAccessedAt=''.
        """
        from fastapi.testclient import TestClient

        from src.ui_server.app import create_app

        mock_retention = MagicMock()
        mock_retention.get_access_record.return_value = {
            "last_accessed_at": "2026-01-15T10:00:00",
            "access_count": 42,
        }
        mock_retention.is_pinned.return_value = True

        with (
            patch("src.ui_server.app.GraphService") as mock_service_cls,
            patch("src.retention.get_retention_manager", return_value=mock_retention),
        ):
            mock_service = MagicMock()
            mock_service.get_entity_by_uuid.return_value = {
                "uuid": "test-uuid-456",
                "name": "PinnedEntity",
                "labels": ["Decision"],
                "summary": "An important decision.",
            }
            mock_service._get_group_id.return_value = "test-group"
            mock_service_cls.return_value = mock_service

            app = create_app(scope_label="project", static_dir=None)
            client = TestClient(app)
            response = client.get("/api/nodes/test-uuid-456")

        assert response.status_code == 200
        data = response.json()
        assert data["pinned"] is True
        assert data["accessCount"] == 42
        assert data["lastAccessedAt"] == "2026-01-15T10:00:00"


class TestAppFactory:
    """Tests for the create_app factory function."""

    def test_static_mount(self, tmp_path: Path):
        """create_app with a static_dir mounts StaticFiles at '/'."""
        from starlette.routing import Mount

        from src.ui_server.app import create_app  # noqa: F401 — intentional RED

        # Create a minimal index.html so StaticFiles has something to serve
        (tmp_path / "index.html").write_text("<html><body>test</body></html>")

        app = create_app(scope_label="project", static_dir=tmp_path)

        # The app must have a Mount route at "/" serving static files
        mount_paths = [
            route.path
            for route in app.routes
            if isinstance(route, Mount)
        ]
        assert "/" in mount_paths


class TestLLMConfigUI:
    """Tests for the [ui] section in LLMConfig / load_config()."""

    def test_ui_ports_from_toml(self, tmp_path: Path):
        """load_config() reads [ui] port from TOML file; api_port is backward-compat alias."""
        from src.llm.config import load_config

        # Test new single [ui] port field
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
        # api_port in old config files maps to ui_port
        assert config.ui_port == 8888

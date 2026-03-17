"""
Persistence and isolation tests for dual-scope Ladybug storage.

These tests verify Phase 1 success criteria:
1. Data persists across GraphManager close/reopen
2. Global and project graphs are isolated
3. Both graphs can be accessed simultaneously
"""
import tempfile
import shutil
from pathlib import Path
import pytest
from src.storage import GraphSelector, GraphManager
from src.models import GraphScope
from src.config import GLOBAL_DB_PATH


class TestGraphSelector:
    """Tests for GraphSelector scope routing."""

    def test_find_project_root_in_git_repo(self, tmp_path):
        """Should find .git directory when present."""
        # Create fake git repo
        (tmp_path / ".git").mkdir()
        subdir = tmp_path / "src" / "nested"
        subdir.mkdir(parents=True)

        # Should find root from nested directory
        root = GraphSelector.find_project_root(subdir)
        assert root == tmp_path

    def test_find_project_root_not_in_git_repo(self, tmp_path):
        """Should return None when .git not found."""
        root = GraphSelector.find_project_root(tmp_path)
        assert root is None

    def test_determine_scope_preference_always_global(self, tmp_path):
        """Preferences should always use global scope."""
        (tmp_path / ".git").mkdir()

        scope, path = GraphSelector.determine_scope(
            operation_type="preference",
            start_path=tmp_path
        )

        assert scope == GraphScope.GLOBAL
        assert path is None

    def test_determine_scope_project_when_available(self, tmp_path):
        """Should use project scope when in git repo."""
        (tmp_path / ".git").mkdir()

        scope, path = GraphSelector.determine_scope(start_path=tmp_path)

        assert scope == GraphScope.PROJECT
        assert path == tmp_path

    def test_determine_scope_fallback_to_global(self, tmp_path):
        """Should fall back to global when not in git repo."""
        scope, path = GraphSelector.determine_scope(start_path=tmp_path)

        assert scope == GraphScope.GLOBAL
        assert path is None


class TestGraphManagerGlobal:
    """Tests for global scope database management."""

    def test_global_driver_creation(self):
        """Should create global driver at correct path."""
        manager = GraphManager()
        try:
            driver = manager.get_driver(GraphScope.GLOBAL)
            assert driver is not None
            assert GLOBAL_DB_PATH.parent.exists()
        finally:
            manager.close_all()

    def test_global_driver_singleton(self):
        """Should return same driver instance on repeated calls."""
        manager = GraphManager()
        try:
            driver1 = manager.get_driver(GraphScope.GLOBAL)
            driver2 = manager.get_driver(GraphScope.GLOBAL)
            assert driver1 is driver2
        finally:
            manager.close_all()


class TestGraphManagerProject:
    """Tests for project scope database management."""

    def test_project_driver_creation(self, tmp_path):
        """Should create project driver at correct path."""
        (tmp_path / ".git").mkdir()
        manager = GraphManager()
        try:
            driver = manager.get_driver(GraphScope.PROJECT, tmp_path)
            assert driver is not None
            assert (tmp_path / ".graphiti").exists()
        finally:
            manager.close_all()

    def test_project_driver_requires_path(self):
        """Should raise ValueError when project_root not provided."""
        manager = GraphManager()
        try:
            with pytest.raises(ValueError, match="project_root is required"):
                manager.get_driver(GraphScope.PROJECT, None)
        finally:
            manager.close_all()

    def test_project_switching(self, tmp_path):
        """Should handle switching between different projects."""
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"
        (project1 / ".git").mkdir(parents=True)
        (project2 / ".git").mkdir(parents=True)

        manager = GraphManager()
        try:
            driver1 = manager.get_driver(GraphScope.PROJECT, project1)
            driver2 = manager.get_driver(GraphScope.PROJECT, project2)

            # Should be different drivers
            assert driver1 is not driver2
            # Both project directories should exist
            assert (project1 / ".graphiti").exists()
            assert (project2 / ".graphiti").exists()
        finally:
            manager.close_all()


class TestPersistence:
    """Tests verifying data persists across manager restarts.

    CRITICAL: These tests verify the core Phase 1 requirement that
    data survives application restarts.

    NOTE (Wave 0): Tests use real_ladybug.Connection imported locally inside each
    test method to avoid module-level conflict with kuzu (both Kuzu-derived C
    extensions cannot be imported in the same process). Wave 2 will remove kuzu
    entirely so the top-level import can be restored.
    """

    @pytest.fixture
    def isolated_global_path(self, tmp_path, monkeypatch):
        """Use isolated global path for tests to avoid polluting user's real global DB."""
        test_global = tmp_path / "test_global" / "graphiti.lbdb"
        monkeypatch.setattr("src.config.paths.GLOBAL_DB_PATH", test_global)
        monkeypatch.setattr("src.storage.graph_manager.GLOBAL_DB_PATH", test_global)
        return test_global

    def test_global_persistence(self, isolated_global_path):
        """Data in global scope should survive manager restart."""
        import real_ladybug as lb

        # First session: write data
        manager1 = GraphManager()
        driver1 = manager1.get_driver(GraphScope.GLOBAL)

        # Use raw LadybugDB connection to create a test node
        # (LadybugDriver provides .db attribute for raw access)
        conn = lb.Connection(driver1.db)
        try:
            # Create a simple test table and insert data
            conn.execute("CREATE NODE TABLE IF NOT EXISTS TestNode(id STRING PRIMARY KEY, value STRING)")
            conn.execute("CREATE (:TestNode {id: 'test1', value: 'persisted'})")
        finally:
            conn.close()

        manager1.close_all()

        # Second session: read data back
        manager2 = GraphManager()
        driver2 = manager2.get_driver(GraphScope.GLOBAL)

        conn = lb.Connection(driver2.db)
        try:
            result = conn.execute("MATCH (n:TestNode {id: 'test1'}) RETURN n.value AS value")
            rows = list(result.rows_as_dict())
            assert len(rows) == 1
            assert rows[0]['value'] == 'persisted'
        finally:
            conn.close()
            manager2.close_all()

    def test_project_persistence(self, tmp_path):
        """Data in project scope should survive manager restart."""
        import real_ladybug as lb

        (tmp_path / ".git").mkdir()

        # First session: write data
        manager1 = GraphManager()
        driver1 = manager1.get_driver(GraphScope.PROJECT, tmp_path)

        conn = lb.Connection(driver1.db)
        try:
            conn.execute("CREATE NODE TABLE IF NOT EXISTS TestNode(id STRING PRIMARY KEY, value STRING)")
            conn.execute("CREATE (:TestNode {id: 'proj1', value: 'project_data'})")
        finally:
            conn.close()

        manager1.close_all()

        # Second session: read data back
        manager2 = GraphManager()
        driver2 = manager2.get_driver(GraphScope.PROJECT, tmp_path)

        conn = lb.Connection(driver2.db)
        try:
            result = conn.execute("MATCH (n:TestNode {id: 'proj1'}) RETURN n.value AS value")
            rows = list(result.rows_as_dict())
            assert len(rows) == 1
            assert rows[0]['value'] == 'project_data'
        finally:
            conn.close()
            manager2.close_all()


class TestIsolation:
    """Tests verifying global and project graphs are isolated."""

    @pytest.fixture
    def isolated_global_path(self, tmp_path, monkeypatch):
        """Use isolated global path for tests."""
        test_global = tmp_path / "test_global" / "graphiti.lbdb"
        monkeypatch.setattr("src.config.paths.GLOBAL_DB_PATH", test_global)
        monkeypatch.setattr("src.storage.graph_manager.GLOBAL_DB_PATH", test_global)
        return test_global

    def test_global_and_project_isolation(self, isolated_global_path, tmp_path):
        """Writing to global should not affect project and vice versa."""
        import real_ladybug as lb

        project_root = tmp_path / "project"
        (project_root / ".git").mkdir(parents=True)

        manager = GraphManager()
        try:
            # Get both drivers
            global_driver = manager.get_driver(GraphScope.GLOBAL)
            project_driver = manager.get_driver(GraphScope.PROJECT, project_root)

            # Write different data to each
            global_conn = lb.Connection(global_driver.db)
            project_conn = lb.Connection(project_driver.db)

            try:
                # Global: create table and insert
                global_conn.execute("CREATE NODE TABLE IF NOT EXISTS IsolationTest(id STRING PRIMARY KEY, scope STRING)")
                global_conn.execute("CREATE (:IsolationTest {id: 'iso1', scope: 'global'})")

                # Project: create same table structure but different data
                project_conn.execute("CREATE NODE TABLE IF NOT EXISTS IsolationTest(id STRING PRIMARY KEY, scope STRING)")
                project_conn.execute("CREATE (:IsolationTest {id: 'iso1', scope: 'project'})")

                # Verify global only sees global data
                global_result = global_conn.execute("MATCH (n:IsolationTest) RETURN n.scope AS scope")
                global_rows = list(global_result.rows_as_dict())
                assert len(global_rows) == 1
                assert global_rows[0]['scope'] == 'global'

                # Verify project only sees project data
                project_result = project_conn.execute("MATCH (n:IsolationTest) RETURN n.scope AS scope")
                project_rows = list(project_result.rows_as_dict())
                assert len(project_rows) == 1
                assert project_rows[0]['scope'] == 'project'

            finally:
                global_conn.close()
                project_conn.close()

        finally:
            manager.close_all()

    def test_simultaneous_access(self, isolated_global_path, tmp_path):
        """Both graphs should be accessible simultaneously."""
        import real_ladybug as lb

        project_root = tmp_path / "project"
        (project_root / ".git").mkdir(parents=True)

        manager = GraphManager()
        try:
            global_driver = manager.get_driver(GraphScope.GLOBAL)
            project_driver = manager.get_driver(GraphScope.PROJECT, project_root)

            # Both drivers should exist and be different
            assert global_driver is not project_driver
            assert global_driver is not None
            assert project_driver is not None

            # Both should be usable
            global_conn = lb.Connection(global_driver.db)
            project_conn = lb.Connection(project_driver.db)

            try:
                # Both can execute queries
                global_result = global_conn.execute("RETURN 'global' AS source")
                project_result = project_conn.execute("RETURN 'project' AS source")

                assert list(global_result.rows_as_dict())[0]['source'] == 'global'
                assert list(project_result.rows_as_dict())[0]['source'] == 'project'
            finally:
                global_conn.close()
                project_conn.close()

        finally:
            manager.close_all()

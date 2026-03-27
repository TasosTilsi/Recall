import asyncio
import json
import sys
import structlog
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from src.storage.ladybug_driver import LadybugDriver
from src.models import GraphScope
from src.config import GLOBAL_DB_PATH, get_project_db_path

logger = structlog.get_logger(__name__)

_VERSION_FILE = Path.home() / ".recall" / "version.json"
_SCHEMA_VERSION = "2.0"


def _is_first_v2_run() -> bool:
    """Detect first run after v1.1->v2.0 migration to clear stale data."""
    if not _VERSION_FILE.exists():
        return True
    try:
        data = json.loads(_VERSION_FILE.read_text())
        return data.get("schema_version") != _SCHEMA_VERSION
    except Exception:
        return True


def _mark_v2_initialized() -> None:
    """Write schema version stamp after successful v2.0 initialization."""
    _VERSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    _VERSION_FILE.write_text(json.dumps({"schema_version": _SCHEMA_VERSION}))


def parse_bolt_uri(uri: str) -> tuple[str, str | None, str | None]:
    """Parse bolt://user:pass@host:port into (clean_uri, user, password).

    Neo4jDriver.__init__ requires credentials separated from the URI.

    Example:
        parse_bolt_uri("bolt://neo4j:changeme@localhost:7687")
        -> ("bolt://localhost:7687", "neo4j", "changeme")
    """
    parsed = urlparse(uri)
    clean_uri = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    return clean_uri, parsed.username, parsed.password


async def _check_neo4j_reachable(uri: str, user: str, password: str) -> bool:
    """Ping Neo4j via bolt to check reachability for fail-fast check."""
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        await driver.verify_connectivity()
        await driver.close()
        return True
    except Exception:
        return False


class GraphManager:
    """Manages dual-scope LadybugDB database instances.

    Maintains singleton LadybugDriver instances for global and project scopes.
    Handles lazy initialization and proper cleanup.

    Singleton pattern: only one Database object should exist per database path.
    This class enforces that constraint per scope.
    """

    def __init__(self, read_only: bool = False):
        self._global_driver = None
        self._project_driver = None
        self._current_project_root: Optional[Path] = None
        self._read_only = read_only

    def _make_driver(self, db_path: str, read_only: bool = False):
        """Create appropriate driver based on backend configuration.

        For LadybugDB (default): creates LadybugDriver at db_path.
        For Neo4j: creates Neo4jDriver using bolt URI from config.
        Fail-fast: if Neo4j configured but unreachable, prints error and exits non-zero.
        """
        from src.llm.config import load_config
        config = load_config()

        if config.backend_type == "neo4j":
            if not config.backend_uri:
                logger.error("backend type is 'neo4j' but no uri configured in [backend] section of llm.toml")
                sys.exit(1)
            clean_uri, user, password = parse_bolt_uri(config.backend_uri)
            # Fail-fast: check Neo4j reachability before returning driver
            reachable = asyncio.run(_check_neo4j_reachable(clean_uri, user or "", password or ""))
            if not reachable:
                print(
                    f"Neo4j unreachable at {config.backend_uri} — run docker compose -f docker-compose.neo4j.yml up -d first",
                    file=sys.stderr,
                )
                sys.exit(1)
            from graphiti_core.driver.neo4j_driver import Neo4jDriver
            return Neo4jDriver(uri=clean_uri, user=user, password=password)
        else:
            # LadybugDB default
            return LadybugDriver(db=db_path, read_only=read_only)

    def _clear_stale_v1_data(self) -> None:
        """Clear retention.db and SQLiteAckQueue on first v2.0 run.

        Old LadybugDB UUIDs won't match new LadybugDB entity UUIDs.
        Fresh start is acceptable — no real users with data to preserve.
        """
        import shutil
        retention_db = Path.home() / ".recall" / "retention.db"
        queue_dir = Path.home() / ".recall" / "queue"
        if retention_db.exists():
            retention_db.unlink()
            logger.info("v2.0 first run: cleared stale retention.db (UUID mismatch)")
        if queue_dir.exists():
            shutil.rmtree(queue_dir)
            logger.info("v2.0 first run: cleared stale SQLiteAckQueue (re-queue on next sync)")

    def get_driver(
        self,
        scope: GraphScope,
        project_root: Optional[Path] = None
    ):
        """Get or create LadybugDriver for the specified scope.

        Args:
            scope: Which graph scope to access
            project_root: Required for PROJECT scope, ignored for GLOBAL

        Returns:
            LadybugDriver instance for the requested scope

        Raises:
            ValueError: If project_root not provided for PROJECT scope
        """
        if scope == GraphScope.GLOBAL:
            return self._get_global_driver()
        else:
            return self._get_project_driver(project_root)

    def _get_global_driver(self):
        """Get or create the global scope driver."""
        if self._global_driver is None:
            GLOBAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not self._read_only and _is_first_v2_run():
                self._clear_stale_v1_data()
            self._global_driver = self._make_driver(str(GLOBAL_DB_PATH), read_only=self._read_only)
            if not self._read_only:
                _mark_v2_initialized()
        return self._global_driver

    def _get_project_driver(self, project_root: Optional[Path]):
        """Get or create project scope driver.

        Handles project switching: if project_root differs from cached,
        closes old connection and creates new one.
        """
        if project_root is None:
            raise ValueError("project_root is required for PROJECT scope")

        # Check if we need to switch projects
        if self._project_driver is not None and self._current_project_root != project_root:
            # Project changed, close old connection
            asyncio.run(self._project_driver.close())
            self._project_driver = None

        if self._project_driver is None:
            db_path = get_project_db_path(project_root)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._project_driver = self._make_driver(str(db_path), read_only=self._read_only)
            self._current_project_root = project_root

        return self._project_driver

    def reset_project(self) -> None:
        """Reset project scope connection.

        Call this when context changes (e.g., user changed directories).
        Next get_driver() for PROJECT scope will detect new project.
        """
        if self._project_driver is not None:
            asyncio.run(self._project_driver.close())
            self._project_driver = None
            self._current_project_root = None

    def close_all(self) -> None:
        """Close all database connections.

        Call this on application shutdown for clean resource release.
        """
        if self._global_driver is not None:
            asyncio.run(self._global_driver.close())
            self._global_driver = None

        if self._project_driver is not None:
            asyncio.run(self._project_driver.close())
            self._project_driver = None
            self._current_project_root = None

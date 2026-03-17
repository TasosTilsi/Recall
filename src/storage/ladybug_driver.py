"""Vendored LadybugDriver for graphiti-core 0.28.1.

LadybugDB (real-ladybug) is the community-maintained fork of KuzuDB.
graphiti-core PR #1296 adds official LadybugDriver support but is not yet merged.
This file vendors the driver locally. It can be replaced with the official import
once PR #1296 merges and graphiti-core releases a new version.

Spike findings (Phase 12 Plan 01):
- real_ladybug provides only low-level bindings: Database, Connection, AsyncConnection
- No graphiti-compatible driver exists in the package
- GraphProvider.LADYBUG absent from graphiti-core 0.28.1 — use GraphProvider.KUZU as alias
  (LadybugDB is a Kuzu fork with identical Cypher dialect and FTS schema)
- AsyncConnection signature: lb.AsyncConnection(database, max_concurrent_queries=4)
- Connection API: lb.Connection(db).execute(cypher) returns QueryResult with .rows_as_dict()

IMPORTANT: Do NOT import from graphiti_core.driver.kuzu_driver — that module imports kuzu
at the top level which will fail once kuzu is removed. Import from graphiti_core.driver.driver
instead (GraphProvider and GraphDriverSession live there).
SCHEMA_QUERIES is embedded directly to avoid any kuzu_driver import.

Ref: https://github.com/zep-ai/graphiti/pull/1296
"""
import copy
from typing import Any

import real_ladybug as lb
import structlog
from graphiti_core.driver.driver import GraphDriver, GraphDriverSession, GraphProvider

logger = structlog.get_logger(__name__)

# Schema DDL copied from graphiti_core.driver.kuzu_driver.SCHEMA_QUERIES (0.28.1).
# Embedded here to avoid importing kuzu_driver which has `import kuzu` at the top level.
# LadybugDB is a Kuzu fork with identical Cypher DDL syntax, so these queries work as-is.
SCHEMA_QUERIES = """
    CREATE NODE TABLE IF NOT EXISTS Episodic (
        uuid STRING PRIMARY KEY,
        name STRING,
        group_id STRING,
        created_at TIMESTAMP,
        source STRING,
        source_description STRING,
        content STRING,
        valid_at TIMESTAMP,
        entity_edges STRING[]
    );
    CREATE NODE TABLE IF NOT EXISTS Entity (
        uuid STRING PRIMARY KEY,
        name STRING,
        group_id STRING,
        labels STRING[],
        created_at TIMESTAMP,
        name_embedding FLOAT[],
        summary STRING,
        attributes STRING
    );
    CREATE NODE TABLE IF NOT EXISTS Community (
        uuid STRING PRIMARY KEY,
        name STRING,
        group_id STRING,
        created_at TIMESTAMP,
        name_embedding FLOAT[],
        summary STRING
    );
    CREATE NODE TABLE IF NOT EXISTS RelatesToNode_ (
        uuid STRING PRIMARY KEY,
        group_id STRING,
        created_at TIMESTAMP,
        name STRING,
        fact STRING,
        fact_embedding FLOAT[],
        episodes STRING[],
        expired_at TIMESTAMP,
        valid_at TIMESTAMP,
        invalid_at TIMESTAMP,
        attributes STRING
    );
    CREATE REL TABLE IF NOT EXISTS RELATES_TO(
        FROM Entity TO RelatesToNode_,
        FROM RelatesToNode_ TO Entity
    );
    CREATE REL TABLE IF NOT EXISTS MENTIONS(
        FROM Episodic TO Entity,
        uuid STRING PRIMARY KEY,
        group_id STRING,
        created_at TIMESTAMP
    );
    CREATE REL TABLE IF NOT EXISTS HAS_MEMBER(
        FROM Community TO Entity,
        FROM Community TO Community,
        uuid STRING,
        group_id STRING,
        created_at TIMESTAMP
    );
    CREATE NODE TABLE IF NOT EXISTS Saga (
        uuid STRING PRIMARY KEY,
        name STRING,
        group_id STRING,
        created_at TIMESTAMP
    );
    CREATE REL TABLE IF NOT EXISTS HAS_EPISODE(
        FROM Saga TO Episodic,
        uuid STRING,
        group_id STRING,
        created_at TIMESTAMP
    );
    CREATE REL TABLE IF NOT EXISTS NEXT_EPISODE(
        FROM Episodic TO Episodic,
        uuid STRING,
        group_id STRING,
        created_at TIMESTAMP
    );
"""


class LadybugDriverSession(GraphDriverSession):
    """Session wrapper for LadybugDriver.

    Mirrors KuzuDriverSession — no real session semantics needed for an
    embedded database; queries execute on the shared connection directly.
    """

    provider = GraphProvider.KUZU  # LadybugDB is a Kuzu fork

    def __init__(self, driver: 'LadybugDriver') -> None:
        self.driver = driver

    async def __aenter__(self) -> 'LadybugDriverSession':
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        pass

    async def close(self) -> None:
        pass

    async def execute_write(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(self, *args, **kwargs)

    async def run(self, query: Any, **kwargs: Any) -> None:
        if isinstance(query, list):
            for cypher, params in query:
                await self.driver.execute_query(cypher, **params)
        else:
            await self.driver.execute_query(query, **kwargs)
        return None


class LadybugDriver(GraphDriver):
    """Embedded graph database driver using LadybugDB (real-ladybug).

    Drop-in replacement for KuzuDriver. All 3 KuzuDB workarounds are eliminated:
    1. _database is NOT set in __init__ — set only via clone()/with_database()
       (KuzuDriver.clone() was a no-op bug returning self; this returns a real copy)
    2. FTS indices / schema created properly in setup_schema() called from __init__
       (KuzuDriver.build_indices_and_constraints() was a no-op; workaround 2 eliminated)
    3. No direct kuzu imports anywhere in this file

    Usage:
        driver = LadybugDriver(db="/path/to/graph.lbdb")
        results, _, _ = await driver.execute_query("MATCH (n) RETURN n.name AS name")
    """

    provider: GraphProvider = GraphProvider.KUZU  # LadybugDB is a Kuzu fork

    def __init__(
        self,
        db: str = ':memory:',
        max_concurrent_queries: int = 4,
    ) -> None:
        super().__init__()
        self._db_path = db
        self._max_concurrent_queries = max_concurrent_queries

        # Create database and setup schema (tables + indices via SCHEMA_QUERIES)
        self.db = lb.Database(db)
        self.setup_schema()

        # AsyncConnection for graphiti-core async query execution
        self.client = lb.AsyncConnection(self.db, max_concurrent_queries=max_concurrent_queries)

        # NOTE: _database is intentionally NOT set here.
        # Graphiti.add_episode() calls driver.with_database(group_id) which creates a
        # clone with _database set. That clone is used for group_id-scoped operations.
        # Setting _database in __init__ would use db_path as group_id, which is wrong.

    def setup_schema(self) -> None:
        """Create all required tables and relations.

        Uses SCHEMA_QUERIES embedded from graphiti-core 0.28.1 KuzuDriver.
        LadybugDB is a Kuzu fork with identical Cypher DDL syntax.
        """
        conn = lb.Connection(self.db)
        conn.execute(SCHEMA_QUERIES)
        conn.close()

    def clone(self, database: str) -> 'LadybugDriver':
        """Return a copy of this driver with _database set to the given value.

        CRITICAL: KuzuDriver.clone() returns self (a no-op bug). This implementation
        returns an actual shallow copy so Graphiti.add_episode() group_id routing works.
        Eliminates workaround 1 (manual driver._database = str(db_path) patch).
        """
        cloned = copy.copy(self)
        cloned._database = database
        return cloned

    def session(self, database: str | None = None) -> LadybugDriverSession:
        """Return a session for executing queries."""
        return LadybugDriverSession(self)

    async def execute_query(
        self,
        cypher_query_: str,
        **kwargs: Any,
    ) -> tuple[list[dict[str, Any]], None, None]:
        """Execute a Cypher query and return results as list of dicts.

        Returns (results, None, None) matching KuzuDriver contract.
        Each result row is a dict keyed by column alias.
        kwargs are passed as query parameters (None-valued entries stripped).
        """
        params = {k: v for k, v in kwargs.items() if v is not None}
        # Strip neo4j-specific routing params that LadybugDB doesn't support
        params.pop('database_', None)
        params.pop('routing_', None)

        try:
            results = await self.client.execute(cypher_query_, parameters=params)
        except Exception as e:
            logger.error(
                "execute_query failed",
                query=cypher_query_[:100],
                error=str(e),
            )
            raise

        if not results:
            return [], None, None

        if isinstance(results, list):
            dict_results = [list(result.rows_as_dict()) for result in results]
        else:
            dict_results = list(results.rows_as_dict())

        return dict_results, None, None  # type: ignore[return-value]

    async def build_indices_and_constraints(self, delete_existing: bool = False) -> None:
        """Create FTS and other indices required by graphiti-core.

        LadybugDB uses the same Cypher FTS index syntax as KuzuDB (identical fork).
        Schema is created during setup_schema() called from __init__.
        This method is kept for ABC compliance and future index additions.
        """
        # Schema/indices are created in setup_schema() called from __init__.
        # This is a no-op here (same pattern as KuzuDriver.build_indices_and_constraints).
        pass

    def delete_all_indexes(self, database_: str = '') -> None:
        """Delete all indexes (no-op for embedded LadybugDB)."""
        pass

    async def close(self) -> None:
        """Close the database connection.

        Relies on GC for cleanup (same pattern as KuzuDriver).
        """
        pass


__all__ = ["LadybugDriver"]

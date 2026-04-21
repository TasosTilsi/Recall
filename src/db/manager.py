"""DatabaseManager — synchronous SQLite connection and schema initialisation."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import structlog

from src.config import Config, load_config
from src.db.schema import CORE_DDL, DDL_EMBEDDINGS

log = structlog.get_logger(__name__)


def _find_project_root(start: Path) -> Optional[Path]:
    """Walk up from start until .git/ is found; return that directory or None."""
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


class DatabaseManager:
    """Manages the SQLite database lifecycle for a recall knowledge graph."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self._config = config or load_config()

    def get_db_path(self) -> Path:
        """Resolve the database file path.

        Priority:
        1. config.db.path if it is an absolute path
        2. config.db.path relative to git project root (walk up from CWD)
        3. Fallback: CWD / config.db.path (if no .git found)
        """
        raw = self._config.db.path
        p = Path(raw)
        if p.is_absolute():
            return p
        # Try project-local placement
        root = _find_project_root(Path.cwd())
        if root:
            return root / p
        # No git root found -- use CWD
        return Path.cwd() / p

    def connect(self) -> sqlite3.Connection:
        """Open and return a sqlite3 connection with FK enforcement enabled.

        The connection has:
        - foreign_keys = ON
        - journal_mode = WAL  (safe for concurrent readers)
        - row_factory = sqlite3.Row (dict-like access)
        """
        db_path = self.get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def init_db(self) -> None:
        """Create all tables, triggers, FTS index, and optionally embeddings table.

        Safe to call multiple times -- all DDL uses CREATE IF NOT EXISTS.
        Embeddings table is created only when config.embeddings is not None.
        """
        db_path = self.get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)

        log.info("initialising database", path=str(db_path))

        with self.connect() as conn:
            for ddl in CORE_DDL:
                conn.execute(ddl)

            if self._config.embeddings is not None:
                log.info("embeddings configured — creating embeddings table")
                conn.execute(DDL_EMBEDDINGS)
            else:
                log.debug("no [embeddings] config — skipping embeddings table")

            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                ("schema_version", "3.0"),
            )
            conn.commit()

        log.info("database ready", path=str(db_path))

    # ------------------------------------------------------------------
    # Query helpers — used by MCP tools and CLI search
    # ------------------------------------------------------------------

    def _row_to_entity(self, row: sqlite3.Row) -> dict:
        """Convert a sqlite3.Row from entities table to a plain dict."""
        return {
            "id": row["id"],
            "name": row["name"],
            "type": row["type"],
            "content": row["content"],
            "tags": row["tags"],
            "source_commit": row["commit_sha"],
            "created_at": row["created_at"],
        }

    def search_fts(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search over entity names and content via FTS5.

        Returns a list of entity dicts with an additional ``rank`` field.
        """
        sql = """
            SELECT e.id, e.name, e.type, e.content, e.tags, e.commit_sha, e.created_at,
                   fts.rank AS rank
            FROM entities_fts fts
            JOIN entities e ON e.rowid = fts.rowid
            WHERE entities_fts MATCH ?
            ORDER BY fts.rank
            LIMIT ?
        """
        with self.connect() as conn:
            rows = conn.execute(sql, (query, limit)).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["source_commit"] = d.pop("commit_sha", None)
            results.append(d)
        return results

    def get_entity_by_id(self, entity_id: str) -> dict | None:
        """Fetch a single entity by its UUID (primary key)."""
        sql = "SELECT * FROM entities WHERE id = ? LIMIT 1"
        with self.connect() as conn:
            row = conn.execute(sql, (entity_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_entity(row)

    def get_entity_by_name(self, name: str) -> dict | None:
        """Fetch a single entity by exact name match."""
        sql = "SELECT * FROM entities WHERE name = ? LIMIT 1"
        with self.connect() as conn:
            row = conn.execute(sql, (name,)).fetchone()
        if row is None:
            return None
        return self._row_to_entity(row)

    def get_backlinks(self, entity_id: str) -> list[dict]:
        """Return direct backlinks for the given entity (both directions).

        Looks up rows where ``from_id`` OR ``to_id`` equals entity_id so that
        the caller sees all relationships the entity participates in.
        """
        sql = """
            SELECT from_id AS source_id,
                   to_id   AS target_id,
                   relationship AS label,
                   '' AS inverse_label,
                   context,
                   '' AS commit_sha
            FROM backlinks
            WHERE from_id = ? OR to_id = ?
        """
        with self.connect() as conn:
            rows = conn.execute(sql, (entity_id, entity_id)).fetchall()
        return [dict(row) for row in rows]

    def get_backlinks_recursive(self, entity_id: str, hops: int) -> list[dict]:
        """BFS traversal of backlinks up to ``hops`` depth.

        Iteratively expands the frontier using ``get_backlinks()``. A visited
        set prevents cycles. Returns deduplicated list of backlink dicts.
        """
        visited: set[str] = {entity_id}
        frontier: set[str] = {entity_id}
        all_links: list[dict] = []
        seen_links: set[tuple] = set()

        for _ in range(max(1, hops)):
            next_frontier: set[str] = set()
            for eid in frontier:
                for link in self.get_backlinks(eid):
                    key = (link["source_id"], link["target_id"], link["label"])
                    if key not in seen_links:
                        seen_links.add(key)
                        all_links.append(link)
                    for nid in (link["source_id"], link["target_id"]):
                        if nid not in visited:
                            visited.add(nid)
                            next_frontier.add(nid)
            frontier = next_frontier
            if not frontier:
                break

        return all_links

    def get_entities_by_type(self, entity_type: str, limit: int = 20) -> list[dict]:
        """Return entities filtered by type.

        Valid types: decision, bug_fix, pattern, file, concept, tech_debt.
        """
        sql = "SELECT * FROM entities WHERE type = ? ORDER BY created_at DESC LIMIT ?"
        with self.connect() as conn:
            rows = conn.execute(sql, (entity_type, limit)).fetchall()
        return [self._row_to_entity(row) for row in rows]

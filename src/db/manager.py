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

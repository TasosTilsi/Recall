"""RetentionManager — SQLite sidecar for node retention metadata.

Provides a single access layer for all retention operations:
- Access logging (for staleness scoring)
- Pin/unpin state
- Archive state
- Staleness score computation
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS access_log (
    uuid TEXT NOT NULL,
    scope TEXT NOT NULL,
    last_accessed_at TEXT NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (uuid, scope)
);

CREATE TABLE IF NOT EXISTS pin_state (
    uuid TEXT NOT NULL,
    scope TEXT NOT NULL,
    pinned_at TEXT NOT NULL,
    PRIMARY KEY (uuid, scope)
);

CREATE TABLE IF NOT EXISTS archive_state (
    uuid TEXT NOT NULL,
    scope TEXT NOT NULL,
    archived_at TEXT NOT NULL,
    PRIMARY KEY (uuid, scope)
);
"""

_manager: Optional["RetentionManager"] = None


def get_retention_manager() -> "RetentionManager":
    """Return the singleton RetentionManager, creating it on first call."""
    global _manager
    if _manager is None:
        db_path = Path.home() / ".recall" / "retention.db"
        _manager = RetentionManager(db_path=db_path)
    return _manager


def reset_retention_manager() -> None:
    """Clear the singleton. Used in tests for isolation."""
    global _manager
    _manager = None


class RetentionManager:
    """Manages retention metadata in a SQLite sidecar database.

    All operations are synchronous (stdlib sqlite3 only).
    WAL journal mode is set on every connection for concurrency safety.

    Args:
        db_path: Path to the SQLite database file. Parent directory
                 is created if it does not exist.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        logger.debug("RetentionManager initialised", db_path=str(db_path))

    def _get_conn(self) -> sqlite3.Connection:
        """Return a new WAL-mode connection with row_factory=sqlite3.Row."""
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        """Create tables if they do not already exist."""
        with self._get_conn() as conn:
            conn.executescript(CREATE_SCHEMA)

    # ------------------------------------------------------------------
    # Access logging
    # ------------------------------------------------------------------

    def record_access(self, uuid: str, scope: str) -> None:
        """Upsert access_log: increment access_count, set last_accessed_at=now."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO access_log (uuid, scope, last_accessed_at, access_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(uuid, scope) DO UPDATE SET
                    access_count = access_count + 1,
                    last_accessed_at = excluded.last_accessed_at
                """,
                (uuid, scope, now_iso),
            )

    def get_access_record(self, uuid: str, scope: str) -> dict:
        """Return {last_accessed_at: datetime|None, access_count: int}."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT last_accessed_at, access_count FROM access_log WHERE uuid=? AND scope=?",
                (uuid, scope),
            ).fetchone()
        if row is None:
            return {"last_accessed_at": None, "access_count": 0}
        ts = row["last_accessed_at"]
        last_accessed = datetime.fromisoformat(ts) if ts else None
        return {"last_accessed_at": last_accessed, "access_count": row["access_count"]}

    # ------------------------------------------------------------------
    # Pin state
    # ------------------------------------------------------------------

    def pin_node(self, uuid: str, scope: str) -> None:
        """Insert into pin_state. No-op if already pinned."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO pin_state (uuid, scope, pinned_at) VALUES (?, ?, ?)",
                (uuid, scope, now_iso),
            )

    def unpin_node(self, uuid: str, scope: str) -> None:
        """Delete from pin_state. No-op if not pinned."""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM pin_state WHERE uuid=? AND scope=?",
                (uuid, scope),
            )

    def is_pinned(self, uuid: str, scope: str) -> bool:
        """Return True if the node is pinned in the given scope."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM pin_state WHERE uuid=? AND scope=?",
                (uuid, scope),
            ).fetchone()
        return row is not None

    def get_pin_state_uuids(self, scope: str) -> set[str]:
        """Return the set of all pinned UUIDs in the given scope."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT uuid FROM pin_state WHERE scope=?",
                (scope,),
            ).fetchall()
        return {row["uuid"] for row in rows}

    # ------------------------------------------------------------------
    # Archive state
    # ------------------------------------------------------------------

    def archive_node(self, uuid: str, scope: str) -> None:
        """Insert into archive_state. No-op if already archived."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO archive_state (uuid, scope, archived_at) VALUES (?, ?, ?)",
                (uuid, scope, now_iso),
            )

    def clear_archive(self, uuid: str, scope: str) -> None:
        """Delete from archive_state. No-op if uuid not in archive_state."""
        with self._get_conn() as conn:
            conn.execute(
                "DELETE FROM archive_state WHERE uuid=? AND scope=?",
                (uuid, scope),
            )

    def is_archived(self, uuid: str, scope: str) -> bool:
        """Return True if the node is archived in the given scope."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM archive_state WHERE uuid=? AND scope=?",
                (uuid, scope),
            ).fetchone()
        return row is not None

    def get_archive_state_uuids(self, scope: str) -> set[str]:
        """Return the set of all archived UUIDs in the given scope."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT uuid FROM archive_state WHERE scope=?",
                (scope,),
            ).fetchall()
        return {row["uuid"] for row in rows}

    # ------------------------------------------------------------------
    # Staleness scoring
    # ------------------------------------------------------------------

    @staticmethod
    def compute_score(
        created_at: datetime,
        last_accessed_at: datetime | None,
        access_count: int,
        retention_days: int,
    ) -> float:
        """Compute staleness score in [0.0, 1.0]. Lower = more stale.

        Algorithm:
            age_factor      = min(age_days / retention_days, 1.0)
            recency_factor  = max(0.0, 1.0 - days_since_access / retention_days)
            access_bonus    = min(access_count * 0.3 * recency_factor, 0.5)
            score           = age_factor * (1.0 - access_bonus)
            return round(score, 3)

        Timezone-naive datetimes are normalised to UTC automatically.
        """
        now = datetime.now(timezone.utc)

        # Normalise naive datetimes
        def _utc(dt: datetime) -> datetime:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt

        created_at = _utc(created_at)
        if last_accessed_at is not None:
            last_accessed_at = _utc(last_accessed_at)

        age_days = (now - created_at).total_seconds() / 86400.0
        age_factor = min(age_days / retention_days, 1.0)

        if last_accessed_at is None:
            days_since_access = float(retention_days)
        else:
            days_since_access = (now - last_accessed_at).total_seconds() / 86400.0

        recency_factor = max(0.0, 1.0 - days_since_access / retention_days)
        access_bonus = min(access_count * 0.3 * recency_factor, 0.5)
        score = age_factor * (1.0 - access_bonus)
        return round(score, 3)

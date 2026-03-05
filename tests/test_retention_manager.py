"""Tests for RetentionManager.

Tests cover:
- Singleton behavior (get_retention_manager / reset_retention_manager)
- Schema creation (three tables exist)
- record_access upsert behavior
- pin/unpin round-trip
- archive / clear_archive (including no-op clear on non-archived uuid)
- is_pinned / is_archived
- get_access_record
- get_archive_state_uuids / get_pin_state_uuids
- compute_score edge cases
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

# --- Isolate singleton across tests ---
import src.retention.manager as _mod


@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure singleton is reset before and after every test."""
    _mod.reset_retention_manager()
    yield
    _mod.reset_retention_manager()


@pytest.fixture()
def db(tmp_path) -> "RetentionManager":  # type: ignore[name-defined]
    from src.retention import RetentionManager
    return RetentionManager(db_path=tmp_path / "retention.db")


# ---------------------------------------------------------------------------
# Imports / public API
# ---------------------------------------------------------------------------

class TestImports:
    def test_public_exports(self):
        from src.retention import RetentionManager, get_retention_manager, reset_retention_manager
        assert RetentionManager is not None
        assert callable(get_retention_manager)
        assert callable(reset_retention_manager)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_same_instance_returned(self, tmp_path):
        from src.retention import get_retention_manager, reset_retention_manager
        # Use a custom db_path by monkeypatching the default path
        from src.retention import manager as m
        # Call twice — should be same object
        mgr1 = get_retention_manager()
        mgr2 = get_retention_manager()
        assert mgr1 is mgr2

    def test_reset_clears_singleton(self, tmp_path):
        from src.retention import get_retention_manager, reset_retention_manager
        mgr1 = get_retention_manager()
        reset_retention_manager()
        mgr2 = get_retention_manager()
        assert mgr1 is not mgr2


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

class TestSchema:
    def test_tables_exist(self, db, tmp_path):
        conn = sqlite3.connect(str(tmp_path / "retention.db"))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "access_log" in tables
        assert "pin_state" in tables
        assert "archive_state" in tables

    def test_wal_mode(self, db, tmp_path):
        conn = sqlite3.connect(str(tmp_path / "retention.db"))
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        conn.close()
        assert mode == "wal"


# ---------------------------------------------------------------------------
# record_access
# ---------------------------------------------------------------------------

class TestRecordAccess:
    def test_first_access_creates_row(self, db):
        db.record_access("uuid-1", "personal")
        rec = db.get_access_record("uuid-1", "personal")
        assert rec["access_count"] == 1
        assert rec["last_accessed_at"] is not None

    def test_repeated_access_increments_count(self, db):
        db.record_access("uuid-2", "work")
        db.record_access("uuid-2", "work")
        db.record_access("uuid-2", "work")
        rec = db.get_access_record("uuid-2", "work")
        assert rec["access_count"] == 3

    def test_different_scopes_independent(self, db):
        db.record_access("uuid-3", "personal")
        db.record_access("uuid-3", "work")
        rec_p = db.get_access_record("uuid-3", "personal")
        rec_w = db.get_access_record("uuid-3", "work")
        assert rec_p["access_count"] == 1
        assert rec_w["access_count"] == 1

    def test_unknown_uuid_returns_zero_count(self, db):
        rec = db.get_access_record("nonexistent", "personal")
        assert rec["access_count"] == 0
        assert rec["last_accessed_at"] is None


# ---------------------------------------------------------------------------
# pin / unpin
# ---------------------------------------------------------------------------

class TestPinUnpin:
    def test_pin_node(self, db):
        db.pin_node("uuid-p1", "personal")
        assert db.is_pinned("uuid-p1", "personal") is True

    def test_unpin_node(self, db):
        db.pin_node("uuid-p2", "personal")
        db.unpin_node("uuid-p2", "personal")
        assert db.is_pinned("uuid-p2", "personal") is False

    def test_pin_idempotent(self, db):
        db.pin_node("uuid-p3", "work")
        db.pin_node("uuid-p3", "work")  # second call should not raise
        assert db.is_pinned("uuid-p3", "work") is True

    def test_unpin_nonexistent_noop(self, db):
        # Should not raise
        db.unpin_node("nonexistent", "personal")
        assert db.is_pinned("nonexistent", "personal") is False

    def test_is_not_pinned_by_default(self, db):
        assert db.is_pinned("uuid-new", "personal") is False

    def test_get_pin_state_uuids(self, db):
        db.pin_node("u1", "scope-a")
        db.pin_node("u2", "scope-a")
        db.pin_node("u3", "scope-b")
        pinned = db.get_pin_state_uuids("scope-a")
        assert pinned == {"u1", "u2"}


# ---------------------------------------------------------------------------
# archive / clear_archive
# ---------------------------------------------------------------------------

class TestArchive:
    def test_archive_node(self, db):
        db.archive_node("uuid-a1", "personal")
        assert db.is_archived("uuid-a1", "personal") is True

    def test_clear_archive_removes(self, db):
        db.archive_node("uuid-a2", "personal")
        db.clear_archive("uuid-a2", "personal")
        assert db.is_archived("uuid-a2", "personal") is False

    def test_clear_archive_noop_on_unarchived(self, db):
        # Should not raise even if uuid not in archive_state
        db.clear_archive("nonexistent", "personal")
        assert db.is_archived("nonexistent", "personal") is False

    def test_archive_idempotent(self, db):
        db.archive_node("uuid-a3", "work")
        db.archive_node("uuid-a3", "work")  # second call should not raise
        assert db.is_archived("uuid-a3", "work") is True

    def test_is_not_archived_by_default(self, db):
        assert db.is_archived("uuid-new", "personal") is False

    def test_get_archive_state_uuids(self, db):
        db.archive_node("u4", "scope-c")
        db.archive_node("u5", "scope-c")
        db.archive_node("u6", "scope-d")
        archived = db.get_archive_state_uuids("scope-c")
        assert archived == {"u4", "u5"}


# ---------------------------------------------------------------------------
# compute_score
# ---------------------------------------------------------------------------

class TestComputeScore:
    """compute_score(created_at, last_accessed_at, access_count, retention_days) -> float 0.0-1.0"""

    def _now(self):
        return datetime.now(timezone.utc)

    def test_brand_new_node_score_zero(self):
        """Node created just now, never accessed — age_factor=0 → score=0.0"""
        from src.retention import RetentionManager
        from datetime import timedelta
        now = self._now()
        score = RetentionManager.compute_score(
            created_at=now,
            last_accessed_at=None,
            access_count=0,
            retention_days=90,
        )
        assert score == 0.0

    def test_fully_aged_node_no_access(self):
        """Node aged exactly to retention_days, never accessed → score=1.0"""
        from src.retention import RetentionManager
        from datetime import timedelta
        now = self._now()
        old = now - timedelta(days=90)
        score = RetentionManager.compute_score(
            created_at=old,
            last_accessed_at=None,
            access_count=0,
            retention_days=90,
        )
        assert score == 1.0

    def test_boundary_at_retention_days(self):
        """Age exactly at retention_days → age_factor=1.0"""
        from src.retention import RetentionManager
        from datetime import timedelta
        now = self._now()
        created = now - timedelta(days=90)
        score = RetentionManager.compute_score(
            created_at=created,
            last_accessed_at=None,
            access_count=0,
            retention_days=90,
        )
        assert score == 1.0

    def test_over_retention_days_capped_at_one(self):
        """Age beyond retention_days → age_factor capped at 1.0"""
        from src.retention import RetentionManager
        from datetime import timedelta
        now = self._now()
        very_old = now - timedelta(days=200)
        score = RetentionManager.compute_score(
            created_at=very_old,
            last_accessed_at=None,
            access_count=0,
            retention_days=90,
        )
        assert score == 1.0

    def test_high_access_reduces_score(self):
        """High access_count reduces score via access_bonus"""
        from src.retention import RetentionManager
        from datetime import timedelta
        now = self._now()
        old = now - timedelta(days=90)
        # Many accesses, recently accessed
        score_many = RetentionManager.compute_score(
            created_at=old,
            last_accessed_at=now,  # just accessed
            access_count=100,
            retention_days=90,
        )
        score_none = RetentionManager.compute_score(
            created_at=old,
            last_accessed_at=None,
            access_count=0,
            retention_days=90,
        )
        assert score_many < score_none

    def test_score_in_range(self):
        """Score must be in [0.0, 1.0]"""
        from src.retention import RetentionManager
        from datetime import timedelta
        now = self._now()
        for days_ago in [0, 10, 45, 90, 150]:
            for count in [0, 5, 50]:
                created = now - timedelta(days=days_ago)
                score = RetentionManager.compute_score(
                    created_at=created,
                    last_accessed_at=None,
                    access_count=count,
                    retention_days=90,
                )
                assert 0.0 <= score <= 1.0, f"score={score} out of range for days_ago={days_ago}, count={count}"

    def test_timezone_naive_input_handled(self):
        """Naive datetimes must be normalized to UTC without error"""
        from src.retention import RetentionManager
        from datetime import timedelta
        naive_now = datetime.utcnow()  # naive
        naive_old = naive_now - timedelta(days=45)
        # Must not raise TypeError
        score = RetentionManager.compute_score(
            created_at=naive_old,
            last_accessed_at=naive_now,
            access_count=3,
            retention_days=90,
        )
        assert 0.0 <= score <= 1.0

    def test_score_rounded_to_3_decimals(self):
        """Score must be rounded to 3 decimal places"""
        from src.retention import RetentionManager
        from datetime import timedelta
        now = self._now()
        created = now - timedelta(days=45)
        score = RetentionManager.compute_score(
            created_at=created,
            last_accessed_at=now - timedelta(days=10),
            access_count=2,
            retention_days=90,
        )
        assert score == round(score, 3)

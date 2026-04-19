"""Tests for src/indexer/indexer.py — incremental sync control flow."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.extractor.git_walker import CommitRecord
from src.indexer.indexer import (
    _commits_after_sha,
    run_init,
    run_sync,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_commit(sha: str) -> CommitRecord:
    """Return a minimal CommitRecord with the given sha."""
    return CommitRecord(
        sha=sha,
        short_sha=sha[:7],
        author="Test User",
        date=datetime(2024, 1, 1),
        message=f"commit {sha}",
        diff="",
    )


FAKE_ENTITIES = [
    {"type": "decision", "name": "use sqlite", "content": "use sqlite for storage", "commit_sha": "sha1"},
]


def _setup_db(tmp_path: Path, config: MagicMock) -> Path:
    """Configure mock config to use a temp DB path."""
    db_path = tmp_path / "recall.db"
    config.db.path = str(db_path)
    return db_path


# ---------------------------------------------------------------------------
# Test 1: run_sync with empty filter (0 commits to process)
# ---------------------------------------------------------------------------

def test_run_sync_empty_after_filter(tmp_path: Path, capsys):
    """run_sync where all commits are already indexed → prints '0 commits to process'."""
    sha1 = "aaa1111" * 5 + "aaa1"  # 36-char fake sha
    sha2 = "bbb2222" * 5 + "bbb2"

    commits = [make_commit(sha1), make_commit(sha2)]
    # last_indexed_sha is sha2 (newest) — nothing newer exists

    from src.config import Config, DBConfig, LLMConfig
    config = Config(llm=LLMConfig(), db=DBConfig(path=str(tmp_path / "recall.db")))

    with (
        patch("src.indexer.indexer.walk_commits", return_value=commits),
        patch("src.indexer.indexer.extract_batch", return_value=FAKE_ENTITIES),
    ):
        # First run init to create and populate the DB
        result_init = run_init(tmp_path, config)
        assert result_init["commits_processed"] == 2

        # Now sync — should find 0 new commits
        result_sync = run_sync(tmp_path, config)

    captured = capsys.readouterr()
    assert "0 commits to process" in captured.out
    assert result_sync == {"commits_processed": 0, "entities_inserted": 0}


# ---------------------------------------------------------------------------
# Test 2: run_sync incremental — only processes commits after last_indexed_sha
# ---------------------------------------------------------------------------

def test_run_sync_incremental(tmp_path: Path):
    """run_sync with last_sha=sha1 and 3 commits → only sha2, sha3 processed."""
    sha1 = "commit1sha"
    sha2 = "commit2sha"
    sha3 = "commit3sha"

    commits = [make_commit(sha1), make_commit(sha2), make_commit(sha3)]

    from src.config import Config, DBConfig, LLMConfig
    config = Config(llm=LLMConfig(), db=DBConfig(path=str(tmp_path / "recall.db")))

    processed_batches = []

    def fake_extract(batch):
        processed_batches.extend([c.sha for c in batch])
        return []

    with (
        patch("src.indexer.indexer.walk_commits", return_value=commits),
        patch("src.indexer.indexer.extract_batch", side_effect=fake_extract),
    ):
        # Init with all 3 commits but we'll manually set last_sha to sha1
        from src.db.manager import DatabaseManager
        db = DatabaseManager(config)
        db.init_db()
        with db.connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                ("last_indexed_sha", sha1),
            )
            conn.commit()

        processed_batches.clear()
        result = run_sync(tmp_path, config)

    # Only sha2 and sha3 should have been processed
    assert sha1 not in processed_batches
    assert sha2 in processed_batches
    assert sha3 in processed_batches
    assert result["commits_processed"] == 2

    # Verify last_indexed_sha was updated to sha3
    db = DatabaseManager(config)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT value FROM metadata WHERE key = ?", ("last_indexed_sha",)
        ).fetchone()
    assert row["value"] == sha3


# ---------------------------------------------------------------------------
# Test 3: run_sync with no DB → delegates to run_init
# ---------------------------------------------------------------------------

def test_run_sync_no_db_delegates_to_init(tmp_path: Path):
    """When DB file does not exist, run_sync calls run_init path."""
    commits = [make_commit("sha_a"), make_commit("sha_b")]

    from src.config import Config, DBConfig, LLMConfig
    config = Config(llm=LLMConfig(), db=DBConfig(path=str(tmp_path / "recall.db")))

    init_called = []

    original_run_init = run_init

    def spy_init(repo_root, cfg=None):
        init_called.append(True)
        return original_run_init(repo_root, cfg)

    with (
        patch("src.indexer.indexer.walk_commits", return_value=commits),
        patch("src.indexer.indexer.extract_batch", return_value=[]),
        patch("src.indexer.indexer.run_init", side_effect=spy_init) as mock_init,
    ):
        result = run_sync(tmp_path, config)

    mock_init.assert_called_once()
    assert result["commits_processed"] == 2


# ---------------------------------------------------------------------------
# Test 4: run_init processes all commits, ignores existing last_indexed_sha
# ---------------------------------------------------------------------------

def test_run_init_processes_all_commits(tmp_path: Path):
    """run_init processes all commits and writes last_indexed_sha as the last sha."""
    sha1 = "init_sha1"
    sha2 = "init_sha2"
    sha3 = "init_sha3"

    commits = [make_commit(sha1), make_commit(sha2), make_commit(sha3)]

    from src.config import Config, DBConfig, LLMConfig
    config = Config(llm=LLMConfig(), db=DBConfig(path=str(tmp_path / "recall.db")))

    with (
        patch("src.indexer.indexer.walk_commits", return_value=commits),
        patch("src.indexer.indexer.extract_batch", return_value=FAKE_ENTITIES),
    ):
        result = run_init(tmp_path, config)

    assert result["commits_processed"] == 3

    # Verify last_indexed_sha was written as sha3 (last in oldest-first list)
    from src.db.manager import DatabaseManager
    db = DatabaseManager(config)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT value FROM metadata WHERE key = ?", ("last_indexed_sha",)
        ).fetchone()
    assert row["value"] == sha3


# ---------------------------------------------------------------------------
# Test 5: _commits_after_sha with unknown sha returns all commits
# ---------------------------------------------------------------------------

def test_commits_after_sha_not_found_returns_all():
    """_commits_after_sha with an unknown sha returns all commits as a safe fallback."""
    commits = [make_commit("sha_x"), make_commit("sha_y"), make_commit("sha_z")]
    result = _commits_after_sha(commits, "unknown_sha")
    assert result == commits

"""indexer.py — Incremental git history indexing control flow.

Entry points:
    run_init(repo_root)  — full rebuild, clears and repopulates DB
    run_sync(repo_root)  — incremental: only commits newer than last_indexed_sha
"""
from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from typing import Optional

import structlog

from src.config import Config, load_config
from src.db.manager import DatabaseManager
from src.extractor.engine import extract_batch
from src.extractor.git_walker import CommitRecord, batch_commits, walk_commits

logger = structlog.get_logger()

_LAST_SHA_KEY = "last_indexed_sha"


def _get_db(repo_root: Path, config: Config) -> DatabaseManager:
    """Return a DatabaseManager for config. Does NOT call init_db()."""
    return DatabaseManager(config)


def _read_last_sha(conn: sqlite3.Connection) -> str | None:
    """Read the last indexed SHA from the metadata table."""
    row = conn.execute(
        "SELECT value FROM metadata WHERE key = ?", (_LAST_SHA_KEY,)
    ).fetchone()
    return row["value"] if row is not None else None


def _write_last_sha(conn: sqlite3.Connection, sha: str) -> None:
    """Write the last indexed SHA to the metadata table."""
    conn.execute(
        "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
        (_LAST_SHA_KEY, sha),
    )
    conn.commit()


def _insert_entities(conn: sqlite3.Connection, entities: list[dict]) -> int:
    """Insert entity records idempotently. Returns count of rows actually inserted.

    Ensures the referenced commit row exists in the commits table before inserting
    each entity (FK constraint: entities.commit_sha REFERENCES commits.sha).
    """
    inserted = 0
    seen_shas: set[str] = set()

    for entity in entities:
        commit_sha = entity.get("commit_sha") or ""
        # Ensure parent commit row exists to satisfy FK constraint
        if commit_sha and commit_sha not in seen_shas:
            conn.execute(
                "INSERT OR IGNORE INTO commits (sha, message, author, date, files_changed)"
                " VALUES (?, ?, ?, ?, ?)",
                (commit_sha, "", "", "", "[]"),
            )
            seen_shas.add(commit_sha)

        entity_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{entity['type']}:{entity['name']}",
            )
        )
        cursor = conn.execute(
            "INSERT OR IGNORE INTO entities (id, type, name, content, commit_sha)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                entity_id,
                entity["type"],
                entity["name"],
                entity.get("content", ""),
                commit_sha if commit_sha else None,
            ),
        )
        inserted += cursor.rowcount
    conn.commit()
    return inserted


def _commits_after_sha(
    commits: list[CommitRecord], sha: str
) -> list[CommitRecord]:
    """Return commits that come after the commit with the given sha.

    Args:
        commits: Oldest-first list from walk_commits.
        sha: SHA of the last indexed commit.

    Returns:
        All commits after the matching commit, or all commits if sha not found
        (safe fallback — logs a warning).
    """
    for idx, commit in enumerate(commits):
        if commit.sha == sha:
            return commits[idx + 1 :]

    # sha not found — could be from before current history; process everything
    logger.warning("last_indexed_sha_not_found", sha=sha, total_commits=len(commits))
    return commits


def run_init(repo_root: Path, config: Optional[Config] = None) -> dict:
    """Full rebuild: walk all commits, extract entities, update last_indexed_sha.

    Args:
        repo_root: Path to the git repository root.
        config: Optional Config instance; loads from default path if not provided.

    Returns:
        Dict with keys 'commits_processed' and 'entities_inserted'.
    """
    config = config or load_config()
    db = _get_db(repo_root, config)
    db.init_db()

    commits = walk_commits(repo_root)
    batch_size = getattr(getattr(config, "indexer", None), "batch_size", 10)
    batches = batch_commits(commits, batch_size)
    total = len(commits)
    entities_inserted = 0
    commits_processed = 0

    with db.connect() as conn:
        # Clear any existing last_indexed_sha so this is a clean rebuild
        conn.execute("DELETE FROM metadata WHERE key = ?", (_LAST_SHA_KEY,))
        conn.commit()

        for i, batch in enumerate(batches):
            start = i * batch_size + 1
            end = min(start + len(batch) - 1, total)
            logger.info("indexing_batch", range=f"{start}–{end}", total=total)
            entities = extract_batch(batch)
            entities_inserted += _insert_entities(conn, entities)
            commits_processed += len(batch)

        if commits:
            # HEAD is the last commit in oldest-first order
            _write_last_sha(conn, commits[-1].sha)

    logger.info(
        "init_complete",
        commits_processed=commits_processed,
        entities_inserted=entities_inserted,
    )
    return {"commits_processed": commits_processed, "entities_inserted": entities_inserted}


def run_sync(repo_root: Path, config: Optional[Config] = None) -> dict:
    """Incremental sync: only process commits newer than last_indexed_sha.

    If no DB exists, delegates to run_init for a full rebuild.
    If no new commits exist after filtering, prints "0 commits to process" and exits.

    Args:
        repo_root: Path to the git repository root.
        config: Optional Config instance; loads from default path if not provided.

    Returns:
        Dict with keys 'commits_processed' and 'entities_inserted'.
    """
    config = config or load_config()
    db = _get_db(repo_root, config)

    # No DB yet — run a full init transparently
    if not db.get_db_path().exists():
        logger.info("no_db_found_running_init")
        return run_init(repo_root, config)

    db.init_db()

    with db.connect() as conn:
        last_sha = _read_last_sha(conn)

    all_commits = walk_commits(repo_root)

    if last_sha:
        new_commits = _commits_after_sha(all_commits, last_sha)
    else:
        # No cursor yet — process everything
        new_commits = all_commits

    if len(new_commits) == 0:
        print("0 commits to process")
        logger.info("sync_complete", commits_processed=0, entities_inserted=0)
        return {"commits_processed": 0, "entities_inserted": 0}

    batch_size = getattr(getattr(config, "indexer", None), "batch_size", 10)
    batches = batch_commits(new_commits, batch_size)
    total = len(new_commits)
    entities_inserted = 0
    commits_processed = 0

    with db.connect() as conn:
        for i, batch in enumerate(batches):
            start = i * batch_size + 1
            end = min(start + len(batch) - 1, total)
            logger.info("syncing_batch", range=f"{start}–{end}", total=total)
            entities = extract_batch(batch)
            entities_inserted += _insert_entities(conn, entities)
            commits_processed += len(batch)

        # Record the most recent processed commit as the new cursor
        _write_last_sha(conn, new_commits[-1].sha)

    logger.info(
        "sync_complete",
        commits_processed=commits_processed,
        entities_inserted=entities_inserted,
    )
    return {"commits_processed": commits_processed, "entities_inserted": entities_inserted}

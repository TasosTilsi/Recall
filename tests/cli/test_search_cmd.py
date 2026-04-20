"""Tests for src/cli/commands/search_cmd.py — TDD RED phase."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli.commands.search_cmd import app


runner = CliRunner()


def _make_db(tmp_path: Path, with_embeddings: bool = False) -> Path:
    """Create an in-memory-backed SQLite DB for search tests."""
    db_path = tmp_path / "recall.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS commits (
            sha         TEXT PRIMARY KEY,
            message     TEXT NOT NULL,
            author      TEXT NOT NULL,
            date        TEXT NOT NULL,
            files_changed TEXT NOT NULL DEFAULT '[]'
        );
        CREATE TABLE IF NOT EXISTS entities (
            id          TEXT PRIMARY KEY,
            type        TEXT NOT NULL,
            name        TEXT NOT NULL,
            content     TEXT NOT NULL DEFAULT '',
            commit_sha  TEXT REFERENCES commits(sha),
            tags        TEXT NOT NULL DEFAULT '[]',
            created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
        );
        CREATE TABLE IF NOT EXISTS backlinks (
            from_id      TEXT NOT NULL REFERENCES entities(id),
            to_id        TEXT NOT NULL REFERENCES entities(id),
            relationship TEXT NOT NULL,
            context      TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (from_id, to_id, relationship)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts
        USING fts5(name, content, content=entities, content_rowid=rowid, tokenize='porter unicode61');
        CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
            INSERT INTO entities_fts(rowid, name, content) VALUES (new.rowid, new.name, new.content);
        END;
    """)

    # Insert a test commit
    conn.execute(
        "INSERT INTO commits (sha, message, author, date) VALUES (?, ?, ?, ?)",
        ("abc123", "feat: add auth", "Alice", "2026-04-01T10:00:00Z"),
    )
    # Insert test entity
    conn.execute(
        "INSERT INTO entities (id, type, name, content, commit_sha) VALUES (?, ?, ?, ?, ?)",
        ("e1", "decision", "Use JWT for auth", "JWT tokens for stateless auth", "abc123"),
    )
    conn.execute(
        "INSERT INTO entities (id, type, name, content, commit_sha) VALUES (?, ?, ?, ?, ?)",
        ("e2", "pattern", "Repository pattern", "Abstracts data access", "abc123"),
    )
    # Insert a backlink: e2 uses e1
    conn.execute(
        "INSERT INTO backlinks (from_id, to_id, relationship, context) VALUES (?, ?, ?, ?)",
        ("e2", "e1", "uses", "repository uses auth decision"),
    )
    conn.commit()
    conn.close()
    return db_path


# Test 1: FTS search returns list of dicts with expected keys
def test_fts_search_returns_results(tmp_path):
    """FTS search returns entity_type, name, snippet, commit_sha, date fields."""
    db_path = _make_db(tmp_path)
    with patch("src.cli.commands.search_cmd._get_db_path", return_value=db_path):
        result = runner.invoke(app, ["JWT"])
    assert result.exit_code == 0
    output = result.output
    assert "decision" in output.lower() or "Use JWT for auth" in output
    assert "abc123" in output


# Test 2: --semantic flag with embeddings configured
def test_semantic_search_with_embeddings(tmp_path):
    """--semantic flag delegates to semantic search path when embeddings configured."""
    db_path = _make_db(tmp_path)
    mock_config = MagicMock()
    mock_config.embeddings = MagicMock()  # embeddings present
    mock_config.embeddings.provider = "ollama"
    mock_config.embeddings.model = "nomic-embed-text"
    mock_config.embeddings.url = "http://localhost:11434"

    with patch("src.cli.commands.search_cmd._get_db_path", return_value=db_path), \
         patch("src.cli.commands.search_cmd.load_config", return_value=mock_config), \
         patch("src.cli.commands.search_cmd._semantic_search", return_value=[]) as mock_sem:
        result = runner.invoke(app, ["JWT", "--semantic"])
    # exit 0 expected (no results prints "No results found" but still exits 0)
    assert result.exit_code == 0 or "Semantic" not in result.output
    mock_sem.assert_called_once()


# Test 3: --semantic flag with NO embeddings section raises error
def test_semantic_search_no_embeddings(tmp_path):
    """--semantic with no [embeddings] config prints error and exits 1."""
    db_path = _make_db(tmp_path)
    mock_config = MagicMock()
    mock_config.embeddings = None  # no embeddings

    with patch("src.cli.commands.search_cmd._get_db_path", return_value=db_path), \
         patch("src.cli.commands.search_cmd.load_config", return_value=mock_config):
        result = runner.invoke(app, ["JWT", "--semantic"])
    assert result.exit_code != 0
    assert "Semantic search requires [embeddings] in ~/.recall/config.toml" in result.output


# Test 4: --related flag appends backlinked entities
def test_related_flag_shows_backlinks(tmp_path):
    """--related flag appends one-hop backlinked entities with relationship type."""
    db_path = _make_db(tmp_path)
    with patch("src.cli.commands.search_cmd._get_db_path", return_value=db_path):
        result = runner.invoke(app, ["pattern", "--related"])
    assert result.exit_code == 0
    # The 'e2' entity (Repository pattern) should show its backlink to e1 (Use JWT for auth)
    output = result.output
    assert "->" in output or "uses" in output


# Test 5: no results prints "No results found for: <query>"
def test_no_results_message(tmp_path):
    """Empty results prints 'No results found for: <query>'."""
    db_path = _make_db(tmp_path)
    with patch("src.cli.commands.search_cmd._get_db_path", return_value=db_path):
        result = runner.invoke(app, ["xyzzy_nonexistent_query_12345"])
    assert result.exit_code == 0
    assert "No results found for: xyzzy_nonexistent_query_12345" in result.output

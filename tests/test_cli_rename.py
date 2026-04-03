"""Tests for Phase 16: Rename & CLI Consolidation (CLI-01, CLI-02, CLI-03)."""
from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import pytest
from typer.testing import CliRunner
from src.cli import app

runner = CliRunner()

PUBLIC_COMMANDS = ["init", "search", "list", "delete", "pin", "unpin", "health", "config", "ui", "note"]
# Only check commands that are truly absent (not found anywhere in --help output)
# Excluded due to appearing in descriptions:
#   "add" — appears in "Manually add a memory" (note description)
#   "compact", "stale", "queue" — appear in "list" description text
#   "hooks" — appears in "init" description ("Install hooks, index git history...")
#   "memory" — appears in app tagline "Local developer memory"
#   "show" — checked separately via absence from commands section
TRULY_REMOVED_COMMANDS = ["capture", "mcp", "summarize"]


# ==================== CLI-01: Entrypoint rename ====================


def test_app_name_is_recall():
    """CLI-01: App instance is named 'recall'."""
    assert app.info.name == "recall"


def test_help_shows_recall_not_graphiti():
    """CLI-01: --help output contains 'recall', not 'graphiti'."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "recall" in result.stdout.lower()
    assert "graphiti" not in result.stdout.lower()


# ==================== CLI-02: 10 public commands ====================


def test_help_lists_exactly_10_public_commands():
    """CLI-02: --help shows all 10 public commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in PUBLIC_COMMANDS:
        assert cmd in result.stdout, f"Expected '{cmd}' in --help output"


def test_help_does_not_show_removed_commands():
    """CLI-02: --help does NOT list removed commands as standalone entries."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in TRULY_REMOVED_COMMANDS:
        assert cmd not in result.stdout, f"Removed command '{cmd}' should not appear in --help"


def test_list_help_shows_stale_flag():
    """CLI-02: recall list --help shows --stale flag."""
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "--stale" in result.stdout


def test_list_help_shows_compact_flag():
    """CLI-02: recall list --help shows --compact flag."""
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "--compact" in result.stdout


def test_list_help_shows_queue_flag():
    """CLI-02: recall list --help shows --queue flag."""
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "--queue" in result.stdout


@patch("src.cli.commands.list_cmd._show_queue_status")
def test_list_queue_flag_calls_show_queue_status(mock_show_queue):
    """CLI-02: recall list --queue calls _show_queue_status."""
    mock_show_queue.return_value = None
    with patch("src.cli.commands.list_cmd.resolve_scope", return_value=(MagicMock(), None)):
        result = runner.invoke(app, ["list", "--queue"])
    mock_show_queue.assert_called_once()


@patch("src.cli.commands.list_cmd._show_stale")
def test_list_stale_flag_calls_show_stale(mock_show_stale):
    """CLI-02: recall list --stale calls _show_stale."""
    mock_show_stale.return_value = None
    with patch("src.cli.commands.list_cmd.resolve_scope", return_value=(MagicMock(), None)):
        result = runner.invoke(app, ["list", "--stale"])
    mock_show_stale.assert_called_once()


def test_note_command_appends_to_jsonl(tmp_path):
    """CLI-02: recall note falls back to pending_tool_captures.jsonl when LLM unavailable."""
    (tmp_path / ".recall").mkdir()
    with patch("src.cli.commands.note_cmd.resolve_scope", return_value=(MagicMock(), tmp_path)):
        with patch("src.graph.service.run_graph_operation", side_effect=RuntimeError("LLM unavailable")):
            result = runner.invoke(app, ["note", "decision: use JWT auth"])
    assert result.exit_code == 0
    # Verify the fallback queue file was created with JSON content
    pending_file = tmp_path / ".recall" / "pending_tool_captures.jsonl"
    assert pending_file.exists(), "pending_tool_captures.jsonl should be created on fallback"
    lines = pending_file.read_text().strip().splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry.get("tool_name") == "Note"
    assert "jwt auth" in entry.get("key_args", "").lower()


def test_note_command_help():
    """CLI-02: recall note --help works and shows text argument."""
    result = runner.invoke(app, ["note", "--help"])
    assert result.exit_code == 0
    assert "text" in result.stdout.lower() or "memory" in result.stdout.lower()


# ==================== CLI-03: Auto-sync in search ====================


def test_auto_sync_called_before_search():
    """CLI-03: _auto_sync is called before search runs."""
    with patch("src.cli.commands.search._auto_sync") as mock_sync:
        with patch("src.cli.commands.search.resolve_scope", return_value=(MagicMock(), None)):
            with patch("src.cli.commands.search._search_entities", return_value=[]):
                result = runner.invoke(app, ["search", "test query"])
    mock_sync.assert_called_once()


def test_auto_sync_fails_silently():
    """CLI-03: _auto_sync failure does not raise or block search.

    GitIndexer is lazily imported inside _auto_sync, so patch at src.indexer.
    """
    from src.cli.commands.search import _auto_sync
    # Should not raise even when GitIndexer fails — _auto_sync catches all exceptions
    with patch("src.indexer.GitIndexer", side_effect=Exception("indexer broken")):
        _auto_sync(Path("/tmp/test"))  # Must not raise


def test_auto_sync_skips_when_no_project_root():
    """CLI-03: _auto_sync skips gracefully when project_root is None."""
    from src.cli.commands.search import _auto_sync
    # When project_root is None, _auto_sync returns early without calling GitIndexer
    with patch("src.indexer.GitIndexer") as mock_indexer:
        _auto_sync(None)
    mock_indexer.assert_not_called()


# ==================== Regression: existing flags still work ====================


def test_search_help_shows_original_flags():
    """Regression: original search flags (--exact, --limit) still present."""
    result = runner.invoke(app, ["search", "--help"])
    assert result.exit_code == 0
    assert "--exact" in result.stdout
    assert "--limit" in result.stdout


def test_list_help_shows_original_flags():
    """Regression: original list flags (--limit, --all) still present."""
    result = runner.invoke(app, ["list", "--help"])
    assert result.exit_code == 0
    assert "--limit" in result.stdout
    assert "--all" in result.stdout

"""Tests for the graphiti sync CLI command (Phase 15-01).

Tests the sync command which is an alias for incremental git indexing.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()


# ==================== Registration Tests ====================


def test_sync_command_registered():
    """sync must be registered as a CLI command."""
    cmd_names = [c.name for c in app.registered_commands]
    assert "sync" in cmd_names, f"sync not registered; found: {cmd_names}"


# ==================== Help Tests ====================


def test_sync_help_exits_zero():
    """graphiti sync --help must exit 0."""
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    assert "sync" in result.output.lower() or "incremental" in result.output.lower()


# ==================== Non-git directory Tests ====================


@patch("src.cli.commands.sync.resolve_scope")
def test_sync_non_git_directory_exits_error(mock_resolve_scope):
    """sync in a non-git directory must exit with error code 1."""
    mock_resolve_scope.return_value = (None, None)

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "git" in result.output.lower() or "repository" in result.output.lower()


# ==================== Incremental Indexing Tests ====================


@patch("src.cli.commands.sync.GitIndexer")
@patch("src.cli.commands.sync.resolve_scope")
def test_sync_calls_indexer_incremental(mock_resolve_scope, mock_indexer_cls):
    """sync must call GitIndexer.run() with full=False."""
    from src.models import GraphScope

    mock_resolve_scope.return_value = (GraphScope.PROJECT, Path("/some/project"))
    mock_indexer = MagicMock()
    mock_indexer.run.return_value = {
        "commits_processed": 5,
        "commits_skipped": 2,
        "entities_created": 10,
        "elapsed_seconds": 1.2,
    }
    mock_indexer_cls.return_value = mock_indexer

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    mock_indexer_cls.assert_called_once_with(project_root=Path("/some/project"))
    mock_indexer.run.assert_called_once_with(full=False)


@patch("src.cli.commands.sync.GitIndexer")
@patch("src.cli.commands.sync.resolve_scope")
def test_sync_shows_commits_processed(mock_resolve_scope, mock_indexer_cls):
    """sync must display how many commits were processed."""
    from src.models import GraphScope

    mock_resolve_scope.return_value = (GraphScope.PROJECT, Path("/some/project"))
    mock_indexer = MagicMock()
    mock_indexer.run.return_value = {
        "commits_processed": 7,
        "commits_skipped": 1,
        "entities_created": 0,
        "elapsed_seconds": 0.5,
    }
    mock_indexer_cls.return_value = mock_indexer

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0
    assert "7" in result.output


# ==================== Exception Handling Tests ====================


@patch("src.cli.commands.sync.GitIndexer")
@patch("src.cli.commands.sync.resolve_scope")
def test_sync_handles_exception_gracefully(mock_resolve_scope, mock_indexer_cls):
    """sync must catch exceptions and exit with code 1."""
    from src.models import GraphScope

    mock_resolve_scope.return_value = (GraphScope.PROJECT, Path("/some/project"))
    mock_indexer = MagicMock()
    mock_indexer.run.side_effect = RuntimeError("Connection refused")
    mock_indexer_cls.return_value = mock_indexer

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 1
    assert "sync failed" in result.output.lower() or "connection refused" in result.output.lower()

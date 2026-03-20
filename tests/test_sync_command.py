"""Tests for the recall index CLI command (Phase 16).

The old `graphiti sync` command is removed in Phase 16. Incremental git
indexing is now available as the hidden `recall index` command:
  - `recall index`          incremental (new commits only)
  - `recall index --force`  full re-index from scratch

These tests replace the original sync-command tests.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()


# ==================== Registration Tests ====================


def test_index_command_registered():
    """index must be registered as a CLI command (hidden=True)."""
    all_names = [c.name for c in app.registered_commands]
    assert "index" in all_names, f"index not registered; found: {all_names}"


def test_sync_command_not_registered():
    """sync must NOT be registered — it was removed in Phase 16."""
    all_names = [c.name for c in app.registered_commands]
    assert "sync" not in all_names, f"sync still registered; Phase 16 should have removed it"


# ==================== Help Tests ====================


def test_index_help_exits_zero():
    """recall index --help must exit 0."""
    result = runner.invoke(app, ["index", "--help"])
    assert result.exit_code == 0
    assert "force" in result.output.lower() or "incremental" in result.output.lower()


# ==================== Non-git directory Tests ====================


@patch("src.cli.commands.index.resolve_scope")
def test_index_non_git_directory_exits_error(mock_resolve_scope):
    """index in a non-git directory must exit with error code 1."""
    mock_resolve_scope.return_value = (None, None)

    result = runner.invoke(app, ["index"])

    assert result.exit_code == 1
    assert "git" in result.output.lower() or "repository" in result.output.lower()


# ==================== Incremental Indexing Tests ====================


@patch("src.indexer.GitIndexer")
@patch("git.Repo")
@patch("src.cli.commands.index.resolve_scope")
def test_index_calls_indexer_incremental(mock_resolve_scope, mock_repo, mock_indexer_cls):
    """index must call GitIndexer.run() with full=False by default."""
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

    result = runner.invoke(app, ["index"])

    assert result.exit_code == 0
    mock_indexer_cls.assert_called_once_with(project_root=Path("/some/project"))
    call_kwargs = mock_indexer.run.call_args
    assert call_kwargs.kwargs.get("full") is False or (
        call_kwargs.args and call_kwargs.args[0] is False
    ), f"Expected full=False, got: {call_kwargs}"


@patch("src.indexer.GitIndexer")
@patch("git.Repo")
@patch("src.cli.commands.index.resolve_scope")
def test_index_shows_commits_processed(mock_resolve_scope, mock_repo, mock_indexer_cls):
    """index must display how many commits were processed."""
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

    result = runner.invoke(app, ["index"])

    assert result.exit_code == 0
    assert "7" in result.output


# ==================== Exception Handling Tests ====================


@patch("src.indexer.GitIndexer")
@patch("git.Repo")
@patch("src.cli.commands.index.resolve_scope")
def test_index_handles_exception_gracefully(mock_resolve_scope, mock_repo, mock_indexer_cls):
    """index must catch exceptions and exit with code 1."""
    from src.models import GraphScope

    mock_resolve_scope.return_value = (GraphScope.PROJECT, Path("/some/project"))
    mock_indexer = MagicMock()
    mock_indexer.run.side_effect = RuntimeError("Connection refused")
    mock_indexer_cls.return_value = mock_indexer

    result = runner.invoke(app, ["index"])

    assert result.exit_code == 1
    assert "index" in result.output.lower() or "connection refused" in result.output.lower()

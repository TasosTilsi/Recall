"""Tests for CLI foundation components.

Tests the CLI app instance, version handling, utils (typo suggestions, scope
resolution, exit codes), input handling, and output functions.
"""
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from src.cli import app
from src.cli.input import read_content
from src.cli.output import console, print_error, print_success
from src.cli.utils import (
    EXIT_BAD_ARGS,
    EXIT_ERROR,
    EXIT_SUCCESS,
    confirm_action,
    resolve_scope,
    suggest_command,
)
from src.models import GraphScope

# CliRunner for testing Typer apps
runner = CliRunner()


# ==================== App Tests ====================


def test_app_help():
    """Test --help flag shows all 10 public commands (Phase 16 rename)."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "recall" in result.stdout.lower()

    # All 10 public commands should appear in help (Phase 16 public surface)
    commands = ["search", "list", "delete", "config", "health", "init", "note", "pin", "unpin", "ui"]
    for cmd in commands:
        assert cmd in result.stdout


def test_app_no_args_shows_help():
    """Test no args shows help (no_args_is_help=True)."""
    result = runner.invoke(app, [])

    # Should show help text, not error
    assert "recall" in result.stdout.lower()
    assert "Commands:" in result.stdout or "Usage:" in result.stdout


def test_app_version():
    """Test --version flag shows version string."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "recall version" in result.stdout.lower() or "0.1.0" in result.stdout


# ==================== Utils Tests ====================


def test_suggest_command_search():
    """Test suggest_command for 'serch' -> 'search'."""
    suggestion = suggest_command("serch")
    assert suggestion == "search"


def test_suggest_command_delete():
    """Test suggest_command for 'delte' -> 'delete'."""
    suggestion = suggest_command("delte")
    assert suggestion == "delete"


def test_suggest_command_list():
    """Test suggest_command for 'lst' -> 'list'."""
    suggestion = suggest_command("lst")
    assert suggestion == "list"


def test_suggest_command_no_match():
    """Test suggest_command returns None for no match."""
    suggestion = suggest_command("xyz")
    assert suggestion is None


def test_exit_codes():
    """Test exit code constants are correct."""
    assert EXIT_SUCCESS == 0
    assert EXIT_ERROR == 1
    assert EXIT_BAD_ARGS == 2


def test_resolve_scope_global():
    """Test resolve_scope with --global flag."""
    scope, project_root = resolve_scope(global_flag=True)

    assert scope == GraphScope.GLOBAL
    assert project_root is None


def test_resolve_scope_both_flags_error():
    """Test resolve_scope raises error when both flags specified."""
    with pytest.raises(typer.BadParameter) as exc_info:
        resolve_scope(global_flag=True, project_flag=True)

    assert "both" in str(exc_info.value).lower()


@patch("src.cli.utils.GraphSelector.find_project_root")
def test_resolve_scope_project(mock_find_root):
    """Test resolve_scope with --project flag."""
    mock_root = Path("/fake/project")
    mock_find_root.return_value = mock_root

    scope, project_root = resolve_scope(project_flag=True)

    assert scope == GraphScope.PROJECT
    assert project_root == mock_root


@patch("src.cli.utils.GraphSelector.find_project_root")
def test_resolve_scope_project_not_in_repo(mock_find_root):
    """Test resolve_scope --project raises error when not in git repo."""
    mock_find_root.return_value = None

    with pytest.raises(typer.BadParameter) as exc_info:
        resolve_scope(project_flag=True)

    assert "git repository" in str(exc_info.value).lower()


@patch("src.cli.utils.GraphSelector.determine_scope")
def test_resolve_scope_auto_detect(mock_determine):
    """Test resolve_scope auto-detects when no flags."""
    mock_determine.return_value = (GraphScope.PROJECT, Path("/auto/project"))

    scope, project_root = resolve_scope()

    assert scope == GraphScope.PROJECT
    assert project_root == Path("/auto/project")
    mock_determine.assert_called_once()


def test_confirm_action_force():
    """Test confirm_action returns True when force=True."""
    result = confirm_action("Delete everything?", force=True)
    assert result is True


def test_confirm_action_no_force_declines():
    """Test confirm_action with user declining."""
    with patch("typer.confirm", return_value=False):
        result = confirm_action("Delete everything?", force=False)
        assert result is False


def test_confirm_action_no_force_accepts():
    """Test confirm_action with user accepting."""
    with patch("typer.confirm", return_value=True):
        result = confirm_action("Delete everything?", force=False)
        assert result is True


# ==================== Input Tests ====================


def test_read_content_positional():
    """Test read_content with positional argument."""
    content = read_content("hello world")
    assert content == "hello world"


def test_read_content_positional_takes_precedence():
    """Test positional arg takes precedence over stdin."""
    # Even if stdin is available, positional should be used
    content = read_content("from positional")
    assert content == "from positional"


@patch("sys.stdin")
def test_read_content_none_tty_raises(mock_stdin):
    """Test read_content raises when no content and stdin is TTY."""
    mock_stdin.isatty.return_value = True

    with pytest.raises(typer.BadParameter) as exc_info:
        read_content(None)

    assert "no content provided" in str(exc_info.value).lower()


@patch("sys.stdin")
def test_read_content_from_stdin(mock_stdin):
    """Test read_content reads from stdin when available."""
    mock_stdin.isatty.return_value = False
    mock_stdin.read.return_value = "  piped content  \n"
    mock_stdin.reconfigure = Mock()

    content = read_content(None)

    assert content == "piped content"
    mock_stdin.reconfigure.assert_called_once_with(encoding='utf-8', errors='replace')


@patch("sys.stdin")
def test_read_content_empty_stdin_raises(mock_stdin):
    """Test read_content raises when stdin is empty."""
    mock_stdin.isatty.return_value = False
    mock_stdin.read.return_value = "   \n  "
    mock_stdin.reconfigure = Mock()

    with pytest.raises(typer.BadParameter) as exc_info:
        read_content(None)

    assert "no content provided" in str(exc_info.value).lower()


# ==================== Output Tests ====================


def test_console_exists():
    """Test console singleton exists."""
    from src.cli.output import console
    assert console is not None


def test_print_success_runs():
    """Test print_success runs without exception."""
    # Just verify it doesn't crash
    print_success("test success message")


def test_print_error_runs():
    """Test print_error runs without exception."""
    # Just verify it doesn't crash
    print_error("test error message")


def test_print_error_with_suggestion():
    """Test print_error with suggestion parameter."""
    # Just verify it doesn't crash
    print_error("test error", suggestion="Try this instead")

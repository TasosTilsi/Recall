"""Tests for the `graphiti ui` CLI command.

RED scaffold (Plan 11-01) — all 4 tests fail with ImportError until
Plan 11-04 creates `src/cli/commands/ui.py`.

Covers: UI-01 (launch command), UI-02 (port config), UI-03 (scope flag).
"""
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

runner = CliRunner()


class TestUICommand:
    """Tests for the `graphiti ui` CLI command."""

    def _make_app(self):
        """Build a minimal Typer app wrapping ui_command — import happens here (RED)."""
        from src.cli.commands.ui import ui_command  # noqa: F401 — intentional RED

        app = typer.Typer()
        app.command()(ui_command)
        return app

    def test_help(self):
        """--help exits 0 and documents the --global flag."""
        app = self._make_app()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--global" in result.output

    def test_missing_static_dir(self, tmp_path):
        """When ui/out/ does not exist the command exits non-zero with a helpful message."""
        app = self._make_app()
        with patch("src.cli.commands.ui.Path") as mock_path_cls:
            mock_static = mock_path_cls.return_value.__truediv__.return_value
            mock_static.exists.return_value = False

            result = runner.invoke(app, [])

        assert result.exit_code != 0
        output = result.output.lower()
        assert any(kw in output for kw in ["static", "ui/out", "missing", "not found"])

    def test_port_conflict(self):
        """When the API port is already bound the command exits non-zero with a clear message."""
        app = self._make_app()
        with patch("socket.socket") as mock_socket_cls:
            mock_sock = mock_socket_cls.return_value.__enter__.return_value
            mock_sock.bind.side_effect = OSError("Address already in use")

            result = runner.invoke(app, [])

        assert result.exit_code != 0
        output = result.output
        assert any(kw in output for kw in ["in use", "conflict", "8765"])

    def test_global_flag(self):
        """--global flag is accepted without an argparse error; scope label includes 'global'."""
        app = self._make_app()
        with patch("src.cli.commands.ui.uvicorn") as mock_uvicorn, \
             patch("src.cli.commands.ui.subprocess") as mock_subprocess:
            mock_uvicorn.run.return_value = None
            mock_subprocess.Popen.return_value = None

            result = runner.invoke(app, ["--global"])

        # Must not be a usage error (exit code 2 means bad CLI args)
        assert result.exit_code != 2
        # Scope label must mention global somewhere in output
        assert "global" in result.output.lower()

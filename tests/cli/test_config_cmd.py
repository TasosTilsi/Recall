"""Tests for src/cli/commands/config_cmd.py — TDD RED phase."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from src.cli.commands.config_cmd import app


runner = CliRunner()


def _write_config(tmp_path: Path, content: str) -> Path:
    """Write a config.toml to tmp_path and return its path."""
    p = tmp_path / "config.toml"
    p.write_text(content)
    return p


SAMPLE_TOML = """\
[llm]
provider = "claude"
model = "claude-haiku-4-5-20251001"
url = ""
api_key = ""

[db]
path = ".recall/recall.db"
"""


# Test 1: config show reads and prints full config file
def test_config_show_prints_file(tmp_path):
    """config show reads ~/.recall/config.toml and prints its full raw contents."""
    config_path = _write_config(tmp_path, SAMPLE_TOML)
    with patch("src.cli.commands.config_cmd.CONFIG_PATH", config_path):
        result = runner.invoke(app, ["show"])
    assert result.exit_code == 0
    assert "[llm]" in result.output
    assert "claude" in result.output


# Test 2: config get llm.provider returns value
def test_config_get_dotted_key(tmp_path):
    """config get llm.provider returns 'claude'."""
    config_path = _write_config(tmp_path, SAMPLE_TOML)
    with patch("src.cli.commands.config_cmd.CONFIG_PATH", config_path):
        result = runner.invoke(app, ["get", "llm.provider"])
    assert result.exit_code == 0
    assert "claude" in result.output


# Test 3: config get missing.key prints error and exits 1
def test_config_get_missing_key(tmp_path):
    """config get missing.key prints 'Key not found: missing.key' and exits 1."""
    config_path = _write_config(tmp_path, SAMPLE_TOML)
    with patch("src.cli.commands.config_cmd.CONFIG_PATH", config_path):
        result = runner.invoke(app, ["get", "missing.key"])
    assert result.exit_code != 0
    assert "Key not found: missing.key" in result.output


# Test 4: config set writes value back to config file
def test_config_set_writes_value(tmp_path):
    """config set llm.provider openai writes value and prints confirmation."""
    config_path = _write_config(tmp_path, SAMPLE_TOML)
    with patch("src.cli.commands.config_cmd.CONFIG_PATH", config_path):
        result = runner.invoke(app, ["set", "llm.provider", "openai"])
    assert result.exit_code == 0
    assert "Set llm.provider = openai" in result.output
    # Verify file was actually updated
    import tomllib
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    assert data["llm"]["provider"] == "openai"


# Test 5: config set creates nested key that doesn't exist yet
def test_config_set_creates_nested_key(tmp_path):
    """config set on a nested key that doesn't exist creates it."""
    config_path = _write_config(tmp_path, SAMPLE_TOML)
    with patch("src.cli.commands.config_cmd.CONFIG_PATH", config_path):
        result = runner.invoke(app, ["set", "embeddings.provider", "ollama"])
    assert result.exit_code == 0
    assert "Set embeddings.provider = ollama" in result.output
    # Verify nested key was created
    import tomllib
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    assert data["embeddings"]["provider"] == "ollama"

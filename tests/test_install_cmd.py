"""Tests for src/cli/commands/install_cmd.py — recall install command."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_settings(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# install_mcp_global tests
# ---------------------------------------------------------------------------

def test_install_mcp_global_no_existing_settings(tmp_path, monkeypatch):
    """Test 1: No existing settings.json -> creates file with mcpServers.recall, returns mcp_registered=True."""
    settings_path = tmp_path / ".claude" / "settings.json"
    monkeypatch.setattr(
        "src.cli.commands.install_cmd.Path.home",
        lambda: tmp_path,
    )

    from src.cli.commands.install_cmd import install_mcp_global

    result = install_mcp_global(force=False)

    assert result["mcp_registered"] is True
    assert settings_path.exists()
    data = json.loads(settings_path.read_text())
    assert "recall" in data["mcpServers"]
    assert data["mcpServers"]["recall"]["command"] == "recall"
    assert data["mcpServers"]["recall"]["args"] == ["mcp", "serve"]


def test_install_mcp_global_already_present_no_force(tmp_path, monkeypatch):
    """Test 2: recall already in mcpServers, force=False -> no-op, returns mcp_registered=False."""
    settings_path = tmp_path / ".claude" / "settings.json"
    _write_settings(
        settings_path,
        {"mcpServers": {"recall": {"command": "recall", "args": ["mcp", "serve"]}}},
    )
    monkeypatch.setattr(
        "src.cli.commands.install_cmd.Path.home",
        lambda: tmp_path,
    )

    from importlib import reload
    import src.cli.commands.install_cmd as mod
    reload(mod)

    result = mod.install_mcp_global(force=False)

    assert result["mcp_registered"] is False
    # File should be unchanged
    data = json.loads(settings_path.read_text())
    assert "recall" in data["mcpServers"]


def test_install_mcp_global_force_overwrites(tmp_path, monkeypatch):
    """Test 3: force=True when already present -> overwrites, returns mcp_registered=True."""
    settings_path = tmp_path / ".claude" / "settings.json"
    _write_settings(
        settings_path,
        {"mcpServers": {"recall": {"command": "old-recall", "args": []}}},
    )
    monkeypatch.setattr(
        "src.cli.commands.install_cmd.Path.home",
        lambda: tmp_path,
    )

    from importlib import reload
    import src.cli.commands.install_cmd as mod
    reload(mod)

    result = mod.install_mcp_global(force=True)

    assert result["mcp_registered"] is True
    data = json.loads(settings_path.read_text())
    assert data["mcpServers"]["recall"]["command"] == "recall"
    assert data["mcpServers"]["recall"]["args"] == ["mcp", "serve"]


# ---------------------------------------------------------------------------
# ensure_recall_dir tests
# ---------------------------------------------------------------------------

def test_ensure_recall_dir_does_not_exist(tmp_path, monkeypatch):
    """Test 4: ~/.recall/ does not exist -> creates it, returns True."""
    monkeypatch.setattr(
        "src.cli.commands.install_cmd.Path.home",
        lambda: tmp_path,
    )

    from importlib import reload
    import src.cli.commands.install_cmd as mod
    reload(mod)

    result = mod.ensure_recall_dir()

    assert result is True
    assert (tmp_path / ".recall").is_dir()


def test_ensure_recall_dir_config_toml_not_overwritten(tmp_path, monkeypatch):
    """Test 5: ~/.recall/config.toml exists -> does NOT overwrite it, returns False."""
    recall_dir = tmp_path / ".recall"
    recall_dir.mkdir(parents=True)
    config_path = recall_dir / "config.toml"
    original_content = "[llm]\nprovider = 'ollama'\n"
    config_path.write_text(original_content)

    monkeypatch.setattr(
        "src.cli.commands.install_cmd.Path.home",
        lambda: tmp_path,
    )

    from importlib import reload
    import src.cli.commands.install_cmd as mod
    reload(mod)

    result = mod.ensure_recall_dir()

    assert result is False
    # config.toml must be untouched
    assert config_path.read_text() == original_content


def test_ensure_recall_dir_exists_no_config(tmp_path, monkeypatch):
    """Test 6: ~/.recall/ exists but no config.toml -> creates dir structure, returns False (no config touched)."""
    recall_dir = tmp_path / ".recall"
    recall_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "src.cli.commands.install_cmd.Path.home",
        lambda: tmp_path,
    )

    from importlib import reload
    import src.cli.commands.install_cmd as mod
    reload(mod)

    result = mod.ensure_recall_dir()

    assert result is False
    assert recall_dir.is_dir()
    assert not (recall_dir / "config.toml").exists()

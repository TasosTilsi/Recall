"""Tests for install_global_hooks() and is_global_hooks_installed() (Phase 15-01).

Tests the global ~/.claude/settings.json hook installation logic.
All tests use tmp_path to avoid touching the real settings file.
"""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.hooks.installer import (
    _is_graphiti_hook,
    install_global_hooks,
    is_global_hooks_installed,
)


# ==================== _is_graphiti_hook ====================


def test_is_graphiti_hook_detects_session_start():
    entry = {"hooks": [{"type": "command", "command": "python /some/path/session_start.py"}]}
    assert _is_graphiti_hook(entry) is True


def test_is_graphiti_hook_detects_inject_context():
    entry = {"hooks": [{"type": "command", "command": "python /some/path/inject_context.py"}]}
    assert _is_graphiti_hook(entry) is True


def test_is_graphiti_hook_detects_capture_entry():
    entry = {"hooks": [{"type": "command", "command": "python /some/path/capture_entry.py"}]}
    assert _is_graphiti_hook(entry) is True


def test_is_graphiti_hook_detects_session_stop():
    entry = {"hooks": [{"type": "command", "command": "python /some/path/session_stop.py"}]}
    assert _is_graphiti_hook(entry) is True


def test_is_graphiti_hook_false_for_unrelated():
    entry = {"hooks": [{"type": "command", "command": "python /other/tool/my_hook.py"}]}
    assert _is_graphiti_hook(entry) is False


def test_is_graphiti_hook_false_for_empty():
    assert _is_graphiti_hook({}) is False
    assert _is_graphiti_hook({"hooks": []}) is False


# ==================== install_global_hooks ====================


def test_install_global_hooks_creates_file_when_missing(tmp_path):
    """Creates settings.json from scratch with all 5 hook entries."""
    fake_settings = tmp_path / ".claude" / "settings.json"

    with patch("src.hooks.installer.Path.home", return_value=tmp_path):
        result = install_global_hooks()

    assert result is True
    assert fake_settings.exists()

    settings = json.loads(fake_settings.read_text())
    hooks = settings.get("hooks", {})

    for hook_type in ("SessionStart", "UserPromptSubmit", "PostToolUse", "PreCompact", "Stop"):
        assert hook_type in hooks, f"{hook_type} missing from hooks"
        entries = hooks[hook_type]
        assert any(_is_graphiti_hook(e) for e in entries), f"No graphiti entry in {hook_type}"


def test_install_global_hooks_preserves_non_graphiti_entries(tmp_path):
    """Non-graphiti existing entries survive install."""
    fake_settings_dir = tmp_path / ".claude"
    fake_settings_dir.mkdir(parents=True)
    fake_settings = fake_settings_dir / "settings.json"

    existing = {
        "hooks": {
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": "python /other/tool.py"}]
                }
            ]
        }
    }
    fake_settings.write_text(json.dumps(existing))

    with patch("src.hooks.installer.Path.home", return_value=tmp_path):
        result = install_global_hooks()

    assert result is True
    settings = json.loads(fake_settings.read_text())
    stop_entries = settings["hooks"]["Stop"]

    # Check both the graphiti hook AND the preserved non-graphiti hook are present
    commands = [h.get("command", "") for e in stop_entries for h in e.get("hooks", [])]
    assert any("session_stop.py" in cmd for cmd in commands), "graphiti hook missing"
    assert any("/other/tool.py" in cmd for cmd in commands), "non-graphiti hook was lost"


def test_install_global_hooks_replaces_existing_graphiti_entries(tmp_path):
    """Existing graphiti entries are replaced (clean overwrite semantics)."""
    fake_settings_dir = tmp_path / ".claude"
    fake_settings_dir.mkdir(parents=True)
    fake_settings = fake_settings_dir / "settings.json"

    old_python = "/old/python"
    existing = {
        "hooks": {
            "Stop": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": f"{old_python} /old/session_stop.py"}]
                }
            ]
        }
    }
    fake_settings.write_text(json.dumps(existing))

    with patch("src.hooks.installer.Path.home", return_value=tmp_path):
        result = install_global_hooks()

    assert result is True
    settings = json.loads(fake_settings.read_text())
    stop_entries = settings["hooks"]["Stop"]
    commands = [h.get("command", "") for e in stop_entries for h in e.get("hooks", [])]

    # Old python path must not appear; new sys.executable should be there
    assert not any(old_python in cmd for cmd in commands), "old graphiti entry not replaced"
    assert any("session_stop.py" in cmd for cmd in commands), "new graphiti entry missing"
    # Only one Stop entry (old was replaced, not duplicated)
    graphiti_stop_entries = [e for e in stop_entries if _is_graphiti_hook(e)]
    assert len(graphiti_stop_entries) == 1, f"Expected 1 graphiti Stop entry, got {len(graphiti_stop_entries)}"


def test_install_global_hooks_uses_sys_executable(tmp_path):
    """The installed commands use sys.executable as Python interpreter."""
    with patch("src.hooks.installer.Path.home", return_value=tmp_path):
        install_global_hooks()

    fake_settings = tmp_path / ".claude" / "settings.json"
    settings = json.loads(fake_settings.read_text())

    # Check one hook type for sys.executable
    session_start_entries = settings["hooks"].get("SessionStart", [])
    commands = [h.get("command", "") for e in session_start_entries for h in e.get("hooks", [])]
    assert any(sys.executable in cmd for cmd in commands), "sys.executable not used in commands"


# ==================== is_global_hooks_installed ====================


def test_is_global_hooks_installed_false_when_file_missing(tmp_path):
    with patch("src.hooks.installer.Path.home", return_value=tmp_path):
        assert is_global_hooks_installed() is False


def test_is_global_hooks_installed_true_after_install(tmp_path):
    with patch("src.hooks.installer.Path.home", return_value=tmp_path):
        install_global_hooks()
        assert is_global_hooks_installed() is True


def test_is_global_hooks_installed_false_without_all_hooks(tmp_path):
    """Returns False when only some hook types have graphiti entries."""
    fake_settings_dir = tmp_path / ".claude"
    fake_settings_dir.mkdir(parents=True)
    fake_settings = fake_settings_dir / "settings.json"

    # Only Stop has a graphiti entry, missing the other 4
    partial = {
        "hooks": {
            "Stop": [
                {"hooks": [{"type": "command", "command": "python /path/session_stop.py"}]}
            ]
        }
    }
    fake_settings.write_text(json.dumps(partial))

    with patch("src.hooks.installer.Path.home", return_value=tmp_path):
        assert is_global_hooks_installed() is False

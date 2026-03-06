"""Tests for configurable capture modes (Phase 10, Plans 02-03).

Covers:
- CAPT-01: decisions-only mode config + narrow prompt
- CAPT-02: decisions-and-patterns mode config + broad prompt
- CAPT-03: config show/set CLI (Plans 02 scope: config parsing only; CLI display in Plan 03)
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Task 1: LLMConfig capture_mode field + load_config() parsing
# ---------------------------------------------------------------------------

class TestCaptureModeConfig:
    """CAPT-01/02: load_config() parses [capture] mode correctly."""

    def test_decisions_only_from_toml(self, tmp_path):
        """[capture] mode = 'decisions-only' → config.capture_mode == 'decisions-only'."""
        toml_file = tmp_path / "llm.toml"
        toml_file.write_text('[capture]\nmode = "decisions-only"\n')

        from src.llm.config import load_config
        config = load_config(toml_file)
        assert config.capture_mode == "decisions-only"

    def test_decisions_and_patterns_from_toml(self, tmp_path):
        """[capture] mode = 'decisions-and-patterns' → config.capture_mode == 'decisions-and-patterns'."""
        toml_file = tmp_path / "llm.toml"
        toml_file.write_text('[capture]\nmode = "decisions-and-patterns"\n')

        from src.llm.config import load_config
        config = load_config(toml_file)
        assert config.capture_mode == "decisions-and-patterns"

    def test_default_is_decisions_only(self, tmp_path):
        """No [capture] section → config.capture_mode == 'decisions-only'."""
        toml_file = tmp_path / "llm.toml"
        toml_file.write_text("# no capture section\n")

        from src.llm.config import load_config
        config = load_config(toml_file)
        assert config.capture_mode == "decisions-only"

    def test_invalid_mode_falls_back(self, tmp_path):
        """Invalid mode value → falls back to 'decisions-only' with structlog warning."""
        toml_file = tmp_path / "llm.toml"
        toml_file.write_text('[capture]\nmode = "everything"\n')

        with patch("structlog.get_logger") as mock_logger_factory:
            mock_logger = MagicMock()
            mock_logger_factory.return_value = mock_logger

            from src.llm import config as config_module
            import importlib
            importlib.reload(config_module)

            config = config_module.load_config(toml_file)

        assert config.capture_mode == "decisions-only"


# ---------------------------------------------------------------------------
# Task 2: Dual prompt constants + capture_mode param in summarize_batch()
# ---------------------------------------------------------------------------

class TestCaptureModeSelection:
    """CAPT-01/02: summarize_batch() selects narrow vs broad prompt."""

    def test_decisions_only_prompt_excludes_bug_fixes_and_deps(self):
        """decisions-only → LLM prompt does NOT contain 'Bug Fixes' or 'Dependencies'."""
        with patch("src.capture.summarizer.chat") as mock_chat, \
             patch("src.capture.summarizer.sanitize_content") as mock_sanitize:
            mock_sanitize.return_value = MagicMock(
                sanitized_content="safe content",
                was_modified=False,
                findings=[],
            )
            mock_chat.return_value = {"message": {"content": "summary text"}}

            from src.capture.summarizer import summarize_batch
            asyncio.run(summarize_batch(["some content"], capture_mode="decisions-only"))

            prompt_used = mock_chat.call_args[1]["messages"][0]["content"]
            assert "Bug Fixes" not in prompt_used
            assert "Dependencies" not in prompt_used

    def test_decisions_and_patterns_prompt_includes_bug_fixes_and_deps(self):
        """decisions-and-patterns → LLM prompt DOES contain 'Bug Fixes & Root Causes' and 'Dependencies & Config'."""
        with patch("src.capture.summarizer.chat") as mock_chat, \
             patch("src.capture.summarizer.sanitize_content") as mock_sanitize:
            mock_sanitize.return_value = MagicMock(
                sanitized_content="safe content",
                was_modified=False,
                findings=[],
            )
            mock_chat.return_value = {"message": {"content": "summary text"}}

            from src.capture.summarizer import summarize_batch
            asyncio.run(summarize_batch(["some content"], capture_mode="decisions-and-patterns"))

            prompt_used = mock_chat.call_args[1]["messages"][0]["content"]
            assert "Bug Fixes & Root Causes" in prompt_used
            assert "Dependencies & Config" in prompt_used


class TestSecurityGate:
    """Security gate (sanitize_content) runs unconditionally regardless of mode."""

    def test_security_gate_is_unconditional(self):
        """sanitize_content() is called exactly once regardless of capture_mode."""
        with patch("src.capture.summarizer.sanitize_content") as mock_sanitize, \
             patch("src.capture.summarizer.chat") as mock_chat:
            mock_sanitize.return_value = MagicMock(
                sanitized_content="safe",
                was_modified=False,
                findings=[],
            )
            mock_chat.return_value = {"message": {"content": "summary"}}

            from src.capture.summarizer import summarize_batch
            asyncio.run(summarize_batch(["secret content"], capture_mode="decisions-and-patterns"))

            mock_sanitize.assert_called_once()


# ---------------------------------------------------------------------------
# Task 3 scope (Plan 03): CLI config show/set — placeholder tests
# These will be implemented in 10-03-PLAN.md
# ---------------------------------------------------------------------------

class TestConfigShow:
    """CAPT-03: graphiti config show contains Capture/Retention sections. (Plan 03 scope)"""

    def test_config_show_has_capture_section(self):
        pytest.skip("Implemented in Plan 10-03")

    def test_config_show_has_retention_section(self):
        pytest.skip("Implemented in Plan 10-03")


class TestConfigSet:
    """CAPT-03: graphiti config --set capture.mode validates input. (Plan 03 scope)"""

    def test_set_valid_mode(self):
        pytest.skip("Implemented in Plan 10-03")

    def test_set_invalid_mode_rejected(self):
        pytest.skip("Implemented in Plan 10-03")

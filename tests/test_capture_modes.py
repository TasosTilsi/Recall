"""Tests for Phase 10 capture mode feature.

Wave 0 — RED phase: All 11 tests must FAIL on current codebase because:
- BATCH_SUMMARIZATION_PROMPT_NARROW and BATCH_SUMMARIZATION_PROMPT_BROAD don't exist yet
- summarize_batch() doesn't accept capture_mode param yet
- LLMConfig doesn't have capture_mode field yet
- config show table lacks Capture Settings / Retention Settings sections
- VALID_CONFIG_KEYS lacks capture.mode and retention.retention_days

Requirements covered:
- CAPT-01: capture_mode field in LLMConfig, loaded from [capture] section in TOML
- CAPT-02: summarize_batch() uses NARROW or BROAD prompt based on capture_mode
- CAPT-03: Security gate unconditional; config show/set support new keys
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner


# ---------------------------------------------------------------------------
# TestCaptureModeConfig (CAPT-01)
# ---------------------------------------------------------------------------


class TestCaptureModeConfig:
    """load_config() reads [capture] mode from TOML and maps to capture_mode field."""

    def test_decisions_only_from_toml(self, tmp_path):
        """[capture] mode = 'decisions-only' -> config.capture_mode == 'decisions-only'."""
        from src.llm.config import load_config

        toml_file = tmp_path / "llm.toml"
        toml_file.write_text('[capture]\nmode = "decisions-only"\n')

        config = load_config(config_path=toml_file)

        assert config.capture_mode == "decisions-only"

    def test_decisions_and_patterns_from_toml(self, tmp_path):
        """[capture] mode = 'decisions-and-patterns' -> config.capture_mode == 'decisions-and-patterns'."""
        from src.llm.config import load_config

        toml_file = tmp_path / "llm.toml"
        toml_file.write_text('[capture]\nmode = "decisions-and-patterns"\n')

        config = load_config(config_path=toml_file)

        assert config.capture_mode == "decisions-and-patterns"

    def test_default_is_decisions_only(self, tmp_path):
        """No [capture] section -> config.capture_mode defaults to 'decisions-only'."""
        from src.llm.config import load_config

        toml_file = tmp_path / "llm.toml"
        toml_file.write_text("# no capture section\n")

        config = load_config(config_path=toml_file)

        assert config.capture_mode == "decisions-only"

    def test_invalid_mode_falls_back(self, tmp_path):
        """[capture] mode = 'invalid' -> falls back to 'decisions-only'."""
        from src.llm.config import load_config

        toml_file = tmp_path / "llm.toml"
        toml_file.write_text('[capture]\nmode = "invalid"\n')

        config = load_config(config_path=toml_file)

        assert config.capture_mode == "decisions-only"


# ---------------------------------------------------------------------------
# TestCaptureModeSelection (CAPT-02)
# ---------------------------------------------------------------------------


class TestCaptureModeSelection:
    """summarize_batch() selects the correct LLM prompt based on capture_mode."""

    def test_decisions_only_prompt(self):
        """summarize_batch(capture_mode='decisions-only') calls LLM with NARROW prompt.

        NARROW prompt must NOT contain 'Bug Fixes' or 'Dependencies'.
        """
        with patch("src.capture.summarizer.sanitize_content") as mock_sanitize, \
             patch("src.capture.summarizer.chat") as mock_chat:
            mock_sanitize.return_value = MagicMock(
                sanitized_content="safe content",
                was_modified=False,
                findings=[],
            )
            mock_chat.return_value = {"message": {"content": "summary text"}}

            from src.capture.summarizer import summarize_batch

            asyncio.run(summarize_batch(["commit message 1"], capture_mode="decisions-only"))

        assert mock_chat.called, "chat() should have been called"
        messages = mock_chat.call_args[1]["messages"]
        prompt_text = " ".join(m["content"] for m in messages if "content" in m)

        assert "Bug Fixes" not in prompt_text, \
            "NARROW prompt should not contain 'Bug Fixes'"
        assert "Dependencies" not in prompt_text, \
            "NARROW prompt should not contain 'Dependencies'"

    def test_decisions_and_patterns_prompt(self):
        """summarize_batch(capture_mode='decisions-and-patterns') calls LLM with BROAD prompt.

        BROAD prompt must contain 'Bug Fixes & Root Causes' and 'Dependencies & Config'.
        """
        with patch("src.capture.summarizer.sanitize_content") as mock_sanitize, \
             patch("src.capture.summarizer.chat") as mock_chat:
            mock_sanitize.return_value = MagicMock(
                sanitized_content="safe content",
                was_modified=False,
                findings=[],
            )
            mock_chat.return_value = {"message": {"content": "summary text"}}

            from src.capture.summarizer import summarize_batch

            asyncio.run(
                summarize_batch(
                    ["commit message 1"],
                    capture_mode="decisions-and-patterns",
                )
            )

        assert mock_chat.called, "chat() should have been called"
        messages = mock_chat.call_args[1]["messages"]
        prompt_text = " ".join(m["content"] for m in messages if "content" in m)

        assert "Bug Fixes & Root Causes" in prompt_text, \
            "BROAD prompt should contain 'Bug Fixes & Root Causes'"
        assert "Dependencies & Config" in prompt_text, \
            "BROAD prompt should contain 'Dependencies & Config'"


# ---------------------------------------------------------------------------
# TestSecurityGate (CAPT-03)
# ---------------------------------------------------------------------------


class TestSecurityGate:
    """Security gate (sanitize_content) runs unconditionally regardless of capture_mode."""

    def test_security_gate_is_unconditional(self):
        """sanitize_content is called exactly once regardless of capture_mode value."""
        with patch("src.capture.summarizer.sanitize_content") as mock_sanitize, \
             patch("src.capture.summarizer.chat") as mock_chat:
            mock_sanitize.return_value = MagicMock(
                sanitized_content="safe",
                was_modified=False,
                findings=[],
            )
            mock_chat.return_value = {"message": {"content": "summary"}}

            from src.capture.summarizer import summarize_batch

            asyncio.run(
                summarize_batch(
                    ["some content"],
                    capture_mode="decisions-only",
                )
            )

        mock_sanitize.assert_called_once()


# ---------------------------------------------------------------------------
# TestConfigShow (CAPT-03 — CLI display)
# ---------------------------------------------------------------------------


class TestConfigShow:
    """CLI `graphiti config` shows Capture Settings and Retention Settings sections."""

    def test_config_show_has_capture_section(self):
        """CLI output of `graphiti config` contains 'Capture Settings' and 'capture.mode'."""
        from src.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["config"])

        output = result.output
        assert "Capture Settings" in output, \
            f"Expected 'Capture Settings' in output, got:\n{output}"
        assert "capture.mode" in output, \
            f"Expected 'capture.mode' in output, got:\n{output}"

    def test_config_show_has_retention_section(self):
        """CLI output of `graphiti config` contains 'Retention Settings' and 'retention.retention_days'."""
        from src.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["config"])

        output = result.output
        assert "Retention Settings" in output, \
            f"Expected 'Retention Settings' in output, got:\n{output}"
        assert "retention.retention_days" in output, \
            f"Expected 'retention.retention_days' in output, got:\n{output}"


# ---------------------------------------------------------------------------
# TestConfigSet (CAPT-03 — CLI set/validate)
# ---------------------------------------------------------------------------


class TestConfigSet:
    """CLI `graphiti config --set` accepts capture.mode with validation."""

    def test_set_valid_mode(self, tmp_path):
        """graphiti config --set capture.mode=decisions-and-patterns exits 0 and writes TOML."""
        from src.cli import app

        config_file = tmp_path / "llm.toml"

        runner = CliRunner()
        with patch("src.cli.commands.config._get_config_path", return_value=config_file):
            result = runner.invoke(
                app,
                ["config", "--set", "capture.mode=decisions-and-patterns"],
            )

        assert result.exit_code == 0, \
            f"Expected exit code 0, got {result.exit_code}. Output:\n{result.output}"
        assert config_file.exists(), "TOML file should have been written"
        content = config_file.read_text()
        assert "decisions-and-patterns" in content, \
            f"Expected 'decisions-and-patterns' in written TOML:\n{content}"

    def test_set_invalid_mode_rejected(self, tmp_path):
        """graphiti config --set capture.mode=invalid exits non-zero and prints 'Valid values'."""
        from src.cli import app

        config_file = tmp_path / "llm.toml"

        runner = CliRunner()
        with patch("src.cli.commands.config._get_config_path", return_value=config_file):
            result = runner.invoke(
                app,
                ["config", "--set", "capture.mode=invalid"],
            )

        assert result.exit_code != 0, \
            f"Expected non-zero exit for invalid mode, got {result.exit_code}. Output:\n{result.output}"
        assert "Valid values" in result.output, \
            f"Expected 'Valid values' in output, got:\n{result.output}"


# ---------------------------------------------------------------------------
# TestIndexerCaptureMode (CAPT-01/CAPT-02 — indexer pipeline)
# ---------------------------------------------------------------------------


class TestIndexerCaptureMode:
    """CAPT-01/CAPT-02: graphiti index respects capture_mode via extract_commit_knowledge."""

    def test_indexer_decisions_only_omits_bugs_and_deps(self):
        """decisions-only mode: free-form prompt does not mention bugs or dependencies."""
        import asyncio
        from src.indexer.extraction import extract_commit_knowledge
        from unittest.mock import AsyncMock, MagicMock
        import datetime

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock()

        asyncio.run(extract_commit_knowledge(
            commit_sha="abc1234",
            commit_message="refactor: clean up imports",
            commit_author="dev",
            diff_content="-import os\n+import sys",
            instance=mock_graphiti,
            group_id="test-group",
            reference_time=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            capture_mode="decisions-only",
        ))

        # Collect all episode bodies passed to add_episode
        call_bodies = [
            call.kwargs.get("episode_body", "") or (call.args[1] if call.args else "")
            for call in mock_graphiti.add_episode.call_args_list
        ]
        freeform_body = next(
            (b for b in call_bodies if "freeform" in (mock_graphiti.add_episode.call_args_list[call_bodies.index(b)].kwargs.get("name", "") or "")),
            call_bodies[-1] if call_bodies else "",
        )
        # The free-form episode body should not contain bugs/deps focus
        assert "bugs fixed" not in freeform_body.lower()
        assert "dependencies introduced" not in freeform_body.lower()

    def test_indexer_decisions_and_patterns_includes_bugs_and_deps(self):
        """decisions-and-patterns mode: free-form prompt includes bugs and dependencies."""
        import asyncio
        from src.indexer.extraction import extract_commit_knowledge
        from unittest.mock import AsyncMock, MagicMock
        import datetime

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock()

        asyncio.run(extract_commit_knowledge(
            commit_sha="def5678",
            commit_message="fix: resolve null pointer in auth",
            commit_author="dev",
            diff_content="+if user is not None:",
            instance=mock_graphiti,
            group_id="test-group",
            reference_time=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            capture_mode="decisions-and-patterns",
        ))

        call_bodies = [
            call.kwargs.get("episode_body", "")
            for call in mock_graphiti.add_episode.call_args_list
        ]
        # At least one call body must mention bugs and dependencies
        combined = " ".join(call_bodies).lower()
        assert "bugs fixed" in combined
        assert "dependencies introduced" in combined

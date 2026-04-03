"""Tests for Phase 21 knowledge quality uplift — SC-2, SC-3, SC-4, SC-5 coverage.

SC-2: Code block entities extracted from git diffs and embedded in episode body.
SC-3: Code context preserved in episode body (code block strings in Entities line).
SC-4: Semantic relationship verbs (MODIFIES, INTRODUCES, etc.) in prompt + episode body.
SC-5: UI parseCodeBlockMeta parser (verified via file read; TS tests in parseCodeBlockMeta.test.ts).
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from src.indexer.extraction import (
    BATCH_EXTRACTION_PROMPT,
    extract_commits_batch,
)


class TestBatchPromptCodeBlocks:
    """SC-2: BATCH_EXTRACTION_PROMPT instructs model to extract code blocks."""

    def test_prompt_contains_code_block_instruction(self):
        """Prompt must contain 'Code Block:' instruction."""
        assert "Code Block:" in BATCH_EXTRACTION_PROMPT, (
            "BATCH_EXTRACTION_PROMPT must contain 'Code Block:' to instruct LLM to extract code entities"
        )

    def test_prompt_contains_file_language_type_fields(self):
        """Prompt must mention File:, Language:, and Type: fields."""
        assert "File:" in BATCH_EXTRACTION_PROMPT, "Prompt must contain 'File:' field"
        assert "Language:" in BATCH_EXTRACTION_PROMPT, "Prompt must contain 'Language:' field"
        assert "Type:" in BATCH_EXTRACTION_PROMPT, "Prompt must contain 'Type:' field"

    def test_prompt_contains_pipe_delimited_example(self):
        """Prompt must include a pipe-delimited example with ' | ' separator."""
        assert " | " in BATCH_EXTRACTION_PROMPT, (
            "BATCH_EXTRACTION_PROMPT must include pipe-delimited format example"
        )

    def test_prompt_format_placeholders_work(self):
        """Calling .format(commits_block=..., count=...) must not raise KeyError."""
        try:
            result = BATCH_EXTRACTION_PROMPT.format(commits_block="test commit", count=1)
            assert "test commit" in result
            assert "1" in result
        except KeyError as e:
            raise AssertionError(f"BATCH_EXTRACTION_PROMPT has unexpected placeholder: {e}") from e


class TestBatchPromptSemanticVerbs:
    """SC-4: BATCH_EXTRACTION_PROMPT steers LLM toward semantic relationship verbs."""

    REQUIRED_VERBS = [
        "MODIFIES",
        "INTRODUCES",
        "FIXES",
        "DEPENDS_ON",
        "REMOVES",
        "REFACTORS",
        "TESTS",
    ]

    def test_prompt_contains_all_seven_verbs(self):
        """All 7 semantic relationship verbs must appear in BATCH_EXTRACTION_PROMPT."""
        missing = [v for v in self.REQUIRED_VERBS if v not in BATCH_EXTRACTION_PROMPT]
        assert not missing, (
            f"BATCH_EXTRACTION_PROMPT is missing these semantic verbs: {missing}"
        )


class TestEpisodeBodyCodeBlocks:
    """SC-3: Code block entities are preserved in the episode body built by extract_commits_batch."""

    def _make_batch(self, n=1):
        return [
            (
                f"abc{i:04d}000",
                f"feat: add feature {i}",
                f"dev{i}",
                f"diff content {i}",
                datetime(2026, 4, i + 1, tzinfo=timezone.utc),
            )
            for i in range(n)
        ]

    def test_code_block_entity_in_episode_body(self):
        """A structured code block string in entities must appear in the episode_body Entities line."""
        batch = self._make_batch(1)
        mock_instance = MagicMock()
        mock_instance.add_episode = AsyncMock()

        code_block_entity = (
            "Code Block: process_queue | File: src/queue/worker.py | Language: Python | Type: function"
        )
        claude_result = json.dumps([
            {
                "sha": "abc0000",
                "entities": ["BackgroundWorker", code_block_entity],
                "relationships": ["Commit abc0000 INTRODUCES BackgroundWorker"],
                "summary": "Adds async background worker.",
            }
        ])

        with patch(
            "src.llm.claude_cli_client._claude_p",
            new_callable=AsyncMock,
            return_value=claude_result,
        ):
            results = asyncio.run(
                extract_commits_batch(batch, mock_instance, "group_test")
            )

        assert len(results) == 1
        assert results[0]["passes"] == 1

        # Inspect the episode_body kwarg passed to add_episode
        call_kwargs = mock_instance.add_episode.call_args_list[0].kwargs
        episode_body = call_kwargs["episode_body"]

        assert code_block_entity in episode_body, (
            f"Code block entity string must appear in episode_body Entities line.\n"
            f"episode_body was:\n{episode_body}"
        )

    def test_multiple_code_blocks_joined(self):
        """Multiple code block entities must be comma-separated in the Entities line."""
        batch = self._make_batch(1)
        mock_instance = MagicMock()
        mock_instance.add_episode = AsyncMock()

        cb1 = "Code Block: fn_a | File: src/a.py | Language: Python | Type: function"
        cb2 = "Code Block: ClassB | File: src/b.py | Language: Python | Type: class"

        claude_result = json.dumps([
            {
                "sha": "abc0000",
                "entities": [cb1, cb2],
                "relationships": [],
                "summary": "Adds two code constructs.",
            }
        ])

        with patch(
            "src.llm.claude_cli_client._claude_p",
            new_callable=AsyncMock,
            return_value=claude_result,
        ):
            results = asyncio.run(
                extract_commits_batch(batch, mock_instance, "group_test")
            )

        assert results[0]["passes"] == 1
        call_kwargs = mock_instance.add_episode.call_args_list[0].kwargs
        episode_body = call_kwargs["episode_body"]

        # Both code block strings must appear; they are joined by ", "
        assert cb1 in episode_body, f"First code block entity must appear in episode_body:\n{episode_body}"
        assert cb2 in episode_body, f"Second code block entity must appear in episode_body:\n{episode_body}"
        assert f"{cb1}, {cb2}" in episode_body, (
            f"Code block entities must be comma-separated:\n{episode_body}"
        )


class TestRelationshipVocab:
    """SC-4: Semantic verb strings are preserved in the episode body Relationships line."""

    def _make_batch(self, n=1):
        return [
            (
                f"def{i:04d}000",
                f"fix: patch commit {i}",
                f"author{i}",
                f"diff {i}",
                datetime(2026, 4, i + 1, tzinfo=timezone.utc),
            )
            for i in range(n)
        ]

    def test_semantic_verb_in_episode_body(self):
        """Semantic verb (MODIFIES) in extracted relationships must appear in episode_body."""
        batch = self._make_batch(1)
        mock_instance = MagicMock()
        mock_instance.add_episode = AsyncMock()

        relationship = "Commit def0000 MODIFIES function process_queue"
        claude_result = json.dumps([
            {
                "sha": "def0000",
                "entities": ["process_queue"],
                "relationships": [relationship],
                "summary": "Modifies queue function.",
            }
        ])

        with patch(
            "src.llm.claude_cli_client._claude_p",
            new_callable=AsyncMock,
            return_value=claude_result,
        ):
            results = asyncio.run(
                extract_commits_batch(batch, mock_instance, "grp")
            )

        assert results[0]["passes"] == 1
        call_kwargs = mock_instance.add_episode.call_args_list[0].kwargs
        episode_body = call_kwargs["episode_body"]

        assert relationship in episode_body, (
            f"Relationship string with semantic verb must appear in episode_body Relationships line.\n"
            f"episode_body was:\n{episode_body}"
        )


class TestColorMap:
    """SC-5: colors.ts defines Function and Class entity type color keys (file read check)."""

    COLORS_FILE = os.path.join(
        os.path.dirname(__file__),
        "..",
        "ui",
        "src",
        "lib",
        "colors.ts",
    )

    def _read_colors_ts(self) -> str:
        path = os.path.normpath(self.COLORS_FILE)
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_function_color_exists(self):
        """ENTITY_TYPE_COLORS must contain a 'Function' key in colors.ts."""
        content = self._read_colors_ts()
        assert "Function" in content, (
            "ui/src/lib/colors.ts must define a 'Function' key in ENTITY_TYPE_COLORS"
        )

    def test_class_color_exists(self):
        """ENTITY_TYPE_COLORS must contain a 'Class' key in colors.ts."""
        content = self._read_colors_ts()
        assert "Class" in content, (
            "ui/src/lib/colors.ts must define a 'Class' key in ENTITY_TYPE_COLORS"
        )

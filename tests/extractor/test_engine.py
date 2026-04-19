"""Tests for src/extractor/engine.py — extract_batch() function.

Tests cover:
- Happy path: mock subprocess returns valid JSON, entities normalized
- Invalid entity types are dropped
- Entity names are lowercased and stripped
- Malformed JSON returns [] without raising
- Subprocess CalledProcessError returns []
- Subprocess TimeoutExpired returns []
- Empty batch raises ValueError
- commit_sha is set on every returned entity from batch[0].sha
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.extractor.engine import extract_batch
from src.extractor.git_walker import CommitRecord
from src.extractor.prompt import VALID_ENTITY_TYPES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_commit(sha: str = "abc1234567890", msg: str = "add feature") -> CommitRecord:
    return CommitRecord(
        sha=sha,
        short_sha=sha[:7],
        author="Test Author",
        date=datetime(2026, 1, 1),
        message=msg,
        diff="--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new",
    )


def _make_valid_response(entities: list[dict]) -> str:
    """Serialise a list of entity dicts into the expected LLM JSON response."""
    return json.dumps({"entities": entities})


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


class TestExtractBatchHappyPath:
    """extract_batch returns correctly normalised EntityRecord dicts on success."""

    def test_returns_entities_from_valid_json(self):
        commit = _make_commit("abc1234567890abcdef")
        raw = _make_valid_response(
            [
                {
                    "type": "decision",
                    "name": "use sqlite",
                    "content": "chose sqlite for storage",
                    "commit_sha": "abc1234",
                }
            ]
        )
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert len(result) == 1
        assert result[0]["type"] == "decision"
        assert result[0]["name"] == "use sqlite"

    def test_commit_sha_set_to_batch_first_commit_sha(self):
        """commit_sha on each entity must equal batch[0].sha."""
        commit1 = _make_commit("firstsha1234567890abc")
        commit2 = _make_commit("secondsha123456789abc")
        raw = _make_valid_response(
            [
                {
                    "type": "pattern",
                    "name": "repository pattern",
                    "content": "used repo pattern",
                    "commit_sha": "whatever",
                }
            ]
        )
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit1, commit2])

        assert result[0]["commit_sha"] == commit1.sha

    def test_multiple_entities_returned(self):
        commit = _make_commit()
        raw = _make_valid_response(
            [
                {"type": "decision", "name": "pick postgres", "content": "db choice", "commit_sha": "abc"},
                {"type": "bug_fix", "name": "fix null ptr", "content": "null fix", "commit_sha": "abc"},
            ]
        )
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert len(result) == 2


# ---------------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------------


class TestNormalization:
    """Entity names must be lowercased and stripped before return."""

    def test_entity_name_is_lowercased(self):
        commit = _make_commit()
        raw = _make_valid_response(
            [{"type": "concept", "name": "SQLAlchemy ORM", "content": "orm usage", "commit_sha": "abc"}]
        )
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert result[0]["name"] == "sqlalchemy orm"

    def test_entity_name_is_stripped(self):
        commit = _make_commit()
        raw = _make_valid_response(
            [{"type": "file", "name": "  main.py  ", "content": "main file", "commit_sha": "abc"}]
        )
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert result[0]["name"] == "main.py"

    def test_entity_name_lowercased_and_stripped_combined(self):
        commit = _make_commit()
        raw = _make_valid_response(
            [{"type": "tech_debt", "name": "  Legacy Code  ", "content": "old code", "commit_sha": "abc"}]
        )
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert result[0]["name"] == "legacy code"


# ---------------------------------------------------------------------------
# Type filtering tests
# ---------------------------------------------------------------------------


class TestTypeFiltering:
    """Entities with invalid type strings must be silently dropped."""

    def test_invalid_type_is_dropped(self):
        commit = _make_commit()
        raw = _make_valid_response(
            [
                {"type": "invalid_type", "name": "bad entity", "content": "should be dropped", "commit_sha": "abc"},
                {"type": "decision", "name": "good entity", "content": "kept", "commit_sha": "abc"},
            ]
        )
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert len(result) == 1
        assert result[0]["name"] == "good entity"

    def test_all_invalid_types_returns_empty(self):
        commit = _make_commit()
        raw = _make_valid_response(
            [
                {"type": "foo", "name": "a", "content": "x", "commit_sha": "abc"},
                {"type": "bar", "name": "b", "content": "y", "commit_sha": "abc"},
            ]
        )
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert result == []

    def test_all_valid_types_are_accepted(self):
        """All six VALID_ENTITY_TYPES must pass through the filter."""
        commit = _make_commit()
        entities = [
            {"type": t, "name": f"entity_{t}", "content": "desc", "commit_sha": "abc"}
            for t in sorted(VALID_ENTITY_TYPES)
        ]
        raw = _make_valid_response(entities)
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert len(result) == len(VALID_ENTITY_TYPES)


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Error cases must return [] without raising."""

    def test_malformed_json_returns_empty_list(self):
        commit = _make_commit()
        mock_result = MagicMock()
        mock_result.stdout = "this is not json {"

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert result == []

    def test_malformed_json_does_not_raise(self):
        commit = _make_commit()
        mock_result = MagicMock()
        mock_result.stdout = "{ broken json"

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            # Must not raise any exception
            result = extract_batch([commit])
        assert isinstance(result, list)

    def test_subprocess_called_process_error_returns_empty_list(self):
        commit = _make_commit()

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "claude"),
        ):
            result = extract_batch([commit])

        assert result == []

    def test_subprocess_timeout_expired_returns_empty_list(self):
        commit = _make_commit()

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired("claude", 60),
        ):
            result = extract_batch([commit])

        assert result == []

    def test_empty_batch_raises_value_error(self):
        with pytest.raises(ValueError, match="batch must not be empty"):
            extract_batch([])

    def test_claude_not_found_raises_runtime_error(self):
        commit = _make_commit()

        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="LLM provider 'claude' not available"):
                extract_batch([commit])

    def test_empty_entities_list_in_response(self):
        commit = _make_commit()
        raw = json.dumps({"entities": []})
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert result == []

    def test_missing_entities_key_returns_empty_list(self):
        """If LLM returns JSON but without 'entities' key, return []."""
        commit = _make_commit()
        raw = json.dumps({"result": "unexpected structure"})
        mock_result = MagicMock()
        mock_result.stdout = raw

        with patch("shutil.which", return_value="/usr/bin/claude"), patch(
            "subprocess.run", return_value=mock_result
        ):
            result = extract_batch([commit])

        assert result == []

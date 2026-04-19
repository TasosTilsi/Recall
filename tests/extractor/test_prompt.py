"""Tests for src.extractor.prompt module."""
from datetime import datetime

import pytest

from src.extractor.git_walker import CommitRecord
from src.extractor.prompt import (
    EXTRACTION_SCHEMA,
    VALID_ENTITY_TYPES,
    EntityRecord,
    ExtractionResult,
    build_batch_prompt,
)


def _make_commit(sha: str = "a" * 40, message: str = "fix: something", diff: str = "some diff") -> CommitRecord:
    return CommitRecord(
        sha=sha,
        short_sha=sha[:7],
        author="Jane Dev",
        date=datetime(2026, 1, 1),
        message=message,
        diff=diff,
    )


class TestExtractionSchema:
    def test_is_dict(self):
        assert isinstance(EXTRACTION_SCHEMA, dict)

    def test_has_entities_key(self):
        assert "entities" in EXTRACTION_SCHEMA

    def test_entities_is_list_schema(self):
        # The schema must describe a list of entity objects
        entities_schema = EXTRACTION_SCHEMA["entities"]
        assert entities_schema is not None

    def test_schema_has_type_field_description(self):
        # Schema should reference 'type' somewhere (as string representation)
        import json
        schema_str = json.dumps(EXTRACTION_SCHEMA)
        assert "type" in schema_str

    def test_schema_has_name_field(self):
        import json
        schema_str = json.dumps(EXTRACTION_SCHEMA)
        assert "name" in schema_str

    def test_schema_has_content_field(self):
        import json
        schema_str = json.dumps(EXTRACTION_SCHEMA)
        assert "content" in schema_str

    def test_schema_has_commit_sha_field(self):
        import json
        schema_str = json.dumps(EXTRACTION_SCHEMA)
        assert "commit_sha" in schema_str


class TestValidEntityTypes:
    def test_is_set(self):
        assert isinstance(VALID_ENTITY_TYPES, (set, frozenset))

    def test_contains_all_six_types(self):
        expected = {"decision", "bug_fix", "pattern", "file", "concept", "tech_debt"}
        assert VALID_ENTITY_TYPES == expected


class TestEntityRecord:
    def test_is_typed_dict(self):
        # Should be constructable as a dict with required keys
        record: EntityRecord = {
            "type": "decision",
            "name": "use sqlite",
            "content": "We chose SQLite for simplicity.",
            "commit_sha": "abc1234",
        }
        assert record["type"] == "decision"
        assert record["name"] == "use sqlite"

    def test_has_correct_keys(self):
        import typing
        hints = typing.get_type_hints(EntityRecord)
        assert set(hints.keys()) == {"type", "name", "content", "commit_sha"}


class TestExtractionResult:
    def test_is_typed_dict(self):
        result: ExtractionResult = {"entities": []}
        assert result["entities"] == []

    def test_has_entities_key(self):
        import typing
        hints = typing.get_type_hints(ExtractionResult)
        assert "entities" in hints


class TestBuildBatchPrompt:
    def test_empty_batch_raises_value_error(self):
        with pytest.raises(ValueError, match="empty"):
            build_batch_prompt([])

    def test_returns_string(self):
        commit = _make_commit()
        result = build_batch_prompt([commit])
        assert isinstance(result, str)

    def test_contains_json_word(self):
        commit = _make_commit()
        result = build_batch_prompt([commit])
        assert "JSON" in result

    def test_contains_all_six_entity_types(self):
        commit = _make_commit()
        result = build_batch_prompt([commit])
        for entity_type in ["decision", "bug_fix", "pattern", "file", "concept", "tech_debt"]:
            assert entity_type in result, f"Missing entity type: {entity_type!r}"

    def test_contains_commit_short_sha(self):
        commit = _make_commit(sha="b" * 40)
        result = build_batch_prompt([commit])
        assert commit.short_sha in result

    def test_contains_commit_author(self):
        commit = _make_commit()
        result = build_batch_prompt([commit])
        assert commit.author in result

    def test_contains_commit_message(self):
        commit = _make_commit(message="fix: memory leak in walker")
        result = build_batch_prompt([commit])
        assert "fix: memory leak in walker" in result

    def test_diff_truncated_to_800_chars(self):
        long_diff = "x" * 2000
        commit = _make_commit(diff=long_diff)
        result = build_batch_prompt([commit])
        # The diff should be truncated; 800 x's should not appear as 2000 x's
        assert "x" * 801 not in result

    def test_multiple_commits_included(self):
        commits = [
            _make_commit(sha="a" * 40, message="fix: bug A"),
            _make_commit(sha="b" * 40, message="feat: feature B"),
        ]
        result = build_batch_prompt(commits)
        assert "aaaaaaa" in result
        assert "bbbbbbb" in result
        assert "fix: bug A" in result
        assert "feat: feature B" in result

    def test_prompt_instructs_no_prose_or_markdown(self):
        commit = _make_commit()
        result = build_batch_prompt([commit])
        # Should contain instruction not to use markdown/prose
        lower = result.lower()
        assert any(word in lower for word in ["markdown", "prose", "code fence", "raw json"])

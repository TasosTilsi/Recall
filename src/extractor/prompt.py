"""Prompt builder and extraction schema for Phase 28 git extractor.

Provides:
- VALID_ENTITY_TYPES: frozenset of allowed entity type strings
- EXTRACTION_SCHEMA: JSON Schema dict describing the expected LLM response
- EntityRecord: TypedDict for a single extracted entity
- ExtractionResult: TypedDict for the full LLM response
- build_batch_prompt(batch): build the system prompt for a batch of commits
"""
from __future__ import annotations

import json
from typing import TypedDict

from src.extractor.git_walker import CommitRecord

# ---------------------------------------------------------------------------
# Entity type constants
# ---------------------------------------------------------------------------

VALID_ENTITY_TYPES: frozenset[str] = frozenset(
    {"decision", "bug_fix", "pattern", "file", "concept", "tech_debt"}
)

# ---------------------------------------------------------------------------
# Typed response structures
# ---------------------------------------------------------------------------


class EntityRecord(TypedDict):
    """A single entity extracted from one or more commits."""

    type: str        # one of VALID_ENTITY_TYPES
    name: str        # lowercase, trimmed
    content: str     # human-readable description
    commit_sha: str  # short sha of the originating commit


class ExtractionResult(TypedDict):
    """Full LLM response payload."""

    entities: list[EntityRecord]


# ---------------------------------------------------------------------------
# JSON Schema describing ExtractionResult for prompt embedding
# ---------------------------------------------------------------------------

EXTRACTION_SCHEMA: dict = {
    "entities": [
        {
            "type": "<one of: decision | bug_fix | pattern | file | concept | tech_debt>",
            "name": "<lowercase, trimmed entity name>",
            "content": "<concise description of the entity>",
            "commit_sha": "<7-char short sha of the commit this entity comes from>",
        }
    ]
}

_SCHEMA_JSON = json.dumps(EXTRACTION_SCHEMA, indent=2)

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_DIFF_PER_COMMIT = 800  # chars to include per commit diff in the prompt

_SYSTEM_HEADER = """\
You are a code knowledge extractor. Analyze the following git commits and return \
ONLY valid JSON with this exact structure:

{schema}

Rules:
- Entity types must be EXACTLY one of: decision, bug_fix, pattern, file, concept, tech_debt
- Entity names must be lowercase and trimmed (no leading/trailing whitespace)
- Do not include any prose, markdown, or code fences — return raw JSON only
- Each entity must be tied to the commit_sha it originates from

Commits to analyze:
""".format(schema=_SCHEMA_JSON)


def build_batch_prompt(batch: list[CommitRecord]) -> str:
    """Build the extraction prompt for a batch of commits.

    Args:
        batch: Non-empty list of :class:`CommitRecord` objects.

    Returns:
        A complete prompt string ready to send to the LLM.

    Raises:
        ValueError: If *batch* is empty.
    """
    if not batch:
        raise ValueError("batch must not be empty")

    commit_blocks: list[str] = []
    for record in batch:
        block = (
            f"--- Commit {record.short_sha} by {record.author} ---\n"
            f"Message: {record.message}\n"
            f"Diff (truncated):\n"
            f"{record.diff[:_DIFF_PER_COMMIT]}"
        )
        commit_blocks.append(block)

    return _SYSTEM_HEADER + "\n\n".join(commit_blocks)

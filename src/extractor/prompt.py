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
    {"decision", "bug_fix", "pattern", "file", "concept", "tech_debt", "workflow", "business_rule"}
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
            "type": "<one of: decision | bug_fix | pattern | file | concept | tech_debt | workflow | business_rule>",
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
You are a Principal Software Engineer and Knowledge Architect. Your task is to extract high-fidelity technical and domain knowledge from the provided git commits.

Analyze the commits and return ONLY a valid JSON object with the following structure:

{schema}

Strict Extraction Rules:
1. **Entity Fidelity**: Ensure names are concise but descriptive. Use kebab-case for multi-word names (e.g., 'auth-middleware-refactor').
2. **Normalization**: All names MUST be lowercase and trimmed of whitespace.
3. **Typing**: Use EXACTLY one of the allowed types.
   - `workflow`: High-level business processes or complex multi-step sequences.
   - `business_rule`: Logic mandated by domain requirements (e.g., 'refund-policy-30-days').
   - `decision`: Architectural choices, 'why' instead of 'what', trade-offs.
   - `bug_fix`: Root causes and resolutions of defects.
   - `pattern`: Reusable solutions or coding conventions introduced.
   - `tech_debt`: Known shortcuts, deferred work, or 'why this is hard to change'.
4. **Contextual Richness**: In the `content` field, explain the 'why' and the 'how', not just the 'what'.
5. **No Prose**: Do not include markdown code fences, headers, or any text outside the JSON object.

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
            f"External Context (PR/Issue): {record.external_context}\n"
            f"Diff (truncated):\n"
            f"{record.diff[:_DIFF_PER_COMMIT]}"
        )
        commit_blocks.append(block)

    return _SYSTEM_HEADER + "\n\n".join(commit_blocks)

"""LLM-powered batch summarization for capture pipeline.

Provides:
- Batch summarization prompt template for LLM
- summarize_batch: Security-filtered LLM summarization with graceful fallback
- summarize_and_store: High-level function that summarizes and stores to graph

Security: Always runs Phase 2 security filters BEFORE sending content to LLM.
"""

from pathlib import Path
from typing import Optional

import structlog

from src.security import sanitize_content
from src.llm import chat, LLMUnavailableError
from src.graph import get_service
from src.models import GraphScope

logger = structlog.get_logger()

VALID_CAPTURE_MODES = {"decisions-only", "decisions-and-patterns"}

# Narrow prompt: only Decisions & Rationale + Architecture & Patterns
BATCH_SUMMARIZATION_PROMPT_NARROW = """You are summarizing a development session from {source}.

INPUT: {count} {items} with full context below.

EXTRACT ONLY:
1. **Decisions & Rationale**: Why something was chosen over alternatives
2. **Architecture & Patterns**: System structure, component relationships, design patterns

EXCLUDE:
- Raw code snippets (store WHAT/WHY, not HOW)
- Routine operations ("ran tests", "formatted code")
- WIP/scratch content (fixup commits, debugging traces)

SPECIAL NOTE - Merge commit deduplication:
- If merge commit content overlaps with individual commits in this batch, skip redundant information
- Focus on unique knowledge not already covered by constituent commits

OUTPUT: Single cohesive session summary as a knowledge graph entity.
Focus on knowledge that helps understand the system's evolution and design decisions.

---
{content}
---

Summarize the session:"""

# Broad prompt: all 4 categories (decisions-and-patterns mode)
BATCH_SUMMARIZATION_PROMPT_BROAD = """You are summarizing a development session from {source}.

INPUT: {count} {items} with full context below.

EXTRACT ONLY:
1. **Decisions & Rationale**: Why something was chosen over alternatives
2. **Architecture & Patterns**: System structure, component relationships, design patterns
3. **Bug Fixes & Root Causes**: What went wrong, why, how it was fixed
4. **Dependencies & Config**: Libraries added/removed, config changes, environment setup

EXCLUDE:
- Raw code snippets (store WHAT/WHY, not HOW)
- Routine operations ("ran tests", "formatted code")
- WIP/scratch content (fixup commits, debugging traces)

SPECIAL NOTE - Merge commit deduplication:
- If merge commit content overlaps with individual commits in this batch, skip redundant information
- Focus on unique knowledge not already covered by constituent commits

OUTPUT: Single cohesive session summary as a knowledge graph entity.
Focus on knowledge that helps understand the system's evolution and design decisions.

---
{content}
---

Summarize the session:"""

# Kept for backward compatibility — alias for BATCH_SUMMARIZATION_PROMPT_BROAD
BATCH_SUMMARIZATION_PROMPT = BATCH_SUMMARIZATION_PROMPT_BROAD


async def summarize_batch(
    content_items: list[str],
    source: str = "git commits",
    item_label: str = "commits",
    capture_mode: str = "decisions-only",
) -> str:
    """Summarize a batch of content items via LLM.

    Security: Runs sanitize_content() on joined content BEFORE sending to LLM.
    This ensures secrets never reach the LLM (defense in depth, Phase 2 gate).

    Fallback: If LLMUnavailableError, returns basic concatenation of content items
    with separator (graceful degradation matching Phase 4 pattern).

    Args:
        content_items: List of content strings (e.g., git diffs, conversation turns)
        source: Source description for prompt (e.g., "git commits", "conversation")
        item_label: Label for items in prompt (e.g., "commits", "turns")

    Returns:
        LLM-generated summary string, or basic concatenation on LLM failure

    Example:
        >>> diffs = [fetch_commit_diff(sha) for sha in batch]
        >>> summary = await summarize_batch(diffs, source="git commits")
        >>> # Store summary in graph
    """
    # Join content with separators
    separator = "\n" + "=" * 80 + "\n"
    joined_content = separator.join(content_items)

    # SECURITY GATE: Filter content BEFORE LLM (locked Phase 2 decision)
    logger.debug(
        "security_filtering_before_llm",
        source=source,
        item_count=len(content_items),
    )
    sanitization_result = sanitize_content(joined_content)
    safe_content = sanitization_result.sanitized_content

    # Log if secrets were found and redacted
    if sanitization_result.was_modified:
        logger.warning(
            "secrets_redacted_before_llm",
            finding_count=len(sanitization_result.findings),
            source=source,
        )

    # Select prompt based on capture mode
    if capture_mode == "decisions-and-patterns":
        prompt_template = BATCH_SUMMARIZATION_PROMPT_BROAD
    else:
        prompt_template = BATCH_SUMMARIZATION_PROMPT_NARROW

    # Format prompt with safe content
    prompt = prompt_template.format(
        source=source,
        count=len(content_items),
        items=item_label,
        content=safe_content,
    )

    # Call LLM with graceful fallback
    try:
        logger.info(
            "calling_llm_for_batch_summary",
            source=source,
            item_count=len(content_items),
        )

        response = chat(
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract response text
        summary = response.get("message", {}).get("content", "")

        if not summary:
            logger.warning("llm_returned_empty_summary", source=source)
            # Fall back to basic concatenation
            return f"Session from {source} ({len(content_items)} {item_label}):\n\n{safe_content}"

        logger.info(
            "llm_summarization_complete",
            source=source,
            summary_length=len(summary),
        )
        return summary

    except LLMUnavailableError as e:
        # LLM unavailable - return basic concatenation (graceful fallback)
        logger.warning(
            "llm_unavailable_fallback_to_concatenation",
            source=source,
            error=str(e),
        )
        return f"Session from {source} ({len(content_items)} {item_label}):\n\n{safe_content}"


async def summarize_and_store(
    content_items: list[str],
    source: str,
    scope: GraphScope,
    project_root: Path | None = None,
    tags: list[str] | None = None,
    capture_mode: str = "decisions-only",
) -> dict | None:
    """High-level function: summarize batch and store in graph.

    Bridges capture pipeline to graph storage. Calls summarize_batch() then
    stores the result via GraphService.add().

    Args:
        content_items: List of content strings to summarize
        source: Source description (e.g., "git", "conversation")
        scope: GraphScope (GLOBAL or PROJECT)
        project_root: Project root path (required for PROJECT scope)
        tags: Optional tags for entity. Defaults to ["auto-capture", source]

    Returns:
        Stored entity dict from graph, or None on failure

    Example:
        >>> commits = read_and_clear_pending_commits()
        >>> diffs = [fetch_commit_diff(sha) for sha in commits]
        >>> entity = await summarize_and_store(
        ...     diffs,
        ...     source="git",
        ...     scope=GraphScope.PROJECT,
        ...     project_root=Path.cwd(),
        ... )
    """
    # Default tags
    if tags is None:
        tags = ["auto-capture", source]

    # Summarize batch
    logger.info(
        "summarize_and_store_start",
        source=source,
        item_count=len(content_items),
        scope=scope.value,
    )

    summary = await summarize_batch(
        content_items,
        source=source,
        item_label="items",
        capture_mode=capture_mode,
    )

    # Store in graph
    try:
        service = get_service()

        result = await service.add(
            content=summary,
            scope=scope,
            project_root=project_root,
            tags=tags,
        )

        logger.info(
            "summarize_and_store_complete",
            source=source,
            entity_name=result.get("name") if result else None,
        )

        return result

    except Exception as e:
        logger.error(
            "summarize_and_store_failed",
            source=source,
            error=str(e),
        )
        return None

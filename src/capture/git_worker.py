"""Git capture worker processing pipeline.

This module provides the end-to-end processing function that the background
worker calls to process pending git commits.

Processing flow:
1. Read pending commits atomically (read_and_clear_pending_commits)
2. Fetch full diffs with per-file truncation (fetch_commit_diff)
3. Pre-filter for relevance (filter_relevant_commit on commit messages)
4. Batch into groups of 10 (BatchAccumulator)
5. Summarize batches via LLM with security filtering (summarize_and_store)
6. Store results in knowledge graph

Key features:
- Default batch size: 10 (per locked user decision)
- Default max lines per file: 500 (Claude's discretion)
- Pre-filtering for relevance before batching (skip irrelevant commits early)
- Integration with Phase 5 queue infrastructure
- Graceful handling of empty pending file

Usage:
    # Process pending commits directly
    entities = await process_pending_commits(
        pending_file=Path("~/.graphiti/pending_commits"),
        batch_size=10,
    )

    # Enqueue for background processing
    job_id = enqueue_git_processing(
        pending_file=Path("~/.graphiti/pending_commits")
    )
"""

import re
from pathlib import Path
from typing import Optional

import structlog

from src.capture.git_capture import (
    read_and_clear_pending_commits,
    fetch_commit_diff,
)
from src.capture.batching import BatchAccumulator
from src.capture.relevance import filter_relevant_commit
from src.capture.summarizer import summarize_and_store
from src.llm.config import load_config
from src.queue import enqueue
from src.models import GraphScope

logger = structlog.get_logger()

# Default settings per user decisions and research
DEFAULT_BATCH_SIZE = 10
DEFAULT_MAX_LINES_PER_FILE = 500


def _extract_commit_message(diff_output: str) -> str:
    """Extract commit message from git show output.

    Parses git show output to find the commit subject line. The format is:
    - commit <hash>
    - Author: <author>
    - Date: <date>
    - <blank line>
    - <indented message>

    Returns the first line of the message (subject).

    Args:
        diff_output: Output from git show command

    Returns:
        Commit message subject line, or empty string if not found

    Example:
        >>> output = '''commit abc123
        ... Author: Test User
        ... Date: 2026-02-13
        ...
        ...     feat: add new feature
        ...
        ...     Details here.
        ... '''
        >>> _extract_commit_message(output)
        'feat: add new feature'
    """
    if not diff_output:
        return ""

    # Split into lines
    lines = diff_output.split('\n')

    # Find the first indented line after the Date: line
    # This is the commit message subject
    found_date = False
    for line in lines:
        if line.startswith('Date:'):
            found_date = True
            continue

        if found_date:
            # Skip blank lines
            if not line.strip():
                continue

            # First non-blank line after Date is the message
            # Remove leading whitespace (typically 4 spaces)
            return line.strip()

    # Fallback: try to find any indented line after metadata
    for i, line in enumerate(lines):
        if line.startswith('    ') and line.strip():
            return line.strip()

    return ""


async def process_pending_commits(
    pending_file: Path | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_lines_per_file: int = DEFAULT_MAX_LINES_PER_FILE,
    scope: GraphScope | None = None,
    project_root: Path | None = None,
) -> list[dict]:
    """Main git capture processing function.

    End-to-end pipeline that processes pending commits:
    1. Atomically read and clear pending commits file
    2. Fetch diffs with per-file truncation
    3. Pre-filter for relevance (skip irrelevant commits early)
    4. Batch relevant diffs into groups of batch_size
    5. Summarize and store each batch

    Args:
        pending_file: Path to pending commits file. None = default (~/.graphiti/pending_commits)
        batch_size: Number of commits per batch. Default: 10 (locked user decision)
        max_lines_per_file: Max lines per file in diff. Default: 500 (Claude's discretion)
        scope: GraphScope for storage. None = auto-detect from project_root
        project_root: Project root path. None = current directory

    Returns:
        List of stored entity dicts (one per batch)

    Example:
        >>> # Process with defaults
        >>> entities = await process_pending_commits()

        >>> # Custom settings
        >>> entities = await process_pending_commits(
        ...     batch_size=15,
        ...     max_lines_per_file=1000,
        ...     scope=GraphScope.PROJECT,
        ...     project_root=Path.cwd()
        ... )
    """
    cfg = load_config()

    # Set defaults
    if scope is None:
        scope = GraphScope.GLOBAL

    if project_root is None:
        project_root = Path.cwd()

    # Read pending commits atomically
    logger.info("process_pending_commits_start", pending_file=str(pending_file))
    commit_hashes = read_and_clear_pending_commits(pending_file)

    if not commit_hashes:
        logger.debug("no_pending_commits")
        return []

    logger.info("pending_commits_found", count=len(commit_hashes))

    # Fetch diffs for each commit
    relevant_diffs = []
    skipped_count = 0

    for sha in commit_hashes:
        try:
            # Fetch full diff with truncation
            diff = fetch_commit_diff(
                commit_sha=sha,
                max_lines_per_file=max_lines_per_file
            )

            # Extract commit message for relevance check
            commit_message = _extract_commit_message(diff)

            # Pre-filter for relevance
            if not filter_relevant_commit(commit_message):
                logger.debug(
                    "commit_skipped_not_relevant",
                    sha=sha[:8],
                    message=commit_message[:60]
                )
                skipped_count += 1
                continue

            # Keep relevant diff
            relevant_diffs.append(diff)
            logger.debug(
                "commit_relevant",
                sha=sha[:8],
                message=commit_message[:60]
            )

        except Exception as e:
            logger.error(
                "failed_to_fetch_commit_diff",
                sha=sha[:8],
                error=str(e)
            )
            # Skip this commit on error
            skipped_count += 1
            continue

    logger.info(
        "relevance_filtering_complete",
        total=len(commit_hashes),
        relevant=len(relevant_diffs),
        skipped=skipped_count
    )

    if not relevant_diffs:
        logger.debug("no_relevant_commits_to_process")
        return []

    # Batch and summarize
    accumulator = BatchAccumulator(batch_size=batch_size)
    stored_entities = []

    for diff in relevant_diffs:
        # Add to accumulator
        batch = accumulator.add(diff)

        # Process full batch
        if batch:
            logger.info("processing_full_batch", batch_size=len(batch))
            entity = await summarize_and_store(
                content_items=batch,
                source="git-commits",
                scope=scope,
                project_root=project_root,
                tags=["auto-capture", "git-commits"],
                capture_mode=cfg.capture_mode,
            )

            if entity:
                stored_entities.append(entity)

    # Flush any partial batch
    partial_batch = accumulator.flush()
    if partial_batch:
        logger.info("processing_partial_batch", batch_size=len(partial_batch))
        entity = await summarize_and_store(
            content_items=partial_batch,
            source="git-commits",
            scope=scope,
            project_root=project_root,
            tags=["auto-capture", "git-commits"],
            capture_mode=cfg.capture_mode,
        )

        if entity:
            stored_entities.append(entity)

    logger.info(
        "process_pending_commits_complete",
        commits_processed=len(relevant_diffs),
        batches_stored=len(stored_entities)
    )

    return stored_entities


def enqueue_git_processing(pending_file: Path | None = None) -> str | None:
    """Enqueue git processing as a background job via Phase 5 queue.

    Creates a job with type="capture_git_commits" and payload containing
    pending_file path. Job will be processed by background worker.

    Sequential job (parallel=False): Only one git processor should run at
    a time to avoid race conditions on pending file.

    Args:
        pending_file: Path to pending commits file. None = default

    Returns:
        Job ID (UUID string) if commits exist, None if no pending commits

    Example:
        >>> job_id = enqueue_git_processing()
        >>> if job_id:
        ...     print(f"Git processing queued: {job_id}")
    """
    # Check if there are pending commits
    from src.capture.git_capture import DEFAULT_PENDING_FILE

    if pending_file is None:
        pending_file = DEFAULT_PENDING_FILE

    if not pending_file.exists():
        logger.debug("no_pending_commits_to_enqueue", path=str(pending_file))
        return None

    # Check if file has content
    try:
        content = pending_file.read_text().strip()
        if not content:
            logger.debug("pending_file_empty", path=str(pending_file))
            return None
    except Exception as e:
        logger.error("failed_to_read_pending_file", path=str(pending_file), error=str(e))
        return None

    # Enqueue job
    logger.info("enqueuing_git_processing", pending_file=str(pending_file))

    job_id = enqueue(
        job_type="capture_git_commits",
        payload={
            "pending_file": str(pending_file),
        },
        parallel=False,  # Sequential - one git processor at a time
    )

    logger.info("git_processing_enqueued", job_id=job_id)
    return job_id

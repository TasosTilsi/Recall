"""Two-pass LLM extraction pipeline for git commit knowledge.

Each qualifying commit is processed in two passes:
  1. Structured Q&A pass: answers specific questions about the commit
  2. Free-form entity pass: extracts entities and relationships as facts

Both passes call instance.add_episode() and tag the episodes with
source_description starting with 'git-history-index:'.

Large diffs (>300 lines) are summarized first before extraction to keep
prompt sizes manageable.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import structlog
from graphiti_core.nodes import EpisodeType

logger = structlog.get_logger()

LARGE_DIFF_THRESHOLD_LINES = 300
DIFF_CONTENT_CHAR_LIMIT = 4000  # chars for prompt

STRUCTURED_EXTRACTION_PROMPT = """\
Analyze this git commit and answer concisely:

Commit: {sha_short} by {author}
Message: {message}

Diff:
{diff_content}

Answer these questions:
1. What decision was made?
2. What components or files were changed?
3. Why was this change made (purpose/motivation)?
4. What was the impact or risk?
"""

FREE_FORM_EXTRACTION_PROMPT_NARROW = """\
Extract entities and relationships from this git commit as natural language knowledge graph facts.
Focus on: people, components, architectural decisions.

Commit: {sha_short} by {author}
Message: {message}

Diff content:
{diff_content}
"""

FREE_FORM_EXTRACTION_PROMPT_BROAD = """\
Extract all entities and relationships from this git commit as natural language knowledge graph facts.
Focus on: people, components, architectural decisions, bugs fixed, features added, dependencies introduced.

Commit: {sha_short} by {author}
Message: {message}

Diff content:
{diff_content}
"""

# Backward-compatible alias — points to broad prompt (original behavior)
FREE_FORM_EXTRACTION_PROMPT = FREE_FORM_EXTRACTION_PROMPT_BROAD

DIFF_SUMMARIZATION_PROMPT = """\
Summarize this large git diff concisely for knowledge extraction.
Describe what changed, which components are affected, and the apparent purpose.
Keep the summary under 300 words.

Diff:
{diff_content}
"""


async def _summarize_diff(diff_content: str, instance: Any) -> str:
    """Summarize a large diff using the project LLM client.

    Falls back to simple truncation if the LLM call fails.

    Args:
        diff_content: Raw diff text
        instance: Recall instance (used to access LLM indirectly)

    Returns:
        Summarized diff string (≤ DIFF_CONTENT_CHAR_LIMIT chars on failure)
    """
    try:
        from src.llm import chat as ollama_chat

        prompt = DIFF_SUMMARIZATION_PROMPT.format(
            diff_content=diff_content[:8000]
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: ollama_chat(messages=[{"role": "user", "content": prompt}])
        )
        summary = response["message"]["content"]
        logger.debug("diff_summarized", original_lines=diff_content.count('\n'))
        return summary
    except Exception as e:
        logger.warning("diff_summarization_failed", error=str(e))
        return diff_content[:DIFF_CONTENT_CHAR_LIMIT]


async def extract_commit_knowledge(
    commit_sha: str,
    commit_message: str,
    commit_author: str,
    diff_content: str,
    instance: Any,
    group_id: str,
    reference_time: datetime,
    capture_mode: str = "decisions-only",
) -> dict:
    """Run the two-pass extraction pipeline for a single git commit.

    Pass 1 — structured Q&A: answers specific questions about the commit.
    Pass 2 — free-form entity extraction: produces knowledge graph facts.

    Both passes call add_episode() with source_description starting with
    'git-history-index:'.

    Large diffs (>LARGE_DIFF_THRESHOLD_LINES lines) are summarized first.

    Args:
        commit_sha: Full commit SHA
        commit_message: Commit subject/body text
        commit_author: Author name or email
        diff_content: Raw diff text for this commit
        instance: Initialized Recall instance
        group_id: Recall group_id for episode tagging
        reference_time: UTC datetime representing when the commit was made

    Returns:
        Dict with keys: sha, passes, was_large, (optionally) error
    """
    sha_short = commit_sha[:7]
    try:
        # Check if diff is large
        is_large = diff_content.count('\n') > LARGE_DIFF_THRESHOLD_LINES

        if is_large:
            logger.info(
                "large_diff_detected",
                sha=sha_short,
                lines=diff_content.count('\n'),
                threshold=LARGE_DIFF_THRESHOLD_LINES,
            )
            diff_content = await _summarize_diff(diff_content, instance)

        # Truncate to char limit for prompts
        diff_for_prompt = diff_content[:DIFF_CONTENT_CHAR_LIMIT]

        # Pass 1 — structured Q&A extraction
        structured_text = STRUCTURED_EXTRACTION_PROMPT.format(
            sha_short=sha_short,
            author=commit_author,
            message=commit_message,
            diff_content=diff_for_prompt,
        )

        await instance.add_episode(
            name=f"git-commit-structured-{sha_short}",
            episode_body=structured_text,
            source_description=f"git-history-index:structured:{sha_short}",
            reference_time=reference_time,
            source=EpisodeType.text,
            group_id=group_id,
        )

        logger.debug("structured_pass_complete", sha=sha_short)

        # Select free-form prompt based on capture mode
        if capture_mode == "decisions-and-patterns":
            freeform_prompt_template = FREE_FORM_EXTRACTION_PROMPT_BROAD
        else:
            freeform_prompt_template = FREE_FORM_EXTRACTION_PROMPT_NARROW

        # Pass 2 — free-form entity extraction
        freeform_text = freeform_prompt_template.format(
            sha_short=sha_short,
            author=commit_author,
            message=commit_message,
            diff_content=diff_for_prompt,
        )

        await instance.add_episode(
            name=f"git-commit-freeform-{sha_short}",
            episode_body=freeform_text,
            source_description=f"git-history-index:freeform:{sha_short}",
            reference_time=reference_time,
            source=EpisodeType.text,
            group_id=group_id,
        )

        logger.debug("freeform_pass_complete", sha=sha_short)

        return {"sha": sha_short, "passes": 2, "was_large": is_large}

    except Exception as e:
        logger.error("extract_commit_knowledge_failed", sha=sha_short, error=str(e))
        return {"sha": sha_short, "passes": 0, "error": str(e)}


# ---------------------------------------------------------------------------
# Batch extraction via claude -p subprocess
# ---------------------------------------------------------------------------

BATCH_SIZE = 10

BATCH_EXTRACTION_PROMPT = """\
Extract entities and relationships from these git commits as a JSON array.
For each commit return: {{"sha": "abc1234", "entities": ["Entity A", "Code Block: process_queue | File: src/queue/worker.py | Language: Python | Type: function"], "relationships": ["Commit abc1234 MODIFIES Entity A"], "summary": "2-sentence description"}}

For each function or class definition that appears as an added (+) line in the diff, add a structured entry to the entities array using this exact pipe-delimited format:
"Code Block: <name> | File: <filepath> | Language: <lang> | Type: function/class"

Use these preferred relationship verbs when applicable: MODIFIES, INTRODUCES, FIXES, DEPENDS_ON, REMOVES, REFACTORS, TESTS.
Write relationship strings using these verbs explicitly, e.g. "Commit abc1234 INTRODUCES class BatchWorker" or "Commit abc1234 FIXES race condition bug".

Commits:
{commits_block}

Return a JSON array with exactly {count} objects (one per commit), in order."""


async def extract_commits_batch(
    batch: list[tuple],  # list of (commit_sha, commit_message, commit_author, diff_content, reference_time)
    instance: Any,
    group_id: str,
    capture_mode: str = "decisions-only",
) -> list[dict]:
    """Extract knowledge from a batch of commits using a single `claude -p` call.

    Sends all commits in `batch` to `claude -p` as a single JSON extraction
    prompt. Parses the returned JSON array (one object per commit), then calls
    `instance.add_episode()` for each commit result individually.

    Args:
        batch: List of tuples (commit_sha, commit_message, commit_author,
               diff_content, reference_time).  Up to BATCH_SIZE entries.
        instance: Initialized graphiti Recall instance.
        group_id: Recall group_id for episode tagging.
        capture_mode: Capture mode string (currently unused in batch path).

    Returns:
        List of per-commit result dicts, each with keys:
          - sha: short (7-char) commit SHA
          - passes: 1 on success, 0 on failure
          - was_large: False (batch path does not summarize diffs)
          - error: present only on failure
    """
    import json as _json
    import re as _re
    from src.llm.claude_cli_client import _claude_p
    from src.llm.config import load_config as _load_cfg
    _icfg = _load_cfg()
    _icli, _imodel = _icfg.indexer_cli, _icfg.indexer_model

    # Build the commits_block string
    lines = []
    for i, (sha, message, author, diff_content, ref_time) in enumerate(batch):
        entry = (
            f"[{i}] sha: {sha[:7]}, author: {author},"
            f" date: {ref_time.strftime('%Y-%m-%d')}\n"
            f"    message: {message[:200]}\n"
            f"    diff: {diff_content[:500]}"
        )
        lines.append(entry)
    commits_block = "\n\n".join(lines)

    # Truncate to stay within claude -p context limits
    if len(commits_block) > 15000:
        commits_block = commits_block[:15000]

    prompt = BATCH_EXTRACTION_PROMPT.format(
        commits_block=commits_block,
        count=len(batch),
    )

    # Call claude -p for the full batch
    try:
        result_text = await _claude_p(prompt, cli=_icli, model=_imodel)
    except Exception as e:
        logger.warning("batch_claude_p_failed", error=str(e))
        return [{"sha": sha[:7], "passes": 0, "error": "batch_claude_failed"} for sha, *_ in batch]

    # Strip markdown code fences if present
    clean = result_text.strip()
    clean = _re.sub(r'^```(?:json)?\s*\n?', '', clean)
    clean = _re.sub(r'\n?```\s*$', '', clean)

    try:
        results = _json.loads(clean)
    except (_json.JSONDecodeError, ValueError) as e:
        logger.warning("batch_json_parse_failed", error=str(e), preview=clean[:200])
        return [{"sha": sha[:7], "passes": 0, "error": "batch_parse_failed"} for sha, *_ in batch]

    # Add episodes individually and build per-commit result list
    per_commit_results: list[dict] = []
    for i, (sha, msg, author, diff, ref_time) in enumerate(batch):
        try:
            extracted = results[i] if i < len(results) else {}
            episode_body = (
                f"Commit {sha[:7]} by {author}: {msg}\n\n"
                f"Entities: {', '.join(extracted.get('entities', []))}\n"
                f"Relationships: {', '.join(extracted.get('relationships', []))}\n"
                f"Summary: {extracted.get('summary', '')}"
            )
            await instance.add_episode(
                name=f"git-commit-batch-{sha[:7]}",
                episode_body=episode_body,
                source_description=f"git-history-index:batch:{sha[:7]}",
                reference_time=ref_time,
                source=EpisodeType.text,
                group_id=group_id,
            )
            per_commit_results.append({
                "sha": sha[:7],
                "passes": 1,
                "was_large": False,
                "entities": extracted.get("entities", []),
                "summary": extracted.get("summary", ""),
            })
        except Exception as e:
            logger.error("batch_episode_failed", sha=sha[:7], error=str(e))
            per_commit_results.append({"sha": sha[:7], "passes": 0, "error": str(e), "entities": []})

    return per_commit_results

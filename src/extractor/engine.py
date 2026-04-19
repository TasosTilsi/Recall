"""LLM extraction engine for Phase 28 git extractor.

Provides:
- extract_batch(batch): call LLM via claude subprocess, parse JSON, normalize entities
"""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import List

import structlog

from src.extractor.git_walker import CommitRecord
from src.extractor.prompt import VALID_ENTITY_TYPES, EntityRecord, build_batch_prompt

logger = structlog.get_logger(__name__)

LLM_TIMEOUT_SECONDS = 60


def extract_batch(batch: list[CommitRecord]) -> list[EntityRecord]:
    """Call the LLM with a batch of commits and return normalized entity records.

    Args:
        batch: Non-empty list of CommitRecord objects to extract entities from.

    Returns:
        List of EntityRecord dicts with normalized names and valid types.
        Returns an empty list on JSON parse errors or subprocess failures.

    Raises:
        ValueError: If batch is empty.
        RuntimeError: If the claude CLI binary is not found on PATH.
    """
    if not batch:
        raise ValueError("batch must not be empty")

    prompt = build_batch_prompt(batch)

    claude_bin = shutil.which("claude")
    if claude_bin is None:
        raise RuntimeError(
            "LLM provider 'claude' not available — install claude CLI"
        )

    try:
        result = subprocess.run(
            [claude_bin, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=LLM_TIMEOUT_SECONDS,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error(
            "engine.extract_batch subprocess failed",
            return_code=exc.returncode,
            batch_size=len(batch),
        )
        return []
    except subprocess.TimeoutExpired:
        logger.error(
            "engine.extract_batch subprocess timed out",
            timeout_seconds=LLM_TIMEOUT_SECONDS,
            batch_size=len(batch),
        )
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        logger.warning(
            "engine.extract_batch malformed JSON from LLM",
            batch_size=len(batch),
            response_preview=result.stdout[:200],
        )
        return []

    raw_entities = data.get("entities", [])

    normalized: list[EntityRecord] = []
    batch_sha = batch[0].sha

    for item in raw_entities:
        entity_type = item.get("type", "")
        if entity_type not in VALID_ENTITY_TYPES:
            continue

        item["name"] = item.get("name", "").lower().strip()
        item["commit_sha"] = batch_sha

        normalized.append(item)

    logger.info(
        "engine.extract_batch complete",
        entities_extracted=len(normalized),
        batch_commits=[c.short_sha for c in batch],
    )

    return normalized

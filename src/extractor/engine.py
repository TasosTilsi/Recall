"""LLM extraction engine for Phase 28 git extractor.

Provides:
- extract_batch(batch): call LLM via claude subprocess, parse JSON, normalize entities
"""
from __future__ import annotations

import asyncio
import json
from typing import List

import structlog

from src.config import load_config
from src.extractor.git_walker import CommitRecord
from src.extractor.prompt import VALID_ENTITY_TYPES, EntityRecord, build_batch_prompt
from src.llm.client import LLMClient, LLMError

logger = structlog.get_logger(__name__)


def extract_batch(batch: list[CommitRecord]) -> list[EntityRecord]:
    """Call the LLM with a batch of commits and return normalized entity records.

    Args:
        batch: Non-empty list of CommitRecord objects to extract entities from.

    Returns:
        List of EntityRecord dicts with normalized names and valid types.
        Returns an empty list on JSON parse errors or API failures.

    Raises:
        ValueError: If batch is empty.
    """
    if not batch:
        raise ValueError("batch must not be empty")

    # This is a synchronous wrapper around the async LLM client for now,
    # as the indexer currently expects synchronous execution.
    try:
        return asyncio.run(_async_extract_batch(batch))
    except Exception as e:
        logger.error("engine.extract_batch failed", error=str(e))
        return []


async def _async_extract_batch(batch: list[CommitRecord]) -> list[EntityRecord]:
    prompt = build_batch_prompt(batch)
    config = load_config()
    client = LLMClient(config)

    try:
        resp = await client.chat([
            {"role": "system", "content": "You are a code knowledge extractor. Return raw JSON ONLY."},
            {"role": "user", "content": prompt}
        ])
    except LLMError as exc:
        logger.error("engine.extract_batch API failed", error=str(exc))
        return []

    try:
        # LLMs sometimes wrap JSON in markdown blocks
        content = resp.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning(
            "engine.extract_batch malformed JSON from LLM",
            batch_size=len(batch),
            response_preview=resp.content[:200],
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

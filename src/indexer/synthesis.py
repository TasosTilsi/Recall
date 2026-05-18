"""synthesis.py — High-level project synthesis after indexing."""
from __future__ import annotations

import asyncio
import uuid
import structlog
from typing import Optional, Any

from src.config import Config, load_config
from src.db.manager import DatabaseManager
from src.llm.client import LLMClient, LLMError

logger = structlog.get_logger(__name__)

SYNTHESIS_PROMPT = """
You are a technical architect. Based on the following knowledge graph entities extracted from a git history,
provide a high-level "Project DNA" summary.

Focus on:
1. The Big Picture: What is this project trying to achieve?
2. Architectural Decisions: What are the key technical choices and trade-offs made?
3. Core Workflows: How does the system handle primary business processes?
4. Integration Boundaries: What external systems or services does it interact with?

Entities:
{entities_blob}

Summary (Markdown format):
"""

def run_synthesis(config: Optional[Config] = None) -> Optional[str]:
    """Gather top entities and generate hierarchical summaries (project + modules)."""
    config = config or load_config()
    db = DatabaseManager(config)

    if not db.get_db_path().exists():
        return None

    # 1. Project-level synthesis
    project_summary_id = _run_project_synthesis(db, config)

    # 2. Module-level synthesis (recursive-like discovery)
    _run_module_synthesis(db, config, project_summary_id)

    return project_summary_id

def _run_project_synthesis(db: DatabaseManager, config: Config) -> Optional[str]:
    entities = []
    with db.connect() as conn:
        rows = conn.execute("""
            SELECT type, name, content FROM entities
            ORDER BY CASE
                WHEN type = 'workflow' THEN 1
                WHEN type = 'business_rule' THEN 2
                WHEN type = 'decision' THEN 3
                ELSE 4
            END, created_at DESC
            LIMIT 50
        """).fetchall()
        entities = [dict(row) for row in rows]

    if not entities:
        return None

    entities_blob = "\n".join([f"- [{e['type']}] {e['name']}: {e['content']}" for e in entities])
    try:
        summary = asyncio.run(_async_synthesize(entities_blob, config))
        if summary:
            return _store_summary(db, summary, scope="project")
    except Exception as e:
        logger.error("synthesis.project_failed", error=str(e))
    return None

def _run_module_synthesis(db: DatabaseManager, config: Config, parent_id: Optional[str]):
    """Identify key modules/components and synthesize summaries for them."""
    with db.connect() as conn:
        # Find 'file' entities that look like directories or core modules
        # This is a heuristic: files with more than 5 connections
        rows = conn.execute("""
            SELECT e.id, e.name, COUNT(b.from_id) as conn_count
            FROM entities e
            JOIN backlinks b ON b.to_id = e.id
            WHERE e.type = 'file'
            GROUP BY e.id
            HAVING conn_count > 5
            LIMIT 5
        """).fetchall()
        modules = [dict(row) for row in rows]

    for mod in modules:
        logger.info("synthesizing_module", name=mod["name"])
        # Fetch entities related to this module
        with db.connect() as conn:
            rows = conn.execute("""
                SELECT e.type, e.name, e.content
                FROM entities e
                JOIN backlinks b ON b.from_id = e.id
                WHERE b.to_id = ?
                LIMIT 20
            """, (mod["id"],)).fetchall()
            mod_entities = [dict(row) for row in rows]

        if not mod_entities:
            continue

        entities_blob = f"Module: {mod['name']}\n" + "\n".join([f"- [{e['type']}] {e['name']}: {e['content']}" for e in mod_entities])
        try:
            summary = asyncio.run(_async_synthesize(entities_blob, config))
            if summary:
                _store_summary(db, summary, scope="module", parent_id=parent_id)
        except Exception as e:
            logger.error("synthesis.module_failed", name=mod["name"], error=str(e))

async def _async_synthesize(entities_blob: str, config: Config) -> Optional[str]:
    client = LLMClient(config)
    prompt = SYNTHESIS_PROMPT.format(entities_blob=entities_blob)

    try:
        resp = await client.chat([
            {"role": "system", "content": "You are a technical architect providing a high-level project summary."},
            {"role": "user", "content": prompt}
        ])
        return resp.content
    except LLMError as e:
        logger.error("synthesis LLM call failed", error=str(e))
        return None

def _store_summary(db: DatabaseManager, content: str, scope: str = "project", parent_id: Optional[str] = None) -> str:
    summary_id = str(uuid.uuid4())
    with db.connect() as conn:
        # Get the latest commit_sha for reference
        last_sha_row = conn.execute("SELECT value FROM metadata WHERE key = 'last_indexed_sha'").fetchone()
        last_sha = last_sha_row["value"] if last_sha_row else None

        conn.execute(
            "INSERT INTO summaries (id, content, commit_sha, scope, parent_id) VALUES (?, ?, ?, ?, ?)",
            (summary_id, content, last_sha, scope, parent_id)
        )
        conn.commit()
    logger.info("synthesis.summary_stored", id=summary_id, scope=scope)
    return summary_id

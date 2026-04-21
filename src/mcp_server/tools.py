"""MCP tool handlers — read-only access to the engineering knowledge graph.

IMPORTANT: All logging in this module MUST go to stderr only.
logging.basicConfig is set in server.py before this module is imported.
Do NOT use structlog. Do NOT use print().
"""
import logging
from typing import Optional

from src.config import load_config
from src.db.manager import DatabaseManager

logger = logging.getLogger(__name__)


def _db() -> DatabaseManager:
    """Return a DatabaseManager using the default config path."""
    return DatabaseManager(load_config())


def search_knowledge(query: str, limit: int = 20) -> dict:
    """Full-text search across entity names and content using FTS5.

    Args:
        query: Search terms (FTS5 MATCH syntax supported).
        limit: Maximum number of results to return (default 20).
    Returns:
        {"results": [{"id", "name", "type", "content", "tags", "source_commit", "created_at"}]}
    """
    try:
        results = _db().search_fts(query, limit=limit)
        return {"results": results}
    except Exception as exc:
        logger.error("search_knowledge failed: %s", exc)
        return {"error": str(exc), "results": []}


def get_entity(entity_id: str) -> dict:
    """Fetch a single entity by UUID or exact name.

    Lookup order: tries UUID first via get_entity_by_id(); if not found,
    falls back to exact name match via get_entity_by_name(). This allows
    callers to use either the UUID or the human-readable entity name.

    Args:
        entity_id: UUID string or exact entity name.
    Returns:
        The entity dict, or {"error": "not found"} if absent by both strategies.
    """
    try:
        db = _db()
        row = db.get_entity_by_id(entity_id)
        if row is None:
            row = db.get_entity_by_name(entity_id)
        if row is None:
            return {"error": "entity not found", "id": entity_id}
        return row
    except Exception as exc:
        logger.error("get_entity failed: %s", exc)
        return {"error": str(exc)}


def get_backlinks(entity_id: str, hops: int = 1) -> dict:
    """Return backlinks for an entity with optional multi-hop traversal.

    With hops=1 (default) returns direct backlinks only. With hops>1 expands
    the graph iteratively: each hop discovers new entity IDs from source_id/
    target_id fields and retrieves their backlinks too. A visited set prevents
    cycles. Deduplication is performed on the final result set.

    Args:
        entity_id: UUID of the entity whose backlinks to retrieve.
        hops: Traversal depth (default 1 = direct backlinks only; max recommended: 3).
    Returns:
        {"entity_id": str, "hops": int, "backlinks": [{"source_id", "target_id",
         "label", "inverse_label", "context", "commit_sha"}]}
    """
    try:
        db = _db()
        links = db.get_backlinks_recursive(entity_id, hops)
        return {"entity_id": entity_id, "hops": hops, "backlinks": links}
    except Exception as exc:
        logger.error("get_backlinks failed: %s", exc)
        return {"error": str(exc), "backlinks": []}


def get_decisions(limit: int = 20) -> dict:
    """Retrieve entities of type 'decision'.

    Args:
        limit: Maximum results (default 20).
    Returns:
        {"type": "decision", "results": [...entity dicts...]}
    """
    try:
        results = _db().get_entities_by_type("decision", limit=limit)
        return {"type": "decision", "results": results}
    except Exception as exc:
        logger.error("get_decisions failed: %s", exc)
        return {"error": str(exc), "results": []}


def get_bugs(limit: int = 20) -> dict:
    """Retrieve entities of type 'bug_fix'.

    Args:
        limit: Maximum results (default 20).
    Returns:
        {"type": "bug_fix", "results": [...entity dicts...]}
    """
    try:
        results = _db().get_entities_by_type("bug_fix", limit=limit)
        return {"type": "bug_fix", "results": results}
    except Exception as exc:
        logger.error("get_bugs failed: %s", exc)
        return {"error": str(exc), "results": []}


def get_patterns(limit: int = 20) -> dict:
    """Retrieve entities of type 'pattern'.

    Args:
        limit: Maximum results (default 20).
    Returns:
        {"type": "pattern", "results": [...entity dicts...]}
    """
    try:
        results = _db().get_entities_by_type("pattern", limit=limit)
        return {"type": "pattern", "results": results}
    except Exception as exc:
        logger.error("get_patterns failed: %s", exc)
        return {"error": str(exc), "results": []}

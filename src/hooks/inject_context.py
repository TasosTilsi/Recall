#!/usr/bin/env python3
"""UserPromptSubmit hook — injects Option C context before every prompt.

Searches the knowledge graph for temporally-current relevant history and
the most recent session summary, formats as Option C XML, outputs JSON to stdout.

Output format: {"context": "<session_context>...</session_context>"}
Empty context: {"context": ""}

Fail-open: any exception or timeout -> outputs {"context": ""} and exits 0.
Token budget: <=4000 tokens total (approx len(text)//4).

3-layer progressive disclosure:
  Layer 1: FTS keyword search (<50ms) — entities + episodes matching prompt keywords
  Layer 2: Recent episodes (chronological, no LLM) — last 20 episodes
  Layer 3: Full node details for top FTS entity hits only

TOON encoding applied to Layer 2 and Layer 3 arrays with 3+ items for ~40% token savings.
"""
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

# TOON imports for efficient history encoding
from src.mcp_server.toon_utils import trim_to_token_budget
from toon import encode

# Fix sys.path for subprocess spawn (CWD undefined when Claude Code calls hooks)
_HOOK_DIR = Path(__file__).resolve().parent
_PROJECT_PKG_ROOT = _HOOK_DIR.parent.parent  # src/ -> project root
if str(_PROJECT_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_PKG_ROOT))

import structlog

logger = structlog.get_logger()

TOKEN_BUDGET = 4000

# Hard timeout for the entire context fetch (seconds).
# UserPromptSubmit hook must complete before the model call; 5s is generous.
_CONTEXT_TIMEOUT_SECONDS = 5.0


def _approx_tokens(text: str) -> int:
    """Approximate token count. Conservative: 4 chars per token."""
    return len(text) // 4


def _read_session_id(project_root: Path) -> Optional[str]:
    """Read session UUID from .recall/.current_session_id."""
    session_file = project_root / ".recall" / ".current_session_id"
    if session_file.exists():
        return session_file.read_text().strip() or None
    return None


def _format_created_at(created_at_val) -> str:
    """Format created_at (ISO string or datetime) to human-readable date."""
    try:
        if isinstance(created_at_val, str):
            dt = datetime.fromisoformat(created_at_val.replace("Z", "+00:00"))
        elif isinstance(created_at_val, datetime):
            dt = created_at_val
        else:
            return "unknown date"
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "unknown date"


def _preprocess_for_toon(text: str) -> str:
    """Remove commas and newlines that could break TOON parsing."""
    if not text:
        return ""
    # Replace commas and newlines with spaces, then collapse multiple spaces
    import re
    text = text.replace(",", " ").replace("\n", " ")
    return re.sub(r'\s+', ' ', text).strip()


async def _fts_entity_search(driver, group_id: str, keywords: str, limit: int = 30) -> list[dict]:
    """Layer 1: instant FTS keyword match on entity names/summaries (<50ms)."""
    cypher = """
    CALL QUERY_FTS_INDEX('Entity', 'node_name_and_summary', $query, TOP := $limit)
    WITH node AS n, score
    WHERE n.group_id = $group_id
    RETURN n.uuid AS uuid, n.name AS name, n.summary AS summary, score
    ORDER BY score DESC
    LIMIT $limit
    """
    records, _, _ = await driver.execute_query(
        cypher, query=keywords, group_id=group_id, limit=limit
    )
    return records


async def _fts_episode_search(driver, group_id: str, keywords: str, limit: int = 20) -> list[dict]:
    """Layer 1b: instant FTS keyword match on episode content."""
    cypher = """
    CALL QUERY_FTS_INDEX('Episodic', 'episode_content', $query, TOP := $limit)
    WITH node AS e, score
    WHERE e.group_id = $group_id
    RETURN e.uuid AS uuid, e.name AS name, e.content AS content, e.created_at AS created_at, score
    ORDER BY score DESC
    LIMIT $limit
    """
    records, _, _ = await driver.execute_query(
        cypher, query=keywords, group_id=group_id, limit=limit
    )
    return records


async def _recent_episodes(driver, group_id: str, limit: int = 20) -> list[dict]:
    """Layer 2: most recent episodes by created_at, no LLM call needed."""
    cypher = """
    MATCH (e:Episodic)
    WHERE e.group_id = $group_id
    RETURN e.uuid AS uuid, e.name AS name, e.content AS content, e.created_at AS created_at
    ORDER BY e.created_at DESC
    LIMIT $limit
    """
    records, _, _ = await driver.execute_query(
        cypher, group_id=group_id, limit=limit
    )
    return records


async def _get_nodes_by_uuids(driver, uuids: list[str]) -> list[dict]:
    """Layer 3: fetch full node details for specific UUIDs."""
    if not uuids:
        return []
    cypher = """
    MATCH (n:Entity)
    WHERE n.uuid IN $uuids
    RETURN n.uuid AS uuid, n.name AS name, n.summary AS summary
    """
    records, _, _ = await driver.execute_query(cypher, uuids=uuids)
    return records


async def _fetch_context_async(
    service,
    scope,
    project_root: Path,
    prompt: str,
    session_id: Optional[str],
) -> tuple[str, list, list]:
    """Fetch context using 3-layer progressive disclosure.

    Layer 1: FTS keyword search (<50ms) -- entities + episodes matching prompt keywords
    Layer 2: Recent episodes (chronological, no LLM) -- last 20 episodes
    Layer 3: Full node details for top FTS hits only -- vector search ONLY if needed

    Returns: (continuity_text, layer2_items, layer3_items)
    """
    import asyncio
    from src.models import GraphScope

    # Get driver directly for FTS queries (bypass service.search which does vector search)
    driver = service._graph_manager.get_driver(scope, project_root)
    group_id = service._get_group_id(scope, project_root)

    # Extract keywords from prompt (simple: first 5 non-stop words > 3 chars)
    words = [w for w in prompt.split() if len(w) > 3][:5]
    keywords = " ".join(words) if words else prompt[:50]

    # Layer 1 + Layer 2 in parallel (both are fast DB queries)
    fts_entities, fts_episodes, recent_eps, continuity_results = await asyncio.gather(
        _fts_entity_search(driver, group_id, keywords, limit=30),
        _fts_episode_search(driver, group_id, keywords, limit=10),
        _recent_episodes(driver, group_id, limit=20),
        service.search(query="session summary", scope=scope, project_root=project_root, limit=3),
        return_exceptions=True,
    )

    # Process continuity (same logic as before)
    continuity = ""
    if not isinstance(continuity_results, Exception) and continuity_results:
        summaries = [
            r for r in continuity_results
            if r.get("source_description") == "session_summary"
            or r.get("source") == "session_summary"
        ]
        if not summaries:
            summaries = [
                r for r in continuity_results
                if "session_summary" in r.get("name", "").lower()
            ]
        if summaries:
            summaries.sort(key=lambda r: r.get("created_at", ""), reverse=True)
            continuity = summaries[0].get("snippet", "")[:500]

    # Build Layer 2 items (recent episodes -- guaranteed fast)
    layer2_items = []
    if not isinstance(recent_eps, Exception):
        layer2_items = recent_eps

    # Build Layer 3 items (full details for top FTS entity hits)
    layer3_items = []
    if not isinstance(fts_entities, Exception) and fts_entities:
        top_uuids = [e["uuid"] for e in fts_entities[:5]]
        try:
            layer3_items = await _get_nodes_by_uuids(driver, top_uuids)
        except Exception as e:
            logger.debug("layer3_fetch_failed", error=str(e))

    # Merge FTS episode hits into layer2 (deduplicate by uuid)
    if not isinstance(fts_episodes, Exception) and fts_episodes:
        seen_uuids = {ep.get("uuid") for ep in layer2_items}
        for ep in fts_episodes:
            if ep.get("uuid") not in seen_uuids:
                layer2_items.append(ep)
                seen_uuids.add(ep.get("uuid"))

    return continuity, layer2_items, layer3_items


def _build_option_c(continuity: str, layer2_items: list, layer3_items: list, token_budget: int) -> str:
    """Build Option C XML with 3-layer data and TOON encoding for compact history.

    Layer 2 (recent episodes) and Layer 3 (entity details) use TOON encoding
    when 3+ items for ~40% token reduction. Per user direction, TOON is used
    for inject_context.py output only (not for batch extraction prompts).
    """
    used_tokens = 0

    # Continuity block (fixed cost)
    if continuity:
        continuity_block = f"<continuity>Last session: {continuity}</continuity>"
    else:
        continuity_block = "<continuity></continuity>"
    used_tokens += _approx_tokens(continuity_block)

    # Layer 2: Recent episodes (TOON encoded if 3+ items)
    layer2_budget = min(1000, (token_budget - used_tokens) // 2)
    if len(layer2_items) >= 3:
        toon_data = []
        for ep in layer2_items:
            snippet = _preprocess_for_toon(
                ep.get("content", ep.get("name", ""))[:300]
            )
            date_str = _format_created_at(ep.get("created_at", ""))
            toon_data.append([snippet, date_str])
        layer2_text = encode(toon_data)
        layer2_text = trim_to_token_budget(layer2_text, layer2_budget)
    elif layer2_items:
        lines = []
        for ep in layer2_items:
            snippet = ep.get("content", ep.get("name", ""))[:300]
            date_str = _format_created_at(ep.get("created_at", ""))
            lines.append(f"  - {snippet} ({date_str})")
        layer2_text = "\n".join(lines)
    else:
        layer2_text = ""
    used_tokens += _approx_tokens(layer2_text)

    # Layer 3: Full entity details (TOON encoded if 3+ items)
    layer3_budget = token_budget - used_tokens - 100  # reserve for XML tags
    if len(layer3_items) >= 3:
        toon_data = []
        for node in layer3_items:
            name = _preprocess_for_toon(node.get("name", ""))
            summary = _preprocess_for_toon(node.get("summary", "")[:400])
            toon_data.append([name, summary])
        layer3_text = encode(toon_data)
        layer3_text = trim_to_token_budget(layer3_text, layer3_budget)
    elif layer3_items:
        lines = []
        for node in layer3_items:
            lines.append(f"  - {node.get('name', '')}: {node.get('summary', '')[:400]}")
        layer3_text = "\n".join(lines)
    else:
        layer3_text = ""

    # Assemble XML
    parts = ["<session_context>", continuity_block]
    if layer2_text:
        parts.append(f"<relevant_history>\n{layer2_text}\n</relevant_history>")
    if layer3_text:
        parts.append(f"<entity_details>\n{layer3_text}\n</entity_details>")
    parts.append("</session_context>")
    return "\n".join(parts)


def main() -> None:
    """Main hook logic. Reads from stdin. Writes JSON with 'context' key to stdout."""
    import asyncio

    empty_output = json.dumps({"context": ""})

    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}

        prompt = hook_input.get("prompt", "")
        cwd_str = hook_input.get("cwd", "")
        project_root = Path(cwd_str).resolve() if cwd_str else Path.cwd()
        session_id = _read_session_id(project_root)

        # If no prompt, nothing useful to retrieve
        if not prompt.strip():
            print(empty_output)
            return

        # Import service (after sys.path fix)
        from src.graph.service import get_service
        from src.models import GraphScope

        service = get_service()
        scope = GraphScope.PROJECT

        # Fetch 3-layer context concurrently in a single event loop with a
        # hard wall-clock timeout.  Fail-open: any timeout or exception → empty context.
        try:
            continuity, layer2_items, layer3_items = asyncio.run(
                asyncio.wait_for(
                    _fetch_context_async(service, scope, project_root, prompt, session_id),
                    timeout=_CONTEXT_TIMEOUT_SECONDS,
                )
            )
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug("inject_context_fetch_failed", error=str(e))
            print(empty_output)
            return

        # If neither continuity nor any layer data, output empty
        if not continuity and not layer2_items and not layer3_items:
            print(empty_output)
            return

        # Build Option C XML within 4000 token budget
        context_xml = _build_option_c(continuity, layer2_items, layer3_items, TOKEN_BUDGET)

        # Output JSON to stdout -- Claude Code reads this for additionalContext injection
        print(json.dumps({"context": context_xml}))

    except Exception:
        logger.warning("inject_context_hook_error", tb=traceback.format_exc())
        # Fail-open: empty context, never block session
        print(empty_output)


if __name__ == "__main__":
    main()

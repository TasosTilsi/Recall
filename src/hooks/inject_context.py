#!/usr/bin/env python3
"""UserPromptSubmit hook — injects Option C context before every prompt.

Searches the knowledge graph for temporally-current relevant history and
the most recent session summary, formats as Option C XML, outputs JSON to stdout.

Output format: {"context": "<session_context>...</session_context>"}
Empty context: {"context": ""}

Fail-open: any exception or timeout -> outputs {"context": ""} and exits 0.
Token budget: <=4000 tokens total (approx len(text)//4).
"""
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

# Fix sys.path for subprocess spawn (CWD undefined when Claude Code calls hooks)
_HOOK_DIR = Path(__file__).resolve().parent
_PROJECT_PKG_ROOT = _HOOK_DIR.parent.parent  # src/ -> project root
if str(_PROJECT_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_PKG_ROOT))

import structlog

logger = structlog.get_logger()

TOKEN_BUDGET = 4000
SEARCH_LIMIT = 20


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


def _fetch_continuity(service, scope, project_root: Path) -> str:
    """Fetch the most recent session_summary episode for <continuity> block."""
    import asyncio

    try:
        results = asyncio.run(service.search(
            query="session summary",
            scope=scope,
            project_root=project_root,
            limit=5,
        ))
        # Filter to session_summary episodes only
        summaries = [
            r for r in results
            if r.get("source_description") == "session_summary"
            or r.get("source") == "session_summary"
        ]
        if not summaries:
            # Fall back: take most recent result tagged with session_summary in name
            summaries = [
                r for r in results
                if "session_summary" in r.get("name", "").lower()
            ]
        if summaries:
            # Sort by created_at descending, take most recent
            summaries.sort(key=lambda r: r.get("created_at", ""), reverse=True)
            return summaries[0].get("snippet", "")[:500]
    except Exception as e:
        logger.debug("continuity_fetch_error", error=str(e))
    return ""


def _fetch_relevant_history(
    service,
    scope,
    project_root: Path,
    prompt: str,
    session_id: Optional[str],
) -> list:
    """3-step progressive retrieval: search -> rank by recency + session boost -> return top-N."""
    import asyncio

    try:
        results = asyncio.run(service.search(
            query=prompt,
            scope=scope,
            project_root=project_root,
            limit=SEARCH_LIMIT,
        ))
    except Exception as e:
        logger.debug("history_search_error", error=str(e))
        return []

    if not results:
        return []

    # Score: recency (higher created_at = higher score) + session boost
    def _rank_key(r: dict):
        created = r.get("created_at", "")
        recency_score = created if isinstance(created, str) else str(created)
        session_boost = 1 if (session_id and session_id in str(r.get("tags", []))) else 0
        return (session_boost, recency_score)

    results.sort(key=_rank_key, reverse=True)
    return results


def _build_option_c(continuity: str, history_items: list, token_budget: int) -> str:
    """Build Option C XML block within token budget.

    Priority when tight: recent session facts -> recent git facts -> older facts (already sorted).
    """
    used_tokens = 0

    # Continuity block (fixed cost)
    if continuity:
        continuity_block = f"<continuity>Last session: {continuity}</continuity>"
    else:
        continuity_block = "<continuity></continuity>"
    used_tokens += _approx_tokens(continuity_block)

    # Build relevant_history items within remaining budget
    history_overhead = _approx_tokens("<relevant_history>\n</relevant_history>")
    remaining = token_budget - used_tokens - history_overhead

    history_lines = []
    for item in history_items:
        snippet = item.get("snippet", item.get("name", ""))[:300]
        date_str = _format_created_at(item.get("created_at", ""))
        line = f"  - {snippet} (since {date_str}, current)"
        line_tokens = _approx_tokens(line)
        if remaining - line_tokens < 0:
            break
        history_lines.append(line)
        remaining -= line_tokens

    history_block = "<relevant_history>\n" + "\n".join(history_lines) + "\n</relevant_history>"

    return (
        "<session_context>\n"
        + continuity_block + "\n"
        + history_block + "\n"
        + "</session_context>"
    )


def main() -> None:
    """Main hook logic. Reads from stdin. Writes JSON with 'context' key to stdout."""
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

        # Fetch continuity (most recent session summary)
        continuity = _fetch_continuity(service, scope, project_root)

        # Fetch relevant history (search -> rank -> top-N)
        history_items = _fetch_relevant_history(
            service, scope, project_root, prompt, session_id
        )

        # If neither continuity nor history, output empty
        if not continuity and not history_items:
            print(empty_output)
            return

        # Build Option C XML within 4000 token budget
        context_xml = _build_option_c(continuity, history_items, TOKEN_BUDGET)

        # Output JSON to stdout -- Claude Code reads this for additionalContext injection
        print(json.dumps({"context": context_xml}))

    except Exception:
        logger.warning("inject_context_hook_error", tb=traceback.format_exc())
        # Fail-open: empty context, never block session
        print(empty_output)


if __name__ == "__main__":
    main()

"""Context resource for the graphiti MCP server.

Provides the graphiti://context resource: session-start context injection
from the local knowledge graph. Returns TOON-encoded decisions + architecture
context (under token budget), or empty string for empty graphs.

IMPORTANT: All output goes to stderr only. The MCP stdio transport uses stdout
for JSON-RPC messages — any stdout write (including print()) corrupts the
protocol. Use `logger.*` calls only; logging is configured to stream=sys.stderr.
"""
import json
import logging
import subprocess
import sys
from pathlib import Path

from src.mcp_server.tools import _GRAPHITI_CLI, _get_cwd

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
logger = logging.getLogger(__name__)


def _is_index_stale(project_root: str | None) -> bool:
    """Check if git index is stale in <10ms.

    Compares current git HEAD SHA against the last_indexed_sha stored in
    .graphiti/index-state.json. Returns False (not stale) if project_root
    is None or any error occurs.
    """
    if not project_root:
        return False
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=project_root
        )
        if result.returncode != 0:
            return False
        current_sha = result.stdout.strip()[:8]

        state_file = Path(project_root) / ".graphiti" / "index-state.json"
        if not state_file.exists():
            return True  # No index at all — stale
        data = json.loads(state_file.read_text())
        last_sha = (data.get("last_indexed_sha") or "")[:8]
        return current_sha != last_sha
    except Exception as e:
        logger.debug("Stale check failed (non-blocking): %s", e)
        return False  # Fail safe: don't trigger re-index on error


def _trigger_background_reindex(project_root: str | None) -> None:
    """Start a background re-index without blocking.

    Uses Popen with DEVNULL so it does not inherit the MCP server's stdio.
    Returns immediately — context injection is NOT blocked by re-indexing.
    """
    if not project_root:
        return
    try:
        subprocess.Popen(
            [_GRAPHITI_CLI, "index"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=project_root,
        )
        logger.info("Background re-index triggered for %s", project_root)
    except Exception as e:
        logger.debug("Background re-index failed to start: %s", e)


def _get_token_budget() -> int:
    """Read mcp.context_tokens from config. Default 8192."""
    try:
        result = subprocess.run(
            [_GRAPHITI_CLI, "config", "get", "mcp.context_tokens"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return int(result.stdout.strip())
    except Exception:
        pass
    return 8192


def get_context() -> str:
    """Session-start context from the local knowledge graph.

    Called by FastMCP when Claude Code accesses graphiti://context.
    Returns TOON-encoded decisions + architecture context, or empty string
    if graph is empty (silent — do not prompt user to fill the graph).

    Latency target: <100ms p95. Stale detection is fast (<10ms).
    Re-indexing is always non-blocking (background subprocess).
    """
    from src.mcp_server.toon_utils import encode_response, trim_to_token_budget

    project_root = _get_cwd()

    # Check staleness in <10ms and trigger background re-index if needed.
    # Do NOT wait for re-index — return current (possibly stale) context immediately.
    if _is_index_stale(project_root):
        _trigger_background_reindex(project_root)

    # Query for high-priority context: decisions + architecture first
    try:
        result = subprocess.run(
            [_GRAPHITI_CLI, "search", "decisions architecture patterns", "--limit", "20", "--format", "json"],
            capture_output=True, text=True, timeout=30,
            cwd=project_root,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Context query timed out")
        return ""
    except Exception as e:
        logger.warning("Context query failed: %s", e)
        return ""

    if result.returncode != 0 or not result.stdout.strip():
        return ""  # Empty graph: silent, inject nothing

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ""

    if not data:
        return ""

    # Encode as TOON and trim to token budget
    encoded = encode_response(data)
    budget = _get_token_budget()
    return trim_to_token_budget(encoded, budget)

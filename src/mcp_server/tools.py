"""MCP tool handler functions that wrap the recall CLI via subprocess.

Each function in this module is a plain Python callable that will be registered
with FastMCP using @mcp.tool() decorators in server.py (Plan 03).

IMPORTANT: All logging in this module MUST go to stderr only — never stdout.
The MCP stdio transport uses stdout for JSON-RPC messages. Any stdout write
(including print() calls, Rich console output, or structlog) will corrupt the
protocol. Use `logger.warning(...)` or `logging.getLogger(__name__).error(...)`
— both route to stderr via the basicConfig below.
"""
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
logger = logging.getLogger(__name__)

# Resolve the recall CLI from the same venv bin/ as the running Python.
# Using the bare name "recall" fails when Claude Code's PATH doesn't include
# the virtualenv (which is the common case for MCP stdio servers).
_RECALL_CLI = str(Path(sys.executable).parent / "recall")

try:
    from src.mcp_server.toon_utils import encode_response
except ImportError:
    def encode_response(data):
        return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_recall(
    args: list[str],
    timeout: int = 30,
    cwd: str | None = None,
) -> tuple[int, str, str]:
    """Run recall CLI and return (returncode, stdout, stderr).

    CWD priority:
    1. GRAPHITI_PROJECT_ROOT env var (explicit override, set by callers who
       know the project root)
    2. The ``cwd`` argument (caller-supplied project directory)
    3. None (inherit the MCP server process CWD, which is Claude Code's CWD)

    Args:
        args: List of CLI arguments (e.g. ["search", "query", "--limit", "5"]).
        timeout: Seconds before subprocess.TimeoutExpired is raised.
        cwd: Working directory for scope detection. Overridden by env var.

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    effective_cwd = os.environ.get("GRAPHITI_PROJECT_ROOT") or cwd
    try:
        result = subprocess.run(
            [_RECALL_CLI] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=effective_cwd,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "recall CLI not found. Run 'pip install graphiti-knowledge-graph' to install."
        )
    return result.returncode, result.stdout, result.stderr


def _get_cwd() -> str | None:
    """Get project CWD for subprocess calls (scope detection).

    Returns GRAPHITI_PROJECT_ROOT if set, else None (inherit process CWD).
    """
    return os.environ.get("GRAPHITI_PROJECT_ROOT") or None


def _scope_flags(scope: str) -> list[str]:
    """Return CLI flags for the given scope value.

    Args:
        scope: "global", "project", or "auto" (no flag added for auto).

    Returns:
        List of zero or one flag strings.
    """
    if scope == "global":
        return ["--global"]
    if scope == "project":
        return ["--project"]
    return []


def _parse_json_or_raw(stdout: str, cmd_name: str) -> str:
    """Parse JSON stdout and encode via encode_response, or return raw on failure.

    Args:
        stdout: Raw stdout string from the graphiti CLI subprocess.
        cmd_name: Command name used in the warning log (e.g. "search", "list").

    Returns:
        encode_response(data) if stdout is valid JSON, else stdout.strip().
    """
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning("recall %s returned non-JSON output; returning raw stdout", cmd_name)
        return stdout.strip()
    return encode_response(data)


# ---------------------------------------------------------------------------
# Read-oriented tools (5)
# ---------------------------------------------------------------------------

def recall_search(
    query: str,
    limit: int = 10,
    exact: bool = False,
    scope: str = "auto",
) -> str:
    """Search the knowledge graph for entities matching a query.

    Args:
        query: The search query string.
        limit: Maximum number of results to return (default 10).
        exact: If True, use exact/literal matching instead of semantic search.
        scope: "auto" (default), "global", or "project".

    Returns:
        TOON-encoded search results or JSON for small result sets.

    Raises:
        RuntimeError: If the recall CLI returns a non-zero exit code.
    """
    cmd = ["search", query, "--limit", str(limit), "--format", "json"]
    if exact:
        cmd.append("--exact")
    cmd.extend(_scope_flags(scope))

    returncode, stdout, stderr = _run_recall(cmd, timeout=30, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"recall search failed: {stderr.strip()}")

    return _parse_json_or_raw(stdout, "search")


def recall_list(
    limit: int = 15,
    scope: str = "auto",
) -> str:
    """List entities in the knowledge graph.

    Args:
        limit: Maximum number of entities to return (default 15).
        scope: "auto" (default), "global", or "project".

    Returns:
        TOON-encoded entity list or JSON for small result sets.

    Raises:
        RuntimeError: If the recall CLI returns a non-zero exit code.
    """
    cmd = ["list", "--limit", str(limit), "--format", "json"]
    cmd.extend(_scope_flags(scope))

    returncode, stdout, stderr = _run_recall(cmd, timeout=30, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"recall list failed: {stderr.strip()}")

    return _parse_json_or_raw(stdout, "list")


def recall_show(name_or_id: str) -> str:
    """Show details for a single entity by name or ID.

    Args:
        name_or_id: The entity name or UUID to look up.

    Returns:
        JSON-encoded entity details (single object, not TOON).

    Raises:
        RuntimeError: If the recall CLI returns a non-zero exit code.
    """
    cmd = ["show", name_or_id, "--format", "json"]

    returncode, stdout, stderr = _run_recall(cmd, timeout=30, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"recall show failed: {stderr.strip()}")

    # Single item — encode_response() returns JSON (not TOON) for single dicts
    return _parse_json_or_raw(stdout, "show")


def recall_summarize(scope: str = "auto") -> str:
    """Get a summary of the knowledge graph contents.

    Args:
        scope: "auto" (default), "global", or "project".

    Returns:
        JSON-encoded summary dict.

    Raises:
        RuntimeError: If the recall CLI returns a non-zero exit code.
    """
    cmd = ["summarize", "--format", "json"]
    cmd.extend(_scope_flags(scope))

    returncode, stdout, stderr = _run_recall(cmd, timeout=60, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"recall summarize failed: {stderr.strip()}")

    # Summary is a single dict object — return as JSON (not TOON)
    return _parse_json_or_raw(stdout, "summarize")


def recall_health() -> str:
    """Check the health status of the recall system.

    Health check failures are informational — this function never raises even
    on non-zero exit. The stderr message is returned as a warning string so
    the caller (Claude Code) can inform the user about degraded state.

    Returns:
        Health status string (plain text stdout, or stderr warning on failure).
    """
    cmd = ["health", "--format", "json"]

    returncode, stdout, stderr = _run_recall(cmd, timeout=15, cwd=_get_cwd())

    if returncode != 0:
        # Health check failure is informational — return warning, don't raise
        warning = stderr.strip() or stdout.strip() or "recall health check returned non-zero exit code."
        logger.warning("recall health non-zero: %s", warning)
        return f"Warning: {warning}"

    return stdout.strip()


# ---------------------------------------------------------------------------
# Write / action tools (5)
# ---------------------------------------------------------------------------

def recall_note(
    content: str,
    tags: str = "",
    scope: str = "auto",
) -> str:
    """Add a note to the knowledge graph.

    Args:
        content: The knowledge content to add.
        tags: Comma-separated tags to attach (optional).
        scope: "auto" (default), "global", or "project".

    Returns:
        Success message from the CLI, or a default message.

    Raises:
        RuntimeError: If the recall CLI returns a non-zero exit code.
    """
    cmd = ["note", content]
    if tags:
        cmd.extend(["--tags", tags])
    cmd.extend(_scope_flags(scope))

    returncode, stdout, stderr = _run_recall(cmd, timeout=60, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"recall note failed: {stderr.strip()}")

    return stdout.strip() or "Note added successfully."


def recall_delete(
    name_or_id: str,
    force: bool = True,
) -> str:
    """Delete an entity from the knowledge graph.

    Always passes --force because MCP callers don't have an interactive TTY
    for confirmation prompts.

    Args:
        name_or_id: The entity name or UUID to delete.
        force: Always True for MCP callers (no interactive TTY).

    Returns:
        Success message from the CLI, or a default message.

    Raises:
        RuntimeError: If the recall CLI returns a non-zero exit code.
    """
    cmd = ["delete", name_or_id, "--force"]

    returncode, stdout, stderr = _run_recall(cmd, timeout=30, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"recall delete failed: {stderr.strip()}")

    return stdout.strip() or "Entity deleted."


def recall_stale(scope: str = "auto") -> str:
    """Preview nodes eligible for TTL archiving.

    Returns TOON-encoded list of stale nodes with name, age (days), and score.
    Score 0.0 = most stale, 1.0 = healthiest.

    Args:
        scope: "auto" (default), "global", or "project".

    Returns:
        TOON-encoded stale node list or JSON for small result sets.

    Raises:
        RuntimeError: If the recall CLI returns a non-zero exit code.
    """
    cmd = ["stale", "--format", "json", "--all"] + _scope_flags(scope)

    returncode, stdout, stderr = _run_recall(cmd, timeout=30, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"recall stale failed: {stderr.strip() or stdout.strip()}")

    return _parse_json_or_raw(stdout, "stale")


def recall_compact(scope: str = "auto") -> str:
    """Compact the knowledge graph by deduplicating entities.

    This operation can be slow (LLM-assisted deduplication). Uses a 120-second
    timeout to accommodate large graphs.

    Args:
        scope: "auto" (default), "global", or "project".

    Returns:
        Success message from the CLI, or a default message.

    Raises:
        RuntimeError: If the recall CLI returns a non-zero exit code.
    """
    cmd = ["compact"]
    cmd.extend(_scope_flags(scope))

    returncode, stdout, stderr = _run_recall(cmd, timeout=120, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"recall compact failed: {stderr.strip()}")

    return stdout.strip() or "Knowledge graph compacted."


def graphiti_index(
    full: bool = False,
    since: str = "",
) -> str:
    """Index git history into the knowledge graph.

    Incremental by default — only processes commits not yet indexed.
    Use full=True to wipe all git-indexed knowledge and re-index entire
    history from scratch. This operation can be slow for large repositories
    (5+ minutes for histories with thousands of commits).

    Args:
        full: If True, wipe all git-indexed knowledge and re-index from scratch.
        since: Index commits since date (YYYY-MM-DD) or commit SHA (optional).
               Empty string means no filtering (default — all new commits).

    Returns:
        Status message from the CLI with commits processed and entities created.

    Raises:
        RuntimeError: If the graphiti CLI returns a non-zero exit code.
    """
    cmd = ["index"]
    if full:
        cmd.append("--full")
    if since:
        cmd.extend(["--since", since])

    returncode, stdout, stderr = _run_graphiti(cmd, timeout=300, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"graphiti index failed: {stderr.strip()}")

    return stdout.strip() or "Git history indexed successfully."


def graphiti_capture() -> str:
    """Capture current conversation context into the knowledge graph.

    Runs asynchronously — returns immediately without waiting for completion.
    Capture operations involve LLM summarization and can take 5-30 seconds.
    Using subprocess.Popen (non-blocking) rather than subprocess.run (blocking)
    ensures the MCP server remains responsive.

    Both stdout and stderr are redirected to DEVNULL so the background process
    does not inherit the stdio transport's file descriptors (which would corrupt
    the JSON-RPC stream).

    start_new_session=True detaches the subprocess from the MCP server process
    group, preventing zombie processes when the server exits.

    Returns:
        Confirmation message that capture started in background.

    Raises:
        RuntimeError: If the graphiti CLI is not found or cannot be launched.
    """
    cwd = _get_cwd()
    try:
        subprocess.Popen(
            [_GRAPHITI_CLI, "capture", "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            cwd=cwd,
        )
        return "Conversation capture started in background."
    except FileNotFoundError:
        raise RuntimeError(
            "graphiti CLI not found. Run 'pip install graphiti-knowledge-graph' to install."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to start capture: {e}")


def graphiti_config(key: str, value: str = "") -> str:
    """Get or set a graphiti configuration value.

    If value is empty, reads the current value of the key.
    If value is non-empty, sets the key to the given value.

    Args:
        key: Dotted config key path (e.g. "cloud.endpoint", "mcp.context_tokens").
        value: Value to set. If empty, performs a get operation.

    Returns:
        Current value (for get) or confirmation (for set) from the CLI.

    Raises:
        RuntimeError: If the graphiti CLI returns a non-zero exit code.
    """
    if value:
        cmd = ["config", "set", key, value]
    else:
        cmd = ["config", "get", key]

    returncode, stdout, stderr = _run_graphiti(cmd, timeout=10, cwd=_get_cwd())

    if returncode != 0:
        raise RuntimeError(f"graphiti config failed: {stderr.strip()}")

    return stdout.strip()


__all__ = [
    "graphiti_add",
    "graphiti_search",
    "graphiti_list",
    "graphiti_show",
    "graphiti_delete",
    "graphiti_summarize",
    "graphiti_stale",
    "graphiti_compact",
    "graphiti_index",
    "graphiti_capture",
    "graphiti_health",
    "graphiti_config",
]

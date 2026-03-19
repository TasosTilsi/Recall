#!/usr/bin/env python3
"""PostToolUse hook — fire-and-forget tool capture via jsonl append.

Appends sanitized tool call content to .graphiti/pending_tool_captures.jsonl.
Security filtering applied before write. No LLM calls, no blocking operations.
Target: <200ms (well within 1s PostToolUse timeout budget).

Fail-open: any exception exits 0 with no stdout output.
"""
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Fix sys.path for subprocess spawn
_HOOK_DIR = Path(__file__).resolve().parent
_PROJECT_PKG_ROOT = _HOOK_DIR.parent.parent
if str(_PROJECT_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_PKG_ROOT))

import structlog

logger = structlog.get_logger()

CAPTURED_TOOLS = {"Write", "Edit", "Bash", "WebFetch"}
OUTPUT_TRUNCATE_CHARS = 500
ARGS_TRUNCATE_CHARS = 200

PENDING_CAPTURES_FILENAME = ".graphiti/pending_tool_captures.jsonl"


def _extract_key_args(tool_name: str, tool_input: dict) -> str:
    """Extract the most relevant argument for the tool call (truncated)."""
    if tool_name in ("Write", "Edit"):
        return str(tool_input.get("file_path", ""))[:ARGS_TRUNCATE_CHARS]
    elif tool_name == "Bash":
        return str(tool_input.get("command", ""))[:ARGS_TRUNCATE_CHARS]
    elif tool_name == "WebFetch":
        return str(tool_input.get("url", ""))[:ARGS_TRUNCATE_CHARS]
    return ""


def _build_content(tool_name: str, key_args: str, output_snippet: str) -> str:
    """Build the content string to be stored as a graph episode."""
    return f"Tool: {tool_name}\nArgs: {key_args}\nOutput: {output_snippet}"


def main() -> None:
    """Main hook logic. Reads from stdin. Writes nothing to stdout."""
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw) if raw.strip() else {}

        tool_name = hook_input.get("tool_name", "")

        # Only capture specified tool types
        if tool_name not in CAPTURED_TOOLS:
            return

        tool_input = hook_input.get("tool_input", {})
        tool_response = hook_input.get("tool_response", {})
        session_id = hook_input.get("session_id", "")
        cwd_str = hook_input.get("cwd", "")
        project_root = Path(cwd_str).resolve() if cwd_str else Path.cwd()

        # Extract key args and truncate output
        key_args = _extract_key_args(tool_name, tool_input)
        output_raw = str(tool_response.get("content", ""))[:OUTPUT_TRUNCATE_CHARS]

        # Security filtering — sanitize BEFORE writing (Phase 2 invariant)
        # sanitize_content returns SanitizationResult; access .sanitized_content for the string
        from src.security import sanitize_content
        sanitized_key_args = sanitize_content(key_args).sanitized_content
        sanitized_output = sanitize_content(output_raw).sanitized_content

        # Build entry dict
        entry = {
            "tool_name": tool_name,
            "key_args": sanitized_key_args,
            "output_snippet": sanitized_output,
            "session_id": session_id,
            "cwd": str(project_root),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Append JSON line to pending captures file (atomic enough for single-writer pattern)
        pending_file = project_root / PENDING_CAPTURES_FILENAME
        pending_file.parent.mkdir(parents=True, exist_ok=True)
        with open(pending_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        logger.debug("tool_capture_appended",
                     tool=tool_name,
                     session_id=session_id[:8] if session_id else "none")

    except Exception:
        logger.warning("capture_entry_hook_error",
                       tb=traceback.format_exc())


if __name__ == "__main__":
    main()

"""Note command for recall CLI.

Manually adds a memory entry to the pending captures queue.
Processed by session_stop.py on next PreCompact hook — same pipeline as PostToolUse.

Fail-open: any exception exits 0 (consistent with hook script behavior).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer

from src.cli.output import print_success, print_error
from src.cli.utils import resolve_scope, EXIT_SUCCESS, EXIT_ERROR


PENDING_CAPTURES_FILENAME = ".graphiti/pending_tool_captures.jsonl"


def note_command(
    text: Annotated[str, typer.Argument(help="Memory text to add (e.g. 'decision: use JWT auth')")],
) -> None:
    """Manually add a memory to the knowledge graph.

    Writes the note to .graphiti/pending_tool_captures.jsonl where it is
    processed by the PreCompact/Stop hook on next session end.

    Examples:
        recall note "decision: use JWT auth with 15min expiry"
        recall note "pattern: always use structlog in src/ except mcp_server"
    """
    try:
        # Security filtering — sanitize before writing (Phase 2 invariant)
        try:
            from src.security import sanitize_content
            sanitized_text = sanitize_content(text).sanitized_content
        except Exception:
            sanitized_text = text  # fail-open: write unsanitized if security import fails

        # Resolve project root for the pending file path
        try:
            scope, root = resolve_scope()
        except Exception:
            root = Path.cwd()

        project_root = root or Path.cwd()

        # Build entry in the same format as capture_entry.py
        entry = {
            "tool_name": "Note",
            "key_args": sanitized_text[:200],
            "output_snippet": "",
            "session_id": "",
            "cwd": str(project_root),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Append to pending captures file
        pending_file = project_root / PENDING_CAPTURES_FILENAME
        pending_file.parent.mkdir(parents=True, exist_ok=True)
        with open(pending_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        print_success(f"Note added — will be processed on next session end")
        raise typer.Exit(EXIT_SUCCESS)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to add note: {e}")
        raise typer.Exit(EXIT_ERROR)

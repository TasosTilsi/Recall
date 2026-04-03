"""Note command for recall CLI.

Immediately adds a memory entry to the knowledge graph via service.add().
Falls back to the pending-captures queue if the LLM is unavailable.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer

from src.cli.output import console, print_success, print_error, print_warning
from src.cli.utils import resolve_scope, EXIT_SUCCESS, EXIT_ERROR


PENDING_CAPTURES_FILENAME = ".recall/pending_tool_captures.jsonl"


def note_command(
    text: Annotated[str, typer.Argument(help="Memory text to add (e.g. 'decision: use JWT auth')")],
) -> None:
    """Manually add a memory to the knowledge graph.

    Saves immediately via the LLM extraction pipeline. Falls back to the
    pending-captures queue if the LLM is unavailable.

    Examples:
        recall note "decision: use JWT auth with 15min expiry"
        recall note "pattern: always use structlog in src/ except mcp_server"
    """
    # Security filtering — sanitize before processing (Phase 2 invariant)
    try:
        from src.security import sanitize_content
        sanitized_text = sanitize_content(text).sanitized_content
    except Exception:
        sanitized_text = text

    preview = sanitized_text[:72] + ("…" if len(sanitized_text) > 72 else "")

    try:
        scope, root = resolve_scope()
    except Exception:
        root = None
    project_root = root or Path.cwd()

    # Try synchronous save via service.add()
    try:
        from src.graph.service import get_service, run_graph_operation
        from src.models import GraphScope

        service = get_service()
        graph_scope = GraphScope.PROJECT if root else GraphScope.GLOBAL

        with console.status(f"[dim]Saving note to knowledge graph...[/dim]"):
            run_graph_operation(
                service.add(
                    content=sanitized_text,
                    scope=graph_scope,
                    project_root=project_root if graph_scope == GraphScope.PROJECT else None,
                    source="note",
                )
            )

        scope_label = "project" if graph_scope == GraphScope.PROJECT else "global"
        print_success(f"Note saved to {scope_label} graph")
        console.print(f"  [dim]{preview}[/dim]")
        console.print(f"  [dim]Run [bold]recall search {_search_hint(sanitized_text)}[/bold] to retrieve it.[/dim]")
        raise typer.Exit(EXIT_SUCCESS)

    except typer.Exit:
        raise
    except Exception as e:
        # LLM unavailable or graph error — fall back to queue
        print_warning(f"LLM unavailable — queuing note for later processing")
        console.print(f"  [dim]{preview}[/dim]")
        try:
            entry = {
                "tool_name": "Note",
                "key_args": sanitized_text[:200],
                "output_snippet": "",
                "session_id": "",
                "cwd": str(project_root),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            pending_file = project_root / PENDING_CAPTURES_FILENAME
            pending_file.parent.mkdir(parents=True, exist_ok=True)
            with open(pending_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            console.print(f"  [dim]Queued — will be processed on next session end.[/dim]")
            raise typer.Exit(EXIT_SUCCESS)
        except typer.Exit:
            raise
        except Exception as queue_err:
            print_error(f"Failed to queue note: {queue_err}")
            raise typer.Exit(EXIT_ERROR)


def _search_hint(text: str) -> str:
    """Extract a short keyword hint from note text for the search suggestion."""
    # Use first meaningful word (skip common prefixes like "decision:", "pattern:")
    words = text.replace(":", " ").split()
    skip = {"decision", "pattern", "note", "todo", "fix", "bug", "always", "never", "use"}
    for word in words:
        clean = word.strip("\"'.,;").lower()
        if len(clean) > 3 and clean not in skip:
            return f'"{clean}"'
    return f'"{words[0]}"' if words else '"..."'

"""Search command for Graphiti CLI.

Searches the knowledge graph with semantic (default) or exact matching,
supporting filters, result formatting, and pagination.
"""
import typer
from typing import Annotated, Optional
from datetime import datetime
from pathlib import Path

from src.cli.output import console, print_table, print_compact, print_json, print_warning
from src.cli.utils import resolve_scope, DEFAULT_LIMIT, EXIT_SUCCESS, EXIT_ERROR
from src.models import GraphScope
from src.graph import get_service, run_graph_operation


def _auto_sync(project_root) -> None:
    """Run incremental git sync before search. Silent and best-effort.

    Implements CLI-03: recall search auto-syncs git history before returning results.
    Uses GitIndexer's built-in cooldown — skips if ran within the last 5 minutes.
    Fails silently if not in a git repo or GitIndexer unavailable.
    """
    try:
        if project_root is None:
            return
        from src.indexer import GitIndexer
        GitIndexer(project_root=project_root).run(full=False)
    except Exception:
        pass  # fail-open: search must not be blocked by sync failure


def _search_entities(
    query: str,
    scope: GraphScope,
    project_root: Optional[Path],
    exact: bool,
    since: Optional[str],
    before: Optional[str],
    type_filter: Optional[str],
    tags: Optional[list[str]],
    limit: Optional[int],
) -> list[dict]:
    """Search entities in the knowledge graph via GraphService.

    Calls GraphService.search() which performs semantic or exact search
    against the knowledge graph database.

    Args:
        query: Search query string
        scope: Graph scope to search in
        project_root: Project root path (required for PROJECT scope)
        exact: Whether to use exact matching (True) or semantic (False)
        since: Filter results after this date/duration (future enhancement)
        before: Filter results before this date (future enhancement)
        type_filter: Filter by type (future enhancement)
        tags: Filter by tags (future enhancement)
        limit: Maximum number of results (None for unlimited)

    Returns:
        List of result dictionaries with name, type, snippet, score, created_at, scope, tags
    """
    # Get service and call search operation
    service = get_service()
    results = run_graph_operation(
        service.search(
            query=query,
            scope=scope,
            project_root=project_root,
            exact=exact,
            limit=limit or 15,
        )
    )

    # Note: Date/type/tag filters not yet implemented in GraphService
    # These will be added in future integration phases
    # For now, we return all matching results from semantic/exact search

    return results


def search_command(
    query: Annotated[str, typer.Argument(help="Search query")],
    exact: Annotated[bool, typer.Option("--exact", "-e", help="Literal string matching instead of semantic")] = False,
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="Search global scope only")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", help="Search project scope only")] = False,
    since: Annotated[Optional[str], typer.Option("--since", help="Filter results after date/duration (e.g., '7d', '2024-01-01')")] = None,
    before: Annotated[Optional[str], typer.Option("--before", help="Filter results before date")] = None,
    type_filter: Annotated[Optional[str], typer.Option("--type", help="Filter by type: entity, relationship")] = None,
    tag: Annotated[Optional[list[str]], typer.Option("--tag", "-t", help="Filter by tag")] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max results to return")] = DEFAULT_LIMIT,
    all_results: Annotated[bool, typer.Option("--all", help="Return all results (no limit)")] = False,
    compact: Annotated[bool, typer.Option("--compact", "-c", help="One-line-per-result view")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
):
    """Search the knowledge graph.

    Supports semantic search (default) and exact literal matching with various
    filters and formatting options.

    Examples:
        recall search "meeting notes"
        recall search "API design" --exact
        recall search "roadmap" --since 7d --tag planning
        recall search "architecture" --compact
        recall search "decisions" --format json
    """
    try:
        # 1. Resolve scope
        scope, project_root = resolve_scope(global_scope, project_scope)

        # 1a. Auto-sync git history before searching (CLI-03)
        _auto_sync(project_root)

        # 2. Determine effective limit
        effective_limit = None if all_results else limit

        # 3. Search with spinner
        with console.status("Searching knowledge graph..."):
            results = _search_entities(
                query=query,
                scope=scope,
                project_root=project_root,
                exact=exact,
                since=since,
                before=before,
                type_filter=type_filter,
                tags=tag,
                limit=effective_limit,
            )

        # 4. Handle no results
        if not results:
            print_warning(f"No results found for '{query}'")
            return

        # 5. Format output based on flags
        if format == "json":
            print_json(results)
        elif compact:
            print_compact(results)
        else:
            # Default: table view
            # Reformat results for table with selected columns
            table_data = []
            for r in results:
                table_data.append({
                    "Name": r["name"],
                    "Type": r["type"],
                    "Snippet": r["snippet"][:60] + "..." if len(r["snippet"]) > 60 else r["snippet"],
                    "Score": f"{r['score']:.2f}" if "score" in r else "N/A",
                    "Created": r["created_at"].split("T")[0],  # Just the date
                })
            print_table(table_data, columns=["Name", "Type", "Snippet", "Score", "Created"])

        # 6. Print result count
        result_count = len(results)
        if all_results or effective_limit is None:
            console.print(f"\n[dim]{result_count} results[/dim]")
        else:
            # Show total available if we're limiting
            console.print(f"\n[dim]{result_count} of {result_count} results[/dim]")
            if result_count >= limit:
                console.print("[dim](use --all for complete list)[/dim]")

    except typer.BadParameter:
        # Re-raise parameter errors (already formatted by typer)
        raise
    except Exception as e:
        from src.cli.output import print_error
        print_error(f"Search failed: {str(e)}")
        raise typer.Exit(EXIT_ERROR)

"""Memory command group for knowledge graph search and management.

Provides `graphiti memory search` for querying the knowledge graph
using hybrid BM25+semantic search.
"""
import typer
from typing import Annotated, Optional
from pathlib import Path

from src.cli.output import console, print_error, print_json
from src.cli.utils import resolve_scope, EXIT_SUCCESS, EXIT_ERROR
from src.graph.service import get_service, run_graph_operation
from src.models import GraphScope

memory_app = typer.Typer(
    name="memory",
    help="Search and manage knowledge graph memory",
    no_args_is_help=True,
)


@memory_app.command(name="search")
def memory_search_command(
    query: Annotated[str, typer.Argument(help="Search query")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results to return")] = 10,
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="Search global scope")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
) -> None:
    """Search knowledge graph for relevant history.

    Uses BM25+semantic hybrid search via graphiti-core.
    Results are sorted by recency (newest first).

    Examples:
        graphiti memory search "authentication decisions"
        graphiti memory search "Phase 15 hooks" --limit 5
        graphiti memory search "LLM config" --global
    """
    try:
        scope, project_root = resolve_scope()

        if global_scope:
            scope = GraphScope.GLOBAL
            project_root = None
        else:
            if project_root is None:
                scope = GraphScope.GLOBAL

        service = get_service()
        results = run_graph_operation(
            service.search(
                query=query,
                scope=scope,
                project_root=project_root,
                limit=limit,
            )
        )

        if not results:
            if format == "json":
                print_json([])
            else:
                console.print("[dim]No results found[/dim]")
            raise typer.Exit(EXIT_SUCCESS)

        if format == "json":
            print_json(results)
        else:
            # Human-readable output: name + snippet + date
            from rich.table import Table
            table = Table(
                title=f"Memory search: '{query}'",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Name", style="white", max_width=30)
            table.add_column("Snippet", style="dim", max_width=60)
            table.add_column("Date", style="cyan", max_width=12)

            for r in results:
                name = r.get("name", "") or ""
                snippet = r.get("snippet", "") or ""
                created = r.get("created_at", "")
                date_str = str(created)[:10] if created else "—"
                table.add_row(
                    name[:30],
                    snippet[:60],
                    date_str,
                )
            console.print(table)

        raise typer.Exit(EXIT_SUCCESS)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Memory search failed: {str(e)}")
        raise typer.Exit(EXIT_ERROR)

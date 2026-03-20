"""List command for displaying entities in the knowledge graph.

Provides table, compact, and JSON output formats with filtering by scope,
type, and tags. Also exposes detail, stale, compact-expire, and queue
views via flags (CLI-02).
"""
from typing import Annotated, Optional, TYPE_CHECKING
from pathlib import Path
import typer
from rich.table import Table
from src.cli.output import console, print_json, print_table, print_compact, print_warning, print_success
from src.cli.utils import resolve_scope, DEFAULT_LIMIT
from src.models import GraphScope
from src.graph import get_service, run_graph_operation

if TYPE_CHECKING:
    pass


def _list_entities(
    scope: GraphScope,
    project_root: Optional[Path],
    limit: Optional[int],
) -> list[dict]:
    """List entities from the knowledge graph via GraphService.

    Calls GraphService.list_entities() which queries the knowledge graph
    database for entities in the specified scope.

    Args:
        scope: Graph scope to list from
        project_root: Project root path (required for PROJECT scope)
        limit: Maximum number of entities to return

    Returns:
        List of entity dictionaries with name, type, created_at, tags, scope, relationship_count
    """
    # Get service and call list operation
    service = get_service()
    entities = run_graph_operation(
        service.list_entities(
            scope=scope,
            project_root=project_root,
            limit=limit,
        )
    )

    # Convert tags from list to string if needed (for table display)
    for entity in entities:
        if "tags" in entity and isinstance(entity["tags"], list):
            entity["tags"] = ", ".join(entity["tags"])

    return entities


def _show_queue_status() -> None:
    """Display background queue status (replaces `recall queue status`)."""
    from src.queue import get_status
    status = get_status()
    health_msg = {"error": "Queue at or over capacity", "warning": "Queue nearly full"}.get(
        status["health"], "Healthy"
    )
    table = Table(title="Queue Status", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Pending jobs", str(status.get("pending", 0)))
    table.add_row("Dead letter", str(status.get("dead_letter", 0)))
    table.add_row("Capacity", str(status.get("max_size", 0)))
    table.add_row("Health", health_msg)
    console.print(table)


def _show_stale(scope: GraphScope, project_root, all_results: bool, format: Optional[str]) -> None:
    """Preview stale nodes (replaces `recall stale`)."""
    with console.status("[cyan]Scanning for stale nodes...", spinner="dots"):
        stale = run_graph_operation(get_service().list_stale(scope, project_root))
    if not stale:
        print_success("No stale nodes found.")
        return
    cap = 25
    total = len(stale)
    display = stale if all_results else stale[:cap]
    if format == "json":
        print_json(display)
        return
    print_table(display, columns=["name", "age_days", "score"])
    if not all_results and total > cap:
        console.print(f"\n[dim]Showing {cap} of {total} stale nodes. Use --all to see all.[/dim]")


def _do_compact(scope: GraphScope, project_root, force: bool, format: Optional[str]) -> None:
    """Archive stale nodes (replaces `recall compact --expire`)."""
    from src.cli.utils import confirm_action
    with console.status("[cyan]Scanning for stale nodes...", spinner="dots"):
        stale = run_graph_operation(get_service().list_stale(scope, project_root))
    if not stale:
        print_success("No stale nodes to archive.")
        return
    console.print(f"\n[cyan]{len(stale)} nodes are eligible for archiving.[/cyan]\n")
    confirmed = confirm_action(f"{len(stale)} nodes will be archived. Proceed?", force=force)
    if not confirmed:
        console.print("Cancelled")
        return
    archived_count = run_graph_operation(
        get_service().archive_nodes([n["uuid"] for n in stale], scope, project_root)
    )
    print_success(f"Archived {archived_count} nodes.")


def _show_entity_detail(name: str, scope: GraphScope, project_root, format: Optional[str]) -> None:
    """Show detailed entity info (replaces `recall show`)."""
    from src.cli.output import print_error
    from src.cli.utils import EXIT_ERROR
    from rich.panel import Panel
    from rich.text import Text
    result = run_graph_operation(get_service().get_entity(name=name, scope=scope, project_root=project_root))
    if not result:
        print_error(f"Entity '{name}' not found.", suggestion="Try 'recall list' to see available entities.")
        raise typer.Exit(EXIT_ERROR)
    if isinstance(result, list):
        # Ambiguous: show numbered list and prompt
        console.print(f"\n[yellow]Multiple entities match '{name}':[/yellow]\n")
        for idx, match in enumerate(result, 1):
            console.print(f"  {idx}. [cyan]{match['name']}[/cyan] ({match['type']}) - ID: {match.get('id', '')}")
        choice = typer.prompt(f"\nSelect entity [1-{len(result)}]", type=int)
        if choice < 1 or choice > len(result):
            print_error(f"Invalid selection: {choice}")
            raise typer.Exit(EXIT_ERROR)
        result = run_graph_operation(get_service().get_entity(name=result[choice - 1]["name"], scope=scope, project_root=project_root))
    if format == "json":
        print_json(result)
        return
    # Rich panel display
    title = Text(result["name"], style="bold cyan")
    console.print(Panel(title, border_style="cyan"))
    console.print("\n[bold]Metadata:[/bold]")
    console.print(f"  [dim]Type:[/dim]        [magenta]{result['type']}[/magenta]")
    console.print(f"  [dim]Scope:[/dim]       {result['scope']}")
    console.print(f"  [dim]Created:[/dim]     [green]{result['created_at']}[/green]")
    tags = result.get("tags", [])
    if tags:
        console.print(f"  [dim]Tags:[/dim]        {', '.join(tags)}")
    content = result.get("content", "")
    if content:
        console.print("\n[bold]Content:[/bold]")
        console.print(Panel(content, border_style="dim", padding=(1, 2)))
    relationships = result.get("relationships", [])
    if relationships:
        console.print("\n[bold]Relationships:[/bold]")
        for rel in relationships:
            console.print(f"  • [yellow]{rel.get('type', 'related_to')}[/yellow] → [cyan]{rel.get('target', 'Unknown')}[/cyan]")
    else:
        console.print("\n[dim]No relationships[/dim]")
    # Record access for retention tracking (best-effort)
    try:
        entity_uuid = result.get("uuid")
        if entity_uuid:
            run_graph_operation(get_service().record_access(entity_uuid, scope, project_root))
    except Exception:
        pass


def list_command(
    name: Annotated[Optional[str], typer.Argument(help="Entity name — show detail for this entity")] = None,
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="List from global scope")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", help="List from project scope")] = False,
    type_filter: Annotated[Optional[str], typer.Option("--type", help="Filter by type: entity, relationship")] = None,
    tag: Annotated[Optional[list[str]], typer.Option("--tag", "-t", help="Filter by tag")] = None,
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max items to show")] = DEFAULT_LIMIT,
    all_results: Annotated[bool, typer.Option("--all", help="Show all items")] = False,
    one_line: Annotated[bool, typer.Option("--one-line", "-c", help="One-line-per-item view")] = False,
    stale: Annotated[bool, typer.Option("--stale", help="Preview nodes eligible for TTL archiving")] = False,
    compact: Annotated[bool, typer.Option("--compact", help="Archive stale nodes (same as compact --expire)")] = False,
    queue: Annotated[bool, typer.Option("--queue", help="Show background processing queue status")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
):
    """List entities in the knowledge graph.

    Shows entities in table format by default, with options for compact
    one-line view or JSON output. Supports filtering by scope, type, and tags.

    Use flags to access detail, stale, compact-expire, and queue views:
        recall list <name>       Show entity detail
        recall list --stale      Preview TTL-eligible nodes
        recall list --compact    Archive stale nodes
        recall list --queue      Show background queue status
    """
    # Resolve scope
    scope, project_root = resolve_scope(global_scope, project_scope)

    # Route to specialised views based on flags
    if queue:
        _show_queue_status()
        return

    if stale:
        _show_stale(scope, project_root, all_results, format)
        return

    if compact:
        _do_compact(scope, project_root, force=False, format=format)
        return

    if name is not None:
        _show_entity_detail(name, scope, project_root, format)
        return

    # Default: entity table (existing behavior continues below)

    # Determine effective limit (None if --all)
    effective_limit = None if all_results else limit

    # Load entities with spinner
    with console.status("[cyan]Loading entities...", spinner="dots"):
        entities = _list_entities(scope, project_root, effective_limit)

    # Check if empty
    if not entities:
        print_warning("No entities found.")
        raise typer.Exit(0)

    # Apply limit if specified
    total_count = len(entities)
    if effective_limit is not None:
        entities = entities[:effective_limit]

    # Output based on format
    if format == "json":
        print_json(entities)
    elif one_line:
        # For compact view, add snippet field from tags
        for entity in entities:
            entity["snippet"] = entity.get("tags", "")
        print_compact(entities, name_key="name", type_key="type", snippet_key="snippet")
    else:
        # Table view with specific columns
        columns = ["name", "type", "tags", "relationship_count", "created_at"]
        # Rename relationship_count to "Relations" for display
        display_entities = []
        for entity in entities:
            display_entity = entity.copy()
            display_entity["Relations"] = display_entity.pop("relationship_count")
            display_entity["Created"] = display_entity.pop("created_at")
            display_entities.append(display_entity)

        print_table(
            display_entities,
            columns=["name", "type", "tags", "Relations", "Created"]
        )

    # Print count summary
    if effective_limit is not None and total_count > effective_limit:
        console.print(f"\n[dim]Showing {len(entities)} of {total_count} entities[/dim]")
    else:
        console.print(f"\n[dim]{len(entities)} entities[/dim]")

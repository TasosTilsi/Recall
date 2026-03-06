"""Show command for displaying detailed entity information.

Provides rich formatted view of entity details including relationships,
with JSON output option and ambiguous name resolution.
"""
from typing import Annotated, Optional
from pathlib import Path
import typer
from rich.panel import Panel
from rich.text import Text
from src.cli.output import console, print_json, print_error
from src.cli.utils import resolve_scope, EXIT_ERROR
from src.graph import get_service, run_graph_operation
from src.models import GraphScope


def _find_entity(name: str, scope: GraphScope, project_root: Optional[Path] = None) -> dict | list[dict]:
    """Find entity by name from the knowledge graph.

    Args:
        name: Entity name or ID to find
        scope: Graph scope (GLOBAL or PROJECT)
        project_root: Project root path (required for PROJECT scope)

    Returns:
        Entity dict if unique match found, list of matches if ambiguous, or empty dict if not found
    """
    result = run_graph_operation(get_service().get_entity(name=name, scope=scope, project_root=project_root))

    # Handle None (not found) -> return empty dict for backward compatibility
    if result is None:
        return {}

    return result


def show_command(
    entity: Annotated[str, typer.Argument(help="Entity name or ID")],
    global_scope: Annotated[bool, typer.Option("--global", "-g")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p")] = False,
    format: Annotated[Optional[str], typer.Option("--format", help="Output format: json")] = None,
):
    """Show detailed entity information.

    Displays full entity details including relationships, metadata, and content.
    If entity name is ambiguous, prompts user to choose from matching entities.
    """
    # Resolve scope
    scope, project_root = resolve_scope(global_scope, project_scope)

    # Find entity
    result = _find_entity(entity, scope, project_root)

    # Handle not found
    if not result or (isinstance(result, dict) and not result):
        print_error(
            f"Entity '{entity}' not found.",
            suggestion="Try 'graphiti list' to see available entities."
        )
        raise typer.Exit(EXIT_ERROR)

    # Handle ambiguous matches
    if isinstance(result, list):
        console.print(f"\n[yellow]Multiple entities match '{entity}':[/yellow]\n")

        # Display numbered list
        for idx, match in enumerate(result, 1):
            console.print(f"  {idx}. [cyan]{match['name']}[/cyan] ({match['type']}) - ID: {match['id']}")

        # Prompt user to choose
        choice = typer.prompt(f"\nSelect entity [1-{len(result)}]", type=int)

        # Validate choice
        if choice < 1 or choice > len(result):
            print_error(f"Invalid selection: {choice}")
            raise typer.Exit(EXIT_ERROR)

        # Get the selected entity by ID (would need another lookup in real implementation)
        selected_name = result[choice - 1]["name"]
        result = _find_entity(selected_name, scope, project_root)

    # Now result is a single entity dict
    entity_data = result

    # JSON output
    if format == "json":
        print_json(entity_data)
        _record_entity_access(entity_data, scope, project_root)
        return

    # Rich formatted output
    # Title panel with entity name
    title = Text(entity_data["name"], style="bold cyan")
    console.print(Panel(title, border_style="cyan"))

    # Metadata section
    console.print("\n[bold]Metadata:[/bold]")
    console.print(f"  [dim]ID:[/dim]          {entity_data.get('id', 'N/A')}")
    console.print(f"  [dim]Type:[/dim]        [magenta]{entity_data['type']}[/magenta]")
    console.print(f"  [dim]Scope:[/dim]       {entity_data['scope']}")
    console.print(f"  [dim]Created:[/dim]     [green]{entity_data['created_at']}[/green]")
    console.print(f"  [dim]Updated:[/dim]     [green]{entity_data['updated_at']}[/green]")

    # Tags
    tags = entity_data.get("tags", [])
    if tags:
        tags_str = ", ".join(tags)
        console.print(f"  [dim]Tags:[/dim]        {tags_str}")

    # Content/description
    content = entity_data.get("content", "")
    if content:
        console.print("\n[bold]Content:[/bold]")
        console.print(Panel(content, border_style="dim", padding=(1, 2)))

    # Relationships
    relationships = entity_data.get("relationships", [])
    if relationships:
        console.print("\n[bold]Relationships:[/bold]")
        for rel in relationships:
            rel_type = rel.get("type", "related_to")
            target = rel.get("target", "Unknown")
            console.print(f"  • [yellow]{rel_type}[/yellow] → [cyan]{target}[/cyan]")
    else:
        console.print("\n[dim]No relationships[/dim]")

    console.print()  # Blank line at end

    # Record access for retention tracking (must never fail show)
    _record_entity_access(entity_data, scope, project_root)


def _record_entity_access(
    entity_data: dict,
    scope: "GraphScope",
    project_root: Optional[Path],
) -> None:
    """Record entity access in retention.db for TTL tracking.

    Silently ignores all errors — access recording must never fail the show command.
    """
    try:
        entity_uuid = entity_data.get("uuid")
        if entity_uuid:
            run_graph_operation(get_service().record_access(entity_uuid, scope, project_root))
    except Exception:
        pass  # access recording must never fail show

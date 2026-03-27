"""Delete command for removing entities from the knowledge graph.

Provides bulk entity deletion with confirmation prompts, ambiguous name
resolution, and JSON/quiet output modes.
"""
from typing import Annotated, Optional
from pathlib import Path
import typer
from rich.table import Table
from src.cli.output import console, print_json, print_error, print_success
from src.cli.utils import resolve_scope, confirm_action, EXIT_ERROR, EXIT_SUCCESS
from src.graph import get_service, run_graph_operation
from src.models import GraphScope


def _resolve_entity(name: str, scope: GraphScope, project_root: Optional[Path] = None) -> dict | list[dict] | None:
    """Resolve entity name to entity object from the knowledge graph.

    Args:
        name: Entity name or ID to resolve
        scope: Graph scope (GLOBAL or PROJECT)
        project_root: Project root path (required for PROJECT scope)

    Returns:
        Entity dict if unique match, list of matches if ambiguous, None if not found
    """
    result = run_graph_operation(get_service().get_entity(name=name, scope=scope, project_root=project_root))
    return result


def _delete_entities(entities: list[dict], scope: GraphScope, project_root: Optional[Path] = None) -> int:
    """Delete entities from the graph.

    Args:
        entities: List of entity dicts to delete
        scope: Graph scope (GLOBAL or PROJECT)
        project_root: Project root path (required for PROJECT scope)

    Returns:
        Count of entities successfully deleted
    """
    # Extract entity names from the entities list
    names = [e["name"] for e in entities]

    # Call GraphService to delete the entities
    deleted_count = run_graph_operation(get_service().delete_entities(names=names, scope=scope, project_root=project_root))

    return deleted_count


def delete_command(
    entities: Annotated[list[str], typer.Argument(help="Entity names or IDs to delete")],
    force: Annotated[bool, typer.Option("--force", help="Skip confirmation prompt")] = False,
    global_scope: Annotated[bool, typer.Option("--global", "-g")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p")] = False,
    format: Annotated[Optional[str], typer.Option("--format", help="Output format: json")] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
):
    """Delete entities from the knowledge graph.

    Supports bulk deletion with confirmation prompts. Use --force to skip
    confirmation. Resolves ambiguous entity names by prompting user to choose.
    """
    # Resolve scope
    scope, project_root = resolve_scope(global_scope, project_scope)

    # Resolve all entity names to actual entities
    resolved_entities = []
    for entity_name in entities:
        result = _resolve_entity(entity_name, scope, project_root)

        # Handle not found
        if result is None:
            print_error(
                f"Entity '{entity_name}' not found.",
                suggestion="Try 'recall list' to see available entities."
            )
            raise typer.Exit(EXIT_ERROR)

        # Handle ambiguous matches
        if isinstance(result, list):
            console.print(f"\n[yellow]Multiple entities match '{entity_name}':[/yellow]\n")

            # Display numbered list
            for idx, match in enumerate(result, 1):
                console.print(f"  {idx}. [cyan]{match['name']}[/cyan] ({match['type']}) - ID: {match['id']}")

            # Prompt user to choose
            choice = typer.prompt(f"\nSelect entity [1-{len(result)}]", type=int)

            # Validate choice
            if choice < 1 or choice > len(result):
                print_error(f"Invalid selection: {choice}")
                raise typer.Exit(EXIT_ERROR)

            # Use selected entity
            resolved_entities.append(result[choice - 1])
        else:
            # Single match
            resolved_entities.append(result)

    # Display what will be deleted and confirm
    if not force:
        console.print("\n[yellow]The following entities will be deleted:[/yellow]\n")

        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Scope")

        for entity in resolved_entities:
            table.add_row(entity["name"], entity["type"], entity["scope"])

        console.print(table)
        console.print()

        # Confirm action
        if not confirm_action(f"Delete {len(resolved_entities)} entities?", force=force):
            console.print("[dim]Cancelled[/dim]")
            raise typer.Exit(EXIT_SUCCESS)

    # Delete entities with spinner
    with console.status(f"[cyan]Deleting {len(resolved_entities)} entities...", spinner="dots"):
        deleted_count = _delete_entities(resolved_entities, scope, project_root)

    # Output results
    entity_names = [e["name"] for e in resolved_entities]

    if format == "json":
        print_json({
            "deleted": deleted_count,
            "entities": entity_names
        })
    elif not quiet:
        if deleted_count == 1:
            print_success(f"Deleted 1 entity: {entity_names[0]}")
        else:
            print_success(f"Deleted {deleted_count} entities")

    raise typer.Exit(EXIT_SUCCESS)

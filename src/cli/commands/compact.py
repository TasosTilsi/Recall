"""Compact command for knowledge graph maintenance.

Merges and deduplicates graph content, rebuilding indexes for optimal performance.
This is a destructive operation that requires confirmation.
"""
import typer
from typing import Annotated, Optional
from pathlib import Path

from src.models import GraphScope
from src.cli.output import console, print_error, print_json, print_success
from src.cli.utils import resolve_scope, confirm_action, EXIT_ERROR
from src.graph import get_service, run_graph_operation


def _get_graph_stats(scope: GraphScope, project_root: Optional[Path] = None) -> dict:
    """Get current graph statistics.

    Args:
        scope: Graph scope to query
        project_root: Project root path (required for PROJECT scope)

    Returns:
        Dictionary with entity_count, relationship_count, duplicate_count, size_bytes
    """
    stats = run_graph_operation(get_service().get_stats(scope=scope, project_root=project_root))
    return stats


def _compact_graph(scope: GraphScope, project_root: Optional[Path] = None) -> dict:
    """Perform graph compaction operation.

    Args:
        scope: Graph scope to compact
        project_root: Project root path (required for PROJECT scope)

    Returns:
        Dictionary with merged_count, removed_count, new_entity_count, new_size_bytes
    """
    result = run_graph_operation(get_service().compact(scope=scope, project_root=project_root))
    return result


def compact_command(
    expire: Annotated[
        bool,
        typer.Option("--expire", help="Archive nodes older than retention_days (no dedup)")
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Skip confirmation prompt")
    ] = False,
    global_scope: Annotated[
        bool,
        typer.Option("--global", "-g", help="Use global scope")
    ] = False,
    project_scope: Annotated[
        bool,
        typer.Option("--project", "-p", help="Use project scope")
    ] = False,
    format: Annotated[
        Optional[str],
        typer.Option("--format", "-f", help="Output format: json")
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress non-essential output")
    ] = False,
):
    """Compact the knowledge graph by merging duplicate entities.

    This is a maintenance operation that:
    - Identifies and merges duplicate entities
    - Removes redundant relationships
    - Rebuilds indexes for optimal performance

    WARNING: This is a destructive operation that cannot be undone.
    Use --force to skip the confirmation prompt.

    Examples:
        graphiti compact
        graphiti compact --force
        graphiti compact --format json
        graphiti compact --expire
        graphiti compact --expire --force
    """
    try:
        # Resolve scope
        scope, project_root = resolve_scope(global_scope, project_scope)

        if expire:
            with console.status("[cyan]Scanning for stale nodes...", spinner="dots"):
                stale = run_graph_operation(
                    get_service().list_stale(scope, project_root)
                )
            if not stale:
                print_success("No stale nodes to archive.")
                raise typer.Exit(0)
            console.print(f"\n[cyan]{len(stale)} nodes are eligible for archiving.[/cyan]\n")
            confirmed = confirm_action(
                f"{len(stale)} nodes will be archived. Proceed?", force=force
            )
            if not confirmed:
                console.print("Cancelled")
                raise typer.Exit(0)
            archived_count = run_graph_operation(
                get_service().archive_nodes([n["uuid"] for n in stale], scope, project_root)
            )
            print_success(f"Archived {archived_count} nodes.")
            return

        # Load current graph statistics
        stats = _get_graph_stats(scope, project_root)

        # Display current state
        if not quiet and format != "json":
            console.print(
                f"\n[cyan]Knowledge graph:[/cyan] "
                f"{stats['entity_count']} entities, "
                f"{stats['relationship_count']} relationships, "
                f"~{stats['duplicate_count']} potential duplicates\n"
            )

        # Check if compaction needed
        if stats["duplicate_count"] == 0:
            print_success("No compaction needed. Graph is clean.")
            raise typer.Exit(0)

        # Confirmation for destructive operation
        confirmed = confirm_action(
            f"Compact the knowledge graph? This will merge {stats['duplicate_count']} duplicate entities.",
            force=force
        )

        if not confirmed:
            console.print("Cancelled")
            raise typer.Exit(0)

        # Perform compaction with spinner and progress updates
        with console.status("Compacting knowledge graph...") as status:
            status.update("Merging duplicates...")
            status.update("Rebuilding indexes...")
            status.update("Finalizing...")

            # Execute compaction
            result = _compact_graph(scope, project_root)

        # Output results
        if format == "json":
            print_json(result)
        else:
            # Success message with summary
            print_success(
                f"Compacted: {result['merged_count']} merged, "
                f"{result['removed_count']} removed. "
                f"{result['new_entity_count']} entities remaining."
            )

            if not quiet:
                # Show size reduction
                old_size_mb = stats['size_bytes'] / (1024 * 1024)
                new_size_mb = result['new_size_bytes'] / (1024 * 1024)
                reduction_pct = ((stats['size_bytes'] - result['new_size_bytes']) / stats['size_bytes']) * 100

                console.print(
                    f"\n[dim]Size: {old_size_mb:.1f}MB → {new_size_mb:.1f}MB "
                    f"({reduction_pct:.1f}% reduction)[/dim]"
                )

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Failed to compact graph: {str(e)}")
        raise typer.Exit(EXIT_ERROR)

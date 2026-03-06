"""Stale command for previewing nodes eligible for archiving.

Shows nodes older than the configured retention_days that would be
archived by 'graphiti compact --expire'.
"""
import structlog
import typer
from typing import Annotated, Optional

from src.cli.output import console, print_json, print_success, print_table
from src.cli.utils import resolve_scope
from src.graph import get_service, run_graph_operation

logger = structlog.get_logger(__name__)


def stale_command(
    global_scope: Annotated[
        bool,
        typer.Option("--global", "-g", help="Use global scope")
    ] = False,
    project_scope: Annotated[
        bool,
        typer.Option("--project", "-p", help="Use project scope")
    ] = False,
    all_results: Annotated[
        bool,
        typer.Option("--all", help="Show all stale nodes (default: 25)")
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Include UUID column in output")
    ] = False,
    format: Annotated[
        Optional[str],
        typer.Option("--format", "-f", help="Output format: json")
    ] = None,
):
    """Preview nodes eligible for archiving based on retention TTL.

    Shows nodes older than the configured retention_days that would be
    archived by 'graphiti compact --expire'.

    Examples:
        graphiti stale
        graphiti stale --all
        graphiti stale --verbose
        graphiti stale --format json
    """
    scope, project_root = resolve_scope(global_scope, project_scope)

    with console.status("[cyan]Scanning for stale nodes...", spinner="dots"):
        stale = run_graph_operation(
            get_service().list_stale(scope, project_root)
        )

    if not stale:
        print_success("No stale nodes found.")
        raise typer.Exit(0)

    cap = 25
    total = len(stale)
    display = stale if all_results else stale[:cap]

    if format == "json":
        print_json(display)
        return

    columns = ["name", "age_days", "score"]
    if verbose:
        columns = ["uuid"] + columns

    print_table(display, columns=columns)

    if not all_results and total > cap:
        console.print(
            f"\n[dim]Showing {cap} of {total} stale nodes. Run with --all to see all.[/dim]"
        )

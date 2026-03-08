"""CLI foundation for Graphiti knowledge graph operations.

This module provides the Typer app instance that all commands register with,
along with the entry point function for console_scripts.
"""
import sys
import typer
from typing import Optional
from src.cli.output import err_console, print_error


# Create main Typer app
app = typer.Typer(
    name="graphiti",
    help="Knowledge graph operations for global preferences and project memory",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-v", help="Show version and exit"
    ),
):
    """Main callback that handles version display and unknown command suggestions."""
    if version:
        # Import here to avoid circular dependency
        import importlib.metadata
        try:
            version_str = importlib.metadata.version("graphiti-knowledge-graph")
        except importlib.metadata.PackageNotFoundError:
            version_str = "0.1.0 (development)"
        typer.echo(f"graphiti version {version_str}")
        raise typer.Exit(0)

    # If command invoked but not found, suggest alternatives
    if ctx.invoked_subcommand is None and ctx.resilient_parsing is False:
        # This is just --help or no command, which is handled by no_args_is_help
        pass


def cli_entry():
    """Entry point for console_scripts.

    This function is registered in pyproject.toml as both 'graphiti' and 'gk'.
    """
    try:
        app()
    except typer.BadParameter as e:
        print_error(str(e))
        sys.exit(2)  # EXIT_BAD_ARGS
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)  # EXIT_ERROR


# Command imports
from src.cli.commands.add import add_command
from src.cli.commands.search import search_command
from src.cli.commands.stale import stale_command
from src.cli.commands.pin import pin_command, unpin_command
from src.cli.commands.summarize import summarize_command
from src.cli.commands.compact import compact_command
from src.cli.commands.list_cmd import list_command
from src.cli.commands.show import show_command
from src.cli.commands.delete import delete_command
from src.cli.commands.config import config_command
from src.cli.commands.health import health_command
from src.cli.commands.queue_cmd import queue_app
from src.cli.commands.capture import capture_command
from src.cli.commands.hooks import hooks_app
from src.cli.commands.index import index_command
from src.cli.commands.mcp import mcp_app
from src.cli.commands.ui import ui_command


# Register commands
app.command(name="add", help="Add content to the knowledge graph")(add_command)
app.command(name="pin", help="Protect a node from TTL archiving permanently")(pin_command)
app.command(name="search", help="Search the knowledge graph")(search_command)
app.command(name="stale", help="Preview nodes eligible for TTL archiving")(stale_command)

app.command(
    name="summarize",
    help="Generate a summary of the knowledge graph"
)(summarize_command)

app.command(
    name="compact",
    help="Compact the knowledge graph by merging duplicates"
)(compact_command)

app.command(
    name="list",
    help="List entities in the knowledge graph"
)(list_command)

app.command(
    name="show",
    help="Show detailed entity information"
)(show_command)

app.command(name="unpin", help="Remove TTL archiving protection from a node")(unpin_command)

app.command(
    name="delete",
    help="Delete entities from the knowledge graph"
)(delete_command)

app.command(
    name="config",
    help="View and modify configuration"
)(config_command)

app.command(
    name="health",
    help="Check system health and diagnostics"
)(health_command)

# Register queue command group
app.add_typer(queue_app, name="queue", help="Manage the background processing queue")

# Register capture command
app.command(name="capture", help="Capture knowledge from conversations")(capture_command)

# Register hooks command group
app.add_typer(hooks_app, name="hooks", help="Manage automatic capture hooks")

# Register index command
app.command(name="index", help="Index git history into the knowledge graph")(index_command)

# Register mcp command group
app.add_typer(mcp_app, name="mcp", help="MCP server for Claude Code integration")

# Register ui command
app.command(name="ui", help="Launch graph visualization UI")(ui_command)


# All 18 commands registered: add, pin, search, stale, summarize, compact, list, show, unpin, delete, config, health, queue (group), capture, hooks (group), index, mcp (group), ui

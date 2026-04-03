"""CLI foundation for recall knowledge graph operations.

This module provides the Typer app instance that all commands register with,
along with the entry point function for console_scripts.
"""
import sys
import logging
import structlog
import typer
from typing import Optional
from src.cli.output import err_console, print_error
from src.llm.provider import validate_provider_startup
from src.llm.config import load_config as _load_config_for_startup
from src.config.paths import migrate_dot_graphiti_to_recall

# Route all structlog output to stderr so JSON/plain CLI output is never polluted.
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING),
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)


# Create main Typer app
app = typer.Typer(
    name="recall",
    help="Local developer memory — search, manage, and browse your knowledge graph",
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
    # Migrate .graphiti/ -> .recall/ on every startup (no-op if already done)
    migrate_dot_graphiti_to_recall()

    if version:
        # Import here to avoid circular dependency
        import importlib.metadata
        try:
            version_str = importlib.metadata.version("graphiti-knowledge-graph")
        except importlib.metadata.PackageNotFoundError:
            version_str = "0.1.0 (development)"
        typer.echo(f"recall version {version_str}")
        raise typer.Exit(0)

    # Provider startup validation (Phase 13) — skip for help/version/health/config/init/index subcommands
    # Must run synchronously here, before any asyncio.run(graph_operation) call.
    _skip_validation_for = {"health", "config", "init", "index", None}
    if ctx.invoked_subcommand not in _skip_validation_for and not version:
        try:
            _startup_config = _load_config_for_startup()
            validate_provider_startup(_startup_config)
        except SystemExit:
            raise  # propagate sys.exit(1) from validate_provider_startup
        except Exception:
            pass  # non-fatal: provider validation errors should not block legacy path

    # If command invoked but not found, suggest alternatives
    if ctx.invoked_subcommand is None and ctx.resilient_parsing is False:
        # This is just --help or no command, which is handled by no_args_is_help
        pass


def cli_entry():
    """Entry point for console_scripts.

    This function is registered in pyproject.toml as both 'recall' and 'rc'.
    """
    try:
        app()
    except typer.BadParameter as e:
        print_error(str(e))
        sys.exit(2)  # EXIT_BAD_ARGS
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)  # EXIT_ERROR


# Command imports — 10 public commands + 1 hidden
from src.cli.commands.search import search_command
from src.cli.commands.pin import pin_command, unpin_command
from src.cli.commands.list_cmd import list_command
from src.cli.commands.delete import delete_command
from src.cli.commands.config import config_app as _config_sub_app
from src.cli.commands.health import health_command
from src.cli.commands.ui import ui_command
from src.cli.commands.init_cmd import init_command
from src.cli.commands.note_cmd import note_command
from src.cli.commands.index import index_command


# Register 10 public commands
app.command(name="init", help="Install hooks, index git history, and generate config")(init_command)
app.command(name="search", help="Search the knowledge graph")(search_command)
app.command(name="list", help="Browse entities; use flags for detail/stale/compact/queue")(list_command)
app.command(name="delete", help="Delete entities from the knowledge graph")(delete_command)
app.command(name="pin", help="Protect a node from TTL archiving permanently")(pin_command)
app.command(name="unpin", help="Remove TTL archiving protection from a node")(unpin_command)
app.command(name="health", help="Check system health and diagnostics")(health_command)
app.add_typer(_config_sub_app, name="config", help="View and modify configuration")
app.command(name="ui", help="Launch graph visualization UI")(ui_command)
app.command(name="note", help="Manually add a memory to the knowledge graph")(note_command)

# Register 1 hidden internal command
app.command(name="index", hidden=True, help="Index git history (hidden — use recall init for first-time setup)")(index_command)

# 10 public commands: init, search, list, delete, pin, unpin, health, config, ui, note | 1 hidden: index

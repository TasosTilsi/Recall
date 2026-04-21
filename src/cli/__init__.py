"""CLI entrypoint for recall-kg — six public commands: init, sync, search, health, config, ui."""
from __future__ import annotations

import logging
import sys

import structlog
import typer

# Route structlog output to stderr so it does not pollute stdout
structlog.configure(
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

app = typer.Typer(
    name="recall",
    help="Engineering knowledge graph — extracts decisions, patterns, and bugs from git history.",
    no_args_is_help=True,
    add_completion=False,
)

# --- Command imports (deferred to avoid heavy startup cost) ---
from src.cli.commands.init_cmd import init_command  # noqa: E402
from src.cli.commands.sync_cmd import sync_command  # noqa: E402
from src.cli.commands.search_cmd import app as search_app  # noqa: E402
from src.cli.commands.health import health_command  # noqa: E402
from src.cli.commands.config_cmd import app as config_app  # noqa: E402
from src.cli.commands.ui import ui_command  # noqa: E402
from src.cli.commands import mcp as mcp_commands  # noqa: E402

# --- Register commands in canonical order ---
app.command(name="init", help="Index git history from scratch (full reindex)")(init_command)
app.command(name="sync", help="Index new commits since last sync")(sync_command)
app.add_typer(search_app, name="search", help="Search the knowledge graph")
app.command(name="health", help="Check LLM provider and database status")(health_command)
app.add_typer(config_app, name="config", help="View and modify configuration")
app.command(name="ui", help="Launch the graph explorer UI")(ui_command)
app.add_typer(mcp_commands.app, name="mcp")


@app.callback()
def _callback(
    version: bool = typer.Option(None, "--version", "-V", is_eager=True, help="Show version and exit"),
) -> None:
    """recall — engineering knowledge graph from git history."""
    if version:
        from importlib.metadata import version as pkg_version, PackageNotFoundError
        try:
            v = pkg_version("recall-kg")
        except PackageNotFoundError:
            v = "dev"
        typer.echo(f"recall {v}")
        raise typer.Exit()


def cli_entry() -> None:
    """Console script entrypoint."""
    app()

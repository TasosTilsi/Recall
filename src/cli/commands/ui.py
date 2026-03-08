"""UI command — launches the Graphiti graph visualization server.

Starts a FastAPI server serving both the REST API and the pre-built Next.js
static UI. Runs in the foreground (blocks terminal). Ctrl+C to stop.
"""
import os
import socket
import subprocess
import uvicorn
import typer
import structlog
from pathlib import Path
from typing import Annotated

from src.cli.utils import resolve_scope, EXIT_ERROR, EXIT_SUCCESS
from src.cli.output import console, print_error

logger = structlog.get_logger(__name__)

# Repo root resolved at module load time (4 levels up from this file:
# src/cli/commands/ui.py → src/cli/commands/ → src/cli/ → src/ → repo root)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)
))))


def ui_command(
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="Visualize global scope graph")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", help="Visualize project scope graph")] = False,
    api_port: Annotated[int, typer.Option("--api-port", help="Override API server port (default from llm.toml [ui] api_port)")] = 0,
):
    """Launch the graph visualization UI.

    Opens a FastAPI server with the Graphiti knowledge graph visualization.
    Visit http://localhost:<api_port> in your browser.

    Press Ctrl+C to stop.
    """
    from src.llm.config import load_config

    config = load_config()
    port = api_port if api_port else config.ui_api_port

    # --- Pre-flight 1: Port availability ---
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
        except OSError:
            print_error(
                f"Port {port} is already in use. "
                f"Set [ui] api_port in ~/.graphiti/llm.toml to use a different port, "
                f"or stop the process using port {port}."
            )
            raise typer.Exit(EXIT_ERROR)

    # --- Pre-flight 2: Static files present ---
    static_dir = Path(_REPO_ROOT) / "ui/out"
    if not static_dir.exists():
        print_error(
            "Static UI files not found. Expected: ui/out/index.html\n"
            "The ui/out/ directory should be committed to git and present after installation.\n"
            "If running from source: cd ui && npm run build"
        )
        raise typer.Exit(EXIT_ERROR)

    # --- Resolve scope ---
    graph_scope, project_root = resolve_scope(global_scope, project_scope)
    scope_str = "global" if global_scope else "project"

    if global_scope:
        scope_label = "global"
    elif project_root:
        scope_label = f"project ({project_root.name})"
    else:
        scope_label = "project"

    # --- Launch banner ---
    console.print(f"\n[bold green]Graphiti UI[/bold green]")
    console.print(f"  [dim]API[/dim]   [cyan]http://localhost:{port}/api[/cyan]")
    console.print(f"  [dim]UI[/dim]    [cyan]http://localhost:{port}[/cyan]")
    console.print(f"  [dim]Scope[/dim] {scope_label}")
    console.print(f"  [dim]Press Ctrl+C to stop[/dim]\n")

    logger.info("ui_server_starting", port=port, scope=scope_str)

    # --- Start uvicorn ---
    from src.ui_server.app import create_app

    app = create_app(
        scope_label=scope_label,
        scope=scope_str,
        project_root=project_root,
        static_dir=static_dir,
    )

    try:
        # uvicorn.run() blocks until Ctrl+C (KeyboardInterrupt)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    except KeyboardInterrupt:
        console.print("\n[dim]Graphiti UI stopped.[/dim]")

    raise typer.Exit(EXIT_SUCCESS)

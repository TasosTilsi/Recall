"""Install command — register recall as a Claude plugin."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import structlog
import typer

from src.cli.output import console, print_error, print_success, print_warning

logger = structlog.get_logger(__name__)

_MCP_ENTRY = {
    "command": "recall",
    "args": ["mcp", "serve"],
}


def install_mcp_global(force: bool = False) -> dict:
    """Write mcpServers.recall entry to ~/.claude/settings.json.

    Returns:
        dict with key ``mcp_registered``: True if entry was written, False if skipped.
    """
    settings_path = Path.home() / ".claude" / "settings.json"

    # Read existing settings (tolerate missing or malformed file)
    config: dict = {}
    if settings_path.exists():
        try:
            config = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("settings.json unreadable — will overwrite", path=str(settings_path))
            config = {}

    if not isinstance(config, dict):
        config = {}

    # Ensure mcpServers key exists
    if "mcpServers" not in config or not isinstance(config["mcpServers"], dict):
        config["mcpServers"] = {}

    # Check if already registered
    if "recall" in config["mcpServers"] and not force:
        logger.debug("recall MCP already registered — skipping", force=force)
        return {"mcp_registered": False}

    # Write entry
    config["mcpServers"]["recall"] = _MCP_ENTRY
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(config, indent=2))
    logger.info("recall MCP registered", path=str(settings_path))
    return {"mcp_registered": True}


def ensure_recall_dir() -> bool:
    """Create ~/.recall/ directory if it does not exist.

    Returns:
        True if the directory was newly created, False if it already existed.
        Never touches config.toml regardless.
    """
    recall_dir = Path.home() / ".recall"
    if recall_dir.exists():
        return False
    recall_dir.mkdir(parents=True, exist_ok=True)
    logger.info("created ~/.recall/ directory")
    return True


def install_command(
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing MCP entry")] = False,
) -> None:
    """Install recall as a Claude plugin: register MCP server and create ~/.recall/ directory."""
    # Step 1: ensure ~/.recall/ exists
    try:
        created = ensure_recall_dir()
        if created:
            print_success("Created ~/.recall/ directory")
        else:
            console.print("[dim]~/.recall/ already exists — skipped[/dim]")
    except OSError as exc:
        print_error(f"Could not create ~/.recall/: {exc}")
        raise typer.Exit(1)

    # Step 2: register MCP server in ~/.claude/settings.json
    try:
        result = install_mcp_global(force=force)
        if result["mcp_registered"]:
            print_success("Registered recall MCP server in ~/.claude/settings.json")
        else:
            console.print("[dim]recall MCP server already registered — skipped (use --force to overwrite)[/dim]")
    except OSError as exc:
        print_error(f"Could not write ~/.claude/settings.json: {exc}")
        raise typer.Exit(1)

    # Step 3: final summary
    console.print(
        "\n[bold green]recall plugin installed.[/bold green] "
        "Start Claude and type [bold]/recall-setup[/bold] to configure."
    )

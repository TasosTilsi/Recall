"""Config command — inspect and modify ~/.recall/config.toml."""
from __future__ import annotations

import tomllib
from pathlib import Path

import structlog
import tomli_w
import typer

logger = structlog.get_logger(__name__)

app = typer.Typer(name="config", help="Inspect and modify recall configuration")

CONFIG_PATH = Path.home() / ".recall" / "config.toml"


@app.command()
def show() -> None:
    """Print full config file contents."""
    try:
        if not CONFIG_PATH.exists():
            typer.echo(f"Config file not found: {CONFIG_PATH}")
            raise typer.Exit(code=1)
        typer.echo(CONFIG_PATH.read_text())
    except typer.Exit:
        raise
    except Exception as e:
        logger.error("config show failed", error=str(e))
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command()
def get(
    key: str = typer.Argument(..., help="Dotted key, e.g. llm.provider"),
) -> None:
    """Get a config value by dotted key."""
    try:
        if not CONFIG_PATH.exists():
            typer.echo(f"Config file not found: {CONFIG_PATH}")
            raise typer.Exit(code=1)

        with open(CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)

        segments = key.split(".")
        current = data
        for seg in segments:
            if not isinstance(current, dict) or seg not in current:
                typer.echo(f"Key not found: {key}")
                raise typer.Exit(code=1)
            current = current[seg]
        typer.echo(current)
    except typer.Exit:
        raise
    except Exception as e:
        logger.error("config get failed", key=key, error=str(e))
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@app.command(name="set")
def set_key(
    key: str = typer.Argument(..., help="Dotted key, e.g. llm.provider"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a config value by dotted key."""
    try:
        # Load existing config, or start fresh if file missing
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "rb") as f:
                data: dict = tomllib.load(f)
        else:
            data = {}
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Traverse/create nested dicts
        segments = key.split(".")
        current = data
        for seg in segments[:-1]:
            if seg not in current or not isinstance(current[seg], dict):
                current[seg] = {}
            current = current[seg]

        # Set leaf value
        current[segments[-1]] = value

        # Write back
        CONFIG_PATH.write_bytes(tomli_w.dumps(data).encode())
        typer.echo(f"Set {key} = {value}")
    except typer.Exit:
        raise
    except Exception as e:
        logger.error("config set failed", key=key, value=value, error=str(e))
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

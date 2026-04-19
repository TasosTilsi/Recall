"""Sync command — incremental git history indexer."""
from __future__ import annotations

from pathlib import Path

import typer

from src.cli.output import console, print_error
from src.cli.utils import EXIT_ERROR, EXIT_SUCCESS


def _find_git_root() -> Path | None:
    """Walk up from cwd looking for a .git directory. Returns None if not found."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _print_index_result(result: dict) -> None:
    """Print indexing result in a consistent format."""
    commits = result.get("commits_processed", 0)
    entities = result.get("entities_inserted", 0)
    console.print(f"[green]Done.[/green] Processed {commits} commit(s), inserted {entities} entity/entities.")


def sync_command() -> None:
    """Index new git commits since last sync.

    Incremental — only processes commits not yet indexed.
    Automatically runs a full init if no database exists yet.

    Examples:
        recall sync
    """
    try:
        root = _find_git_root()
        if root is None:
            print_error(
                "Not in a git repository. Cannot sync git history.",
                suggestion="Navigate to a git repository and try again",
            )
            raise typer.Exit(EXIT_ERROR)

        from src.config import load_config
        from src.indexer import run_sync

        config = load_config()
        db_path = root / config.db.path

        if not db_path.exists():
            console.print("[dim]No database found — running full init...[/dim]")

        with console.status("Syncing new commits..."):
            result = run_sync(root, config)

        _print_index_result(result)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Sync failed: {str(e)}")
        raise typer.Exit(EXIT_ERROR)

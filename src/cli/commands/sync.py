"""Sync command for Graphiti CLI.

Incrementally indexes new git commits since the last sync.
This is an alias for `graphiti index` with no-args incremental semantics.
"""
import typer
from pathlib import Path

from src.cli.output import console, print_success, print_error
from src.cli.utils import resolve_scope, EXIT_SUCCESS, EXIT_ERROR
from src.indexer import GitIndexer


def sync_command() -> None:
    """Incrementally index new git commits since last sync."""
    try:
        scope, root = resolve_scope()

        if root is None:
            print_error(
                "Not in a git repository. Cannot sync git history.",
                suggestion="Navigate to a git repository and try again"
            )
            raise typer.Exit(EXIT_ERROR)

        with console.status("Syncing git history..."):
            stats = GitIndexer(project_root=root).run(full=False)

        # Handle cooldown case
        if stats.get("skipped_reason") == "cooldown":
            console.print(
                "Index is up to date (ran within the last 5 minutes)."
            )
            raise typer.Exit(EXIT_SUCCESS)

        commits_processed = stats.get("commits_processed", 0)
        commits_skipped = stats.get("commits_skipped", 0)
        elapsed_seconds = stats.get("elapsed_seconds", 0.0)

        print_success(
            f"Synced {commits_processed} commits, skipped {commits_skipped}"
        )

        console.print(
            f"[dim]Sync completed in {elapsed_seconds:.1f}s[/dim]"
        )

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Sync failed: {str(e)}")
        raise typer.Exit(EXIT_ERROR)

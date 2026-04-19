"""Init command — full git history reindex."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from src.cli.output import console, print_error, print_warning
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


def init_command(
    force: Annotated[bool, typer.Option("--force", help="Wipe existing DB and re-index from scratch")] = False,
) -> None:
    """Index git history from scratch (full reindex).

    Wipes the existing database and re-processes all git commits.
    Use 'recall sync' to only process new commits.

    Examples:
        recall init
        recall init --force
    """
    try:
        root = _find_git_root()
        if root is None:
            print_error(
                "Not in a git repository. Cannot index git history.",
                suggestion="Navigate to a git repository and try again",
            )
            raise typer.Exit(EXIT_ERROR)

        from src.config import load_config
        from src.indexer import run_init

        config = load_config()
        db_path = root / config.db.path

        if db_path.exists() and not force:
            print_warning(
                "Database already exists. Use --force to wipe and re-index, "
                "or 'recall sync' for incremental indexing."
            )
            raise typer.Exit(EXIT_SUCCESS)

        with console.status("Indexing git history (full reindex)..."):
            result = run_init(root, config)

        _print_index_result(result)

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Init failed: {str(e)}")
        raise typer.Exit(EXIT_ERROR)

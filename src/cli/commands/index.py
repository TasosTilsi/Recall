"""Index command for recall CLI.

Indexes git commit history into the knowledge graph.
Incremental by default — only processes commits not yet indexed.
"""
import typer
from typing import Annotated, Optional
from pathlib import Path

from src.cli.output import console, print_success, print_error, print_warning
from src.cli.utils import resolve_scope, EXIT_SUCCESS, EXIT_ERROR


def index_command(
    force: Annotated[bool, typer.Option("--force", help="Wipe all git-indexed knowledge and re-index entire history from scratch")] = False,
    since: Annotated[Optional[str], typer.Option("--since", help="Index commits since date (YYYY-MM-DD) or commit SHA")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Show per-commit progress")] = False,
) -> None:
    """Index git history into the knowledge graph.

    Incremental by default — only processes commits not yet indexed.
    Use --force to wipe and re-index entire history.

    Examples:
        recall index                         # Incremental index (new commits only)
        recall index --force                 # Wipe and re-index everything
        recall index --since 2024-01-01      # Index commits since date
        recall index --since abc1234         # Index commits since a SHA
        recall index --verbose               # Show per-commit progress
    """
    try:
        # Resolve scope — index command requires a git project root
        scope, root = resolve_scope()

        if root is None:
            print_error(
                "Not in a git repository. Cannot index git history.",
                suggestion="Navigate to a git repository and try again"
            )
            raise typer.Exit(EXIT_ERROR)

        # Validate the git repo is accessible
        try:
            import git as gitpython
            gitpython.Repo(str(root), search_parent_directories=True)
        except gitpython.exc.GitCommandNotFound:
            print_error(
                "Git executable not found. Cannot index git history.",
                suggestion="Install git and ensure it is on your PATH"
            )
            raise typer.Exit(EXIT_ERROR)
        except gitpython.exc.InvalidGitRepositoryError:
            print_error(
                "Not in a git repository. Cannot index git history.",
                suggestion="Navigate to a git repository and try again"
            )
            raise typer.Exit(EXIT_ERROR)

        # Warn before full re-index (destructive)
        if force:
            print_warning(
                "Wiping all git-indexed knowledge. This will re-process the entire git history."
            )

        # Import and instantiate GitIndexer
        from src.indexer import GitIndexer
        indexer = GitIndexer(project_root=root)

        # Full re-index: reset state and episodes first
        if force:
            indexer.reset_full()

        # Build optional status callback for verbose mode
        status_callback = None
        if verbose:
            def status_callback(msg: str) -> None:
                console.print(f"[dim]{msg}[/dim]")

        # Run indexing with progress spinner
        with console.status("Indexing git history...") as status:
            result = indexer.run(since=since, full=False, verbose=verbose, status_callback=status_callback)

        # Handle cooldown case
        if result.get("skipped_reason") == "cooldown":
            console.print(
                "Index is up to date (ran within the last 5 minutes). Use --force to force re-index."
            )
            raise typer.Exit(EXIT_SUCCESS)

        # Handle other early-exit cases
        if result.get("skipped_reason") == "not_a_git_repo":
            print_error("Not a git repository. Cannot index git history.")
            raise typer.Exit(EXIT_ERROR)

        if result.get("skipped_reason") == "graphiti_init_failed":
            print_error(
                "Failed to initialize knowledge graph. Cannot index git history.",
                suggestion="Run 'recall health' to diagnose configuration issues"
            )
            raise typer.Exit(EXIT_ERROR)

        # Success output
        commits_processed = result.get("commits_processed", 0)
        commits_skipped = result.get("commits_skipped", 0)
        elapsed_seconds = result.get("elapsed_seconds", 0.0)
        entity_names = result.get("entity_names_sample", [])

        if commits_processed == 0:
            console.print("[dim]Nothing new to index — all commits already processed.[/dim]")
            console.print("[dim]Use --force to re-index everything.[/dim]")
            raise typer.Exit(EXIT_SUCCESS)

        print_success(
            f"Indexed {commits_processed} commit{'s' if commits_processed != 1 else ''}"
            + (f", skipped {commits_skipped}" if commits_skipped else "")
            + f" in {elapsed_seconds:.1f}s"
        )

        if entity_names:
            console.print()
            console.print(f"[dim]Knowledge extracted ({len(entity_names)} entities sampled):[/dim]")
            for name in entity_names[:12]:
                console.print(f"  [cyan]·[/cyan] {name}")
            if len(entity_names) > 12:
                console.print(f"  [dim]... and {len(entity_names) - 12} more[/dim]")
        else:
            console.print("[dim]No new entities extracted from this batch.[/dim]")

        console.print()
        console.print("[dim]Run [bold]recall search <query>[/bold] to explore indexed knowledge.[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Indexing failed: {str(e)}")
        raise typer.Exit(EXIT_ERROR)

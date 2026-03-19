"""Hooks command group for Graphiti CLI.

Manages automatic capture hooks for git and Claude Code.
Provides install, uninstall, and status subcommands.
"""
import typer
from typing import Annotated, Optional
from pathlib import Path
from rich.table import Table

from src.cli.output import console, print_success, print_json, print_error
from src.cli.utils import resolve_scope, EXIT_SUCCESS, EXIT_ERROR
from src.hooks import (
    install_hooks,
    uninstall_hooks,
    get_hook_status,
    set_hooks_enabled,
    get_hooks_enabled,
)
from src.hooks.installer import (
    install_precommit_hook,
    uninstall_precommit_hook,
    is_precommit_hook_installed,
    install_postcheckout_hook,
    install_postrewrite_hook,
    upgrade_postmerge_hook,
    uninstall_postcheckout_hook,
    uninstall_postrewrite_hook,
    is_postcheckout_hook_installed,
    is_postrewrite_hook_installed,
    install_global_hooks,
    is_global_hooks_installed,
)

# Create hooks command group
hooks_app = typer.Typer(
    name="hooks",
    help="Manage automatic capture hooks",
    no_args_is_help=True
)


@hooks_app.command(name="install")
def install_command(
    git_only: Annotated[bool, typer.Option("--git-only", help="Install only git hooks")] = False,
    claude_only: Annotated[bool, typer.Option("--claude-only", help="Install only Claude Code hooks")] = False,
    force: Annotated[bool, typer.Option("--force", help="Force reinstall even if already installed")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
):
    """Install automatic capture hooks.

    By default, installs both git post-commit and Claude Code Stop hooks.
    Use --git-only or --claude-only to install specific hook types.

    The git hook captures commit information automatically after each commit.
    The Claude Code hook captures conversation knowledge when sessions end.

    Examples:
        graphiti hooks install              # Install both hook types
        graphiti hooks install --git-only   # Install only git hook
        graphiti hooks install --force      # Reinstall even if present
    """
    try:
        # Resolve project root (hooks require project context)
        scope, root = resolve_scope()

        if root is None:
            print_error(
                "Not in a git repository. Hooks require a project context.",
                suggestion="Navigate to a git repository and try again"
            )
            raise typer.Exit(EXIT_ERROR)

        # Determine which hooks to install
        install_git = not claude_only
        install_claude = not git_only

        # Derive .git directory for new hook installer functions
        git_dir = root / ".git"

        # Install hooks
        with console.status("Installing hooks..."):
            result = install_hooks(
                root,
                install_git=install_git,
                install_claude=install_claude
            )

            # Upgrade post-merge hook if it's the old Phase 7 journal-based one
            upgrade_postmerge_hook(git_dir)

            # Install pre-commit hook (secret scanning + size checks)
            precommit_installed = install_precommit_hook(root, force=force)

            # Install indexer trigger hooks (post-checkout and post-rewrite)
            postcheckout_installed = install_postcheckout_hook(git_dir)
            postrewrite_installed = install_postrewrite_hook(git_dir)

        # Install global Claude Code memory hooks (~/.claude/settings.json)
        global_hooks_installed = False
        with console.status("Installing global Claude Code memory hooks..."):
            global_hooks_installed = install_global_hooks()

        # Output result
        if format == "json":
            result["precommit_installed"] = precommit_installed
            result["postcheckout_installed"] = postcheckout_installed
            result["postrewrite_installed"] = postrewrite_installed
            print_json(result)
        else:
            # Display what was installed
            installed = []
            skipped = []

            if result.get("git_installed"):
                installed.append("post-commit")
            elif install_git:
                skipped.append("post-commit (already installed)")

            if result.get("claude_installed"):
                installed.append("Claude Code Stop hook")
            elif install_claude:
                skipped.append("Claude hook (already installed)")

            if precommit_installed:
                installed.append("pre-commit")
            else:
                skipped.append("pre-commit (already installed)")

            if postcheckout_installed:
                installed.append("post-checkout")
            else:
                skipped.append("post-checkout (already installed)")

            if postrewrite_installed:
                installed.append("post-rewrite")
            else:
                skipped.append("post-rewrite (already installed)")

            if global_hooks_installed:
                installed.append("Claude Code global memory hooks (SessionStart, UserPromptSubmit, PostToolUse, PreCompact, Stop)")
            elif is_global_hooks_installed():
                skipped.append("Claude Code global memory hooks (already installed)")
            else:
                console.print("[yellow]Warning:[/yellow] Failed to install global Claude Code hooks — check ~/.claude/ permissions")

            # Success message
            if installed:
                hooks_str = ", ".join(installed)
                print_success(f"Installed hooks: {hooks_str}")
                console.print(
                    "[dim]All 5 hooks deployed: pre-commit, post-commit, post-merge, post-checkout, post-rewrite[/dim]"
                )

            if skipped:
                console.print(f"[dim]Skipped: {', '.join(skipped)}[/dim]")
                console.print("[dim]Use --force to reinstall[/dim]")

            # Show helpful next steps
            if installed:
                console.print("\n[cyan]Automatic capture is now enabled![/cyan]")
                console.print("[dim]Run 'graphiti hooks status' to verify installation[/dim]")

    except Exception as e:
        print_error(f"Failed to install hooks: {str(e)}")
        raise typer.Exit(EXIT_ERROR)


@hooks_app.command(name="uninstall")
def uninstall_command(
    git_only: Annotated[bool, typer.Option("--git-only", help="Remove only git hooks")] = False,
    claude_only: Annotated[bool, typer.Option("--claude-only", help="Remove only Claude Code hooks")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
):
    """Uninstall automatic capture hooks.

    Removes hook scripts from .git/hooks/ and .claude/settings.json.
    This does NOT disable hooks via config - it physically removes them.

    Use 'graphiti config set hooks.enabled false' to temporarily disable
    hooks without removing the hook files.

    Examples:
        graphiti hooks uninstall              # Remove both hook types
        graphiti hooks uninstall --git-only   # Remove only git hook
    """
    try:
        # Resolve project root
        scope, root = resolve_scope()

        if root is None:
            print_error(
                "Not in a git repository. Cannot uninstall hooks.",
                suggestion="Navigate to a git repository and try again"
            )
            raise typer.Exit(EXIT_ERROR)

        # Determine which hooks to remove
        remove_git = not claude_only
        remove_claude = not git_only

        # Derive .git directory for new hook installer functions
        git_dir = root / ".git"

        # Uninstall hooks
        with console.status("Removing hooks..."):
            result = uninstall_hooks(
                root,
                remove_git=remove_git,
                remove_claude=remove_claude
            )

            # Also remove pre-commit, post-checkout, and post-rewrite hooks
            precommit_removed = uninstall_precommit_hook(root)
            postcheckout_removed = uninstall_postcheckout_hook(git_dir)
            postrewrite_removed = uninstall_postrewrite_hook(git_dir)

        # Output result
        if format == "json":
            result["precommit_removed"] = precommit_removed
            result["postcheckout_removed"] = postcheckout_removed
            result["postrewrite_removed"] = postrewrite_removed
            print_json(result)
        else:
            # Display what was removed
            removed = []

            if result.get("git_removed"):
                removed.append("post-commit hook")
            if result.get("claude_removed"):
                removed.append("Claude Code Stop hook")
            if precommit_removed:
                removed.append("pre-commit hook")
            if postcheckout_removed:
                removed.append("post-checkout hook")
            if postrewrite_removed:
                removed.append("post-rewrite hook")

            if removed:
                hooks_str = ", ".join(removed)
                print_success(f"Removed {hooks_str}")
            else:
                console.print("[dim]No hooks were installed[/dim]")

    except Exception as e:
        print_error(f"Failed to uninstall hooks: {str(e)}")
        raise typer.Exit(EXIT_ERROR)


@hooks_app.command(name="status")
def status_command(
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
):
    """Show hook installation and enablement status.

    Displays whether hooks are enabled via config and whether hook files
    are installed for git and Claude Code.

    Examples:
        graphiti hooks status              # Show status table
        graphiti hooks status --format json  # JSON output
    """
    try:
        # Resolve project root
        scope, root = resolve_scope()

        if root is None:
            print_error(
                "Not in a git repository. Cannot check hook status.",
                suggestion="Navigate to a git repository and try again"
            )
            raise typer.Exit(EXIT_ERROR)

        # Get hook status
        status = get_hook_status(root)

        # Derive .git directory for new hook status checks
        git_dir = root / ".git"
        precommit_installed = is_precommit_hook_installed(root)
        postcheckout_installed = is_postcheckout_hook_installed(git_dir)
        postrewrite_installed = is_postrewrite_hook_installed(git_dir)
        global_hooks = is_global_hooks_installed()

        # JSON output mode
        if format == "json":
            output = {
                "git_installed": status.get("git_hook_installed", False),
                "claude_installed": status.get("claude_hook_installed", False),
                "precommit_installed": precommit_installed,
                "postcheckout_installed": postcheckout_installed,
                "postrewrite_installed": postrewrite_installed,
            }
            print_json(output)
            raise typer.Exit(EXIT_SUCCESS)

        # Rich table output
        table = Table(
            title="Hook Status",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Hook Type", style="white")
        table.add_column("Installed", style="white")

        # Helper for checkmark/X display
        def status_icon(installed: bool) -> str:
            return "[green]✓[/green]" if installed else "[red]✗[/red]"

        # Add rows for each hook type
        table.add_row(
            "Git pre-commit",
            status_icon(precommit_installed)
        )
        table.add_row(
            "Git post-commit",
            status_icon(status.get("git_hook_installed", False))
        )
        table.add_row(
            "Claude Code Stop",
            status_icon(status.get("claude_hook_installed", False))
        )
        table.add_row(
            "Git post-checkout",
            status_icon(postcheckout_installed)
        )
        table.add_row(
            "Git post-rewrite",
            status_icon(postrewrite_installed)
        )
        table.add_row(
            "Claude Code global (memory hooks)",
            status_icon(global_hooks)
        )

        console.print(table)

        # Show helpful hints based on status
        if not status.get("git_hook_installed") and not status.get("claude_hook_installed"):
            console.print("\n[yellow]⚠[/yellow] No hooks are installed")
            console.print("[dim]Run 'graphiti hooks install' to install hooks[/dim]")

    except Exception as e:
        print_error(f"Failed to get hook status: {str(e)}")
        raise typer.Exit(EXIT_ERROR)

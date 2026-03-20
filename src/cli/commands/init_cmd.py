"""Init command for recall CLI.

Idempotent one-command setup: install hooks, run full git history index,
write ~/.graphiti/llm.toml template if missing, register MCP server.

Each step warns on failure and continues — safe to re-run.
"""
import typer
from typing import Annotated

from src.cli.output import console, print_success, print_warning, print_error
from src.cli.utils import resolve_scope, EXIT_SUCCESS


def init_command(
    skip_index: Annotated[bool, typer.Option("--skip-index", help="Skip git history indexing")] = False,
    force: Annotated[bool, typer.Option("--force", help="Force reinstall hooks and overwrite config")] = False,
) -> None:
    """Set up recall: install hooks, index git history, configure LLM, register MCP.

    Idempotent — safe to re-run. Each step warns and continues on failure.

    Steps performed:
    1. Install 4 Claude Code hook scripts to ~/.claude/settings.json
    2. Run full git history index (bootstrap the graph from git log)
    3. Write ~/.recall/config.toml template if missing (static template — edit to customize)
    4. Register MCP server in Claude Desktop config (~/.claude.json)

    Examples:
        recall init                    # Full setup
        recall init --skip-index       # Skip git history index (faster)
        recall init --force            # Force reinstall hooks and overwrite config
    """
    console.print("[bold cyan]Setting up recall...[/bold cyan]\n")

    # Step 1: Install global Claude Code hooks
    console.print("[cyan]Step 1/4:[/cyan] Installing Claude Code hooks...")
    try:
        from src.hooks.installer import install_global_hooks, is_global_hooks_installed
        if not force and is_global_hooks_installed():
            console.print("[dim]  Hooks already installed — skipping (use --force to reinstall)[/dim]")
        else:
            success = install_global_hooks()
            if success:
                print_success("  Claude Code hooks installed (~/.claude/settings.json)")
            else:
                print_warning("  Failed to install hooks — check ~/.claude/ permissions")
    except Exception as e:
        print_warning(f"  Hook installation failed: {e}")

    # Step 2: Full git history index
    if skip_index:
        console.print("[dim]Step 2/4: Skipping git history index (--skip-index)[/dim]")
    else:
        console.print("[cyan]Step 2/4:[/cyan] Indexing git history...")
        try:
            scope, root = resolve_scope()
            if root is None:
                console.print("[dim]  No git repo found — skipping git history index[/dim]")
            else:
                from src.indexer import GitIndexer
                indexer = GitIndexer(project_root=root)
                indexer.reset_full()
                with console.status("  Indexing commits..."):
                    result = indexer.run(full=False)
                commits = result.get("commits_processed", 0)
                print_success(f"  Indexed {commits} commits from git history")
        except Exception as e:
            print_warning(f"  Git indexing failed: {e}")

    # Step 3: Write config template if missing
    console.print("[cyan]Step 3/4:[/cyan] Checking LLM configuration...")
    try:
        from pathlib import Path
        config_path = Path.home() / ".recall" / "config.toml"
        if config_path.exists() and not force:
            console.print(f"[dim]  Config already exists at {config_path} — skipping[/dim]")
        else:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            template = '''[cloud]
models = []
# endpoint = "https://api.example.com/v1"
# api_key  = "sk-..."

[local]
models = ["gemma2:9b"]
endpoint = "http://localhost:11434"
auto_start = false

[embeddings]
models = ["nomic-embed-text"]

[retry]
max_attempts = 3
delay_seconds = 2

[timeout]
request_seconds = 180

[capture]
mode = "decisions-only"

# Backend configuration — uncomment to switch from the embedded default.
# Absence of this section = LadybugDB (embedded, no container required).
# [backend]
# type = "ladybug"  # default — no container required
# type = "neo4j"
# uri  = "bolt://neo4j:changeme@localhost:7687"
'''
            config_path.write_text(template)
            print_success(f"  Config template written to {config_path} (edit to customize)")
    except Exception as e:
        print_warning(f"  Config generation failed: {e}")

    # Step 4: Register MCP server
    console.print("[cyan]Step 4/4:[/cyan] Registering MCP server...")
    try:
        from src.mcp_server.install import install_mcp_server
        results = install_mcp_server(force=force)
        if results.get("claude_json_updated"):
            print_success("  MCP server registered in ~/.claude.json")
        else:
            console.print("[dim]  MCP server already registered — skipping[/dim]")
    except Exception as e:
        print_warning(f"  MCP registration failed: {e}")

    console.print("\n[bold green]Setup complete.[/bold green]")
    console.print("[dim]Restart Claude Code to activate hooks and MCP server.[/dim]")
    raise typer.Exit(EXIT_SUCCESS)

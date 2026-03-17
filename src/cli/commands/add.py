"""Add command for Graphiti CLI.

Adds content to the knowledge graph with automatic scope detection,
tagging, and source provenance tracking.
"""
import typer
from typing import Annotated, Optional
from datetime import datetime
from pathlib import Path

from src.cli.input import read_content
from src.cli.output import console, print_success, print_json, print_error
from src.cli.utils import resolve_scope, EXIT_SUCCESS, EXIT_ERROR
from src.models import GraphScope
from src.config.paths import get_project_db_path
from src.graph import get_service, run_graph_operation
from src.llm import LLMUnavailableError
from src.hooks import install_hooks
import structlog


def _detect_source() -> str:
    """Auto-detect source provenance.

    Returns:
        Source string (git remote URL if in repo, else "manual")
    """
    try:
        import subprocess
        # Try to get git remote URL
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Default to manual if not in git repo or git not available
    return "manual"


def _ensure_project_directory(project_root: Path) -> None:
    """Ensure .graphiti/ directory exists for project scope.

    Args:
        project_root: Root directory of the project
    """
    graphiti_dir = project_root / ".graphiti"
    if not graphiti_dir.exists():
        graphiti_dir.mkdir(parents=True, exist_ok=True)


def _auto_install_hooks(project_root: Path) -> None:
    """Auto-install hooks on first graphiti add in a project.

    Installs the Claude Code Stop hook on first use. The git post-commit hook
    was removed in v2.0 (Phase 15 prep: replaced by incremental graphiti sync
    on SessionStart).

    This function:
    1. Checks if .git directory exists (only install in git repos)
    2. Installs Claude Code hook (install_hooks handles idempotency)
    3. Logs the auto-installation (transparent to user)
    4. Best-effort: Never fails the add operation

    Args:
        project_root: Root directory of the project
    """
    logger = structlog.get_logger()

    try:
        # Check if .git directory exists (only install in git repos)
        git_dir = project_root / ".git"
        if not git_dir.exists():
            return

        # Install Claude Code hook (install_git=True is a no-op in v2.0)
        result = install_hooks(
            project_root,
            install_git=False,
            install_claude=True
        )

        if result.get("claude_hook"):
            logger.info(
                "auto_install_hooks",
                action="hooks_installed",
                claude=result.get("claude_hook", False)
            )

    except Exception as e:
        # Best-effort: Log warning but do NOT fail the add operation
        logger.warning(
            "auto_install_hooks",
            action="install_failed",
            error=str(e),
            message="Hook installation failed, continuing with add operation"
        )


def _add_entity(
    content: str,
    scope: GraphScope,
    project_root: Optional[Path],
    tags: Optional[list[str]],
    source: str,
) -> dict:
    """Add entity to the knowledge graph via GraphService.

    Calls GraphService.add() which invokes Graphiti.add_episode() to write
    real content to the Kuzu graph database. Content is sanitized for secrets
    before storage, and entities/relationships are extracted via LLM.

    Args:
        content: Content to add to knowledge graph
        scope: Graph scope (GLOBAL or PROJECT)
        project_root: Project root path (if PROJECT scope)
        tags: Optional list of tags for categorization
        source: Source provenance

    Returns:
        Dictionary with entity metadata (name, type, scope, created_at, tags,
        source, content_length, nodes_created, edges_created)

    Raises:
        LLMUnavailableError: If LLM is unavailable for entity extraction
    """
    try:
        # Get service and call add operation
        service = get_service()
        result = run_graph_operation(
            service.add(
                content=content,
                scope=scope,
                project_root=project_root,
                tags=tags,
                source=source,
            )
        )
        return result
    except LLMUnavailableError as e:
        # Re-raise with user-friendly message
        print_error(
            f"Cannot add content: LLM service unavailable. {str(e)}\n"
            "Please check your Ollama configuration with 'graphiti health'."
        )
        raise


def add_command(
    content: Annotated[Optional[str], typer.Argument(help="Content to add to knowledge graph")] = None,
    tag: Annotated[Optional[list[str]], typer.Option("--tag", "-t", help="Tags for categorization (can repeat)")] = None,
    source: Annotated[Optional[str], typer.Option("--source", "-s", help="Source provenance (auto-detected if omitted)")] = None,
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="Use global scope")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", help="Use project scope")] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", help="Output format: json")] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress success messages")] = False,
):
    """Add content to the knowledge graph.

    Content can be provided as a positional argument or piped via stdin.

    Examples:
        graphiti add "Meeting notes from 2026-02-11"
        echo "Important concept" | graphiti add
        graphiti add "Feature idea" --tag roadmap --tag feature
        graphiti add "Global preference" --global
    """
    try:
        # 1. Resolve content from positional arg or stdin
        resolved_content = read_content(content)

        # 2. Resolve scope
        scope, root = resolve_scope(global_scope, project_scope)

        # 3. Auto-detect source if not provided
        if source is None:
            source = _detect_source()

        # 4. Auto-init .graphiti/ directory for project scope
        if scope == GraphScope.PROJECT and root:
            _ensure_project_directory(root)

        # 4.5 Auto-install hooks on first add (best-effort)
        if root:
            _auto_install_hooks(root)

        # 5. Add entity with spinner
        with console.status("Adding to knowledge graph..."):
            result = _add_entity(
                content=resolved_content,
                scope=scope,
                project_root=root,
                tags=tag,
                source=source,
            )

        # 6. Output result
        if format == "json":
            print_json(result)
        elif not quiet:
            entity_name = result.get("name", "entity")
            tags_str = f" (tags: {', '.join(result['tags'])})" if result.get("tags") else ""
            print_success(f"Added {entity_name} to {scope.value} scope{tags_str}")

    except typer.BadParameter:
        # Re-raise parameter errors (already formatted by typer)
        raise
    except Exception as e:
        print_error(f"Failed to add content: {str(e)}")
        raise typer.Exit(EXIT_ERROR)


# Note: Tag handling is implemented via --tag flag
# Future enhancement: LLM-based auto-categorization when tags not provided
# This would analyze content and suggest/apply relevant tags automatically

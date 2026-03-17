"""Health check command for system diagnostics."""
import sys
from pathlib import Path
from typing import Annotated, Optional

import httpx
import typer
from rich.table import Table

from src.cli.output import console, print_json
from src.cli.utils import EXIT_ERROR, EXIT_SUCCESS
from src.config.paths import GLOBAL_DB_DIR, get_project_db_path
from src.llm import get_client, load_config
from src.storage import GraphSelector


def _check_ollama_cloud() -> dict:
    """Check cloud Ollama connectivity.

    Returns:
        Dict with name, status, detail keys
    """
    config = load_config()

    # Check if API key is configured
    if not config.cloud_api_key:
        return {
            "name": "Cloud Ollama",
            "status": "warning",
            "detail": "No API key configured. Set OLLAMA_API_KEY environment variable.",
        }

    # Try to ping cloud endpoint
    try:
        headers = {"Authorization": f"Bearer {config.cloud_api_key}"}
        response = httpx.get(
            f"{config.cloud_endpoint}/api/tags",
            headers=headers,
            timeout=5.0
        )
        if response.status_code == 200:
            return {
                "name": "Cloud Ollama",
                "status": "ok",
                "detail": f"Connected to {config.cloud_endpoint}",
            }
        else:
            return {
                "name": "Cloud Ollama",
                "status": "error",
                "detail": f"HTTP {response.status_code}. Check OLLAMA_API_KEY.",
            }
    except Exception as e:
        return {
            "name": "Cloud Ollama",
            "status": "error",
            "detail": f"Connection failed: {str(e)}. Check OLLAMA_API_KEY.",
        }


def _check_ollama_local() -> dict:
    """Check local Ollama connectivity.

    Returns:
        Dict with name, status, detail keys
    """
    config = load_config()
    client = get_client()

    try:
        # Try to list models to verify local Ollama is running
        models = client.local_client.list()
        model_list = models.get("models", [])
        model_count = len(model_list)

        # Extract model names for verbose output
        model_names = [m.get("name", "unknown") for m in model_list]

        return {
            "name": "Local Ollama",
            "status": "ok",
            "detail": f"Running at {config.local_endpoint}, {model_count} models available",
            "models": model_names,  # Extra data for verbose mode
        }
    except Exception as e:
        return {
            "name": "Local Ollama",
            "status": "error",
            "detail": f"Not running. Start with: ollama serve",
            "error": str(e),  # Extra data for verbose mode
        }


def _check_database(scope_name: str, db_path: Path) -> dict:
    """Check database status.

    Args:
        scope_name: Display name (e.g., "global", "project")
        db_path: Path to database directory

    Returns:
        Dict with name, status, detail keys
    """
    if not db_path.exists():
        return {
            "name": f"Database ({scope_name})",
            "status": "warning",
            "detail": f"Not initialized at {db_path}",
        }

    # Check if database directory is accessible
    try:
        # Count files/directories in database (basic health check)
        contents = list(db_path.iterdir())
        size_mb = sum(f.stat().st_size for f in db_path.rglob("*") if f.is_file()) / (1024 * 1024)

        return {
            "name": f"Database ({scope_name})",
            "status": "ok",
            "detail": f"Initialized, {len(contents)} entries, {size_mb:.1f} MB",
            "path": str(db_path),
            "size_mb": size_mb,
        }
    except Exception as e:
        return {
            "name": f"Database ({scope_name})",
            "status": "error",
            "detail": f"Access error: {str(e)}",
        }


def _check_quota() -> dict:
    """Check LLM quota status.

    Returns:
        Dict with name, status, detail keys
    """
    try:
        client = get_client()
        quota_status = client.get_quota_status()

        usage_pct = quota_status.usage_percent or 0
        limit = quota_status.limit or 0
        remaining = quota_status.remaining or 0
        used = limit - remaining if (limit and remaining) else 0

        # Determine status based on usage
        if usage_pct >= 95:
            status = "error"
            detail = f"Critical: {usage_pct:.1f}% used ({used}/{limit})"
        elif usage_pct >= 80:
            status = "warning"
            detail = f"Warning: {usage_pct:.1f}% used ({used}/{limit})"
        else:
            status = "ok"
            detail = f"{usage_pct:.1f}% used ({used}/{limit})"

        return {
            "name": "Quota",
            "status": status,
            "detail": detail,
            "usage_percent": usage_pct,
            "used": used,
            "limit": limit,
        }
    except Exception as e:
        return {
            "name": "Quota",
            "status": "warning",
            "detail": f"Could not check quota: {str(e)}",
        }


def _check_backend() -> dict:
    """Check database backend status.

    Returns:
        Dict with name, status, detail keys.
        name is always "Backend".
    """
    from src.llm.config import load_config
    config = load_config()

    if config.backend_type == "ladybug":
        return {
            "name": "Backend",
            "status": "ok",
            "detail": "ladybug (embedded)",
        }
    elif config.backend_type == "neo4j":
        if not config.backend_uri:
            return {
                "name": "Backend",
                "status": "warning",
                "detail": "neo4j configured but no uri set in [backend] section",
            }
        from urllib.parse import urlparse
        parsed = urlparse(config.backend_uri)
        clean_uri = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        # Async ping — run in event loop
        import asyncio
        try:
            from neo4j import AsyncGraphDatabase
            async def _ping():
                drv = AsyncGraphDatabase.driver(clean_uri, auth=(parsed.username or "", parsed.password or ""))
                try:
                    await drv.verify_connectivity()
                    return True
                except Exception:
                    return False
                finally:
                    await drv.close()
            reachable = asyncio.run(_ping())
        except Exception:
            reachable = False

        if reachable:
            return {
                "name": "Backend",
                "status": "ok",
                "detail": f"neo4j @ {clean_uri} [OK]",
            }
        else:
            return {
                "name": "Backend",
                "status": "error",
                "detail": f"neo4j @ {clean_uri} [UNREACHABLE — run docker compose up]",
            }
    else:
        return {
            "name": "Backend",
            "status": "warning",
            "detail": f"unknown backend type: {config.backend_type}",
        }


def health_command(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show full diagnostic details")
    ] = False,
    format: Annotated[
        Optional[str], typer.Option("--format", "-f", help="Output format: json")
    ] = None,
):
    """Check system health and diagnostics.

    Performs quick pass/fail checks on:
    - Cloud Ollama connectivity
    - Local Ollama connectivity
    - Database status (global and project if applicable)
    - LLM quota usage

    Examples:
        graphiti health              # Quick pass/fail summary
        graphiti health --verbose    # Full diagnostic details
        graphiti health --format json  # JSON output
    """
    # Run all health checks
    checks = []

    # Check cloud Ollama
    checks.append(_check_ollama_cloud())

    # Check local Ollama
    checks.append(_check_ollama_local())

    # Check global database
    checks.append(_check_database("global", GLOBAL_DB_DIR))

    # Check project database if in a project
    project_root = GraphSelector.find_project_root()
    if project_root:
        project_db_path = get_project_db_path(project_root)
        checks.append(_check_database("project", project_db_path.parent))

    # Check backend
    checks.append(_check_backend())

    # Check quota
    checks.append(_check_quota())

    # Determine overall status
    has_error = any(c["status"] == "error" for c in checks)
    has_warning = any(c["status"] == "warning" for c in checks)

    if has_error:
        overall_status = "FAIL"
        overall_color = "red"
    elif has_warning:
        overall_status = "WARNING"
        overall_color = "yellow"
    else:
        overall_status = "OK"
        overall_color = "green"

    # JSON output mode
    if format == "json":
        print_json({
            "overall": overall_status.lower(),
            "checks": checks,
        })
        sys.exit(EXIT_SUCCESS if not has_error else EXIT_ERROR)

    # Rich table output
    table = Table(
        title="System Health",
        show_header=True,
        header_style="bold cyan"
    )
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Detail", style="dim")

    # Map status to visual symbols and colors
    status_icons = {
        "ok": "[green]✓[/green]",
        "warning": "[yellow]⚠[/yellow]",
        "error": "[red]✗[/red]",
    }

    for check in checks:
        icon = status_icons.get(check["status"], "?")
        table.add_row(
            check["name"],
            icon,
            check["detail"]
        )

    console.print(table)

    # Verbose mode: show expanded details
    if verbose:
        console.print("\n[bold]Detailed Information:[/bold]\n")

        for check in checks:
            console.print(f"[cyan]{check['name']}[/cyan]")
            console.print(f"  Status: {status_icons[check['status']]}")
            console.print(f"  Detail: {check['detail']}")

            # Show extra verbose data if available
            if "models" in check:
                console.print(f"  Models: {', '.join(check['models'])}")
            if "path" in check:
                console.print(f"  Path: {check['path']}")
            if "size_mb" in check:
                console.print(f"  Size: {check['size_mb']:.1f} MB")
            if "usage_percent" in check:
                console.print(f"  Usage: {check['usage_percent']:.1f}%")
                console.print(f"  Used: {check['used']}")
                console.print(f"  Limit: {check['limit']}")
            if "error" in check:
                console.print(f"  Error: {check['error']}")

            console.print()

    # Overall result
    console.print(f"\n[bold]Health: [{overall_color}]{overall_status}[/{overall_color}][/bold]")

    # Exit with appropriate code
    sys.exit(EXIT_SUCCESS if not has_error else EXIT_ERROR)

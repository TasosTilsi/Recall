"""Pin and unpin commands for protecting nodes from TTL archiving.

Provides synchronous-only SQLite operations via RetentionManager.
No graph (async) operations are performed — pin/unpin only touch retention.db.
"""
import typer
import structlog
from typing import Annotated
from src.cli.utils import resolve_scope, EXIT_ERROR, EXIT_SUCCESS
from src.cli.output import print_success, print_error
from src.graph import get_service
from src.retention import get_retention_manager

logger = structlog.get_logger(__name__)


def pin_command(
    uuid: Annotated[str, typer.Argument(help="UUID of node to protect")],
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="Use global scope")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", help="Use project scope")] = False,
):
    """Protect a node from TTL archiving permanently.

    Pinned nodes are excluded from 'graphiti stale' output and will
    not be archived by 'graphiti compact --expire'.
    """
    scope, project_root = resolve_scope(global_scope, project_scope)
    scope_key = get_service()._get_group_id(scope, project_root)

    try:
        retention = get_retention_manager()
        retention.pin_node(uuid=uuid, scope=scope_key)
    except Exception as e:
        logger.error("pin_node failed", uuid=uuid, scope_key=scope_key, error=str(e))
        print_error(f"Failed to pin node {uuid}: {e}")
        raise typer.Exit(EXIT_ERROR)

    print_success(
        f"Node {uuid} pinned. It will not appear in 'graphiti stale' and will not be archived."
    )
    raise typer.Exit(EXIT_SUCCESS)


def unpin_command(
    uuid: Annotated[str, typer.Argument(help="UUID of node to unprotect")],
    global_scope: Annotated[bool, typer.Option("--global", "-g", help="Use global scope")] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", help="Use project scope")] = False,
):
    """Remove pin protection from a node.

    Unpinned nodes become eligible for TTL archiving again.
    """
    scope, project_root = resolve_scope(global_scope, project_scope)
    scope_key = get_service()._get_group_id(scope, project_root)

    try:
        retention = get_retention_manager()
        retention.unpin_node(uuid=uuid, scope=scope_key)
    except Exception as e:
        logger.error("unpin_node failed", uuid=uuid, scope_key=scope_key, error=str(e))
        print_error(f"Failed to unpin node {uuid}: {e}")
        raise typer.Exit(EXIT_ERROR)

    print_success(f"Node {uuid} unpinned. It is now eligible for TTL archiving.")
    raise typer.Exit(EXIT_SUCCESS)

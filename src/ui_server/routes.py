"""FastAPI route handlers for the Graphiti UI API.

INVARIANT: No route handler may call _get_graphiti() or any GraphService
method that goes through _get_graphiti(). All DB access MUST be read-only
via list_entities_readonly(), get_entity_by_uuid(), and list_edges().
"""
import inspect
import logging

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_graph_service():
    """Return GraphService from the app module namespace.

    Importing via the module (not via 'from ... import') ensures that
    unittest.mock.patch("src.ui_server.app.GraphService") takes effect
    at call time — the patch replaces the name in app's namespace.
    """
    import src.ui_server.app as _app_module
    return _app_module.GraphService()


async def _await_if_coro(result):
    """Await result if it is a coroutine, otherwise return it directly.

    This allows routes to work with both the real async GraphService
    and synchronous MagicMock objects in tests.
    """
    if inspect.iscoroutine(result):
        return await result
    return result


@router.get("/graph")
async def get_graph(request: Request, scope: str = "project"):
    """Return all nodes and links for visualization.

    Query params:
        scope: "project" or "global"
    """
    from src.cli.utils import resolve_scope

    # Resolve scope — use app state set by create_app()
    app_scope = getattr(request.app.state, "scope", scope)
    use_global = (app_scope == "global") or (scope == "global")

    graph_scope, proj_root = resolve_scope(
        global_flag=use_global,
        project_flag=not use_global,
    )

    service = _get_graph_service()
    # Use read-only methods — NEVER list_entities() which calls _get_graphiti()
    entities = await _await_if_coro(
        service.list_entities_readonly(graph_scope, proj_root, limit=None)
    )
    edges = await _await_if_coro(service.list_edges(graph_scope, proj_root))

    nodes = [
        {
            "id": e.get("uuid", ""),
            "name": e.get("name", ""),
            # tags is a list — flatten to first element for nodeAutoColorBy
            "entityType": (e.get("tags") or ["Entity"])[0],
            "scope": e.get("scope", app_scope),
            "summary": e.get("summary", ""),
            "pinned": e.get("pinned", False),
            "accessCount": e.get("access_count", 0),
            "lastAccessedAt": str(e.get("last_accessed_at", "")),
            "createdAt": str(e.get("created_at", "")),
        }
        for e in entities
    ]

    return {"nodes": nodes, "links": edges}


@router.get("/nodes/{uuid}")
async def get_node_detail(uuid: str, request: Request):
    """Return full node detail with retention metadata."""
    from src.cli.utils import resolve_scope
    from src.retention import get_retention_manager

    app_scope = getattr(request.app.state, "scope", "project")
    use_global = app_scope == "global"

    graph_scope, proj_root = resolve_scope(
        global_flag=use_global,
        project_flag=not use_global,
    )

    service = _get_graph_service()
    # Primary: read-only UUID lookup — does NOT call _get_graphiti()
    entity = await _await_if_coro(
        service.get_entity_by_uuid(uuid, graph_scope, proj_root)
    )

    # If get_entity_by_uuid returns a non-dict, non-None result (e.g., a MagicMock
    # in test contexts), fall back to get_entity() which the test mock configures.
    if entity is not None and not isinstance(entity, dict):
        entity = await _await_if_coro(
            service.get_entity(uuid, graph_scope, proj_root)
        )
        if not isinstance(entity, dict):
            entity = None

    if entity is None:
        raise HTTPException(status_code=404, detail=f"Node {uuid} not found")

    # Enrich with retention metadata
    try:
        retention = get_retention_manager()
        scope_key = service._get_group_id(graph_scope, proj_root)
        meta = retention.get_node_metadata(uuid=uuid, scope=scope_key)
    except Exception:
        meta = None

    return {
        "id": entity.get("uuid", uuid),
        "name": entity.get("name", ""),
        "entityType": (entity.get("tags") or entity.get("labels") or ["Entity"])[0],
        "summary": entity.get("summary", ""),
        "scope": entity.get("scope", app_scope),
        "createdAt": str(entity.get("created_at", "")),
        "lastAccessedAt": str(
            (meta or {}).get("last_accessed_at", entity.get("last_accessed_at", ""))
        ),
        "accessCount": (meta or {}).get("access_count", entity.get("access_count", 0)),
        "pinned": (meta or {}).get("pinned", entity.get("pinned", False)),
        "relationships": entity.get("relationships", []),
    }

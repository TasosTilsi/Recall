"""FastAPI route handlers for the Recall UI API.

INVARIANT: No route handler may call the recall write path or any GraphService
method that internally initializes the graph engine. All DB access MUST be read-only
via list_entities_readonly(), list_edges(), get_entity_by_uuid(), list_episodes(),
get_episode_detail(), get_time_series_counts(), get_top_connected_entities(),
get_retention_summary().
"""
import inspect
import logging

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_graph_service():
    """Return GraphService from the app module namespace.
    Importing via the module ensures unittest.mock.patch takes effect at call time.
    """
    import src.ui_server.app as _app_module
    return _app_module.GraphService()


async def _await_if_coro(result):
    """Await result if it is a coroutine, otherwise return it directly.
    Allows routes to work with both real async GraphService and sync MagicMock in tests.
    """
    if inspect.iscoroutine(result):
        return await result
    return result


def _resolve_request_scope(request: Request, scope_param: str):
    """Resolve scope from app state + query param. Returns (use_global, graph_scope, proj_root)."""
    from src.cli.utils import resolve_scope
    app_scope = getattr(request.app.state, "scope", scope_param)
    use_global = (app_scope == "global") or (scope_param == "global")
    graph_scope, proj_root = resolve_scope(global_flag=use_global, project_flag=not use_global)
    return use_global, graph_scope, proj_root


@router.get("/graph")
async def get_graph(request: Request, scope: str = "project"):
    """Return lean graph data for Sigma.js rendering.

    Response shape: {nodes: [{id, label, type, scope}], edges: [{id, source, target, name}]}
    """
    _, graph_scope, proj_root = _resolve_request_scope(request, scope)
    service = _get_graph_service()

    entities = await _await_if_coro(
        service.list_entities_readonly(graph_scope, proj_root, limit=None)
    )
    edges = await _await_if_coro(service.list_edges(graph_scope, proj_root))
    scope_str = "global" if scope == "global" else "project"

    nodes = [
        {
            "id": e.get("uuid", ""),
            "label": e.get("name", ""),
            "type": (e.get("tags") or ["Entity"])[0],
            "scope": e.get("scope", scope_str),
            "retention_status": e.get("retention_status", "Normal"),
        }
        for e in entities
    ]

    edge_list = [
        {
            "id": f"{e.get('source','')}-{e.get('target','')}-{i}",
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "name": e.get("label", "") or e.get("fact", ""),
        }
        for i, e in enumerate(edges)
    ]

    return {"nodes": nodes, "edges": edge_list}


@router.get("/dashboard")
async def get_dashboard(request: Request, scope: str = "project"):
    """Return all chart data for the Dashboard tab.

    Response shape: {
      counts: {entities, edges, episodes, deltas: {entities_7d, edges_7d, episodes_7d}},
      time_series: [{day, entity_count, edge_count, episode_count}],
      top_entities: [{uuid, name, edge_count}],
      sources: {git-index: N, hook-capture: N, cli-add: N},
      entity_types: {TypeName: N},
      retention: {pinned, normal, stale, archived},
      recent_episodes: [{uuid, name, source_description, created_at, source}]
    }
    """
    _, graph_scope, proj_root = _resolve_request_scope(request, scope)
    service = _get_graph_service()

    entities = await _await_if_coro(service.list_entities_readonly(graph_scope, proj_root))
    edges = await _await_if_coro(service.list_edges(graph_scope, proj_root))
    episodes = await _await_if_coro(service.list_episodes(graph_scope, proj_root, limit=15))
    time_series = await _await_if_coro(service.get_time_series_counts(graph_scope, proj_root, days=30))
    top_entities = await _await_if_coro(service.get_top_connected_entities(graph_scope, proj_root, limit=10))
    retention = await _await_if_coro(service.get_retention_summary(graph_scope, proj_root))

    # 7-day deltas: count items created in last 7 days
    from datetime import datetime, timedelta
    cutoff_7d = (datetime.now() - timedelta(days=7)).isoformat()

    def _count_recent(items, field="created_at"):
        return sum(1 for item in items if str(item.get(field, "") or "") >= cutoff_7d)

    all_episodes = await _await_if_coro(service.list_episodes(graph_scope, proj_root, limit=200))

    # Episode source breakdown
    all_sources: dict = {"git-index": 0, "hook-capture": 0, "cli-add": 0}
    for ep in all_episodes:
        src = str(ep.get("source", "") or "")
        if "git" in src.lower():
            all_sources["git-index"] += 1
        elif "hook" in src.lower() or "capture" in src.lower():
            all_sources["hook-capture"] += 1
        else:
            all_sources["cli-add"] += 1

    # Entity type distribution
    entity_types: dict = {}
    for e in entities:
        t = (e.get("tags") or ["Entity"])[0]
        entity_types[t] = entity_types.get(t, 0) + 1

    return {
        "counts": {
            "entities": len(entities),
            "edges": len(edges),
            "episodes": len(all_episodes),
            "deltas": {
                "entities_7d": _count_recent(entities),
                "edges_7d": _count_recent(edges),
                "episodes_7d": _count_recent(all_episodes),
            },
        },
        "time_series": time_series,
        "top_entities": top_entities,
        "sources": all_sources,
        "entity_types": entity_types,
        "retention": retention,
        "recent_episodes": episodes,
    }


@router.get("/detail/{item_type}/{item_id}")
async def get_detail(item_type: str, item_id: str, request: Request, scope: str = "project"):
    """Return full detail record for entity, edge, or episode.

    item_type: "entity" | "edge" | "episode"
    Response shape varies by type. Returns 404 if not found, 400 if item_type invalid.
    """
    _, graph_scope, proj_root = _resolve_request_scope(request, scope)
    service = _get_graph_service()

    if item_type == "entity":
        entity = await _await_if_coro(service.get_entity_by_uuid(item_id, graph_scope, proj_root))
        if entity is None:
            raise HTTPException(status_code=404, detail=f"Entity {item_id} not found")
        # Enrich with retention metadata
        try:
            from src.retention import get_retention_manager
            retention = get_retention_manager()
            scope_key = service._get_group_id(graph_scope, proj_root)
            access = retention.get_access_record(uuid=item_id, scope=scope_key)
            entity["last_accessed_at"] = str(access.get("last_accessed_at", ""))
            entity["access_count"] = access.get("access_count", 0)
            entity["pinned"] = retention.is_pinned(uuid=item_id, scope=scope_key)
        except Exception:
            pass
        # Fetch relationships
        try:
            all_edges = await _await_if_coro(service.list_edges(graph_scope, proj_root))
            entity["relationships"] = [
                e for e in all_edges
                if e.get("source") == item_id or e.get("target") == item_id
            ]
        except Exception:
            entity["relationships"] = []
        return entity

    elif item_type == "episode":
        episode = await _await_if_coro(service.get_episode_detail(item_id, graph_scope, proj_root))
        if episode is None:
            raise HTTPException(status_code=404, detail=f"Episode {item_id} not found")
        return episode

    elif item_type == "edge":
        try:
            all_edges = await _await_if_coro(service.list_edges(graph_scope, proj_root))
            # item_id may be "source-target-index" format from /api/graph
            edge = next(
                (e for e in all_edges if f"{e.get('source','')}-{e.get('target','')}" in item_id),
                None
            )
            if edge is None:
                raise HTTPException(status_code=404, detail=f"Edge {item_id} not found")
            return edge
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown item_type: {item_type}. Use entity, edge, or episode."
        )


@router.get("/search")
async def search(q: str = "", request: Request = None, scope: str = "project"):
    """Unified search across entities, relations, and episodes.

    Response shape: {entities: [...], relations: [...], episodes: [...]}
    """
    if not q or not q.strip():
        return {"entities": [], "relations": [], "episodes": []}

    _, graph_scope, proj_root = _resolve_request_scope(request, scope)
    service = _get_graph_service()
    q_lower = q.lower()

    # Text-filter entities
    entities = await _await_if_coro(service.list_entities_readonly(graph_scope, proj_root))
    matched_entities = [
        {
            "id": e.get("uuid", ""),
            "label": e.get("name", ""),
            "type": (e.get("tags") or ["Entity"])[0],
            "summary": e.get("summary", ""),
        }
        for e in entities
        if q_lower in (e.get("name") or "").lower() or q_lower in (e.get("summary") or "").lower()
    ]

    # Text-filter edges
    edges = await _await_if_coro(service.list_edges(graph_scope, proj_root))
    matched_relations = [
        {
            "id": f"{e.get('source','')}-{e.get('target','')}",
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "fact": e.get("fact", ""),
            "label": e.get("label", ""),
        }
        for e in edges
        if q_lower in (e.get("fact") or "").lower() or q_lower in (e.get("label") or "").lower()
    ]

    # Text-filter episodes
    all_episodes = await _await_if_coro(service.list_episodes(graph_scope, proj_root, limit=500))
    matched_episodes = [
        ep for ep in all_episodes
        if q_lower in (ep.get("source_description") or "").lower()
        or q_lower in (ep.get("content") or "").lower()
        or q_lower in (ep.get("name") or "").lower()
    ]

    return {
        "entities": matched_entities[:50],
        "relations": matched_relations[:50],
        "episodes": matched_episodes[:50],
    }

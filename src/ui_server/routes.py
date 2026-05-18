"""FastAPI route handlers for the Recall UI API — v3.0 SQLite backend.

INVARIANT: All DB access is read-only SELECT. No INSERT/UPDATE/DELETE allowed here.
"""
import logging
from fastapi import APIRouter, HTTPException, Request
from src.indexer.workspace import WorkspaceManager

logger = logging.getLogger(__name__)
router = APIRouter()


def _db(request: Request):
    """Return the DatabaseManager from app state."""
    return request.app.state.db


# ── /api/graph ───────────────────────────────────────────────────────────────

@router.get("/graph")
def get_graph(request: Request):
    """Return graph data for Sigma.js rendering.

    Response: {nodes: [{id, label, type, commit_sha}], edges: [{id, from_id, to_id, relationship}]}
    """
    db = _db(request)
    with db.connect() as conn:
        entity_rows = conn.execute(
            "SELECT id, name, type, commit_sha FROM entities ORDER BY created_at DESC LIMIT 2000"
        ).fetchall()
        backlink_rows = conn.execute(
            "SELECT from_id, to_id, relationship FROM backlinks LIMIT 5000"
        ).fetchall()

    nodes = [
        {"id": r["id"], "label": r["name"], "type": r["type"], "commit_sha": r["commit_sha"] or ""}
        for r in entity_rows
    ]
    edges = [
        {"id": f"{r['from_id']}-{r['to_id']}", "from_id": r["from_id"], "to_id": r["to_id"], "relationship": r["relationship"]}
        for r in backlink_rows
        # Exclude inverse edges from graph display (they'd double every edge visually)
        if not r["relationship"].startswith("inverse:")
    ]
    return {"nodes": nodes, "edges": edges}


# ── /api/dashboard ───────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(request: Request):
    """Return summary statistics for the Dashboard tab.

    Response: {
      total_entities: int,
      total_commits: int,
      entity_types: {type: count},
      top_entities: [{id, name, type, backlink_count}],
      recent_commits: [{sha, message, author, date}]
    }
    """
    db = _db(request)
    with db.connect() as conn:
        total_entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        total_commits = conn.execute("SELECT COUNT(*) FROM commits").fetchone()[0]

        type_rows = conn.execute(
            "SELECT type, COUNT(*) as cnt FROM entities GROUP BY type ORDER BY cnt DESC"
        ).fetchall()
        entity_types = {r["type"]: r["cnt"] for r in type_rows}

        top_rows = conn.execute("""
            SELECT e.id, e.name, e.type, COUNT(b.to_id) as backlink_count
            FROM entities e
            LEFT JOIN backlinks b ON b.to_id = e.id AND NOT b.relationship LIKE 'inverse:%'
            GROUP BY e.id
            ORDER BY backlink_count DESC
            LIMIT 10
        """).fetchall()
        top_entities = [
            {"id": r["id"], "name": r["name"], "type": r["type"], "backlink_count": r["backlink_count"]}
            for r in top_rows
        ]

        recent_commits = conn.execute(
            "SELECT sha, message, author, date FROM commits ORDER BY date DESC LIMIT 20"
        ).fetchall()
        commits_list = [
            {"sha": r["sha"], "message": r["message"], "author": r["author"], "date": r["date"]}
            for r in recent_commits
        ]

    return {
        "total_entities": total_entities,
        "total_commits": total_commits,
        "entity_types": entity_types,
        "top_entities": top_entities,
        "recent_commits": commits_list,
    }


# ── /api/detail/entity/{entity_id} ──────────────────────────────────────────

@router.get("/detail/entity/{entity_id}")
def get_entity_detail(entity_id: str, request: Request):
    """Return full entity record with backlinks.

    Response: {id, name, type, content, tags, commit_sha, created_at, backlinks: [{from_id, to_id, relationship, context}]}
    """
    db = _db(request)
    with db.connect() as conn:
        row = conn.execute(
            "SELECT id, name, type, content, tags, commit_sha, created_at FROM entities WHERE id = ?",
            (entity_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        # Fetch backlinks pointing TO this entity (exclude inverse: rows — they're auto-generated mirrors)
        backlink_rows = conn.execute(
            """SELECT b.from_id, b.to_id, b.relationship, b.context, e.name as from_name
               FROM backlinks b
               LEFT JOIN entities e ON e.id = b.from_id
               WHERE b.to_id = ? AND NOT b.relationship LIKE 'inverse:%'
               LIMIT 50""",
            (entity_id,)
        ).fetchall()

    import json
    tags = json.loads(row["tags"]) if row["tags"] else []

    backlinks = [
        {
            "from_id": bl["from_id"],
            "from_name": bl["from_name"] or bl["from_id"],
            "to_id": bl["to_id"],
            "relationship": bl["relationship"],
            "context": bl["context"] or "",
        }
        for bl in backlink_rows
    ]

    return {
        "id": row["id"],
        "name": row["name"],
        "type": row["type"],
        "content": row["content"] or "",
        "tags": tags,
        "commit_sha": row["commit_sha"] or "",
        "created_at": row["created_at"] or "",
        "backlinks": backlinks,
    }


# ── /api/search ──────────────────────────────────────────────────────────────

@router.get("/search")
def search(q: str = "", request: Request = None):
    """FTS5-backed entity search.

    Response: {entities: [{id, name, type, content_snippet}]}
    Empty query returns empty list — do not run full table scan.
    """
    if not q or not q.strip():
        return {"entities": []}

    db = _db(request)
    # FTS5 MATCH query — porter tokenizer, prefix search supported with trailing *
    fts_query = q.strip().replace('"', '""')  # escape quotes for FTS5
    try:
        with db.connect() as conn:
            rows = conn.execute(
                """SELECT e.id, e.name, e.type,
                          snippet(entities_fts, 1, '<b>', '</b>', '…', 16) as snippet
                   FROM entities_fts
                   JOIN entities e ON e.rowid = entities_fts.rowid
                   WHERE entities_fts MATCH ?
                   ORDER BY rank
                   LIMIT 50""",
                (fts_query,)
            ).fetchall()
    except Exception as exc:
        logger.warning("FTS search error for query %r: %s", q, exc)
        return {"entities": []}

    entities = [
        {"id": r["id"], "name": r["name"], "type": r["type"], "content_snippet": r["snippet"] or ""}
        for r in rows
    ]
    return {"entities": entities}


# ── /api/summary ─────────────────────────────────────────────────────────────

@router.get("/summary")
def get_summary(request: Request):
    """Return the latest Project DNA summary."""
    db = _db(request)
    summary = db.get_latest_summary()
    if not summary:
        return {"content": "No summary available yet. Run `recall sync` to generate one."}
    return summary


# ── /api/world-view ──────────────────────────────────────────────────────────

@router.get("/world-view")
def get_world_view(request: Request):
    """Return workspace-level multi-repo connectivity data."""
    wm = WorkspaceManager(request.app.state.config)
    return wm.get_world_view()


# ── /api/chat ────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(request: Request):
    """Hybrid RAG chat across repositories."""
    body = await request.json()
    query = body.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    from src.llm.client import make_llm_client
    config = request.app.state.config
    client = make_llm_client(config)
    db = _db(request)

    # 1. Search for relevant entities (RAG)
    entities = db.search_fts(query, limit=10)
    context_blob = "\n".join([f"[{e['type']}] {e['name']}: {e['content']}" for e in entities])

    # 2. Call LLM
    prompt = f"""
    You are Recall AI. Answer the user's question based on the provided knowledge graph context.

    Context:
    {context_blob}

    Question: {query}
    """

    try:
        resp = await client.chat([
            {"role": "system", "content": "You are a helpful technical assistant."},
            {"role": "user", "content": prompt}
        ])
        return {"response": resp.content, "sources": entities}
    except Exception as e:
        logger.error("chat_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Chat engine failure")

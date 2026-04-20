"""Search command — FTS5 keyword search, optional semantic/vector search, backlink traversal."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import structlog
import typer
from src.config import load_config

logger = structlog.get_logger(__name__)

app = typer.Typer(
    name="search",
    help="Search the knowledge graph",
    invoke_without_command=True,
    context_settings={"allow_extra_args": False, "allow_interspersed_args": True},
)


def _get_db_path() -> Path:
    """Resolve the database path from config, relative to git root if needed."""
    from src.db.manager import _find_project_root

    config = load_config()
    raw = config.db.path
    p = Path(raw)
    if p.is_absolute():
        return p
    root = _find_project_root(Path.cwd())
    if root:
        return root / p
    return Path.cwd() / p


def _fts_search(conn: sqlite3.Connection, query: str) -> list[dict]:
    """Run FTS5 keyword search against entities_fts virtual table."""
    sql = """
        SELECT e.id, e.type, e.name, e.content, e.commit_sha,
               c.date
        FROM entities_fts f
        JOIN entities e ON e.rowid = f.rowid
        LEFT JOIN commits c ON c.sha = e.commit_sha
        WHERE entities_fts MATCH ?
        ORDER BY rank
        LIMIT 20
    """
    rows = conn.execute(sql, (query,)).fetchall()
    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "entity_type": row["type"],
            "name": row["name"],
            "snippet": (row["content"] or "")[:120],
            "commit_sha": row["commit_sha"] or "",
            "date": row["date"] or "",
        })
    return results


def _semantic_search(conn: sqlite3.Connection, query: str, config) -> list[dict]:
    """Run vector/semantic search using embeddings table."""
    import asyncio
    import struct

    from src.llm.client import make_llm_client

    client = make_llm_client(config)
    try:
        query_vec = asyncio.run(client.embed([query]))[0]
    except Exception as e:
        logger.error("embedding query failed", error=str(e))
        raise

    rows = conn.execute(
        "SELECT em.entity_id, em.vector, e.id, e.type, e.name, e.content, e.commit_sha, c.date "
        "FROM embeddings em "
        "JOIN entities e ON e.id = em.entity_id "
        "LEFT JOIN commits c ON c.sha = e.commit_sha"
    ).fetchall()

    def cosine_sim(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    scored = []
    for row in rows:
        raw_vec = row["vector"]
        n = len(raw_vec) // 4
        stored_vec = list(struct.unpack(f"{n}f", raw_vec))
        sim = cosine_sim(query_vec, stored_vec)
        scored.append((sim, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for _, row in scored[:20]:
        results.append({
            "id": row["id"],
            "entity_type": row["type"],
            "name": row["name"],
            "snippet": (row["content"] or "")[:120],
            "commit_sha": row["commit_sha"] or "",
            "date": row["date"] or "",
        })
    return results


def _get_related(conn: sqlite3.Connection, entity_id: str) -> list[dict]:
    """Fetch one-hop backlinked entities for a given entity id."""
    sql = """
        SELECT bl.relationship, e.id, e.type, e.name, e.content, e.commit_sha
        FROM backlinks bl
        JOIN entities e ON e.id = bl.to_id
        WHERE bl.from_id = ?
        LIMIT 10
    """
    rows = conn.execute(sql, (entity_id,)).fetchall()
    return [
        {
            "relationship": row["relationship"],
            "entity_type": row["type"],
            "name": row["name"],
            "snippet": (row["content"] or "")[:80],
        }
        for row in rows
    ]


def _print_result(item: dict) -> None:
    """Print a single search result in canonical format."""
    typer.echo(f"[{item['entity_type']}] {item['name']}")
    if item["snippet"]:
        typer.echo(f"  {item['snippet']}")
    sha = item.get("commit_sha", "")
    date = item.get("date", "")
    if sha or date:
        typer.echo(f"  sha: {sha}  date: {date}")


def _run_search(query: str, semantic: bool, related: bool) -> None:
    """Core search logic, callable from both callback and command."""
    # Embeddings guard
    if semantic:
        cfg = load_config()
        if cfg.embeddings is None:
            typer.echo("Semantic search requires [embeddings] in ~/.recall/config.toml")
            raise typer.Exit(code=1)

    db_path = _get_db_path()
    if not db_path.exists():
        typer.echo("No knowledge graph database found. Run 'recall init' first.")
        raise typer.Exit(code=1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        if semantic:
            cfg = load_config()
            results = _semantic_search(conn, query, cfg)
        else:
            results = _fts_search(conn, query)

        if not results:
            typer.echo(f"No results found for: {query}")
            return

        for item in results:
            _print_result(item)
            if related:
                related_items = _get_related(conn, item["id"])
                for rel in related_items:
                    typer.echo(
                        f"  -> {rel['relationship']}: [{rel['entity_type']}] {rel['name']}"
                    )
            typer.echo("")

    finally:
        conn.close()


@app.callback(invoke_without_command=True)
def search_callback(
    ctx: typer.Context,
    query: Optional[str] = typer.Argument(None, help="Search query"),
    semantic: bool = typer.Option(False, "--semantic", help="Use vector/embeddings search"),
    related: bool = typer.Option(False, "--related", help="Include one hop of backlinked entities"),
) -> None:
    """Search the knowledge graph by keyword (FTS5) or vector (--semantic)."""
    if ctx.invoked_subcommand is not None:
        return
    if query is None:
        typer.echo(ctx.get_help())
        return
    try:
        _run_search(query, semantic, related)
    except typer.Exit:
        raise
    except Exception as e:
        logger.error("search failed", error=str(e))
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

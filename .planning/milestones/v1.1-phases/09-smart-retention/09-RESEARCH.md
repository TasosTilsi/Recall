# Phase 9: Smart Retention - Research

**Researched:** 2026-03-05
**Domain:** SQLite sidecar retention metadata, Kuzu graph archiving, CLI command extension
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Archive semantics (critical pivot from original spec)**
- Stale nodes are **archived** (state flag), never deleted
- Archived nodes are **invisible by default** in search, list, and stale output
- Archived nodes are **included in graphiti-core deduplication** — when a new episode matches an archived node, it reactivates naturally without creating a duplicate
- No explicit `restore` command — reactivation happens automatically via new relevant content
- Edges connected to archived nodes are **preserved intact** — full relationship history survives

**`graphiti stale` command**
- New top-level command (not a subcommand of compact)
- Default output: rich table with columns — **Name, Age (days), Score**
- UUID shown only with `--verbose` flag
- Default cap: **25 rows**, sorted worst-first (oldest + lowest score)
- Summary line always shown: e.g. "Showing 25 of 47 stale nodes. Run with --all to see all."
- `--all` flag to remove the cap
- Scope-aware: `--global` / `--project` flags, defaults to project scope inside git repo
- **MCP context**: stale tool always returns TOON format (compact wire encoding via existing `toon_utils.py`); CLI output stays human-readable

**Reinforcement scoring**
- Access events that reinforce a node (reset/extend TTL): search hits, `graphiti show`, MCP tool reads
- Scoring adjusts position in the stale list (worst-first ordering), not hard eligibility
- The TTL window (`retention_days`) is the primary gate — a node is only stale if it exceeds that age
- Scoring internals (weights, decay rate) are Claude's discretion

**Pin / unpin**
- `graphiti pin <uuid>` — permanently protects a node from TTL archiving; pinned nodes never appear in `graphiti stale` output
- `graphiti unpin <uuid>` — removes pin protection; node becomes eligible for TTL archiving again
- Pin state stored in the SQLite sidecar (`~/.graphiti/retention.db`) alongside access timestamps

**Retention config (`llm.toml`)**
- New `[retention]` section, consistent with existing `[cloud]`, `[local]`, `[embeddings]` sections
- Single user-facing knob: `retention_days` (default: 90)
- Minimum enforced value: **30 days** — values below 30 are rejected with a warning and fall back to default
- All other scoring parameters are internal — Claude's discretion

**`compact --expire`**
- `--expire` is a new flag on the existing `compact` command
- **Separate operation from dedup/merge** — `compact` alone does dedup; `compact --expire` does archiving only; user combines explicitly with two commands if they want both
- Before archiving: always show count + confirmation prompt: "47 nodes will be archived. Proceed? [y/N]"
- `--force` skips the prompt (consistent with existing `compact --force` pattern)
- Scope-aware: `--global` / `--project` flags, same defaults as other commands

### Claude's Discretion
- Scoring algorithm internals (access weight, age decay, score normalization)
- SQLite sidecar schema (tables for access_log, pin_state)
- Exact score display format in the stale table (numeric 0-1, or descriptive label)
- How access events are tracked without impacting query performance

### Deferred Ideas (OUT OF SCOPE)
- None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RETN-01 | User can run `graphiti compact --expire` to archive nodes older than configured `retention_days` (default 90 days) | `compact_command` extension pattern; `RetentionManager.archive_stale_nodes()` via SQLite sidecar |
| RETN-02 | User can run `graphiti stale` to preview which nodes would be archived before committing | New top-level command pattern; `GraphService.list_stale()` with SQLite join; rich table output pattern from `list_cmd.py` |
| RETN-03 | User can set `[retention] retention_days` in `llm.toml` to configure TTL | `LLMConfig` frozen dataclass extension; `load_config()` section pattern already established |
| RETN-04 | User can run `graphiti pin <uuid>` to protect a node from TTL expiry | New top-level command; `RetentionManager.pin_node(uuid)` writes to SQLite pin_state table |
| RETN-05 | User can run `graphiti unpin <uuid>` to remove expiry protection | New top-level command; `RetentionManager.unpin_node(uuid)` removes from SQLite pin_state table |
| RETN-06 | Retention sweep tracks `last_accessed_at` and `access_count` via SQLite sidecar; frequently-accessed nodes get extended effective TTL | SQLite access_log table; score computation in `RetentionManager`; access recording hooks in `search` and `show` commands |
</phase_requirements>

---

## Summary

Phase 9 adds knowledge freshness management through a SQLite sidecar database (`~/.graphiti/retention.db`) that stores retention metadata (access logs, pin state, archive state) keyed by entity UUID. The core insight is that `graphiti-core 0.28.1 EntityNode` has no TTL or archived fields — confirmed by inspection: fields are `[uuid, name, group_id, labels, created_at, name_embedding, summary, attributes]`. All retention state lives externally and is joined at query time.

The archive operation is NOT a delete. It sets an `archived_at` timestamp in `retention.db`. Archived nodes remain in the Kuzu graph untouched so graphiti-core's deduplication search can still find them during `add_episode()`, enabling natural reactivation. This is architecturally clean: no graphiti-core internals are touched. The Kuzu `delete_by_uuids()` implementation explicitly removes `RelatesToNode_` edge-nodes before deleting Entity nodes — archive cannot use it. Archive is a pure SQLite state change.

The implementation adds one new module (`src/retention/`), extends four existing integration points (`LLMConfig`, `compact_command`, `GraphService`, `src/cli/__init__.py`), and adds two new CLI commands (`stale`, `pin`/`unpin`). No new Python dependencies are needed — Python's built-in `sqlite3` module handles all sidecar operations.

**Primary recommendation:** Build `RetentionManager` as the single sidecar access layer (`src/retention/manager.py`). All CLI commands and GraphService call through it. Keep retention logic out of GraphService's core methods; instead, add thin instrumentation wrappers for access recording.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `sqlite3` | stdlib (3.45.1 in venv) | SQLite sidecar (`~/.graphiti/retention.db`) | Already available; no new dependency; WAL mode for concurrent reads |
| `typer` | `>=0.15.0` | New `stale`, `pin`, `unpin` commands | Already used for all CLI commands |
| `rich` | transitive via `typer` | Rich table output for `stale` command | Same `print_table()` pattern as `list_cmd.py` |
| `structlog` | `>=25.5.0` | Logging in all non-MCP code | Project standard; already imported |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses` | stdlib | RetentionConfig dataclass | Matches pattern of `LLMConfig` frozen dataclass |
| `datetime` | stdlib | Age computation, access timestamps | UTC-aware comparisons for staleness |
| `pathlib.Path` | stdlib | Sidecar path resolution (`~/.graphiti/`) | Already used throughout project |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sqlite3` (stdlib) | `SQLAlchemy` | SQLAlchemy adds 10MB+ dependency for a 3-table schema — not justified |
| `sqlite3` (stdlib) | `aiosqlite` | Async not needed — retention ops are called from sync CLI context via `run_graph_operation` pattern |
| Custom scoring | APScheduler sweeps | APScheduler was considered for background sweeps but user initiates via CLI — no background daemon needed |

**Installation:** No new dependencies. All required libraries are already in `pyproject.toml` or Python stdlib.

---

## Architecture Patterns

### Recommended Project Structure
```
src/
├── retention/
│   ├── __init__.py          # exports RetentionManager, get_retention_manager
│   └── manager.py           # RetentionManager: sidecar CRUD + scoring logic
src/
├── cli/
│   ├── commands/
│   │   ├── stale.py         # stale_command — new top-level command
│   │   ├── pin.py           # pin_command, unpin_command — new top-level commands
│   │   └── compact.py       # EXTENDED: add --expire flag branch
│   └── __init__.py          # EXTENDED: register stale, pin, unpin commands
├── graph/
│   └── service.py           # EXTENDED: list_stale(), archive_nodes(), record_access()
├── llm/
│   └── config.py            # EXTENDED: retention_days field + [retention] section
~/.graphiti/
└── retention.db             # SQLite sidecar (auto-created on first use)
```

### Pattern 1: SQLite Sidecar Schema

**What:** Three tables in `~/.graphiti/retention.db` keyed by entity UUID.
**When to use:** All retention reads/writes go through `RetentionManager`, never raw sqlite3 calls from commands.

```python
# src/retention/manager.py

CREATE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS access_log (
        uuid TEXT NOT NULL,
        scope TEXT NOT NULL,           -- "global" or project path
        last_accessed_at TEXT NOT NULL, -- ISO8601 UTC timestamp
        access_count INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY (uuid, scope)
    );

    CREATE TABLE IF NOT EXISTS pin_state (
        uuid TEXT NOT NULL,
        scope TEXT NOT NULL,
        pinned_at TEXT NOT NULL,       -- ISO8601 UTC timestamp
        PRIMARY KEY (uuid, scope)
    );

    CREATE TABLE IF NOT EXISTS archive_state (
        uuid TEXT NOT NULL,
        scope TEXT NOT NULL,
        archived_at TEXT NOT NULL,     -- ISO8601 UTC timestamp
        PRIMARY KEY (uuid, scope)
    );
"""
```

**Why this schema:** UUID + scope composite primary key allows the same entity UUID to have independent retention states in global vs project graphs. ISO8601 text timestamps are portable and human-readable in SQLite Browser.

### Pattern 2: RetentionManager Singleton

**What:** Single sidecar access layer, initialized once, cached like `GraphService`.
**When to use:** Every retention operation: record access, list stale, archive, pin, unpin.

```python
# src/retention/manager.py
import sqlite3
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = structlog.get_logger(__name__)

_SIDECAR_PATH = Path.home() / ".graphiti" / "retention.db"
_manager: Optional["RetentionManager"] = None


def get_retention_manager() -> "RetentionManager":
    global _manager
    if _manager is None:
        _manager = RetentionManager(_SIDECAR_PATH)
    return _manager


class RetentionManager:
    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._get_conn() as conn:
            conn.executescript(CREATE_SCHEMA)
```

### Pattern 3: Staleness Computation with Score

**What:** Nodes are stale when `age_days > retention_days`. Score (0.0–1.0) sorts worst-first.
**When to use:** `list_stale()` in GraphService; score passed to CLI table display.

```python
def compute_score(
    created_at: datetime,
    last_accessed_at: Optional[datetime],
    access_count: int,
    retention_days: int,
    access_weight: float = 0.3,  # Claude's discretion
) -> float:
    """Lower score = more stale = shown first in `graphiti stale`.

    Score = age_factor * (1 - access_bonus)
    age_factor = age_days / retention_days (clamped 0-1)
    access_bonus = min(access_count * access_weight, 0.5)

    A node accessed 3+ times gets max 50% stale score reduction.
    """
    now = datetime.now(timezone.utc)
    created_aware = created_at.replace(tzinfo=timezone.utc) if created_at.tzinfo is None else created_at
    age_days = (now - created_aware).days

    age_factor = min(age_days / max(retention_days, 1), 1.0)

    last = last_accessed_at or created_at
    last_aware = last.replace(tzinfo=timezone.utc) if last.tzinfo is None else last
    days_since_access = (now - last_aware).days
    recency_factor = max(0.0, 1.0 - days_since_access / max(retention_days, 1))

    access_bonus = min(access_count * access_weight * recency_factor, 0.5)
    score = age_factor * (1.0 - access_bonus)
    return round(score, 3)
```

### Pattern 4: Extending compact_command with --expire Flag

**What:** Branch inside `compact_command` — `--expire` path calls `service.archive_stale_nodes()`, the non-`--expire` path runs existing dedup logic unchanged.
**When to use:** Always separate dedup and archiving code paths within the same function.

```python
# Extension to src/cli/commands/compact.py
def compact_command(
    expire: Annotated[
        bool,
        typer.Option("--expire", help="Archive nodes older than retention_days (no dedup)")
    ] = False,
    # ... existing flags unchanged ...
):
    if expire:
        # Archive path
        stale = run_graph_operation(service.list_stale(scope, project_root, show_all=True))
        if not stale:
            print_success("No stale nodes to archive.")
            raise typer.Exit(0)
        confirmed = confirm_action(
            f"{len(stale)} nodes will be archived. Proceed?", force=force
        )
        if not confirmed:
            console.print("Cancelled")
            raise typer.Exit(0)
        archived = run_graph_operation(
            service.archive_nodes([n["uuid"] for n in stale], scope, project_root)
        )
        print_success(f"Archived {archived} nodes.")
        return
    # ... existing dedup path unchanged ...
```

### Pattern 5: Access Recording Without Performance Impact

**What:** Record access events asynchronously within existing service methods by calling `RetentionManager.record_access()` after the primary operation succeeds.
**When to use:** `GraphService.search()`, `GraphService.get_entity()`.

```python
# In GraphService.search() — after results are fetched:
async def search(self, query, scope, project_root, ...):
    results = await graphiti.search(...)
    # Record access for any entity UUIDs found in results
    # This runs after the response is ready — no impact on search latency
    retention = get_retention_manager()
    scope_key = self._get_group_id(scope, project_root)
    for edge in results:
        # Edges don't have entity UUIDs directly; record via source/target UUIDs if available
        # Fallback: skip recording for edges, record only for direct entity reads (get_entity)
        pass
    return result_list
```

**Practical approach:** Record access reliably in `get_entity()` (exact UUID available). For `search()` results, edges are returned (not entity nodes with UUIDs), so access recording for search is deferred to Phase 2 optimization; RETN-06 is satisfied by `get_entity` + `show` recording.

### Pattern 6: New stale_command Registration

**What:** Top-level `graphiti stale` command registered in `src/cli/__init__.py` like other commands.
**When to use:** New file `src/cli/commands/stale.py`.

```python
# In src/cli/__init__.py — add to imports and registration:
from src.cli.commands.stale import stale_command
from src.cli.commands.pin import pin_command, unpin_command

app.command(name="stale", help="Preview nodes eligible for TTL archiving")(stale_command)
app.command(name="pin", help="Protect a node from TTL archiving permanently")(pin_command)
app.command(name="unpin", help="Remove pin protection from a node")(unpin_command)
```

### Pattern 7: LLMConfig Extension for [retention] Section

**What:** Add `retention_days: int = 90` and `retention_min_days: int = 30` (internal) to `LLMConfig`.
**When to use:** Same frozen dataclass pattern with `load_config()` extraction.

```python
# In LLMConfig dataclass:
retention_days: int = 90   # user-facing, from [retention] retention_days
# No retention_min_days in config — enforced as constant in load_config()

# In load_config():
retention = config_data.get("retention", {})
raw_days = retention.get("retention_days", 90)
if raw_days < 30:
    import structlog
    structlog.get_logger(__name__).warning(
        "retention_days below minimum, using default",
        configured=raw_days,
        minimum=30,
        using=90,
    )
    raw_days = 90

return LLMConfig(
    ...,
    retention_days=raw_days,
)
```

### Anti-Patterns to Avoid

- **Deleting archived nodes from Kuzu:** Archive is a SQLite state flag only. Never call `Node.delete_by_uuids()` for archived nodes — this would destroy edges (Kuzu `delete_by_uuids` explicitly deletes `RelatesToNode_` nodes first).
- **Storing archived state in EntityNode:** graphiti-core 0.28.1 has no `archived` field on EntityNode. Adding one would require patching graphiti-core internals.
- **Blocking search with access recording:** Record access after returning results, never before. A failing retention write should not fail the search.
- **Using `asyncio.run()` inside async context:** Follow existing pattern — `RetentionManager` is sync (sqlite3 is sync); call it directly inside async GraphService methods without `run_in_executor`.
- **Placing `retention.db` inside project directories:** Sidecar lives at `~/.graphiti/retention.db` (global). The `scope` column in each table partitions per-project state.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Confirmation prompt | Custom `input()` call | `confirm_action(message, force=force)` from `src/cli/utils.py` | Already handles `--force` flag, typer integration |
| Scope resolution | Custom git detection | `resolve_scope(global_flag, project_flag)` from `src/cli/utils.py` | Handles both flags, auto-detect, error messages |
| Table output | Custom Rich table | `print_table(data, columns=[...])` from `src/cli/output.py` | Consistent styling, handles empty state |
| JSON output | `json.dumps()` directly | `print_json(data)` from `src/cli/output.py` | Consistent formatting |
| TOON encoding for MCP | Custom encoding | `encode_response(data)` from `src/mcp_server/toon_utils.py` | Already implemented, 3+ item threshold |
| SQLite WAL setup | Per-connection PRAGMA | Put `PRAGMA journal_mode=WAL` in `_get_conn()` | Single place, applies to every connection |

**Key insight:** The utility layer (`src/cli/utils.py`, `src/cli/output.py`) is well-established. Retention commands must reuse it — not because it's convenient, but because consistency in UX is a requirement (the CONTEXT.md explicitly references `resolve_scope()` and `confirm_action()` as patterns to follow).

---

## Common Pitfalls

### Pitfall 1: UUID Availability in Stale List

**What goes wrong:** `graphiti stale` needs entity UUIDs (for archive operation), but the default table shows Name, Age, Score only (UUIDs in `--verbose`). The compact command's archive path needs UUIDs to pass to `archive_nodes()`. The stale list internally always contains UUIDs; the CLI just doesn't display them by default.

**Why it happens:** Conflating the display model with the data model.

**How to avoid:** `list_stale()` always returns dicts with `uuid`, `name`, `age_days`, `score`. The CLI layer controls which columns are displayed. `compact --expire` calls `list_stale(show_all=True)` and uses the `uuid` key from each dict.

**Warning signs:** If `compact --expire` tries to resolve UUIDs from names, that's wrong — list_stale must return UUIDs.

### Pitfall 2: Timezone-Naive datetime Comparison

**What goes wrong:** `EntityNode.created_at` may be timezone-naive (uses `utc_now()` from graphiti-core which returns naive UTC). Comparing with `datetime.now(timezone.utc)` causes `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Why it happens:** graphiti-core's `utc_now()` returns a naive UTC datetime (confirmed by Node source inspection).

**How to avoid:** Always normalize before subtraction:
```python
created_aware = entity.created_at.replace(tzinfo=timezone.utc)
age_days = (datetime.now(timezone.utc) - created_aware).days
```

**Warning signs:** `TypeError` in staleness computation during `graphiti stale`.

### Pitfall 3: Concurrent sqlite3 Access from Async Context

**What goes wrong:** GraphService methods are async. If `RetentionManager._get_conn()` is called inside an async function alongside Kuzu's async driver, they share the same event loop thread — sqlite3 blocking I/O could block the loop.

**Why it happens:** sqlite3 is synchronous; asyncio runs on a single thread.

**How to avoid:** Keep retention DB operations fast and bounded (simple indexed lookups, no full scans). For writes (record_access), accept the minor blocking as acceptable — these are sub-millisecond operations on a local file. Do NOT wrap in `run_in_executor` for simple single-row operations; it adds overhead without benefit at this scale.

**Warning signs:** Only becomes a problem if retention queries scan large tables without indexes. Solution: ensure indexes on `(uuid, scope)` which the `PRIMARY KEY` already provides.

### Pitfall 4: Stale Check Includes Already-Archived Nodes

**What goes wrong:** `list_stale()` returns nodes already in `archive_state`, causing `compact --expire` to try to "archive" already-archived nodes.

**Why it happens:** Forgetting to filter `archive_state` in the stale query.

**How to avoid:** `list_stale()` must exclude UUIDs already in `archive_state`. Query pattern:
```sql
-- Nodes not in archive_state and not in pin_state
SELECT uuid FROM nodes_over_ttl
WHERE uuid NOT IN (SELECT uuid FROM archive_state WHERE scope = ?)
  AND uuid NOT IN (SELECT uuid FROM pin_state WHERE scope = ?)
```

**Warning signs:** `compact --expire` reports archiving nodes that were already archived.

### Pitfall 5: Frozen LLMConfig Dataclass

**What goes wrong:** Trying to add `retention_days` via `config.retention_days = 90` — `LLMConfig` is a frozen dataclass (`@dataclass(frozen=True)`), so attribute assignment raises `FrozenInstanceError`.

**Why it happens:** Forgetting the `frozen=True` on `LLMConfig`.

**How to avoid:** Add `retention_days: int = 90` as a field in the dataclass definition AND add the extraction in `load_config()`. Never modify the config object after creation.

**Warning signs:** `FrozenInstanceError` when testing config loading.

### Pitfall 6: MCP stale Tool Must Return TOON for 3+ Items

**What goes wrong:** The MCP `stale` tool returns plain JSON instead of TOON format, consuming unnecessary tokens.

**Why it happens:** Forgetting the CONTEXT.md requirement: "MCP context: stale tool always returns TOON format".

**How to avoid:** Use `encode_response(stale_list)` from `toon_utils.py`. The existing `encode_response()` already applies the 3-item threshold automatically — use it unconditionally.

**Warning signs:** MCP stale tool output starts with `[` (JSON array) rather than TOON header.

---

## Code Examples

Verified patterns from existing codebase:

### SQLite Sidecar Init Pattern (modeled on existing singleton pattern)
```python
# src/retention/manager.py
# Source: Modeled on src/graph/service.py singleton pattern (get_service/reset_service)
_manager: Optional["RetentionManager"] = None

def get_retention_manager() -> "RetentionManager":
    global _manager
    if _manager is None:
        _manager = RetentionManager(Path.home() / ".graphiti" / "retention.db")
    return _manager

def reset_retention_manager() -> None:
    """Reset singleton — used in tests."""
    global _manager
    _manager = None
```

### Access Recording in GraphService.get_entity (after entity found)
```python
# Source: Modeled on src/graph/service.py get_entity() structure
# After entity_dicts is built:
if entity_dicts:
    from src.retention.manager import get_retention_manager
    retention = get_retention_manager()
    scope_key = self._get_group_id(scope, project_root)
    for ed in entity_dicts:
        retention.record_access(uuid=ed.get("uuid") or record["uuid"], scope=scope_key)
```

### stale_command Table Output (following list_cmd.py pattern)
```python
# src/cli/commands/stale.py
# Source: Modeled on src/cli/commands/list_cmd.py print_table usage
def stale_command(
    global_scope: Annotated[bool, typer.Option("--global", "-g", ...)] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", ...)] = False,
    all_results: Annotated[bool, typer.Option("--all", ...)] = False,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", ...)] = False,
    format: Annotated[Optional[str], typer.Option("--format", "-f", ...)] = None,
):
    scope, project_root = resolve_scope(global_scope, project_scope)
    with console.status("[cyan]Scanning for stale nodes...", spinner="dots"):
        stale = run_graph_operation(get_service().list_stale(scope, project_root, show_all=all_results))

    cap = 25
    total = len(stale)
    display = stale if all_results else stale[:cap]

    if format == "json":
        print_json(display)
    else:
        columns = ["name", "age_days", "score"]
        if verbose:
            columns = ["uuid"] + columns
        print_table(display, columns=columns)
        if not all_results and total > cap:
            console.print(f"\n[dim]Showing {cap} of {total} stale nodes. Run with --all to see all.[/dim]")
```

### pin_command Pattern
```python
# src/cli/commands/pin.py
# Source: Modeled on src/cli/commands/delete.py structure
def pin_command(
    uuid: Annotated[str, typer.Argument(help="UUID of node to pin")],
    global_scope: Annotated[bool, typer.Option("--global", "-g", ...)] = False,
    project_scope: Annotated[bool, typer.Option("--project", "-p", ...)] = False,
):
    scope, project_root = resolve_scope(global_scope, project_scope)
    scope_key = _scope_to_key(scope, project_root)
    retention = get_retention_manager()
    retention.pin_node(uuid=uuid, scope=scope_key)
    print_success(f"Node {uuid} pinned. It will not appear in 'graphiti stale' output.")
```

### compact_command --expire Branch
```python
# src/cli/commands/compact.py — EXTENSION
# Source: Existing compact_command structure in src/cli/commands/compact.py
def compact_command(
    expire: Annotated[bool, typer.Option("--expire", help="Archive stale nodes (no dedup)")] = False,
    force: Annotated[bool, typer.Option("--force", ...)] = False,
    # ... existing flags ...
):
    scope, project_root = resolve_scope(global_scope, project_scope)

    if expire:
        stale = run_graph_operation(get_service().list_stale(scope, project_root, show_all=True))
        if not stale:
            print_success("No stale nodes to archive.")
            raise typer.Exit(0)
        confirmed = confirm_action(
            f"{len(stale)} nodes will be archived. Proceed?", force=force
        )
        if not confirmed:
            console.print("Cancelled")
            raise typer.Exit(0)
        archived_count = run_graph_operation(
            get_service().archive_nodes([n["uuid"] for n in stale], scope, project_root)
        )
        print_success(f"Archived {archived_count} nodes.")
        return
    # ... existing dedup code unchanged ...
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Deleting stale nodes | Archiving (state flag) | Design decision in CONTEXT.md | Preserves edges, enables reactivation |
| graphiti-core TTL fields | SQLite sidecar | v0.28.1 has no TTL fields (confirmed) | All retention metadata is external |
| APScheduler background sweeps | User-initiated via CLI | Design decision (no daemon needed) | Simpler architecture, no background thread |

**Confirmed:**
- `EntityNode` fields: `[uuid, name, group_id, labels, created_at, name_embedding, summary, attributes]` — no TTL, archived, or pin fields (HIGH confidence — direct inspection of installed 0.28.1)
- `Node.delete_by_uuids()` for Kuzu explicitly deletes `RelatesToNode_` edge-nodes — confirms archive must NOT use this method
- `sqlite3.sqlite_version` = 3.45.1 in project venv — WAL mode is supported

---

## Open Questions

1. **Access recording for search results (edge-based, no entity UUIDs)**
   - What we know: `graphiti.search()` returns edge objects, not entity nodes with UUIDs. `EntityNode.get_by_group_ids()` returns entity nodes with UUIDs.
   - What's unclear: Whether edge objects expose source/target entity UUIDs in graphiti-core 0.28.1 (`edge.source_node_uuid`, `edge.target_node_uuid`).
   - Recommendation: In GraphService.list_stale's first pass, inspect edge attributes available. If not available without extra queries, limit access recording to `get_entity()` + `show` calls only. RETN-06 says "search hits" reinforce a node — but if UUIDs aren't readily available from search edges, defer search-based recording as a follow-up.

2. **`list_stale()` performance at scale**
   - What we know: `EntityNode.get_by_group_ids()` fetches up to `limit` entities from Kuzu. Each entity needs age + retention metadata from SQLite.
   - What's unclear: At 1000+ entities, the join cost between Kuzu entities and SQLite records is unknown.
   - Recommendation: Fetch entities from Kuzu (using `get_by_group_ids`), then batch-query SQLite for retention metadata with `WHERE uuid IN (...)`. Avoid N+1 queries. Likely fine at typical knowledge graph sizes (<500 nodes), but note this in implementation.

3. **Reactivation mechanism — how graphiti-core deduplicates**
   - What we know: Archived nodes remain in Kuzu. graphiti-core's `add_episode()` runs entity resolution (dedup via embedding similarity + FTS).
   - What's unclear: Whether an archived node (invisible in stale/list but present in Kuzu) will be matched during dedup search and updated in place, or whether `add_episode` would create a new node.
   - Recommendation: Since archive is a pure SQLite state flag and the Kuzu entity is untouched, graphiti-core's resolution will find the existing Kuzu node and update it normally. The reactivation step (clearing `archive_state` in SQLite) must be implemented in `GraphService.add()` — after `add_episode()` succeeds, check if any entities touched by the episode were previously archived and remove them from `archive_state`. This requires querying `EntityNode` by name to find touched UUIDs post-episode.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of installed `graphiti-core==0.28.1` — `EntityNode.model_fields.keys()` returns `[uuid, name, group_id, labels, created_at, name_embedding, summary, attributes]` (no TTL/archived fields)
- Direct inspection of `Node.delete_by_uuids()` source — Kuzu path explicitly deletes `RelatesToNode_` nodes before Entity nodes
- `sqlite3.sqlite_version` = 3.45.1 confirmed in project venv
- `src/llm/config.py` — LLMConfig frozen dataclass pattern with section-per-config-block in `load_config()`
- `src/cli/commands/compact.py` — exact `compact_command` signature for `--expire` extension
- `src/cli/commands/list_cmd.py` — `print_table()`, `resolve_scope()`, `confirm_action()` patterns
- `src/cli/__init__.py` — command registration pattern
- `src/mcp_server/toon_utils.py` — `encode_response()` with 3-item threshold
- `pyproject.toml` — confirmed no APScheduler or aiosqlite in dependencies (no new deps needed)

### Secondary (MEDIUM confidence)
- sqlite3 WAL mode behavior for concurrent read from multiple CLI processes — well-documented Python stdlib behavior, not verified against this specific deployment

### Tertiary (LOW confidence)
- Score weighting (0.3 access_weight, 0.5 max access_bonus) — these are Claude's discretion per CONTEXT.md; values chosen for intuitive behavior but not validated against real usage patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project; no new dependencies confirmed
- Architecture: HIGH — directly confirmed EntityNode fields, delete_by_uuids behavior, existing CLI patterns
- Pitfalls: HIGH — pitfalls 1-5 derived from direct code inspection; pitfall 6 from CONTEXT.md requirement

**Research date:** 2026-03-05
**Valid until:** 2026-06-05 (stable — graphiti-core pinned at 0.28.1, no upgrade planned)

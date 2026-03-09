# Phase 9: Smart Retention - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Knowledge graph freshness management — nodes that exceed `retention_days` without access are **archived** (not deleted), frequently-accessed nodes persist longer, and pinned nodes are permanently protected. The full graph history is preserved. `graphiti stale` previews what would be archived. `compact --expire` performs the archiving.

</domain>

<decisions>
## Implementation Decisions

### Archive semantics (critical pivot from original spec)
- Stale nodes are **archived** (state flag), never deleted
- Archived nodes are **invisible by default** in search, list, and stale output
- Archived nodes are **included in graphiti-core deduplication** — when a new episode matches an archived node, it reactivates naturally without creating a duplicate
- No explicit `restore` command — reactivation happens automatically via new relevant content
- Edges connected to archived nodes are **preserved intact** — full relationship history survives

### `graphiti stale` command
- New top-level command (not a subcommand of compact)
- Default output: rich table with columns — **Name, Age (days), Score**
- UUID shown only with `--verbose` flag
- Default cap: **25 rows**, sorted worst-first (oldest + lowest score)
- Summary line always shown: e.g. "Showing 25 of 47 stale nodes. Run with --all to see all."
- `--all` flag to remove the cap
- Scope-aware: `--global` / `--project` flags, defaults to project scope inside git repo
- **MCP context**: stale tool always returns TOON format (compact wire encoding via existing `toon_utils.py`); CLI output stays human-readable

### Reinforcement scoring
- Access events that reinforce a node (reset/extend TTL): search hits, `graphiti show`, MCP tool reads
- Scoring adjusts position in the stale list (worst-first ordering), not hard eligibility
- The TTL window (`retention_days`) is the primary gate — a node is only stale if it exceeds that age
- Scoring internals (weights, decay rate) are Claude's discretion

### Pin / unpin
- `graphiti pin <uuid>` — permanently protects a node from TTL archiving; pinned nodes never appear in `graphiti stale` output
- `graphiti unpin <uuid>` — removes pin protection; node becomes eligible for TTL archiving again
- Pin state stored in the SQLite sidecar (`~/.graphiti/retention.db`) alongside access timestamps

### Retention config (`llm.toml`)
- New `[retention]` section, consistent with existing `[cloud]`, `[local]`, `[embeddings]` sections
- Single user-facing knob: `retention_days` (default: 90)
- Minimum enforced value: **30 days** — values below 30 are rejected with a warning and fall back to default
- All other scoring parameters are internal — Claude's discretion

### `compact --expire`
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

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/cli/commands/compact.py` — existing `compact_command` with `--force`, `--global`, `--project`, `--format json`; `--expire` extends this
- `src/mcp_server/toon_utils.py` — TOON encoding already implemented; stale MCP tool reuses it
- `src/graph/service.py` — `compact()`, `get_stats()`, `list_entities()` exist; retention adds `list_stale()`, `archive_nodes()`, `pin_node()`, `unpin_node()`
- `src/llm/config.py` — `LLMConfig` dataclass with `load_config()`; add `retention_days: int = 90` under new `[retention]` section
- `src/cli/utils.py` — `resolve_scope()`, `confirm_action()` — reuse for stale and compact --expire

### Established Patterns
- All CLI commands use `resolve_scope(global_scope, project_scope)` for scope handling
- `confirm_action(message, force=force)` pattern for destructive ops
- `--format json` on commands that output data — stale gets this too
- structlog everywhere except `src/mcp_server/` (uses stdlib logging to stderr)

### Integration Points
- New `graphiti stale` command registered in `src/cli/__init__.py` alongside existing commands
- `compact_command` in `src/cli/commands/compact.py` gets `--expire` flag branch
- SQLite sidecar (`~/.graphiti/retention.db`) is new infrastructure — no existing sidecar pattern
- graphiti-core `EntityNode` has no `archived` or `pin` fields — all retention metadata lives in `retention.db`, joined by UUID at query time

</code_context>

<specifics>
## Specific Ideas

- Archive is a **state flag in the SQLite sidecar**, not a field on EntityNode — graphiti-core 0.28.1 has no TTL/archived fields, so all retention metadata lives externally
- Archived nodes must be reachable during graphiti-core's entity resolution (deduplication) so re-relevance reactivates rather than duplicates
- TOON output for the MCP stale tool follows the existing split-context pattern in `mcp_server/tools.py`

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-smart-retention*
*Context gathered: 2026-03-05*

# Milestones

## v2.0 Rebuild (Shipped: 2026-04-07)

**Phases completed:** 12 phases, 42 plans, 55 tasks

**Key accomplishments:**

- real-ladybug==0.15.1 installed and spike confirmed: LadybugDriver must be vendored locally (~280 lines); kuzu and real_ladybug cannot coexist in same process; test infrastructure scaffolded for Wave 2
- Vendored LadybugDriver (~200 lines) wrapping real_ladybug AsyncConnection; GraphManager rewritten with zero Kuzu imports or workarounds; paths renamed .kuzu -> .lbdb; kuzu removed from deps
- 3 direct kuzu.Database/Connection methods in service.py rewritten to driver.execute_query() — service.py now has 0 import kuzu occurrences; same dict return shapes; all 11 retention tests pass
- BackendConfig fields (backend_type/backend_uri) added to LLMConfig; _make_driver() routes to LadybugDriver or Neo4jDriver; fail-fast Neo4j check; Backend row in health output; docker-compose.neo4j.yml created; graphiti config init generates llm.toml with commented [backend] block
- Post-commit hook installer removed (3 functions + callers); 2 LadybugDB integration tests enabled and passing; full suite 299 passed 2 skipped; kuzu fully purged from src/; human smoke test checkpoint reached
- make_llm_client() and make_embedder() factories in adapters.py route graphiti-core LLM calls to OpenAIGenericClient or OllamaLLMClient based on URL-detected SDK, with GraphService wired via load_config()
- Provider health rows in `graphiti health` (Provider/Embed/Fallback with OK/UNREACHABLE) and fail-fast startup gate via validate_provider_startup() hooked into main_callback()
- 1. [Rule 1 - Bug] Additional source files not in plan's file list had .graphiti references
- Five new read-only GraphService methods (list_episodes, get_episode_detail, get_time_series_counts, get_top_connected_entities, get_retention_summary) using driver.execute_query() to unblock Plan 03 API routes
- Task 1 — Scaffold:
- Recharts Dashboard (9 charts) and Sigma.js WebGL graph renderer with graphology data model, FA2 physics, and episode diamond toggle
- shadcn Table-based Entities/Relations/Episodes tabs with slide-in DetailPanel featuring breadcrumb in-place navigation and 3 content modes (entity/edge/episode)
- Task 1 — Search results page:
- graphiti memory search CLI command and global hooks install wiring added: memory_app Typer sub-app with BM25+semantic search, hooks install now writes all 5 entries to ~/.claude/settings.json
- 16 pytest tests covering MEM-01 through MEM-05 via subprocess hook invocation; E2E human approval confirmed ~/.claude/settings.json has all 5 hook types registered
- Typer app renamed from graphiti to recall with recall/rc entrypoints; CLI surface collapsed from 20 to 10 public + 1 hidden commands; init_cmd.py and note_cmd.py created
- recall list absorbs show/stale/compact/queue via 4 new flags; recall search silently auto-syncs git before every query
- 11 obsolete CLI command files deleted; session_start.py upgraded to call GitIndexer directly (no subprocess); all hook manager/installer references updated from graphiti to recall binary
- Phase 16 CLI rename test suite: 16 tests covering recall rename (CLI-01), 10-command surface (CLI-02), and auto-sync in search (CLI-03) with 15 pre-existing test regressions fixed
- 1. [Rule 1 - Bug] Updated stale test assertion for binary name
- MEM-03 VERIFICATION.md reference corrected from graphiti memory search to recall search; stale Wave 3 skip removed from test_neo4j_unreachable_raises_on_init with test body updated to current GraphManager API — 4 passed, 0 skipped
- One-liner:
- One-liner:
- 1. [Rule 1 - Bug] Fixed `self.graph_manager` → `self._graph_manager` in list_entities_readonly() and list_edges()
- Multi-select retention filter Combobox in Entities toolbar, dynamic retention badges, Sigma.js colored border rings on entity nodes, and stacked GraphLegend retention panel — all wired to retention_status from 19-01 API
- 5 end-to-end integration tests verifying retention_status flows from service through /api/graph API to Sigma.js node shape, with full suite green (395/397 tests pass)
- One-liner:
- Batch git indexing via single `claude -p` call per 10 commits with `asyncio.Semaphore(3)` parallelism, replacing per-commit sequential Ollama extraction
- FTS keyword search replacing vector-only context injection: 3-layer progressive disclosure using QUERY_FTS_INDEX Cypher + TOON encoding for ~40% token savings in inject_context.py
- One-liner:
- 24-test coverage of claude-cli batch extraction, FTS-first context injection, and session_stop claude wiring across 3 new test files
- One-liner:
- One-liner:
- One-liner:
- Phase 12 (DB Migration):
- One-liner:
- One-liner:

---

## v1.1 Advanced Features (Shipped: 2026-03-09)

**Phases completed:** 4 phases (9–11.1), 14 plans | **Codebase delta:** ~14,585 lines Python + 341 lines TypeScript (UI) | 92 commits
**Git range:** v1.0 → 1a4a745 | **Timeline:** 2026-03-01 → 2026-03-09 (8 days)

**Key accomplishments:**

1. Smart retention (Phase 9): TTL-based 90-day expiry with reinforcement scoring — `graphiti stale` previews candidates, `graphiti compact --expire` deletes stale nodes with no dangling edges, `graphiti pin/unpin` protects critical knowledge permanently
2. Configurable capture modes (Phase 10): `decisions-only` (narrow, default) and `decisions-and-patterns` (broad) selectable via `[capture] mode` in `llm.toml`; security sanitization gate is unconditional regardless of mode
3. Graph UI (Phase 11): `graphiti ui` launches FastAPI + pre-built Next.js static export at `http://localhost:8765` — ForceGraph2D visualization, entity type color legend, node sidebar with retention metadata, scope toggle (project/global), read-only Kuzu mount
4. Retention wiring gap closure (Phase 11.1): 4 integration gaps from audit closed — retention fields (access_count, last_accessed_at, pinned, archived) surfaced in Graph UI sidebar and canvas filters; ui.port key normalized in config CLI

---

## v1.0 MVP (Shipped: 2026-03-01)

**Phases completed:** 18 phases (Phases 1–8.9), 62 plans, 27 days (2026-02-02 → 2026-03-01)
**Codebase:** 44,453 lines Python | 247 commits

**Key accomplishments:**

1. Persistent Kuzu dual-scope knowledge graph: global preferences at `~/.graphiti/global/` and per-project isolation at `.graphiti/` — survives restarts, supports graph queries and temporal relationships
2. Defense-in-depth security filtering: file exclusions (.env*, *.key, *secret*), high-entropy string detection (AWS keys, GitHub tokens, JWTs), pre-commit validation hook, complete audit log
3. Hybrid cloud/local Ollama LLM: cloud-first with quota tracking and graceful fallback hierarchy — system never completely fails, always indicates active provider
4. CLI-first architecture with 16+ commands (`graphiti`/`gk`): add, search, list, show, delete, summarize, compact, config, health, hooks, index, queue, capture — with JSON output mode
5. Automatic knowledge capture: git post-commit hook + async SQLiteAckQueue + BackgroundWorker + conversation hooks for Claude Code — all non-blocking, under 100ms hook overhead
6. Local-first git history indexing: `graphiti index` builds Kuzu graph from commit logs/diffs on demand; `.graphiti/` fully gitignored — no merge conflicts, no secrets committed
7. MCP server with 11 tools for Claude Code: stdio transport, context injection on session start (stale-index detection, 8K token budget), TOON-encoded responses

**Git range:** d8c909c (project init) → a61485c (Phase 8.9 complete)

---

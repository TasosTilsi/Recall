# Pitfalls Research

**Domain:** Python CLI knowledge graph tool — v1.1 feature additions (retention, capture modes, UI, multi-provider LLM)
**Researched:** 2026-03-01
**Confidence:** HIGH — all critical pitfalls verified against codebase inspection, graphiti-core source, and upstream GitHub issues

---

## Critical Pitfalls

### Pitfall 1: Node.delete_by_uuids Leaves Orphaned RelatesToNode_ and Episodic References

**What goes wrong:**
TTL-based retention deletes `Entity` nodes using `Node.delete_by_uuids(driver, uuids)` (the pattern already used in `service.delete_entities()` and `service.compact()`). In the Kuzu backend, `RelatesToNode_` nodes act as reified edges — they are separate graph nodes connecting `Entity` pairs. Deleting an `Entity` without first deleting its associated `RelatesToNode_` nodes leaves orphaned edge-nodes in the graph. Graphiti also has a confirmed upstream bug (issue #1083) where `remove_episode()` leaves `Entity` nodes with no `MENTIONS` relationships, meaning a TTL pass that only queries for `last_accessed` timestamps will never enumerate these orphans.

**Why it happens:**
Two distinct problems compound:
1. Kuzu uses reified edges (`RelatesToNode_`) that are not automatically cascade-deleted when their target entities are deleted. The deletion responsibility falls on the caller.
2. `Node.delete_by_uuids()` deletes the `Entity` node rows but does not run a companion `DETACH DELETE` or pre-delete of associated edge nodes — that logic would need to be added explicitly.
3. The upstream orphan-entity bug (open PR #1130, unmerged as of 2026-03-01) means the graph already accumulates entities with zero MENTIONS edges; retention queries filtering by `last_accessed` won't see these.

**How to avoid:**
For TTL deletion, issue two queries before deleting Entity nodes:
1. `MATCH (n:Entity {uuid: $uuid})-[:RELATES_TO]->(e:RelatesToNode_) DETACH DELETE e` — clear edge nodes first.
2. Then `Node.delete_by_uuids(driver, uuids)` for the entity itself.
Additionally, run a sweep for zero-MENTIONS orphans after every retention pass: `MATCH (n:Entity) WHERE NOT EXISTS { (:Episodic)-[:MENTIONS]->(n) } RETURN n.uuid` and delete those too.
Wrap both in a single transaction (Kuzu supports `BEGIN TRANSACTION`) to avoid partial-delete corruption.

**Warning signs:**
- `graphiti stats` shows `entity_count` decreasing but `relationship_count` stays flat or grows after retention runs.
- `RelatesToNode_` count query returns more nodes than `entity_count * avg_degree` suggests.
- Repeated `compact()` calls don't reduce graph size significantly — orphaned edge-nodes bloat the DB.

**Phase to address:** Smart Retention (Phase 9) — retention is the first feature to delete nodes at scale. Build deletion cleanup into the retention sweep from day one. Do not defer orphan cleanup to a later compaction step.

---

### Pitfall 2: Kuzu Database Is Archived — Upgrading graphiti-core May Force a Backend Migration

**What goes wrong:**
KuzuDB was archived in October 2025 and is no longer actively maintained. graphiti-core (issue #1132, opened 2026-01-02) opened discussion of switching to LadybugDB (a Kuzu fork) or another backend. If graphiti-core releases a version that drops the `graphiti-core[kuzu]` extra or changes the `KuzuDriver` interface, upgrading to fix other bugs (e.g., the orphan entity bug #1083) could require migrating the entire storage backend.

**Why it happens:**
The project depends on `graphiti-core[kuzu]==0.28.1` pinned exactly. Three existing workarounds are tightly coupled to this version's internal structure (`driver._database`, `build_indices_and_constraints()` being a no-op, `get_fulltext_indices(GraphProvider.KUZU)`). Upgrading to address graphiti-core bugs risks breaking these workarounds silently.

**How to avoid:**
- Keep graphiti-core pinned at `==0.28.1` throughout v1.1. Do not bump the version without a dedicated research spike.
- If a bump is needed, run the full test suite and explicitly verify: (a) `driver._database` attribute still missing (if fixed upstream, remove workaround), (b) FTS indices still not created by `build_indices_and_constraints()` (if fixed, remove manual `_create_fts_indices()`), (c) `get_fulltext_indices(GraphProvider.KUZU)` query strings still match the installed Kuzu schema.
- Track the upstream issue #1132. If graphiti-core drops Kuzu in a future release, plan a migration to FalkorDB (official migration guide exists) as a dedicated milestone, not a mid-feature change.

**Warning signs:**
- `pip install` dependency resolver tries to upgrade graphiti-core when installing a new provider library (e.g., `openai`, `anthropic`). Pin hard in `pyproject.toml`.
- `build_indices_and_constraints()` starts creating indices where it previously did nothing — workaround may now run twice, causing harmless but confusing errors.
- `KuzuDriver` constructor signature changes — `KuzuDriver(db=str(db_path))` pattern breaks.

**Phase to address:** Multi-Provider LLM (Phase 11) — that phase adds new Python dependencies (openai, anthropic). Dependency resolver must be guarded. Add explicit check: `assert graphiti_core.__version__ == "0.28.1"` in test suite startup before implementing multi-provider.

---

### Pitfall 3: OllamaLLMClient Is the Only Concrete Adapter — Multi-Provider Abstraction Breaks graphiti-core Wiring

**What goes wrong:**
`GraphService.__init__()` hardcodes `OllamaLLMClient()` and `OllamaEmbedder()` as the adapters wired to `Graphiti(graph_driver=driver, llm_client=self._llm_client, embedder=self._embedder, ...)`. Adding OpenAI, Anthropic, or Groq providers requires either (a) creating parallel adapter classes per provider, or (b) making `OllamaLLMClient` a routing hub that forwards to the selected provider. If done naively — e.g., by creating `OpenAILLMClient` that directly wraps `openai.OpenAI()` — developers discover that graphiti-core's `LLMClient` ABC has internal retry logic, caching, and prompt injection hooks that differ subtly from the Ollama path, causing structured output parsing failures for non-Ollama providers.

The known upstream issue: `format=response_model.model_json_schema()` passed to Ollama for constrained generation is stripped for cloud calls in `chat()` (line 440 of `client.py`). New providers that natively support structured output (OpenAI's `response_format=`, Anthropic's tool-use JSON mode) need their own stripping and injection logic — the `_strip_schema_suffix()` and `_inject_example()` methods in `OllamaLLMClient` are only calibrated for Ollama behavior.

**Why it happens:**
The `OllamaLLMClient._generate_response()` method has Ollama-specific logic baked in:
- `format=` kwarg injection for constrained generation
- `_strip_schema_suffix()` that matches graphiti-core's exact prompt suffix format
- `_inject_example()` for cloud models that ignore `format=`
- `_normalize_field_names()` for dot-prefix key normalization (cloud Ollama-specific behavior)

None of these apply cleanly to OpenAI or Anthropic SDKs, which have entirely different structured output APIs (`response_format={"type": "json_schema", ...}` for OpenAI; tool-use JSON extraction for Anthropic).

**How to avoid:**
Implement multi-provider as a new `ProviderFactory` class that selects and instantiates the correct adapter at startup based on `[provider]` section in `llm.toml`. Each provider gets its own concrete adapter class (e.g., `OpenAILLMClient`, `AnthropicLLMClient`) inheriting from graphiti-core's `LLMClient` ABC — not from `OllamaLLMClient`. The existing `OllamaLLMClient` is not modified; it remains the default path. `GraphService._create_adapters()` is refactored to call `ProviderFactory.create()` instead of directly instantiating Ollama adapters. This is surgical — no existing code path changes.

**Warning signs:**
- Structured output calls return `{"content": raw_text}` fallback instead of parsed Pydantic dicts — indicates the new provider's response isn't being parsed correctly.
- `validate_response_model` errors in graphiti-core logs — means the adapter returned the wrong dict structure.
- Embedding calls fail with `NotImplementedError` — a new provider's `EmbedderClient` subclass forgot to implement `create_batch()`.

**Phase to address:** Multi-Provider LLM (Phase 11) — introduce `ProviderFactory` and keep `OllamaLLMClient` untouched. New adapters are additions, not modifications to existing adapter code.

---

### Pitfall 4: TTL Retention Deletes Nodes That the Background Queue Has Pending Episodes For

**What goes wrong:**
The background queue (`SQLiteAckQueue` + `BackgroundWorker`) processes capture jobs asynchronously. A node for "Python async patterns" might be created at `T=0`, a new episode captured at `T=80 days` (just before TTL), and the processing job queued but not yet executed when the TTL sweep at `T=90 days` deletes the node. The queue job then runs and calls `graphiti.add_episode()`, which tries to resolve or merge the entity — but the entity was deleted 30 seconds ago. This causes a silent partial write: the episode body is stored but the entity cannot be re-linked correctly, producing a dangling episodic node.

**Why it happens:**
The queue (`src/queue/`) is decoupled from the graph layer by design — jobs are CLI replays or structured payloads, not transactions. There is no lock or coordination mechanism between the retention sweep and the queue processing. The retention sweep runs synchronously inside `asyncio.run()`, while the queue is processed in a background thread by `BackgroundWorker`. These run independently.

**How to avoid:**
Use a pessimistic window: when computing the 90-day TTL, subtract the queue's maximum item TTL (default 24 hours, configured as `queue_item_ttl_hours`). Only delete nodes with `last_accessed < now - 90days - 24hours`. This guarantees any queued episode for a node will have either been processed or expired from the queue before the node is deleted.
Additionally: retention should run as a scheduled CLI command (`graphiti retain`), not as part of any hot path. Schedule it for off-hours (e.g., cron at 3am) so it doesn't race with normal capture traffic.

**Warning signs:**
- `graphiti stats` shows `episode_count` growing while `entity_count` is stable or declining — episodic nodes with no linked entities accumulating.
- Background worker logs show `capture_git_commits_complete` followed by graphiti errors about missing entities.
- Dead letter queue fills up with `capture_git_commits` jobs after a retention run.

**Phase to address:** Smart Retention (Phase 9) — the TTL window calculation must account for queue depth from the start. Do not implement retention without reviewing the queue TTL config.

---

### Pitfall 5: MCP Server stdio Transport Gets Corrupted by a Localhost UI Server on the Same Process

**What goes wrong:**
The MCP server uses FastMCP with stdio transport — Claude Code sends JSON-RPC over stdout, the MCP server reads from stdin. Any write to stdout from the MCP server process corrupts the protocol. If `graphiti ui` starts a web server (FastAPI + Uvicorn) in the same process as the MCP server, there are two failure modes: (a) Uvicorn's startup banner and access logs write to stdout if not explicitly redirected, and (b) the `signal.SIGTERM` handler from Uvicorn conflicts with FastMCP's own shutdown handler, causing the MCP server to exit mid-session when the UI server is stopped.

**Why it happens:**
Python's Uvicorn binds log handlers at startup. The default Uvicorn config writes access logs to stdout unless explicitly set to stderr. When `graphiti ui` is implemented as a subcommand of the Typer CLI, developers may be tempted to start the web server in the same process for simplicity. The MCP server (`graphiti mcp serve`) already uses `sys.executable` to resolve the CLI binary path, meaning MCP tools run as subprocess calls — but if the UI server is started inside the MCP server's process tree (e.g., via a new MCP tool `graphiti_ui`), the stdio corruption risk is immediate.

**How to avoid:**
The UI server MUST run as a fully separate process: `graphiti ui` starts Uvicorn as a subprocess with `stdout=subprocess.DEVNULL` and `stderr` routed to a log file. The UI command is a standalone Typer subcommand that spawns Uvicorn via `subprocess.Popen(..., start_new_session=True)` — the same pattern used by `graphiti_capture()` in `tools.py`. Never embed Uvicorn in-process with MCP server. Use port 7437 (or configurable) with explicit check for port availability before binding.

**Warning signs:**
- Claude Code MCP tool calls return `json.JSONDecodeError` on responses that look like HTTP access log entries.
- `graphiti mcp serve` exits unexpectedly when `graphiti ui` is stopped.
- MCP server logs contain Uvicorn startup banners mixed with JSON-RPC frames.

**Phase to address:** Graph UI (Phase 10) — the `graphiti ui` command architecture must be subprocess-based from the design, not refactored after the fact. This is a non-negotiable constraint: never inline the UI server.

---

### Pitfall 6: Configurable Capture Modes Bypass the Security Filter If Mode-Checking Happens Before Sanitization

**What goes wrong:**
The current capture pipeline always runs `sanitize_content()` before any LLM call (enforced in `summarizer.py` and `service.add()`). Configurable capture modes (decisions-only vs decisions-and-patterns) require filtering content at the capture stage — deciding what content to capture at all. If the mode check is implemented as "filter before sanitize" (i.e., check if content matches the capture mode, then only sanitize what passes), a bug in the mode filter could allow raw content with secrets to bypass the security gate. The "decisions-and-patterns" mode captures more content including code patterns — higher surface area for accidental secret exposure.

**Why it happens:**
Developers implement the mode filter as a pre-filter to avoid wasting sanitizer cycles on content that won't be captured anyway. The optimization is logical but inverts the security invariant: sanitize-then-filter is safe, filter-then-sanitize is risky.

**How to avoid:**
Lock the order: sanitize first, filter mode second — always. Even in decisions-only mode, the security gate runs on all candidate content before the mode filter decides whether to keep or discard it. Add a comment in `summarizer.py` and `capture/conversation.py` marking this order as a security invariant. Write a test that passes a string with a secret through the decisions-only filter path and asserts the secret is `[REDACTED]` in anything stored.

**Warning signs:**
- A code review shows `if mode == "decisions_only": ... else: sanitize_content(...)` branching — the sanitization is not unconditional.
- Test coverage for capture mode changes doesn't include a secret-containing content fixture.
- `git diff` after adding mode support shows changes to `src/security/` — the security layer should not need changes for capture mode.

**Phase to address:** Configurable Capture Modes (Phase 9 or Phase 10) — add an explicit integration test: `test_capture_modes_always_sanitize_before_filter()` as a gating requirement before mode selection ships.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| `process_queue()` returning `(0, 0)` | Unblocked Phase 5 | Retention phases can't inspect queue health before deciding to delete | Fix before retention ships — retention needs real queue metrics |
| `asyncio.run()` in `GraphManager.reset_project()` called from sync context | Avoids async threading complexity | Crashes if called from within a running event loop (e.g., from an async test) | Acceptable until async tests are added; fix in Phase 10 at latest |
| `service._get_graphiti()` called as a private method by `indexer.py` | Avoids duplicating initialization logic | Fragile — any rename of `_get_graphiti` silently breaks indexer | Acceptable as tech debt; document with a `# FRAGILE` comment |
| `GraphSelector` dead export in `src/storage/` | None — it's dead code | Confuses future developers adding providers | Remove during multi-provider phase as cleanup |
| Hardcoded `OllamaLLMClient()` in `GraphService.__init__()` | Simple, no config needed | Multi-provider requires refactoring the constructor | Acceptable until Phase 11; document the coupling explicitly |
| Retention scoring stored as metadata vs. separate tracking table | Simpler — no new table | If graphiti-core changes node schema, retention metadata is lost on upgrade | Use a separate SQLite tracking file alongside the graph DB, not node attributes |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Kuzu `DETACH DELETE` | Using `DELETE` without `DETACH` on nodes that have edges — Kuzu raises a runtime error | Always use `DETACH DELETE` for node deletion, or delete edges first then `DELETE` node |
| graphiti-core `LLMClient` ABC | Subclassing and forgetting to implement `_generate_response` (async, not `generate`) | Check the ABC: the required method is `_generate_response(messages, response_model, max_tokens, model_size)` |
| Anthropic embeddings | Anthropic does not offer an embedding API — pairing `AnthropicLLMClient` with `AnthropicEmbedder` is impossible | For Anthropic LLM provider, keep `OllamaEmbedder` for embeddings; embeddings remain local-only |
| OpenAI structured output | Passing `format=json_schema_dict` (Ollama pattern) to OpenAI SDK — OpenAI uses `response_format={"type": "json_schema", "json_schema": {...}}` | New provider adapters must implement provider-specific structured output, not reuse the Ollama `format=` pattern |
| FastAPI static file serving | `StaticFiles` mounts must be added after all API routes — mounting at "/" too early shadows all routes | Mount static files last; use `app.mount("/", StaticFiles(...), name="static")` as the final line |
| SQLiteAckQueue multithreading | Creating `SQLiteAckQueue` with `multithreading=False` (default) when accessing from background threads | Always set `multithreading=True` when queue is accessed from worker threads (existing decision, must be preserved for new retention use) |
| Uvicorn in background thread | `uvicorn.run()` installs its own signal handlers which override the main thread's handlers | Use `uvicorn.Server` + `uvicorn.Config` directly with `server.serve()` in an asyncio task, or use subprocess — never `uvicorn.run()` in a secondary thread |
| graphiti-core `Graphiti` constructor | Passing `llm_client=openai_client` where `openai_client` is a raw `openai.OpenAI()` object — graphiti-core expects an `LLMClient` subclass | Always wrap raw provider clients in a graphiti-core-compatible adapter class |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Retention sweep doing N+1 Kuzu queries (one `last_accessed` query per node) | Retention takes minutes for a 500-node graph | Batch query: `MATCH (n:Entity) WHERE n.last_accessed < $cutoff RETURN n.uuid` — single query returns all expired UUIDs | At 100+ nodes with per-node queries |
| Graph visualization loading all nodes/edges at once | UI freezes on graphs with 300+ nodes (vis.js force layout with >200 nodes is sluggish) | Always paginate: load top-50 by `created_at` DESC, add "load more" button | At 200+ nodes |
| `OllamaEmbedder.create_batch()` sequential loop | Batch embedding of 100 episodes takes 100x single-embed time | For retention scoring (access frequency calculation), pre-compute scores during add/search, not during retention sweep | At 50+ items in a batch |
| PyVis generating HTML on every visualization request | 2-5 second delay on every UI page refresh | Generate HTML once at startup; expose a websocket or SSE endpoint for incremental updates | Immediately — static HTML generation is expensive |
| `compact()` loading all 1000 entities into memory for deduplication | OOM risk on large graphs | Add `LIMIT` to the entity load query; process duplicates in pages of 100 | At 500+ entities with long summaries |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing `access_count` and `last_accessed` as entity node attributes in Kuzu | These fields may be logged by graphiti-core's PII removal pass (v0.28.0 added PII stripping) — access metadata is not PII but the stripping logic may corrupt numeric fields it misidentifies | Store retention metadata in a separate SQLite file (`~/.graphiti/retention.db`) keyed by `entity_uuid` — not as node attributes |
| UI server exposing graph search endpoint without scope isolation | A request to `/api/search?q=password` against the global scope could return redacted content that still hints at secret structure | UI API must enforce the same scope-scoped `group_id` filtering that the CLI uses; never expose an unrestricted cross-scope search |
| Multi-provider API key in `llm.toml` stored without file permissions check | If `llm.toml` is world-readable, OpenAI/Anthropic keys are exposed | At startup, check `stat(config_path).st_mode & 0o077 == 0` and warn if group/world readable |
| `decisions-and-patterns` mode capturing code snippets verbatim | Code patterns may contain hardcoded credentials, test keys, or internal URLs | The security gate already handles this — the mistake is implementing mode switching before verifying the gate is hit unconditionally (see Pitfall 6) |
| New provider adapter logging API responses at DEBUG level | Responses may contain PII or sensitive content from user queries | Log only response length and model name at DEBUG; never log response content |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| `graphiti retain` running synchronously and blocking the terminal for minutes | User kills the process mid-retention, leaving graph in partially deleted state | Run retention as background job with `--background` flag; show progress via `graphiti queue status` |
| Graph UI opening at `localhost:7437` without detecting whether port is in use | Two `graphiti ui` instances conflict; second silently fails | Check port availability before starting; print clear error "Port 7437 in use — stop the existing UI or use --port" |
| Capture mode change taking effect immediately on existing captured content | User switches to decisions-only but all existing decisions-and-patterns content remains | Mode only affects new captures; make this explicit in the CLI output: "Capture mode set to decisions-only. Existing knowledge not affected." |
| Multi-provider config error (missing API key) only discovered at first LLM call | User writes knowledge, gets cryptic error 60 seconds into an add operation | Validate provider config at `graphiti health` time: check API key is set, provider endpoint reachable, before any graph operation |
| TTL expiry deleting a node the user manually added | User added a critical decision node 91 days ago; it disappears without warning | Show expiry dates in `graphiti show` output; warn 7 days before expiry via `graphiti health`; never auto-delete nodes tagged `pinned` |

---

## "Looks Done But Isn't" Checklist

- [ ] **TTL Retention:** `Node.delete_by_uuids()` called without first deleting associated `RelatesToNode_` nodes — verify with a Kuzu query count of `RelatesToNode_` before and after deletion.
- [ ] **TTL Retention:** Zero-MENTIONS orphan sweep not implemented — verify with `MATCH (n:Entity) WHERE NOT EXISTS { (:Episodic)-[:MENTIONS]->(n) }` returns 0 after retention.
- [ ] **Capture Mode:** Security sanitization runs unconditionally before mode filter — verify with a test that injects a secret into both mode paths.
- [ ] **Multi-Provider:** `OllamaEmbedder` is still used for embeddings even when LLM provider is switched to OpenAI/Anthropic — verify `graphiti health` with Anthropic provider shows embeddings as "local Ollama".
- [ ] **UI Server:** `graphiti ui` subprocess redirects stdout to DEVNULL — verify MCP server still responds correctly while UI is running.
- [ ] **UI Server:** Graph visualization only loads nodes in the active `group_id` scope — verify global scope shows only global nodes, not project nodes.
- [ ] **Retention + Queue:** TTL window accounts for `queue_item_ttl_hours` (default 24h) — verify no entity is deleted with pending queue items by checking dead letter queue is empty after a retention run.
- [ ] **Multi-Provider Config:** `graphiti health` validates provider API key at startup, not at first use — verify a bad API key produces an immediate `health` error, not a silent delayed failure.
- [ ] **graphiti-core version:** Pin is still `==0.28.1` in `pyproject.toml` after all new dependencies added — verify `pip show graphiti-core | grep Version`.
- [ ] **Reinforcement Scoring:** Access events during `search` and `show` update the retention metadata — verify a searched entity's `access_count` increments and `last_accessed` timestamp updates.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Orphaned RelatesToNode_ after retention run | MEDIUM | Run `graphiti compact` to dedup, then manual Kuzu query `MATCH (e:RelatesToNode_) WHERE NOT (()-[:RELATES_TO]->(e)) DETACH DELETE e` to purge orphan edges |
| graphiti-core upgrade breaks workarounds | HIGH | Revert to `==0.28.1` pin via `pip install graphiti-core[kuzu]==0.28.1`; audit `graph_manager.py` workarounds one by one against new version's source |
| MCP stdio corrupted by UI server | LOW | Kill `graphiti ui` process; restart MCP server (`graphiti mcp serve`); verify MCP tools respond correctly |
| Provider adapter returns wrong structured output format | LOW | Fall back to Ollama provider in `llm.toml`; debug adapter's `_generate_response` in isolation with a unit test |
| Retention deleted a pinned node | MEDIUM | Reindex from git history (`graphiti index --full`) to recover project knowledge; add `pinned` label support to prevent future deletion |
| Capture mode misconfigured — decisions-and-patterns capturing secrets | HIGH | Run `graphiti compact` to deduplicate; audit recent captures with `graphiti list --limit 100`; delete affected entities; add `pinned` label to safe nodes |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Orphaned RelatesToNode_ and Episodic nodes after deletion | Phase 9 (Smart Retention) | `MATCH (e:RelatesToNode_) WHERE NOT (()-[:RELATES_TO]->(e)) RETURN count(e)` returns 0 after retention run |
| Kuzu archived — graphiti-core upgrade risk | Phase 11 (Multi-Provider) — dependency resolver guard | `assert graphiti_core.__version__ == "0.28.1"` in test suite; `pip check` passes |
| OllamaLLMClient tightly coupled — multi-provider breaks adapters | Phase 11 (Multi-Provider) | New provider passes graphiti-core's own integration test suite for structured output |
| TTL deletes nodes with pending queue items | Phase 9 (Smart Retention) | No dead letter queue entries after retention run; queue depth checked before deletion window |
| MCP stdio corrupted by UI server | Phase 10 (Graph UI) | MCP tool calls succeed while `graphiti ui` is running in parallel |
| Capture mode bypasses security sanitization | Phase 9 or 10 (Capture Modes) | `test_capture_modes_always_sanitize_before_filter()` passes; secrets are `[REDACTED]` in all mode paths |
| Retention metadata stored as node attributes (upgrade-fragile) | Phase 9 (Smart Retention) | Retention metadata in `~/.graphiti/retention.db` SQLite, not Kuzu node properties |
| Multi-provider API key not validated at startup | Phase 11 (Multi-Provider) | `graphiti health` returns non-zero exit with clear error if configured provider key is invalid |

---

## Sources

- graphiti-core GitHub issue #1083: Orphaned entities not cleaned up during episode deletion (open, PR #1130 unmerged) — https://github.com/getzep/graphiti/issues/1083
- graphiti-core GitHub issue #1132: Kuzu is archived — https://github.com/getzep/graphiti/issues/1132
- KuzuDB archived October 2025 — https://www.theregister.com/2025/10/14/kuzudb_abandoned/
- FalkorDB KuzuDB migration guide — https://www.falkordb.com/blog/kuzudb-to-falkordb-migration/
- graphiti-core LLM Configuration (multi-provider) — https://help.getzep.com/graphiti/configuration/llm-configuration
- Kuzu driver datetime timezone bug — https://github.com/getzep/graphiti/issues/893
- graphiti-core pypi releases page — https://pypi.org/project/graphiti-core/
- Codebase inspection: `src/graph/service.py` (delete_entities, compact), `src/storage/graph_manager.py` (workarounds), `src/graph/adapters.py` (OllamaLLMClient), `src/llm/client.py` (OllamaClient), `src/queue/worker.py` (BackgroundWorker), `src/capture/summarizer.py` (security gate order)
- graphiti-core DeepWiki provider configuration — https://deepwiki.com/getzep/graphiti/9.3-provider-configuration

---
*Pitfalls research for: Python knowledge graph CLI — v1.1 Smart Retention, Capture Modes, Graph UI, Multi-Provider LLM*
*Researched: 2026-03-01*

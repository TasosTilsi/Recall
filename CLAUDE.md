# graphiti-knowledge-graph

Dual-scope knowledge graph CLI using LadybugDB, local Ollama LLMs, and graphiti-core.

## Commands

```bash
pip install -e ".[dev]"          # install with dev deps
pip install -e ".[reranking]"    # optional BGE reranker

recall <cmd>                     # or: rc <cmd>
recall mcp serve                 # start MCP server (stdio)

pytest tests/                    # run test suite
```

Config: `~/.recall/llm.toml`

## Architecture

```
src/
  cli/
    commands/         # init, search, list, delete, pin, unpin,
                      # health, config, ui, note
  hooks/
    session_start.py  # SessionStart: UUID + incremental git index
    inject_context.py # UserPromptSubmit: context injection (Option C)
    capture_entry.py  # PostToolUse: queue append (fire-and-forget)
    session_stop.py   # Stop/PreCompact: drain queue + summarize
    installer.py      # install_global_hooks() to ~/.claude/settings.json
  graph/
    service.py        # GraphService — all graph operations
    adapters.py       # LLM client + embedder factories
  storage/
    graph_manager.py  # Backend routing (LadybugDB / Neo4j)
    ladybug_driver.py # Vendored LadybugDB graphiti-core driver
  llm/
    config.py         # LLMConfig dataclass, load_config()
    client.py         # OllamaClient with cloud/local failover
    provider.py       # OpenAI-compatible provider client (Phase 13)
  indexer/
    indexer.py        # GitIndexer — incremental git history indexing
    extraction.py     # extract_commit_knowledge() per commit
  queue/
    worker.py         # BackgroundWorker for async capture
  retention/
    manager.py        # TTL-based retention, pin/unpin, stale/archive
  security/
    sanitizer.py      # Entity-level secret scrubbing
    detector.py       # High-entropy + pattern detection
  mcp_server/
    tools.py          # MCP tool handlers
    toon_utils.py     # TOON encoding/decoding
  ui_server/
    app.py            # FastAPI app
    routes.py         # /graph, /dashboard, /entities, /search, /episodes
.planning/            # GSD phase plans
```

## Code Standards

### Logging
- Use `structlog.get_logger()` everywhere **except** `src/mcp_server/`
- In `src/mcp_server/`: use standard `logging` routed to **stderr only**
- Never print to stdout in MCP server — corrupts the stdio transport
- Never call `logger.error("msg", error=e)` with stdlib logging — use structlog-style kwargs

### Async
- `asyncio.run(coro)` at top level — no retry wrapper (causes "cannot reuse awaited coroutine")
- `_get_graphiti()` is async (required for `await build_indices_and_constraints()`)
- SQLiteAckQueue: use `multithreading=True` when ollama_chat runs in `run_in_executor`

### LLM Config (`~/.recall/llm.toml`)

**Default (Ollama legacy mode):**
```toml
[local]
models = ["gemma2:9b"]

[embeddings]
models = ["nomic-embed-text"]
```

**Optional: OpenAI-compatible provider (Phase 13):**
```toml
[llm]
primary_url = "https://api.openai.com/v1"
primary_api_key = "sk-..."
primary_models = ["gpt-4o-mini"]
embed_url = "http://localhost:11434"
embed_models = ["nomic-embed-text"]
```

- `[llm]` section activates `llm_mode = "provider"` and disables `[cloud]`/`[local]` Ollama paths
- When `[llm]` absent: `llm_mode = "legacy"` — Ollama cloud/local failover applies
- Embeddings always local (cloud embed unsupported by current API key)

### LadybugDB Notes
- `LadybugDriver` is vendored at `src/storage/ladybug_driver.py` (~280 lines) — graphiti-core 0.28.1 has no official driver
- Uses `GraphProvider.KUZU` as alias (LadybugDB is a Kuzu fork with identical Cypher/FTS dialect)
- Row access via dict keys: `row['uuid']` not `row[0]` — `execute_query()` returns `list[dict]`
- Read-only methods do NOT pass `read_only=True` — not applicable to `execute_query()` abstraction

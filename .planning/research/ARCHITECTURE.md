# Architecture Research

**Domain:** v1.1 Advanced Features integration into existing graphiti-knowledge-graph
**Researched:** 2026-03-01
**Confidence:** HIGH

---

## Context

This document answers four concrete integration questions for v1.1:
1. Smart retention — where does TTL/scoring live?
2. Configurable capture modes — how does decisions-only vs decisions-and-patterns hook in?
3. Localhost UI — where does `graphiti ui` live, what serves it?
4. Multi-provider LLM — how does the provider abstraction fit the existing client and config?

All analysis is grounded in the actual source code of the v1.0 codebase.

---

## 1. Smart Retention

### The Core Constraint

`EntityNode` in graphiti-core 0.26.3/0.28.1 has exactly these fields:
`uuid`, `name`, `group_id`, `labels`, `created_at`, `summary`, `attributes`, `name_embedding`.

There is **no** `last_accessed_at`, `score`, `ttl`, or `expired_at` field on `EntityNode`.
The `EdgeNode` (stored as `RelatesToNode_` in Kuzu) does have `expired_at`, `valid_at`, and `invalid_at`
fields — these are part of graphiti-core's temporal edge model. Entities have none of these.

This means: **retention metadata cannot be stored inside graphiti-core-managed node rows without
forking graphiti-core**. The `attributes` dict field on `EntityNode` is a valid escape hatch —
it is serialized to JSON in Kuzu and is opaque to graphiti-core's own logic.

### Recommended Approach: SQLite Retention Sidecar

Store retention metadata in a dedicated SQLite table alongside the Kuzu databases, not inside Kuzu.

**Why not Kuzu node properties:**
- Adding properties to the `Entity` table in Kuzu without graphiti-core awareness requires raw DDL
  (`ALTER TABLE Entity ADD ...`) and breaks if graphiti-core ever recreates the schema.
- The `attributes` JSON field is an option but requires custom Kuzu queries on every read;
  it is not indexed and makes bulk TTL queries slow.

**Why not graphiti-core episode metadata:**
- `EpisodicNode` stores source content, not entity-level access tracking.
- There is no hook in graphiti-core to intercept reads for access-time stamping.

**Why SQLite sidecar is correct:**
- The queue module already uses `SQLiteAckQueue` (persistqueue under the hood) at
  `~/.graphiti/` — a SQLite retention DB fits this pattern naturally.
- Retention is an application-level concern (this codebase's logic), not a graph-schema concern.
- The sidecar is fast for bulk TTL queries: `SELECT uuid FROM retention WHERE last_accessed < X`.
- It does not require any changes to graphiti-core or Kuzu schema.
- It survives graphiti-core upgrades cleanly.

**Where the sidecar lives:**
```
~/.graphiti/retention.db          # global scope sidecar
.graphiti/retention.db            # per-project scope sidecar
```

Same placement pattern as `graphiti.kuzu` — one DB per scope, one retention sidecar per scope.

### Schema

```sql
CREATE TABLE IF NOT EXISTS entity_retention (
    uuid TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    created_at REAL NOT NULL,       -- Unix timestamp
    last_accessed_at REAL NOT NULL, -- Updated on every search/get_entity hit
    access_count INTEGER DEFAULT 0, -- Reinforcement signal
    reinforcement_score REAL DEFAULT 1.0,  -- Computed: decays with time, boosts with access
    ttl_days INTEGER DEFAULT 90     -- Per-entity override (NULL = use config default)
);
CREATE INDEX IF NOT EXISTS idx_last_accessed ON entity_retention(last_accessed_at);
CREATE INDEX IF NOT EXISTS idx_group_id ON entity_retention(group_id);
```

### New Module: `src/retention/`

```
src/retention/
    __init__.py
    store.py          # RetentionStore — SQLite sidecar CRUD
    policy.py         # RetentionPolicy — TTL, scoring, expiry decisions
    sweeper.py        # RetentionSweeper — background scan + delete expired
```

`RetentionStore` is initialized by `GraphService.__init__()` alongside `GraphManager`.
It receives the same `scope` and `project_root` signals to open the correct sidecar.

### What `compact()` in `service.py` Becomes

The existing `compact()` method removes exact-name duplicates. Retention adds a distinct operation:
`expire()` — deletes entities whose `reinforcement_score` has decayed below threshold.

These are separate concerns:
- `compact()` — deduplication (already shipped, kept as-is)
- `expire()` — time-based decay (new, added to `GraphService`)

Both should be exposed as a combined `graphiti compact --with-expiry` flag for convenience,
or as separate `graphiti compact` and `graphiti expire` commands. The MCP tool `graphiti_compact`
should accept an optional `--with-expiry` argument.

### Access Tracking Hook

`GraphService.search()` and `GraphService.get_entity()` are the two read paths.
After every successful result, call `retention_store.record_access(uuid)` for each returned entity.
This is a fire-and-forget write to SQLite (no await needed — use `threading.Thread` or
run in the existing `BackgroundWorker`).

```
src/graph/service.py (modified)
    search()
        → calls retention_store.record_access() for each result uuid
    get_entity()
        → calls retention_store.record_access() for entity uuid
```

### LLMConfig Addition

Add to `LLMConfig` in `src/llm/config.py`:
```python
retention_ttl_days: int = 90                  # Default entity TTL
retention_score_threshold: float = 0.1        # Delete below this score
retention_sweep_interval_hours: int = 24      # How often sweeper runs
```

And corresponding `[retention]` section in `llm.toml`:
```toml
[retention]
ttl_days = 90
score_threshold = 0.1
sweep_interval_hours = 24
```

---

## 2. Configurable Capture Modes

### What "Decisions-Only" vs "Decisions-and-Patterns" Actually Means

Looking at `src/capture/relevance.py`: there are already four `RELEVANCE_CATEGORIES`:
`decisions`, `architecture`, `bugs`, `dependencies`. All four are active today.

Looking at `src/capture/summarizer.py`: `BATCH_SUMMARIZATION_PROMPT` extracts
"Decisions & Rationale", "Architecture & Patterns", "Bug Fixes & Root Causes",
"Dependencies & Config" — all four categories, always.

So "decisions-only" in v1.1 means **narrowing** the prompt and the relevance filter
to only `decisions` + `bugs` (no architecture patterns, no dependency tracking).
"Decisions-and-patterns" is the current full behavior, but renamed to make it explicit.

### Where the Mode Hook Lives

**Not in the git post-commit hook shell script.** The shell hook just appends the commit hash
to `~/.graphiti/pending_commits`. The mode needs to be read when the background worker
processes the queue — in Python, not shell.

**The capture pipeline flow:**
```
git commit
  → post-commit.sh appends hash to pending_commits
  → BackgroundWorker reads pending_commits (src/queue/worker.py)
  → git_worker.py fetches diff, calls summarize_and_store()
  → summarize_and_store() → summarize_batch() → BATCH_SUMMARIZATION_PROMPT
  → service.add()
```

The mode lives in `summarize_batch()` — it selects which prompt template to use.

### Implementation: Prompt Selection, Not Filter

The mode is a **prompt change**, not a post-LLM filter. Two separate prompts:

```python
# src/capture/summarizer.py

DECISIONS_ONLY_PROMPT = """...
EXTRACT ONLY:
1. **Decisions & Rationale**: Why something was chosen over alternatives
2. **Bug Fixes & Root Causes**: What went wrong, why, how it was fixed
EXCLUDE: Architecture patterns, dependency changes, all code details
..."""

DECISIONS_AND_PATTERNS_PROMPT = """... (current BATCH_SUMMARIZATION_PROMPT) ..."""
```

`summarize_batch()` accepts a `mode: str = "decisions-and-patterns"` argument.
The mode value is read from `LLMConfig` at call time.

For `decisions-only`, the `relevance.py` filter is tightened too: only `decisions`
and `bugs` categories pass. This provides a pre-LLM filter that reduces content
sent to the LLM (saves tokens, faster), and a prompt that excludes the rest.

### Config Integration

**`LLMConfig` addition:**
```python
capture_mode: str = "decisions-and-patterns"  # "decisions-only" | "decisions-and-patterns"
```

**`llm.toml` section:**
```toml
[capture]
mode = "decisions-only"  # or "decisions-and-patterns"
```

**No changes to the git hook shell template.** The hook is mode-agnostic.
The mode is read in Python when content is processed.

### Files Modified

| File | Change |
|------|--------|
| `src/capture/summarizer.py` | Add `DECISIONS_ONLY_PROMPT`, `mode` param to `summarize_batch()` |
| `src/capture/relevance.py` | Add `filter_for_mode(content, mode)` — narrows categories |
| `src/llm/config.py` | Add `capture_mode: str` field |
| `src/llm/config.py` (`load_config`) | Read `[capture] mode` from TOML |
| `src/capture/git_worker.py` | Pass `mode=config.capture_mode` to `summarize_and_store()` |
| `src/capture/conversation.py` | Same — pass mode for conversation captures |

### No New Modules

This is entirely a parameterization of existing code. No new `src/` directory needed.

---

## 3. Localhost UI

### What `graphiti ui` Should Do

The UI goal is: graph visualization (entity nodes + relationship edges) and a monitoring
dashboard for capture stats. This is a read-only view of Kuzu data.

### Option A: Docker-based Kuzu Explorer (Recommended for Node Graph)

Kuzu ships an official browser-based explorer (`kuzudb/explorer` Docker image) that provides
graph visualization at `http://localhost:8000`. The user mounts a local Kuzu database path
as a volume.

**`graphiti ui` command implementation:**
```
src/cli/commands/ui.py (new)
```

The command:
1. Checks Docker is available (`docker info`)
2. Resolves the current scope's Kuzu DB path (global or project)
3. Mounts it read-only: `docker run -p 8000:8000 -v <db_path>:/database:ro kuzudb/explorer`
4. Opens browser to `http://localhost:8000`
5. Stays running until Ctrl+C (or `--detach` flag)

**Constraint:** Kuzu Explorer requires Docker. Document this requirement.
The Kuzu DB cannot be open by two writers simultaneously — use read-only volume mount to avoid
conflicts with the running graphiti process.

**Cons of this option:** requires Docker; the Explorer UI is Kuzu's generic query interface,
not a graphiti-branded dashboard. Good for graph exploration, not for capture monitoring.

### Option B: FastAPI + Custom UI (Recommended for Monitoring Dashboard)

For the monitoring dashboard (capture stats, queue depth, retention health), a small FastAPI
server in `src/ui/` is the right tool. It does not require Docker.

**`graphiti ui` serves two surfaces:**
- `/` → static HTML dashboard (capture stats, queue depth, entity counts, retention health)
- `/api/stats` → JSON endpoint — entity_count, episode_count, queue_depth, last_capture_time
- `/api/graph` → JSON graph data (nodes + edges) for D3.js or Cytoscape.js visualization

**`src/ui/` module:**
```
src/ui/
    __init__.py
    server.py         # FastAPI app, route definitions
    static/
        index.html    # Dashboard HTML (single file, embedded JS — no build step)
```

**How it reads Kuzu:**
`server.py` calls `GraphService` methods directly (same process, same `run_graph_operation()`
pattern). It does NOT go through the CLI subprocess. This is acceptable because `graphiti ui`
is a long-running process that owns the GraphService for the duration of the session.

**Important:** `graphiti ui` must NOT run at the same time as `graphiti mcp serve` using the
same Kuzu DB path, since Kuzu allows only one writer per database. Document this constraint.
In practice, during UI sessions the user is browsing — not committing — so capture hooks
will try to write to Kuzu while the UI holds the connection. Mitigation: open the Kuzu DB
in read-only mode for the UI server (check KuzuDriver constructor options).

### Recommended Hybrid

- Phase 9 (quick win): Use Docker Kuzu Explorer approach. Zero custom UI code, one command.
- Phase 10: Add FastAPI dashboard in `src/ui/` for capture monitoring. Kuzu Explorer handles graph viz.

This matches the PROJECT.md "Web UI deferred to Phase 10" note.

### CLI Command Location

```
src/cli/commands/ui.py (new file)
```

Registered in the main CLI `__init__.py` the same way `mcp_app`, `hooks_app` are registered.

```python
@ui_app.command(name="open")  # or just `graphiti ui` as a direct command
def ui_command(
    scope: ...,
    port: int = typer.Option(8000, "--port"),
    no_browser: bool = typer.Option(False, "--no-browser"),
):
    ...
```

**Files to Create/Modify:**

| File | Action |
|------|--------|
| `src/cli/commands/ui.py` | New — Typer command group, Docker launcher or FastAPI launcher |
| `src/cli/__init__.py` | Modified — register `ui_app` |
| `src/ui/server.py` | New (Phase 10 only) — FastAPI app |
| `src/ui/static/index.html` | New (Phase 10 only) — Dashboard HTML |

---

## 4. Multi-Provider LLM

### Current Architecture

```
src/llm/
    client.py       # OllamaClient — hard-wired to Ollama SDK (cloud + local)
    config.py       # LLMConfig frozen dataclass + load_config()
```

`OllamaClient` is Ollama-specific: it uses `ollama.Client` (the Ollama Python SDK),
not the OpenAI SDK. The cloud endpoint (`https://ollama.com`) happens to be OpenAI-API-compatible,
but the client is instantiated as an `ollama.Client` with an Authorization header.

`OllamaLLMClient` in `src/graph/adapters.py` wraps `OllamaClient` to implement
graphiti-core's `LLMClient` ABC.

### What Multi-Provider Means in Practice

The goal: add OpenAI, Anthropic, Groq, and any OpenAI-compatible endpoint as `[provider]`
config without code changes. The user changes `llm.toml` only.

The right abstraction is a **provider factory** that returns a unified callable interface.

### Recommended Approach: New `src/llm/providers/` Directory

**NOT LiteLLM** — LiteLLM adds a large dependency with a proxy server pattern. This project
runs locally and needs minimal dependencies. The providers are: OpenAI-compatible (covers
OpenAI, Groq, any OpenAI-API endpoint), Anthropic (separate SDK), and Ollama (existing).

**Provider interface** — a Protocol matching the existing `OllamaClient.chat()` signature:
```python
# src/llm/providers/base.py
class LLMProvider(Protocol):
    def chat(self, model=None, messages=None, **kwargs) -> dict: ...
    def embed(self, model=None, input=None, **kwargs) -> dict: ...
    def generate(self, model=None, prompt=None, **kwargs) -> dict: ...
```

**Provider implementations:**
```
src/llm/providers/
    __init__.py
    base.py           # LLMProvider Protocol
    ollama.py         # Extracted from client.py — existing OllamaClient logic
    openai_compat.py  # OpenAI SDK client (covers OpenAI, Groq, custom endpoints)
    anthropic.py      # Anthropic SDK client (translate chat messages format)
```

`openai_compat.py` uses `openai.OpenAI(base_url=..., api_key=...)`. This covers:
- OpenAI native (`https://api.openai.com/v1`)
- Groq (`https://api.groq.com/openai/v1`)
- Any OpenAI-compatible local endpoint (LM Studio, Ollama via `/v1/` path, etc.)

`anthropic.py` uses `anthropic.Anthropic(api_key=...)` and translates message format.

### Config Changes

**`LLMConfig` — add provider section:**
```python
# New fields
provider_type: str = "ollama"             # "ollama" | "openai" | "anthropic" | "openai_compat"
provider_endpoint: str | None = None      # Custom endpoint (openai_compat)
provider_api_key: str | None = None       # API key for provider
provider_models: list[str] = field(default_factory=list)  # Provider model list
```

**`llm.toml` — new `[provider]` section:**
```toml
[provider]
type = "openai"                           # Replaces cloud Ollama
endpoint = "https://api.openai.com/v1"   # Optional override
api_key = "sk-..."                        # Or via PROVIDER_API_KEY env var
models = ["gpt-4o-mini"]
```

The existing `[cloud]` and `[local]` sections remain for Ollama compatibility.
`[provider]` takes precedence over `[cloud]` when set.

### How It Integrates with `OllamaLLMClient` in `adapters.py`

`OllamaLLMClient` calls `ollama_chat` (imported from `src.llm`) through `run_in_executor`.
After the refactor, `src.llm.chat` becomes provider-aware: it calls the configured provider
rather than always Ollama.

The `adapters.py` file does NOT change. The `OllamaLLMClient` name is a historical artifact;
it continues to work by routing through the updated `src.llm.chat()` function.

### `client.py` Refactor

`OllamaClient` in `client.py` is renamed to the `ollama.py` provider. `client.py` becomes
a thin **provider factory**:

```python
# src/llm/client.py (refactored)
def get_provider(config: LLMConfig) -> LLMProvider:
    if config.provider_type == "openai" or config.provider_type == "openai_compat":
        from src.llm.providers.openai_compat import OpenAICompatProvider
        return OpenAICompatProvider(config)
    elif config.provider_type == "anthropic":
        from src.llm.providers.anthropic import AnthropicProvider
        return AnthropicProvider(config)
    else:  # "ollama" (default)
        from src.llm.providers.ollama import OllamaProvider
        return OllamaProvider(config)
```

The module-level `chat()`, `embed()`, `generate()` functions in `src/llm/__init__.py`
call `get_provider(load_config())` and dispatch. The existing callers (`adapters.py`,
`summarizer.py`, `indexer/`) continue to work without modification.

### Files Modified/Created

| File | Action |
|------|--------|
| `src/llm/config.py` | Add `provider_type`, `provider_endpoint`, `provider_api_key`, `provider_models` fields |
| `src/llm/client.py` | Refactor to provider factory `get_provider()` |
| `src/llm/providers/__init__.py` | New — package init |
| `src/llm/providers/base.py` | New — `LLMProvider` Protocol |
| `src/llm/providers/ollama.py` | New — extracted from `client.py` (OllamaClient logic) |
| `src/llm/providers/openai_compat.py` | New — OpenAI SDK adapter |
| `src/llm/providers/anthropic.py` | New — Anthropic SDK adapter |
| `src/graph/adapters.py` | No changes |
| `src/llm/__init__.py` | Modified — `chat()` calls `get_provider()` |

---

## System Overview: v1.1 Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           INTERFACE LAYER                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   CLI    │  │  Hooks   │  │   MCP    │  │  UI cmd  │  │  Queue   │   │
│  │ (typer)  │  │ (git +   │  │ (stdio)  │  │(ui.py)   │  │ worker   │   │
│  │          │  │ session) │  │          │  │          │  │          │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       └─────────────┴─────────────┴──────────────┴─────────────┘         │
├───────────────────────────────────────────────────────────────────────────┤
│                         SERVICE LAYER                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                GraphService (service.py)                             │  │
│  │  add() search() get_entity() compact() expire() [NEW]               │  │
│  │  + retention_store.record_access()  [NEW hook in search/get_entity] │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
├───────────────────────────────────────────────────────────────────────────┤
│                       CAPTURE LAYER  (modified)                           │
│  ┌────────────────────────┐  ┌──────────────────────────────────────┐    │
│  │    summarizer.py       │  │          relevance.py                 │    │
│  │  mode-aware prompts    │  │  filter_for_mode(content, mode)      │    │
│  │  DECISIONS_ONLY_PROMPT │  │  narrows categories for decisions-   │    │
│  │  DECISIONS_AND_... PTR │  │  only mode                           │    │
│  └────────────────────────┘  └──────────────────────────────────────┘    │
├───────────────────────────────────────────────────────────────────────────┤
│                        LLM LAYER  (new providers)                         │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                    Provider Factory (client.py)                    │   │
│  │  get_provider(config) → OllamaProvider | OpenAICompatProvider |   │   │
│  │                          AnthropicProvider                         │   │
│  └────────────────────────────────────────────────────────────────────┘   │
├───────────────────────────────────────────────────────────────────────────┤
│                       STORAGE LAYER                                       │
│  ┌────────────────────────┐  ┌────────────────────────┐                  │
│  │    Kuzu Graph DB       │  │   SQLite Retention DB  │  [NEW]           │
│  │  (graphiti-core +      │  │   entity_retention     │                  │
│  │   KuzuDriver)          │  │   (per-scope sidecar)  │                  │
│  └────────────────────────┘  └────────────────────────┘                  │
└───────────────────────────────────────────────────────────────────────────┘
```

### New Modules Summary

| New Module | Purpose |
|------------|---------|
| `src/retention/store.py` | SQLite sidecar CRUD for retention metadata |
| `src/retention/policy.py` | TTL scoring, expiry decisions |
| `src/retention/sweeper.py` | Background scan + delete expired entities |
| `src/llm/providers/base.py` | LLMProvider Protocol |
| `src/llm/providers/ollama.py` | Extracted OllamaClient (existing logic) |
| `src/llm/providers/openai_compat.py` | OpenAI SDK adapter |
| `src/llm/providers/anthropic.py` | Anthropic SDK adapter |
| `src/cli/commands/ui.py` | `graphiti ui` command (Docker launcher) |

### Modified Files Summary

| Modified File | Change |
|---------------|--------|
| `src/graph/service.py` | Add `expire()` method; add retention access tracking in `search()` and `get_entity()` |
| `src/capture/summarizer.py` | Add `DECISIONS_ONLY_PROMPT`; `mode` param to `summarize_batch()` |
| `src/capture/relevance.py` | Add `filter_for_mode(content, mode)` |
| `src/capture/git_worker.py` | Pass `mode=config.capture_mode` to `summarize_and_store()` |
| `src/capture/conversation.py` | Pass `mode=config.capture_mode` to `summarize_and_store()` |
| `src/llm/config.py` | Add provider fields, capture_mode, retention fields |
| `src/llm/client.py` | Refactor to provider factory; existing OllamaClient logic moves to `providers/ollama.py` |
| `src/llm/__init__.py` | `chat()` calls `get_provider()` instead of singleton OllamaClient |
| `src/cli/__init__.py` | Register `ui_app` |

---

## Recommended Component Boundaries

| Component | Responsibility | Does NOT Do |
|-----------|---------------|-------------|
| `src/retention/store.py` | Read/write retention SQLite sidecar | Graph queries, entity deletion |
| `src/retention/policy.py` | Score calculation, expiry decisions | Storage, deletion |
| `src/retention/sweeper.py` | Periodic scan, calls `service.expire()` | Score logic, storage directly |
| `src/llm/providers/` | LLM API calls per provider | Failover logic (stays in `client.py`) |
| `src/cli/commands/ui.py` | Spawn Docker or FastAPI process | Read data directly (delegates to CLI/service) |
| `src/ui/server.py` (Phase 10) | Serve HTTP dashboard | Modify data — read-only |

---

## Data Flow Changes

### Retention Access Tracking

```
User: graphiti search "query"
  → GraphService.search()
  → graphiti-core search() → Kuzu
  → Results: [entity_uuids]
  → RetentionStore.record_access(uuids)  [async, background]
  → Returns results to user
```

### Capture Mode Flow

```
git commit
  → post-commit.sh: append hash to pending_commits [no change]
  → BackgroundWorker.process()
  → git_worker.py: fetch diff
  → relevance.filter_for_mode(diff, config.capture_mode)  [new filter step]
  → summarize_batch(items, mode=config.capture_mode)  [prompt selection]
  → service.add(summary)
```

### Multi-Provider LLM Flow

```
adapters.py: OllamaLLMClient._generate_response(messages, response_model)
  → loop.run_in_executor(None, lambda: ollama_chat(messages=..., **kwargs))
  → src.llm.__init__.chat()
  → get_provider(load_config())           [NEW: provider factory]
  → provider.chat(messages=..., **kwargs) [dispatches to Ollama/OpenAI/Anthropic]
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Storing TTL Metadata in Kuzu Entity Nodes

**What people do:** Add `last_accessed_at` property to the `Entity` node table with raw Kuzu DDL.
**Why it is wrong:** graphiti-core rebuilds/recreates schema on `build_indices_and_constraints()` calls.
Custom properties added outside graphiti-core's schema management can be dropped silently.
Also breaks compatibility with future graphiti-core upgrades.
**Do this instead:** SQLite sidecar keyed by uuid.

### Anti-Pattern 2: Mode Selection in the Shell Hook

**What people do:** Add a `GRAPHITI_CAPTURE_MODE` environment variable to `post-commit.sh`
and pass it through the shell script.
**Why it is wrong:** The hook just captures the commit hash — it does not process content.
The mode needs to be active when the background worker summarizes commits (Python), not when
the hash is appended (shell). Shell env vars do not survive across asynchronous background processing.
**Do this instead:** Read `config.capture_mode` in `summarize_batch()` at processing time.

### Anti-Pattern 3: Making `graphiti ui` Open the Kuzu DB for Writing

**What people do:** Serve a FastAPI app that uses `GraphService` with read-write Kuzu access
simultaneously with background capture.
**Why it is wrong:** Kuzu is embedded (one writer at a time). If the UI server holds an open
write connection and a git hook fires, the hook's `service.add()` call will block or fail.
**Do this instead:** Open Kuzu in read-only mode for the UI server, or use the Docker Kuzu
Explorer (which documents the read-only volume mount pattern explicitly).

### Anti-Pattern 4: Adding LiteLLM as a Dependency

**What people do:** Add LiteLLM to get multi-provider support "for free".
**Why it is wrong:** LiteLLM is 170MB+ with dozens of transitive dependencies. It has a
proxy-server model that adds latency. This project is a local tool where dependency minimalism
matters. The OpenAI Python SDK covers OpenAI + Groq + any OpenAI-compatible endpoint; Anthropic
has its own SDK. That is two optional dependencies, not a gateway.
**Do this instead:** `openai` and `anthropic` as optional extras in `pyproject.toml`
(`pip install graphiti-knowledge-graph[openai]` or `[anthropic]`).

---

## Phase Sequencing Recommendation

Based on integration complexity and dependency order:

| Phase | Feature | Rationale |
|-------|---------|-----------|
| Phase 9 | Smart retention | Standalone new module; no existing code changes except `service.py` hook |
| Phase 10 | Configurable capture modes | Touches summarizer + relevance — easy prompt change, low risk |
| Phase 11 | `graphiti ui` (Docker Explorer) | No new UI code for Phase 11 — just a CLI command wrapper |
| Phase 12 | Multi-provider LLM | Largest refactor (client.py decomposition); do last to avoid blocking earlier phases |

**Why retention before modes:**
Retention requires the new sidecar infrastructure. Capture mode changes are simpler (prompt
parameterization) and do not block any other phase.

**Why UI before multi-provider LLM:**
UI is a new surface (no existing code to break). Multi-provider LLM refactors the core
`client.py` / `__init__.py` and `adapters.py` dependency chain — highest regression risk.
Do it after other features are stable.

---

## Integration Points Summary (for Planner)

| Question | Answer | New Files | Modified Files |
|----------|--------|-----------|----------------|
| Retention TTL/scoring | SQLite sidecar (`src/retention/`); EntityNode has no TTL fields | `src/retention/store.py`, `policy.py`, `sweeper.py` | `service.py`, `config.py` |
| Retention vs compact() | `compact()` = dedup (unchanged); `expire()` = new method in service | None | `service.py` |
| Capture mode | Prompt change + filter in summarizer.py; no hook changes | None | `summarizer.py`, `relevance.py`, `config.py`, `git_worker.py`, `conversation.py` |
| Localhost UI | Docker Kuzu Explorer wrapped by CLI command | `src/cli/commands/ui.py` | `src/cli/__init__.py` |
| UI data access | Read-only Kuzu mount (Docker) or read-only GraphService (FastAPI, Phase 10) | `src/ui/server.py` (Phase 10) | None |
| Multi-provider LLM | `src/llm/providers/` directory; `client.py` becomes factory | `providers/base.py`, `ollama.py`, `openai_compat.py`, `anthropic.py` | `client.py`, `config.py`, `llm/__init__.py` |
| Adapters.py changes | None — `OllamaLLMClient` continues working unchanged | None | None |

---

## Sources

- graphiti-core 0.26.3 source: `/home/tasostilsi/Development/Projects/graphiti-knowledge-graph/.venv/lib/python3.12/site-packages/graphiti_core/nodes.py` (EntityNode fields verified)
- graphiti-core edges.py: confirmed `expired_at`, `valid_at`, `invalid_at` fields exist on EdgeNode only
- Kuzu Explorer Docker: [kuzudb/explorer](https://github.com/kuzudb/explorer), [Docker Hub](https://hub.docker.com/r/kuzudb/explorer)
- Kuzu Explorer docs: [docs.kuzudb.com/visualization/kuzu-explorer/](https://docs.kuzudb.com/visualization/kuzu-explorer/)
- Multi-provider options: [LiteLLM](https://docs.litellm.ai/docs/), [aisuite](https://pypi.org/project/aisuite/)
- graphiti-core GitHub: [getzep/graphiti](https://github.com/getzep/graphiti)
- Existing codebase reviewed: `service.py`, `adapters.py`, `client.py`, `config.py`, `summarizer.py`, `relevance.py`, `graph_manager.py`, `hooks/`, `capture/`

---

*Architecture research for: graphiti-knowledge-graph v1.1 Advanced Features*
*Researched: 2026-03-01*

# Phase 13: Multi-Provider LLM - Research

**Researched:** 2026-03-17
**Domain:** Python LLM client routing — openai SDK base_url pattern, Ollama SDK, graphiti-core adapter bridge
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Config shape — new [llm] section**

A new flat `[llm]` section unifies primary, fallback, and embeddings provider config. Old `[cloud]` and `[local]` sections are silently ignored when `[llm]` is present; they continue to work unchanged when `[llm]` is absent (full backward compat — PROV-02).

```toml
[llm]
primary_url     = "https://api.openai.com/v1"
primary_api_key = "sk-..."
primary_models  = ["gpt-4o-mini"]

fallback_url    = "http://localhost:11434"        # optional
fallback_models = ["gemma2:9b", "llama3.2:3b"]

embed_url       = "https://api.openai.com/v1"     # or separate URL
# embed_api_key = "sk-..."                         # optional; defaults to primary_api_key
embed_models    = ["text-embedding-3-small"]
```

**Auto-detect SDK by URL (no explicit `type` field):**
- URL contains `localhost` or `127.0.0.1` → Ollama SDK
- URL contains `ollama.com` → Ollama SDK (cloud path)
- Any other URL → openai-compatible SDK (`openai` library with `base_url` override)

**Backward compat:** `graphiti config init` continues to generate the old `[cloud]`/`[local]` format by default. The new `[llm]` section is documented as opt-in in comments. PROV-02 is satisfied.

**Provider routing + fallback**
- `[llm]` section replaces cloud Ollama entirely when present
- Runtime provider failure → **fail hard** with a clear error naming provider + endpoint + remediation hint (consistent with Phase 12 Neo4j fail-fast pattern)
- **No silent fallback** to Ollama when the configured primary provider fails — user explicitly opted out of Ollama
- Fallback is **explicit only**: `fallback_url` in `[llm]` triggers fallback; unconfigured = no fallback
- `[cloud]` and `[local]` sections silently ignored (no warning logged) when `[llm]` is present

**Embeddings scope**
- `embed_url` supports any URL — same SDK auto-detection as primary/fallback
- Embeddings are **no longer hardcoded to local-only**; users can configure `text-embedding-3-small`, Groq embed, or any compatible endpoint
- `embed_api_key` is optional; falls back to `primary_api_key` when not set
- `embed_models` lists which embedding models to use

**Startup validation**
- **Lightweight ping** (list-models endpoint) on **every `graphiti` command invocation**
- Validates both primary provider and embed endpoint: reachable + API key accepted
- Fail fast with clear error if unreachable (names provider, endpoint, what to check)
- Same trigger scope as Phase 12 Neo4j validation — consistent CLI behavior

**Health display format:** `provider: openai/gpt-4o-mini @ api.openai.com [OK]`

All three rows shown when configured:
```
provider:  openai/gpt-4o-mini @ api.openai.com [OK]
embed:     openai/text-embedding-3-small @ api.openai.com [OK]
fallback:  ollama/gemma2:9b @ localhost:11434 [OK]
```

Each row: `<tier>: <sdk>/<first-model> @ <hostname> [OK|UNREACHABLE]`
Rows for unconfigured tiers are omitted.

### Claude's Discretion
- Exact openai SDK version pin (openai >= 1.0 recommended for `base_url` override pattern)
- Whether to create a new `ProviderClient` class or extend `OllamaClient` for routing
- Exact timeout budget for startup ping (short — should not add perceptible delay)
- Error message wording (must name provider + endpoint + remediation)
- How to represent detected provider type internally (enum vs string)
- Whether to update `graphiti config init` to include commented-out `[llm]` block as a hint

### Deferred Ideas (OUT OF SCOPE)
- N-provider failover chain (ordered list beyond primary+fallback) — PROV-05 (explicitly deferred in REQUIREMENTS.md)
- `graphiti config init` generating a commented-out `[llm]` block as a hint — Claude's discretion on whether to include in Phase 13 or a future polish phase
- Per-operation provider routing (e.g. different provider for chat vs generate) — out of scope; single provider for all ops
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PROV-01 | User can set a `[llm]` section in `llm.toml` to switch to OpenAI, Groq, or any OpenAI-compatible endpoint without code changes | New `[llm]` section parsing in `load_config()` + SDK auto-detection by URL in new `ProviderClient` |
| PROV-02 | Existing Ollama config works unchanged when no `[llm]` section is present | `if "llm" not in config_data:` guard in `load_config()`; `OllamaClient` path unchanged |
| PROV-03 | `graphiti health` shows the active provider name and reachability status | `_check_provider()` helper in `health.py` following Phase 12 backend row pattern |
| PROV-04 | Provider API key is validated at startup with a clear error if unreachable (not at first use) | `validate_provider_startup()` called from CLI entrypoint `cli_entry()` or Typer callback |
</phase_requirements>

---

## Summary

Phase 13 adds a new `[llm]` section to `llm.toml` that enables users to route all graph operations through any OpenAI-compatible endpoint (OpenAI, Groq, or self-hosted) without code changes. The key implementation insight is that graphiti-core already ships `OpenAIGenericClient` and `OpenAIEmbedder` built on `AsyncOpenAI(base_url=..., api_key=...)` — the `base_url` override pattern is how graphiti-core itself supports multiple providers. This means the adapter layer (`OllamaLLMClient`, `OllamaEmbedder`) does not need to learn the openai SDK directly; instead, when `[llm]` is present, graphiti-core's own openai-compatible clients can be instantiated and returned from `GraphService`.

The migration boundary is clean: `src/llm/config.py` adds new fields for `[llm]` section parsing; a new `ProviderClient` class (or light routing wrapper) holds URL-to-SDK detection logic; `src/graph/adapters.py` and `src/graph/service.py` gain a factory that selects either the existing Ollama adapter or graphiti-core's `OpenAIGenericClient` / `OpenAIEmbedder` based on the config. Startup validation pings `client.models.list()` (openai-compatible) or `local_client.list()` (Ollama) and calls `sys.exit(1)` on failure — identical to the Phase 12 Neo4j fail-fast pattern.

**Primary recommendation:** Create a `ProviderClient` factory in `src/llm/provider.py` that inspects `LLMConfig.llm_*` fields, detects SDK by URL, instantiates the correct async client, and exposes `ping()` / `chat()` / `embed()` methods. When `[llm]` is present, `GraphService` uses `OpenAIGenericClient(config=GraphitiLLMConfig(api_key=..., base_url=..., model=...))` and `OpenAIEmbedder` directly — reusing graphiti-core's existing battle-tested openai adapters rather than bridging through `OllamaClient`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai (AsyncOpenAI) | 2.17.0 (in venv) | OpenAI-compatible chat + embeddings | graphiti-core already depends on this; `base_url` override is the universal multi-provider pattern |
| ollama | 0.6.1 (pinned) | Ollama SDK for local + cloud ollama.com | Already installed; used by existing `OllamaClient` |
| httpx | >=0.28.0 (installed) | HTTP for startup ping fallback if SDK list fails | Already a dependency |
| tenacity | 9.1.4 (pinned) | Retry on transient errors | Already installed; used in existing `_retry_cloud()` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| graphiti_core.llm_client.openai_generic_client.OpenAIGenericClient | 0.28.1 | graphiti-core's built-in openai-compatible LLM adapter | Use when `[llm]` section present and URL is not Ollama |
| graphiti_core.embedder.openai.OpenAIEmbedder | 0.28.1 | graphiti-core's built-in openai embedder | Use when `embed_url` is not Ollama |
| graphiti_core.llm_client.config.LLMConfig as GraphitiLLMConfig | 0.28.1 | Config object for graphiti-core clients | Pass `api_key`, `base_url`, `model` to instantiate any graphiti-core client |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| graphiti-core's `OpenAIGenericClient` | Build custom AsyncOpenAI wrapper | No advantage — graphiti-core already has a tested, maintained adapter; wrapping ourselves duplicates ~200 lines |
| URL-based SDK detection | Explicit `type` field in `[llm]` | CONTEXT.md locked decision: no `type` field; URL detection is the UX goal |
| Sync openai client | Async `AsyncOpenAI` | graphiti-core's adapter layer is async; must match |

**Installation:** No new packages needed. `openai` is already in the venv at 2.17.0 (installed by `graphiti-core[neo4j]`). No `pyproject.toml` changes required.

**Version verification (confirmed):**
- `openai==2.17.0` in project venv — `pip show openai` in `.venv` confirms
- `ollama==0.6.1` pinned in `pyproject.toml`
- `graphiti-core==0.28.1` pinned in `pyproject.toml`

---

## Architecture Patterns

### Recommended Project Structure (new files)
```
src/
  llm/
    client.py         # OllamaClient — unchanged (legacy path)
    config.py         # LLMConfig — add llm_* fields; load_config() parses [llm] section
    provider.py       # NEW: ProviderClient factory — SDK detection, ping, chat, embed
    __init__.py       # Add get_provider_client(); keep get_client() for backward compat
  graph/
    adapters.py       # OllamaLLMClient/OllamaEmbedder — unchanged; used when no [llm] section
    service.py        # GraphService — factory selects adapter based on config
```

### Pattern 1: SDK Auto-Detection by URL

**What:** Inspect the URL string to pick the right SDK client without a `type` field.

**When to use:** Every time `[llm]` section is present and a client must be instantiated.

```python
# Source: CONTEXT.md locked decision
from urllib.parse import urlparse

def _detect_sdk(url: str) -> str:
    """Returns 'ollama' or 'openai'."""
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname in ("localhost", "127.0.0.1") or hostname.endswith(".local"):
        return "ollama"
    if "ollama.com" in hostname:
        return "ollama"
    return "openai"
```

### Pattern 2: ProviderClient Factory

**What:** A new `ProviderClient` class in `src/llm/provider.py` holds the per-tier clients and exposes `ping()`, `chat()`, `embed()`.

**When to use:** Only when `[llm]` section is present in config. Legacy `OllamaClient` path unchanged when `[llm]` absent.

```python
# Source: graphiti-core 0.28.1 — OpenAIGenericClient uses AsyncOpenAI(api_key, base_url)
from openai import AsyncOpenAI
import asyncio

class ProviderClient:
    def __init__(self, config: LLMConfig):
        # primary tier
        if _detect_sdk(config.llm_primary_url) == "openai":
            self._primary = AsyncOpenAI(
                api_key=config.llm_primary_api_key,
                base_url=config.llm_primary_url,
                timeout=config.request_timeout_seconds,
            )
        else:
            from ollama import Client
            self._primary_ollama = Client(host=config.llm_primary_url)
        # similar for fallback and embed tiers

    async def ping_primary(self) -> bool:
        """Lightweight list-models call to verify reachability + auth."""
        try:
            await self._primary.models.list()
            return True
        except Exception:
            return False
```

### Pattern 3: graphiti-core Adapter Selection Factory

**What:** `GraphService.__init__()` (or a factory function) returns different `(LLMClient, EmbedderClient)` pairs based on whether `[llm]` is configured.

**When to use:** At `GraphService` construction time — called once per operation in `graph_manager.py`.

```python
# Source: graphiti-core 0.28.1 — OpenAIGenericClient.__init__ signature
from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
from graphiti_core.llm_client.config import LLMConfig as GraphitiLLMConfig
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

def _make_llm_client(config: LLMConfig):
    if config.llm_mode == "provider":  # [llm] section present
        graphiti_cfg = GraphitiLLMConfig(
            api_key=config.llm_primary_api_key,
            base_url=config.llm_primary_url,
            model=config.llm_primary_models[0],
        )
        return OpenAIGenericClient(config=graphiti_cfg)
    else:
        return OllamaLLMClient()  # existing path

def _make_embedder(config: LLMConfig):
    if config.llm_mode == "provider":
        embed_cfg = OpenAIEmbedderConfig(
            api_key=config.llm_embed_api_key or config.llm_primary_api_key,
            base_url=config.llm_embed_url,
            embedding_model=config.llm_embed_models[0],
        )
        return OpenAIEmbedder(config=embed_cfg)
    else:
        return OllamaEmbedder()  # existing path
```

### Pattern 4: Startup Validation (fail-fast, Phase 12 pattern)

**What:** Call `ping()` on every `graphiti` command; `sys.exit(1)` with a named-endpoint error if unreachable.

**Where to hook:** `cli_entry()` in `src/cli/__init__.py` OR a Typer `@app.callback` that runs before every subcommand. The Phase 12 Neo4j check is in `health.py` for the health command but also in `graph_manager.py` for any operation that opens the driver. For Phase 13 the natural hook point is the Typer callback or a `_validate_provider()` helper called early in `cli_entry()`.

```python
# Source: Phase 12 pattern — sys.exit(1) with named error
import sys

def validate_provider_startup(config: LLMConfig):
    """Call on every graphiti command when [llm] section is present."""
    if config.llm_mode != "provider":
        return  # legacy Ollama path — no startup ping
    provider_client = ProviderClient(config)
    ok = asyncio.run(provider_client.ping_primary())
    if not ok:
        print(
            f"Provider unreachable: {config.llm_primary_url} — "
            f"check primary_api_key and primary_url in ~/.graphiti/llm.toml",
            file=sys.stderr,
        )
        sys.exit(1)
```

### Pattern 5: LLMConfig New Fields

**What:** Add `llm_*` fields to the frozen dataclass. Add `llm_mode` sentinel (`"legacy"` vs `"provider"`) to avoid checking `llm_primary_url is not None` everywhere.

```python
# Source: existing LLMConfig pattern in src/llm/config.py
@dataclass(frozen=True)
class LLMConfig:
    # ... existing fields unchanged ...

    # [llm] section fields — all None when [llm] absent (llm_mode == "legacy")
    llm_mode: str = "legacy"           # "legacy" | "provider"
    llm_primary_url: str | None = None
    llm_primary_api_key: str | None = None
    llm_primary_models: list[str] = field(default_factory=list)
    llm_fallback_url: str | None = None
    llm_fallback_models: list[str] = field(default_factory=list)
    llm_embed_url: str | None = None
    llm_embed_api_key: str | None = None
    llm_embed_models: list[str] = field(default_factory=list)
```

**load_config() parsing — follows `[backend]` pattern from Phase 12:**

```python
# Source: src/llm/config.py — backend section parsing pattern
llm_section = config_data.get("llm", {})
if llm_section:
    llm_mode = "provider"
    # [cloud]/[local] silently ignored — no warning, per CONTEXT.md
else:
    llm_mode = "legacy"
```

### Anti-Patterns to Avoid
- **Calling `asyncio.run()` inside an already-running event loop:** `ping()` is async; `validate_provider_startup()` wraps it with `asyncio.run()`. If called inside graphiti-core's async execution, this will deadlock. Solution: ping must be called synchronously before `asyncio.run(graph_operation)`, not inside it.
- **Mutating the frozen `LLMConfig`:** It is a frozen dataclass. All new fields must have defaults. Never `dataclasses.replace()` to smuggle state in — use the `ProviderClient` singleton.
- **Using the `type` field that CONTEXT.md rejected:** Do not add `primary_type = "openai"` to the TOML schema. URL detection is the locked UX.
- **Stripping `format=` from openai SDK calls:** The `format=` kwarg is Ollama-SDK-specific. `OpenAIGenericClient._generate_response()` uses `response_format={"type": "json_schema", ...}` — entirely different parameter. Do not pass Ollama-style kwargs to openai SDK.
- **Reusing the `OllamaClient` for openai-compatible endpoints:** `OllamaClient` wraps the `ollama` Python SDK which speaks the Ollama REST API (`/api/chat`), not the OpenAI REST API (`/v1/chat/completions`). They are incompatible wire protocols despite naming similarities.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| openai-compatible LLM calls | Custom `AsyncOpenAI` wrapper | `graphiti_core.llm_client.openai_generic_client.OpenAIGenericClient` | Already implements `_generate_response`, retries, structured output via `json_schema` response_format |
| openai-compatible embeddings | Custom `AsyncOpenAI.embeddings` wrapper | `graphiti_core.embedder.openai.OpenAIEmbedder` | Already implements `create()` and `create_batch()` with proper `base_url` support |
| Structured output via openai | `format=` Ollama-style | `response_format={"type": "json_schema", "json_schema": {...}}` via `OpenAIGenericClient` | OpenAI API uses `response_format` not `format`; `OpenAIGenericClient` handles this |
| HTTP ping for reachability | Custom httpx call to `/health` | `AsyncOpenAI.models.list()` | list-models confirms both connectivity AND auth in one call; returns `openai.AuthenticationError` on 401 |

**Key insight:** graphiti-core 0.28.1 already ships `OpenAIGenericClient` and `OpenAIEmbedder` that encapsulate the exact `AsyncOpenAI(api_key=..., base_url=...)` pattern. Phase 13 should be a thin routing/config layer on top, not a reimplementation.

---

## Common Pitfalls

### Pitfall 1: Ollama SDK vs OpenAI SDK Wire Protocol Mismatch
**What goes wrong:** Pointing Ollama SDK `Client(host="https://api.openai.com/v1")` at OpenAI. The Ollama SDK calls `/api/chat` not `/v1/chat/completions`. Gets 404.
**Why it happens:** Both SDKs speak to similar endpoints but different REST paths.
**How to avoid:** The URL-based SDK detection resolves this; any non-localhost, non-ollama.com URL must use `AsyncOpenAI`, not `ollama.Client`.
**Warning signs:** 404 errors from OpenAI/Groq during testing.

### Pitfall 2: asyncio.run() in Already-Running Event Loop
**What goes wrong:** `validate_provider_startup()` calls `asyncio.run(ping())` but graphiti-core operations are already inside `asyncio.run()` in `run_graph_operation()`. Raises `RuntimeError: This event loop is already running`.
**Why it happens:** Startup ping must run synchronously from CLI, but uses async openai SDK.
**How to avoid:** Call `validate_provider_startup()` in `cli_entry()` before `app()` (or early in Typer callback), never inside an async context. Use `asyncio.run()` only at the outermost call site.
**Warning signs:** `RuntimeError: This event loop is already running` in test or CLI.

### Pitfall 3: embed_api_key Fallback Not Applied
**What goes wrong:** `embed_api_key` is optional in TOML; if user omits it, `OpenAIEmbedder` gets `api_key=None` and every embed call fails with 401.
**Why it happens:** `load_config()` sets `llm_embed_api_key = llm_section.get("embed_api_key", None)` without applying fallback.
**How to avoid:** In `load_config()`: `llm_embed_api_key = llm_section.get("embed_api_key") or llm_section.get("primary_api_key")`. Apply the fallback at parse time, not at use time.
**Warning signs:** All embeddings return 401 when `embed_api_key` is not explicitly set.

### Pitfall 4: Startup Ping Adds Perceptible Latency
**What goes wrong:** Every `graphiti search` takes 2+ seconds just for the startup ping.
**Why it happens:** `models.list()` makes a network call on every invocation.
**How to avoid:** Set a short timeout (1–2 seconds connect, 3 seconds read). If the endpoint is unreachable within that window, fail fast. Do NOT retry the ping — one attempt only. `AsyncOpenAI(timeout=httpx.Timeout(connect=1.0, read=3.0, write=2.0, pool=5.0))`.
**Warning signs:** `graphiti health` takes >3 seconds; any `graphiti` command feels sluggish.

### Pitfall 5: `_is_cloud_available("embed")` Hardcode Must Be Removed
**What goes wrong:** The existing `OllamaClient._is_cloud_available()` contains `if operation == "embed": return False`. When `[llm]` section configures `embed_url`, this legacy hardcode in the old path is a red herring — but if any code still routes through `OllamaClient` for embed after Phase 13, this hardcode silently ignores the `embed_url` config.
**Why it happens:** Phase 13 removes the hardcode by making the `ProviderClient` path (not `OllamaClient`) handle all embed when `[llm]` is present.
**How to avoid:** Document clearly: `OllamaClient` is the legacy path (no `[llm]` section). `ProviderClient` is the new path (`[llm]` present). Never mix paths.

### Pitfall 6: OpenAIGenericClient Response Format Incompatibility
**What goes wrong:** Some local openai-compatible endpoints (Ollama in OpenAI-compat mode, LM Studio) don't support `response_format={"type": "json_schema", ...}`. They fall back to returning JSON text that `OpenAIGenericClient` may fail to parse.
**Why it happens:** `OpenAIGenericClient._generate_response()` always sends `json_schema` response_format. Local openai-compatible servers often only support `json_object` or ignore the parameter.
**How to avoid:** For `fallback_url` that is Ollama (localhost), use the existing `OllamaLLMClient` path (Ollama SDK with `format=` constrained generation) rather than routing through `OpenAIGenericClient`. The SDK detection resolves this: localhost → Ollama SDK → `OllamaLLMClient`.
**Warning signs:** Fallback to Ollama endpoint returns garbled JSON or parse errors.

---

## Code Examples

### openai SDK base_url override (verified from graphiti-core source)

```python
# Source: graphiti_core/llm_client/openai_generic_client.py line 91
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="sk-...", base_url="https://api.groq.com/openai/v1")
# For Groq: base_url = "https://api.groq.com/openai/v1"
# For OpenAI: base_url = "https://api.openai.com/v1" (default if None)
# For local openai-compat: base_url = "http://localhost:11434/v1" (Ollama openai compat)
```

### openai SDK embeddings with base_url (verified from graphiti-core source)

```python
# Source: graphiti_core/embedder/openai.py line 52
from openai import AsyncOpenAI
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

embed_cfg = OpenAIEmbedderConfig(
    api_key="sk-...",
    base_url="https://api.openai.com/v1",
    embedding_model="text-embedding-3-small",
)
embedder = OpenAIEmbedder(config=embed_cfg)
# embedder.create("text") returns list[float]
# embedder.create_batch(["a", "b"]) returns list[list[float]] — batch call, not looped
```

### openai SDK startup ping (verified from SDK introspection)

```python
# Source: openai 2.17.0 AsyncOpenAI.models.list()
import asyncio
from openai import AsyncOpenAI, AuthenticationError, APIConnectionError

async def ping_openai_compatible(base_url: str, api_key: str | None) -> tuple[bool, str]:
    """Returns (ok, error_detail)."""
    client = AsyncOpenAI(
        api_key=api_key or "no-key",
        base_url=base_url,
        timeout=3.0,  # short timeout for startup ping
        max_retries=0,  # no retries on startup ping
    )
    try:
        await client.models.list()
        return True, ""
    except AuthenticationError:
        return False, "API key rejected (401)"
    except APIConnectionError as e:
        return False, f"Connection refused: {e}"
    except Exception as e:
        return False, str(e)
```

### LLMConfig new fields with load_config() parsing

```python
# Source: existing pattern in src/llm/config.py — follows [backend] section parsing
llm_section = config_data.get("llm", {})
if llm_section:
    llm_mode = "provider"
    llm_primary_url = llm_section.get("primary_url", "")
    llm_primary_api_key = llm_section.get("primary_api_key")
    llm_primary_models = llm_section.get("primary_models", [])
    llm_fallback_url = llm_section.get("fallback_url")
    llm_fallback_models = llm_section.get("fallback_models", [])
    llm_embed_url = llm_section.get("embed_url", llm_primary_url)
    llm_embed_api_key = llm_section.get("embed_api_key") or llm_primary_api_key
    llm_embed_models = llm_section.get("embed_models", [])
else:
    llm_mode = "legacy"
    llm_primary_url = None
    # ... all others None/empty
```

### Health row format (following Phase 12 Backend row pattern)

```python
# Source: src/cli/commands/health.py — _check_backend() pattern
from urllib.parse import urlparse

def _check_provider() -> list[dict]:
    """Returns list of health check dicts for provider/embed/fallback tiers."""
    config = load_config()
    if config.llm_mode != "provider":
        return []  # No [llm] section — skip provider rows

    rows = []
    # Primary tier
    parsed = urlparse(config.llm_primary_url)
    hostname = parsed.hostname or config.llm_primary_url
    sdk_name = "ollama" if _detect_sdk(config.llm_primary_url) == "ollama" else "openai"
    first_model = config.llm_primary_models[0] if config.llm_primary_models else "?"
    ok = asyncio.run(_ping(config.llm_primary_url, config.llm_primary_api_key))
    status = "ok" if ok else "error"
    rows.append({
        "name": "Provider",
        "status": status,
        "detail": f"{sdk_name}/{first_model} @ {hostname} [{'OK' if ok else 'UNREACHABLE'}]",
    })
    # Embed and fallback rows follow same pattern
    return rows
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cloud Ollama only (via ollama SDK) | Any OpenAI-compatible via `base_url` | Phase 13 | Groq, OpenAI, local openai-compat all supported |
| `_is_cloud_available("embed")` hardcoded False | URL-driven embed routing | Phase 13 | Embeddings can now use cloud providers |
| Single [cloud]/[local] config shape | Flat [llm] section with per-tier URLs | Phase 13 | Unified config; backward compatible |
| No startup validation for LLM | Lightweight ping on every command | Phase 13 | Consistent with Phase 12 Neo4j fail-fast |

**Deprecated/outdated after Phase 13:**
- `OllamaClient._is_cloud_available("embed")` hardcode returning `False`: superseded by URL-based routing in `ProviderClient`. Hardcode stays in `OllamaClient` for the legacy path (no regressions), but `ProviderClient` never calls it.
- `_check_ollama_cloud()` and `_check_ollama_local()` in `health.py`: these check the old cloud/local Ollama health. When `[llm]` is present, the new `_check_provider()` replaces them. Both old checks can be skipped for the `[llm]` path.

---

## Key Integration Points

### Where Changes Land

1. **`src/llm/config.py`** — HIGHEST CHANGE DENSITY
   - Add 9 new `llm_*` fields to `LLMConfig` frozen dataclass (all with defaults so existing callers don't break)
   - Add `[llm]` section parsing in `load_config()` after existing section parsing
   - When `[llm]` present, set `llm_mode = "provider"`; `[cloud]`/`[local]` values still parsed but ignored by routing layer

2. **`src/llm/provider.py`** — NEW FILE
   - `_detect_sdk(url: str) -> Literal["ollama", "openai"]` — URL-based detection
   - `ProviderClient` — holds async clients for primary/fallback/embed tiers; exposes `ping_primary()`, `ping_embed()`, `chat()`, `embed()`, `current_provider_label()`
   - `validate_provider_startup(config: LLMConfig)` — synchronous, calls `asyncio.run()`, `sys.exit(1)` on failure

3. **`src/graph/adapters.py`** or `src/graph/service.py` — ROUTING FACTORY
   - Add `make_llm_client(config: LLMConfig)` and `make_embedder(config: LLMConfig)` functions
   - `make_llm_client`: if `llm_mode == "provider"` and primary SDK is openai → return `OpenAIGenericClient`; if ollama → return `OllamaLLMClient`
   - `make_embedder`: if `llm_mode == "provider"` → `OpenAIEmbedder` or `OllamaEmbedder` based on embed URL
   - `GraphService.__init__()` calls these factories instead of hardcoding `OllamaLLMClient()`

4. **`src/cli/commands/health.py`** — PROVIDER ROWS
   - Add `_check_provider() -> list[dict]` that returns 0–3 rows (provider/embed/fallback)
   - Insert rows into `checks` list before backend/quota rows
   - Rows only shown when `[llm]` is configured; unconfigured tiers omitted entirely

5. **`src/cli/__init__.py`** — STARTUP VALIDATION HOOK
   - Call `validate_provider_startup(load_config())` at the start of `cli_entry()` or in the Typer `@app.callback`
   - Must run BEFORE `app()` to catch auth errors before any graph operation

6. **`src/llm/__init__.py`** — OPTIONAL UPDATE
   - `get_provider_client()` convenience function (mirrors `get_client()`)
   - `reset_provider_client()` for test isolation

### What Does NOT Change
- `OllamaClient` — untouched; still used when `[llm]` absent
- `OllamaLLMClient`, `OllamaEmbedder` in `adapters.py` — untouched; still used for local/fallback Ollama
- All existing tests — must continue to pass (no `[llm]` in test configs = legacy path)
- `graphiti config init` template — existing `[cloud]`/`[local]` template format preserved

---

## Open Questions

1. **Where exactly in the CLI to hook startup validation**
   - What we know: Phase 12 Neo4j check is inside `graph_manager.py` (called when driver is first opened). That pattern requires an operation to trigger it — not on every command.
   - What's unclear: CONTEXT.md says "every `graphiti` command invocation". The Typer `@app.callback` runs before every subcommand including `graphiti help` and `graphiti config`. Should we skip the ping for `health` (it does its own) and `config` (no graph ops)?
   - Recommendation: Hook in `@app.callback` but skip when `ctx.invoked_subcommand in ("health", "config")`. Or hook only in graph operation entry points.

2. **OpenAIGenericClient's `generate_response` vs `_generate_response` return type**
   - What we know: `OpenAIGenericClient._generate_response()` returns `dict[str, Any]`. `OllamaLLMClient._generate_response()` also returns `dict[str, Any]`. Both implement the same `LLMClient` ABC method — should be drop-in.
   - What's unclear: `OpenAIGenericClient` was updated to use `(response, input_tokens, output_tokens)` return from `_generate_response` internally in `generate_response`. The public `generate_response()` method returns `dict[str, Any]` which is what graphiti-core calls. Adapter compatibility is through the public interface, not `_generate_response`. No issue expected.
   - Recommendation: Use `OpenAIGenericClient` as-is; do not call `_generate_response` directly.

3. **Groq embedding support**
   - What we know: Groq's openai-compatible API (`api.groq.com/openai/v1`) supports chat but embedding models are limited (Groq uses a different embed endpoint).
   - What's unclear: Whether `OpenAIEmbedder` with `base_url="https://api.groq.com/openai/v1"` works for Groq embed.
   - Recommendation: Document in TOML comments that `embed_url` for Groq should be a separate provider (e.g., OpenAI for embeddings). This is a user concern, not a code concern — the code is provider-agnostic.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options] asyncio_mode = "strict"` |
| Quick run command | `pytest tests/test_llm_config.py tests/test_provider.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROV-01 | `[llm]` section parsed; `llm_mode == "provider"` | unit | `pytest tests/test_llm_config.py::test_llm_section_sets_provider_mode -x` | ❌ Wave 0 |
| PROV-01 | SDK auto-detection: localhost → ollama, api.openai.com → openai | unit | `pytest tests/test_provider.py::test_detect_sdk_by_url -x` | ❌ Wave 0 |
| PROV-01 | `make_llm_client()` returns `OpenAIGenericClient` when `[llm]` openai URL | unit | `pytest tests/test_provider.py::test_make_llm_client_openai -x` | ❌ Wave 0 |
| PROV-02 | No `[llm]` section → `llm_mode == "legacy"` → `OllamaLLMClient` returned | unit | `pytest tests/test_llm_config.py::test_legacy_mode_when_no_llm_section -x` | ❌ Wave 0 |
| PROV-02 | Existing `[cloud]`/`[local]` TOML parses without error when no `[llm]` section | unit | `pytest tests/test_llm_config.py::test_old_cloud_local_sections_work -x` | ✅ (existing coverage) |
| PROV-03 | `_check_provider()` returns empty list when `llm_mode == "legacy"` | unit | `pytest tests/test_health_command.py::test_provider_rows_absent_when_legacy -x` | ❌ Wave 0 |
| PROV-03 | Health row format matches spec: `openai/gpt-4o-mini @ api.openai.com [OK]` | unit | `pytest tests/test_health_command.py::test_provider_row_format -x` | ❌ Wave 0 |
| PROV-04 | `validate_provider_startup()` calls `sys.exit(1)` when ping fails | unit | `pytest tests/test_provider.py::test_startup_validation_fails_fast -x` | ❌ Wave 0 |
| PROV-04 | `validate_provider_startup()` passes when ping succeeds | unit | `pytest tests/test_provider.py::test_startup_validation_passes -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_llm_config.py tests/test_provider.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_provider.py` — covers PROV-01, PROV-04 (SDK detection, factory, startup validation)
- [ ] `tests/test_llm_config.py` — extend with `[llm]` section test cases for PROV-01, PROV-02
- [ ] `tests/test_health_command.py` — covers PROV-03 (health row format)

*(Existing `tests/test_llm_config.py` and `tests/test_llm_client.py` cover legacy path — no changes needed there, extend only)*

---

## Sources

### Primary (HIGH confidence)
- `graphiti-core 0.28.1` installed source — `openai_generic_client.py`, `openai_base_client.py`, `embedder/openai.py`, `llm_client/config.py` — read directly from `.venv`
- `openai 2.17.0` SDK — `AsyncOpenAI` signature, `models.list()`, exception types (`AuthenticationError`, `APIConnectionError`) — verified via `python -c "import openai; ..."` in project venv
- `src/llm/config.py`, `src/llm/client.py`, `src/graph/adapters.py`, `src/cli/commands/health.py`, `src/cli/__init__.py` — read directly; all integration points confirmed

### Secondary (MEDIUM confidence)
- CONTEXT.md Phase 13 — decisions locked by user discussion; treated as authoritative specification
- STATE.md, ROADMAP.md — phase context and ordering confirmed

### Tertiary (LOW confidence)
- None — all findings verified from installed source code

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — openai SDK already installed, graphiti-core clients read directly from venv
- Architecture: HIGH — integration points identified by reading all affected files; no assumptions
- Pitfalls: HIGH — derived from code inspection (hardcoded `_is_cloud_available("embed")`, asyncio re-entrancy risk, etc.)

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable libraries; graphiti-core 0.28.1 pinned)

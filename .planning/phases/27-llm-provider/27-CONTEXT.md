# Phase 27: LLM Provider - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Pre-planning discussion

<domain>
## Phase Boundary

Implement `src/llm/` — a single-provider LLM client that reads config, sends chat requests, and reports health. No fallback logic anywhere. Implements `recall health` command (wired in Phase 29 but the health-check logic lives here).

</domain>

<decisions>
## Implementation Decisions

### Claude provider: subprocess only
- Use `claude -p` subprocess via `shutil.which("claude")` — existing v2.0 pattern
- Do NOT use the Anthropic SDK (`anthropic.Anthropic()`) — no API key requirement
- If `claude` binary not found: fail with clear error naming the missing binary

### Default claude model
- Default model: `claude-haiku-4-5-20251001`
- User can override via `model` key in `[llm]` config section

### Provider routing
- `provider = "claude"` → subprocess `claude -p --model <model>`
- `provider = "ollama"` → HTTP to `url` (default `http://localhost:11434`)
- `provider = "openai"` → HTTP to `url` with `api_key` in Authorization header
- Ollama cloud: same provider = "ollama" but with `api_key` set (sent as Bearer token)
- Single provider only — no fallback, no retry on different provider

### No fallback
- If the configured provider fails: exit with error message naming provider and URL
- Do NOT silently try another provider
- Retry on transient HTTP errors is acceptable (e.g. 1 retry with backoff), but not provider switching

### Health check logic
- Check if provider is reachable via a minimal ping/list request
- Return structured result: `{provider, model, status: "OK"|"UNREACHABLE", embeddings_status}`
- Must complete within 5 seconds (timeout)

### Config file format (canonical — all phases use this)
```toml
[llm]
provider = "claude"                    # claude | ollama | openai
model = "claude-haiku-4-5-20251001"   # default for claude
url = ""                               # ollama/openai only
api_key = ""                           # openai or ollama cloud

[embeddings]                           # optional — omit to disable
provider = "ollama"
model = "nomic-embed-text"
url = "http://localhost:11434"
api_key = ""                           # ollama cloud

[db]                                   # optional — omit for project-local default
path = ".recall/recall.db"
```

### Claude's Discretion
- Internal class/function structure of `src/llm/`
- Exact subprocess call format (follow existing `claude_cli_client.py` patterns for reference)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 27 success criteria
- `.planning/REQUIREMENTS.md` — LLM-01 through LLM-04
- `src/llm/claude_cli_client.py` — v2.0 subprocess client (reference implementation, will be replaced)
- `CLAUDE.md` — structlog usage, async patterns

</canonical_refs>

<deferred>
## Deferred Ideas

- Streaming responses — not needed for v3.0
- Multi-provider fallback — explicitly excluded by design

</deferred>

---
*Phase: 27-llm-provider*
*Context gathered: 2026-04-14 via pre-planning discussion*

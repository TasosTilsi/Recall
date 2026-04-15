# Phase 30: MCP Server - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning
**Source:** Pre-planning discussion

<domain>
## Phase Boundary

Rebuild `src/mcp_server/` as a read-only stdio MCP server with six knowledge tools. The Phase 25 stub is gutted — this phase replaces it with a real FastMCP implementation.

</domain>

<decisions>
## Implementation Decisions

### Transport: stdio only
- `recall mcp serve` starts the server on stdio
- NEVER print to stdout except valid MCP protocol frames
- All diagnostic logs to stderr only (use standard `logging` routed to stderr — NOT structlog, per CLAUDE.md)

### Six read-only tools
- `search_knowledge(query: str)` — FTS5 search via `src/db/`
- `get_entity(id: str)` — fetch single entity by ID
- `get_backlinks(entity_id: str)` — all backlinks for an entity with relationship labels
- `get_decisions(limit: int = 20)` — entities of type `decision`
- `get_bugs(limit: int = 20)` — entities of type `bug_fix`
- `get_patterns(limit: int = 20)` — entities of type `pattern`

### FastMCP
- Use FastMCP (existing dependency from v2.0) for the server implementation
- Follow existing `src/mcp_server/tools.py` structure as reference

### DB access
- Read-only queries via `src/db/` module (Phase 26)
- No LLM calls in MCP server — tools are pure DB reads

### Config file format (canonical)
```toml
[llm]
provider = "claude"
model = "claude-haiku-4-5-20251001"
url = ""
api_key = ""

[embeddings]
provider = "ollama"
model = "nomic-embed-text"
url = "http://localhost:11434"
api_key = ""

[db]
path = ".recall/recall.db"
```

### Claude's Discretion
- JSON response schema for each tool
- Error handling when DB not initialized

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 30 success criteria
- `.planning/REQUIREMENTS.md` — MCP-01, MCP-02
- `src/mcp_server/tools.py` — v2.0 MCP tools (reference structure, will be replaced)
- `CLAUDE.md` — MCP server logging rules (stderr only, no stdout)

</canonical_refs>

<deferred>
## Deferred Ideas

- Write tools (add entities manually) — v3.0 is read-only MCP
- SSE/HTTP transport — stdio only for v3.0

</deferred>

---
*Phase: 30-mcp-server*
*Context gathered: 2026-04-14 via pre-planning discussion*

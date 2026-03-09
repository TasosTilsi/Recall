# Phase 11: Graph UI - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

A `graphiti ui` command that launches a local-only graph visualization app — a Python FastAPI backend serving graph data + a Next.js TypeScript frontend rendering an interactive physics-based graph. No Docker, no Podman, local process only. Users can visually explore entity nodes and relationship edges across project or global scope.

</domain>

<decisions>
## Implementation Decisions

### Architecture
- **Backend**: Thin Python FastAPI server (`graphiti serve` internally) that queries the existing Kuzu DB via `GraphService` and returns JSON
- **Frontend**: Next.js + TypeScript — separate package, bundled with the Python project
- **Reusability**: The FastAPI backend is designed as a general-purpose `graphiti serve` foundation — the UI is its first consumer, but it can eventually host health/stats endpoints for the v2+ monitoring dashboard (UI-04) and could co-exist with the MCP HTTP transport
- FastAPI endpoints (minimum): `GET /api/graph` (all nodes + edges for scope), `GET /api/nodes/:uuid` (node detail)

### Process lifetime
- `graphiti ui` runs **foreground** — blocks the terminal, shows API and UI URLs on start, Ctrl+C cleanly shuts down both servers
- Display on launch:
  ```
  ┏ Graphiti UI
  ┃ API  → http://localhost:8765
  ┃ UI   → http://localhost:3000
  ┃ Scope: project (.graphiti/)
  ┗ Press Ctrl+C to stop
  ```
- No browser auto-open — print URL only. Works correctly on SSH/headless environments.

### Ports
- API server default: **8765** (avoids MCP HTTP conflict on 8000)
- Next.js UI default: **3000**
- Both configurable in `llm.toml` under a new `[ui]` section:
  ```toml
  [ui]
  api_port = 8765
  ui_port = 3000
  ```
- Same config pattern as `[retention]` and `[capture]` sections

### Scope
- Default scope: project (same as all other CLI commands — project graph when inside a git repo)
- `--global` flag: show global graph
- **In-UI scope toggle**: Project / Global toggle button in the header — clicking re-fetches graph data from API without restarting anything. No terminal interaction needed.

### Graph visualization
- **Library**: physics-based / force-directed family (react-force-graph, sigma.js, or similar — research will determine best fit for Next.js + TypeScript + 200–500 nodes + hierarchical-default requirement)
- **Default layout**: Hierarchical — readable at any node count
- **Force-directed toggle**: User can switch to physics-based layout (nodes float and settle with spring physics) via a toggle in the UI — ideal for exploring smaller subgraphs with cool animations
- **Visual style**: Smooth physics feel — dragging a node makes others respond fluidly

### Node coloring
- **Default color mode**: Color by entity type — each entity type (Decision, Architecture, Bug Fix, Dependency, Pattern, etc.) gets a distinct color
- **Alternate color mode**: Color by scope (global vs project nodes)
- **Toggle**: A color-mode toggle switch in the UI switches between the two modes live — no restart
- Dark mode optimized throughout
- A legend in the corner explains the active color mapping

### Node detail sidebar
- Clicking a node opens a **right sidebar panel** with full metadata:
  - Entity name + entity type
  - LLM-generated summary text
  - List of related nodes with edge labels (relationships)
  - Timestamps: `created_at`, `last_accessed_at`
  - Access count
  - Pinned status (from `retention.db`)
- Sidebar slides in from the right — does not displace the graph

### Search and filter
- **Search by name**: Text input in header — typing dims non-matching nodes and highlights matches in the graph (client-side, no API call)
- **Filter by type**: Dropdown to show only nodes of a specific entity type
- Both controls active simultaneously — additive filtering

### Empty / error states
- Graph loading: minimal spinner
- Empty graph (no nodes): helpful message — "No knowledge graph entries yet. Run `graphiti add` or `graphiti index` to populate."
- API unreachable: "Could not reach API — is `graphiti ui` running?"

### Claude's Discretion
- Exact graph visualization library (react-force-graph vs sigma.js vs vis-network — research determines best fit)
- Next.js project structure and build tooling (Vite vs next dev vs bundled static export)
- How Next.js frontend is shipped with the Python package (static build served by FastAPI, or spawned as a dev server)
- Exact color values for entity types (dark-mode optimized)
- Edge rendering style (curved vs straight, label visibility threshold)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/graph/service.py` — `GraphService` with `list_entities()`, `search()`, `get_stats()`. FastAPI backend will call these methods directly to serve `/api/graph` and `/api/nodes/:uuid`
- `src/llm/config.py` — `LLMConfig` dataclass + `load_config()`. Add `[ui]` section with `api_port` and `ui_port` fields (same pattern as `[retention]` and `[capture]`)
- `src/cli/commands/mcp.py` — MCP HTTP transport already uses port 8000 via FastMCP/Starlette. New UI API uses 8765 to avoid conflict. Pattern reference for spawning a server from CLI command.
- `src/cli/utils.py` — `resolve_scope()` for `--global` / `--project` flag handling — reuse in `graphiti ui` command
- `src/retention/manager.py` — `RetentionManager` for reading pin status and access counts from `retention.db` — needed for the node detail sidebar

### Established Patterns
- Scope flags: `--global` / `--project` with `resolve_scope()` — established in Phase 9, used everywhere
- `[section]` TOML config structure — `[ui]` follows `[retention]` and `[capture]` pattern
- Rich console output for CLI status messages
- structlog everywhere except `src/mcp_server/` (stderr-only)

### Integration Points
- New `graphiti ui` command registered in `src/cli/__init__.py`
- `LLMConfig` extended with `ui_api_port: int = 8765` and `ui_port: int = 3000`
- FastAPI backend reads Kuzu DB path from `resolve_scope()` output — same path resolution the CLI already uses
- `retention.db` queried for pin status + access counts in the node detail endpoint

</code_context>

<specifics>
## Specific Ideas

- The FastAPI backend is intentionally designed as a reusable `graphiti serve` foundation — not just throwaway UI plumbing. Future monitoring dashboard (UI-04, v2+) adds endpoints to the same server.
- "Smooth physics — nodes float and settle" is the target feel for force-directed mode. Dragging a node should make others respond fluidly.
- The scope toggle in the header re-fetches data without restarting — no terminal interaction needed after launch.
- The color-mode toggle (by type vs by scope) is a live switch in the UI.

</specifics>

<deferred>
## Deferred Ideas

- Monitoring dashboard tab (capture stats, queue depth, entity count over time) — noted as UI-04 in REQUIREMENTS.md v2+ backlog
- Real-time streaming updates (WebSocket) — UI-05, v2+ backlog
- Docker/Podman deployment — explicitly deferred to next milestone (v2.0)
- Inline graph editing — explicitly out of scope (UI must be read-only; editing bypasses the CLI security layer)

</deferred>

---

*Phase: 11-graph-ui*
*Context gathered: 2026-03-08*

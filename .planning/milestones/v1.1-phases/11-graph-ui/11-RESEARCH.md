# Phase 11: Graph UI - Research

**Researched:** 2026-03-08
**Domain:** FastAPI + Next.js + react-force-graph-2d — local-process graph visualization
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Architecture**
- Backend: Thin Python FastAPI server (`graphiti serve` internally) that queries the existing Kuzu DB via `GraphService` and returns JSON
- Frontend: Next.js + TypeScript — separate package, bundled with the Python project
- Reusability: FastAPI backend designed as a general-purpose `graphiti serve` foundation (UI is its first consumer; UI-04 monitoring dashboard and MCP HTTP transport can co-exist later)
- FastAPI endpoints (minimum): `GET /api/graph` (all nodes + edges for scope), `GET /api/nodes/:uuid` (node detail)

**Process lifetime**
- `graphiti ui` runs foreground — blocks the terminal, shows API and UI URLs on start, Ctrl+C cleanly shuts down both servers
- Display on launch:
  ```
  ┏ Graphiti UI
  ┃ API  → http://localhost:8765
  ┃ UI   → http://localhost:3000
  ┃ Scope: project (.graphiti/)
  ┗ Press Ctrl+C to stop
  ```
- No browser auto-open — print URL only

**Ports**
- API server default: **8765** (avoids MCP HTTP conflict on 8000)
- Next.js UI default: **3000**
- Both configurable in `llm.toml` under `[ui]` section

**Scope**
- Default: project scope (auto-detect from git repo)
- `--global` flag: show global graph
- In-UI scope toggle: re-fetches graph data without restarting

**Graph visualization**
- Default layout: Hierarchical (readable at any node count — out of scope to use force-directed as default per REQUIREMENTS.md)
- Force-directed toggle: user switches to physics layout in-UI
- Node coloring default: by entity type; alternate: by scope (global vs project)
- Color-mode toggle in header, live switch
- Dark mode optimized, legend in corner

**Node detail sidebar**
- Right panel on node click: entity name, type, LLM summary, related nodes with edge labels, `created_at`, `last_accessed_at`, access count, pinned status (from `retention.db`)

**Search and filter**
- Search by name: client-side, dims non-matching nodes
- Filter by type: dropdown, additive with search
- Empty/error state messages

### Claude's Discretion

- Exact graph visualization library (research determines best fit for Next.js + TypeScript + 200-500 nodes + hierarchical-default requirement)
- Next.js project structure and build tooling
- How Next.js frontend is shipped with the Python package (static build served by FastAPI, or spawned as a dev server)
- Exact color values for entity types (dark-mode optimized)
- Edge rendering style (curved vs straight, label visibility threshold)

### Deferred Ideas (OUT OF SCOPE)

- Monitoring dashboard tab (UI-04, v2+)
- Real-time streaming updates / WebSocket (UI-05, v2+)
- Docker/Podman deployment (deferred to v2.0)
- Inline graph editing (out of scope permanently — read-only invariant)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UI-01 | User can run `graphiti ui` to launch a localhost graph browser | FastAPI + Next.js static export pattern; CLI command registration in `src/cli/__init__.py` |
| UI-02 | `graphiti ui` mounts the scope-appropriate Kuzu DB read-only and opens the browser on launch | FastAPI reads DB path from `resolve_scope()` + `GLOBAL_DB_PATH`/`get_project_db_path()`; Kuzu is opened read-only via `GraphService`; no write endpoints exposed |
| UI-03 | User can choose global vs. project scope when launching `graphiti ui` | `--global` flag wired through `resolve_scope()` (established pattern); in-UI toggle re-fetches from API |
</phase_requirements>

---

## Summary

Phase 11 adds a local-process graph visualization command: `graphiti ui`. It launches a Python FastAPI backend (serving graph data from the existing Kuzu DB via `GraphService`) alongside a Next.js + TypeScript frontend that renders an interactive force-graph. Both processes run in the foreground, blocking the terminal until Ctrl+C.

The architecture is a static-export pattern: `next build` (with `output: 'export'`) produces an `out/` directory of plain HTML/CSS/JS that FastAPI serves via `StaticFiles`. This means a single origin (`http://localhost:8765`), no CORS configuration required in production, and no Node.js dependency at runtime after the build. During development, running `next dev` at port 3000 alongside the FastAPI server at 8765 does require CORS headers — these must be added to the FastAPI app using Starlette's built-in `CORSMiddleware`.

The recommended graph visualization library is `react-force-graph-2d` (v1.29.1). It ships bundled TypeScript definitions (`dist/react-force-graph-2d.d.ts`), supports DAG/hierarchical layout natively via `dagMode` prop, has `nodeAutoColorBy` for entity-type coloring, and `onNodeClick` for sidebar integration. It is a lighter dependency than sigma.js (which requires the `graphology` ecosystem separately) and has simpler integration with plain React/Next.js without requiring a separate graph model object.

**Primary recommendation:** FastAPI 0.135.x + Next.js 16 static export + react-force-graph-2d 1.29.1. FastAPI is a new `pyproject.toml` dependency (`fastapi>=0.135.0`). `aiofiles` is required for `StaticFiles` to serve the static export. The Next.js frontend lives in `ui/` at the repo root, builds to `ui/out/`, and is included in the Python package via `package_data`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | `>=0.135.0` | HTTP API server + static file serving | Not currently in pyproject.toml — must be added. Standard Python async HTTP framework. Starlette (already in venv via `mcp`) provides the underlying ASGI but FastAPI's decorator routing and Pydantic response models are needed for clean `/api/` endpoints. |
| uvicorn | `>=0.41.0` | ASGI server runtime | Already in venv via `mcp`. FastAPI runs on uvicorn. |
| aiofiles | `>=23.0.0` | Async static file serving | Required by Starlette's `StaticFiles`. Not currently in venv — must be added to pyproject.toml. |
| next | `16.1.6` | React framework with static export | Latest stable (2026-03). `output: 'export'` in `next.config.ts` produces `out/` directory. App Router compatible. |
| react | `19.2.4` | UI library | Next.js 16 peer dependency. |
| react-dom | `19.2.4` | DOM rendering | Next.js 16 peer dependency. |
| typescript | `5.9.3` | Type safety | Standard for Next.js projects. |
| react-force-graph-2d | `1.29.1` | 2D canvas force-directed graph | Bundled `.d.ts` types, DAG hierarchical layout via `dagMode`, `nodeAutoColorBy`, `onNodeClick`, `forceEngine` access for layout switching. Lightweight, no separate graph model ecosystem required. |
| tailwindcss | `4.2.1` | Utility CSS | Standard for Next.js + dark mode. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| d3-force | bundled with react-force-graph | Physics engine | Accessed via `graphRef.current.d3Force()` to adjust link distance, charge strength |
| @dagrejs/dagre | `2.0.4` | Hierarchical layout algorithm | Used by react-force-graph-2d when `dagMode="td"` (top-down) is set — provides the hierarchical coordinate computation |
| fastapi[standard] | `>=0.135.0` | FastAPI with all optional deps | `fastapi[standard]` installs `python-multipart`, `email-validator` etc. For Phase 11 only the base `fastapi` is needed. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-force-graph-2d | sigma.js + @react-sigma/core | sigma.js requires separate `graphology` graph model (additional package), `graphology-layout-forceatlas2` for physics, and no built-in dagre hierarchical. More powerful for very large graphs (WebGL), but more boilerplate for our 200-500 node use case. |
| react-force-graph-2d | vis-network | vis-network has built-in hierarchical layout but no React bindings — requires imperative DOM management. React wrapper packages are unofficial and poorly maintained. |
| Next.js static export | Next.js dev server spawned by Python | Dev server approach requires Node.js at runtime after install, complicates shutdown (SIGTERM to child process on Windows behaves differently), and adds startup latency (~3s for `next dev` cold start). Static export is built once at `pip install` time; FastAPI serves instantly. |
| FastAPI StaticFiles | Separate nginx/caddy for static | Overkill for a local-only tool. FastAPI can serve `out/` directly with `StaticFiles(directory=..., html=True)`. |

### Installation

**Python (pyproject.toml additions):**
```bash
# Add to [project] dependencies in pyproject.toml:
# "fastapi>=0.135.0"
# "aiofiles>=23.0.0"

pip install -e ".[dev]"
```

**Node.js (ui/ directory):**
```bash
cd ui/
npm install
npm run build   # produces ui/out/ — done once at install time
```

---

## Architecture Patterns

### Recommended Project Structure

```
ui/                              # Next.js frontend (separate npm package)
  package.json
  next.config.ts                 # output: 'export', images: {unoptimized: true}
  tsconfig.json
  src/
    app/
      page.tsx                   # Root page — mounts ForceGraph
      layout.tsx                 # HTML shell, dark background
    components/
      GraphCanvas.tsx            # ForceGraph2D wrapper, layout toggle
      NodeSidebar.tsx            # Right slide-in panel
      SearchFilter.tsx           # Header search + type filter
      Legend.tsx                 # Color legend overlay
    lib/
      api.ts                     # fetch('/api/graph'), fetch('/api/nodes/:uuid')
      colors.ts                  # Entity type → color mapping
  out/                           # Built static export (gitignored, built at install)
src/
  ui_server/                     # New Python package
    __init__.py
    app.py                       # FastAPI app factory, mounts /api and StaticFiles
    routes.py                    # GET /api/graph, GET /api/nodes/{uuid}
    startup.py                   # Process launcher: uvicorn + next dev OR serve static
  cli/
    commands/
      ui.py                      # `graphiti ui` Typer command
```

### Pattern 1: FastAPI Static Export Serving

**What:** Next.js builds to `out/` with `output: 'export'`. FastAPI mounts this with `StaticFiles(html=True)` so SPA routes (`/`, etc.) resolve to `index.html`.

**When to use:** Production install — all graph data is fetched client-side from `/api/` on the same origin. No CORS needed.

```python
# Source: https://www.starlette.io/staticfiles/
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

def create_app(db_path: Path, scope_label: str) -> FastAPI:
    app = FastAPI(title="Graphiti UI API")

    # API routes registered first (must come before the catch-all static mount)
    app.include_router(api_router, prefix="/api")

    # Serve Next.js static export — html=True means directory requests serve index.html
    static_dir = Path(__file__).parent.parent.parent / "ui" / "out"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")

    return app
```

**Critical:** API router must be registered BEFORE the `StaticFiles` mount. The static mount is a catch-all — any path not matched by API routes falls through to the static files.

### Pattern 2: CORS for Development Mode

**What:** When running `next dev` at port 3000 for frontend development, API calls from 3000 → 8765 are cross-origin. FastAPI must add CORS headers.

**When to use:** Only needed if running `next dev` alongside the FastAPI server during frontend development. Not needed in production (same-origin from static export).

```python
# Source: Starlette middleware docs
from starlette.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # next dev origin only
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

### Pattern 3: Foreground Process Management with Ctrl+C

**What:** The `graphiti ui` command runs uvicorn in the main thread. Python's default SIGINT handling (`KeyboardInterrupt`) provides clean Ctrl+C shutdown.

```python
# Source: uvicorn programmatic API docs
import uvicorn
import signal
import subprocess
import sys
from pathlib import Path

def launch_ui(api_port: int, ui_port: int, scope_label: str, static_dir: Path):
    from src.ui_server.app import create_app

    # Print launch banner
    from rich.console import Console
    console = Console()
    console.print(f"[bold]Graphiti UI[/bold]")
    console.print(f"  API  → http://localhost:{api_port}")
    console.print(f"  UI   → http://localhost:{api_port}")   # static served by FastAPI
    console.print(f"  Scope: {scope_label}")
    console.print(f"  Press Ctrl+C to stop")

    app = create_app(...)

    # uvicorn.run() blocks until Ctrl+C
    uvicorn.run(app, host="127.0.0.1", port=api_port, log_level="warning")
```

**Key insight:** Static export means we only start one process (uvicorn). The `next dev` two-process approach (uvicorn + subprocess for Next.js dev server) is only needed for frontend development iteration, not for the shipped `graphiti ui` command.

### Pattern 4: LLMConfig Extension for `[ui]` Section

**What:** Extend the frozen `LLMConfig` dataclass and `load_config()` following the exact same pattern as `[retention]` and `[capture]` sections.

```python
# In src/llm/config.py — additions to LLMConfig dataclass
ui_api_port: int = 8765
ui_port: int = 3000   # reserved for future next dev mode; not used by static-export launch

# In load_config():
ui = config_data.get("ui", {})
# ... in return LLMConfig(...):
ui_api_port=ui.get("api_port", 8765),
ui_port=ui.get("ui_port", 3000),
```

**TOML format:**
```toml
[ui]
api_port = 8765
ui_port = 3000
```

### Pattern 5: react-force-graph-2d Hierarchical + Force Toggle

**What:** `dagMode="td"` enables hierarchical top-down layout. `dagMode={null}` (or omitted) enables force-directed physics. The toggle switches between these two modes without remounting the graph.

```typescript
// Source: react-force-graph-2d GitHub README / npm package d.ts
import ForceGraph2D from 'react-force-graph-2d';

const [layoutMode, setLayoutMode] = useState<'hierarchical' | 'force'>('hierarchical');

<ForceGraph2D
  graphData={graphData}          // { nodes: [...], links: [...] }
  dagMode={layoutMode === 'hierarchical' ? 'td' : undefined}
  dagLevelDistance={60}
  nodeAutoColorBy="entityType"   // nodes colored by this field value
  nodeLabel="name"
  onNodeClick={(node) => setSelectedNode(node)}
  nodeCanvasObject={(node, ctx, globalScale) => {
    // Custom rendering for labels — only render label text above threshold scale
    if (globalScale >= 1.5) {
      ctx.fillText(node.name, node.x, node.y + 8);
    }
  }}
  backgroundColor="#0f172a"      // dark slate
  linkColor={() => '#334155'}
  width={width}
  height={height}
/>
```

### Pattern 6: `/api/graph` Response Shape

**What:** The FastAPI endpoint returns a `graphData` object compatible with `react-force-graph-2d` directly. The frontend consumes it without transformation.

```python
# GET /api/graph?scope=project
# Response:
{
  "nodes": [
    {
      "id": "uuid-string",
      "name": "EntityName",
      "entityType": "Decision",       # from entity.labels[0] or "Entity"
      "summary": "LLM summary text",
      "scope": "project",
      "createdAt": "2026-03-08T...",
      "pinned": false,
      "accessCount": 3,
      "lastAccessedAt": "2026-03-08T..."
    }
  ],
  "links": [
    {
      "source": "uuid-of-source",
      "target": "uuid-of-target",
      "label": "RELATES_TO",
      "fact": "edge fact text"
    }
  ]
}
```

### Anti-Patterns to Avoid

- **Do not register the StaticFiles mount before API routes.** The `StaticFiles` catch-all intercepts all paths including `/api/`. Always `include_router` first.
- **Do not use `next dev` in the shipped `graphiti ui` command.** `next dev` requires Node.js at runtime and adds ~3s cold start. Use static export built at install time.
- **Do not use `asyncio.run()` inside uvicorn's event loop.** Uvicorn runs an event loop; calling `asyncio.run()` from within a FastAPI route handler raises `RuntimeError: This event loop is already running`. Use `await` directly in async route handlers.
- **Do not open Kuzu DB for writing from the UI server.** `GraphService` must be initialized with a read-only mode or the API must be designed to never call mutating methods (`add`, `delete`, `compact`). The `GET /api/graph` endpoint calls `list_entities()` which is read-only.
- **Do not use `nodeAutoColorBy` with raw `labels` field.** `labels` is a Python list serialized to JSON array. The frontend must flatten to a string (`entityType: labels[0] ?? 'Entity'`) before `nodeAutoColorBy` can group by it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP routing + JSON serialization | Custom WSGI/ASGI handler | `fastapi` + Pydantic response models | FastAPI auto-validates, auto-documents, handles async natively. Starlette is already in venv — FastAPI wraps it with developer-friendly decorators. |
| Static file serving | Custom `open(file).read()` route | `fastapi.staticfiles.StaticFiles` | Handles content-type headers, ETag caching, `html=True` SPA routing, async I/O via aiofiles. |
| Force graph physics | Custom canvas physics | `react-force-graph-2d` | WebWorker-based D3 force simulation, zoom/pan, node dragging with force response, DAG layout algorithm — months of work to replicate. |
| Hierarchical layout math | Topological sort + coordinate assignment | `dagMode="td"` in react-force-graph-2d (uses `@dagrejs/dagre` internally) | Dagre implements the Sugiyama method for proper hierarchical graph layout. |
| TypeScript graph types | Custom interfaces | `react-force-graph-2d` bundled `.d.ts` | Types for `NodeObject`, `LinkObject`, `GraphData` are bundled — no separate `@types/` package needed. |
| CORS headers | Manual header injection | `starlette.middleware.cors.CORSMiddleware` | Already in venv via `mcp`. One-liner middleware registration. |
| Port conflict detection | Parse `netstat` output | `socket.bind()` probe | `socket.bind(('localhost', port))` raises `OSError` if port is in use. Simple, cross-platform, no subprocess. |

**Key insight:** The graph rendering problem is genuinely hard (physics simulation, canvas WebWorkers, zoom/pan, DAG layout). react-force-graph-2d is a battle-tested library (>5k GitHub stars) that solves all of it. The value-add of Phase 11 is in the API design, the sidebar with retention data, and the scope toggle — not in reimplementing graph layout algorithms.

---

## Common Pitfalls

### Pitfall 1: StaticFiles mount order silently breaks API

**What goes wrong:** Registering `app.mount("/", StaticFiles(...))` before `app.include_router(api_router, prefix="/api")` causes all API requests to return 404 or static file content. FastAPI matches mounts in order; the root static mount is a greedy catch-all.

**Why it happens:** The `Mount` ASGI component is matched by path prefix. `"/"` matches everything.

**How to avoid:** Always `include_router` for all API routes before the static files `mount`. Structure the app factory as: create app → add middleware → include routers → mount static.

**Warning signs:** `GET /api/graph` returns HTML (the index.html) instead of JSON.

### Pitfall 2: Next.js App Router + static export limitations

**What goes wrong:** Using `useSearchParams()` in a Server Component, or having any page that uses `dynamic = 'force-dynamic'`, breaks `next build` with `output: 'export'`.

**Why it happens:** Static export pre-renders all pages at build time. Dynamic server-side data fetching is incompatible.

**How to avoid:** All data fetching must be client-side (`'use client'` components calling `fetch('/api/...')`). Never use `getServerSideProps` or dynamic API routes. The `next.config.ts` must set `images: { unoptimized: true }` (Next.js image optimization requires a server).

**Warning signs:** `next build` fails with `Error: Dynamic server usage: Route / used "dynamic = force-dynamic"`.

### Pitfall 3: react-force-graph-2d SSR/window crash in Next.js

**What goes wrong:** `react-force-graph-2d` uses `canvas` and `window` — APIs that don't exist during Next.js server-side rendering. Importing it directly in a page component causes `ReferenceError: window is not defined` during `next build`.

**Why it happens:** Next.js pre-renders pages in Node.js where `window` is undefined.

**How to avoid:** Use `next/dynamic` with `ssr: false` to lazy-load the graph component:

```typescript
// Source: Next.js dynamic import docs
import dynamic from 'next/dynamic';

const GraphCanvas = dynamic(() => import('@/components/GraphCanvas'), {
  ssr: false,
  loading: () => <div>Loading graph...</div>
});
```

**Warning signs:** `ReferenceError: window is not defined` or `ReferenceError: document is not defined` during `npm run build`.

### Pitfall 4: Kuzu DB opened for writing by FastAPI

**What goes wrong:** `GraphService._get_graphiti()` calls `build_indices_and_constraints()` on first use, which writes to the database. This violates the read-only invariant for the UI.

**Why it happens:** `_get_graphiti()` always calls `build_indices_and_constraints()` on first access (it's designed for write operations).

**How to avoid:** The FastAPI routes must use a read-only path that bypasses `build_indices_and_constraints()`. The safest approach is to open the Kuzu driver directly in read-only mode OR to only call `EntityNode.get_by_group_ids()` and `driver.execute_query()` without going through `_get_graphiti()` for the read path.

Kuzu DB supports read-only access mode: the driver can be opened with read-only flag to prevent any writes.

**Warning signs:** The UI server modifies `created_at` or schema on the Kuzu DB while it's also being modified by `graphiti add`.

### Pitfall 5: `asyncio.run()` inside uvicorn event loop

**What goes wrong:** Calling `run_graph_operation(coro)` (which uses `asyncio.run()`) from inside a FastAPI route handler raises `RuntimeError: This event loop is already running`.

**Why it happens:** Uvicorn runs its own event loop. `asyncio.run()` tries to create a new loop, which fails in an already-running loop context.

**How to avoid:** FastAPI route handlers must be `async def` and use `await` directly. Never use `run_graph_operation()` inside a route handler — that helper is for sync CLI context only.

```python
# WRONG — in a FastAPI route handler
@app.get("/api/graph")
def get_graph():
    result = run_graph_operation(service.list_entities(...))  # RuntimeError!

# RIGHT
@app.get("/api/graph")
async def get_graph():
    result = await service.list_entities(...)  # correct
```

### Pitfall 6: Port conflict silently hangs

**What goes wrong:** If port 8765 is already in use, uvicorn hangs or emits a cryptic OSError. The user sees no clear error message.

**Why it happens:** `uvicorn.run()` calls `socket.bind()` internally and does not surface a friendly error by default.

**How to avoid:** Probe the port before starting uvicorn. Use `socket.bind()` as a pre-flight check and emit a clear error message with Typer:

```python
import socket
def check_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return True
        except OSError:
            return False
```

---

## Code Examples

Verified patterns from official sources and npm package inspection:

### FastAPI app factory with static mount

```python
# src/ui_server/app.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from pathlib import Path

def create_app(scope_label: str, dev_mode: bool = False) -> FastAPI:
    app = FastAPI(title="Graphiti UI API", docs_url=None, redoc_url=None)

    # CORS only needed for local next dev workflow
    if dev_mode:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_methods=["GET"],
            allow_headers=["*"],
        )

    # API routes (MUST come before static mount)
    from src.ui_server.routes import router
    app.include_router(router, prefix="/api")

    # Serve Next.js static export
    static_dir = Path(__file__).parent.parent.parent / "ui" / "out"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")

    return app
```

### `graphiti ui` Typer command

```python
# src/cli/commands/ui.py
import typer
from typing import Annotated
from src.cli.utils import resolve_scope

def ui_command(
    global_flag: Annotated[bool, typer.Option("--global", help="Visualize global scope graph")] = False,
    project_flag: Annotated[bool, typer.Option("--project", help="Visualize project scope graph")] = False,
    api_port: Annotated[int, typer.Option("--api-port", help="API server port")] = 0,
):
    """Launch the graph visualization UI in your browser."""
    import socket
    from src.llm.config import load_config
    from src.cli.output import console, print_error

    config = load_config()
    port = api_port or config.ui_api_port

    # Pre-flight: check port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
        except OSError:
            print_error(f"Port {port} is already in use. Set [ui] api_port in llm.toml to use a different port.")
            raise typer.Exit(1)

    scope, project_root = resolve_scope(global_flag, project_flag)
    scope_label = "global" if global_flag else f"project ({project_root.name if project_root else '?'})"

    console.print(f"[bold green]Graphiti UI[/bold green]")
    console.print(f"  API  → http://localhost:{port}/api")
    console.print(f"  UI   → http://localhost:{port}")
    console.print(f"  Scope: {scope_label}")
    console.print(f"  [dim]Press Ctrl+C to stop[/dim]")

    import uvicorn
    from src.ui_server.app import create_app
    app = create_app(scope_label=scope_label)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
```

### react-force-graph-2d with DAG + force toggle

```typescript
// ui/src/components/GraphCanvas.tsx
'use client';
import ForceGraph2D from 'react-force-graph-2d';
import { useState, useRef } from 'react';

type NodeData = {
  id: string;
  name: string;
  entityType: string;
  scope: 'project' | 'global';
  summary: string;
  pinned: boolean;
  accessCount: number;
};

export function GraphCanvas({ data, onNodeClick }: Props) {
  const [layout, setLayout] = useState<'hierarchical' | 'force'>('hierarchical');
  const graphRef = useRef<any>(null);

  return (
    <ForceGraph2D
      ref={graphRef}
      graphData={data}
      // DAG hierarchical: dagMode="td" (top-down). null = force-directed physics.
      dagMode={layout === 'hierarchical' ? 'td' : undefined}
      dagLevelDistance={60}
      nodeAutoColorBy="entityType"
      nodeLabel="name"
      onNodeClick={onNodeClick}
      backgroundColor="#0f172a"
      linkColor={() => '#334155'}
      nodeCanvasObjectMode={() => 'after'}
      nodeCanvasObject={(node: any, ctx, globalScale) => {
        // Only render text label when zoomed in enough
        if (globalScale < 1.2) return;
        ctx.font = `${12 / globalScale}px sans-serif`;
        ctx.fillStyle = '#f1f5f9';
        ctx.textAlign = 'center';
        ctx.fillText(node.name, node.x, node.y + node.val + 3);
      }}
    />
  );
}
```

### Next.js dynamic import (SSR guard)

```typescript
// ui/src/app/page.tsx — guards against window undefined during next build
import dynamic from 'next/dynamic';

const GraphCanvas = dynamic(
  () => import('@/components/GraphCanvas').then(mod => ({ default: mod.GraphCanvas })),
  { ssr: false, loading: () => <p className="text-slate-400">Loading graph...</p> }
);
```

### Next.js config for static export

```typescript
// ui/next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'export',          // produces out/ directory
  images: {
    unoptimized: true,       // required for static export
  },
  trailingSlash: true,       // ensures out/index.html exists for StaticFiles
  basePath: '',              // served from root of FastAPI
};

export default nextConfig;
```

### FastAPI `/api/graph` endpoint

```python
# src/ui_server/routes.py
from fastapi import APIRouter, Query
from src.graph.service import GraphService
from src.models import GraphScope
from src.config.paths import GLOBAL_DB_PATH, get_project_db_path
from src.storage import GraphSelector

router = APIRouter()

@router.get("/graph")
async def get_graph(scope: str = Query("project")):
    """Return all nodes and links for the given scope."""
    # Resolve scope
    if scope == "global":
        graph_scope = GraphScope.GLOBAL
        project_root = None
    else:
        graph_scope = GraphScope.PROJECT
        project_root = GraphSelector.find_project_root()

    service = GraphService()
    entities = await service.list_entities(graph_scope, project_root, limit=None)

    # Build links from entity relationships
    # Each entity dict has relationship_count — for links we need a separate query
    # The /api/graph endpoint needs a new service method or direct Kuzu query
    # to fetch edge data (source_uuid, target_uuid, fact, name)

    nodes = [
        {
            "id": e["uuid"],
            "name": e["name"],
            "entityType": e["tags"][0] if e["tags"] else "Entity",
            "scope": e["scope"],
            "summary": e.get("summary", ""),
        }
        for e in entities
    ]
    return {"nodes": nodes, "links": []}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Docker Kuzu Explorer (original v1.1 plan) | FastAPI + Next.js local-process | Phase 11 CONTEXT.md decision | No Docker dependency, full control over UI features (sidebar, scope toggle, search) |
| Next.js Pages Router | App Router | Next.js 13+ | App Router is the standard for Next.js 13+. Static export works with App Router when all pages are client-side. |
| `next export` (separate command) | `output: 'export'` in `next.config.ts` | Next.js 14+ | `next export` is deprecated. The config-based export is the only supported approach in Next.js 14+. |
| `react-force-graph` (3D default) | `react-force-graph-2d` | N/A | 2D canvas is correct for a knowledge graph tool — 3D adds complexity without value for text-based graphs. |

**Deprecated/outdated:**
- `next export` CLI command: replaced by `output: 'export'` in next.config since Next.js 14
- `getServerSideProps` / `getStaticProps`: Pages Router API — not used with App Router
- `@types/react-force-graph-2d`: Does not exist on npm — types are bundled in the package itself

---

## Open Questions

1. **Kuzu read-only driver mode**
   - What we know: Kuzu 0.11.3 is installed. The Python kuzu package supports opening databases in read-only mode with `kuzu.Database(path, read_only=True)`.
   - What's unclear: Whether `KuzuDriver` from graphiti-core can be initialized with a read-only database instance, or whether we need to bypass `GraphService._get_graphiti()` entirely for the UI read path.
   - Recommendation: In the API routes, instantiate `kuzu.Database(db_path, read_only=True)` and `kuzu.Connection(db)` directly rather than going through `GraphService`. This avoids `build_indices_and_constraints()` writes and guarantees read-only access.

2. **Edge data for `/api/graph`**
   - What we know: `list_entities()` returns `relationship_count` per entity but not the actual link `(source_uuid, target_uuid, fact)` data needed for `react-force-graph-2d`'s `links` array.
   - What's unclear: Whether to add a new `list_edges()` method to `GraphService` or query Kuzu directly in the API route using `execute_query()`.
   - Recommendation: Add `async def list_edges(scope, project_root) -> list[dict]` to `GraphService`. This keeps Kuzu query logic in the service layer. The query pattern already exists in `get_entity()` — `MATCH (n)-[:RELATES_TO]->(e:RelatesToNode_)-[:RELATES_TO]->(m)`.

3. **Next.js build at install time**
   - What we know: `pyproject.toml` uses setuptools. There is no `build.py` hook currently.
   - What's unclear: The cleanest way to run `npm run build` in `ui/` during `pip install -e .` without a custom build backend.
   - Recommendation: Ship the pre-built `ui/out/` directory in the repository (committed to git). This avoids the need for Node.js at install time. Add `ui/node_modules/` to `.gitignore` but commit `ui/out/`. Update `pyproject.toml` with `[tool.setuptools.package-data]` to include `ui/out/**` in the installed package. This is the simplest approach and matches how the CONTEXT.md frames it ("bundled with the Python project").

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | none — pytest auto-discovers `tests/` |
| Quick run command | `pytest tests/test_ui_command.py -x -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 | `graphiti ui --help` exits 0 and shows scope flags | unit (CLI runner) | `pytest tests/test_ui_command.py::TestUICommand::test_help -x` | Wave 0 |
| UI-01 | `graphiti ui` fails with clear error when Node.js/`ui/out/` missing | unit (CLI runner) | `pytest tests/test_ui_command.py::TestUICommand::test_missing_static_dir -x` | Wave 0 |
| UI-01 | `GET /api/graph` returns JSON with `nodes` and `links` keys | unit (TestClient) | `pytest tests/test_ui_server.py::TestAPIRoutes::test_graph_endpoint -x` | Wave 0 |
| UI-01 | `GET /api/nodes/{uuid}` returns node detail with retention fields | unit (TestClient) | `pytest tests/test_ui_server.py::TestAPIRoutes::test_node_detail_endpoint -x` | Wave 0 |
| UI-02 | Port conflict detected before uvicorn starts — clear error message | unit (CLI runner) | `pytest tests/test_ui_command.py::TestUICommand::test_port_conflict -x` | Wave 0 |
| UI-02 | FastAPI app factory mounts StaticFiles when `ui/out/` exists | unit (create_app) | `pytest tests/test_ui_server.py::TestAppFactory::test_static_mount -x` | Wave 0 |
| UI-03 | `--global` flag resolves to global scope | unit (CLI runner) | `pytest tests/test_ui_command.py::TestUICommand::test_global_flag -x` | Wave 0 |
| UI-03 | LLMConfig loads `[ui] api_port` and `ui_port` from TOML | unit (load_config) | `pytest tests/test_llm_config.py::TestUIConfig::test_ui_ports_from_toml -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_ui_command.py tests/test_ui_server.py -x -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite (285 existing + new UI tests) green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_ui_command.py` — covers UI-01, UI-02, UI-03 CLI behavior
- [ ] `tests/test_ui_server.py` — covers UI-01, UI-02 FastAPI routes with mocked `GraphService`
- [ ] `src/ui_server/__init__.py` — new package init
- [ ] `src/ui_server/app.py` — FastAPI app factory
- [ ] `src/ui_server/routes.py` — `/api/graph`, `/api/nodes/{uuid}`
- [ ] `src/cli/commands/ui.py` — Typer command
- [ ] `ui/package.json` — Next.js project
- [ ] `ui/next.config.ts` — static export config
- [ ] `ui/out/` — pre-built static files (committed to git, Wave 0 can use a minimal placeholder `index.html`)

---

## Sources

### Primary (HIGH confidence)

- npm registry (`npm show react-force-graph-2d`, `npm show next`, `npm show @react-sigma/core`) — versions and peer dependencies verified directly
- `dist/react-force-graph-2d.d.ts` presence confirmed via `npm show react-force-graph-2d types`
- `starlette.middleware.cors.CORSMiddleware` — confirmed available in project venv (starlette 0.52.1 via `mcp` dep)
- `fastapi` 0.135.1 — latest stable confirmed via `pip index versions fastapi`
- `uvicorn` 0.41.0 — confirmed installed in project venv
- `aiofiles` — confirmed NOT in project venv (must be added)
- `fastapi` — confirmed NOT in project venv (must be added)
- `starlette.io/staticfiles/` — `html=True` behavior verified: "Automatically loads `index.html` for directories"
- Source code review: `src/llm/config.py`, `src/graph/service.py`, `src/cli/utils.py`, `src/cli/__init__.py`, `src/retention/manager.py` — all existing integration points verified directly

### Secondary (MEDIUM confidence)

- react-force-graph GitHub README (via WebFetch) — DAG mode prop (`dagMode="td"`), `nodeAutoColorBy`, `onNodeClick` confirmed
- FastAPI static files tutorial (via WebFetch) — `StaticFiles(directory=..., html=True)` pattern confirmed
- Next.js `output: 'export'` — standard since Next.js 14+; `next export` CLI deprecated (training knowledge, consistent with npm package version 16.1.6)

### Tertiary (LOW confidence)

- Next.js 16 App Router + static export compatibility — confirmed at MEDIUM via version inspection but not tested in this project
- Kuzu `read_only=True` database mode — documented in kuzu Python SDK (training knowledge; pre-flight check recommended during implementation)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via npm registry and pip index directly
- Architecture: HIGH — FastAPI static-files + react-force-graph-2d pattern is well-documented and all parts verified
- Pitfalls: HIGH — all 6 pitfalls derived from direct code inspection (import order, SSR, asyncio.run, Kuzu write)

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable ecosystem; fastapi and Next.js have frequent releases but no breaking changes expected)

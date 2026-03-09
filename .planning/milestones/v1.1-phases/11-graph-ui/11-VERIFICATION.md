---
phase: 11-graph-ui
verified: 2026-03-09T11:00:00Z
status: human_needed
score: 9/10 must-haves verified
re_verification: false
human_verification:
  - test: "Run `graphiti ui` and open http://localhost:8765 in a browser"
    expected: "Page loads showing graph canvas area, header with scope/layout/color-mode toggles, search input, and type dropdown"
    why_human: "Plan 11-05 human-verify checkpoint was auto-approved by user directive — browser rendering was never confirmed by a human"
  - test: "Click a node in the graph"
    expected: "Right sidebar panel opens showing entity name, type, summary, created/last-accessed timestamps, and an X close button"
    why_human: "Node click sidebar interaction requires visual confirmation — automated tests mock the service layer, not the canvas interaction"
  - test: "Click 'Global' scope button in the header"
    expected: "Graph re-fetches and updates without server restart; URL visible in terminal stays the same"
    why_human: "Scope toggle re-fetch is a client-side behaviour not covered by automated tests"
  - test: "Type a name fragment in the search input"
    expected: "Non-matching nodes visually dim (become dark/slate colour) while matching nodes retain their colour"
    why_human: "Canvas colour dimming is a graphical effect not testable programmatically"
  - test: "Confirm no write/edit controls are visible anywhere in the UI"
    expected: "No Edit, Delete, Add, or Save buttons present anywhere in the rendered page"
    why_human: "Read-only invariant requires visual inspection of the rendered page"
  - test: "Run `graphiti ui --global` and confirm banner shows 'Scope: global'"
    expected: "Terminal banner prints 'Scope: global'; browser at http://localhost:8765 shows global graph data"
    why_human: "UI-03 global scope flag requires live run verification — test_global_flag only confirms the flag is accepted without parse error"
  - test: "Press Ctrl+C while `graphiti ui` is running"
    expected: "Server stops cleanly, terminal prints 'Graphiti UI stopped.' and returns to prompt"
    why_human: "KeyboardInterrupt shutdown path cannot be verified without running the process"
---

# Phase 11: Graph UI Verification Report

**Phase Goal:** Provide a graph visualization UI accessible via `graphiti ui` CLI command, displaying entities and relationships from the local Kuzu DB graph with interactive navigation.
**Verified:** 2026-03-09T11:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | `graphiti ui --help` exits 0 and shows `--global` flag | VERIFIED | All 4 TestUICommand tests GREEN; grep on ui.py confirms `--global` option |
| 2  | `graphiti ui` with port in use exits non-zero with "already in use" message | VERIFIED | `test_port_conflict` passes GREEN; socket.bind() pre-flight in ui.py confirmed |
| 3  | `graphiti ui` with ui/out/ missing exits non-zero with message about static files | VERIFIED | `test_missing_static_dir` passes GREEN; static_dir.exists() check in ui.py confirmed |
| 4  | `graphiti ui --global` resolves global scope without parse error | VERIFIED | `test_global_flag` passes GREEN; resolve_scope wired to global_scope flag |
| 5  | GET /api/graph returns {nodes: [...], links: [...]} | VERIFIED | `test_graph_endpoint` passes GREEN; routes.py confirmed returns exactly this shape |
| 6  | GET /api/nodes/{uuid} returns node detail with id, name, entityType, pinned, accessCount | VERIFIED | `test_node_detail_endpoint` passes GREEN; routes.py response confirmed |
| 7  | FastAPI app mounts StaticFiles AFTER API router (no catch-all override) | VERIFIED | `test_static_mount` passes GREEN; app.py confirmed: include_router before _RootMount append |
| 8  | LLMConfig has ui_api_port and ui_port loaded from [ui] TOML section | VERIFIED | `test_ui_ports_from_toml` passes GREEN; config.py lines 68-69, 155-156 confirmed |
| 9  | GraphService read-only methods use kuzu.Database(read_only=True) | VERIFIED | grep confirms `read_only=True` on lines 1150, 1192, 1241 of service.py; no _get_graphiti() calls in routes |
| 10 | Browser renders interactive graph at http://localhost:8765 | NEEDS HUMAN | Plan 11-05 human-verify checkpoint was auto-approved by user directive — actual browser rendering never confirmed |

**Score:** 9/10 truths verified (automated); 1 flagged for human verification

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_ui_command.py` | 4 CLI tests covering UI-01, UI-02, UI-03 | VERIFIED | 4 tests pass GREEN |
| `tests/test_ui_server.py` | 4 server tests covering UI-01, UI-02 | VERIFIED | 4 tests pass GREEN |
| `src/ui_server/__init__.py` | Package init | VERIFIED | Exists, importable |
| `src/ui_server/app.py` | FastAPI app factory `create_app()` | VERIFIED | Exists, substantive, exports `create_app`, wired via `include_router` before StaticFiles |
| `src/ui_server/routes.py` | GET /api/graph, GET /api/nodes/{uuid} | VERIFIED | Exists, substantive, exports `router`, uses read-only GraphService methods |
| `src/cli/commands/ui.py` | `graphiti ui` Typer command | VERIFIED | Exists, substantive (port pre-flight, scope resolution, uvicorn launch), imports `create_app` |
| `src/cli/__init__.py` | CLI registration of ui_command | VERIFIED | Line 77: import; line 139: app.command registration |
| `src/graph/service.py` | `list_edges()`, `list_entities_readonly()`, `get_entity_by_uuid()` | VERIFIED | All 3 methods present at lines 1133, 1174, 1224; all use `read_only=True` |
| `src/llm/config.py` | `ui_api_port` and `ui_port` fields | VERIFIED | Lines 68-69 (fields), 155-156 (load_config parsing) |
| `pyproject.toml` | `fastapi>=0.135.0` and `aiofiles>=23.0.0` deps | VERIFIED | Lines 7 and 9 confirmed |
| `ui/package.json` | npm package with react-force-graph-2d | VERIFIED | `"react-force-graph-2d": "1.29.1"` present |
| `ui/next.config.ts` | Static export config (`output: 'export'`) | VERIFIED | Line 4: `output: 'export'` confirmed |
| `ui/src/app/page.tsx` | Root page with `dynamic(..., { ssr: false })` | VERIFIED | Lines 10-12: GraphCanvas dynamic import with ssr:false |
| `ui/src/components/GraphCanvas.tsx` | ForceGraph2D wrapper with dagMode | VERIFIED | `import ForceGraph2D` and `dagMode` prop confirmed |
| `ui/src/lib/api.ts` | fetch helpers for /api/graph and /api/nodes/{uuid} | VERIFIED | `fetch(\`${API_BASE}/graph?scope=${scope}\`)` and `/api/nodes/` fetch confirmed |
| `ui/out/index.html` | Pre-built static export committed to git | VERIFIED | File exists; .gitignore excludes `ui/node_modules/` and `ui/.next/` but NOT `ui/out/` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/cli/__init__.py` | `src/cli/commands/ui.py` | `app.command(name="ui")(ui_command)` | WIRED | Lines 77 (import) + 139 (registration) confirmed |
| `src/cli/commands/ui.py` | `src/ui_server/app.py` | `create_app(...)` passed to `uvicorn.run()` | WIRED | Line 87: `from src.ui_server.app import create_app`; line 89: `create_app(...)` called |
| `src/ui_server/app.py` | `src/ui_server/routes.py` | `app.include_router(router, prefix="/api")` BEFORE StaticFiles | WIRED | Lines 62-63 confirmed; `_RootMount` appended after |
| `src/ui_server/routes.py` | `src/graph/service.py` | `await service.list_entities_readonly(...)` and `await service.list_edges(...)` | WIRED | Lines 58-61 of routes.py; methods exist in service.py at lines 1133, 1174 |
| `src/ui_server/routes.py` | `kuzu.Database(read_only=True)` | read-only DB in GraphService methods | WIRED | `read_only=True` confirmed at service.py lines 1150, 1192, 1241 |
| `ui/src/app/page.tsx` | `ui/src/components/GraphCanvas.tsx` | `dynamic(..., { ssr: false })` | WIRED | Lines 10-12 confirmed |
| `ui/src/lib/api.ts` | `/api/graph` | `fetch(\`${API_BASE}/graph?scope=${scope}\`)` | WIRED | Line 32 confirmed |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UI-01 | 11-01, 11-02, 11-03, 11-04 | `graphiti ui` launches FastAPI server at http://localhost:8765 — no Docker required | SATISFIED (automated) | `graphiti ui --help` confirmed; port pre-flight tested; create_app wired to uvicorn |
| UI-02 | 11-01, 11-02, 11-03, 11-04 | Mounts scope-appropriate Kuzu DB read-only, prints URL (no browser auto-open) | SATISFIED (automated) | `read_only=True` in all GraphService methods; URL printed via console.print in ui.py; no webbrowser.open call |
| UI-03 | 11-01, 11-03, 11-04 | User can choose global vs. project scope via `--global` flag | SATISFIED (automated) | `--global` flag accepted without parse error; `resolve_scope(global_flag=True)` called |

All three UI requirement IDs (UI-01, UI-02, UI-03) are marked `[x]` complete in `.planning/REQUIREMENTS.md`. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `pyproject.toml` | 42 | `# TODO: Phase 12 — add MANIFEST.in or data_files for ui/out/ in wheel builds` | Info | Intentional deferral — `ui/out/` is committed to git and resolves correctly for editable installs; wheel packaging is a Phase 12 concern |

No blocker or warning-level anti-patterns found in implementation files. The TODO in pyproject.toml is a tracked, intentional deferral documented in the 11-04-SUMMARY.md.

### Human Verification Required

Plan 11-05 was the human-verify checkpoint for Phase 11. It was auto-approved per user directive to continue autonomously. The following items require browser-level confirmation before the phase goal ("interactive navigation") is fully verified:

#### 1. Browser Rendering at http://localhost:8765

**Test:** Run `graphiti ui` and visit http://localhost:8765 in a browser.
**Expected:** Page loads showing the graph canvas area, header bar with Project/Global scope buttons, Hierarchical/Force layout buttons, By Type/By Scope colour-mode buttons, a search input, and a type dropdown.
**Why human:** SSR build completed (`ui/out/index.html` exists), but actual canvas rendering by react-force-graph-2d requires a real browser (canvas API). No programmatic test covers this.

#### 2. Node Click — Sidebar Opens

**Test:** With nodes visible in the graph, click any node.
**Expected:** Right sidebar panel slides open showing entity name, entity type badge, summary text, Created and Last Accessed dates, and a close button (X).
**Why human:** Node click handler calls `fetchNodeDetail` and renders NodeSidebar. Tests mock at the service layer; the canvas interaction and DOM rendering are not exercised.

#### 3. Scope Toggle — Live Re-fetch

**Test:** Click the "Global" button in the header while the server is running.
**Expected:** Graph area briefly shows a loading state then re-renders with global scope data; server terminal stays running (no restart).
**Why human:** Scope toggle re-fetch is a client-side state update triggered by a button click — not covered by automated tests.

#### 4. Search Dimming

**Test:** Type a name fragment into the search input.
**Expected:** Nodes whose names do not match the search term become dark/slate coloured (dimmed) while matching nodes retain their assigned colour.
**Why human:** Canvas colour calculation (nodeColor callback) requires visual inspection. The logic is unit-testable in isolation but no test was written for it.

#### 5. Read-Only Invariant — No Write Controls

**Test:** Inspect the full rendered page (graph view, node sidebar, all header controls).
**Expected:** No "Edit", "Delete", "Add Node", "Save", or any other write-action button is present anywhere.
**Why human:** This is a visual audit of the rendered UI. The code does not contain write controls (confirmed by code review), but a human must confirm the rendered page matches intent.

#### 6. `graphiti ui --global` Scope Label

**Test:** Run `graphiti ui --global` and observe the terminal banner.
**Expected:** Banner prints "Scope: global"; browser shows nodes from the global graph scope.
**Why human:** `test_global_flag` only confirms the flag does not produce a parse error. It does not confirm the correct scope_label or that global graph data is returned.

#### 7. Ctrl+C Clean Shutdown

**Test:** Start `graphiti ui`, then press Ctrl+C.
**Expected:** Terminal prints "Graphiti UI stopped." and returns to the shell prompt cleanly (no traceback).
**Why human:** KeyboardInterrupt handling requires a running process to test; not exercised in any automated test.

### Gaps Summary

No automated-verifiable gaps were found. All 9 programmatically testable must-haves are verified:

- All 8 Phase 11 tests pass GREEN (293 total tests passing, no regressions)
- All key artifacts exist and are substantive (not stubs)
- All key links are wired (CLI registration, create_app, router prefix, read-only DB access)
- REQUIREMENTS.md UI-01, UI-02, UI-03 all marked complete with correct descriptions
- `ui/out/index.html` committed to git; .gitignore correctly excludes node_modules//.next/ but not out/
- No `_get_graphiti()` calls in route handlers (invariant confirmed by grep)

The one outstanding item is the human browser verification deferred in Plan 11-05. The phase goal includes "interactive navigation" which cannot be confirmed by automated tests alone.

---

_Verified: 2026-03-09T11:00:00Z_
_Verifier: Claude (gsd-verifier)_

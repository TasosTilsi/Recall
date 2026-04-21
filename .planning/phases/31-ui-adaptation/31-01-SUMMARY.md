---
phase: 31-ui-adaptation
plan: 31-01
subsystem: ui_server
tags: [fastapi, sqlite, routes, api, v3.0]
dependency_graph:
  requires: [26-01, 28-01]
  provides: [UI-01, UI-02, UI-03, UI-04]
  affects: [src/ui_server/app.py, src/ui_server/routes.py]
tech_stack:
  added: []
  patterns: [synchronous-fastapi-routes, sqlite3-context-manager, FTS5-match-query]
key_files:
  created: []
  modified:
    - src/ui_server/app.py
    - src/ui_server/routes.py
decisions:
  - "All UI route handlers are synchronous (def not async def) — sqlite3 is blocking and no async benefit"
  - "DatabaseManager.connect() used as context manager in every route — connection opened and closed per request"
  - "Inverse backlink rows excluded from graph edges and entity detail backlinks — they'd double every edge visually"
  - "Empty FTS search query returns empty list — prevents full table scan on empty input"
  - "create_app() does not call db.init_db() — UI server is read-only; init is the indexer's responsibility"
metrics:
  duration: "114s"
  completed_date: "2026-04-21"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 31 Plan 01: UI Server Backend Rewrite Summary

FastAPI ui_server rewritten from GraphService/LadybugDB to direct SQLite queries via DatabaseManager, exposing four clean v3.0 API endpoints with entity-type counts, backlink graphs, and FTS5 search.

## What Was Built

Replaced both `src/ui_server/app.py` and `src/ui_server/routes.py` to serve the v3.0 SQLite schema:

### app.py
- `create_app(dev_mode, static_dir)` — simplified signature (removed scope_label/scope/project_root)
- Instantiates `DatabaseManager(load_config())` and stores as `app.state.db`
- No `db.init_db()` call — read-only server
- CORS middleware and StaticFiles mount preserved unchanged

### routes.py
Four synchronous endpoints backed by direct SQLite queries:

| Endpoint | Response |
|---|---|
| `GET /api/graph` | `{nodes: [{id, label, type, commit_sha}], edges: [{id, from_id, to_id, relationship}]}` — 2000 nodes, 5000 edges max, inverse: edges excluded |
| `GET /api/dashboard` | `{total_entities, total_commits, entity_types, top_entities, recent_commits}` — entity_types keyed by six canonical types |
| `GET /api/detail/entity/{entity_id}` | `{id, name, type, content, tags, commit_sha, created_at, backlinks}` — backlinks include relationship + context fields |
| `GET /api/search?q=` | `{entities: [{id, name, type, content_snippet}]}` — FTS5 MATCH with snippet(), empty q returns `[]` |

## Deviations from Plan

None — plan executed exactly as written. The stale-reference grep showed hits in `.pyc` cache files only; all `.py` source files are clean.

## Known Stubs

None — all four endpoints query real SQLite tables. The UI will serve empty responses if the database has not been indexed yet (expected — `recall init` or `recall sync` populates data).

## Self-Check: PASSED

Files verified:
- FOUND: src/ui_server/app.py
- FOUND: src/ui_server/routes.py

Commits verified:
- 73a48b5: feat(31-01): wire DatabaseManager into app state, remove GraphService
- b138bc2: feat(31-01): rewrite routes.py with four SQLite-backed endpoints

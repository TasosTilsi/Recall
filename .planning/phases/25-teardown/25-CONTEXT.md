---
phase: 25
name: Teardown
status: context_captured
date: 2026-04-14
---

# Phase 25: Teardown — Context

## Phase Goal

The legacy codebase is gone and the new module layout is in place — no imports of removed code compile.

## Domain Boundary

Pure demolition + structural reset. This phase delivers:
1. All legacy modules deleted (hooks, queue, retention, storage, graph, security, capture, gitops, models, llm, indexer/old, config/)
2. graphiti-core and real-ladybug removed from pyproject.toml
3. New skeleton directories in place (src/db/, src/extractor/, src/indexer/, src/cli/, src/mcp_server/, src/ui_server/, src/config.py)
4. ui_server/ carries forward from v2.0 (selective survivor — see decisions)
5. Package renamed to recall-kg
6. tests/ and scripts/ fully deleted

**What this phase does NOT do:** implement any actual functionality in db/, extractor/, indexer/, or cli/ — those are Phases 26–29.

---

## Decisions

### D1: Survivors — what partial code carries over

**Decision:** Selective survival — `ui_server/` carries forward as-is, `cli/` and `mcp_server/` get gutted to minimal stubs.

**Rationale:** ui_server/ contains working shadcn/Sigma.js graph UI that's expensive to rebuild; it stays and gets updated in Phase 31. cli/ and mcp_server/ need a full rewrite against the new stack, so stubs are cleaner than forward-porting v2.0 code that will be deleted anyway.

**Implementation guidance:**
- `src/ui_server/` — move from old layout to new layout unchanged (or leave in place if already at root src/ui_server/)
- `src/cli/` — replace with a single `__init__.py` that creates a typer app and registers 6 stub commands: `init`, `sync`, `search`, `health`, `config`, `mcp`. Each command body is just `pass` or a `typer.echo("not implemented yet")`.
- `src/mcp_server/` — replace with a minimal `__init__.py`. No FastMCP, no tools. Phase 30 rebuilds it.

### D2: Stub depth for `recall --help`

**Decision:** Minimal — `recall --help` must not crash, but individual subcommands crashing is acceptable. Fix happens in Phase 29.

**Rationale:** User explicitly said: "don't care if something crashes, but be sure to fix it in the next stages." The success criterion `recall --help loads without errors` is the bar — not individual commands.

**Implementation guidance:**
- The typer app at `src/cli/__init__.py` registers 6 commands as stubs
- `recall --help` exits 0 and lists the 6 command names
- `recall init` etc. may crash or print "not implemented" — that's fine

### D3: Package rename

**Decision:** Rename in Phase 25 — from `graphiti-knowledge-graph` to `recall-kg`.

**Rationale:** Clean break alongside all other structural changes. Downstream phases start with the correct package name.

**Implementation guidance:**
- `pyproject.toml`: change `name = "graphiti-knowledge-graph"` → `name = "recall-kg"`
- `pyproject.toml`: change `description` to reflect v3.0 purpose
- Remove `graphiti-core[neo4j]==0.28.1` and `real-ladybug==0.15.1` from dependencies
- Remove other deleted-module deps (ollama==0.6.1, persist-queue==1.1.0, python-toon>=0.1.3, sentence-transformers>=2.0.0, tenacity==9.1.4) — these belong to deleted subsystems
- Keep: fastapi, GitPython, httpx, mcp[cli], structlog, typer, uvicorn, starlette (still needed for ui_server)
- The `.egg-info` directory (graphiti_knowledge_graph.egg-info) should be deleted
- `pip install -e .` must succeed after changes

### D4: Tests and scripts — full deletion

**Decision:** Delete `tests/` entirely. Delete `scripts/` entirely. No placeholders, no smoke tests. Clean slate.

**Rationale:** User said "delete everything, the scripts/ folder and verify all as well." All tests reference deleted modules and would be broken. Each future phase adds its own tests from scratch.

**Implementation guidance:**
- `rm -rf tests/`
- `rm -rf scripts/`
- The `src/graphiti_knowledge_graph.egg-info/` directory should also be removed (stale after rename)

---

## Canonical Refs

- `.planning/ROADMAP.md` — Phase 25 success criteria (4 criteria to verify)
- `.planning/REQUIREMENTS.md` — ARCH-01, ARCH-02 (module layout requirements)
- `pyproject.toml` — current dependencies to remove/update
- `src/ui_server/` — surviving component; planner should read to confirm it has no imports from deleted modules

---

## What Downstream Agents Need to Know

**Researcher (gsd-phase-researcher):** No external research needed. This is a demolition phase with no new dependencies. The only question worth researching: does `ui_server/` currently import from any module being deleted? If so, those imports must be stubbed or removed.

**Planner (gsd-planner):** Phase is purely structural. Plans should be:
1. Remove legacy module directories from src/
2. Update pyproject.toml (rename, remove dead deps)
3. Scaffold new skeleton directories with `__init__.py` stubs
4. Gut cli/ to minimal typer stub (6 commands)
5. Gut mcp_server/ to empty stub
6. Delete tests/ and scripts/
7. Verify: `python -c "import src"` clean, `pip install -e .` succeeds, `recall --help` exits 0, directory tree matches spec

**Critical constraint:** `ui_server/` must not be broken. Before deleting any module, grep ui_server/ for imports from that module and stub or remove them.

---

## Deferred Ideas

- Distribution/polish: plugin PATH detection and packaging — this is Phase 32/33 scope, not Phase 25
- Smoke test scaffolding — user wants clean slate, each future phase owns its own tests

# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-01
**Phases:** 18 (Phases 1–8.9, including 10 decimal gap-closure insertions) | **Plans:** 62 | **Timeline:** 27 days

### What Was Built

- Persistent Kuzu graph database with dual-scope isolation (global preferences + per-project knowledge)
- Defense-in-depth security: file exclusions, high-entropy detection, entity sanitization, pre-commit blocking hook
- Hybrid cloud/local Ollama LLM with quota tracking and graceful fallback — never completely fails
- Full CLI with 16+ commands; CLI-first architecture where MCP and hooks wrap CLI subprocesses
- Async background queue (SQLiteAckQueue + BackgroundWorker) for non-blocking git and conversation capture
- Automatic capture from git commits (post-commit hook) and Claude Code conversations (every 5-10 turns)
- Local-first git history indexer replacing journal-based approach — `.graphiti/` fully gitignored
- MCP server with 11 tools, context injection with stale-index detection, TOON encoding for large responses

### What Worked

- **CLI-first architecture**: Having the CLI as single source of truth made MCP and hook wiring straightforward. Subprocess-based MCP tools meant no code duplication between CLI and MCP layer.
- **GSD phase structure**: Planning-then-executing at plan granularity kept changes atomic and easy to reason about. Decimal phase insertions (7.1, 8.1–8.9) worked well for urgent gap closure without renumbering.
- **Audit-driven gap closure**: Running milestone audit before marking complete caught real integration bugs (graphiti_index missing, hooks.enabled CLI syntax, _is_claude_hook_installed depth). Worth the extra cycle.
- **Security filtering as a phase**: Building security in Phase 2 (before LLM and capture phases) meant it was always available as a gate. sanitize_content() runs before LLM in all capture paths.
- **Milestone audit + gap phases pattern**: The chain audit → plan-gap-phases → execute → re-audit is effective for catching integration issues invisible at phase level.

### What Was Inefficient

- **Phase 7 → 7.1 pivot**: Significant rework — journal writer, replay engine, checkpoint tracking, LFS helpers all built in Phase 7 and removed in 7.1. The local-first decision should have been made before Phase 7. Architectural pivots cost ~2 phases.
- **Phase 4 gap closure (04-07 through 04-11)**: CLI was built with mock stubs in original plans. Wiring to real graph operations required 5 extra plans (nearly doubled Phase 4). Implement real operations in original plans next time.
- **10 gap-closure decimal phases**: Phases 8.1–8.9 were necessary but indicate that verification was incomplete during main phases. Writing VERIFICATION.md during each phase (not as retroactive gap closure) would have prevented several of these.
- **State update lag**: ROADMAP.md progress table, REQUIREMENTS.md status notes, and STATE.md fell behind actual completion multiple times. Updating these in the plan execution itself (not as a separate step) avoids the drift.

### Patterns Established

- **Decimal phase insertion**: `X.Y` phases for urgent insertions between planned phases. Clearly marked `[INSERTED]` in roadmap. Maintains numeric ordering without renumbering downstream phases.
- **CLI subprocess for MCP tools**: All MCP tools call `graphiti <command>` as subprocess using `_GRAPHITI_CLI = Path(sys.executable).parent / 'graphiti'`. Never rely on PATH inheritance.
- **TOON encoding threshold**: Apply TOON for 3+ item lists, plain JSON for scalars. 3-item threshold where TOON header overhead pays off.
- **Security gate before LLM**: `sanitize_content()` always runs before LLM in capture paths. Belt-and-suspenders with pre-commit hook.
- **SQLiteAckQueue with multithreading=True**: Required when background worker runs `ollama_chat` in `run_in_executor` threads.
- **GRAPHITI_HOOK_START/END markers**: Idempotent hook section management — detect, update, or remove without touching other tools' content.
- **sys.executable path resolution**: Avoids PATH issues in Claude Code subprocess contexts consistently.
- **`lstrip('.')` not `strip('.')`**: For normalizing dot-prefixed field names from LLM — only strip leading dots, never trailing.

### Key Lessons

1. **Define architecture before building**: The Phase 7 → 7.1 pivot (journal → local-first) cost ~2 phases. Architecture decisions about storage model should be made before starting, not mid-milestone.
2. **Implement real operations in original plans**: Building CLI with mock stubs and wiring real operations later (Phase 4 gap closure) nearly doubled Phase 4 plan count. Integrate real operations from the start.
3. **Write VERIFICATION.md during execution**: Writing 3 VERIFICATION.md files retroactively in Phase 8.8 was overhead that could have been eliminated by including VERIFICATION.md creation in each phase's final plan.
4. **Audit before declaring done**: The milestone audit caught real bugs (graphiti_index missing, hooks.enabled syntax) that would have silently broken user flows. Always audit before marking complete.
5. **Keep docs in sync during execution**: ROADMAP.md progress table and REQUIREMENTS.md status notes drifted. Update state docs as part of plan execution, not separately.
6. **Security filtering is infrastructure, not feature**: Build it early (Phase 2 here) so all subsequent phases can use it as a dependency. Retrofitting security is harder.

### Cost Observations

- Model mix: ~80% sonnet, ~15% opus (planning/architecture), ~5% haiku (quick tasks)
- Sessions: ~15-20 sessions over 27 days
- Notable: Parallel wave execution within phases significantly reduced wall-clock time. GSD balanced model profile (sonnet default) worked well for this codebase scale.

---

## Milestone: v1.1 — Advanced Features

**Shipped:** 2026-03-09
**Phases:** 4 (Phases 9–11.1, including 1 decimal gap-closure insertion) | **Plans:** 14 | **Timeline:** 8 days

### What Was Built

- Smart retention: TTL-based 90-day expiry + reinforcement scoring; `graphiti stale/compact --expire/pin/unpin`; SQLite sidecar for retention metadata
- Configurable capture modes: `decisions-only` / `decisions-and-patterns` selectable via `llm.toml`; sanitize-before-mode invariant enforced unconditionally
- Graph UI: FastAPI backend + Next.js 16 static export; ForceGraph2D visualization; scope toggle; entity sidebar with retention metadata; read-only Kuzu mount
- Gap closure (Phase 11.1): 4 integration gaps from audit closed — retention fields in UI, archive/pin canvas filters, ui.port config key normalization

### What Worked

- **Shorter milestone, tighter scope**: 8 days vs 27 days for v1.0. Fewer phases means each phase is more focused and integration gaps are fewer.
- **Audit-then-gap pattern again**: Phase 11.1 was created directly from the v1.1 audit. The pattern from v1.0 confirmed: run audit, create decimal gap phase, close before declaring done.
- **SQLite sidecar for retention**: Keeping retention metadata separate from graphiti-core's schema avoided a schema fork. Clean boundary between graphiti-core concerns and our extensions.
- **Sanitize-before-mode invariant**: Establishing this as an explicit non-negotiable in Phase 10 (not just an implicit ordering) paid off — it was referenced in audit checks and Phase 14 design.
- **Graph UI as static export**: Pre-building Next.js to `ui/out/` and committing to git means zero build step at runtime. FastAPI serves pre-built files. No node_modules in production.

### What Was Inefficient

- **Phase 11.1 executed as direct commits**: The gap closure work was done in git commits without GSD plan files, leaving the phase directory empty. Made GSD tooling report the phase as unplanned. A minimal PLAN.md + SUMMARY.md would have kept tooling consistent.
- **Ghost phase 10-local-memory**: A substantial set of plans was created (5 plans) for a "Local Memory System" milestone that was never wired into the roadmap. Plans sat dormant and confused GSD progress tracking until cleaned up. Research and planning artifacts should be committed to the roadmap before building the plan files.
- **PROV-01–04 in v1.1 requirements**: Multi-provider LLM was never realistic for v1.1 scope given the complexity of decomposing `client.py`. It was moved to v2.0 early but the requirements remained in REQUIREMENTS.md creating a false "incomplete" signal. Remove requirements from the active list when they're formally deferred.

### Patterns Established

- **Sanitize-before-mode invariant**: Security gate runs unconditionally before any capture mode filter. Established as non-negotiable architectural rule in v1.1.
- **Static UI export committed to git**: Pre-built `ui/out/` directory committed to repo — zero build step at runtime, works offline.
- **SQLite sidecar for schema extension**: When graphiti-core's schema lacks fields (e.g., TTL, access tracking), use a SQLite sidecar rather than forking graphiti-core's models.
- **APScheduler 3.x pin**: Pin `>=3.10.4,<4.0` for in-process schedulers — v4 is a breaking API rewrite.
- **Ghost phase detection**: Phases planned outside the roadmap should be wired in immediately or archived. Orphan plan directories confuse GSD init/routing.

### Key Lessons

1. **Wire phases into roadmap immediately**: The 10-local-memory ghost phase sat for weeks undetected. Any research/planning artifact should be in ROADMAP.md before creating plan files.
2. **Keep plan files for all executed work**: Phase 11.1 executed as direct commits without PLAN.md/SUMMARY.md files, breaking GSD tooling consistency. Even quick gap closure needs minimal GSD artifacts.
3. **Remove deferred requirements promptly**: PROV-01–04 deferred to v2.0 but remained in REQUIREMENTS.md until milestone completion. Defer cleanly — remove from active list and note in Phase Details.
4. **8-day milestone rhythm is achievable**: 4 phases, 14 plans, 8 days. Tight scope + established patterns = fast iteration. Keep milestones this size going forward.

### Cost Observations

- Model mix: ~85% sonnet, ~15% opus (research/architecture phases)
- Sessions: ~6-8 sessions over 8 days
- Notable: Much faster than v1.0. Established patterns (CLI-first, async queue, security gate) meant less architectural decision-making per phase.

---

## Milestone: v2.0 — Rebuild

**Shipped:** 2026-04-07
**Phases:** 13 (Phases 12–24, including 5 gap-closure phases) | **Plans:** 48 | **Timeline:** 21 days (2026-03-17 → 2026-04-07)

### What Was Built

- KuzuDB → LadybugDB (embedded, zero Docker) + Neo4j opt-in via Docker Compose; all 3 Kuzu workarounds removed; vendored `LadybugDriver` (~280 lines)
- Multi-provider LLM: switch OpenAI/Groq/compatible via `[llm]` section in `llm.toml`; URL-based SDK auto-detection; fail-fast startup validation; health provider rows
- 4 Claude Code hook scripts (pure Python): SessionStart (≤5s, git sync), UserPromptSubmit (≤6s, FTS-first Option C context injection), PostToolUse (fire-and-forget queue), SessionEnd (session summary via `claude -p`)
- CLI renamed `graphiti` → `recall` (alias `rc`); 9-command public surface; all plumbing hidden; `recall search` auto-syncs git
- shadcn/ui dual-view (table + Sigma.js WebGL graph) with Recharts dashboard, retention filter, node-click detail panel with breadcrumb navigation
- Fast indexing: `ClaudeCliLLMClient` via `claude -p` subprocess; 10-commit batch extraction; `asyncio.Semaphore(3)` parallelism; FTS-first 3-layer context injection; 90min → <2min
- Knowledge quality uplift: code block entity extraction from diffs; semantic relationship types (MODIFIES, INTRODUCES, FIXES, DEPENDS_ON); structured metadata chips in UI

### What Worked

- **Phase ordering locked upfront**: The 12→13→15→16→14 execution order was decided in research before any phase started. No dependency surprises mid-milestone.
- **`claude -p` for indexing**: Using the Claude Code subscription path (no `ANTHROPIC_API_KEY` required) for batch extraction was the key insight that unlocked the 90min→2min speedup. Same pattern as claude-mem.
- **Nyquist sweep as an explicit phase**: Treating validation compliance as a deliberate phase (Phase 23) rather than hoping each phase would do it correctly — effectively caught 8 missing VALIDATION.md files.
- **Audit → gap-phases pattern (3rd iteration)**: The 5-gap audit leading to Phases 22, 23, 24 followed the same pattern as v1.0 (8.1–8.9) and v1.1 (11.1). Predictable, reliable. Expect ~4-8 gap-closure plans per milestone.
- **FTS-first context injection**: Routing keyword-matching prompts through LadybugDB FTS5 (Layer 1, <50ms) before touching vector search was a significant UX win. The 3-layer progressive disclosure pattern from claude-mem adapted cleanly.

### What Was Inefficient

- **Phase 14 tracking drift**: ROADMAP.md showed "6/7 | In Progress" throughout v2.0 despite Phase 14 being complete on disk (7/7 SUMMARY.md). The progress table wasn't updated when Phase 14 finished. STATE.md tracking metrics are only as good as the updates made during execution.
- **UI-03 split across 3 phases (19, 22, 24)**: The retention filter requirement took 3 phases to close (19 for API+list view, 22 for detail panel fix, 24 for audit closure). Should have been caught in Phase 19 via more thorough E2E testing of the detail panel path.
- **Phase 14 running as a large 7-plan monolith**: The Graph UI redesign accumulated 7 plans but the human checkpoint was deferred to the last plan. Introducing intermediate verification checkpoints after Plan 4 (scaffold+shell) would have caught the Sigma.js setup issues earlier.
- **13 phases for a "rebuild"**: Many phases were gap-closure and quality work added reactively (17, 18, 19, 22, 23, 24 = 6 of 13 phases). Pre-emptively including a "quality and verification pass" phase at v2.0 planning would have reduced reactive gap closure cycles.

### Patterns Established

- **`ClaudeCliLLMClient` pattern**: When `ANTHROPIC_API_KEY` unavailable, use `claude -p` subprocess via `shutil.which("claude")`. Falls back to Ollama if not on PATH. Auto-detected at runtime.
- **3-layer FTS-first context injection**: Layer 1 (FTS compact, <50ms) → Layer 2 (chronological, no LLM) → Layer 3 (vector for filtered IDs only). Adapted from claude-mem's progressive disclosure.
- **Option C format**: `<session_context>` wrapping `<continuity>` (session summary) + `<relevant_history>` (temporal facts). ≤4000 token budget. Priority: recent session → recent git → older session → older git.
- **LadybugDriver vendoring**: Vendor ~280 lines locally when official graphiti-core driver not available. Use `GraphProvider.KUZU` as alias when Cypher dialect is identical. Dict-keyed row access (`row['uuid']`, not `row[0]`).
- **Gap-closure phase as planning artifact**: Phases 17/18/24 (doc-only gap closure) need `nyquist_compliant: true` via VALIDATION.md citing the D-03 "compliant by definition" pattern — no production code, no tests to sample.

### Key Lessons

1. **Track progress table in real-time**: ROADMAP.md "In Progress" entries that are actually done create confusion at audit time. Update `Status` and `Completed` columns as part of the final plan in each phase.
2. **E2E test detail panel paths in UI phases**: Retention status showed "Normal" in detail panel while list-view filter worked correctly (Phase 19). Testing the whole user flow (not just the API endpoint) in the original phase would have caught this without a follow-up phase (22).
3. **Plan a "quality pass" phase proactively**: 6 of 13 phases were reactive gap closure. A single pre-planned "Phase X: Quality & Verification Pass" at milestone planning would absorb this predictable overhead with less context-switching.
4. **The `claude -p` pattern is now baseline**: Any future feature requiring LLM extraction (session summaries, batch indexing, Q&A generation) should default to `ClaudeCliLLMClient` first, Ollama as fallback. ~10x faster and no API key management.
5. **Lock phase execution order before planning**: The 12→13→15→16→14 order locked upfront prevented mid-milestone dependency surprises. Do this as a first step in `/gsd:discuss-phase` for any milestone with 3+ interdependent phases.

### Cost Observations

- Model mix: ~80% sonnet, ~10% opus (research phases), ~10% haiku (stub generation, quick tasks)
- Sessions: ~18-22 sessions over 21 days
- Notable: Phase 21 (Knowledge Quality Uplift) had the longest single plan (198 min for 21-03) due to complex test infrastructure. FTS-first pattern in Phase 20 reduced LLM call count significantly for the indexer.

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Timeline | Key Change |
|-----------|--------|-------|----------|------------|
| v1.0 MVP | 18 | 62 | 27 days | First milestone; established baseline patterns |
| v1.1 Advanced Features | 4 | 14 | 8 days | Shorter scope, faster; ghost phase discovery |
| v2.0 Rebuild | 13 | 48 | 21 days | Major backend+CLI+UI rebuild; FTS-first injection; `claude -p` indexing |

### Cumulative Quality

| Milestone | Gap-Closure Phases | Architecture Pivots | Notes |
|-----------|--------------------|---------------------|-------|
| v1.0 | 10 (7.1, 8.1–8.9) | 1 (journal → local-first) | Pivot cost ~2 phases |
| v1.1 | 1 (11.1) | 0 | Clean execution; ghost phase cleanup needed |
| v2.0 | 6 (17, 18, 19, 22, 23, 24) | 0 | Reactive gap closure ~46% of phases; proactive quality pass needed |

### Top Lessons (Verified Across Milestones)

1. Architecture decisions before building avoids expensive mid-milestone pivots (v1.0 lesson — not an issue in v1.1/v2.0; kept via phase ordering lock)
2. Implement real integrations in original plans — mock stubs defer debt, not eliminate it (v1.0)
3. Write VERIFICATION.md during phase execution, not as retroactive gap closure (v1.0; confirmed again in v2.0 — 11 partial requirements retroactively upgraded)
4. Wire phases into roadmap immediately — orphan plan directories break GSD tooling and hide work (v1.1)
5. Track progress table in real-time — stale "In Progress" entries cause audit confusion (v2.0)
6. Plan a proactive quality/verification phase — reactive gap closure consumes ~40% of phases predictably (v2.0)

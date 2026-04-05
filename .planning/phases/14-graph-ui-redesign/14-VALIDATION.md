---
phase: 14
slug: graph-ui-redesign
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-20
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

> **Note:** Per D-02, this is a forward-looking contract. Phase 14 vitest infrastructure (`ui/vitest.config.ts`, `ui/src/__tests__/`) is not yet fully set up. `nyquist_compliant: true` reflects that the contract clearly defines test strategy, sampling rate, and per-task verification map. `wave_0_complete` remains `false` until vitest stubs are created.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), pytest (backend API) |
| **Config file** | `ui/vitest.config.ts` (Wave 0 installs), `pytest.ini` (existing) |
| **Quick run command** | `cd ui && npx vitest run --reporter=dot` |
| **Full suite command** | `cd ui && npx vitest run && pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd ui && npx vitest run --reporter=dot`
- **After every plan wave:** Run `cd ui && npx vitest run && pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | UI-04 | unit | `pytest tests/test_graph_service_ui.py -x -q` | ✅ exists | ⬜ pending |
| 14-01-02 | 01 | 0 | UI-04 | unit | `pytest tests/test_graph_service_ui.py -x -q` | ✅ exists | ⬜ pending |
| 14-02-01 | 02 | 1 | UI-01 | e2e-manual | Browser: open `recall ui`, see table+graph tabs | n/a | ⬜ pending |
| 14-02-02 | 02 | 1 | UI-01 | unit | `cd ui && npx vitest run --reporter=dot` | ❌ W0 | ⬜ pending |
| 14-02-03 | 02 | 1 | UI-02 | unit | `cd ui && npx vitest run --reporter=dot` | ❌ W0 | ⬜ pending |
| 14-03-01 | 03 | 2 | UI-03 | unit | `cd ui && npx vitest run --reporter=dot` | ❌ W0 | ⬜ pending |
| 14-03-02 | 03 | 2 | UI-03 | e2e-manual | Browser: toggle filter, refresh — filter state persists | n/a | ⬜ pending |
| 14-04-01 | 04 | 2 | UI-01 | unit | `cd ui && npx vitest run --reporter=dot` | ❌ W0 | ⬜ pending |
| 14-04-02 | 04 | 2 | UI-04 | unit | `pytest tests/test_graph_service_ui.py -x -q` | ✅ exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_graph_service_ui.py` — stubs for UI-04 GraphService method tests (file exists)
- [ ] `ui/src/__tests__/` — vitest test stubs for component/hook tests
- [ ] `ui/vitest.config.ts` — vitest config (jsdom environment)
- [ ] `ui/package.json` — vitest + @testing-library/react installed

*Wave 0 installs test infrastructure before any UI or service code is written. Backend pytest tests exist; frontend vitest infrastructure pending.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Table ↔ Graph tab switch without page reload | UI-01 | DOM interaction + visual | Open `recall ui`, click Table tab, click Graph tab — no full page load |
| Scope toggle updates list and graph | UI-02 | Requires live graph data | Toggle Project/Global — entity count changes in both views |
| Filter state persists within session | UI-03 | Session-scoped state | Select "pinned" filter, navigate away, return — filter still selected |
| Sigma.js graph renders nodes and edges | UI-01 | Canvas rendering, not DOM | Open graph view — nodes visible, edges drawn |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [ ] Wave 0 complete — vitest infrastructure not yet set up (forward contract per D-02)

**Approval:** forward-contract — see D-02

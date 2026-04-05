---
phase: 19
slug: wire-ui-03-retention-filter
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-27
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `pytest.ini` / `ui/vite.config.ts` |
| **Quick run command** | `pytest tests/test_phase19_integration.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q && cd ui && npm run test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_phase19_integration.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q && cd ui && npm run test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | UI-03 | unit | `pytest tests/test_phase19_integration.py::test_retention_status_field -x -q` | ✅ exists | ✅ green |
| 19-01-02 | 01 | 1 | UI-03 | unit | `pytest tests/test_phase19_integration.py::test_archived_entities_included -x -q` | ✅ exists | ✅ green |
| 19-01-03 | 01 | 1 | UI-03 | unit | `pytest tests/test_phase19_integration.py::test_api_graph_node_shape -x -q` | ✅ exists | ✅ green |
| 19-02-01 | 02 | 2 | UI-03 | unit | `cd ui && npm run test -- --run` | ✅ exists | ✅ green |
| 19-02-02 | 02 | 2 | UI-03 | unit | `cd ui && npm run test -- --run` | ✅ exists | ✅ green |
| 19-02-03 | 02 | 2 | UI-03 | unit | `cd ui && npm run test -- --run` | ✅ exists | ✅ green |
| 19-03-01 | 03 | 3 | UI-03 | integration | `pytest tests/test_phase19_integration.py -x -q` | ✅ exists | ✅ green |
| 19-03-02 | 03 | 3 | UI-03 | manual | N/A — smoke test | N/A | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_phase19_integration.py` — integration tests for end-to-end UI-03 retention filter flow — 16 tests pass
- [x] `ui/src/routes/__tests__/Entities.test.tsx` — component test stubs for retention filter dropdown

*Wave 0 stubs created during Phase 19 execution. All tests pass.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sigma.js node ring colors visible in graph view | UI-03 | Canvas rendering requires visual inspection | Open `/ui`, navigate to Graph view, verify pinned nodes show amber ring, stale nodes show red ring, archived show gray ring |
| Retention filter hides archived by default | UI-03 | DOM state interaction | Load Entities view, confirm archived entities absent; select "Archived" in filter, confirm they appear |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed — test_phase19_integration.py 16 passed

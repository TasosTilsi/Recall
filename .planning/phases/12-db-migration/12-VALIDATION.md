---
phase: 12
slug: db-migration
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-17
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| Plan 01 Task 1 | 01 | 1 | DB-01 | unit | `pytest tests/ -x -q` | ✅ exists | ✅ green |
| Plan 01 Task 2 | 01 | 1 | DB-01 | integration | `pytest tests/test_backend_integration.py::test_ladybug_driver_creates_fresh_db -x -q` | ✅ exists | ✅ green |
| Plan 02 Task 1 | 02 | 2 | DB-01 | unit | `pytest tests/test_storage.py -x -q` | ✅ exists | ✅ green |
| Plan 02 Task 2 | 02 | 2 | DB-01 | integration | `pytest tests/test_backend_integration.py -x -q` | ✅ exists | ✅ green |
| Plan 03 Task 1 | 03 | 2 | DB-01 | unit | `pytest tests/test_storage.py -x -q` | ✅ exists | ✅ green |
| Plan 04 Task 1 | 04 | 3 | DB-02 | unit | `pytest tests/test_backend_config.py -x -q` | ✅ exists | ✅ green |
| Plan 04 Task 2 | 04 | 3 | DB-02 | unit/integration | `pytest tests/test_backend_config.py tests/test_backend_integration.py -x -q` | ✅ exists | ✅ green |
| Plan 05 Task 1 | 05 | 4 | DB-01 | integration | `pytest tests/test_backend_integration.py -x -q` | ✅ exists | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_backend_config.py` — stubs for DB-02 (BackendConfig parsing, bolt URI, health row)
- [x] `tests/test_backend_integration.py` — stubs for DB-01 (LadybugDriver integration: fresh DB, FTS dedup)
- [x] `tests/test_storage.py` — GraphManager structural tests (driver swap, no kuzu imports)
- [x] `tests/conftest.py` — shared fixtures for backend-agnostic tests

*All Wave 0 tests exist and pass. Full suite: 435 passed, 1 skipped (2026-04-04).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FTS deduplication (same entity added twice resolves to one node) | DB-01 | Requires live LadybugDB instance | Run `recall add "Alice met Bob"` twice; `recall search "Alice"` must return 1 node |
| Neo4j opt-in via `llm.toml` `[backend] type = "neo4j"` | DB-02 | Requires Docker + Neo4j running | Set config, run `docker compose up`, run `recall add` and `recall search` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed — all tests exist and pass (435 passed, 1 skipped, 2026-04-04)

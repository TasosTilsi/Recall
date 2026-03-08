---
phase: 11
slug: graph-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 11 — Validation Strategy

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
| 11-01-01 | 01 | 1 | UI-01 | unit | `pytest tests/test_ui_server.py -x -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | UI-01 | unit | `pytest tests/test_ui_server.py -x -q` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | UI-01 | unit | `pytest tests/test_ui_server.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | UI-02 | unit | `pytest tests/test_ui_server.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | UI-02 | unit | `pytest tests/test_ui_server.py -x -q` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 2 | UI-01 | manual | See manual verifications | N/A | ⬜ pending |
| 11-03-02 | 03 | 2 | UI-03 | unit | `pytest tests/test_ui_command.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ui_server.py` — stubs for UI-01, UI-02 (FastAPI server, read-only graph endpoint, scope resolution)
- [ ] `tests/test_ui_command.py` — stubs for UI-03 (CLI `graphiti ui` command, `--global` flag, missing deps error)

*Existing infrastructure covers pytest fixtures via conftest.py.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Graph visualization renders at `http://localhost:8765` | UI-01 | Requires browser + running server | Run `graphiti ui`, visit `http://localhost:8765` in your browser, verify nodes/edges visible |
| Graph is read-only — no edit UI elements | UI-02 | Visual inspection required | Inspect rendered UI for absence of edit/delete controls |
| `--global` shows global scope graph | UI-03 | Requires two separate DB mounts | Run `graphiti ui --global`, visit `http://localhost:8765`, verify different node set from project scope |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
phase: 10
slug: configurable-capture-modes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pytest.ini` / `pyproject.toml` |
| **Quick run command** | `pytest tests/test_capture_modes.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_capture_modes.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 0 | CAPT-01/02/03 | unit | `pytest tests/test_capture_modes.py -x` | ❌ W0 | ⬜ pending |
| 10-02-01 | 02 | 1 | CAPT-01/02 | unit | `pytest tests/test_capture_modes.py::TestCaptureModeConfig -x` | ✅ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | CAPT-01/02 | unit | `pytest tests/test_capture_modes.py::TestCaptureModeSelection -x` | ✅ W0 | ⬜ pending |
| 10-02-03 | 02 | 1 | CAPT-01/02 | unit | `pytest tests/test_capture_modes.py::TestSecurityGate -x` | ✅ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | CAPT-03 | unit | `pytest tests/test_capture_modes.py::TestConfigShow -x` | ✅ W0 | ⬜ pending |
| 10-03-02 | 03 | 2 | CAPT-03 | unit | `pytest tests/test_capture_modes.py::TestConfigSet -x` | ✅ W0 | ⬜ pending |
| 10-03-03 | 03 | 2 | CAPT-01/02/03 | integration | `pytest tests/ -x` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_capture_modes.py` — stubs for all CAPT-01, CAPT-02, CAPT-03 test cases below

**Tests to stub in Wave 0:**
- `TestCaptureModeConfig::test_decisions_only_from_toml` — CAPT-01
- `TestCaptureModeConfig::test_decisions_and_patterns_from_toml` — CAPT-02
- `TestCaptureModeConfig::test_default_is_decisions_only` — CAPT-01
- `TestCaptureModeConfig::test_invalid_mode_falls_back` — CAPT-01
- `TestCaptureModeSelection::test_decisions_only_prompt` — CAPT-01 (narrow: no Bug/Dep categories)
- `TestCaptureModeSelection::test_decisions_and_patterns_prompt` — CAPT-02 (broad: all 4 categories)
- `TestSecurityGate::test_security_gate_is_unconditional` — CAPT-01/02 (sanitize_content runs regardless)
- `TestConfigShow::test_config_show_has_capture_section` — CAPT-03
- `TestConfigShow::test_config_show_has_retention_section` — CAPT-03 (Phase 9 fix)
- `TestConfigSet::test_set_valid_mode` — CAPT-03
- `TestConfigSet::test_set_invalid_mode_rejected` — CAPT-03

*Existing infrastructure: pytest, `tmp_path` fixture, `CliRunner` from typer — no new framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `graphiti config show` renders "Capture Settings" section visually in terminal | CAPT-03 | Rich table rendering — automated test checks string output, visual spot-check confirms layout | Run `graphiti config show`, confirm "Capture Settings" section appears with `capture.mode` row |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

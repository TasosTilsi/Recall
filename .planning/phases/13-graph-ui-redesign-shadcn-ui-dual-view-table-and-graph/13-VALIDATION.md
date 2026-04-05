---
phase: 13
slug: multi-provider-llm
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-17
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

> **Note:** Directory name is a legacy artifact from old phase numbering. Phase 13 = Multi-Provider LLM per ROADMAP.md.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `pytest tests/test_llm_config.py tests/test_provider.py -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_llm_config.py tests/test_provider.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | PROV-01, PROV-02 | unit | `pytest tests/test_llm_config.py -x -q` | ✅ exists | ✅ green |
| 13-01-02 | 01 | 1 | PROV-01 | unit | `pytest tests/test_provider.py -x -q` | ✅ exists | ✅ green |
| 13-02-01 | 02 | 2 | PROV-03, PROV-04 | unit | `pytest tests/test_provider.py -x -q` | ✅ exists | ✅ green |
| 13-03-01 | 03 | 2 | PROV-01 | unit | `pytest tests/test_provider.py -x -q` | ✅ exists | ✅ green |
| 13-04-01 | 04 | 3 | PROV-03 | manual | `recall health` output review | N/A | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_llm_config.py` — PROV-01, PROV-02 (LLMConfig [llm] section parsing, backward compat) — 24 tests pass
- [x] `tests/test_provider.py` — PROV-01 through PROV-04 (ProviderClient URL auto-detection, routing, startup validation, health rows) — passes

*Wave 0 phantom stubs were never created as separate files; coverage was implemented directly in `test_llm_config.py` and `test_provider.py` instead.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Health output format | PROV-03 | Requires live provider endpoint or mock | Run `recall health` with [llm] section set; verify provider/embed/fallback rows appear with correct format |
| Startup fail-fast on bad key | PROV-04 | Requires network call with invalid key | Set invalid api_key in [llm], run any `recall` command; verify error names provider + endpoint |
| Ollama backward compat | PROV-02 | Requires local Ollama running | Remove [llm] section from llm.toml; run `recall health`; verify Ollama provider shown |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed — all tests exist and pass (test_llm_config 24 passed, test_provider passes)

---
plan: 27-03
phase: 27-llm-provider
status: complete
completed: 2026-04-19
---

## Summary

Created `src/llm/health.py` with `HealthResult` dataclass and `check_health(config) -> HealthResult`. Probes LLM and embeddings providers within 5-second timeout. Never raises — all errors captured as UNREACHABLE status.

## Key Files

### Created
- `src/llm/health.py` — check_health() + HealthResult
- `tests/test_llm_health_v3.py` — 6 tests (all mocked)

## Test Results

```
19 passed in 0.11s  (all 3 test files combined)
```

## Decisions

- asyncio.wait_for(timeout=5.0) wraps both chat and embed probes
- TimeoutError caught alongside LLMError → UNREACHABLE
- bare Exception fallback catches unexpected errors without raising
- embeddings_status "not configured" when config.embeddings is None

## Self-Check: PASSED

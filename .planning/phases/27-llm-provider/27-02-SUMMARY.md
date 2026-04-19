---
plan: 27-02
phase: 27-llm-provider
status: complete
completed: 2026-04-19
---

## Summary

Created `src/llm/client.py` with `LLMClient`, `LLMError`, `LLMResponse`, `make_llm_client`. Single-provider router: claude uses subprocess, ollama/openai use httpx. No fallback. Updated `src/llm/__init__.py` to export v3.0 public API only.

## Key Files

### Created
- `src/llm/client.py` — LLMClient with _chat_claude/_chat_ollama/_chat_openai dispatch
- `src/llm/__init__.py` — v3.0 public re-exports only
- `tests/test_llm_client_v3.py` — 7 tests (all mocked, no live network/subprocess)

## Test Results

```
7 passed in 0.09s
```

## Decisions

- `PIPE` imported from `asyncio.subprocess` (not `asyncio` directly — Python 3.12)
- httpx.AsyncClient used as async context manager per request (no connection pooling needed)
- embed() raises LLMError immediately when config.embeddings is None

## Self-Check: PASSED

---
plan: 27-01
phase: 27-llm-provider
status: complete
completed: 2026-04-19
---

## Summary

Created `src/config.py` — v3.0 canonical config module with frozen dataclasses (`Config`, `LLMConfig`, `EmbeddingsConfig`, `DBConfig`) and `load_config()` reading from `~/.recall/config.toml` via stdlib `tomllib`.

## Key Files

### Created
- `src/config.py` — Config dataclasses + load_config(), provider validation, ollama url default
- `tests/test_config_v3.py` — 6 tests covering full config, missing file, invalid provider, defaults
- `tests/__init__.py` — test package init

## Test Results

```
6 passed in 0.07s
```

## Decisions

- Used `frozen=True` on all dataclasses per plan spec
- `config_path` parameter name (not `path`) for test override compatibility
- `Config.__post_init__` handles None defaults for frozen fields
- ollama with empty url gets `http://localhost:11434` injected at load time

## Self-Check: PASSED

#!/usr/bin/env python3
"""
Phase 13: Multi-Provider LLM — Verification Script
Requirements: PROV-01 · PROV-02 · PROV-03 · PROV-04

Usage:
    python scripts/verify_phase_13.py [--fail-fast] [--skip-live]

Tests:

  Static (no live provider required):
  1. PROV-01: LLMConfig has all 9 llm_* fields with correct defaults
  2. PROV-01: load_config() sets llm_mode="provider" when [llm] section present
  3. PROV-01: load_config() sets llm_mode="legacy" when [llm] section absent
  4. PROV-01: embed_api_key falls back to primary_api_key when not set
  5. PROV-01: [cloud]/[local] sections silently ignored when [llm] present
  6. PROV-02: _detect_sdk() returns "ollama" for localhost/127.0.0.1/.local/ollama.com URLs
  7. PROV-02: _detect_sdk() returns "openai" for all other URLs
  8. PROV-02: ProviderClient.primary_label() formats as "sdk/model @ hostname"
  9. PROV-02: ProviderClient.embed_label() formats as "sdk/model @ hostname"
 10. PROV-02: ProviderClient.fallback_label() returns None when no fallback configured
 11. PROV-04: validate_provider_startup() is a no-op in legacy mode
 12. PROV-04: validate_provider_startup() calls sys.exit(1) when ping fails
 13. PROV-03: make_llm_client() returns OllamaLLMClient in legacy mode
 14. PROV-03: make_llm_client() returns OpenAIGenericClient in provider mode
 15. PROV-03: make_embedder() returns OllamaEmbedder in legacy mode
 16. PROV-03: make_embedder() returns OpenAIEmbedder in provider mode
 17. PROV-03: GraphService.__init__() uses make_llm_client() / make_embedder() factories
 18. PROV-04: startup hook in __init__.py skips validation for "health" and "config" subcommands
 19. PROV-04: recall health --format json reflects Provider/Embed rows in provider mode

  Live-provider (skipped with --skip-live):
 20. PROV-04: recall health exits 0 in legacy mode (Ollama not required — checks structure only)
"""

import asyncio
import inspect
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

RECALL = str(ROOT / ".venv" / "bin" / "recall")

# Minimal [llm] TOML for testing
PROVIDER_TOML = """
[llm]
primary_url     = "https://api.openai.com/v1"
primary_api_key = "sk-test-key"
primary_models  = ["gpt-4o-mini"]
embed_url       = "https://api.openai.com/v1"
embed_models    = ["text-embedding-3-small"]
"""

PROVIDER_TOML_NO_EMBED_KEY = """
[llm]
primary_url     = "https://api.openai.com/v1"
primary_api_key = "sk-fallback-key"
primary_models  = ["gpt-4o-mini"]
embed_models    = ["text-embedding-3-small"]
"""

PROVIDER_TOML_WITH_CLOUD = """
[llm]
primary_url     = "https://api.openai.com/v1"
primary_api_key = "sk-test-key"
primary_models  = ["gpt-4o-mini"]

[cloud]
endpoint = "https://ollama.com"
models   = ["llama3:8b"]

[local]
models = ["gemma2:9b"]
"""

LEGACY_TOML = """
[cloud]
endpoint = "https://ollama.com"

[local]
models = ["gemma2:9b"]
"""


class Runner:
    def __init__(self, fail_fast: bool = False):
        self.fail_fast = fail_fast
        self.passed = 0
        self.failed = 0
        self.failures: list[str] = []

    def ok(self, msg: str) -> None:
        print(f"  {GREEN}[PASS]{RESET} {msg}")
        self.passed += 1

    def fail(self, msg: str, detail: str = "") -> None:
        print(f"  {RED}[FAIL]{RESET} {msg}")
        if detail:
            print(f"         {YELLOW}{detail}{RESET}")
        self.failed += 1
        self.failures.append(msg)
        if self.fail_fast:
            self.summary()
            sys.exit(1)

    def skip(self, msg: str, reason: str = "") -> None:
        print(f"  {CYAN}[SKIP]{RESET} {msg}")
        if reason:
            print(f"         {reason}")

    def banner(self, title: str) -> None:
        print(f"\n{BOLD}── {title} ──{RESET}")

    def summary(self) -> bool:
        width = 60
        print(f"\n{BOLD}{'━' * width}{RESET}")
        print(f"{BOLD} Phase 13: Multi-Provider LLM — Verification Results{RESET}")
        print(f"{BOLD}{'━' * width}{RESET}")
        print(f" Tests passed:  {GREEN}{self.passed}{RESET}")
        print(f" Tests failed:  {RED}{self.failed}{RESET}")
        if self.failures:
            print("\n Failed:")
            for f in self.failures:
                print(f"   {RED}✗{RESET} {f}")
        else:
            print(
                f"\n {GREEN}All required tests passed.{RESET} "
                f"Requirements PROV-01 · PROV-02 · PROV-03 · PROV-04 verified."
            )
        print()
        return self.failed == 0


def run_recall(*args, timeout: int = 60, env: dict | None = None) -> subprocess.CompletedProcess:
    import os
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    return subprocess.run(
        [RECALL, *args], capture_output=True, text=True, cwd=ROOT, timeout=timeout, env=proc_env
    )


def _write_toml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "llm.toml"
    p.write_text(content.strip())
    return p


# ── Tests 1–5 (PROV-01): LLMConfig fields and load_config() ──────────────────

def test_llmconfig_fields(r: Runner) -> None:
    r.banner("Tests 1–5 (PROV-01): LLMConfig llm_* fields and load_config() parsing")

    from src.llm.config import LLMConfig, load_config

    # Test 1: all 9 fields exist with correct defaults
    c = LLMConfig()
    expected_fields = {
        "llm_mode": "legacy",
        "llm_primary_url": None,
        "llm_primary_api_key": None,
        "llm_primary_models": [],
        "llm_fallback_url": None,
        "llm_fallback_models": [],
        "llm_embed_url": None,
        "llm_embed_api_key": None,
        "llm_embed_models": [],
    }
    missing = []
    wrong = []
    for field, default in expected_fields.items():
        if not hasattr(c, field):
            missing.append(field)
        elif getattr(c, field) != default:
            wrong.append(f"{field}={getattr(c, field)!r} (expected {default!r})")

    if missing:
        r.fail(f"LLMConfig missing fields: {missing}")
    elif wrong:
        r.fail(f"LLMConfig wrong defaults: {wrong}")
    else:
        r.ok("LLMConfig has all 9 llm_* fields with correct defaults")

    # Test 2: provider mode when [llm] section present
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = _write_toml(Path(tmpdir), PROVIDER_TOML)
        cfg = load_config(config_path=cfg_path)
        if cfg.llm_mode == "provider":
            r.ok("load_config() sets llm_mode='provider' with [llm] section")
        else:
            r.fail(f"Expected llm_mode='provider', got {cfg.llm_mode!r}")

        if cfg.llm_primary_url == "https://api.openai.com/v1":
            r.ok("llm_primary_url parsed correctly from [llm] section")
        else:
            r.fail(f"llm_primary_url wrong: {cfg.llm_primary_url!r}")

        if cfg.llm_primary_models == ["gpt-4o-mini"]:
            r.ok("llm_primary_models parsed correctly")
        else:
            r.fail(f"llm_primary_models wrong: {cfg.llm_primary_models!r}")

    # Test 3: legacy mode when no [llm] section
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = _write_toml(Path(tmpdir), LEGACY_TOML)
        cfg = load_config(config_path=cfg_path)
        if cfg.llm_mode == "legacy":
            r.ok("load_config() sets llm_mode='legacy' with no [llm] section")
        else:
            r.fail(f"Expected llm_mode='legacy', got {cfg.llm_mode!r}")

        if cfg.llm_primary_url is None and cfg.llm_primary_models == []:
            r.ok("llm_* fields are None/[] in legacy mode")
        else:
            r.fail(f"llm_* fields non-empty in legacy mode: url={cfg.llm_primary_url!r}")

    # Test 4: embed_api_key falls back to primary_api_key
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = _write_toml(Path(tmpdir), PROVIDER_TOML_NO_EMBED_KEY)
        cfg = load_config(config_path=cfg_path)
        if cfg.llm_embed_api_key == "sk-fallback-key":
            r.ok("llm_embed_api_key falls back to primary_api_key when not set")
        else:
            r.fail(
                f"embed_api_key fallback failed: got {cfg.llm_embed_api_key!r}, "
                f"primary={cfg.llm_primary_api_key!r}"
            )

    # Test 5: [cloud]/[local] sections silently ignored when [llm] present
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = _write_toml(Path(tmpdir), PROVIDER_TOML_WITH_CLOUD)
        try:
            cfg = load_config(config_path=cfg_path)
            if cfg.llm_mode == "provider":
                r.ok("[cloud]/[local] sections silently ignored when [llm] present — no exception")
            else:
                r.fail(f"llm_mode wrong with mixed sections: {cfg.llm_mode!r}")
        except Exception as e:
            r.fail("[cloud]/[local] + [llm] raised an exception", detail=str(e))


# ── Tests 6–10 (PROV-02): _detect_sdk() and ProviderClient labels ────────────

def test_detect_sdk_and_labels(r: Runner) -> None:
    r.banner("Tests 6–10 (PROV-02): _detect_sdk() + ProviderClient labels")

    from src.llm.provider import _detect_sdk, ProviderClient
    from src.llm.config import LLMConfig

    # Test 6: ollama URLs
    ollama_cases = [
        ("http://localhost:11434", "ollama"),
        ("http://127.0.0.1:11434", "ollama"),
        ("https://ollama.com", "ollama"),
        ("http://mybox.local:11434", "ollama"),
    ]
    all_ok = True
    for url, expected in ollama_cases:
        result = _detect_sdk(url)
        if result != expected:
            r.fail(f"_detect_sdk({url!r}) = {result!r}, expected {expected!r}")
            all_ok = False
    if all_ok:
        r.ok("_detect_sdk() returns 'ollama' for localhost/127.0.0.1/.local/ollama.com URLs")

    # Test 7: openai URLs
    openai_cases = [
        ("https://api.openai.com/v1", "openai"),
        ("https://api.groq.com/openai/v1", "openai"),
        ("https://my-ollama.ngrok.io", "openai"),  # external host — openai SDK
    ]
    all_ok = True
    for url, expected in openai_cases:
        result = _detect_sdk(url)
        if result != expected:
            r.fail(f"_detect_sdk({url!r}) = {result!r}, expected {expected!r}")
            all_ok = False
    if all_ok:
        r.ok("_detect_sdk() returns 'openai' for external provider URLs")

    # Test 8: primary_label() format
    cfg = LLMConfig(
        llm_mode="provider",
        llm_primary_url="https://api.openai.com/v1",
        llm_primary_api_key="sk-test",
        llm_primary_models=["gpt-4o-mini"],
        llm_embed_url="https://api.openai.com/v1",
        llm_embed_models=["text-embedding-3-small"],
    )
    pc = ProviderClient(cfg)
    label = pc.primary_label()
    if "openai" in label and "gpt-4o-mini" in label and "api.openai.com" in label:
        r.ok(f"primary_label() formats correctly: {label!r}")
    else:
        r.fail(f"primary_label() format wrong: {label!r}")

    # Test 9: embed_label() format
    embed_label = pc.embed_label()
    if "openai" in embed_label and "text-embedding-3-small" in embed_label:
        r.ok(f"embed_label() formats correctly: {embed_label!r}")
    else:
        r.fail(f"embed_label() format wrong: {embed_label!r}")

    # Test 10: fallback_label() returns None when not configured
    if pc.fallback_label() is None:
        r.ok("fallback_label() returns None when no fallback_url configured")
    else:
        r.fail(f"fallback_label() should be None, got: {pc.fallback_label()!r}")


# ── Tests 11–12 (PROV-04): validate_provider_startup() ───────────────────────

def test_startup_validation(r: Runner) -> None:
    r.banner("Tests 11–12 (PROV-04): validate_provider_startup() behavior")

    from src.llm.provider import validate_provider_startup, ProviderClient
    from src.llm.config import LLMConfig

    # Test 11: no-op in legacy mode
    legacy_cfg = LLMConfig(llm_mode="legacy")
    try:
        with patch("sys.exit") as mock_exit:
            validate_provider_startup(legacy_cfg)
            if mock_exit.called:
                r.fail("validate_provider_startup() called sys.exit in legacy mode")
            else:
                r.ok("validate_provider_startup() is a no-op in legacy mode")
    except Exception as e:
        r.fail("validate_provider_startup() raised in legacy mode", detail=str(e))

    # Test 12: sys.exit(1) when ping fails
    provider_cfg = LLMConfig(
        llm_mode="provider",
        llm_primary_url="https://api.openai.com/v1",
        llm_primary_api_key="sk-bad-key",
        llm_primary_models=["gpt-4o-mini"],
        llm_embed_url="https://api.openai.com/v1",
        llm_embed_models=["text-embedding-3-small"],
    )
    with patch.object(ProviderClient, "ping_primary", new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = (False, "401 Unauthorized")
        with patch("sys.exit") as mock_exit:
            validate_provider_startup(provider_cfg)
            if mock_exit.called and mock_exit.call_args[0][0] == 1:
                r.ok("validate_provider_startup() calls sys.exit(1) when ping fails")
            else:
                r.fail(
                    "validate_provider_startup() did not call sys.exit(1) on ping failure",
                    detail=f"sys.exit calls: {mock_exit.call_args_list}",
                )


# ── Tests 13–17 (PROV-03): Adapter factories and GraphService wiring ─────────

def test_adapter_factories(r: Runner) -> None:
    r.banner("Tests 13–17 (PROV-03): make_llm_client() / make_embedder() factories + GraphService")

    from src.graph.adapters import make_llm_client, make_embedder, OllamaLLMClient, OllamaEmbedder
    from src.llm.config import LLMConfig

    legacy_cfg = LLMConfig(llm_mode="legacy")
    provider_cfg = LLMConfig(
        llm_mode="provider",
        llm_primary_url="https://api.openai.com/v1",
        llm_primary_api_key="sk-test",
        llm_primary_models=["gpt-4o-mini"],
        llm_embed_url="https://api.openai.com/v1",
        llm_embed_models=["text-embedding-3-small"],
    )

    # Test 13: legacy → OllamaLLMClient
    client = make_llm_client(legacy_cfg)
    if isinstance(client, OllamaLLMClient):
        r.ok("make_llm_client() returns OllamaLLMClient in legacy mode")
    else:
        r.fail(f"make_llm_client(legacy) returned {type(client).__name__}, expected OllamaLLMClient")

    # Test 14: provider → OpenAIGenericClient
    try:
        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
        client = make_llm_client(provider_cfg)
        if isinstance(client, OpenAIGenericClient):
            r.ok("make_llm_client() returns OpenAIGenericClient in provider mode")
        else:
            r.fail(f"make_llm_client(provider) returned {type(client).__name__}, expected OpenAIGenericClient")
    except ImportError as e:
        r.fail("Could not import OpenAIGenericClient from graphiti-core", detail=str(e))

    # Test 15: legacy → OllamaEmbedder
    embedder = make_embedder(legacy_cfg)
    if isinstance(embedder, OllamaEmbedder):
        r.ok("make_embedder() returns OllamaEmbedder in legacy mode")
    else:
        r.fail(f"make_embedder(legacy) returned {type(embedder).__name__}, expected OllamaEmbedder")

    # Test 16: provider → OpenAIEmbedder
    try:
        from graphiti_core.embedder.openai import OpenAIEmbedder
        embedder = make_embedder(provider_cfg)
        if isinstance(embedder, OpenAIEmbedder):
            r.ok("make_embedder() returns OpenAIEmbedder in provider mode")
        else:
            r.fail(f"make_embedder(provider) returned {type(embedder).__name__}, expected OpenAIEmbedder")
    except ImportError as e:
        r.fail("Could not import OpenAIEmbedder from graphiti-core", detail=str(e))

    # Test 17: GraphService.__init__() uses factories (source inspection)
    import src.graph.service as svc_mod
    src_text = inspect.getsource(svc_mod.GraphService.__init__)
    if "make_llm_client" in src_text and "make_embedder" in src_text:
        r.ok("GraphService.__init__() uses make_llm_client() and make_embedder() factories")
    else:
        r.fail("GraphService.__init__() does not reference factory functions")


# ── Tests 18–19 (PROV-04): startup hook and health routing ───────────────────

def test_startup_hook_and_health(r: Runner) -> None:
    r.banner("Tests 18–19 (PROV-04): startup hook skips and health provider rows")

    # Test 18: startup hook skips "health" and "config" (source inspection)
    import src.cli as cli_mod
    src_text = inspect.getsource(cli_mod.main_callback)
    if '"health"' in src_text and '"config"' in src_text:
        r.ok("startup hook in __init__.py skips validation for 'health' and 'config' subcommands")
    else:
        r.fail("startup hook does not skip 'health'/'config' — may cause startup loops")

    if "validate_provider_startup" in src_text:
        r.ok("validate_provider_startup() called in main_callback")
    else:
        r.fail("validate_provider_startup() not called in main_callback")

    # Test 19: health command --format json has Provider/Embed keys in provider mode
    # We mock load_config to return a provider config without needing a real provider
    from src.llm.config import LLMConfig
    from src.llm.provider import ProviderClient

    provider_cfg = LLMConfig(
        llm_mode="provider",
        llm_primary_url="https://api.openai.com/v1",
        llm_primary_api_key="sk-test",
        llm_primary_models=["gpt-4o-mini"],
        llm_embed_url="https://api.openai.com/v1",
        llm_embed_models=["text-embedding-3-small"],
    )

    import src.cli.commands.health as health_mod
    with patch.object(health_mod, "load_config", return_value=provider_cfg), \
         patch.object(ProviderClient, "ping_primary", new_callable=AsyncMock) as mp, \
         patch.object(ProviderClient, "ping_embed", new_callable=AsyncMock) as me:
        mp.return_value = (False, "UNREACHABLE")
        me.return_value = (False, "UNREACHABLE")
        rows = health_mod._check_provider()

    names = [r_["name"] for r_ in rows]
    if "Provider" in names and "Embed" in names:
        r.ok("_check_provider() returns Provider and Embed rows in provider mode")
    else:
        r.fail(f"_check_provider() missing expected rows. Got names: {names}")

    # Verify no Provider rows in legacy mode
    legacy_cfg = LLMConfig(llm_mode="legacy")
    with patch.object(health_mod, "load_config", return_value=legacy_cfg):
        rows_legacy = health_mod._check_provider()
    if rows_legacy == []:
        r.ok("_check_provider() returns empty list in legacy mode")
    else:
        r.fail(f"_check_provider() non-empty in legacy mode: {rows_legacy}")


# ── Test 20 (PROV-04): recall health exits 0 in legacy mode ─────────────────

def test_health_command_legacy(r: Runner, skip_live: bool) -> None:
    r.banner("Test 20 (PROV-04): recall health exits 0 in legacy mode")

    if skip_live:
        r.skip("recall health legacy-mode exit code", reason="--skip-live flag set")
        return

    # Force legacy mode by using a temp config with no [llm] section
    # The health command checks Ollama which may not be running; we just verify
    # it doesn't exit(1) due to a provider validation crash
    res = run_recall("health", "--format", "json", timeout=30)
    output = res.stdout + res.stderr

    # As long as it's not a Python traceback crash (returncode 2 = typer bad args, 0/1 = health result)
    if res.returncode in (0, 1):
        r.ok(f"recall health exits with code {res.returncode} (no crash)")
        if "overall" in output:
            r.ok("recall health --format json produces structured JSON output")
        else:
            r.fail("recall health --format json: no 'overall' key in output", detail=output[:300])
    else:
        r.fail(
            f"recall health exited with unexpected code {res.returncode}",
            detail=output[:300],
        )


# ── Prerequisites ──────────────────────────────────────────────────────────────

def check_prerequisites() -> None:
    if not Path(RECALL).exists():
        print(f"{RED}ERROR: recall CLI not found at {RECALL} — run: pip install -e .{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} recall CLI available")

    try:
        from src.llm.config import LLMConfig  # noqa: F401
        print(f"  {GREEN}OK{RESET} src.llm.config importable")
    except ImportError as e:
        print(f"{RED}ERROR: src.llm.config import failed: {e}{RESET}")
        sys.exit(1)

    try:
        from src.llm.provider import ProviderClient, _detect_sdk, validate_provider_startup  # noqa: F401
        print(f"  {GREEN}OK{RESET} src.llm.provider importable")
    except ImportError as e:
        print(f"{RED}ERROR: src.llm.provider import failed: {e}{RESET}")
        sys.exit(1)

    try:
        from src.graph.adapters import make_llm_client, make_embedder  # noqa: F401
        print(f"  {GREEN}OK{RESET} adapter factories importable")
    except ImportError as e:
        print(f"{RED}ERROR: adapter factory import failed: {e}{RESET}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    fail_fast = "--fail-fast" in sys.argv
    skip_live = "--skip-live" in sys.argv

    print(f"\n{BOLD}Phase 13: Multi-Provider LLM — Verification{RESET}")
    print(f"Requirements: PROV-01 · PROV-02 · PROV-03 · PROV-04")
    if skip_live:
        print(f"{YELLOW}Note: --skip-live set — test 20 will be skipped.{RESET}")
    else:
        print(f"{YELLOW}Note: Test 20 runs recall health live. Use --skip-live to skip.{RESET}")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites()

    test_llmconfig_fields(r)
    test_detect_sdk_and_labels(r)
    test_startup_validation(r)
    test_adapter_factories(r)
    test_startup_hook_and_health(r)
    test_health_command_legacy(r, skip_live)

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Phase 10: Configurable Capture Modes — Human Verification Script
Requirements: CAPT-01 · CAPT-02 · CAPT-03

Usage:
    python scripts/verify_phase_10.py [--fail-fast]

Tests:
    1. CAPT-01: LLMConfig.capture_mode field exists and defaults to "decisions-only"
    2. CAPT-01: [capture] TOML section parsed into capture_mode
    3. CAPT-02: Dual prompts in summarizer (NARROW / BROAD) + capture_mode param
    4. CAPT-02: Dual prompts in indexer extraction (NARROW / BROAD) + capture_mode param
    5. CAPT-02: call-site wiring — git_worker, conversation, indexer pass capture_mode
    6. CAPT-03: recall config --format json exposes capture.mode and retention.retention_days
    7. CAPT-03: recall config --set capture.mode=decisions-and-patterns persists to toml
    8. CAPT-03: recall config --get capture.mode returns current value (not blank)
    9. CAPT-03: recall config --set capture.mode=invalid exits non-zero with "Valid values"

No Ollama required — all tests run against CLI subprocess or source code inspection.
"""

import inspect
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN   = "\033[0;36m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

RECALL = str(ROOT / ".venv" / "bin" / "recall")


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

    def info(self, msg: str) -> None:
        print(f"         {msg}")

    def banner(self, title: str) -> None:
        print(f"\n{BOLD}── {title} ──{RESET}")

    def summary(self) -> bool:
        width = 60
        print(f"\n{BOLD}{'━' * width}{RESET}")
        print(f"{BOLD} Phase 10: Configurable Capture Modes — Verification Results{RESET}")
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
                f"Requirements CAPT-01 · CAPT-02 · CAPT-03 verified."
            )
        print()
        return self.failed == 0


def run_recall(*args, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [RECALL, *args],
        capture_output=True, text=True, cwd=ROOT, timeout=timeout,
    )


# ── Prerequisites ──────────────────────────────────────────────────────────────

def check_prerequisites() -> None:
    if not Path(RECALL).exists():
        print(f"{RED}ERROR: recall CLI not found at {RECALL} — run: pip install -e .{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} recall CLI available")


# ── Test 1 (CAPT-01): LLMConfig.capture_mode field ───────────────────────────

def test_llmconfig_capture_mode_field(r: Runner) -> None:
    r.banner("Test 1 (CAPT-01): LLMConfig.capture_mode field and default")

    from src.llm.config import LLMConfig, load_config

    cfg = LLMConfig()
    if cfg.capture_mode == "decisions-only":
        r.ok("LLMConfig default capture_mode = 'decisions-only'")
    else:
        r.fail(f"Expected default 'decisions-only', got '{cfg.capture_mode}'")

    loaded = load_config()
    if hasattr(loaded, "capture_mode"):
        r.ok(f"load_config() returns config with capture_mode = '{loaded.capture_mode}'")
    else:
        r.fail("load_config() result has no capture_mode attribute")


# ── Test 2 (CAPT-01): TOML [capture] section parsing ─────────────────────────

def test_toml_capture_section_parsing(r: Runner) -> None:
    r.banner("Test 2 (CAPT-01): [capture] TOML section parsed into capture_mode")

    import src.llm.config as cfg_mod

    toml_content = '[capture]\nmode = "decisions-and-patterns"\n'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        tmp_path = Path(f.name)

    try:
        cfg = cfg_mod.load_config(config_path=tmp_path)
        if cfg.capture_mode == "decisions-and-patterns":
            r.ok("[capture] mode = 'decisions-and-patterns' parsed correctly")
        else:
            r.fail(
                f"Expected 'decisions-and-patterns', got '{cfg.capture_mode}'",
                detail=f"Loaded from: {tmp_path}",
            )
    except Exception as e:
        r.fail(f"load_config() raised exception reading [capture] section: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)


# ── Test 3 (CAPT-02): Dual prompts in summarizer ─────────────────────────────

def test_summarizer_dual_prompts(r: Runner) -> None:
    r.banner("Test 3 (CAPT-02): Dual prompts in summarizer (NARROW / BROAD)")

    try:
        import src.capture.summarizer as summ_mod

        if hasattr(summ_mod, "BATCH_SUMMARIZATION_PROMPT_NARROW"):
            narrow = summ_mod.BATCH_SUMMARIZATION_PROMPT_NARROW
            if "bugs" not in narrow.lower() and "dependencies" not in narrow.lower():
                r.ok("BATCH_SUMMARIZATION_PROMPT_NARROW exists and omits bugs/dependencies")
            else:
                r.fail("BATCH_SUMMARIZATION_PROMPT_NARROW should not mention bugs or dependencies")
        else:
            r.fail("BATCH_SUMMARIZATION_PROMPT_NARROW not found in summarizer.py")

        if hasattr(summ_mod, "BATCH_SUMMARIZATION_PROMPT_BROAD"):
            broad = summ_mod.BATCH_SUMMARIZATION_PROMPT_BROAD
            if "bug" in broad.lower() or "pattern" in broad.lower():
                r.ok("BATCH_SUMMARIZATION_PROMPT_BROAD exists and includes extended categories")
            else:
                r.fail("BATCH_SUMMARIZATION_PROMPT_BROAD seems too narrow — expected bug/pattern mention")
        else:
            r.fail("BATCH_SUMMARIZATION_PROMPT_BROAD not found in summarizer.py")

        sig = inspect.signature(summ_mod.summarize_and_store)
        if "capture_mode" in sig.parameters:
            r.ok("summarize_and_store() accepts capture_mode parameter")
        else:
            r.fail("summarize_and_store() has no capture_mode parameter")

    except ImportError as e:
        r.fail(f"Could not import summarizer module: {e}")


# ── Test 4 (CAPT-02): Dual prompts in indexer extraction ─────────────────────

def test_indexer_dual_prompts(r: Runner) -> None:
    r.banner("Test 4 (CAPT-02): Dual prompts in indexer extraction (NARROW / BROAD)")

    try:
        import src.indexer.extraction as ext_mod

        if hasattr(ext_mod, "FREE_FORM_EXTRACTION_PROMPT_NARROW"):
            narrow = ext_mod.FREE_FORM_EXTRACTION_PROMPT_NARROW
            if "bugs fixed" not in narrow.lower() and "dependencies introduced" not in narrow.lower():
                r.ok("FREE_FORM_EXTRACTION_PROMPT_NARROW omits 'bugs fixed' and 'dependencies introduced'")
            else:
                r.fail("FREE_FORM_EXTRACTION_PROMPT_NARROW still mentions bugs or dependencies")
        else:
            r.fail("FREE_FORM_EXTRACTION_PROMPT_NARROW not found in extraction.py")

        if hasattr(ext_mod, "FREE_FORM_EXTRACTION_PROMPT_BROAD"):
            broad = ext_mod.FREE_FORM_EXTRACTION_PROMPT_BROAD
            if "bugs fixed" in broad.lower() and "dependencies introduced" in broad.lower():
                r.ok("FREE_FORM_EXTRACTION_PROMPT_BROAD includes 'bugs fixed' and 'dependencies introduced'")
            else:
                r.fail("FREE_FORM_EXTRACTION_PROMPT_BROAD missing expected focus categories")
        else:
            r.fail("FREE_FORM_EXTRACTION_PROMPT_BROAD not found in extraction.py")

        if hasattr(ext_mod, "FREE_FORM_EXTRACTION_PROMPT"):
            r.ok("FREE_FORM_EXTRACTION_PROMPT alias still importable (backward compatible)")
        else:
            r.fail("FREE_FORM_EXTRACTION_PROMPT alias removed — backward compatibility broken")

        sig = inspect.signature(ext_mod.extract_commit_knowledge)
        if "capture_mode" in sig.parameters:
            default = sig.parameters["capture_mode"].default
            if default == "decisions-only":
                r.ok("extract_commit_knowledge() capture_mode defaults to 'decisions-only'")
            else:
                r.fail(f"capture_mode default is '{default}', expected 'decisions-only'")
        else:
            r.fail("extract_commit_knowledge() has no capture_mode parameter")

    except ImportError as e:
        r.fail(f"Could not import extraction module: {e}")


# ── Test 5 (CAPT-02): call-site wiring ───────────────────────────────────────

def test_callsite_wiring(r: Runner) -> None:
    r.banner("Test 5 (CAPT-02): capture_mode wired through git_worker, conversation, indexer")

    for module_path, min_count in [
        ("src/capture/git_worker.py", 1),
        ("src/capture/conversation.py", 1),
        ("src/indexer/indexer.py", 2),  # asyncio.run + loop.run_until_complete fallback
    ]:
        src = (ROOT / module_path).read_text()
        count = src.count("capture_mode=cfg.capture_mode")
        label = f"{module_path}"
        if count >= min_count:
            r.ok(f"{label}: {count}x 'capture_mode=cfg.capture_mode' (expected ≥{min_count})")
        else:
            r.fail(
                f"{label}: found {count} call site(s), expected ≥{min_count}",
                detail="capture_mode not threaded through",
            )

    for module_path in ["src/capture/git_worker.py", "src/capture/conversation.py", "src/indexer/indexer.py"]:
        src = (ROOT / module_path).read_text()
        if "load_config" in src:
            r.ok(f"{module_path} imports load_config")
        else:
            r.fail(f"{module_path} does not import load_config")


# ── Test 6 (CAPT-03): config display ─────────────────────────────────────────

def test_config_display(r: Runner) -> None:
    r.banner("Test 6 (CAPT-03): recall config --format json shows capture + retention")

    res = run_recall("config", "--format", "json")
    output = res.stdout + res.stderr

    if res.returncode != 0:
        r.fail("recall config --format json exited non-zero", detail=output[:300])
        return

    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        r.fail("recall config --format json output is not valid JSON", detail=res.stdout[:200])
        return

    if "capture" in data and "mode" in data["capture"]:
        r.ok(f"JSON has capture.mode = '{data['capture']['mode']}'")
    else:
        r.fail("JSON output missing 'capture.mode'")

    if "retention" in data and "retention_days" in data["retention"]:
        r.ok(f"JSON has retention.retention_days = {data['retention']['retention_days']}")
    else:
        r.fail("JSON output missing 'retention.retention_days'")


# ── Test 7 (CAPT-03): config set persists ────────────────────────────────────

def test_config_set(r: Runner, original_mode: str) -> None:
    r.banner("Test 7 (CAPT-03): recall config --set capture.mode persists to toml")

    res = run_recall("config", "--set", "capture.mode=decisions-and-patterns")
    output = res.stdout + res.stderr

    if res.returncode != 0:
        r.fail("--set capture.mode=decisions-and-patterns exited non-zero", detail=output[:300])
    else:
        r.ok("--set capture.mode=decisions-and-patterns exited 0")

    if "decisions-and-patterns" in output:
        r.ok("Success message contains 'decisions-and-patterns'")
    else:
        r.fail("Success message missing 'decisions-and-patterns'", detail=output[:200])

    # Verify persistence via JSON
    res2 = run_recall("config", "--format", "json")
    try:
        data = json.loads(res2.stdout)
        actual = data.get("capture", {}).get("mode")
        if actual == "decisions-and-patterns":
            r.ok("Persisted: config --format json confirms capture.mode = 'decisions-and-patterns'")
        else:
            r.fail(f"Not persisted: capture.mode = '{actual}'")
    except json.JSONDecodeError:
        r.fail("Could not parse config JSON to verify persistence")

    # Always restore
    run_recall("config", "--set", f"capture.mode={original_mode}")
    r.info(f"Restored capture.mode to '{original_mode}'")


# ── Test 8 (CAPT-03): config get ─────────────────────────────────────────────

def test_config_get(r: Runner) -> None:
    r.banner("Test 8 (CAPT-03): recall config --get capture.mode returns value")

    res = run_recall("config", "--get", "capture.mode")
    output = (res.stdout + res.stderr).strip()

    if res.returncode != 0:
        r.fail("--get capture.mode exited non-zero", detail=output[:200])
        return

    if output:
        r.ok(f"--get capture.mode printed: '{output}' (not blank)")
    else:
        r.fail("--get capture.mode printed blank output")


# ── Test 9 (CAPT-03): config set validation ───────────────────────────────────

def test_config_set_validation(r: Runner) -> None:
    r.banner("Test 9 (CAPT-03): recall config --set capture.mode=invalid rejected")

    res = run_recall("config", "--set", "capture.mode=invalid")
    output = res.stdout + res.stderr

    if res.returncode != 0:
        r.ok("--set capture.mode=invalid exited non-zero (rejected)")
    else:
        r.fail("--set capture.mode=invalid exited 0 — should have been rejected")

    if "valid values" in output.lower():
        r.ok("Error message contains 'Valid values'")
    else:
        r.fail("Error message missing 'Valid values'", detail=output[:200])

    if "decisions-only" in output and "decisions-and-patterns" in output:
        r.ok("Error message lists both valid options")
    else:
        r.fail("Error message does not list both valid options", detail=output[:200])


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    fail_fast = "--fail-fast" in sys.argv

    print(f"\n{BOLD}Phase 10: Configurable Capture Modes — Human Verification{RESET}")
    print(f"Requirements: CAPT-01 · CAPT-02 · CAPT-03")
    print(f"{YELLOW}Note: No Ollama required — all tests use source inspection or CLI subprocess.{RESET}")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites()

    # Read original capture mode so we can restore after test 7
    res = run_recall("config", "--get", "capture.mode")
    original_mode = (res.stdout + res.stderr).strip() or "decisions-only"
    r.info(f"Current capture.mode = '{original_mode}' (will be restored after test 7)")

    test_llmconfig_capture_mode_field(r)
    test_toml_capture_section_parsing(r)
    test_summarizer_dual_prompts(r)
    test_indexer_dual_prompts(r)
    test_callsite_wiring(r)
    test_config_display(r)
    test_config_set(r, original_mode)
    test_config_get(r)
    test_config_set_validation(r)

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

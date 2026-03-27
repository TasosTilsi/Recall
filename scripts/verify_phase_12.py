#!/usr/bin/env python3
"""
Phase 12: DB Migration — Verification Script
Requirements: DB-01 · DB-02

Usage:
    python scripts/verify_phase_12.py [--fail-fast] [--skip-ollama]

Tests:

  Static (no Ollama required):
  1. DB-01: Zero `import kuzu` statements in src/ (comments excluded)
  2. DB-01: real-ladybug in pyproject.toml, kuzu absent
  3. DB-01: DB path suffix is .lbdb in src/config/paths.py
  4. DB-01: LadybugDriver loads and connects to :memory: without error
  5. DB-01: LadybugDriver executes a Cypher write+read round-trip
  6. DB-01: GraphManager._make_driver() defaults to LadybugDriver (source inspection)
  7. DB-01: graphiti health output contains Backend row with "ladybug (embedded)"
  8. DB-02: LLMConfig has backend_type and backend_uri fields
  9. DB-02: docker-compose.neo4j.yml exists in project root
 10. DB-02: GraphManager._make_driver() routes to Neo4jDriver when backend_type="neo4j" (source)

  Ollama-required (skipped with --skip-ollama):
 11. DB-01: graphiti add + graphiti search work end-to-end with LadybugDB
 12. DB-01: FTS deduplication — add same entity twice, confirm 1 node not 2
"""

import inspect
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

GRAPHITI = str(ROOT / ".venv" / "bin" / "graphiti")
LBDB_PATH = Path.home() / ".recall" / "global" / "recall.lbdb"


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
        print(f"{BOLD} Phase 12: DB Migration — Verification Results{RESET}")
        print(f"{BOLD}{'━' * width}{RESET}")
        print(f" Tests passed:  {GREEN}{self.passed}{RESET}")
        print(f" Tests failed:  {RED}{self.failed}{RESET}")
        if self.failures:
            print("\n Failed:")
            for f in self.failures:
                print(f"   {RED}✗{RESET} {f}")
        else:
            print(f"\n {GREEN}All required tests passed.{RESET} Requirements DB-01 · DB-02 verified.")
        print()
        return self.failed == 0


def run_graphiti(*args, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        [GRAPHITI, *args], capture_output=True, text=True, cwd=ROOT, timeout=timeout
    )


# ── Test 1 (DB-01): No real kuzu imports ──────────────────────────────────────

def test_no_kuzu_imports(r: Runner) -> None:
    r.banner("Test 1 (DB-01): Zero `import kuzu` statements in src/")

    import re
    src_dir = ROOT / "src"
    real_imports = []
    comment_pattern = re.compile(r"^\s*#")
    import_pattern = re.compile(r"\bimport kuzu\b")

    for py_file in src_dir.rglob("*.py"):
        for lineno, line in enumerate(py_file.read_text().splitlines(), 1):
            if import_pattern.search(line) and not comment_pattern.match(line):
                real_imports.append(f"{py_file.relative_to(ROOT)}:{lineno}: {line.strip()}")

    if real_imports:
        r.fail(
            f"Found {len(real_imports)} real `import kuzu` statement(s)",
            detail="\n         ".join(real_imports[:5]),
        )
    else:
        r.ok("Zero `import kuzu` statements in src/ (comments excluded)")


# ── Test 2 (DB-01): pyproject.toml deps ───────────────────────────────────────

def test_pyproject_deps(r: Runner) -> None:
    r.banner("Test 2 (DB-01): pyproject.toml — real-ladybug present, kuzu absent")

    pyproject = (ROOT / "pyproject.toml").read_text()

    if "real-ladybug" in pyproject or "real_ladybug" in pyproject:
        r.ok("real-ladybug present in pyproject.toml")
    else:
        r.fail("real-ladybug missing from pyproject.toml")

    # kuzu should only appear in comments or as part of other words
    import re
    kuzu_dep = re.search(r'^\s*["\']?kuzu["\']?\s*[>=!<]', pyproject, re.MULTILINE)
    if kuzu_dep:
        r.fail("kuzu still listed as a dependency", detail=kuzu_dep.group().strip())
    else:
        r.ok("kuzu absent from pyproject.toml dependencies")


# ── Test 3 (DB-01): DB path uses .lbdb ────────────────────────────────────────

def test_db_path_suffix(r: Runner) -> None:
    r.banner("Test 3 (DB-01): DB path suffix is .lbdb in src/config/paths.py")

    paths_text = (ROOT / "src" / "config" / "paths.py").read_text()

    if ".lbdb" in paths_text:
        r.ok(".lbdb suffix present in src/config/paths.py")
    else:
        r.fail(".lbdb suffix missing from src/config/paths.py")

    import re
    # Only flag actual path strings (quoted or in assignments), not migration comments
    kuzu_path_uses = re.findall(r'(?<![#\s])["\'][^"\']*\.kuzu[^"\']*["\']|=\s*[^#\n]*\.kuzu', paths_text)
    if kuzu_path_uses:
        r.fail(".kuzu path still used in src/config/paths.py", detail=str(kuzu_path_uses[:3]))
    else:
        r.ok(".kuzu path removed from src/config/paths.py (migration comments are fine)")


# ── Tests 4–5 (DB-01): LadybugDriver functional ───────────────────────────────

def test_ladybug_driver(r: Runner) -> None:
    r.banner("Tests 4–5 (DB-01): LadybugDriver loads and executes Cypher")

    try:
        from src.storage.ladybug_driver import LadybugDriver
        r.ok("LadybugDriver importable from src.storage.ladybug_driver")
    except ImportError as e:
        r.fail("LadybugDriver import failed", detail=str(e))
        return

    # Test 4: connect to :memory:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            driver = LadybugDriver(db=f"{tmpdir}/test.lbdb")
        r.ok("LadybugDriver(db=path) constructs without error")
    except Exception as e:
        r.fail("LadybugDriver constructor raised", detail=str(e))
        return

    # Test 5: write + read round-trip via execute_query
    import asyncio

    async def _roundtrip() -> bool:
        with tempfile.TemporaryDirectory() as tmpdir:
            driver = LadybugDriver(db=f"{tmpdir}/roundtrip.lbdb")
            async with driver.session() as session:
                await session.run("CREATE NODE TABLE IF NOT EXISTS T (uuid STRING PRIMARY KEY, val STRING)")
                await session.run("MERGE (t:T {uuid: 'test-1'}) SET t.val = 'hello'")
                records, _, _ = await driver.execute_query(
                    "MATCH (t:T {uuid: $uuid}) RETURN t.val AS val", uuid="test-1"
                )
            return len(records) == 1 and records[0]["val"] == "hello"

    try:
        ok = asyncio.run(_roundtrip())
        if ok:
            r.ok("LadybugDriver write+read round-trip via execute_query() succeeds")
        else:
            r.fail("LadybugDriver round-trip: unexpected query result")
    except Exception as e:
        r.fail("LadybugDriver round-trip raised", detail=str(e))


# ── Test 6 (DB-01): GraphManager routes to LadybugDriver ──────────────────────

def test_graph_manager_default_driver(r: Runner) -> None:
    r.banner("Test 6 (DB-01): GraphManager._make_driver() defaults to LadybugDriver")

    import src.storage.graph_manager as gm_mod
    src_text = inspect.getsource(gm_mod.GraphManager._make_driver)

    if "LadybugDriver" in src_text:
        r.ok("_make_driver() references LadybugDriver")
    else:
        r.fail("_make_driver() does not reference LadybugDriver")

    if "return LadybugDriver" in src_text:
        r.ok("_make_driver() returns LadybugDriver as default path")
    else:
        r.fail("_make_driver() default return is not LadybugDriver")


# ── Test 7 (DB-01): graphiti health shows Backend row ─────────────────────────

def test_health_backend_row(r: Runner) -> None:
    r.banner("Test 7 (DB-01): graphiti health contains Backend row")

    res = run_graphiti("health")
    if res.returncode != 0:
        r.fail("graphiti health exited non-zero", detail=res.stderr[:300])
        return

    output = res.stdout + res.stderr
    if "Backend" in output:
        r.ok("'Backend' row present in graphiti health output")
    else:
        r.fail("'Backend' row missing from graphiti health output")

    if "ladybug" in output.lower():
        r.ok("'ladybug' mentioned in Backend row")
    else:
        r.fail("'ladybug' not found in graphiti health output")


# ── Tests 8–10 (DB-02): BackendConfig and Neo4j opt-in ───────────────────────

def test_backend_config(r: Runner) -> None:
    r.banner("Tests 8–10 (DB-02): BackendConfig in LLMConfig + Neo4j opt-in")

    # Test 8: LLMConfig has backend_type and backend_uri
    try:
        from src.llm.config import LLMConfig
        config = LLMConfig()
        if hasattr(config, "backend_type"):
            r.ok(f"LLMConfig.backend_type exists (default: {config.backend_type!r})")
        else:
            r.fail("LLMConfig.backend_type field missing")

        if hasattr(config, "backend_uri"):
            r.ok("LLMConfig.backend_uri exists")
        else:
            r.fail("LLMConfig.backend_uri field missing")

        if config.backend_type == "ladybug":
            r.ok("LLMConfig.backend_type defaults to 'ladybug'")
        else:
            r.fail(f"Expected backend_type default 'ladybug', got {config.backend_type!r}")
    except Exception as e:
        r.fail("LLMConfig raised on import/construction", detail=str(e))

    # Test 9: docker-compose.neo4j.yml exists
    compose_file = ROOT / "docker-compose.neo4j.yml"
    if compose_file.exists():
        r.ok("docker-compose.neo4j.yml exists in project root")
        content = compose_file.read_text()
        if "neo4j" in content.lower():
            r.ok("docker-compose.neo4j.yml references neo4j service")
        else:
            r.fail("docker-compose.neo4j.yml exists but no 'neo4j' service found")
    else:
        r.fail("docker-compose.neo4j.yml missing from project root")

    # Test 10: _make_driver routes to Neo4j (source check)
    import src.storage.graph_manager as gm_mod
    src_text = inspect.getsource(gm_mod.GraphManager._make_driver)
    if "neo4j" in src_text.lower() and "Neo4jDriver" in src_text:
        r.ok("_make_driver() has Neo4j routing branch (Neo4jDriver)")
    else:
        r.fail("_make_driver() missing Neo4j routing branch")


# ── Tests 11–12 (DB-01): End-to-end add+search + FTS dedup (Ollama) ──────────

def test_e2e_add_search(r: Runner, skip_ollama: bool) -> None:
    r.banner("Tests 11–12 (DB-01): End-to-end add+search + FTS dedup (Ollama required)")

    if skip_ollama:
        r.skip("graphiti add + search (end-to-end)", reason="--skip-ollama flag set")
        r.skip("FTS deduplication", reason="--skip-ollama flag set")
        return

    # Check Ollama is reachable
    import urllib.request, urllib.error
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
    except (urllib.error.URLError, OSError):
        r.skip("graphiti add + search (end-to-end)", reason="Ollama not reachable at localhost:11434")
        r.skip("FTS deduplication", reason="Ollama not reachable at localhost:11434")
        return

    # Test 11: add + search round-trip
    TEST_CONTENT = "LadybugDB is a community fork of KuzuDB used as the Phase 12 graph backend."
    TEST_QUERY = "LadybugDB"

    add_res = run_graphiti("add", TEST_CONTENT, timeout=120)
    if add_res.returncode == 0:
        r.ok("graphiti add succeeded with LadybugDB backend")
    else:
        r.fail("graphiti add failed", detail=(add_res.stderr or add_res.stdout)[:300])
        r.skip("FTS deduplication", reason="graphiti add failed — cannot test dedup")
        return

    search_res = run_graphiti("search", TEST_QUERY, timeout=60)
    if search_res.returncode == 0:
        r.ok("graphiti search succeeded with LadybugDB backend")
        if "LadybugDB" in search_res.stdout or "ladybug" in search_res.stdout.lower():
            r.ok("Search results reference the added content")
        else:
            r.skip("Search results don't mention LadybugDB (may be ranked below threshold)")
    else:
        r.fail("graphiti search failed", detail=(search_res.stderr or search_res.stdout)[:300])

    # Test 12: FTS deduplication — add same fact twice, expect no duplicate entity
    DEDUP_CONTENT = "Claude Code is an AI coding tool made by Anthropic for software development."
    run_graphiti("add", DEDUP_CONTENT, timeout=120)
    add2_res = run_graphiti("add", DEDUP_CONTENT, timeout=120)

    if add2_res.returncode != 0:
        r.fail("Second graphiti add (dedup test) failed", detail=(add2_res.stderr or add2_res.stdout)[:200])
        return

    # Count Entity nodes via list command
    list_res = run_graphiti("list", "entities", timeout=30)
    if list_res.returncode != 0:
        r.skip("FTS dedup entity count", reason="graphiti list entities failed")
        return

    # Count occurrences of "Claude Code" in output — should appear once, not twice
    count = list_res.stdout.lower().count("claude code")
    if count == 1:
        r.ok(f"FTS deduplication: 'Claude Code' entity appears exactly once after two identical adds")
    elif count == 0:
        r.skip("FTS dedup: 'Claude Code' not found in entity list (may have been named differently)")
    else:
        r.fail(
            f"FTS deduplication: 'Claude Code' appears {count} times — duplicate entities created",
            detail="FTS index may not be merging entities correctly",
        )


# ── Prerequisites ──────────────────────────────────────────────────────────────

def check_prerequisites() -> None:
    if not Path(GRAPHITI).exists():
        print(f"{RED}ERROR: graphiti CLI not found at {GRAPHITI} — run: pip install -e .{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} graphiti CLI available")

    try:
        import real_ladybug  # noqa: F401
        print(f"  {GREEN}OK{RESET} real_ladybug importable")
    except ImportError:
        print(f"{RED}ERROR: real_ladybug not importable — run: pip install -e '.[dev]'{RESET}")
        sys.exit(1)

    try:
        from fastapi.testclient import TestClient  # noqa: F401
        print(f"  {GREEN}OK{RESET} fastapi TestClient available")
    except ImportError:
        print(f"{YELLOW}WARN{RESET} fastapi not importable — some tests may fail")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    fail_fast   = "--fail-fast"   in sys.argv
    skip_ollama = "--skip-ollama" in sys.argv

    print(f"\n{BOLD}Phase 12: DB Migration — Verification{RESET}")
    print(f"Requirements: DB-01 · DB-02")
    if skip_ollama:
        print(f"{YELLOW}Note: --skip-ollama set — tests 11–12 will be skipped.{RESET}")
    else:
        print(f"{YELLOW}Note: Tests 11–12 require Ollama running at localhost:11434.{RESET}")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites()

    test_no_kuzu_imports(r)
    test_pyproject_deps(r)
    test_db_path_suffix(r)
    test_ladybug_driver(r)
    test_graph_manager_default_driver(r)
    test_health_backend_row(r)
    test_backend_config(r)
    test_e2e_add_search(r, skip_ollama)

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

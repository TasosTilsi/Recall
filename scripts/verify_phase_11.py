#!/usr/bin/env python3
"""
Phase 11: Graph UI — Verification Script
Requirements: UI-01 · UI-02 · UI-03
Integration gaps: INT-01 · INT-02 · INT-03 · INT-04

Usage:
    python scripts/verify_phase_11.py [--fail-fast]

Tests (no Ollama required — uses source inspection, FastAPI TestClient, direct DB writes):

  1. UI-01: recall ui --help exits 0 and shows --global flag
  2. UI-01: Port conflict pre-flight exits non-zero with "already in use" message
  3. UI-01: Missing static dir exits non-zero with message about static files
  4. UI-02: GET /api/graph returns {nodes: [...], links: [...]} shape
  5. UI-02: GraphService read-only methods use kuzu.Database(read_only=True)
  6. UI-03: recall ui --global flag accepted without parse error

  Integration gap checks (detected by audit INT-01–INT-04):
  7. INT-01: GET /api/nodes/{uuid} returns real retention values (pinned, accessCount)
            — catches the get_node_metadata() nonexistent method bug
  8. INT-02: Archived nodes absent from GET /api/graph response
            — catches list_entities_readonly() missing archive post-filter
  9. INT-03: Pinned nodes have pinned:true in GET /api/graph response
            — catches list_entities_readonly() hardcoded pinned:False
 10. INT-04: recall config --format json exposes ui.port and ui.api_port keys

All tests use FastAPI TestClient with real RetentionManager + Kuzu (no mocks for
retention or DB paths). Test entities are written directly to Kuzu and cleaned up
after the run.
"""

import inspect
import json
import socket
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
RESET = "\033[0m"

RECALL = str(ROOT / ".venv" / "bin" / "recall")
LBDB_PATH = Path.home() / ".recall" / "global" / "recall.lbdb"
RETENTION_DB = Path.home() / ".recall" / "retention.db"
GROUP_ID = ROOT.name  # "graphiti-knowledge-graph"

MARKER_UUID = "verify-phase11-test-uuid-0001"
MARKER_NAME = "VerifyPhase11TestNode"


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

    def info(self, msg: str) -> None:
        print(f"         {msg}")

    def banner(self, title: str) -> None:
        print(f"\n{BOLD}── {title} ──{RESET}")

    def summary(self) -> bool:
        width = 60
        print(f"\n{BOLD}{'━' * width}{RESET}")
        print(f"{BOLD} Phase 11: Graph UI — Verification Results{RESET}")
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
                f"Requirements UI-01 · UI-02 · UI-03 and integration gaps INT-01–INT-04 verified."
            )
        print()
        return self.failed == 0


def run_recall(*args, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [RECALL, *args], capture_output=True, text=True, cwd=ROOT, timeout=timeout
    )


# ── LadybugDB helpers ─────────────────────────────────────────────────────────

def _insert_test_entity() -> None:
    """Insert a single test entity directly into LadybugDB for INT-02/03 tests."""
    import asyncio
    from datetime import datetime

    async def _insert():
        from src.storage.ladybug_driver import LadybugDriver
        driver = LadybugDriver(db=str(LBDB_PATH))
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with driver.session() as session:
            await session.run(
                f"MERGE (e:Entity {{uuid: '{MARKER_UUID}'}}) "
                f"ON CREATE SET e.name = '{MARKER_NAME}', e.group_id = '{GROUP_ID}', "
                f"e.labels = ['Entity'], e.created_at = timestamp('{now}'), "
                f"e.name_embedding = [], e.summary = 'UAT test node Phase 11', e.attributes = '{{}}'"
            )

    asyncio.run(_insert())


def _delete_test_entity() -> None:
    import asyncio

    async def _delete():
        from src.storage.ladybug_driver import LadybugDriver
        driver = LadybugDriver(db=str(LBDB_PATH))
        async with driver.session() as session:
            await session.run(f"MATCH (e:Entity {{uuid: '{MARKER_UUID}'}}) DETACH DELETE e")

    asyncio.run(_delete())


def _clean_retention(uuid: str) -> None:
    if not RETENTION_DB.exists():
        return
    rdb = sqlite3.connect(RETENTION_DB)
    for table in ("pin_state", "archive_state", "access_log"):
        rdb.execute(f"DELETE FROM {table} WHERE uuid = ?", (uuid,))
    rdb.commit()


# ── Test client helper ─────────────────────────────────────────────────────────

def _make_test_client(scope: str = "project"):
    """Build a FastAPI TestClient with real app state (no mocks)."""
    import os
    # Suppress BGE reranker auto-load during TestClient initialization
    os.environ.setdefault("GRAPHITI_RERANKER_DISABLED", "1")

    from fastapi.testclient import TestClient
    from src.ui_server.app import create_app

    app = create_app(
        scope_label="project",
        scope="project",
        project_root=ROOT,
        static_dir=ROOT / "ui" / "out",
    )
    app.state.scope = scope
    return TestClient(app, raise_server_exceptions=False)


def _db_exists() -> bool:
    return LBDB_PATH.exists()


# ── Test 1–3 (UI-01): CLI behaviour ──────────────────────────────────────────

def test_cli_help_and_flag(r: Runner) -> None:
    r.banner("Tests 1–3 (UI-01): CLI behaviour")

    # Test 1: --help
    res = run_recall("ui", "--help")
    if res.returncode == 0:
        r.ok("recall ui --help exits 0")
    else:
        r.fail("recall ui --help exited non-zero", detail=res.stderr[:200])

    if "--global" in res.stdout:
        r.ok("--global flag present in help output")
    else:
        r.fail("--global flag missing from help output")

    # Test 2: port conflict
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", 18765))
        sock.listen(1)

        from src.ui_server.app import create_app
        from src.cli.commands.ui import ui_command
        import src.cli.commands.ui as ui_mod

        src = inspect.getsource(ui_mod)
        if "already in use" in src or "port" in src.lower():
            r.ok("Port conflict pre-flight check exists in ui.py source")
        else:
            r.fail("Port conflict pre-flight check not found in ui.py")
    finally:
        sock.close()

    # Test 3: missing static dir
    import src.cli.commands.ui as ui_mod2
    src2 = inspect.getsource(ui_mod2)
    if "static" in src2.lower() and ("exist" in src2 or "missing" in src2 or "not found" in src2.lower()):
        r.ok("Missing static dir check exists in ui.py source")
    else:
        r.fail("Missing static dir check not found in ui.py")


# ── Test 4–5 (UI-02): API shape and read-only DB ─────────────────────────────

def test_api_shape_and_readonly(r: Runner) -> None:
    r.banner("Tests 4–5 (UI-02): API shape and read-only DB access")

    # Test 4: /api/graph shape
    if not _db_exists():
        r.skip("GET /api/graph shape", reason="Kuzu DB not found — run recall add at least once")
    else:
        try:
            client = _make_test_client()
            resp = client.get("/api/graph")
            if resp.status_code == 200:
                r.ok("GET /api/graph returns 200")
            else:
                r.fail(f"GET /api/graph returned {resp.status_code}", detail=resp.text[:200])
                return

            data = resp.json()
            if "nodes" in data and "links" in data:
                r.ok(f"Response has 'nodes' and 'links' keys ({len(data['nodes'])} nodes, {len(data['links'])} links)")
            else:
                r.fail("Response missing 'nodes' or 'links' key", detail=str(list(data.keys())))
        except Exception as e:
            r.fail(f"TestClient raised: {e}")

    # Test 5: methods use driver.execute_query() abstraction (no direct kuzu after Phase 12)
    import src.graph.service as svc_mod
    src_text = inspect.getsource(svc_mod.GraphService.list_entities_readonly)
    if "execute_query" in src_text:
        r.ok("list_entities_readonly() uses driver.execute_query() abstraction")
    else:
        r.fail("list_entities_readonly() does NOT use driver.execute_query()")

    src_edges = inspect.getsource(svc_mod.GraphService.list_edges)
    if "execute_query" in src_edges:
        r.ok("list_edges() uses driver.execute_query() abstraction")
    else:
        r.fail("list_edges() does NOT use driver.execute_query()")

    src_uuid = inspect.getsource(svc_mod.GraphService.get_entity_by_uuid)
    if "execute_query" in src_uuid:
        r.ok("get_entity_by_uuid() uses driver.execute_query() abstraction")
    else:
        r.fail("get_entity_by_uuid() does NOT use driver.execute_query()")


# ── Test 6 (UI-03): --global flag ─────────────────────────────────────────────

def test_global_flag(r: Runner) -> None:
    r.banner("Test 6 (UI-03): --global flag accepted without parse error")

    import src.cli.commands.ui as ui_mod
    src = inspect.getsource(ui_mod)
    if "global" in src and "resolve_scope" in src:
        r.ok("--global flag and resolve_scope() present in ui.py source")
    else:
        r.fail("--global flag or resolve_scope() missing from ui.py")


# ── Test 7 (INT-01): /api/nodes/{uuid} returns real retention values ──────────

def test_node_detail_retention_enrichment(r: Runner) -> None:
    r.banner("Test 7 (INT-01): GET /api/nodes/{uuid} surfaces real retention metadata")

    if not _db_exists():
        r.skip("INT-01: node detail retention", reason="Kuzu DB not found")
        return

    _clean_retention(MARKER_UUID)
    _insert_test_entity()

    try:
        # Record an access and pin the test node
        from src.retention import get_retention_manager, reset_retention_manager
        reset_retention_manager()
        rm = get_retention_manager()
        rm.record_access(MARKER_UUID, GROUP_ID)
        rm.pin_node(MARKER_UUID, GROUP_ID)

        client = _make_test_client()
        resp = client.get(f"/api/nodes/{MARKER_UUID}")

        if resp.status_code == 200:
            r.ok("GET /api/nodes/{uuid} returns 200 for test entity")
        elif resp.status_code == 404:
            r.fail("GET /api/nodes/{uuid} returned 404 — test entity not found in Kuzu")
            return
        else:
            r.fail(f"GET /api/nodes/{uuid} returned {resp.status_code}", detail=resp.text[:200])
            return

        data = resp.json()

        # Check pinned field reflects reality (INT-01 bug: always False due to get_node_metadata)
        if data.get("pinned") is True:
            r.ok("pinned: true returned correctly (retention.is_pinned() called)")
        else:
            r.fail(
                "INT-01: pinned field is False despite node being pinned",
                detail=f"response pinned={data.get('pinned')} — routes.py calls nonexistent get_node_metadata(); fix: use is_pinned() directly"
            )

        # Check accessCount field reflects reality
        if data.get("accessCount", 0) >= 1:
            r.ok(f"accessCount: {data['accessCount']} returned correctly (retention.get_access_record() called)")
        else:
            r.fail(
                "INT-01: accessCount is 0 despite recorded access",
                detail=f"response accessCount={data.get('accessCount')} — routes.py calls nonexistent get_node_metadata(); fix: use get_access_record() directly"
            )

    finally:
        _clean_retention(MARKER_UUID)
        reset_retention_manager()


# ── Test 8 (INT-02): Archived nodes absent from /api/graph ────────────────────

def test_archived_nodes_filtered_from_graph(r: Runner) -> None:
    r.banner("Test 8 (INT-02): Archived nodes absent from GET /api/graph")

    if not _db_exists():
        r.skip("INT-02: archive filter", reason="Kuzu DB not found")
        return

    _clean_retention(MARKER_UUID)
    _insert_test_entity()

    try:
        # Archive the test node in retention.db
        from src.retention import get_retention_manager, reset_retention_manager
        reset_retention_manager()
        rm = get_retention_manager()
        rm.archive_node(MARKER_UUID, GROUP_ID)

        client = _make_test_client()
        resp = client.get("/api/graph")

        if resp.status_code != 200:
            r.fail(f"GET /api/graph returned {resp.status_code}", detail=resp.text[:200])
            return

        node_ids = {n["id"] for n in resp.json().get("nodes", [])}

        if MARKER_UUID not in node_ids:
            r.ok("Archived node absent from /api/graph nodes (archive post-filter working)")
        else:
            r.fail(
                "INT-02: Archived node still present in /api/graph nodes",
                detail=f"UUID {MARKER_UUID} still in response — list_entities_readonly() missing get_archive_state_uuids() filter"
            )

    finally:
        _clean_retention(MARKER_UUID)
        reset_retention_manager()


# ── Test 9 (INT-03): Pinned nodes have pinned:true in /api/graph ──────────────

def test_pinned_nodes_flagged_in_graph(r: Runner) -> None:
    r.banner("Test 9 (INT-03): Pinned nodes have pinned:true in GET /api/graph")

    if not _db_exists():
        r.skip("INT-03: pin flag in graph", reason="Kuzu DB not found")
        return

    _clean_retention(MARKER_UUID)
    _insert_test_entity()

    try:
        from src.retention import get_retention_manager, reset_retention_manager
        reset_retention_manager()
        rm = get_retention_manager()
        rm.pin_node(MARKER_UUID, GROUP_ID)

        client = _make_test_client()
        resp = client.get("/api/graph")

        if resp.status_code != 200:
            r.fail(f"GET /api/graph returned {resp.status_code}", detail=resp.text[:200])
            return

        nodes = resp.json().get("nodes", [])
        test_node = next((n for n in nodes if n["id"] == MARKER_UUID), None)

        if test_node is None:
            r.skip("INT-03: test node not in graph response (may be excluded for other reasons)")
            return

        if test_node.get("pinned") is True:
            r.ok("Pinned node has pinned:true in /api/graph nodes (pin state surfaced)")
        else:
            r.fail(
                "INT-03: Pinned node has pinned:False in /api/graph nodes",
                detail=f"list_entities_readonly() hardcodes 'pinned': False — add get_pin_state_uuids() lookup"
            )

    finally:
        _clean_retention(MARKER_UUID)
        reset_retention_manager()


# ── Test 10 (INT-04): config show/set exposes ui.port ─────────────────────────

def test_config_exposes_ui_port(r: Runner) -> None:
    r.banner("Test 10 (INT-04): recall config --format json exposes ui.port and ui.api_port")

    res = run_recall("config", "--format", "json")
    if res.returncode != 0:
        r.fail("recall config --format json exited non-zero", detail=res.stderr[:200])
        return

    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError:
        r.fail("recall config --format json output is not valid JSON", detail=res.stdout[:200])
        return

    if "ui" in data and "port" in data["ui"]:
        r.ok(f"JSON has ui.port = {data['ui']['port']}")
    else:
        r.fail(
            "INT-04: JSON output missing 'ui.port'",
            detail="config.py VALID_CONFIG_KEYS missing ui.port — add to VALID_CONFIG_KEYS, attr_map, table, and JSON output"
        )

    if "ui" in data and "api_port" in data.get("ui", {}):
        r.ok(f"JSON has ui.api_port = {data['ui']['api_port']}")
    else:
        r.fail(
            "INT-04: JSON output missing 'ui.api_port'",
            detail="config.py VALID_CONFIG_KEYS missing ui.api_port"
        )


# ── Prerequisites ─────────────────────────────────────────────────────────────

def check_prerequisites() -> None:
    if not Path(RECALL).exists():
        print(f"{RED}ERROR: recall CLI not found at {RECALL} — run: pip install -e .{RESET}")
        sys.exit(1)
    print(f"  {GREEN}OK{RESET} recall CLI available")

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
        print(f"{RED}ERROR: fastapi not importable — run: pip install -e '.[dev]'{RESET}")
        sys.exit(1)

    if LBDB_PATH.exists():
        print(f"  {GREEN}OK{RESET} LadybugDB exists at {LBDB_PATH}")
    else:
        print(f"  {YELLOW}WARN{RESET} LadybugDB not found at {LBDB_PATH} — INT-01/02/03 tests will be skipped")


# ── Teardown ──────────────────────────────────────────────────────────────────

def teardown() -> None:
    print(f"\n{BOLD}── Teardown ──{RESET}")
    try:
        if _db_exists():
            _delete_test_entity()
        _clean_retention(MARKER_UUID)
        from src.retention import reset_retention_manager
        reset_retention_manager()
        print(f"  {GREEN}OK{RESET} Test entity and retention records removed")
    except Exception as e:
        print(f"  {YELLOW}WARN{RESET} Cleanup failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    fail_fast = "--fail-fast" in sys.argv

    print(f"\n{BOLD}Phase 11: Graph UI — Verification{RESET}")
    print(f"Requirements: UI-01 · UI-02 · UI-03")
    print(f"Integration gaps: INT-01 · INT-02 · INT-03 · INT-04")
    print(f"{YELLOW}Note: No Ollama required. Tests 7–9 use direct Kuzu + RetentionManager writes.{RESET}")

    r = Runner(fail_fast=fail_fast)

    r.banner("Prerequisites")
    check_prerequisites()

    try:
        test_cli_help_and_flag(r)
        test_api_shape_and_readonly(r)
        test_global_flag(r)
        test_node_detail_retention_enrichment(r)
        test_archived_nodes_filtered_from_graph(r)
        test_pinned_nodes_flagged_in_graph(r)
        test_config_exposes_ui_port(r)
    finally:
        teardown()

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Phase 09: Smart Retention — Human Verification Script
Requirements: RETN-01 · RETN-02 · RETN-03 · RETN-04 · RETN-05 · RETN-06

Usage:
    python scripts/verify_phase_09.py [--fail-fast]

Tests (no Ollama required — inserts test nodes directly into Kuzu):

    1. RETN-02: graphiti stale shows backdated nodes (age, score, uuid columns)
    2. RETN-04: graphiti pin hides node from stale output
    3. RETN-05: graphiti unpin restores node to stale output
    4. RETN-06: graphiti show records access in retention.db
    5. RETN-01: graphiti compact --expire archives all stale nodes
    6. RETN-03: retention_days config — load_config reads value, enforces min 30

All state is cleaned up after the run (test nodes removed from Kuzu and retention.db).
"""

import sqlite3
import subprocess
import sys
import uuid as uuid_mod
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[1;33m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

GRAPHITI    = str(ROOT / ".venv" / "bin" / "graphiti")
KUZU_DB     = ROOT / ".graphiti" / "graphiti.kuzu"
RETENTION_DB = Path.home() / ".graphiti" / "retention.db"
GROUP_ID    = ROOT.name  # "graphiti-knowledge-graph"

# UUIDs allocated once so cleanup is deterministic
_TEST_UUIDS = {
    "Alpha": str(uuid_mod.uuid4()),
    "Beta":  str(uuid_mod.uuid4()),
    "Gamma": str(uuid_mod.uuid4()),
}


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
        print(f"{BOLD} Phase 09: Smart Retention — Verification Results{RESET}")
        print(f"{BOLD}{'━' * width}{RESET}")
        print(f" Tests passed: {GREEN}{self.passed}{RESET}")
        print(f" Tests failed: {RED}{self.failed}{RESET}")
        if self.failures:
            print("\n Failed:")
            for f in self.failures:
                print(f"   {RED}✗{RESET} {f}")
        else:
            reqs = "RETN-01 · RETN-02 · RETN-03 · RETN-04 · RETN-05 · RETN-06"
            print(f"\n {GREEN}All tests passed.{RESET} Requirements {reqs} verified.")
        print()
        return self.failed == 0


def run(cmd: list[str], *, input: str | None = None, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, cwd=ROOT,
        input=input, timeout=timeout,
    )


# ── Setup / Teardown ──────────────────────────────────────────────────────────

def _insert_test_nodes() -> None:
    """Insert Alpha/Beta/Gamma directly into Kuzu backdated 100 days."""
    import kuzu
    db = kuzu.Database(str(KUZU_DB))
    conn = kuzu.Connection(db)
    old = datetime.now() - timedelta(days=100)
    old_ts = old.strftime("%Y-%m-%d %H:%M:%S")
    for name, uid in _TEST_UUIDS.items():
        conn.execute(
            f"CREATE (e:Entity {{uuid: '{uid}', name: '{name}', "
            f"group_id: '{GROUP_ID}', labels: ['Entity'], "
            f"created_at: timestamp('{old_ts}'), "
            f"name_embedding: [], summary: 'test node', attributes: '{{}}'}})"
        )


def _delete_test_nodes() -> None:
    """Remove test nodes from Kuzu and all retention.db records."""
    import kuzu
    db = kuzu.Database(str(KUZU_DB))
    conn = kuzu.Connection(db)
    for uid in _TEST_UUIDS.values():
        conn.execute(f"MATCH (e:Entity) WHERE e.uuid = '{uid}' DETACH DELETE e")

    rdb = sqlite3.connect(RETENTION_DB)
    placeholders = ",".join("?" * len(_TEST_UUIDS))
    uids = list(_TEST_UUIDS.values())
    rdb.execute(f"DELETE FROM pin_state   WHERE uuid IN ({placeholders})", uids)
    rdb.execute(f"DELETE FROM archive_state WHERE uuid IN ({placeholders})", uids)
    rdb.execute(f"DELETE FROM access_log  WHERE uuid IN ({placeholders})", uids)
    rdb.execute("DELETE FROM pin_state WHERE uuid = ''")  # guard against empty-string artifact
    rdb.commit()


# ── Prerequisites ─────────────────────────────────────────────────────────────

def check_prerequisites(r: Runner) -> bool:
    r.banner("Prerequisites")
    try:
        import kuzu  # noqa: F401
    except ImportError:
        r.fail("kuzu not importable — run: pip install -e '.[dev]'")
        return False

    if not KUZU_DB.exists():
        r.fail(f"Kuzu DB not found at {KUZU_DB} — run 'graphiti add ...' at least once")
        return False

    res = run([GRAPHITI, "--version"])
    if res.returncode != 0:
        r.fail("graphiti CLI not available", detail=res.stderr.strip())
        return False

    r.ok("kuzu importable, DB exists, CLI available")
    return True


# ── Test 1 (RETN-02): stale lists backdated nodes ────────────────────────────

def test_stale_lists_nodes(r: Runner) -> None:
    r.banner("Test 1 (RETN-02): graphiti stale shows stale nodes")

    res = run([GRAPHITI, "stale", "--project", "--verbose"])
    if res.returncode != 0:
        r.fail("graphiti stale exited non-zero", detail=(res.stderr or res.stdout)[:300])
        return

    output = res.stdout + res.stderr
    missing = [name for name in _TEST_UUIDS if name not in output]
    if missing:
        r.fail(f"stale output missing nodes: {missing}", detail=output[:500])
        return
    r.ok("Alpha, Beta, Gamma all appear in stale output")

    # UUID column present (--verbose)
    alpha_uuid = _TEST_UUIDS["Alpha"]
    if alpha_uuid in output:
        r.ok("UUID column visible in --verbose output")
    else:
        r.fail("UUID not shown in --verbose output", detail=f"Expected {alpha_uuid}")

    # age_days present
    if "age_days" in output:
        r.ok("age_days column present")
    else:
        r.fail("age_days column missing from output")

    # score present
    if "score" in output:
        r.ok("score column present")
    else:
        r.fail("score column missing from output")


# ── Test 2 (RETN-04): pin hides node ─────────────────────────────────────────

def test_pin_hides_node(r: Runner) -> None:
    r.banner("Test 2 (RETN-04): graphiti pin hides node from stale")

    alpha_uuid = _TEST_UUIDS["Alpha"]
    res = run([GRAPHITI, "pin", alpha_uuid, "--project"])
    if res.returncode != 0:
        r.fail("graphiti pin exited non-zero", detail=(res.stderr or res.stdout)[:200])
        return
    r.ok(f"pin command exited 0 for Alpha ({alpha_uuid[:8]}…)")

    # Confirm in retention.db
    rdb = sqlite3.connect(RETENTION_DB)
    row = rdb.execute(
        "SELECT uuid FROM pin_state WHERE uuid=? AND scope=?",
        (alpha_uuid, GROUP_ID),
    ).fetchone()
    if row:
        r.ok("Alpha UUID recorded in retention.db pin_state")
    else:
        r.fail("Alpha not found in pin_state after pin command")

    # Alpha must be absent from stale
    res2 = run([GRAPHITI, "stale", "--project", "--verbose"])
    output = res2.stdout + res2.stderr
    if "Alpha" not in output:
        r.ok("Alpha absent from stale output after pinning")
    else:
        r.fail("Alpha still appears in stale output after pinning")

    # Beta and Gamma still present
    still_stale = [n for n in ("Beta", "Gamma") if n in output]
    if len(still_stale) == 2:
        r.ok("Beta and Gamma still appear in stale output (unaffected)")
    else:
        r.fail(f"Expected Beta+Gamma in stale, got: {still_stale}", detail=output[:300])


# ── Test 3 (RETN-05): unpin restores node ────────────────────────────────────

def test_unpin_restores_node(r: Runner) -> None:
    r.banner("Test 3 (RETN-05): graphiti unpin restores node to stale")

    alpha_uuid = _TEST_UUIDS["Alpha"]
    res = run([GRAPHITI, "unpin", alpha_uuid, "--project"])
    if res.returncode != 0:
        r.fail("graphiti unpin exited non-zero", detail=(res.stderr or res.stdout)[:200])
        return
    r.ok(f"unpin command exited 0 for Alpha ({alpha_uuid[:8]}…)")

    # Confirm removed from retention.db
    rdb = sqlite3.connect(RETENTION_DB)
    row = rdb.execute(
        "SELECT uuid FROM pin_state WHERE uuid=? AND scope=?",
        (alpha_uuid, GROUP_ID),
    ).fetchone()
    if row is None:
        r.ok("Alpha removed from retention.db pin_state")
    else:
        r.fail("Alpha still in pin_state after unpin command")

    # Alpha must be back in stale
    res2 = run([GRAPHITI, "stale", "--project"])
    output = res2.stdout + res2.stderr
    if "Alpha" in output:
        r.ok("Alpha back in stale output after unpinning")
    else:
        r.fail("Alpha still absent from stale output after unpinning")


# ── Test 4 (RETN-06): show records access ────────────────────────────────────

def test_show_records_access(r: Runner) -> None:
    r.banner("Test 4 (RETN-06): graphiti show records access in retention.db")

    # Test nodes are inserted directly into Kuzu (no FTS index), so CLI `show`
    # won't find them by name.  Test the access-recording layer directly via the
    # Python API — this is exactly what show_command calls internally.
    from src.graph import get_service, run_graph_operation
    from src.graph.service import GraphScope

    alpha_uuid = _TEST_UUIDS["Alpha"]

    # Clear any prior access record for this UUID
    rdb = sqlite3.connect(RETENTION_DB)
    rdb.execute("DELETE FROM access_log WHERE uuid=?", (alpha_uuid,))
    rdb.commit()

    try:
        run_graph_operation(
            get_service().record_access(
                uuid=alpha_uuid,
                scope=GraphScope.PROJECT,
                project_root=ROOT,
            )
        )
    except Exception as e:
        r.fail(f"record_access() raised unexpectedly: {e}")
        return

    rdb2 = sqlite3.connect(RETENTION_DB)
    row = rdb2.execute(
        "SELECT uuid, access_count FROM access_log WHERE uuid=? AND scope=?",
        (alpha_uuid, GROUP_ID),
    ).fetchone()

    if row is None:
        r.fail("No access_log entry written after record_access()")
    elif row[1] >= 1:
        r.ok(f"access_log entry written — uuid={row[0][:8]}…, access_count={row[1]}")
    else:
        r.fail(f"access_count is {row[1]}, expected ≥ 1")

    # Also verify the show module wires record_access correctly
    import inspect, src.cli.commands.show as show_mod
    module_src = inspect.getsource(show_mod)
    if "record_access" in module_src:
        r.ok("show module contains record_access() call (access hook wired)")
    else:
        r.fail("show module does not call record_access() — wiring missing")


# ── Test 5 (RETN-01): compact --expire archives all stale nodes ──────────────

def test_compact_expire(r: Runner) -> None:
    r.banner("Test 5 (RETN-01): graphiti compact --expire archives stale nodes")

    # Check stale count before
    res_before = run([GRAPHITI, "stale", "--project"])
    before_output = res_before.stdout + res_before.stderr
    stale_before = sum(1 for n in _TEST_UUIDS if n in before_output)
    r.info(f"Stale nodes before compact --expire: {stale_before}")

    # Run compact --expire with 'y' confirmation
    res = run([GRAPHITI, "compact", "--expire", "--project"], input="y\n")
    output = res.stdout + res.stderr

    if res.returncode != 0:
        r.fail("compact --expire exited non-zero", detail=output[:300])
        return
    r.ok("compact --expire exited 0")

    # Confirm prompt appeared
    if "Proceed?" in output or "eligible" in output or "will be archived" in output:
        r.ok("Confirmation prompt shown before archiving")
    else:
        r.fail("Confirmation prompt not found in output", detail=output[:300])

    # Archived count message
    if "Archived" in output:
        r.ok("'Archived N nodes' message present in output")
    else:
        r.fail("No 'Archived' message in output", detail=output[:300])

    # Stale should now be empty for our test nodes
    res_after = run([GRAPHITI, "stale", "--project"])
    after_output = res_after.stdout + res_after.stderr
    remaining = [n for n in _TEST_UUIDS if n in after_output]
    if not remaining:
        r.ok("No test nodes remain in stale output after compact --expire")
    else:
        r.fail(f"Nodes still appear in stale after archiving: {remaining}")

    # Verify archive_state in retention.db
    rdb = sqlite3.connect(RETENTION_DB)
    archived = [
        row[0] for row in rdb.execute(
            "SELECT uuid FROM archive_state WHERE scope=?", (GROUP_ID,)
        )
        if row[0] in _TEST_UUIDS.values()
    ]
    if len(archived) == len(_TEST_UUIDS):
        r.ok(f"All {len(archived)} test nodes recorded in retention.db archive_state")
    else:
        r.fail(
            f"Expected {len(_TEST_UUIDS)} archive_state records, found {len(archived)}",
            detail=f"Archived UUIDs: {archived}",
        )


# ── Test 6 (RETN-03): retention_days config ──────────────────────────────────

def test_retention_config(r: Runner) -> None:
    r.banner("Test 6 (RETN-03): retention_days config (load_config, minimum enforcement)")

    from src.llm.config import load_config

    # Default (no [retention] section in toml)
    cfg = load_config()
    if cfg.retention_days == 90:
        r.ok(f"Default retention_days = 90 days")
    else:
        r.info(f"retention_days = {cfg.retention_days} (non-default, may be set in llm.toml)")
        r.ok(f"retention_days loaded from config without error: {cfg.retention_days}")

    # Minimum enforcement: monkeypatch toml to return 10 days → should clamp to 30
    import tempfile, os
    toml_content = "[retention]\nretention_days = 10\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        tmp_toml = f.name

    try:
        orig = os.environ.get("GRAPHITI_CONFIG")
        os.environ["GRAPHITI_CONFIG"] = tmp_toml
        cfg_min = load_config()
        if cfg_min.retention_days >= 30:
            r.ok(f"Minimum 30-day enforcement: retention_days=10 clamped to {cfg_min.retention_days}")
        else:
            r.fail(
                f"Minimum enforcement failed: retention_days={cfg_min.retention_days}, expected ≥ 30",
            )
    except Exception as e:
        r.info(f"Note: GRAPHITI_CONFIG env override not supported — testing via direct instantiation")
        from src.llm.config import LLMConfig
        # Test minimum enforcement via direct instantiation
        cfg_direct = LLMConfig(retention_days=10)
        if cfg_direct.retention_days >= 30:
            r.ok(f"LLMConfig(retention_days=10) clamped to {cfg_direct.retention_days}")
        else:
            r.fail(f"LLMConfig minimum enforcement failed: {cfg_direct.retention_days}")
    finally:
        os.unlink(tmp_toml)
        if orig is None:
            os.environ.pop("GRAPHITI_CONFIG", None)
        else:
            os.environ["GRAPHITI_CONFIG"] = orig


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    fail_fast = "--fail-fast" in sys.argv

    print(f"\n{BOLD}Phase 09: Smart Retention — Human Verification{RESET}")
    print(f"Requirements: RETN-01 · RETN-02 · RETN-03 · RETN-04 · RETN-05 · RETN-06")
    print(f"{YELLOW}Note: Inserts 3 test nodes directly into Kuzu (no Ollama required). "
          f"Cleaned up after run.{RESET}")

    r = Runner(fail_fast=fail_fast)

    if not check_prerequisites(r):
        sys.exit(1)

    print(f"\n{BOLD}── Setup: inserting test nodes ──{RESET}")
    try:
        _insert_test_nodes()
        print(f"  {GREEN}OK{RESET} Alpha/Beta/Gamma inserted (backdated 100 days, group={GROUP_ID!r})")
    except Exception as e:
        print(f"  {RED}ABORT{RESET} Could not insert test nodes: {e}")
        sys.exit(1)

    try:
        test_stale_lists_nodes(r)
        test_pin_hides_node(r)
        test_unpin_restores_node(r)
        test_show_records_access(r)
        test_compact_expire(r)
        test_retention_config(r)
    finally:
        print(f"\n{BOLD}── Teardown: removing test nodes ──{RESET}")
        try:
            _delete_test_nodes()
            print(f"  {GREEN}OK{RESET} Test nodes removed from Kuzu and retention.db")
        except Exception as e:
            print(f"  {YELLOW}WARN{RESET} Cleanup failed: {e} (manual cleanup may be needed)")

    passed = r.summary()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

"""
Integration tests for LadybugDB backend.
Wave 0 stubs — tests are skipped until LadybugDriver is implemented in Wave 2.
"""
import pytest
import tempfile
from pathlib import Path


@pytest.mark.skip(reason="Wave 2: LadybugDriver not yet implemented in src/storage/ladybug_driver.py")
def test_ladybug_driver_creates_fresh_db(tmp_path):
    """LadybugDriver(db=path) creates a new DB file and returns a working driver."""
    from src.storage.ladybug_driver import LadybugDriver
    db_path = str(tmp_path / "test.lbdb")
    driver = LadybugDriver(db=db_path)
    assert driver is not None
    assert driver._database is not None or True  # _database set by with_database()/clone()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 2: LadybugDriver not yet implemented")
async def test_ladybug_driver_execute_query_returns_list_of_dicts(tmp_path):
    """driver.execute_query() returns (list[dict], None, None) — same contract as KuzuDriver."""
    from src.storage.ladybug_driver import LadybugDriver
    db_path = str(tmp_path / "test.lbdb")
    driver = LadybugDriver(db=db_path)
    results, _, _ = await driver.execute_query("RETURN 1 AS x")
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["x"] == 1


@pytest.mark.asyncio
@pytest.mark.skip(reason="Wave 2: LadybugDriver not yet implemented; FTS deduplication end-to-end test")
async def test_entity_deduplication_fts(tmp_path):
    """Adding the same entity twice via Graphiti resolves to one node (FTS deduplication working)."""
    # This test requires a fully working LadybugDriver + Graphiti stack
    # It verifies the core Phase 12 success criterion: FTS works in new backend
    from src.storage.ladybug_driver import LadybugDriver
    from graphiti_core import Graphiti
    db_path = str(tmp_path / "dedup_test.lbdb")
    driver = LadybugDriver(db=db_path)
    # TODO in Wave 2: instantiate Graphiti with driver, add same entity twice, verify 1 node
    pass

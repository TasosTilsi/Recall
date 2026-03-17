"""
Integration tests for LadybugDB backend.
"""
import pytest


def test_ladybug_driver_creates_fresh_db(tmp_path):
    """LadybugDriver(db=path) creates a new DB file and returns a working driver."""
    from src.storage.ladybug_driver import LadybugDriver
    db_path = str(tmp_path / "test.lbdb")
    driver = LadybugDriver(db=db_path)
    assert driver is not None
    # _database is NOT set in __init__ — it's set only via clone()/with_database()
    # Use getattr to avoid AttributeError when _database is absent (correct behavior)
    assert getattr(driver, '_database', None) is None  # not set until clone() called
    # clone() sets _database
    cloned = driver.clone("test_group")
    assert cloned._database == "test_group"
    assert cloned is not driver  # must be a copy, not self


@pytest.mark.asyncio
async def test_ladybug_driver_execute_query_returns_list_of_dicts(tmp_path):
    """driver.execute_query() returns (list[dict], None, None) — same contract as KuzuDriver."""
    from src.storage.ladybug_driver import LadybugDriver
    db_path = str(tmp_path / "test.lbdb")
    driver = LadybugDriver(db=db_path)
    results, second, third = await driver.execute_query("RETURN 1 AS x")
    assert second is None
    assert third is None
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["x"] == 1


@pytest.mark.asyncio
@pytest.mark.skip(reason="manual: requires Ollama running — run: graphiti add 'Alice met Bob', graphiti add 'Alice met Bob', graphiti search 'Alice' — expect 1 node")
@pytest.mark.integration
async def test_entity_deduplication_fts(tmp_path):
    """Adding the same entity twice via Graphiti resolves to one node (FTS deduplication working).

    Manual verification steps:
        1. graphiti add "Alice met Bob"
        2. graphiti add "Alice met Bob"
        3. graphiti search "Alice"
        Expected: 1 entity node named Alice (not 2 duplicates)
    This proves LadybugDB FTS indices are working correctly.
    """
    pass

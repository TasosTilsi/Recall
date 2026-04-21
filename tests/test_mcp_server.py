"""Smoke tests for src/mcp_server/ — no live DB required."""
import importlib
import inspect
import io
import sys
import unittest.mock


def test_server_import_does_not_write_stdout():
    """Importing server.py must produce zero bytes on stdout."""
    buf = io.StringIO()
    with unittest.mock.patch("sys.stdout", buf):
        import src.mcp_server.server  # noqa: F401 — side effect is what we test
    assert buf.getvalue() == "", f"stdout contaminated: {buf.getvalue()!r}"


def test_six_tools_registered():
    """FastMCP instance must have exactly the six required tools."""
    from src.mcp_server.server import mcp
    registered = {t.name for t in mcp._tool_manager.list_tools()}
    expected = {
        "search_knowledge",
        "get_entity",
        "get_backlinks",
        "get_decisions",
        "get_bugs",
        "get_patterns",
    }
    assert registered == expected, f"Tool mismatch — got: {registered}"


def test_tool_signatures():
    """Each tool must accept the documented parameters."""
    from src.mcp_server import tools

    sig_search = inspect.signature(tools.search_knowledge)
    assert "query" in sig_search.parameters
    assert "limit" in sig_search.parameters

    # get_entity: UUID-or-name lookup — single entity_id parameter
    sig_entity = inspect.signature(tools.get_entity)
    assert "entity_id" in sig_entity.parameters

    # get_backlinks: must accept hops for multi-hop traversal (default=1)
    sig_backlinks = inspect.signature(tools.get_backlinks)
    assert "entity_id" in sig_backlinks.parameters
    assert "hops" in sig_backlinks.parameters, "get_backlinks must have hops parameter"
    assert sig_backlinks.parameters["hops"].default == 1, "hops default must be 1"

    for fn_name in ("get_decisions", "get_bugs", "get_patterns"):
        fn = getattr(tools, fn_name)
        sig = inspect.signature(fn)
        assert "limit" in sig.parameters, f"{fn_name} missing limit param"

"""FastMCP stdio server — read-only engineering knowledge graph access.

Start with: recall mcp serve

Transport: stdio only (Claude Code manages the lifecycle).
IMPORTANT: logging.basicConfig(stream=sys.stderr) is set before all imports.
Never write to stdout — corrupts the MCP protocol.
"""
import logging
import sys

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

from mcp.server.fastmcp import FastMCP

from src.mcp_server.tools import (
    search_knowledge,
    get_entity,
    get_backlinks,
    get_decisions,
    get_bugs,
    get_patterns,
)

mcp = FastMCP(
    "recall",
    instructions=(
        "recall is an engineering knowledge graph built from this repository's git history. "
        "Use search_knowledge for keyword search, get_decisions/get_bugs/get_patterns to "
        "browse by category, get_entity to fetch details by UUID or name, and get_backlinks "
        "to explore relationships (use hops>1 for multi-hop traversal). All responses are JSON."
    ),
)

mcp.tool()(search_knowledge)
mcp.tool()(get_entity)
mcp.tool()(get_backlinks)
mcp.tool()(get_decisions)
mcp.tool()(get_bugs)
mcp.tool()(get_patterns)


def serve() -> None:
    """Entry point called by `recall mcp serve` CLI command."""
    mcp.run(transport="stdio")

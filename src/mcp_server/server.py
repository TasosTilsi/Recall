"""FastMCP server for graphiti knowledge graph.

Entry point: `graphiti mcp serve` (via CLI command group in src/cli/commands/mcp.py)

Transports:
  stdio          — default, Claude Code manages lifecycle
  streamable-http — standalone server on localhost:8000

All tool responses use TOON format for arrays, JSON/plain text for scalars.
Context resource returns TOON-encoded decisions + architecture context.

IMPORTANT: All output goes to stderr only. The MCP stdio transport uses stdout
for JSON-RPC messages — any stdout write (including print()) corrupts the
protocol. logging.basicConfig(stream=sys.stderr) is set before any imports
that might log.
"""
import logging
import sys

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

from mcp.server.fastmcp import FastMCP

from src.mcp_server.tools import (
    recall_note,
    recall_search,
    recall_list,
    recall_show,
    recall_delete,
    recall_summarize,
    recall_compact,
    recall_index,
    recall_health,
    recall_config,
)
from src.mcp_server.context import get_context

# Create the FastMCP server with instructions for Claude
mcp = FastMCP(
    "recall",
    instructions=(
        "recall is this user's personal knowledge graph for coding projects. "
        "Tool responses use TOON format (a compact wire encoding) — always present "
        "results as natural human-readable prose, never show TOON to the user. "
        "Use --limit flags to self-manage token budgets. "
        "Capture important decisions with recall_note after architecture discussions."
    )
)

# Register all 10 CLI tools with recall_ prefix
mcp.tool()(recall_note)
mcp.tool()(recall_search)
mcp.tool()(recall_list)
mcp.tool()(recall_show)
mcp.tool()(recall_delete)
mcp.tool()(recall_summarize)
mcp.tool()(recall_compact)
mcp.tool()(recall_index)
mcp.tool()(recall_health)
mcp.tool()(recall_config)

# Register context resource for session-start injection
mcp.resource("graphiti://context")(get_context)


def main(transport: str = "stdio", port: int = 8000) -> None:
    """Start the MCP server with the specified transport.

    Args:
        transport: "stdio" (default) or "streamable-http"
        port: HTTP port for streamable-http transport (default 8000)
    """
    if transport == "streamable-http":
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

"""MCP server CLI command group.

Usage: recall mcp serve
"""
import typer

app = typer.Typer(help="MCP server commands.")


@app.command()
def serve() -> None:
    """Start the stdio MCP server for Claude integration."""
    from src.mcp_server import serve as _serve
    _serve()

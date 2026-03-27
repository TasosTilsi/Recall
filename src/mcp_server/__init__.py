"""MCP server for recall knowledge graph.

Exposes all CLI commands as MCP tools (recall_ prefix) and provides a
recall://context resource for session-start context injection.

Modules:
    server.py   — FastMCP app, tool registrations, resource, transport entry point
    tools.py    — Subprocess-based tool handler functions (CLI wrappers)
    context.py  — recall://context resource (stale detection, query, TOON encode)
    install.py  — recall mcp install command (writes ~/.claude.json)
    toon_utils.py — TOON encoding utilities with array-size guard and token budget
"""

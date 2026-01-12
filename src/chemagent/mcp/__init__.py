"""
ChemAgent MCP (Model Context Protocol) Server.

This module provides an OPTIONAL MCP interface to ChemAgent.
It wraps the existing ChemAgent functionality for use with
MCP-compatible clients like Claude Desktop and VS Code.

This is a PARALLEL interface - it does NOT replace or modify:
- REST API (api/server.py)
- CLI (cli.py)
- Direct Python usage (from chemagent import ChemAgent)

Usage:
    # Run as MCP server (for Claude Desktop integration)
    python -m chemagent.mcp

    # Or use the entry point
    chemagent-mcp

Configuration for Claude Desktop (~/.config/claude/claude_desktop_config.json):
    {
        "mcpServers": {
            "chemagent": {
                "command": "python",
                "args": ["-m", "chemagent.mcp"]
            }
        }
    }
"""

# Check if MCP is available
try:
    import mcp
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

# Conditional imports
if MCP_AVAILABLE:
    from chemagent.mcp.server import (
        create_mcp_server,
        run_mcp_server,
    )
else:
    create_mcp_server = None
    run_mcp_server = None

__all__ = [
    "MCP_AVAILABLE",
    "create_mcp_server",
    "run_mcp_server",
]

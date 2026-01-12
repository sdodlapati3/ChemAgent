"""
Entry point for running ChemAgent as an MCP server.

Usage:
    python -m chemagent.mcp

This starts the MCP server using stdio transport,
allowing Claude Desktop and other MCP clients to connect.
"""

from chemagent.mcp.server import main

if __name__ == "__main__":
    main()

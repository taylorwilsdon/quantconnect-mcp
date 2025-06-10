#!/usr/bin/env python3
"""QuantConnect MCP Server Entry Point"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.server import mcp
from src.tools import (
    register_quantbook_tools,
    register_data_tools,
    register_analysis_tools,
    register_portfolio_tools,
    register_universe_tools
)
from src.resources import register_system_resources

def main():
    """Initialize and run the QuantConnect MCP server."""
    
    # Register all tool modules
    print("🔧 Registering QuantConnect tools...")
    register_quantbook_tools(mcp)
    register_data_tools(mcp)
    register_analysis_tools(mcp)
    register_portfolio_tools(mcp)
    register_universe_tools(mcp)
    
    # Register resources
    print("📊 Registering system resources...")
    register_system_resources(mcp)
    
    print(f"✅ QuantConnect MCP Server initialized")
    
    # Determine transport method
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    
    if transport == "streamable-http":
        print(f"🌐 Starting HTTP server on {mcp.host}:{mcp.port}")
        mcp.run(
            transport="streamable-http",
            host=os.getenv("MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("MCP_PORT", "8000")),
            path=os.getenv("MCP_PATH", "/mcp")
        )
    elif transport == "stdio":
        print("📡 Starting STDIO transport")
        mcp.run()  # Default stdio transport
    else:
        print(f"🚀 Starting with {transport} transport")
        mcp.run(transport=transport)

if __name__ == "__main__":
    main()
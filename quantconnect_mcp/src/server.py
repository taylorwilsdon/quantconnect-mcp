"""QuantConnect MCP Server Core Configuration"""

import os
from typing import Optional
from fastmcp import FastMCP

from .tools import (
    register_auth_tools,
    register_project_tools,
    register_file_tools,
    register_backtest_tools,
    register_live_tools,
)
from .auth import configure_auth
from .utils import safe_print


mcp: FastMCP = FastMCP(
    name="QuantConnect MCP Server",
    instructions="""
    This server provides comprehensive QuantConnect API functionality for:
    - Project and backtest management
    - File management within projects
    - Authentication and API access
    - Compilation and execution of code and jupyter notebooks

    You must never use emojis. They will `contains invalid characters` exceptions.

    When writing QuantConnect code, refer to the QuantConnect documentation and platform resources for:
    - Proper import patterns and modules available on the platform
    - Algorithm class structures and inheritance requirements
    - Available data types, resolutions, and market data APIs
    - Portfolio management and trading methods
    - Research environment capabilities and libraries

    Use the available tools to interact with QuantConnect's cloud platform.
    """,
    on_duplicate_tools="error",
    dependencies=[
        "pandas",
        "numpy",
        "scipy",
        "scikit-learn",
        "matplotlib",
        "seaborn",
        "arch",
        "statsmodels",
        "httpx",
    ],
)

def main():
    """Initialize and run the QuantConnect MCP server."""

    # Auto-configure authentication from environment variables if available
    user_id = os.getenv("QUANTCONNECT_USER_ID")
    api_token = os.getenv("QUANTCONNECT_API_TOKEN")
    organization_id = os.getenv("QUANTCONNECT_ORGANIZATION_ID")

    if user_id and api_token:
        try:
            safe_print("🔐 Configuring QuantConnect authentication from environment...")
            configure_auth(user_id, api_token, organization_id)
            safe_print("✅ Authentication configured successfully")
        except Exception as e:
            safe_print(f"⚠️  Failed to configure authentication: {e}")
            safe_print(
                "💡 You can configure authentication later using the configure_quantconnect_auth tool"
            )

    # Register all tool modules
    safe_print("🔧 Registering QuantConnect tools...")
    register_auth_tools(mcp)
    register_project_tools(mcp)
    register_file_tools(mcp)
    register_backtest_tools(mcp)
    register_live_tools(mcp)


    safe_print(f"✅ QuantConnect MCP Server initialized")

    # Determine transport method
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8000"))
        safe_print(f"🌐 Starting HTTP server on {host}:{port}")
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            path=os.getenv("MCP_PATH", "/mcp"),
        )
    elif transport == "stdio":
        safe_print("📡 Starting STDIO transport")
        mcp.run()  # Default stdio transport
    else:
        safe_print(f"🚀 Starting with {transport} transport")
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""QuantConnect MCP Server Entry Point"""

import os
import sys
from pathlib import Path

# Ensure package root is in Python path for consistent imports
package_root = Path(__file__).parent.parent
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from quantconnect_mcp.src.server import mcp
from quantconnect_mcp.src.tools import (
    register_quantbook_tools,
    register_data_tools,
    register_analysis_tools,
    register_portfolio_tools,
    register_universe_tools,
    register_auth_tools,
    register_project_tools,
    register_file_tools,
    register_backtest_tools,
)
from quantconnect_mcp.src.resources import register_system_resources
from quantconnect_mcp.src.auth import configure_auth
from quantconnect_mcp.src.utils import safe_print


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
    register_quantbook_tools(mcp)
    register_data_tools(mcp)
    register_analysis_tools(mcp)
    register_portfolio_tools(mcp)
    register_universe_tools(mcp)

    # Register resources
    safe_print("📊 Registering system resources...")
    register_system_resources(mcp)

    safe_print(f"✅ QuantConnect MCP Server initialized")

    # Determine transport method
    transport = os.getenv("MCP_TRANSPORT", "stdio")

    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", os.getenv("PORT", "8000")))
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

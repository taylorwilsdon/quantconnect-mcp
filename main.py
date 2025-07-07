#!/usr/bin/env python3
"""QuantConnect MCP Server Entry Point with Enhanced Setup Process"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.server import mcp
from src.auth import configure_auth


def main():
    """Initialize and run the QuantConnect MCP server with enhanced setup process."""
    
    print("🚀 QuantConnect MCP Server Starting...", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Auto-configure authentication from environment variables if available
    user_id = os.getenv("QUANTCONNECT_USER_ID")
    api_token = os.getenv("QUANTCONNECT_API_TOKEN")
    organization_id = os.getenv("QUANTCONNECT_ORGANIZATION_ID")

    if user_id and api_token:
        try:
            print("🔐 Configuring QuantConnect authentication from environment...", file=sys.stderr)
            configure_auth(user_id, api_token, organization_id)
            print("✅ Authentication configured successfully", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Failed to configure authentication: {e}", file=sys.stderr)
            print("💡 You can configure authentication later using the configure_quantconnect_auth tool", file=sys.stderr)
    else:
        print("💡 No environment credentials found. You can configure authentication later.", file=sys.stderr)
        print("   Set QUANTCONNECT_USER_ID and QUANTCONNECT_API_TOKEN environment variables", file=sys.stderr)
        print("   or use the configure_quantconnect_auth tool", file=sys.stderr)

    # Show tool registration process
    print("\n🔧 Registering QuantConnect tools...", file=sys.stderr)
    print("   📊 Authentication tools", file=sys.stderr)
    print("   🗂️  Project management tools", file=sys.stderr)
    print("   📄 File management tools", file=sys.stderr)
    print("   🔥 Backtest tools", file=sys.stderr)
    print("   🧪 QuantBook research tools", file=sys.stderr)
    print("   📈 Data retrieval tools", file=sys.stderr)
    print("   🔬 Statistical analysis tools", file=sys.stderr)
    print("   💰 Portfolio optimization tools", file=sys.stderr)
    print("   🌐 Universe selection tools", file=sys.stderr)

    print("\n📊 Registering system resources...", file=sys.stderr)
    print("   💻 System monitoring", file=sys.stderr)
    print("   🖥️  Server status", file=sys.stderr)
    print("   🛠️  Performance metrics", file=sys.stderr)

    print(f"\n✅ QuantConnect MCP Server initialized successfully!", file=sys.stderr)
    print(f"🎯 {len(mcp._tool_manager._tools)} tools available", file=sys.stderr)
    print(f"📊 {len(mcp._resource_manager._resources)} resources available", file=sys.stderr)

    # Determine transport method
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    
    print(f"\n🌐 Transport: {transport}", file=sys.stderr)
    
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8000"))
        path = os.getenv("MCP_PATH", "/mcp")
        print(f"🌍 Starting HTTP server on {host}:{port}{path}", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            path=path,
        )
    elif transport == "stdio":
        print("📡 Starting STDIO transport", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        mcp.run()  # Default stdio transport
    else:
        print(f"🚀 Starting with {transport} transport", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        mcp.run(transport=transport)


if __name__ == "__main__":
    main()
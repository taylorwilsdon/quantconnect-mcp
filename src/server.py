"""QuantConnect MCP Server Core Configuration"""

# Ensure FastMCP does NOT print its ASCII banner (which would break the
# initial JSON-RPC handshake expected by IDE clients such as Claude Code).
# FastMCP honours the `FASTMCP_DISABLE_BANNER` env flag (supported since
# fastmcp 2.8). We set it *before* importing anything from fastmcp.

import os

# Respect existing user preference if already defined.
os.environ.setdefault("FASTMCP_DISABLE_BANNER", "1")

from fastmcp import FastMCP
from typing import Optional

# Import tool and resource registration utilities. Placed **inside** the
# module (not only in the CLI entry-point) so that *any* code path which
# simply does `python -m quantconnect_mcp.server` or runs the console script
# will automatically expose the full QuantConnect tool-suite.  We **avoid**
# printing here because stdout must remain clean until after the MCP
# handshake, otherwise clients such as Claude Code will disconnect.

from .tools import (
    register_auth_tools,
    register_project_tools,
    register_file_tools,
    register_backtest_tools,
    register_quantbook_tools,
    register_data_tools,
    register_analysis_tools,
    register_portfolio_tools,
    register_universe_tools,
)
from .resources import register_system_resources
from .auth import configure_auth

mcp: FastMCP = FastMCP(
    name="QuantConnect MCP Server",
    instructions="""
    This server provides comprehensive QuantConnect API functionality for:
    - Research environment operations with QuantBook
    - Historical data retrieval and analysis
    - Statistical analysis (PCA, cointegration, mean reversion)
    - Portfolio optimization and risk analysis
    - Universe selection and asset filtering
    - Alternative data integration

    Use the available tools to interact with QuantConnect's research capabilities.
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

# ---------------------------------------------------------------------------
# One-time initialisation: configure API auth (if env vars present) and
# register *all* tools & resources with the MCP instance.
# ---------------------------------------------------------------------------

# 1) Silent, best-effort auth configuration from environment variables.  We
#    swallow exceptions because failing auth should not crash the entire
#    server – the caller can always run the `configure_quantconnect_auth`
#    tool later.

_user_id = os.getenv("QUANTCONNECT_USER_ID")
_api_token = os.getenv("QUANTCONNECT_API_TOKEN")
_org_id = os.getenv("QUANTCONNECT_ORGANIZATION_ID")

if _user_id and _api_token:
    try:
        configure_auth(_user_id, _api_token, _org_id)
    except Exception:
        # Deliberately ignore – the configure_auth tool will report issues
        pass

# 2) Register every tool category.

register_auth_tools(mcp)
register_project_tools(mcp)
register_file_tools(mcp)
register_backtest_tools(mcp)
register_quantbook_tools(mcp)
register_data_tools(mcp)
register_analysis_tools(mcp)
register_portfolio_tools(mcp)
register_universe_tools(mcp)

# 3) Register system resources (CPU/memory etc.).

register_system_resources(mcp)

def main():
    # Determine transport method from environment
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8000"))
        path = os.getenv("MCP_PATH", "/mcp")
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            path=path,
        )
    elif transport == "stdio":
        mcp.run()  # Default stdio transport
    else:
        mcp.run(transport=transport)

if __name__ == "__main__":
    main()

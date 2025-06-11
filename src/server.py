"""QuantConnect MCP Server Core Configuration"""

from fastmcp import FastMCP
import os
from typing import Optional

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
    port=int(os.getenv("MCP_PORT", "8000")),
    host=os.getenv("MCP_HOST", "127.0.0.1"),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
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

if __name__ == "__main__":
    mcp.run()

"""QuantConnect MCP Server Core Configuration"""

import os
from typing import Optional
from fastmcp import FastMCP

from .tools import (
    register_analysis_tools,
    register_portfolio_tools,
    register_universe_tools,
    register_auth_tools,
    register_project_tools,
    register_file_tools,
    register_backtest_tools,
)
from .resources import register_system_resources
from .auth import configure_auth
from .utils import safe_print


mcp: FastMCP = FastMCP(
    name="QuantConnect MCP Server",
    instructions="""
    This server provides QuantConnect API functionality for:
    - Project and backtest management
    - Statistical analysis (PCA, cointegration, mean reversion)
    - Portfolio optimization and risk analysis
    - Universe selection and asset filtering
    - Alternative data integration
    - File management and organization
    
    Optional QuantBook functionality (requires ENABLE_QUANTBOOK=true):
    - Research environment operations with QuantBook in Docker containers
    - Historical data retrieval and analysis
    - Interactive Jupyter-like code execution

    Use the available tools to interact with QuantConnect's capabilities.
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

# Server configuration is now handled in main.py

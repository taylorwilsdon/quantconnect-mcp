"""QuantConnect MCP Tools Package"""

# Core tools (always available)
from .analysis_tools import register_analysis_tools
from .portfolio_tools import register_portfolio_tools
from .universe_tools import register_universe_tools
from .auth_tools import register_auth_tools
from .project_tools import register_project_tools
from .file_tools import register_file_tools
from .backtest_tools import register_backtest_tools

# QuantBook tools are imported conditionally in main.py to avoid Docker dependency
# from .quantbook_tools import register_quantbook_tools
# from .data_tools import register_data_tools

__all__ = [
    "register_analysis_tools",
    "register_portfolio_tools",
    "register_universe_tools",
    "register_auth_tools",
    "register_project_tools",
    "register_file_tools",
    "register_backtest_tools",
    # QuantBook tools excluded from __all__ - imported conditionally
    # "register_quantbook_tools",
    # "register_data_tools",
]

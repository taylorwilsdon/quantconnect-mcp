"""Every tool the server exposes, grouped by QuantConnect API area."""

from quantconnect_mcp.tools import (
    account,
    ai,
    backtests,
    compile,
    files,
    live,
    object_store,
    optimizations,
    projects,
)

ALL_TOOLS = (
    *account.TOOLS,
    *projects.TOOLS,
    *files.TOOLS,
    *compile.TOOLS,
    *backtests.TOOLS,
    *optimizations.TOOLS,
    *live.TOOLS,
    *object_store.TOOLS,
    *ai.TOOLS,
)

__all__ = ["ALL_TOOLS"]

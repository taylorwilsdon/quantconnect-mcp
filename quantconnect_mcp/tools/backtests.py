"""Backtest tools."""

from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.tools._shared import (
    CLIENT,
    DESTRUCTIVE,
    MUTATING,
    READ_ONLY,
    Index,
    check_range,
)

# The spec requires end - start < 100 for orders and insights.
PAGE_LIMIT = 99


@tool(annotations=MUTATING)
async def create_backtest(
    project_id: int,
    compile_id: str,
    backtest_name: str,
    parameters: dict[str, str | float] | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Start a backtest from a successful compile.

    Args:
        project_id: The project to backtest.
        compile_id: A compile ID whose state is BuildSuccess.
        backtest_name: A name for the backtest.
        parameters: Algorithm parameter overrides, for example {"ema_fast": 10}.
    """
    return await qc.post(
        "backtests/create",
        projectId=project_id,
        compileId=compile_id,
        backtestName=backtest_name,
        parameters=parameters,
    )


@tool(annotations=READ_ONLY)
async def read_backtest(
    project_id: int, backtest_id: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Read a backtest's progress, statistics, and runtime results.

    Args:
        project_id: The project that owns the backtest.
        backtest_id: The backtest to read.
    """
    return await qc.post("backtests/read", projectId=project_id, backtestId=backtest_id)


@tool(annotations=READ_ONLY)
async def list_backtests(
    project_id: int, include_statistics: bool = False, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """List a project's backtests.

    Args:
        project_id: The project to inspect.
        include_statistics: Include each backtest's summary statistics.
    """
    return await qc.post(
        "backtests/list", projectId=project_id, includeStatistics=include_statistics
    )


@tool(annotations=READ_ONLY)
async def read_backtest_chart(
    project_id: int,
    backtest_id: str,
    name: str,
    start: Index,
    end: Index,
    count: int = 100,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Read one chart from a backtest, sampled to a number of points.

    If the response has status "loading", the chart is still being generated: call again.

    Args:
        project_id: The project that owns the backtest.
        backtest_id: The backtest to read.
        name: Chart name, for example "Strategy Equity".
        start: Start of the window, as a Unix timestamp in seconds.
        end: End of the window, as a Unix timestamp in seconds.
        count: Number of data points to return.
    """
    check_range(start, end)
    return await qc.post(
        "backtests/chart/read",
        projectId=project_id,
        backtestId=backtest_id,
        name=name,
        start=start,
        end=end,
        count=count,
    )


@tool(annotations=READ_ONLY)
async def read_backtest_orders(
    project_id: int,
    backtest_id: str,
    start: Index = 0,
    end: Index = PAGE_LIMIT,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Read a page of a backtest's orders, at most 99 per call.

    If the response has status "loading", the orders are still being generated: call again.

    Args:
        project_id: The project that owns the backtest.
        backtest_id: The backtest to read.
        start: Index of the first order (inclusive).
        end: Index after the last order (exclusive).
    """
    check_range(start, end, PAGE_LIMIT)
    return await qc.post(
        "backtests/orders/read",
        projectId=project_id,
        backtestId=backtest_id,
        start=start,
        end=end,
    )


@tool(annotations=READ_ONLY)
async def read_backtest_insights(
    project_id: int,
    backtest_id: str,
    start: Index = 0,
    end: Index = PAGE_LIMIT,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Read a page of the alpha insights a backtest emitted, at most 99 per call.

    Args:
        project_id: The project that owns the backtest.
        backtest_id: The backtest to read.
        start: Index of the first insight (inclusive).
        end: Index after the last insight (exclusive).
    """
    check_range(start, end, PAGE_LIMIT)
    return await qc.post(
        "backtests/read/insights",
        projectId=project_id,
        backtestId=backtest_id,
        start=start,
        end=end,
    )


@tool(annotations=READ_ONLY)
async def read_backtest_report(
    project_id: int, backtest_id: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Read the full HTML performance report for a completed backtest.

    If the response says the report is still generating, call again shortly.

    Args:
        project_id: The project that owns the backtest.
        backtest_id: The backtest to report on.
    """
    return await qc.post("backtests/read/report", projectId=project_id, backtestId=backtest_id)


@tool(annotations=MUTATING)
async def update_backtest(
    project_id: int,
    backtest_id: str,
    name: str | None = None,
    note: str | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Rename a backtest or attach a note to it.

    Args:
        project_id: The project that owns the backtest.
        backtest_id: The backtest to update.
        name: New backtest name.
        note: Note to attach to the backtest.
    """
    if name is None and note is None:
        raise ToolError("Provide a new name, a note, or both")
    return await qc.post(
        "backtests/update",
        projectId=project_id,
        backtestId=backtest_id,
        name=name,
        note=note,
    )


@tool(annotations=DESTRUCTIVE)
async def delete_backtest(
    project_id: int, backtest_id: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Permanently delete a backtest.

    Args:
        project_id: The project that owns the backtest.
        backtest_id: The backtest to delete.
    """
    return await qc.post("backtests/delete", projectId=project_id, backtestId=backtest_id)


TOOLS = (
    create_backtest,
    read_backtest,
    list_backtests,
    read_backtest_chart,
    read_backtest_orders,
    read_backtest_insights,
    read_backtest_report,
    update_backtest,
    delete_backtest,
)

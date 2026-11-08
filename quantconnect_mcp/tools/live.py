"""Live trading tools."""

from typing import Any, Literal

from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.tools._shared import (
    CLIENT,
    DESTRUCTIVE,
    READ_ONLY,
    Index,
    check_range,
)

# Spec bounds on end - start: < 100 for insights, <= 1,000 for orders, <= 250 for logs.
PAGE_LIMIT = 99
ORDERS_PAGE_LIMIT = 1000
LOG_PAGE_LIMIT = 250

LiveStatus = Literal["Running", "Stopped", "RuntimeError", "Liquidated"]


@tool(annotations=DESTRUCTIVE)
async def create_live_algorithm(
    project_id: int,
    compile_id: str,
    node_id: str,
    brokerage: dict[str, Any],
    data_providers: dict[str, dict[str, Any]] | None = None,
    version_id: int = -1,
    parameters: dict[str, str | float] | None = None,
    notification: dict[str, Any] | None = None,
    automatic_redeploy: bool | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Deploy a compiled project to live trading. This can place real orders.

    Args:
        project_id: The project to deploy.
        compile_id: A compile ID whose state is BuildSuccess.
        node_id: The live node to run on (see read_project_nodes).
        brokerage: Brokerage settings. Must include "id", for example
            {"id": "QuantConnectBrokerage"} for paper trading, plus any
            brokerage-specific credentials.
        data_providers: Data provider settings keyed by provider ID, in order of
            precedence. Defaults to the brokerage's own data feed.
        version_id: LEAN version to run. -1 uses the latest release.
        parameters: Algorithm parameter overrides.
        notification: Notification settings: {"events": [...], "targets": [...]}.
        automatic_redeploy: Redeploy automatically if the algorithm stops unexpectedly.
    """
    brokerage_id = brokerage.get("id")
    if not brokerage_id:
        raise ToolError('brokerage must include an "id", for example "QuantConnectBrokerage"')
    return await qc.post(
        "live/create",
        projectId=project_id,
        compileId=compile_id,
        nodeId=node_id,
        versionId=version_id,
        brokerage=brokerage,
        dataProviders=data_providers or {brokerage_id: {"id": brokerage_id}},
        parameters=parameters,
        notification=notification,
        automaticRedeploy=automatic_redeploy,
    )


@tool(annotations=READ_ONLY)
async def read_live_algorithm(project_id: int, qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """Read the status, runtime statistics, and charts of a project's live algorithm.

    Args:
        project_id: The live project.
    """
    return await qc.post("live/read", projectId=project_id)


@tool(annotations=READ_ONLY)
async def list_live_algorithms(
    status: LiveStatus | None = None,
    project_id: int | None = None,
    latest: bool | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """List live algorithms, optionally filtered.

    Args:
        status: Only include algorithms with this status.
        project_id: Only include deployments of this project.
        latest: Only include the most recent deployment of each project.
    """
    return await qc.post("live/list", status=status, projectId=project_id, latest=latest)


@tool(annotations=READ_ONLY)
async def read_live_logs(
    project_id: int,
    algorithm_id: str,
    start_line: Index = 0,
    end_line: Index = LOG_PAGE_LIMIT,
    query: str | None = None,
    deployment_logs: bool | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Read a page of a live algorithm's logs, at most 250 lines per call.

    Args:
        project_id: The live project.
        algorithm_id: The deploy ID of the live algorithm, for example "L-6e9d...".
        start_line: First line to read (inclusive, zero-based).
        end_line: Line after the last one to read (exclusive).
        query: Only return lines that contain this text.
        deployment_logs: Read the deployment logs instead of the algorithm logs.
    """
    check_range(start_line, end_line, LOG_PAGE_LIMIT)
    return await qc.post(
        "live/logs/read",
        projectId=project_id,
        algorithmId=algorithm_id,
        startLine=start_line,
        endLine=end_line,
        query=query,
        deploymentLogs=deployment_logs,
    )


@tool(annotations=READ_ONLY)
async def read_live_chart(
    project_id: int,
    name: str,
    start: Index,
    end: Index,
    count: int = 100,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Read one chart from a live algorithm, sampled to a number of points.

    If the response has status "loading", the chart is still being generated: call again.

    Args:
        project_id: The live project.
        name: Chart name, for example "Strategy Equity".
        start: Start of the window, as a Unix timestamp in seconds.
        end: End of the window, as a Unix timestamp in seconds.
        count: Number of data points to return.
    """
    check_range(start, end)
    return await qc.post(
        "live/chart/read", projectId=project_id, name=name, start=start, end=end, count=count
    )


@tool(annotations=READ_ONLY)
async def read_live_portfolio(project_id: int, qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """Read the current holdings and cash of a live algorithm.

    Args:
        project_id: The live project.
    """
    return await qc.post("live/portfolio/read", projectId=project_id)


@tool(annotations=READ_ONLY)
async def read_live_orders(
    project_id: int,
    start: Index = 0,
    end: Index = 100,
    deploy_id: str | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Read a page of a live algorithm's orders, at most 1000 per call (default 100).

    Args:
        project_id: The live project.
        start: Index of the first order (inclusive).
        end: Index after the last order (exclusive).
        deploy_id: Read a specific deployment. Defaults to the latest.
    """
    check_range(start, end, ORDERS_PAGE_LIMIT)
    return await qc.post(
        "live/orders/read", projectId=project_id, start=start, end=end, deployId=deploy_id
    )


@tool(annotations=READ_ONLY)
async def read_live_insights(
    project_id: int,
    start: Index = 0,
    end: Index = PAGE_LIMIT,
    algorithm_id: str | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Read a page of the alpha insights a live algorithm emitted, at most 99 per call.

    Args:
        project_id: The live project.
        start: Index of the first insight (inclusive).
        end: Index after the last insight (exclusive).
        algorithm_id: Read a specific deployment. Defaults to the latest.
    """
    check_range(start, end, PAGE_LIMIT)
    return await qc.post(
        "live/insights/read",
        projectId=project_id,
        start=start,
        end=end,
        algorithmId=algorithm_id,
    )


@tool(annotations=DESTRUCTIVE)
async def liquidate_live_algorithm(
    project_id: int, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Close every position of a live algorithm at market and stop it.

    Args:
        project_id: The live project to liquidate.
    """
    return await qc.post("live/update/liquidate", projectId=project_id)


@tool(annotations=DESTRUCTIVE)
async def stop_live_algorithm(project_id: int, qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """Stop a live algorithm, leaving its positions open.

    Args:
        project_id: The live project to stop.
    """
    return await qc.post("live/update/stop", projectId=project_id)


@tool(annotations=DESTRUCTIVE)
async def create_live_command(
    project_id: int, command: dict[str, Any], qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Send a command to a running live algorithm.

    The algorithm handles it in its on_command method, or in the Command class
    named by the "$type" key.

    Args:
        project_id: The live project.
        command: The command payload, for example {"$type": "MyCommand", "ticker": "SPY"}.
    """
    return await qc.post("live/commands/create", projectId=project_id, command=command)


@tool(annotations=DESTRUCTIVE)
async def broadcast_live_command(
    command: dict[str, Any],
    exclude_project_id: int | None = None,
    organization_id: str | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Send a command to every live algorithm in the organization.

    Args:
        command: The command payload, for example {"$type": "MyCommand"}.
        exclude_project_id: A project to leave out of the broadcast.
        organization_id: Organization to broadcast to. Defaults to your organization.
    """
    return await qc.post(
        "live/commands/broadcast",
        organizationId=await qc.organization_id(organization_id),
        excludeProjectId=exclude_project_id,
        command=command,
    )


TOOLS = (
    create_live_algorithm,
    read_live_algorithm,
    list_live_algorithms,
    read_live_logs,
    read_live_chart,
    read_live_portfolio,
    read_live_orders,
    read_live_insights,
    liquidate_live_algorithm,
    stop_live_algorithm,
    create_live_command,
    broadcast_live_command,
)

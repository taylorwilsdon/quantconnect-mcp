"""Compilation tools."""

import asyncio
from typing import Any

from fastmcp import Context
from fastmcp.tools import tool

from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.tools._shared import CLIENT, MUTATING, READ_ONLY

POLL_INTERVAL_SECONDS = 2.0
MAX_POLLS = 60


@tool(annotations=MUTATING)
async def compile_project(
    project_id: int, ctx: Context, wait: bool = True, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Compile a project. A successful compile ID is required to backtest, optimize, or deploy.

    Args:
        project_id: The project to compile.
        wait: Wait for the build to finish (state BuildSuccess or BuildError) and
            return its logs. When false, return immediately with state InQueue.
    """
    result = await qc.post("compile/create", projectId=project_id)
    for poll in range(1, MAX_POLLS + 1):
        if not wait or result.get("state") != "InQueue":
            break
        await ctx.report_progress(poll, MAX_POLLS, "Waiting for the build to finish")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        result = await qc.post("compile/read", projectId=project_id, compileId=result["compileId"])
    return result


@tool(annotations=READ_ONLY)
async def read_compilation_result(
    project_id: int, compile_id: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Read the state and build logs of a compile job.

    Args:
        project_id: The compiled project.
        compile_id: The compile ID returned by compile_project.
    """
    return await qc.post("compile/read", projectId=project_id, compileId=compile_id)


TOOLS = (compile_project, read_compilation_result)

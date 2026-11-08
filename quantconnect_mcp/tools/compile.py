"""Compilation tools."""

import asyncio
from typing import Any

from fastmcp import Context
from fastmcp.exceptions import ToolError
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
            return its logs. Fails with the compile ID if the build is still queued
            after about two minutes. When false, return immediately with state InQueue.
    """
    result = await qc.post("compile/create", projectId=project_id)
    if not wait or result.get("state") != "InQueue":
        return result
    compile_id = result.get("compileId")
    if not compile_id:
        raise ToolError("QuantConnect queued the build but returned no compileId to poll")
    for poll in range(1, MAX_POLLS + 1):
        await ctx.report_progress(poll, MAX_POLLS, "Waiting for the build to finish")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        result = await qc.post("compile/read", projectId=project_id, compileId=compile_id)
        if result.get("state") != "InQueue":
            return result
    raise ToolError(
        f"Build {compile_id} did not finish within the wait window; "
        "check it later with read_compilation_result"
    )


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

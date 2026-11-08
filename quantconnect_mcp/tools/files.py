"""Project file tools."""

from typing import Any

from fastmcp.tools import tool

from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.tools._shared import CLIENT, DESTRUCTIVE, MUTATING, READ_ONLY


@tool(annotations=MUTATING)
async def create_file(
    project_id: int, name: str, content: str = "", qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Add a file to a project.

    Args:
        project_id: The project to add the file to.
        name: File name, for example "alpha.py" or "utils/helpers.py".
        content: Initial file contents.
    """
    return await qc.post("files/create", projectId=project_id, name=name, content=content)


@tool(annotations=READ_ONLY)
async def read_file(
    project_id: int, name: str | None = None, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Read one file from a project, or every file when no name is given.

    Args:
        project_id: The project that contains the file.
        name: The file to read. Omit to read all files.
    """
    return await qc.post("files/read", projectId=project_id, name=name)


@tool(annotations=MUTATING)
async def update_file_content(
    project_id: int, name: str, content: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Replace the full contents of a project file.

    Args:
        project_id: The project that contains the file.
        name: The file to overwrite.
        content: The new file contents.
    """
    return await qc.post("files/update", projectId=project_id, name=name, content=content)


@tool(annotations=MUTATING)
async def update_file_name(
    project_id: int, name: str, new_name: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Rename a project file.

    Args:
        project_id: The project that contains the file.
        name: The current file name.
        new_name: The new file name.
    """
    return await qc.post("files/update", projectId=project_id, name=name, newName=new_name)


@tool(annotations=DESTRUCTIVE)
async def delete_file(
    project_id: int, name: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Delete a file from a project.

    Args:
        project_id: The project that contains the file.
        name: The file to delete.
    """
    return await qc.post("files/delete", projectId=project_id, name=name)


TOOLS = (create_file, read_file, update_file_content, update_file_name, delete_file)

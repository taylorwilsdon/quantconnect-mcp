"""Project, collaborator, and node management tools."""

from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.tools import tool

from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.tools._shared import CLIENT, DESTRUCTIVE, MUTATING, READ_ONLY, Language


@tool(annotations=MUTATING)
async def create_project(
    name: str,
    language: Language = "Py",
    organization_id: str | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Create a new project.

    Args:
        name: Project name, unique within the organization. Use slashes for folders.
        language: "Py" for Python or "C#".
        organization_id: Organization to create the project in. Defaults to the
            configured organization, then to your preferred organization.
    """
    return await qc.post(
        "projects/create",
        name=name,
        language=language,
        organizationId=organization_id or qc.configured_organization_id,
    )


@tool(annotations=READ_ONLY)
async def read_project(
    project_id: int | None = None, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Read one project, or list every project when no ID is given.

    Args:
        project_id: The project to read. Omit to list all projects.
    """
    return await qc.post("projects/read", projectId=project_id)


@tool(annotations=MUTATING)
async def update_project(
    project_id: int,
    name: str | None = None,
    description: str | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Rename a project or change its description.

    Args:
        project_id: The project to update.
        name: New project name.
        description: New project description.
    """
    if name is None and description is None:
        raise ToolError("Provide a new name, a new description, or both")
    return await qc.post(
        "projects/update", projectId=project_id, name=name, description=description
    )


@tool(annotations=DESTRUCTIVE)
async def delete_project(project_id: int, qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """Permanently delete a project, including its files and backtests.

    Args:
        project_id: The project to delete.
    """
    return await qc.post("projects/delete", projectId=project_id)


@tool(annotations=MUTATING)
async def create_project_collaborator(
    project_id: int,
    collaborator_user_id: str,
    write: bool = True,
    live_control: bool = False,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Add a collaborator to a project.

    Args:
        project_id: The project to share.
        collaborator_user_id: The collaborator's user ID, from their profile URL.
        write: Allow the collaborator to edit files.
        live_control: Allow the collaborator to deploy and stop live algorithms.
    """
    return await qc.post(
        "projects/collaboration/create",
        projectId=project_id,
        collaboratorUserId=collaborator_user_id,
        collaborationWrite=write,
        collaborationLiveControl=live_control,
    )


@tool(annotations=READ_ONLY)
async def read_project_collaborators(
    project_id: int, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """List a project's collaborators and their permissions.

    Args:
        project_id: The project to inspect.
    """
    return await qc.post("projects/collaboration/read", projectId=project_id)


@tool(annotations=MUTATING)
async def update_project_collaborator(
    project_id: int,
    collaborator_user_id: str,
    write: bool,
    live_control: bool,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Change a collaborator's permissions.

    Args:
        project_id: The shared project.
        collaborator_user_id: The collaborator's user ID.
        write: Allow the collaborator to edit files.
        live_control: Allow the collaborator to deploy and stop live algorithms.
    """
    return await qc.post(
        "projects/collaboration/update",
        projectId=project_id,
        collaboratorUserId=collaborator_user_id,
        write=write,
        liveControl=live_control,
    )


@tool(annotations=DESTRUCTIVE)
async def delete_project_collaborator(
    project_id: int, collaborator_user_id: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Remove a collaborator from a project.

    Args:
        project_id: The shared project.
        collaborator_user_id: The collaborator's user ID.
    """
    return await qc.post(
        "projects/collaboration/delete",
        projectId=project_id,
        collaboratorId=collaborator_user_id,
    )


@tool(annotations=READ_ONLY)
async def read_project_nodes(project_id: int, qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """List the backtest, research, and live nodes available to a project.

    Args:
        project_id: The project to inspect.
    """
    return await qc.post("projects/nodes/read", projectId=project_id)


@tool(annotations=MUTATING)
async def update_project_nodes(
    project_id: int, nodes: list[str] | None = None, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Choose which nodes a project may use.

    Args:
        project_id: The project to configure.
        nodes: Node IDs the project may use. Omit or pass an empty list to let
            QuantConnect pick the best available node automatically.
    """
    return await qc.post("projects/nodes/update", projectId=project_id, nodes=nodes or [])


TOOLS = (
    create_project,
    read_project,
    update_project,
    delete_project,
    create_project_collaborator,
    read_project_collaborators,
    update_project_collaborator,
    delete_project_collaborator,
    read_project_nodes,
    update_project_nodes,
)

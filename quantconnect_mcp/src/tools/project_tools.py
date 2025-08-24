"""Project Management Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, Optional
from ..auth.quantconnect_auth import get_auth_instance  # type: ignore


def register_project_tools(mcp: FastMCP):
    """Register project management tools with the MCP server."""

    @mcp.tool()
    async def create_project(
        name: str, language: str = "Py", organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new project in your QuantConnect organization.

        Args:
            name: Project name (must be unique within organization)
            language: Programming language - "C#" or "Py" (default: "Py")
            organization_id: Optional organization ID (uses default if not specified)

        Returns:
            Dictionary containing project creation result with project details
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        # Validate language parameter
        valid_languages = ["C#", "Py"]
        if language not in valid_languages:
            return {
                "status": "error",
                "error": f"Invalid language '{language}'. Must be one of: {valid_languages}",
            }

        try:
            # Prepare request data
            request_data = {"name": name, "language": language}

            # Add organization ID if provided, otherwise use the auth instance's default
            if organization_id:
                request_data["organizationId"] = organization_id
            elif auth.organization_id:
                request_data["organizationId"] = auth.organization_id

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="projects/create", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    # Extract project info from the response
                    projects = data.get("projects", [])
                    if projects:
                        # The newly created project should be in the list
                        created_project = None
                        for project in projects:
                            if (
                                project.get("name") == name
                                and project.get("language") == language
                            ):
                                created_project = project
                                break

                        if created_project:
                            return {
                                "status": "success",
                                "project": created_project,
                                "message": f"Successfully created project '{name}' with {language} language",
                            }

                    # Fallback response if project not found in list
                    return {
                        "status": "success",
                        "project": {
                            "name": name,
                            "language": language,
                            "organizationId": request_data.get("organizationId"),
                        },
                        "message": f"Successfully created project '{name}' with {language} language",
                        "note": "Full project details not available in response",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Project creation failed",
                        "details": errors,
                        "api_response": data,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to create project: {str(e)}",
                "project_name": name,
                "language": language,
            }

    @mcp.tool()
    async def read_project(project_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Read project details by ID or list all projects if no ID provided.

        Args:
            project_id: Optional project ID to get specific project details.
                       If not provided, returns list of all projects.

        Returns:
            Dictionary containing project details or list of all projects
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {}
            if project_id is not None:
                request_data["projectId"] = project_id

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="projects/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    projects = data.get("projects", [])
                    versions = data.get("versions", [])

                    # If specific project ID was requested
                    if project_id is not None:
                        if projects:
                            return {
                                "status": "success",
                                "project": projects[0],
                                "versions": versions,
                                "message": f"Successfully retrieved project {project_id}",
                            }
                        else:
                            return {
                                "status": "error",
                                "error": f"Project with ID {project_id} not found",
                            }

                    # If no project ID specified, return all projects
                    else:
                        return {
                            "status": "success",
                            "projects": projects,
                            "total_projects": len(projects),
                            "versions": versions,
                            "message": f"Successfully retrieved {len(projects)} projects",
                        }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read project(s)",
                        "details": errors,
                        "api_response": data,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to read project(s): {str(e)}",
                "project_id": project_id,
            }

    @mcp.tool()
    async def update_project(
        project_id: int, name: Optional[str] = None, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a project's name and/or description.

        Args:
            project_id: ID of the project to update
            name: Optional new name for the project
            description: Optional new description for the project

        Returns:
            Dictionary containing update result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        # Validate at least one field is provided
        if name is None and description is None:
            return {
                "status": "error",
                "error": "At least one of 'name' or 'description' must be provided for update",
            }

        try:
            # Prepare request data
            request_data: Dict[str, Any] = {"projectId": int(project_id)}

            if name is not None:
                request_data["name"] = name
            if description is not None:
                request_data["description"] = description

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="projects/update", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    update_fields = []
                    if name is not None:
                        update_fields.append(f"name to '{name}'")
                    if description is not None:
                        update_fields.append(f"description")

                    return {
                        "status": "success",
                        "project_id": project_id,
                        "updated_fields": update_fields,
                        "message": f"Successfully updated project {project_id}: {', '.join(update_fields)}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Project update failed",
                        "details": errors,
                        "project_id": project_id,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to update project: {str(e)}",
                "project_id": project_id,
            }

    @mcp.tool()
    async def compile_project(project_id: int) -> Dict[str, Any]:
        """
        Compile a project in QuantConnect.

        Args:
            project_id: The ID of the project to compile.

        Returns:
            A dictionary containing the compilation result with compile ID, state, and logs.
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data with project ID in JSON payload
            request_data = {"projectId": project_id}
            
            response = await auth.make_authenticated_request(
                endpoint="compile/create", method="POST", json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return {
                        "status": "success",
                        "compile_id": data.get("compileId"),
                        "state": data.get("state"),
                        "project_id": data.get("projectId"),
                        "signature": data.get("signature"),
                        "signature_order": data.get("signatureOrder", []),
                        "logs": data.get("logs", []),
                        "message": "Project compilation started successfully.",
                    }
                else:
                    return {
                        "status": "error",
                        "error": "Project compilation failed.",
                        "details": data.get("errors", []),
                        "project_id": project_id,
                    }
            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }
            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": response.text[:500] if hasattr(response, "text") else "No response text",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": f"An unexpected error occurred: {e}",
                "project_id": project_id,
            }

    @mcp.tool()
    async def read_compilation_result(project_id: int, compile_id: str) -> Dict[str, Any]:
        """
        Read the result of a compilation job in QuantConnect.

        Args:
            project_id: The ID of the project that was compiled.
            compile_id: The compile ID returned from compile_project.

        Returns:
            A dictionary containing the compilation result with state, logs, and errors.
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data with project ID and compile ID in JSON payload
            request_data = {"projectId": project_id, "compileId": compile_id}
            
            response = await auth.make_authenticated_request(
                endpoint="compile/read", method="POST", json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logs = data.get("logs", [])
                    errors = data.get("errors", [])
                    state = data.get("state")
                    
                    # Check for compilation warnings in logs that indicate issues
                    warnings = []
                    for log in logs:
                        if "Warning" in log:
                            warnings.append(log)
                    
                    # If there are warnings or explicit errors, treat as compilation failure
                    if warnings or errors:
                        return {
                            "status": "error",
                            "compile_id": data.get("compileId"),
                            "state": state,
                            "project_id": data.get("projectId"),
                            "signature": data.get("signature"),
                            "signature_order": data.get("signatureOrder", []),
                            "logs": logs,
                            "errors": errors,
                            "warnings": warnings,
                            "message": f"Compilation completed with {len(warnings)} warnings and {len(errors)} errors. Code issues must be fixed before proceeding.",
                            "error": f"Compilation failed: {len(warnings)} warnings, {len(errors)} errors found",
                        }
                    
                    return {
                        "status": "success",
                        "compile_id": data.get("compileId"),
                        "state": state,
                        "project_id": data.get("projectId"),
                        "signature": data.get("signature"),
                        "signature_order": data.get("signatureOrder", []),
                        "logs": logs,
                        "errors": errors,
                        "message": f"Compilation result retrieved successfully. State: {state}",
                    }
                else:
                    return {
                        "status": "error",
                        "error": "Failed to read compilation result.",
                        "details": data.get("errors", []),
                        "project_id": project_id,
                        "compile_id": compile_id,
                    }
            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }
            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": response.text[:500] if hasattr(response, "text") else "No response text",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": f"An unexpected error occurred: {e}",
                "project_id": project_id,
                "compile_id": compile_id,
            }

    @mcp.tool()
    async def delete_project(project_id: int) -> Dict[str, Any]:
        """
        Delete a project from QuantConnect.

        Args:
            project_id: The ID of the project to delete.

        Returns:
            A dictionary containing the deletion result.
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {"projectId": project_id}
            
            response = await auth.make_authenticated_request(
                endpoint="projects/delete", method="POST", json=request_data
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "message": f"Successfully deleted project {project_id}.",
                    }
                else:
                    return {
                        "status": "error",
                        "error": "Project deletion failed.",
                        "details": data.get("errors", []),
                        "project_id": project_id,
                    }
            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }
            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": response.text[:500] if hasattr(response, "text") else "No response text",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": f"An unexpected error occurred: {e}",
                "project_id": project_id,
            }

    @mcp.tool()
    async def create_project_collaborator(
        project_id: int, email: str, permission: str = "read"
    ) -> Dict[str, Any]:
        """
        Add a collaborator to a project.

        Args:
            project_id: ID of the project to add collaborator to
            email: Email address of the user to add as collaborator
            permission: Permission level ("read" or "write", default: "read")

        Returns:
            Dictionary containing collaborator addition result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        # Validate permission parameter
        valid_permissions = ["read", "write"]
        if permission not in valid_permissions:
            return {
                "status": "error",
                "error": f"Invalid permission '{permission}'. Must be one of: {valid_permissions}",
            }

        try:
            # Prepare request data
            request_data = {
                "projectId": project_id,
                "email": email,
                "permission": permission,
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="projects/collaborators/create", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "collaborator_email": email,
                        "permission": permission,
                        "message": f"Successfully added collaborator {email} with {permission} permission to project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to add project collaborator",
                        "details": errors,
                        "project_id": project_id,
                        "email": email,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to add project collaborator: {str(e)}",
                "project_id": project_id,
                "email": email,
            }

    @mcp.tool()
    async def read_project_collaborators(project_id: int) -> Dict[str, Any]:
        """
        List all collaborators on a project.

        Args:
            project_id: ID of the project to list collaborators for

        Returns:
            Dictionary containing list of project collaborators
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {"projectId": project_id}

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="projects/collaborators/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    collaborators = data.get("collaborators", [])
                    
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "collaborators": collaborators,
                        "total_collaborators": len(collaborators),
                        "message": f"Successfully retrieved {len(collaborators)} collaborators for project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read project collaborators",
                        "details": errors,
                        "project_id": project_id,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to read project collaborators: {str(e)}",
                "project_id": project_id,
            }

    @mcp.tool()
    async def update_project_collaborator(
        project_id: int, user_id: int, permission: str
    ) -> Dict[str, Any]:
        """
        Update collaborator information in a project.

        Args:
            project_id: ID of the project containing the collaborator
            user_id: User ID of the collaborator to update
            permission: New permission level ("read" or "write")

        Returns:
            Dictionary containing update result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        # Validate permission parameter
        valid_permissions = ["read", "write"]
        if permission not in valid_permissions:
            return {
                "status": "error",
                "error": f"Invalid permission '{permission}'. Must be one of: {valid_permissions}",
            }

        try:
            # Prepare request data
            request_data = {
                "projectId": project_id,
                "userId": user_id,
                "permission": permission,
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="projects/collaborators/update", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "user_id": user_id,
                        "permission": permission,
                        "message": f"Successfully updated collaborator {user_id} permission to {permission} for project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to update project collaborator",
                        "details": errors,
                        "project_id": project_id,
                        "user_id": user_id,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to update project collaborator: {str(e)}",
                "project_id": project_id,
                "user_id": user_id,
            }

    @mcp.tool()
    async def delete_project_collaborator(
        project_id: int, user_id: int
    ) -> Dict[str, Any]:
        """
        Remove a collaborator from a project.

        Args:
            project_id: ID of the project to remove collaborator from
            user_id: User ID of the collaborator to remove

        Returns:
            Dictionary containing removal result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {
                "projectId": project_id,
                "userId": user_id,
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="projects/collaborators/delete", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "user_id": user_id,
                        "message": f"Successfully removed collaborator {user_id} from project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to remove project collaborator",
                        "details": errors,
                        "project_id": project_id,
                        "user_id": user_id,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to remove project collaborator: {str(e)}",
                "project_id": project_id,
                "user_id": user_id,
            }

    @mcp.tool()
    async def read_project_nodes(project_id: int) -> Dict[str, Any]:
        """
        Read the available and selected nodes of a project.

        Args:
            project_id: ID of the project to read nodes for

        Returns:
            Dictionary containing project node information
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {"projectId": project_id}

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="projects/nodes/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    nodes = data.get("nodes", {})
                    
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "nodes": nodes,
                        "message": f"Successfully retrieved node information for project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read project nodes",
                        "details": errors,
                        "project_id": project_id,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to read project nodes: {str(e)}",
                "project_id": project_id,
            }

    @mcp.tool()
    async def update_project_nodes(
        project_id: int, nodes: Dict[str, bool]
    ) -> Dict[str, Any]:
        """
        Update the active state of the given nodes to true.

        Args:
            project_id: ID of the project to update nodes for
            nodes: Dictionary mapping node IDs to their active state (true/false)

        Returns:
            Dictionary containing update result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {
                "projectId": project_id,
                "nodes": nodes,
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="projects/nodes/update", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    active_nodes = [node_id for node_id, active in nodes.items() if active]
                    
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "updated_nodes": nodes,
                        "active_nodes": active_nodes,
                        "message": f"Successfully updated {len(nodes)} node(s) for project {project_id}, {len(active_nodes)} now active",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to update project nodes",
                        "details": errors,
                        "project_id": project_id,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to update project nodes: {str(e)}",
                "project_id": project_id,
            }
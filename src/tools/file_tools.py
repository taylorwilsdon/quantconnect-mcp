"""File Management Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, Optional
from ..auth.quantconnect_auth import get_auth_instance  # type: ignore


def register_file_tools(mcp: FastMCP):
    """Register file management tools with the MCP server."""

    @mcp.tool()
    async def create_file(project_id: int, name: str, content: str) -> Dict[str, Any]:
        """
        Create a new file in a QuantConnect project.

        Args:
            project_id: ID of the project to add the file to
            name: Name of the file (e.g., "main.py", "algorithm.cs")
            content: Content of the file

        Returns:
            Dictionary containing file creation result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {"projectId": project_id, "name": name, "content": content}

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="files/create", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "file_name": name,
                        "content_length": len(content),
                        "message": f"Successfully created file '{name}' in project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "File creation failed",
                        "details": errors,
                        "project_id": project_id,
                        "file_name": name,
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
                "error": f"Failed to create file: {str(e)}",
                "project_id": project_id,
                "file_name": name,
            }

    @mcp.tool()
    async def read_file(project_id: int, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Read a specific file from a project or all files if no name provided.

        Args:
            project_id: ID of the project to read files from
            name: Optional name of specific file to read. If not provided, reads all files.

        Returns:
            Dictionary containing file content(s) or error information
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data: Dict[str, Any] = {"projectId": project_id}
            if name is not None:
                request_data["name"] = name

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="files/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    files = data.get("files", [])

                    # If specific file was requested
                    if name is not None:
                        if files:
                            file_data = files[0]
                            return {
                                "status": "success",
                                "project_id": project_id,
                                "file": file_data,
                                "message": f"Successfully read file '{name}' from project {project_id}",
                            }
                        else:
                            return {
                                "status": "error",
                                "error": f"File '{name}' not found in project {project_id}",
                            }

                    # If all files were requested
                    else:
                        return {
                            "status": "success",
                            "project_id": project_id,
                            "files": files,
                            "total_files": len(files),
                            "message": f"Successfully read {len(files)} files from project {project_id}",
                        }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "File read failed",
                        "details": errors,
                        "project_id": project_id,
                        "file_name": name,
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
                "error": f"Failed to read file(s): {str(e)}",
                "project_id": project_id,
                "file_name": name,
            }

    @mcp.tool()
    async def update_file_content(
        project_id: int, name: str, content: str
    ) -> Dict[str, Any]:
        """
        Update the content of a file in a QuantConnect project.

        Args:
            project_id: ID of the project containing the file
            name: Name of the file to update
            content: New content for the file

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
            request_data = {"projectId": project_id, "name": name, "content": content}

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="files/update", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "file_name": name,
                        "content_length": len(content),
                        "message": f"Successfully updated content of file '{name}' in project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "File content update failed",
                        "details": errors,
                        "project_id": project_id,
                        "file_name": name,
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
                "error": f"Failed to update file content: {str(e)}",
                "project_id": project_id,
                "file_name": name,
            }

    @mcp.tool()
    async def update_file_name(
        project_id: int, old_file_name: str, new_name: str
    ) -> Dict[str, Any]:
        """
        Update the name of a file in a QuantConnect project.

        Args:
            project_id: ID of the project containing the file
            old_file_name: Current name of the file
            new_name: New name for the file

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
                "oldFileName": old_file_name,
                "newName": new_name,
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="files/update", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "old_name": old_file_name,
                        "new_name": new_name,
                        "message": f"Successfully renamed file from '{old_file_name}' to '{new_name}' in project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "File name update failed",
                        "details": errors,
                        "project_id": project_id,
                        "old_name": old_file_name,
                        "new_name": new_name,
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
                "error": f"Failed to update file name: {str(e)}",
                "project_id": project_id,
                "old_name": old_file_name,
                "new_name": new_name,
            }

"""Optimization Management Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, Optional
from ..auth.quantconnect_auth import get_auth_instance  # type: ignore


def register_optimization_tools(mcp: FastMCP):
    """Register optimization management tools with the MCP server."""

    @mcp.tool()
    async def estimate_optimization_time(
        project_id: int,
        compile_id: str,
        node_type: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Estimate the execution time of an optimization with the specified parameters.

        Args:
            project_id: ID of the project to optimize
            compile_id: Compile ID from successful project compilation
            node_type: Type of node to use for optimization
            parameters: Dictionary of optimization parameters

        Returns:
            Dictionary containing estimated optimization time
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
                "compileId": compile_id,
                "nodeType": node_type,
                "parameters": parameters,
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="optimizations/estimate", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "compile_id": compile_id,
                        "node_type": node_type,
                        "estimated_time": data.get("estimatedTime"),
                        "message": f"Successfully estimated optimization time for project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Optimization time estimation failed",
                        "details": errors,
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
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to estimate optimization time: {str(e)}",
                "project_id": project_id,
                "compile_id": compile_id,
            }

    @mcp.tool()
    async def create_optimization(
        project_id: int,
        compile_id: str,
        node_type: str,
        parameters: Dict[str, Any],
        name: Optional[str] = None,
        maximum_runtime: Optional[int] = None,
        output_target: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an optimization with the specified parameters.

        Args:
            project_id: ID of the project to optimize
            compile_id: Compile ID from successful project compilation
            node_type: Type of node to use for optimization
            parameters: Dictionary of optimization parameters
            name: Optional name for the optimization
            maximum_runtime: Optional maximum runtime in seconds
            output_target: Optional optimization target (e.g., "Sharpe Ratio")

        Returns:
            Dictionary containing optimization creation result
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
                "compileId": compile_id,
                "nodeType": node_type,
                "parameters": parameters,
            }

            # Add optional parameters
            if name is not None:
                request_data["name"] = name
            if maximum_runtime is not None:
                request_data["maximumRuntime"] = maximum_runtime
            if output_target is not None:
                request_data["outputTarget"] = output_target

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="optimizations/create", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    optimization = data.get("optimization", {})
                    optimization_id = optimization.get("optimizationId")
                    
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "compile_id": compile_id,
                        "optimization_id": optimization_id,
                        "optimization": optimization,
                        "message": f"Successfully created optimization {optimization_id} for project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Optimization creation failed",
                        "details": errors,
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
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to create optimization: {str(e)}",
                "project_id": project_id,
                "compile_id": compile_id,
            }

    @mcp.tool()
    async def read_optimization(
        optimization_id: str
    ) -> Dict[str, Any]:
        """
        Read an optimization by its ID.

        Args:
            optimization_id: ID of the optimization to read

        Returns:
            Dictionary containing optimization details and results
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {"optimizationId": optimization_id}

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="optimizations/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    optimization = data.get("optimization", {})
                    
                    return {
                        "status": "success",
                        "optimization_id": optimization_id,
                        "optimization": optimization,
                        "message": f"Successfully read optimization {optimization_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read optimization",
                        "details": errors,
                        "optimization_id": optimization_id,
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
                "error": f"Failed to read optimization: {str(e)}",
                "optimization_id": optimization_id,
            }

    @mcp.tool()
    async def list_optimizations(
        project_id: int
    ) -> Dict[str, Any]:
        """
        List all optimizations for a project.

        Args:
            project_id: ID of the project to list optimizations for

        Returns:
            Dictionary containing list of optimizations
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
                endpoint="optimizations/list", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    optimizations = data.get("optimizations", [])
                    
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "optimizations": optimizations,
                        "total_optimizations": len(optimizations),
                        "message": f"Successfully retrieved {len(optimizations)} optimizations for project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to list optimizations",
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
                "error": f"Failed to list optimizations: {str(e)}",
                "project_id": project_id,
            }

    @mcp.tool()
    async def update_optimization(
        optimization_id: str,
        name: str
    ) -> Dict[str, Any]:
        """
        Update the name of an optimization.

        Args:
            optimization_id: ID of the optimization to update
            name: New name for the optimization

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
                "optimizationId": optimization_id,
                "name": name
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="optimizations/update", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "optimization_id": optimization_id,
                        "new_name": name,
                        "message": f"Successfully updated optimization {optimization_id} name to '{name}'",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Optimization update failed",
                        "details": errors,
                        "optimization_id": optimization_id,
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
                "error": f"Failed to update optimization: {str(e)}",
                "optimization_id": optimization_id,
            }

    @mcp.tool()
    async def abort_optimization(
        optimization_id: str
    ) -> Dict[str, Any]:
        """
        Abort an optimization that is currently running.

        Args:
            optimization_id: ID of the optimization to abort

        Returns:
            Dictionary containing abort result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {"optimizationId": optimization_id}

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="optimizations/abort", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "optimization_id": optimization_id,
                        "message": f"Successfully aborted optimization {optimization_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Optimization abort failed",
                        "details": errors,
                        "optimization_id": optimization_id,
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
                "error": f"Failed to abort optimization: {str(e)}",
                "optimization_id": optimization_id,
            }

    @mcp.tool()
    async def delete_optimization(
        optimization_id: str
    ) -> Dict[str, Any]:
        """
        Delete an optimization.

        Args:
            optimization_id: ID of the optimization to delete

        Returns:
            Dictionary containing deletion result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {"optimizationId": optimization_id}

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="optimizations/delete", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "optimization_id": optimization_id,
                        "message": f"Successfully deleted optimization {optimization_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Optimization deletion failed",
                        "details": errors,
                        "optimization_id": optimization_id,
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
                "error": f"Failed to delete optimization: {str(e)}",
                "optimization_id": optimization_id,
            }
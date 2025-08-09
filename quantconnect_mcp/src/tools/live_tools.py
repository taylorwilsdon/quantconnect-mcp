"""Live Trading Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, Optional, List
from ..auth.quantconnect_auth import get_auth_instance  # type: ignore


def register_live_tools(mcp: FastMCP):
    """Register live trading tools with the MCP server."""

    @mcp.tool()
    async def create_live_algorithm(
        project_id: int,
        compile_id: str,
        node_id: str,
        brokerage_id: str,
        brokerage_config: Dict[str, Any],
        data_providers: Optional[Dict[str, Any]] = None,
        version_id: str = "-1",
        parameters: Optional[Dict[str, Any]] = None,
        notifications: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a live algorithm deployment.

        Args:
            project_id: ID of the project to deploy
            compile_id: Compile ID from successful project compilation
            node_id: ID of the node that will run the algorithm
            brokerage_id: Brokerage identifier (e.g., "QuantConnectBrokerage", "InteractiveBrokersBrokerage")
            brokerage_config: Brokerage configuration dictionary with credentials and settings
            data_providers: Optional data provider configurations (defaults to same as brokerage)
            version_id: Version of Lean to use (default: "-1" for master)
            parameters: Optional algorithm parameters
            notifications: Optional notification settings

        Returns:
            Dictionary containing live algorithm deployment result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        # Validate required brokerage config
        if not isinstance(brokerage_config, dict) or "id" not in brokerage_config:
            return {
                "status": "error",
                "error": "brokerage_config must be a dictionary with 'id' field",
            }

        try:
            # Prepare request data
            request_data = {
                "versionId": version_id,
                "projectId": project_id,
                "compileId": compile_id,
                "nodeId": node_id,
                "brokerage": brokerage_config,
            }

            # Set up data providers (default to same as brokerage if not specified)
            if data_providers is None:
                request_data["dataProviders"] = {
                    brokerage_id: {"id": brokerage_id}
                }
            else:
                request_data["dataProviders"] = data_providers

            # Add optional parameters
            if parameters:
                request_data["parameters"] = parameters
            else:
                request_data["parameters"] = {}

            if notifications:
                request_data["notification"] = notifications
            else:
                request_data["notification"] = {}

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="live/create", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    live_algorithm = data.get("live", {})
                    deploy_id = live_algorithm.get("deployId")
                    status = live_algorithm.get("status")

                    return {
                        "status": "success",
                        "project_id": project_id,
                        "compile_id": compile_id,
                        "deploy_id": deploy_id,
                        "live_status": status,
                        "brokerage": live_algorithm.get("brokerage"),
                        "launched": live_algorithm.get("launched"),
                        "live_algorithm": live_algorithm,
                        "message": f"Successfully created live algorithm {deploy_id} with status: {status}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Live algorithm creation failed",
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
                "error": f"Failed to create live algorithm: {str(e)}",
                "project_id": project_id,
                "compile_id": compile_id,
            }

    @mcp.tool()
    async def read_live_algorithm(
        project_id: int, deploy_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read comprehensive live algorithm statistics, runtime data, and details.

        Args:
            project_id: ID of the project with the live algorithm
            deploy_id: Optional deploy ID for specific algorithm (omit to get latest)

        Returns:
            Dictionary containing detailed live algorithm statistics, runtime data, charts, and files
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
            if deploy_id:
                request_data["deployId"] = deploy_id

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="live/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    # Extract all the detailed information from LiveAlgorithmResults
                    deploy_id = data.get("deployId")
                    status = data.get("status")
                    message = data.get("message")
                    clone_id = data.get("cloneId")
                    launched = data.get("launched")
                    stopped = data.get("stopped")
                    brokerage = data.get("brokerage")
                    security_types = data.get("securityTypes")
                    project_name = data.get("projectName")
                    data_center = data.get("dataCenter")
                    public = data.get("public")
                    files = data.get("files", [])
                    runtime_statistics = data.get("runtimeStatistics", {})
                    charts = data.get("charts", {})
                    
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "deploy_id": deploy_id,
                        "live_status": status,
                        "message": message,
                        "clone_id": clone_id,
                        "launched": launched,
                        "stopped": stopped,
                        "brokerage": brokerage,
                        "security_types": security_types,
                        "project_name": project_name,
                        "data_center": data_center,
                        "public": public,
                        "files": files,
                        "runtime_statistics": runtime_statistics,
                        "charts": charts,
                        "total_files": len(files),
                        "has_runtime_stats": bool(runtime_statistics),
                        "response": f"Successfully read live algorithm {deploy_id} for project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read live algorithm",
                        "details": errors,
                        "project_id": project_id,
                        "deploy_id": deploy_id,
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
                "error": f"Failed to read live algorithm: {str(e)}",
                "project_id": project_id,
                "deploy_id": deploy_id,
            }

    @mcp.tool()
    async def liquidate_live_algorithm(project_id: int) -> Dict[str, Any]:
        """
        Liquidate all positions in a live algorithm.

        Args:
            project_id: ID of the project with the live algorithm to liquidate

        Returns:
            Dictionary containing liquidation result
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
                endpoint="live/update/liquidate", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "message": f"Successfully liquidated live algorithm for project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Live algorithm liquidation failed",
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
                "error": f"Failed to liquidate live algorithm: {str(e)}",
                "project_id": project_id,
            }

    @mcp.tool()
    async def stop_live_algorithm(project_id: int) -> Dict[str, Any]:
        """
        Stop a live algorithm.

        Args:
            project_id: ID of the project with the live algorithm to stop

        Returns:
            Dictionary containing stop result
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
                endpoint="live/update/stop", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "message": f"Successfully stopped live algorithm for project {project_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Live algorithm stop failed",
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
                "error": f"Failed to stop live algorithm: {str(e)}",
                "project_id": project_id,
            }

    @mcp.tool()
    async def list_live_algorithms(
        status: Optional[str] = None,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List live algorithms with optional filters.

        Args:
            status: Optional status filter (e.g., "Running", "Stopped")
            start: Optional start time (Unix timestamp)
            end: Optional end time (Unix timestamp)

        Returns:
            Dictionary containing list of live algorithms
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
            if status:
                request_data["status"] = status
            if start is not None:
                request_data["start"] = start
            if end is not None:
                request_data["end"] = end

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="live/list", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    live_algorithms = data.get("live", [])
                    
                    return {
                        "status": "success",
                        "live_algorithms": live_algorithms,
                        "total_count": len(live_algorithms),
                        "filters": {
                            "status": status,
                            "start": start,
                            "end": end,
                        },
                        "message": f"Successfully retrieved {len(live_algorithms)} live algorithms",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to list live algorithms",
                        "details": errors,
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
                "error": f"Failed to list live algorithms: {str(e)}",
            }

    @mcp.tool()
    async def read_live_logs(
        project_id: int,
        algorithm_id: str,
        start_line: int,
        end_line: int,
        format: str = "json",
    ) -> Dict[str, Any]:
        """
        Read logs from a live algorithm.

        Args:
            project_id: Project ID of the live running algorithm
            algorithm_id: Deploy ID (Algorithm ID) of the live running algorithm
            start_line: Start line of logs to read
            end_line: End line of logs to read (difference must be < 250)
            format: Format of log results (default: "json")

        Returns:
            Dictionary containing live algorithm logs
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        # Validate line range
        if end_line <= start_line:
            return {
                "status": "error",
                "error": "end_line must be greater than start_line",
            }

        if end_line - start_line >= 250:
            return {
                "status": "error",
                "error": "Line range too large: difference between start_line and end_line must be less than 250",
            }

        if start_line < 0 or end_line < 0:
            return {
                "status": "error",
                "error": "start_line and end_line must be non-negative",
            }

        try:
            # Prepare request data
            request_data = {
                "format": format,
                "projectId": project_id,
                "algorithmId": algorithm_id,
                "startLine": start_line,
                "endLine": end_line,
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="live/logs/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    logs = data.get("logs", [])
                    length = data.get("length", 0)
                    deployment_offset = data.get("deploymentOffset", 0)
                    
                    return {
                        "status": "success",
                        "project_id": project_id,
                        "algorithm_id": algorithm_id,
                        "start_line": start_line,
                        "end_line": end_line,
                        "logs": logs,
                        "length": length,
                        "deployment_offset": deployment_offset,
                        "format": format,
                        "message": f"Successfully retrieved {len(logs)} log lines from live algorithm {algorithm_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read live algorithm logs",
                        "details": errors,
                        "project_id": project_id,
                        "algorithm_id": algorithm_id,
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
                "error": f"Failed to read live algorithm logs: {str(e)}",
                "project_id": project_id,
                "algorithm_id": algorithm_id,
                "start_line": start_line,
                "end_line": end_line,
            }
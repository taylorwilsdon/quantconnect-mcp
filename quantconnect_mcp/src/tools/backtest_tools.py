"""Backtest Management Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, Optional
from ..auth.quantconnect_auth import get_auth_instance  # type: ignore


def register_backtest_tools(mcp: FastMCP):
    """Register backtest management tools with the MCP server."""

    @mcp.tool()
    async def create_backtest(
        project_id: int,
        compile_id: str,
        backtest_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new backtest for a compiled project.

        Args:
            project_id: ID of the project to backtest
            compile_id: Compile ID from a successful project compilation
            backtest_name: Name for the backtest
            parameters: Optional dictionary of parameters for the backtest (e.g., {"ema_fast": 10, "ema_slow": 100})

        Returns:
            Dictionary containing backtest creation result and backtest details
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
                "backtestName": backtest_name,
            }

            # Add parameters if provided
            if parameters:
                for key, value in parameters.items():
                    request_data[f"parameters[{key}]"] = value

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="backtests/create", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    backtest_results = data.get("backtest", [])
                    debugging = data.get("debugging", False)

                    if backtest_results:
                        backtest = backtest_results[0]
                        return {
                            "status": "success",
                            "project_id": project_id,
                            "compile_id": compile_id,
                            "backtest_name": backtest_name,
                            "backtest": backtest,
                            "debugging": debugging,
                            "message": f"Successfully created backtest '{backtest_name}' for project {project_id}",
                        }
                    else:
                        return {
                            "status": "success",
                            "project_id": project_id,
                            "compile_id": compile_id,
                            "backtest_name": backtest_name,
                            "debugging": debugging,
                            "message": f"Backtest '{backtest_name}' created but no results yet",
                            "note": "Backtest may still be initializing",
                        }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    if any("Compile id not found" in e for e in errors):
                        return {
                            "status": "error",
                            "error": "Compile ID not found. Please compile the project first using the 'compile_project' tool.",
                            "details": errors,
                            "project_id": project_id,
                            "compile_id": compile_id,
                        }
                    return {
                        "status": "error",
                        "error": "Backtest creation failed",
                        "details": errors,
                        "project_id": project_id,
                        "compile_id": compile_id,
                        "backtest_name": backtest_name,
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
                "error": f"Failed to create backtest: {str(e)}",
                "project_id": project_id,
                "compile_id": compile_id,
                "backtest_name": backtest_name,
            }

    @mcp.tool()
    async def read_backtest(
        project_id: int, backtest_id: str, chart: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Read backtest results and statistics from a project.

        Args:
            project_id: ID of the project containing the backtest
            backtest_id: ID of the specific backtest to read
            chart: Optional chart name to include chart data in response

        Returns:
            Dictionary containing backtest results, statistics, and optional chart data
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {"projectId": project_id, "backtestId": backtest_id}

            # Add chart parameter if provided
            if chart is not None:
                request_data["chart"] = chart

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="backtests/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    backtest_results = data.get("backtest", [])
                    debugging = data.get("debugging", False)

                    if backtest_results:
                        backtest = backtest_results[0]
                        return {
                            "status": "success",
                            "project_id": project_id,
                            "backtest_id": backtest_id,
                            "backtest": backtest,
                            "debugging": debugging,
                            "chart_included": chart is not None,
                            "message": f"Successfully read backtest {backtest_id} from project {project_id}",
                        }
                    else:
                        return {
                            "status": "error",
                            "error": f"Backtest {backtest_id} not found in project {project_id}",
                        }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read backtest",
                        "details": errors,
                        "project_id": project_id,
                        "backtest_id": backtest_id,
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
                "error": f"Failed to read backtest: {str(e)}",
                "project_id": project_id,
                "backtest_id": backtest_id,
            }

    @mcp.tool()
    async def read_backtest_chart(
        project_id: int,
        backtest_id: str,
        name: str,
        count: int = 100,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Read chart data from a backtest.

        Args:
            project_id: Project ID containing the backtest
            backtest_id: ID of the backtest to get chart from
            name: Name of the chart to retrieve (e.g., "Strategy Equity")
            count: Number of data points to request (default: 100)
            start: Optional UTC start timestamp in seconds
            end: Optional UTC end timestamp in seconds

        Returns:
            Dictionary containing chart data or loading status
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
                "backtestId": backtest_id,
                "name": name,
                "count": count,
            }

            # Add optional timestamp parameters
            if start is not None:
                request_data["start"] = start
            if end is not None:
                request_data["end"] = end

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="backtests/chart/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    # Check if chart is still loading
                    if "progress" in data and "status" in data:
                        progress = data.get("progress", 0)
                        status = data.get("status", "loading")
                        return {
                            "status": "loading",
                            "project_id": project_id,
                            "backtest_id": backtest_id,
                            "chart_name": name,
                            "progress": progress,
                            "chart_status": status,
                            "message": f"Chart '{name}' is loading... ({progress * 100:.1f}% complete)",
                        }

                    # Chart is ready
                    elif "chart" in data:
                        chart = data.get("chart")
                        return {
                            "status": "success",
                            "project_id": project_id,
                            "backtest_id": backtest_id,
                            "chart_name": name,
                            "chart": chart,
                            "count": count,
                            "start": start,
                            "end": end,
                            "message": f"Successfully retrieved chart '{name}' from backtest {backtest_id}",
                        }

                    else:
                        return {
                            "status": "error",
                            "error": "Unexpected response format - no chart or progress data found",
                        }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read backtest chart",
                        "details": errors,
                        "project_id": project_id,
                        "backtest_id": backtest_id,
                        "chart_name": name,
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
                "error": f"Failed to read backtest chart: {str(e)}",
                "project_id": project_id,
                "backtest_id": backtest_id,
                "chart_name": name,
            }

    @mcp.tool()
    async def read_backtest_orders(
        project_id: int, backtest_id: str, start: int = 0, end: int = 100
    ) -> Dict[str, Any]:
        """
        Read orders from a backtest.

        Args:
            project_id: ID of the project containing the backtest
            backtest_id: ID of the backtest to read orders from
            start: Starting index of orders to fetch (default: 0)
            end: Last index of orders to fetch (default: 100, max range: 100)

        Returns:
            Dictionary containing orders data and total count
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        # Validate range
        if end - start > 100:
            return {
                "status": "error",
                "error": "Range too large: end - start must be less than or equal to 100",
            }

        if start < 0 or end < 0:
            return {
                "status": "error",
                "error": "Start and end indices must be non-negative",
            }

        if start >= end:
            return {
                "status": "error",
                "error": "Start index must be less than end index",
            }

        try:
            # Prepare request data
            request_data = {
                "projectId": project_id,
                "backtestId": backtest_id,
                "start": start,
                "end": end,
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="backtests/orders/read", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                # Note: This API doesn't appear to have a "success" field based on the spec
                orders = data.get("orders", {})
                length = data.get("length", 0)

                return {
                    "status": "success",
                    "project_id": project_id,
                    "backtest_id": backtest_id,
                    "start": start,
                    "end": end,
                    "orders": orders,
                    "length": length,
                    "message": f"Successfully retrieved {length} orders from backtest {backtest_id} (range: {start}-{end})",
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
                "error": f"Failed to read backtest orders: {str(e)}",
                "project_id": project_id,
                "backtest_id": backtest_id,
                "start": start,
                "end": end,
            }

    @mcp.tool()
    async def read_backtest_insights(
        project_id: int, backtest_id: str, start: int = 0, end: int = 100
    ) -> Dict[str, Any]:
        """
        Read insights from a backtest.

        Args:
            project_id: ID of the project containing the backtest
            backtest_id: ID of the backtest to read insights from
            start: Starting index of insights to fetch (default: 0)
            end: Last index of insights to fetch (default: 100, max range: 100)

        Returns:
            Dictionary containing insights data and total count
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        # Validate range
        if end - start > 100:
            return {
                "status": "error",
                "error": "Range too large: end - start must be less than or equal to 100",
            }

        if start < 0 or end < 0:
            return {
                "status": "error",
                "error": "Start and end indices must be non-negative",
            }

        if start >= end:
            return {
                "status": "error",
                "error": "Start index must be less than end index",
            }

        try:
            # Prepare request data
            request_data = {
                "projectId": project_id,
                "backtestId": backtest_id,
                "start": start,
                "end": end,
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="backtests/read/insights", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    insights = data.get("insights", [])
                    length = data.get("length", 0)

                    return {
                        "status": "success",
                        "project_id": project_id,
                        "backtest_id": backtest_id,
                        "start": start,
                        "end": end,
                        "insights": insights,
                        "length": length,
                        "message": f"Successfully retrieved {length} insights from backtest {backtest_id} (range: {start}-{end})",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read backtest insights",
                        "details": errors,
                        "project_id": project_id,
                        "backtest_id": backtest_id,
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
                "error": f"Failed to read backtest insights: {str(e)}",
                "project_id": project_id,
                "backtest_id": backtest_id,
                "start": start,
                "end": end,
            }

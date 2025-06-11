"""System Information Resources for QuantConnect MCP Server"""

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError
import platform
import os
import psutil
from datetime import datetime
from typing import Dict, Any


def register_system_resources(mcp: FastMCP):
    """Register system information resources with the MCP server."""

    @mcp.resource("resource://system/info")
    async def system_info() -> Dict[str, Any]:
        """Get comprehensive system information."""
        return {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage("/").total,
                "used": psutil.disk_usage("/").used,
                "free": psutil.disk_usage("/").free,
            },
            "timestamp": datetime.now().isoformat(),
        }

    @mcp.resource("resource://quantconnect/server/status")
    async def server_status() -> Dict[str, Any]:
        """Get QuantConnect MCP server status and statistics."""
        from ..tools.quantbook_tools import _quantbook_instances  # type: ignore

        # Count active QuantBook instances
        active_instances = len(_quantbook_instances)

        # Get instance details
        instance_details = {}
        for name, qb in _quantbook_instances.items():
            try:
                securities_count = (
                    len(qb.Securities) if hasattr(qb, "Securities") else 0
                )
                instance_details[name] = {
                    "type": str(type(qb).__name__),
                    "securities_count": securities_count,
                    "status": "active",
                }
            except Exception as e:
                instance_details[name] = {"status": "error", "error": str(e)}

        return {
            "server_name": "QuantConnect MCP Server",
            "status": "running",
            "active_quantbook_instances": active_instances,
            "instance_details": instance_details,
            "available_tools": [
                "QuantBook Management",
                "Data Retrieval",
                "Statistical Analysis",
                "Portfolio Optimization",
                "Universe Selection",
            ],
            "timestamp": datetime.now().isoformat(),
        }

    @mcp.resource("resource://quantconnect/tools/summary")
    async def tools_summary() -> Dict[str, Any]:
        """Get summary of available QuantConnect tools."""
        return {
            "quantbook_tools": {
                "description": "QuantBook instance management and initialization",
                "tools": [
                    "initialize_quantbook",
                    "list_quantbook_instances",
                    "get_quantbook_info",
                    "remove_quantbook_instance",
                ],
            },
            "data_tools": {
                "description": "Data retrieval and management",
                "tools": [
                    "add_equity",
                    "add_multiple_equities",
                    "get_history",
                    "add_alternative_data",
                    "get_alternative_data_history",
                ],
            },
            "analysis_tools": {
                "description": "Statistical analysis and research",
                "tools": [
                    "perform_pca_analysis",
                    "test_cointegration",
                    "analyze_mean_reversion",
                    "calculate_correlation_matrix",
                ],
            },
            "portfolio_tools": {
                "description": "Portfolio optimization and performance analysis",
                "tools": [
                    "sparse_optimization",
                    "calculate_portfolio_performance",
                    "optimize_equal_weight_portfolio",
                ],
            },
            "universe_tools": {
                "description": "Universe selection and asset screening",
                "tools": [
                    "get_etf_constituents",
                    "add_etf_universe_securities",
                    "select_uncorrelated_assets",
                    "screen_assets_by_criteria",
                ],
            },
            "total_tools": 19,
            "timestamp": datetime.now().isoformat(),
        }

    @mcp.resource("resource://system/processes/{limit}")
    async def top_processes(limit: str) -> list:
        """Get top N processes by CPU usage."""
        try:
            n = int(limit)
            if n <= 0 or n > 100:
                raise ResourceError("Limit must be between 1 and 100")

            processes = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
                try:
                    processes.append(proc.info)
                except psutil.NoSuchProcess:
                    pass

            # Sort by CPU usage and return top N
            processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
            return processes[:n]

        except ValueError:
            raise ResourceError(f"Invalid limit: {limit}")

    @mcp.resource("resource://quantconnect/performance/metrics")
    async def performance_metrics() -> Dict[str, Any]:
        """Get server performance metrics."""
        return {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": {
                "percent": psutil.virtual_memory().percent,
                "used_gb": psutil.virtual_memory().used / (1024**3),
                "available_gb": psutil.virtual_memory().available / (1024**3),
            },
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else None,
            "active_connections": len(psutil.net_connections()),
            "uptime_seconds": datetime.now().timestamp() - psutil.boot_time(),
            "timestamp": datetime.now().isoformat(),
        }

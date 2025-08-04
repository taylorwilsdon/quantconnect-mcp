"""QuantBook Management Tools for QuantConnect MCP Server (Container-Based)

CRITICAL FOR LLMs - HOW TO EXECUTE QUANTBOOK CODE:
- DO NOT execute standalone Python scripts - qb won't be available!
- INSTEAD: Modify the existing /LeanCLI/research.ipynb notebook file
- qb is ONLY available in Jupyter notebooks with Foundation-Py-Default kernel

CORRECT WORKFLOW for execute_quantbook_code:
1. Read the existing /LeanCLI/research.ipynb file
2. Add your code as a new cell to the notebook
3. Execute the notebook to get results
4. qb will be available automatically in the notebook

ENVIRONMENT NOTES:
- Research notebooks are located at /LeanCLI in the container
- A default starter notebook 'research.ipynb' is automatically created
- QuantBook is pre-initialized and available as 'qb' in all notebooks
- When creating new notebooks, they MUST use the 'Foundation-Py-Default' kernel
"""

import asyncio
from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import json
import logging

from ..adapters import (
    SessionManager,
    ResearchSession,
    get_session_manager,
    initialize_session_manager,
)

logger = logging.getLogger(__name__)


def register_quantbook_tools(mcp: FastMCP):
    """Register QuantBook management tools with the MCP server."""

    @mcp.tool()
    async def initialize_quantbook(
        instance_name: str = "default",
        organization_id: Optional[str] = None,
        token: Optional[str] = None,
        memory_limit: str = "2g",
        cpu_limit: float = 1.0,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        Initialize a new QuantBook instance in a Docker container for research operations.

        IMPORTANT: Research notebooks are located at /LeanCLI in the container.
        - A default starter notebook 'research.ipynb' is automatically created
        - QuantBook is pre-initialized and available as 'qb' in all notebooks
        - When creating new notebooks, they MUST use the 'Foundation-Py-Default' kernel to have qb access

        Args:
            instance_name: Name identifier for this QuantBook instance
            organization_id: Optional organization ID for QuantConnect (not used in container)
            token: Optional API token for QuantConnect (not used in container)
            memory_limit: Container memory limit (e.g., "2g", "512m")
            cpu_limit: Container CPU limit (fraction of CPU, e.g. 1.0 = 1 CPU)
            timeout: Default execution timeout in seconds

        Returns:
            Dictionary containing initialization status and instance info
        """
        try:
            # Initialize session manager if needed
            await initialize_session_manager()
            manager = get_session_manager()

            # Create or get research session
            # Note: lean-cli manages memory and CPU limits internally
            session = await manager.get_or_create_session(
                session_id=instance_name,
                # Only pass supported parameters for lean-cli based session
                port=None,  # Will use default or env var
            )

            # Initialize the session and wait for container to be ready
            await session.initialize()

            # Check if session initialized successfully
            if not session._initialized:
                return {
                    "status": "error",
                    "error": "Failed to initialize research session",
                    "message": f"Failed to initialize QuantBook instance '{instance_name}'",
                }

            # Try a simple test to see if we can detect the container is ready
            # But don't execute complex QuantBook code during initialization
            try:
                test_result = await session.execute("print('Container ready')", timeout=10)
                container_ready = test_result["status"] == "success"
            except Exception:
                container_ready = False

            if container_ready:
                return {
                    "status": "success",
                    "instance_name": instance_name,
                    "session_id": session.session_id,
                    "message": f"QuantBook instance '{instance_name}' initialized successfully in container",
                    "container_info": {
                        "memory_limit": memory_limit,
                        "cpu_limit": cpu_limit,
                        "timeout": timeout,
                        "workspace": str(session.workspace_dir),
                        "port": session.port,
                    },
                    "usage_instructions": {
                        "CRITICAL": "To use QuantBook functions, the first line in a cell should be qb = QuantBook()",
                        "DO": "Use qb directly: equity = qb.AddEquity('AAPL')",
                        "example": "equity = qb.AddEquity('AAPL')\nhistory = qb.History(equity.Symbol, 10, Resolution.Daily)",
                        "notebook_location": "/LeanCLI - where research.ipynb is located",
                        "kernel": "Use 'Foundation-Py-Default' kernel for new notebooks"
                    }
                }
            else:
                # Container is still starting up, but session was created successfully
                return {
                    "status": "success",
                    "instance_name": instance_name,
                    "session_id": session.session_id,
                    "message": f"QuantBook instance '{instance_name}' is starting up. Jupyter Lab will be available at http://localhost:{session.port}",
                    "container_info": {
                        "memory_limit": memory_limit,
                        "cpu_limit": cpu_limit,
                        "timeout": timeout,
                        "workspace": str(session.workspace_dir),
                        "port": session.port,
                    },
                    "note": "Container is still starting. You can check the web interface or try executing code in a few seconds.",
                    "usage_instructions": {
                        "CRITICAL": "To use QuantBook functions, the first line in a cell should be qb = QuantBook()",
                        "DO": "Use qb directly: equity = qb.AddEquity('AAPL')",
                        "example": "equity = qb.AddEquity('AAPL')\nhistory = qb.History(equity.Symbol, 10, Resolution.Daily)",
                        "notebook_location": "/LeanCLI - where research.ipynb is located",
                        "kernel": "Use 'Foundation-Py-Default' kernel for new notebooks"
                    }
                }

        except Exception as e:
            logger.error(
                f"Failed to initialize QuantBook instance '{instance_name}': {e}"
            )
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to initialize QuantBook instance '{instance_name}'",
            }

    @mcp.tool()
    async def list_quantbook_instances() -> Dict[str, Any]:
        """
        List all active QuantBook instances.

        Returns:
            Dictionary containing all active QuantBook instances
        """
        try:
            manager = get_session_manager()
            sessions = manager.list_sessions()
            session_count = manager.get_session_count()

            return {
                "instances": [s["session_id"] for s in sessions],
                "count": len(sessions),
                "session_details": sessions,
                "capacity": session_count,
                "status": "success",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to list QuantBook instances",
            }

    @mcp.tool()
    async def get_quantbook_info(instance_name: str = "default") -> Dict[str, Any]:
        """
        Get information about a specific QuantBook instance.

        Args:
            instance_name: Name of the QuantBook instance

        Returns:
            Dictionary containing instance information
        """
        try:
            manager = get_session_manager()
            session = await manager.get_session(instance_name)

            if session is None:
                available_sessions = [s["session_id"] for s in manager.list_sessions()]
                return {
                    "status": "error",
                    "error": f"QuantBook instance '{instance_name}' not found",
                    "available_instances": available_sessions,
                }

            # Get QuantBook info from container
            info_code = """
            try:
                # Get securities count
                securities_count = len(qb.Securities) if hasattr(qb, 'Securities') else 0

                # Get available methods
                available_methods = [method for method in dir(qb) if not method.startswith('_')]

                print(f"Securities count: {securities_count}")
                print(f"Available methods: {len(available_methods)}")
                print(f"QuantBook type: {type(qb).__name__}")

                # Store results for JSON return
                qb_info = {
                    'securities_count': securities_count,
                    'available_methods': available_methods[:50],  # Limit to first 50 methods
                    'total_methods': len(available_methods),
                    'type': type(qb).__name__
                }

            except Exception as e:
                print(f"Error getting QuantBook info: {e}")
                qb_info = {
                    'error': str(e),
                    'securities_count': 0,
                    'available_methods': [],
                    'total_methods': 0,
                    'type': 'Unknown'
                }
            """

            result = await session.execute(info_code)

            # Handle case where container is still starting
            if result["status"] == "error" and "Container not found" in result.get(
                "error", ""
            ):
                return {
                    "status": "success",
                    "instance_name": instance_name,
                    "session_id": session.session_id,
                    "container_info": {
                        "created_at": session.created_at.isoformat(),
                        "last_used": session.last_used.isoformat(),
                        "port": session.port,
                        "workspace": str(session.workspace_dir),
                        "initialized": session._initialized,
                        "jupyter_url": f"http://localhost:{session.port}",
                    },
                    "message": "Container is still starting up. Jupyter Lab should be available soon.",
                    "note": result.get("message", ""),
                }

            return {
                "status": "success",
                "instance_name": instance_name,
                "session_id": session.session_id,
                "container_info": {
                    "created_at": session.created_at.isoformat(),
                    "last_used": session.last_used.isoformat(),
                    "port": session.port,
                    "workspace": str(session.workspace_dir),
                    "initialized": session._initialized,
                },
                "execution_result": result,
            }

        except Exception as e:
            logger.error(
                f"Failed to get info for QuantBook instance '{instance_name}': {e}"
            )
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to get info for QuantBook instance '{instance_name}'",
            }

    @mcp.tool()
    async def check_quantbook_container(
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Check if the container for a QuantBook instance is running.

        Args:
            instance_name: Name of the QuantBook instance

        Returns:
            Dictionary containing container status
        """
        try:
            manager = get_session_manager()
            session = await manager.get_session(instance_name)

            if session is None:
                available_sessions = [s["session_id"] for s in manager.list_sessions()]
                return {
                    "status": "error",
                    "error": f"QuantBook instance '{instance_name}' not found",
                    "available_instances": available_sessions,
                }

            # Try to find the container
            await session._find_container()

            return {
                "status": "success",
                "instance_name": instance_name,
                "container_found": session.container is not None,
                "container_name": session.container.name if session.container else None,
                "port": session.port,
                "jupyter_url": f"http://localhost:{session.port}",
                "message": (
                    "Container is running"
                    if session.container
                    else "Container not yet found - may still be starting"
                ),
            }

        except Exception as e:
            logger.error(
                f"Failed to check container for instance '{instance_name}': {e}"
            )
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to check container for instance '{instance_name}'",
            }

    @mcp.tool()
    async def remove_quantbook_instance(instance_name: str) -> Dict[str, Any]:
        """
        Remove a QuantBook instance and clean up its container.

        Args:
            instance_name: Name of the QuantBook instance to remove

        Returns:
            Dictionary containing removal status
        """
        try:
            manager = get_session_manager()
            success = await manager.close_session(instance_name)

            if not success:
                available_sessions = [s["session_id"] for s in manager.list_sessions()]
                return {
                    "status": "error",
                    "error": f"QuantBook instance '{instance_name}' not found",
                    "available_instances": available_sessions,
                }

            remaining_sessions = [s["session_id"] for s in manager.list_sessions()]
            return {
                "status": "success",
                "message": f"QuantBook instance '{instance_name}' removed successfully",
                "remaining_instances": remaining_sessions,
            }

        except Exception as e:
            logger.error(f"Failed to remove QuantBook instance '{instance_name}': {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to remove QuantBook instance '{instance_name}'",
            }

    @mcp.tool()
    async def execute_quantbook_code(
        code: str,
        instance_name: str = "default",
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute Python code in a QuantBook container.

        IMPORTANT: This function should modify and execute code in /LeanCLI/research.ipynb

        The LLM should:
        1. Read the existing /LeanCLI/research.ipynb file
        2. Add the code as a new cell to the notebook
        3. Execute the notebook cell
        4. Return the results

        QuantBook (qb) is ONLY available inside Jupyter notebooks with Foundation-Py-Default kernel!
        DO NOT try to execute standalone Python scripts - they won't have access to qb.

        Example workflow:
        1. Read /LeanCLI/research.ipynb
        2. Add cell with: equity = qb.AddEquity("AAPL")
        3. Execute the notebook
        4. Return results

        Args:
            code: Python code to add to research.ipynb and execute
            instance_name: Name of the QuantBook instance
            timeout: Execution timeout in seconds (uses session default if None)

        Returns:
            Dictionary containing execution results
        """
        try:
            manager = get_session_manager()
            session = await manager.get_session(instance_name)

            if session is None:
                available_sessions = [s["session_id"] for s in manager.list_sessions()]
                return {
                    "status": "error",
                    "error": f"QuantBook instance '{instance_name}' not found",
                    "available_instances": available_sessions,
                    "message": "Initialize a QuantBook instance first using initialize_quantbook",
                }

            # Execute the code
            result = await session.execute(code, timeout=timeout)
            result["instance_name"] = instance_name

            return result

        except Exception as e:
            logger.error(
                f"Failed to execute code in QuantBook instance '{instance_name}': {e}"
            )
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to execute code in QuantBook instance '{instance_name}'",
                "instance_name": instance_name,
            }

    @mcp.tool()
    async def get_session_manager_status() -> Dict[str, Any]:
        """
        Get status information about the session manager.

        Returns:
            Dictionary containing session manager status
        """
        try:
            manager = get_session_manager()
            session_count = manager.get_session_count()
            sessions = manager.list_sessions()

            return {
                "status": "success",
                "running": manager._running,
                "session_count": session_count,
                "sessions": sessions,
                "configuration": {
                    "max_sessions": manager.max_sessions,
                    "session_timeout_hours": manager.session_timeout.total_seconds()
                    / 3600,
                    "cleanup_interval_seconds": manager.cleanup_interval,
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to get session manager status",
            }


async def get_quantbook_session(
    instance_name: str = "default",
) -> Optional[ResearchSession]:
    """
    Helper function to get QuantBook session for other tools.

    Args:
        instance_name: Name of the QuantBook instance

    Returns:
        ResearchSession instance or None if not found
    """
    try:
        manager = get_session_manager()
        return await manager.get_session(instance_name)
    except Exception as e:
        logger.error(f"Failed to get QuantBook session '{instance_name}': {e}")
        return None


def get_quantbook_instance(instance_name: str = "default"):
    """
    Legacy compatibility function for get_quantbook_instance.
    Returns None since the old synchronous API is no longer supported.

    This function exists to prevent import errors but will return None,
    causing tools that depend on it to fail gracefully.
    """
    logger.warning(
        f"get_quantbook_instance is deprecated and no longer functional. Use get_quantbook_session instead."
    )
    return None

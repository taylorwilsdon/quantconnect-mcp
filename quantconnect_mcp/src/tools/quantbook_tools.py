"""QuantBook Management Tools for QuantConnect MCP Server (Container-Based)"""

import asyncio
from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import json
import logging

from ..adapters import SessionManager, ResearchSession, get_session_manager, initialize_session_manager

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
            session = await manager.get_or_create_session(
                session_id=instance_name,
                memory_limit=memory_limit,
                cpu_limit=cpu_limit,
                timeout=timeout,
            )

            # Initialize QuantBook in the container (like lean-cli)
            init_code = """
# Import necessary modules
import pandas as pd
import numpy as np
import sys
import os

# Set up LEAN environment
sys.path.append('/Lean')

try:
    from QuantConnect.Research import QuantBook
    from QuantConnect import *
    
    # Create global QuantBook instance
    qb = QuantBook()
    print(f"QuantBook initialized successfully in LEAN environment")
    print(f"Available methods: {len([m for m in dir(qb) if not m.startswith('_')]):d}")
    print(f"LEAN modules loaded: QuantConnect available")
except ImportError as e:
    print(f"Warning: LEAN modules not fully available: {e}")
    print("Basic Python environment ready (pandas, numpy)")
    qb = None
"""

            result = await session.execute(init_code)
            
            if result["status"] != "success":
                return {
                    "status": "error",
                    "error": result.get("error", "Unknown error"),
                    "message": f"Failed to initialize QuantBook in container for instance '{instance_name}'",
                }

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
                },
                "output": result.get("output", ""),
            }

        except Exception as e:
            logger.error(f"Failed to initialize QuantBook instance '{instance_name}': {e}")
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
            
            return {
                "status": "success",
                "instance_name": instance_name,
                "session_id": session.session_id,
                "container_info": {
                    "created_at": session.created_at.isoformat(),
                    "last_used": session.last_used.isoformat(),
                    "memory_limit": session.memory_limit,
                    "cpu_limit": session.cpu_limit,
                    "workspace": str(session.workspace_dir),
                },
                "execution_result": result,
            }

        except Exception as e:
            logger.error(f"Failed to get info for QuantBook instance '{instance_name}': {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to get info for QuantBook instance '{instance_name}'",
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
        Execute arbitrary Python code in a QuantBook container.

        Args:
            code: Python code to execute
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
            logger.error(f"Failed to execute code in QuantBook instance '{instance_name}': {e}")
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
                    "session_timeout_hours": manager.session_timeout.total_seconds() / 3600,
                    "cleanup_interval_seconds": manager.cleanup_interval,
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to get session manager status",
            }


async def get_quantbook_session(instance_name: str = "default") -> Optional[ResearchSession]:
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
    logger.warning(f"get_quantbook_instance is deprecated and no longer functional. Use get_quantbook_session instead.")
    return None
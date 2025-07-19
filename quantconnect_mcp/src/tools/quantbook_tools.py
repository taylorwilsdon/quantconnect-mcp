"""QuantBook Management Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import json

# Global QuantBook instance storage
_quantbook_instances: Dict[str, Any] = {}


def register_quantbook_tools(mcp: FastMCP):
    """Register QuantBook management tools with the MCP server."""

    @mcp.tool()
    async def initialize_quantbook(
        instance_name: str = "default",
        organization_id: Optional[str] = None,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initialize a new QuantBook instance for research operations.

        Args:
            instance_name: Name identifier for this QuantBook instance
            organization_id: Optional organization ID for QuantConnect
            token: Optional API token for QuantConnect

        Returns:
            Dictionary containing initialization status and instance info
        """
        try:
            # Import QuantConnect modules
            from QuantConnect.Research import QuantBook  # type: ignore

            # Create new QuantBook instance
            qb = QuantBook()

            # Store the instance
            _quantbook_instances[instance_name] = qb

            return {
                "status": "success",
                "instance_name": instance_name,
                "message": f"QuantBook instance '{instance_name}' initialized successfully",
                "available_instances": list(_quantbook_instances.keys()),
            }

        except ImportError as e:
            return {
                "status": "error",
                "error": f"Failed to import QuantConnect modules: {str(e)}",
                "message": "Ensure QuantConnect LEAN is properly installed",
            }
        except Exception as e:
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
        return {
            "instances": list(_quantbook_instances.keys()),
            "count": len(_quantbook_instances),
            "status": "success",
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
        if instance_name not in _quantbook_instances:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
                "available_instances": list(_quantbook_instances.keys()),
            }

        try:
            qb = _quantbook_instances[instance_name]

            # Get basic info about the instance
            securities_count = len(qb.Securities) if hasattr(qb, "Securities") else 0

            return {
                "status": "success",
                "instance_name": instance_name,
                "securities_count": securities_count,
                "type": str(type(qb).__name__),
                "available_methods": [
                    method for method in dir(qb) if not method.startswith("_")
                ],
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to get info for QuantBook instance '{instance_name}'",
            }

    @mcp.tool()
    async def remove_quantbook_instance(instance_name: str) -> Dict[str, Any]:
        """
        Remove a QuantBook instance from memory.

        Args:
            instance_name: Name of the QuantBook instance to remove

        Returns:
            Dictionary containing removal status
        """
        if instance_name not in _quantbook_instances:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
                "available_instances": list(_quantbook_instances.keys()),
            }

        try:
            del _quantbook_instances[instance_name]
            return {
                "status": "success",
                "message": f"QuantBook instance '{instance_name}' removed successfully",
                "remaining_instances": list(_quantbook_instances.keys()),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to remove QuantBook instance '{instance_name}'",
            }


def get_quantbook_instance(instance_name: str = "default"):
    """Helper function to get QuantBook instance for other tools."""
    return _quantbook_instances.get(instance_name)

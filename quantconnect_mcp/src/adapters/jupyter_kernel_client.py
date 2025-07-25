"""Jupyter Kernel Client for executing code in research containers."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class JupyterKernelClient:
    """Client for interacting with Jupyter kernels via REST API."""
    
    def __init__(self, base_url: str):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of Jupyter server (e.g., http://localhost:8888)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.kernel_id: Optional[str] = None
    
    async def list_kernels(self) -> list:
        """List all running kernels."""
        try:
            response = await self.client.get(f"{self.base_url}/api/kernels")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list kernels: {e}")
            return []
    
    async def create_kernel(self) -> Optional[str]:
        """Create a new kernel and return its ID."""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/kernels",
                json={"name": "python3"}
            )
            response.raise_for_status()
            kernel_info = response.json()
            self.kernel_id = kernel_info["id"]
            logger.info(f"Created kernel: {self.kernel_id}")
            return self.kernel_id
        except Exception as e:
            logger.error(f"Failed to create kernel: {e}")
            return None
    
    async def get_or_create_kernel(self) -> Optional[str]:
        """Get existing kernel or create a new one."""
        # First check if we have a kernel
        if self.kernel_id:
            # Verify it's still running
            kernels = await self.list_kernels()
            if any(k["id"] == self.kernel_id for k in kernels):
                return self.kernel_id
        
        # Check for existing kernels
        kernels = await self.list_kernels()
        if kernels:
            # Use the first available kernel
            self.kernel_id = kernels[0]["id"]
            logger.info(f"Using existing kernel: {self.kernel_id}")
            return self.kernel_id
        
        # Create new kernel
        return await self.create_kernel()
    
    async def execute_code(self, code: str) -> Dict[str, Any]:
        """
        Execute code in the kernel.
        
        Args:
            code: Python code to execute
            
        Returns:
            Dictionary with execution results
        """
        kernel_id = await self.get_or_create_kernel()
        if not kernel_id:
            return {
                "status": "error",
                "error": "Failed to get or create kernel",
                "output": ""
            }
        
        # Create execution request
        msg_id = str(uuid.uuid4())
        
        # Connect to WebSocket for kernel communication
        ws_url = f"{self.base_url.replace('http', 'ws')}/api/kernels/{kernel_id}/channels"
        
        try:
            # For now, use a simpler approach - execute via container
            # This is a placeholder for full WebSocket implementation
            logger.warning("WebSocket execution not yet implemented, falling back to container exec")
            return {
                "status": "error",
                "error": "Jupyter kernel execution not yet implemented",
                "output": ""
            }
            
        except Exception as e:
            logger.error(f"Failed to execute code: {e}")
            return {
                "status": "error",
                "error": str(e),
                "output": ""
            }
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()
"""QuantConnect Research Session with Jupyter Kernel Support"""

import asyncio
import json
import logging
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import docker
import docker.types
import pandas as pd
from docker.models.containers import Container

from .logging_config import get_container_logger, security_logger

logger = logging.getLogger(__name__)


class JupyterResearchSession:
    """
    Enhanced Research Session that attempts to use Jupyter kernel if available.
    Falls back to direct Python execution if kernel is not ready.
    """
    
    IMAGE = "quantconnect/research:latest"
    CONTAINER_WORKSPACE = "/Lean"
    NOTEBOOKS_PATH = "/Lean/Notebooks"
    TIMEOUT_DEFAULT = 300  # 5 minutes
    KERNEL_WAIT_TIME = 60  # Maximum time to wait for kernel
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        workspace_dir: Optional[Path] = None,
        memory_limit: str = "2g",
        cpu_limit: float = 1.0,
        timeout: int = TIMEOUT_DEFAULT,
    ):
        """Initialize a new research session."""
        self.session_id = session_id or f"qb_{uuid.uuid4().hex[:8]}"
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.timeout = timeout
        self.created_at = datetime.utcnow()
        self.last_used = self.created_at
        self.kernel_ready = False
        self.kernel_name = None
        
        # Setup workspace
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
            self.workspace_dir.mkdir(parents=True, exist_ok=True)
            self._temp_dir = None
        else:
            self._temp_dir = tempfile.TemporaryDirectory(prefix=f"qc_research_{self.session_id}_")
            self.workspace_dir = Path(self._temp_dir.name)
        
        # Docker client and container
        self.client = docker.from_env()
        self.container: Optional[Container] = None
        self._initialized = False
        
        logger.info(f"Created Jupyter research session {self.session_id}")
    
    async def initialize(self) -> None:
        """Initialize the Docker container and wait for Jupyter kernel."""
        if self._initialized:
            return
        
        try:
            # Ensure the image is available
            try:
                self.client.images.get(self.IMAGE)
            except docker.errors.ImageNotFound:
                logger.info(f"Pulling image {self.IMAGE}...")
                self.client.images.pull(self.IMAGE)
            
            # Start container with Jupyter environment
            volumes = {
                str(self.workspace_dir): {
                    "bind": self.NOTEBOOKS_PATH,
                    "mode": "rw"
                }
            }
            
            environment = {
                "PYTHONPATH": "/Lean:/Lean/Library",
                "COMPOSER_DLL_DIRECTORY": "/Lean",
            }
            
            # Start the container
            self.container = self.client.containers.run(
                self.IMAGE,
                command=["sleep", "infinity"],  # Keep container running
                volumes=volumes,
                environment=environment,
                working_dir=self.NOTEBOOKS_PATH,
                detach=True,
                mem_limit=self.memory_limit,
                cpu_period=100000,
                cpu_quota=int(100000 * self.cpu_limit),
                name=f"qc_jupyter_{self.session_id}",
                remove=True,
                labels={
                    "mcp.quantconnect.session_id": self.session_id,
                    "mcp.quantconnect.created_at": self.created_at.isoformat(),
                },
            )
            
            # Wait for container to be ready
            await asyncio.sleep(3)
            
            # Check for Jupyter kernel availability
            await self._wait_for_jupyter_kernel()
            
            self._initialized = True
            
            # Security logging
            security_logger.log_session_created(self.session_id, self.container.id)
            logger.info(f"Jupyter research session {self.session_id} initialized (kernel_ready={self.kernel_ready})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Jupyter research session {self.session_id}: {e}")
            await self.close()
            raise
    
    async def _wait_for_jupyter_kernel(self) -> bool:
        """Wait for Jupyter kernel to be ready."""
        logger.info("Checking for Jupyter kernel availability...")
        
        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).seconds < self.KERNEL_WAIT_TIME:
            try:
                # Check if Jupyter is available
                jupyter_check = await asyncio.to_thread(
                    self.container.exec_run,
                    "which jupyter",
                    workdir="/"
                )
                
                if jupyter_check.exit_code != 0:
                    logger.info("Jupyter not found in container, using direct Python execution")
                    return False
                
                # List available kernels
                kernel_list = await asyncio.to_thread(
                    self.container.exec_run,
                    "jupyter kernelspec list --json",
                    workdir="/"
                )
                
                if kernel_list.exit_code == 0 and kernel_list.output:
                    try:
                        kernels = json.loads(kernel_list.output.decode())
                        available_kernels = kernels.get("kernelspecs", {})
                        
                        # Look for QuantConnect kernel
                        for kernel_name, kernel_info in available_kernels.items():
                            if "python" in kernel_name.lower() or "quant" in kernel_name.lower():
                                self.kernel_name = kernel_name
                                self.kernel_ready = True
                                logger.info(f"Found Jupyter kernel: {kernel_name}")
                                return True
                    except json.JSONDecodeError:
                        pass
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.warning(f"Error checking for Jupyter kernel: {e}")
                await asyncio.sleep(5)
        
        logger.info("Jupyter kernel not ready after timeout, using direct Python execution")
        return False
    
    async def execute_with_kernel(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute code using Jupyter kernel."""
        execution_timeout = timeout or self.timeout
        
        try:
            # Create a temporary notebook file
            notebook_content = {
                "cells": [{
                    "cell_type": "code",
                    "source": code,
                    "metadata": {}
                }],
                "metadata": {
                    "kernelspec": {
                        "name": self.kernel_name or "python3",
                        "display_name": "Python 3"
                    }
                },
                "nbformat": 4,
                "nbformat_minor": 5
            }
            
            notebook_filename = f"temp_{uuid.uuid4().hex[:8]}.ipynb"
            notebook_path = f"{self.NOTEBOOKS_PATH}/{notebook_filename}"
            
            # Write notebook to container
            write_cmd = f"cat > {notebook_path} << 'EOF'\n{json.dumps(notebook_content)}\nEOF"
            await asyncio.to_thread(
                self.container.exec_run,
                ['/bin/sh', '-c', write_cmd]
            )
            
            # Execute notebook
            exec_cmd = f"jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout={execution_timeout} {notebook_filename}"
            
            exec_result = await asyncio.wait_for(
                asyncio.to_thread(
                    self.container.exec_run,
                    exec_cmd,
                    workdir=self.NOTEBOOKS_PATH
                ),
                timeout=execution_timeout + 10  # Add buffer for nbconvert overhead
            )
            
            if exec_result.exit_code == 0:
                # Read the executed notebook to get output
                read_cmd = f"cat {notebook_path}"
                read_result = await asyncio.to_thread(
                    self.container.exec_run,
                    read_cmd
                )
                
                if read_result.exit_code == 0 and read_result.output:
                    executed_nb = json.loads(read_result.output.decode())
                    
                    # Extract output from first cell
                    outputs = []
                    if executed_nb["cells"] and "outputs" in executed_nb["cells"][0]:
                        for output in executed_nb["cells"][0]["outputs"]:
                            if "text" in output:
                                outputs.append(output["text"])
                            elif "data" in output and "text/plain" in output["data"]:
                                outputs.append(output["data"]["text/plain"])
                    
                    # Clean up notebook
                    await asyncio.to_thread(
                        self.container.exec_run,
                        f"rm -f {notebook_path}"
                    )
                    
                    return {
                        "status": "success",
                        "output": "\n".join(outputs),
                        "error": None,
                        "session_id": self.session_id,
                        "kernel_used": True
                    }
            
            # If execution failed, return error
            error_output = exec_result.output.decode() if exec_result.output else "Unknown error"
            return {
                "status": "error",
                "output": "",
                "error": f"Kernel execution failed: {error_output}",
                "session_id": self.session_id,
                "kernel_used": True
            }
            
        except asyncio.TimeoutError:
            return {
                "status": "error",
                "output": "",
                "error": f"Kernel execution timed out after {execution_timeout} seconds",
                "session_id": self.session_id,
                "timeout": True,
                "kernel_used": True
            }
        except Exception as e:
            logger.error(f"Kernel execution error: {e}")
            return {
                "status": "error",
                "output": "",
                "error": f"Kernel execution error: {str(e)}",
                "session_id": self.session_id,
                "kernel_used": True
            }
    
    async def execute(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Execute Python code in the research container."""
        if not self._initialized:
            await self.initialize()
        
        if not self.container:
            raise ValueError("Container not available")
        
        self.last_used = datetime.utcnow()
        
        # Try kernel execution if available
        if self.kernel_ready:
            logger.info("Attempting kernel execution...")
            result = await self.execute_with_kernel(code, timeout)
            if result["status"] == "success" or "timeout" not in result:
                return result
            logger.warning("Kernel execution failed, falling back to direct execution")
        
        # Fall back to direct Python execution (from original implementation)
        # This would use the same approach as the original research_session.py
        logger.info("Using direct Python execution...")
        
        # Import the original execute logic here or create a base class
        # For now, return a placeholder
        return {
            "status": "error",
            "output": "",
            "error": "Direct execution not implemented in this demo",
            "session_id": self.session_id,
            "kernel_used": False
        }
    
    async def close(self, reason: str = "normal") -> None:
        """Clean up the research session."""
        logger.info(f"Closing Jupyter research session {self.session_id} (reason: {reason})")
        
        try:
            if self.container:
                self.container.stop(timeout=10)
                self.container = None
            
            if self._temp_dir:
                self._temp_dir.cleanup()
                self._temp_dir = None
            
            security_logger.log_session_destroyed(self.session_id, reason)
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
        
        finally:
            self._initialized = False
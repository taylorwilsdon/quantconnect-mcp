"""QuantConnect Research Session Container Adapter"""

import asyncio
import hashlib
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


class ResearchSessionError(Exception):
    """Custom exception for research session errors."""
    pass


class ResearchSession:
    """
    Container-based QuantConnect Research session adapter.
    
    Manages a Docker container running the quantconnect/research image
    and provides methods to execute code and exchange data.
    """
    
    IMAGE = "quantconnect/research:latest"  # Use DEFAULT_RESEARCH_IMAGE from lean constants
    CONTAINER_WORKSPACE = "/Lean"  # Match LEAN_ROOT_PATH
    NOTEBOOKS_PATH = "/Lean/Notebooks"
    TIMEOUT_DEFAULT = 300  # 5 minutes
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        workspace_dir: Optional[Path] = None,
        memory_limit: str = "2g",
        cpu_limit: float = 1.0,
        timeout: int = TIMEOUT_DEFAULT,
    ):
        """
        Initialize a new research session.
        
        Args:
            session_id: Unique identifier for this session
            workspace_dir: Local workspace directory (temp dir if None)
            memory_limit: Container memory limit (e.g., "2g", "512m")
            cpu_limit: Container CPU limit (fraction of CPU)
            timeout: Default execution timeout in seconds
        """
        self.session_id = session_id or f"qb_{uuid.uuid4().hex[:8]}"
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.timeout = timeout
        self.created_at = datetime.utcnow()
        self.last_used = self.created_at
        
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
        
        logger.info(f"Created research session {self.session_id}")
    
    async def initialize(self) -> None:
        """Initialize the Docker container."""
        if self._initialized:
            return
        
        try:
            # Ensure the image is available
            try:
                self.client.images.get(self.IMAGE)
            except docker.errors.ImageNotFound:
                logger.info(f"Pulling image {self.IMAGE}...")
                self.client.images.pull(self.IMAGE)
            
            # Start container with proper LEAN research environment
            # Use similar approach to lean-cli research command
            volumes = {
                str(self.workspace_dir): {
                    "bind": self.NOTEBOOKS_PATH,
                    "mode": "rw"
                }
            }
            
            # Add environment variables like lean-cli does
            environment = {
                "COMPOSER_DLL_DIRECTORY": "/Lean",
                "LEAN_ENGINE": "true",
                "PYTHONPATH": "/Lean"
            }
            
            # Create container with simplified configuration to ensure it starts
            try:
                self.container = self.client.containers.run(
                    self.IMAGE,
                    command=["sleep", "infinity"],  # Simple command that definitely works
                    volumes=volumes,
                    environment=environment,
                    working_dir="/",  # Start in root, create notebooks dir later
                    detach=True,
                    mem_limit=self.memory_limit,
                    cpu_period=100000,
                    cpu_quota=int(100000 * self.cpu_limit),
                    name=f"qc_research_{self.session_id}",
                    remove=True,  # Auto-remove when stopped
                    labels={
                        "mcp.quantconnect.session_id": self.session_id,
                        "mcp.quantconnect.created_at": self.created_at.isoformat(),
                    },
                )
                
                # Explicitly check if container started
                self.container.reload()
                if self.container.status != "running":
                    # If not running, get logs to see what went wrong
                    logs = self.container.logs().decode()
                    raise ResearchSessionError(f"Container failed to start (status: {self.container.status}). Logs: {logs}")
                    
                logger.info(f"Container {self.container.id} started successfully with status: {self.container.status}")
                
            except Exception as e:
                logger.error(f"Failed to create/start container: {e}")
                raise ResearchSessionError(f"Container creation failed: {e}")
            
            # Wait a moment for container to start
            await asyncio.sleep(2)
            
            # Initialize Python environment in the container
            # First create the notebooks directory if it doesn't exist
            mkdir_result = await asyncio.to_thread(
                self.container.exec_run,
                f"mkdir -p {self.NOTEBOOKS_PATH}",
                workdir="/"
            )
            
            # Test basic Python functionality
            init_commands = [
                ("python3 --version", "Check Python version"),
                ("python3 -c \"import sys; print('Python initialized:', sys.version)\"", "Test Python import"),
                ("python3 -c \"import pandas as pd; import numpy as np; print('Data libraries available')\"", "Test data libraries"),
            ]
            
            for cmd, description in init_commands:
                logger.info(f"Running initialization: {description}")
                result = await asyncio.to_thread(
                    self.container.exec_run,
                    cmd,
                    workdir="/"  # Use root for init commands
                )
                if result.exit_code != 0:
                    error_msg = result.output.decode() if result.output else "No output"
                    logger.error(f"Init command failed: {cmd} - {error_msg}")
                    raise ResearchSessionError(f"Container initialization failed ({description}): {error_msg}")
                else:
                    output = result.output.decode() if result.output else ""
                    logger.info(f"Init success: {output.strip()}")
            
            self._initialized = True
            
            # Security logging
            security_logger.log_session_created(self.session_id, self.container.id)
            logger.info(f"Research session {self.session_id} initialized successfully")
            
            container_logger = get_container_logger(self.session_id)
            container_logger.info(f"Container {self.container.id} ready for session {self.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to initialize research session {self.session_id}: {e}")
            await self.close()
            raise ResearchSessionError(f"Failed to initialize research session: {e}")
    
    async def execute(
        self,
        code: str,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute Python code in the research container with comprehensive error handling.
        
        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds (uses default if None)
            
        Returns:
            Dictionary with execution results
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.container:
            raise ResearchSessionError("Container not available")
        
        # Security and logging
        code_hash = hashlib.sha256(code.encode()).hexdigest()[:16]
        container_logger = get_container_logger(self.session_id)
        
        # Basic security checks
        if len(code) > 50000:  # 50KB limit
            security_logger.log_security_violation(
                self.session_id, "CODE_SIZE_LIMIT", f"Code size: {len(code)} bytes"
            )
            return {
                "status": "error",
                "output": "",
                "error": "Code size exceeds 50KB limit",
                "session_id": self.session_id,
            }
        
        # Check for potentially dangerous operations
        dangerous_patterns = [
            "import os", "import subprocess", "import sys", "__import__",
            "exec(", "eval(", "compile(", "open(", "file(",
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code.lower():
                security_logger.log_security_violation(
                    self.session_id, "DANGEROUS_CODE_PATTERN", f"Pattern: {pattern}"
                )
                container_logger.warning(f"Potentially dangerous code pattern detected: {pattern}")
        
        self.last_used = datetime.utcnow()
        execution_timeout = timeout or self.timeout
        
        container_logger.info(f"Executing code (hash: {code_hash}, timeout: {execution_timeout}s)")
        
        try:
            # Check container health before execution
            try:
                container_status = self.container.status
                if container_status != "running":
                    raise ResearchSessionError(f"Container is not running (status: {container_status})")
            except Exception as e:
                raise ResearchSessionError(f"Failed to check container status: {e}")
            
            # Execute code directly in container using exec_run (like lean-cli)
            # Create a temporary Python script
            script_content = f"""#!/usr/bin/env python3
import sys
import traceback
import pandas as pd
import numpy as np
from io import StringIO

# Capture stdout
old_stdout = sys.stdout
sys.stdout = captured_output = StringIO()

try:
    # Execute the user code
{chr(10).join('    ' + line for line in code.split(chr(10)))}
    
    output = captured_output.getvalue()
    print(output, file=old_stdout, end='')
except Exception as e:
    sys.stdout = old_stdout
    print(captured_output.getvalue(), end='')
    print(f"Error: {{e}}", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
finally:
    sys.stdout = old_stdout
"""
            
            # Use asyncio timeout for better control
            try:
                exec_result = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.container.exec_run,
                        f'python3 -c {json.dumps(script_content)}',
                        workdir=self.NOTEBOOKS_PATH,
                        stdout=True,
                        stderr=True,
                    ),
                    timeout=execution_timeout
                )
            except asyncio.TimeoutError:
                security_logger.log_resource_limit_hit(
                    self.session_id, "EXECUTION_TIMEOUT", f"{execution_timeout}s"
                )
                container_logger.error(f"Code execution timed out after {execution_timeout}s")
                return {
                    "status": "error",
                    "output": "",
                    "error": f"Code execution timed out after {execution_timeout} seconds",
                    "session_id": self.session_id,
                    "timeout": True,
                }
            
            # Removed duplicate exit code check - handled below
            
            # Parse result with enhanced error handling - simplified approach like lean-cli
            output_text = exec_result.output.decode() if exec_result.output else ""
            
            # Check execution status based on exit code (simpler, more reliable)
            if exec_result.exit_code == 0:
                # Success
                security_logger.log_code_execution(self.session_id, code_hash, True)
                container_logger.info(f"Code execution successful (hash: {code_hash})")
                
                return {
                    "status": "success",
                    "output": output_text,
                    "error": None,
                    "session_id": self.session_id,
                }
            else:
                # Error
                security_logger.log_code_execution(self.session_id, code_hash, False)
                container_logger.error(f"Code execution failed (hash: {code_hash}, exit_code: {exec_result.exit_code})")
                
                return {
                    "status": "error",
                    "output": output_text,
                    "error": f"Code execution failed with exit code {exec_result.exit_code}",
                    "session_id": self.session_id,
                    "exit_code": exec_result.exit_code,
                }
        
        except ResearchSessionError:
            # Re-raise custom exceptions
            raise
        except Exception as e:
            container_logger.error(f"Unexpected error during code execution: {e}")
            security_logger.log_code_execution(self.session_id, code_hash, False)
            return {
                "status": "error",
                "output": "",
                "error": f"Unexpected execution error: {str(e)}",
                "session_id": self.session_id,
                "exception_type": type(e).__name__,
            }
    
    async def save_dataframe(
        self,
        df: pd.DataFrame,
        filename: str,
        format: str = "parquet"
    ) -> Dict[str, Any]:
        """
        Save a pandas DataFrame to the workspace.
        
        Args:
            df: DataFrame to save
            filename: Output filename
            format: File format (parquet, csv, json)
            
        Returns:
            Operation result
        """
        try:
            filepath = self.workspace_dir / filename
            
            if format.lower() == "parquet":
                df.to_parquet(filepath)
            elif format.lower() == "csv":
                df.to_csv(filepath, index=False)
            elif format.lower() == "json":
                df.to_json(filepath, orient="records", date_format="iso")
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            return {
                "status": "success",
                "message": f"DataFrame saved to {filename}",
                "filepath": str(filepath),
                "format": format,
                "shape": df.shape,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to save DataFrame to {filename}",
            }
    
    async def load_dataframe(
        self,
        filename: str,
        format: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load a pandas DataFrame from the workspace.
        
        Args:
            filename: Input filename
            format: File format (auto-detected if None)
            
        Returns:
            Operation result with DataFrame data
        """
        try:
            filepath = self.workspace_dir / filename
            
            if not filepath.exists():
                return {
                    "status": "error",
                    "error": f"File {filename} not found in workspace",
                }
            
            # Auto-detect format if not specified
            if format is None:
                format = filepath.suffix.lower().lstrip(".")
            
            if format == "parquet":
                df = pd.read_parquet(filepath)
            elif format == "csv":
                df = pd.read_csv(filepath)
            elif format == "json":
                df = pd.read_json(filepath)
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported format: {format}",
                }
            
            return {
                "status": "success",
                "message": f"DataFrame loaded from {filename}",
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.to_dict(),
                "data": df.to_dict("records")[:100],  # Limit to first 100 rows
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to load DataFrame from {filename}",
            }
    
    def is_expired(self, max_idle_time: timedelta = timedelta(hours=1)) -> bool:
        """Check if session has been idle too long."""
        return datetime.utcnow() - self.last_used > max_idle_time
    
    async def close(self, reason: str = "normal") -> None:
        """Clean up the research session with enhanced logging."""
        logger.info(f"Closing research session {self.session_id} (reason: {reason})")
        container_logger = get_container_logger(self.session_id)
        
        try:
            if self.container:
                container_id = self.container.id
                try:
                    container_logger.info(f"Stopping container {container_id}")
                    self.container.stop(timeout=10)
                    container_logger.info(f"Container {container_id} stopped successfully")
                except Exception as e:
                    container_logger.warning(f"Error stopping container {container_id}: {e}")
                    try:
                        container_logger.info(f"Force killing container {container_id}")
                        self.container.kill()
                        container_logger.warning(f"Container {container_id} force killed")
                    except Exception as e2:
                        container_logger.error(f"Error killing container {container_id}: {e2}")
                
                self.container = None
            
            if self._temp_dir:
                container_logger.info(f"Cleaning up temporary directory: {self._temp_dir.name}")
                self._temp_dir.cleanup()
                self._temp_dir = None
            
            # Security logging
            security_logger.log_session_destroyed(self.session_id, reason)
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            container_logger.error(f"Cleanup failed: {e}")
        
        finally:
            self._initialized = False
            logger.info(f"Research session {self.session_id} cleanup completed")
    
    def __repr__(self) -> str:
        return (
            f"ResearchSession(id={self.session_id}, "
            f"initialized={self._initialized}, "
            f"created_at={self.created_at.isoformat()})"
        )
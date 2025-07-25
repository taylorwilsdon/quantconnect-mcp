"""QuantConnect Research Session using lean-cli."""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import docker
from docker.models.containers import Container

from .logging_config import get_container_logger, security_logger

logger = logging.getLogger(__name__)


class ResearchSessionError(Exception):
    """Custom exception for research session errors."""
    pass


class ResearchSession:
    """
    Research session that uses lean-cli to manage the research environment.
    
    This approach ensures full compatibility with QuantConnect's setup
    by delegating all initialization and container management to lean-cli.
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        workspace_dir: Optional[Path] = None,
        port: Optional[int] = None,
    ):
        """
        Initialize a new research session.
        
        Args:
            session_id: Unique identifier for this session
            workspace_dir: Directory for the lean project (temp dir if None)
            port: Port to run Jupyter on (default: 8888)
        """
        self.session_id = session_id or f"qb_{uuid.uuid4().hex[:8]}"
        self.port = port or int(os.environ.get("QUANTBOOK_DOCKER_PORT", "8888"))
        self.created_at = datetime.utcnow()
        self.last_used = self.created_at
        
        # Setup workspace
        if workspace_dir:
            self.workspace_dir = Path(workspace_dir)
            self._temp_dir = None
        else:
            self._temp_dir = tempfile.TemporaryDirectory(prefix=f"qc_research_{self.session_id}_")
            self.workspace_dir = Path(self._temp_dir.name)
        
        # Ensure workspace exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Docker client for container management
        self.client = docker.from_env()
        self.container: Optional[Container] = None
        self._initialized = False
        
        logger.info(f"Created research session {self.session_id} using lean-cli (port: {self.port})")
    
    async def _check_lean_cli(self) -> bool:
        """Check if lean-cli is installed and available."""
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["lean", "--version"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                logger.info(f"lean-cli version: {result.stdout.strip()}")
                return True
            else:
                logger.error(f"lean-cli check failed: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.error("lean-cli not found in PATH")
            return False
        except Exception as e:
            logger.error(f"Error checking lean-cli: {e}")
            return False
    
    async def _init_lean_project(self) -> bool:
        """Initialize a lean project in the workspace directory."""
        try:
            # Check if already initialized (either lean.json or config.json)
            lean_json = self.workspace_dir / "lean.json"
            config_json = self.workspace_dir / "config.json"
            
            if lean_json.exists() or config_json.exists():
                logger.info("Lean project already initialized")
                return True
            
            # Run lean init in the workspace directory
            logger.info(f"Initializing lean project in {self.workspace_dir}")
            
            # First, we need to ensure we're logged in
            # Check if credentials are available
            if not all([
                os.environ.get("QUANTCONNECT_USER_ID"),
                os.environ.get("QUANTCONNECT_API_TOKEN"),
                os.environ.get("QUANTCONNECT_ORGANIZATION_ID")
            ]):
                logger.warning("QuantConnect credentials not fully configured")
                # Continue anyway - lean init might work with cached credentials
            
            # Run lean init
            org_id = os.environ.get("QUANTCONNECT_ORGANIZATION_ID", "")
            init_cmd = ["lean", "init"]
            if org_id:
                init_cmd.extend(["--organization", org_id])
            
            logger.info(f"Running: {' '.join(init_cmd)}")
            result = await asyncio.to_thread(
                subprocess.run,
                init_cmd,
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"lean init failed with return code {result.returncode}")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                
                # Check if it's a credentials issue
                if "Please log in" in result.stderr or "authentication" in result.stderr.lower():
                    logger.error("Authentication required. Please run 'lean login' first.")
                
                return False
            
            logger.info("Lean project initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing lean project: {e}")
            return False
    
    async def _find_container(self) -> None:
        """Try to find the research container."""
        all_containers = self.client.containers.list()
        logger.info(f"Looking for container among {len(all_containers)} running containers")
        
        # Try different name patterns that lean-cli might use
        name_patterns = [
            "lean_cli_",
            "research",
            str(self.port),
        ]
        
        for container in all_containers:
            container_name_lower = container.name.lower()
            # Check if any of our patterns match
            if any(pattern.lower() in container_name_lower for pattern in name_patterns):
                # Additional check - make sure it's a research container
                try:
                    # Check ports
                    port_bindings = container.ports.get('8888/tcp', [])
                    for binding in port_bindings:
                        if binding.get('HostPort') == str(self.port):
                            self.container = container
                            logger.info(f"Found research container: {container.name}")
                            return
                except Exception as e:
                    logger.debug(f"Error checking container {container.name}: {e}")
    
    async def _create_research_notebook(self) -> Path:
        """Create a default research notebook if it doesn't exist."""
        notebooks_dir = self.workspace_dir / "Research"
        notebooks_dir.mkdir(parents=True, exist_ok=True)
        
        notebook_path = notebooks_dir / "research.ipynb"
        if not notebook_path.exists():
            notebook_content = {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": [
                            "# QuantConnect Research Environment\n",
                            "Welcome to the QuantConnect Research Environment. ",
                            "QuantBook is automatically available as 'qb'."
                        ]
                    },
                    {
                        "cell_type": "code",
                        "metadata": {},
                        "source": [
                            "# QuantBook Analysis\n",
                            "# Documentation: https://www.quantconnect.com/docs/v2/research-environment\n",
                            "# qb is pre-initialized and ready to use"
                        ]
                    }
                ],
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3"
                    }
                },
                "nbformat": 4,
                "nbformat_minor": 4
            }
            with open(notebook_path, "w") as f:
                json.dump(notebook_content, f, indent=2)
            logger.info(f"Created default research notebook: {notebook_path}")
        
        return notebooks_dir
    
    async def initialize(self) -> None:
        """Initialize the research environment using lean-cli."""
        if self._initialized:
            return
        
        try:
            # Check if lean-cli is available
            if not await self._check_lean_cli():
                raise ResearchSessionError(
                    "lean-cli is not installed. Please install it with: pip install lean"
                )
            
            # Initialize lean project if needed
            init_success = await self._init_lean_project()
            if not init_success:
                logger.warning("Failed to initialize lean project, will try to proceed anyway")
            
            # Create research notebook directory
            research_dir = await self._create_research_notebook()
            
            # Start the research environment using lean-cli
            logger.info(f"Starting research environment on port {self.port}")
            
            # Build the lean research command
            cmd = [
                "lean", "research",
                str(research_dir),  # Project directory
                "--port", str(self.port),
                "--no-open"  # Don't open browser automatically
            ]
            
            # Add detach flag to run in background
            cmd.append("--detach")
            
            # Run the command
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"lean research failed with return code {result.returncode}")
                logger.error(f"stdout: {result.stdout}")
                logger.error(f"stderr: {result.stderr}")
                
                error_msg = result.stderr or result.stdout or "Unknown error"
                
                # Provide helpful error messages
                if "Please log in" in error_msg:
                    raise ResearchSessionError(
                        "Authentication required. Please run 'lean login' first to authenticate with QuantConnect."
                    )
                elif "lean.json" in error_msg or "config.json" in error_msg:
                    raise ResearchSessionError(
                        "No Lean configuration found. Please run 'lean init' in your project directory first."
                    )
                else:
                    raise ResearchSessionError(f"Failed to start research environment: {error_msg}")
            
            # Extract container name from output
            output = result.stdout
            logger.info(f"lean research output: {output}")
            
            # Wait a moment for container to fully start
            await asyncio.sleep(2)
            
            # Find the container - lean-cli uses specific naming patterns
            container_name = None
            self.container = None
            
            # First try to extract from output
            for line in output.split('\n'):
                if "container" in line.lower() and ("started" in line or "running" in line):
                    # Try different extraction patterns
                    import re
                    # Pattern 1: 'container-name'
                    match = re.search(r"'([^']+)'", line)
                    if match:
                        container_name = match.group(1)
                        logger.info(f"Extracted container name from output: {container_name}")
                        break
                    # Pattern 2: container-name (no quotes)
                    match = re.search(r"container[:\s]+(\S+)", line, re.IGNORECASE)
                    if match:
                        container_name = match.group(1)
                        logger.info(f"Extracted container name from output (pattern 2): {container_name}")
                        break
            
            # Try to get container by extracted name
            if container_name:
                try:
                    self.container = self.client.containers.get(container_name)
                    logger.info(f"Found container by name: {container_name}")
                except docker.errors.NotFound:
                    logger.warning(f"Container {container_name} not found")
            
            # If not found yet, search by various patterns
            if not self.container:
                # List all running containers for debugging
                all_containers = self.client.containers.list()
                logger.info(f"All running containers: {[c.name for c in all_containers]}")
                
                # Try different name patterns that lean-cli might use
                name_patterns = [
                    "lean_cli_",
                    self.session_id,
                    "research",
                    str(self.port),  # Sometimes port is in the name
                ]
                
                for container in all_containers:
                    container_name_lower = container.name.lower()
                    # Check if any of our patterns match
                    if any(pattern.lower() in container_name_lower for pattern in name_patterns):
                        # Additional check - make sure it's a research container
                        if "research" in container_name_lower or str(self.port) in container.ports.get('8888/tcp', [{}])[0].get('HostPort', ''):
                            self.container = container
                            logger.info(f"Found research container by pattern matching: {container.name}")
                            break
            
            # Last resort - check by port binding
            if not self.container:
                for container in all_containers:
                    try:
                        # Check if this container has port 8888 mapped to our port
                        port_bindings = container.ports.get('8888/tcp', [])
                        if port_bindings:
                            for binding in port_bindings:
                                if binding.get('HostPort') == str(self.port):
                                    self.container = container
                                    logger.info(f"Found container by port {self.port}: {container.name}")
                                    break
                    except Exception as e:
                        logger.debug(f"Error checking container {container.name}: {e}")
                    
                    if self.container:
                        break
            
            self._initialized = True
            
            # Security logging
            if self.container:
                security_logger.log_session_created(self.session_id, self.container.id)
                logger.info(f"Research session {self.session_id} initialized successfully with container {self.container.name}")
            else:
                logger.warning(f"Research session {self.session_id} initialized but container not yet found")
                logger.info("Container may still be starting up. Will retry on first execute.")
            
            logger.info(f"Jupyter Lab accessible at: http://localhost:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize research session: {e}")
            await self.close()
            raise ResearchSessionError(f"Failed to initialize research session: {e}")
    
    async def execute(self, code: str, timeout: int = 300) -> Dict[str, Any]:
        """
        Execute code by modifying /LeanCLI/research.ipynb where qb is available.
        This ensures all code has access to the pre-initialized QuantBook instance.
        """
        if not self._initialized:
            await self.initialize()
        
        # If container wasn't found during init, try to find it again
        if not self.container:
            logger.warning("Container not found during init, attempting to locate it again...")
            await self._find_container()
            
            if not self.container:
                # Return a specific error that helps with debugging
                return {
                    "status": "error",
                    "output": "",
                    "error": "Container not found. The Jupyter environment may still be starting up.",
                    "session_id": self.session_id,
                    "message": f"Please check http://localhost:{self.port} to see if Jupyter is running."
                }
        
        self.last_used = datetime.utcnow()
        
        try:
            # ALWAYS use /LeanCLI/research.ipynb
            notebook_path = "/LeanCLI/research.ipynb"
            
            # Read the existing notebook
            read_cmd = f"cat {notebook_path}"
            read_result = await asyncio.to_thread(
                self.container.exec_run,
                read_cmd,
                demux=False
            )
            
            if read_result.exit_code != 0:
                logger.error(f"Failed to read notebook at {notebook_path}")
                # Create a basic notebook if it doesn't exist
                notebook_content = {
                    "cells": [
                        {
                            "cell_type": "markdown",
                            "metadata": {},
                            "source": ["# QuantConnect Research\n", "qb is pre-initialized and ready to use"]
                        }
                    ],
                    "metadata": {
                        "kernelspec": {
                            "display_name": "Foundation-Py-Default",
                            "language": "python",
                            "name": "python3"
                        }
                    },
                    "nbformat": 4,
                    "nbformat_minor": 4
                }
            else:
                # Parse existing notebook
                try:
                    notebook_content = json.loads(read_result.output.decode('utf-8'))
                except Exception as e:
                    logger.error(f"Failed to parse notebook: {e}")
                    return {
                        "status": "error",
                        "output": "",
                        "error": f"Failed to parse notebook: {e}",
                        "session_id": self.session_id,
                    }
            
            # Add new cell with the code
            new_cell = {
                "cell_type": "code",
                "metadata": {},
                "source": code.split('\n') if isinstance(code, str) else code,
                "outputs": []
            }
            notebook_content["cells"].append(new_cell)
            
            # Write the updated notebook back
            notebook_json = json.dumps(notebook_content, indent=2)
            write_cmd = f"cat > {notebook_path} << 'EOF'\n{notebook_json}\nEOF"
            write_result = await asyncio.to_thread(
                self.container.exec_run,
                ['/bin/sh', '-c', write_cmd],
                demux=False
            )
            
            if write_result.exit_code != 0:
                logger.error(f"Failed to write notebook: {write_result.output}")
                return {
                    "status": "error",
                    "output": "",
                    "error": "Failed to update notebook",
                    "session_id": self.session_id,
                }
            
            # Now we need to execute the notebook and get the output
            # For now, return success to indicate the notebook was updated
            return {
                "status": "success",
                "output": "Code added to /LeanCLI/research.ipynb. The notebook has been updated with your code where qb is available.",
                "error": None,
                "session_id": self.session_id,
                "note": "To see results, check the Jupyter interface or read the notebook file."
            }
            
            # Use low-level Docker API for better output capture (following old working approach)
            # Write the script using exec_create/exec_start
            write_cmd = f"cat > {script_path} << 'EOF'\n{script_content}\nEOF"
            write_exec = await asyncio.to_thread(
                self.container.client.api.exec_create,
                self.container.id,
                ['/bin/sh', '-c', write_cmd],
                stdout=True,
                stderr=True,
                workdir=notebooks_dir
            )
            write_result = await asyncio.to_thread(
                self.container.client.api.exec_start,
                write_exec['Id'],
                stream=False
            )
            
            # Check if write was successful
            write_info = await asyncio.to_thread(
                self.container.client.api.exec_inspect,
                write_exec['Id']
            )
            if write_info.get('ExitCode', -1) != 0:
                logger.error(f"Failed to write script: {write_result}")
                raise RuntimeError(f"Failed to write script to container")
            
            # Execute the script using the appropriate Python
            # Try multiple Python paths that lean-cli might use
            python_commands = [
                "/opt/miniconda3/bin/python",  # Conda environment
                "python3",                      # System python3
                "python",                       # System python
            ]
            
            exec_result = None
            exec_output = None
            exit_code = -1
            
            for python_cmd in python_commands:
                try:
                    # Create execution command
                    exec_cmd = f"{python_cmd} {script_filename}"
                    exec_instance = await asyncio.to_thread(
                        self.container.client.api.exec_create,
                        self.container.id,
                        exec_cmd,
                        stdout=True,
                        stderr=True,
                        workdir=notebooks_dir,
                        environment={
                            "PYTHONPATH": "/Lean:/Lean/Library:/opt/miniconda3/lib/python3.8/site-packages",
                            "LEAN_ENGINE": "true",
                            "COMPOSER_DLL_DIRECTORY": "/Lean"
                        }
                    )
                    
                    # Execute and get output
                    exec_output = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.container.client.api.exec_start,
                            exec_instance['Id'],
                            stream=False
                        ),
                        timeout=timeout
                    )
                    
                    # Get execution info
                    exec_info = await asyncio.to_thread(
                        self.container.client.api.exec_inspect,
                        exec_instance['Id']
                    )
                    
                    exit_code = exec_info.get('ExitCode', -1)
                    
                    if exit_code == 0:
                        logger.info(f"Successfully executed with: {python_cmd}")
                        break
                    else:
                        logger.debug(f"Failed with {python_cmd}: exit code {exit_code}")
                        
                except asyncio.TimeoutError:
                    logger.error(f"Execution timed out after {timeout}s")
                    return {
                        "status": "error",
                        "output": "",
                        "error": f"Code execution timed out after {timeout} seconds",
                        "session_id": self.session_id,
                        "timeout": True,
                    }
                except Exception as e:
                    logger.debug(f"Error with {python_cmd}: {e}")
                    continue
            
            # Clean up the script file
            cleanup_exec = await asyncio.to_thread(
                self.container.client.api.exec_create,
                self.container.id,
                f'rm -f {script_filename}',
                workdir=notebooks_dir
            )
            await asyncio.to_thread(
                self.container.client.api.exec_start,
                cleanup_exec['Id'],
                stream=False
            )
            
            # Process the output
            if exec_output is None:
                raise RuntimeError("Could not execute code in any Python environment")
            
            # Decode output - exec_output is bytes when stream=False
            output_str = exec_output.decode('utf-8', errors='replace') if exec_output else ""
            
            # The output might contain both stdout and stderr mixed
            # For now, we'll return it all as output
            if exit_code == 0:
                return {
                    "status": "success",
                    "output": output_str.strip(),
                    "error": None,
                    "session_id": self.session_id,
                }
            else:
                # Try to separate error from output
                lines = output_str.split('\n')
                error_lines = [l for l in lines if 'Error' in l or 'Traceback' in l or 'File "' in l]
                error_msg = '\n'.join(error_lines) if error_lines else "Execution failed"
                
                return {
                    "status": "error",
                    "output": output_str.strip(),
                    "error": error_msg,
                    "session_id": self.session_id,
                    "exit_code": exit_code,
                }
            
        except Exception as e:
            logger.error(f"Error executing code: {e}")
            return {
                "status": "error",
                "output": "",
                "error": str(e),
                "session_id": self.session_id,
            }
    
    def is_expired(self, max_idle_time: timedelta = timedelta(hours=1)) -> bool:
        """Check if session has been idle too long."""
        return datetime.utcnow() - self.last_used > max_idle_time
    
    async def close(self, reason: str = "normal") -> None:
        """Stop the research session."""
        logger.info(f"Closing research session {self.session_id} (reason: {reason})")
        
        try:
            if self.container:
                try:
                    # Stop the container
                    self.container.stop(timeout=10)
                    logger.info(f"Container {self.container.name} stopped")
                except Exception as e:
                    logger.warning(f"Error stopping container: {e}")
                    try:
                        self.container.kill()
                    except Exception as e2:
                        logger.error(f"Error killing container: {e2}")
                
                self.container = None
            
            # Clean up temp directory if used
            if self._temp_dir:
                self._temp_dir.cleanup()
                self._temp_dir = None
            
            # Security logging
            security_logger.log_session_destroyed(self.session_id, reason)
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
        finally:
            self._initialized = False
            logger.info(f"Research session {self.session_id} closed")
    
    def __repr__(self) -> str:
        return (
            f"ResearchSession(id={self.session_id}, "
            f"initialized={self._initialized}, "
            f"port={self.port})"
        )
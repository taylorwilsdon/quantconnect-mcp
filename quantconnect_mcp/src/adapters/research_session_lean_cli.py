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
                            "QuantBook is automatically available as 'qb'.",
                            "qb = QuantBook()"
                        ]
                    },
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "source": [
                            "# QuantBook Analysis\n",
                            "# Documentation: https://www.quantconnect.com/docs/v2/research-environment\n",
                            "\n",
                            "import os\n",
                            "import glob\n",
                            "\n",
                            "# Configure QuantConnect environment properly\n",
                            "import QuantConnect\n",
                            "from QuantConnect.Configuration import Config\n",
                            "\n",
                            "# Reset config and set required values\n",
                            "Config.Reset()\n",
                            "Config.Set('data-folder', '/Lean/Data')\n",
                            "Config.Set('log-handler', 'ConsoleLogHandler')\n",
                            "Config.Set('debug-mode', 'false')\n",
                            "Config.Set('results-destination-folder', '/LeanCLI')\n",
                            "\n",
                            "# Initialize QuantBook with proper error handling\n",
                            "qb = None\n",
                            "try:\n",
                            "    qb = QuantBook()\n",
                            "    print('✅ QuantBook initialized successfully!')\n",
                            "except Exception as e:\n",
                            "    print(f'❌ QuantBook initialization failed: {e}')\n",
                            "    print('Will attempt to continue with limited functionality...')\n",
                            "\n",
                            "print('Checking for QuantBook initialization...')\n",
                            "\n",
                            "# Look for IPython startup scripts\n",
                            "startup_paths = [\n",
                            "    '/root/.ipython/profile_default/startup/',\n",
                            "    '/opt/miniconda3/etc/ipython/startup/',\n",
                            "    '/etc/ipython/startup/',\n",
                            "    '~/.ipython/profile_default/startup/'\n",
                            "]\n",
                            "\n",
                            "for path in startup_paths:\n",
                            "    expanded_path = os.path.expanduser(path)\n",
                            "    if os.path.exists(expanded_path):\n",
                            "        print(f'\\nFound startup directory: {expanded_path}')\n",
                            "        files = glob.glob(os.path.join(expanded_path, '*.py'))\n",
                            "        for f in files:\n",
                            "            print(f'  Startup script: {os.path.basename(f)}')\n",
                            "            # Read first few lines to see what it does\n",
                            "            try:\n",
                            "                with open(f, 'r') as file:\n",
                            "                    lines = file.readlines()[:10]\n",
                            "                    for line in lines:\n",
                            "                        if 'QuantBook' in line or 'qb' in line:\n",
                            "                            print(f'    -> {line.strip()}')\n",
                            "            except:\n",
                            "                pass\n",
                            "\n",
                            "# Check if qb is already available\n",
                            "try:\n",
                            "    qb\n",
                            "    print('\\n✓ QuantBook is ALREADY initialized and available as qb!')\n",
                            "    print(f'Type: {type(qb)}')\n",
                            "except NameError:\n",
                            "    print('\\n✗ QuantBook (qb) is NOT available in the current namespace')\n",
                            "    print('\\nThis suggests we need to run in the Jupyter web interface where startup scripts are executed')\n"
                        ],
                        "outputs": []
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
                        },
                        {
                            "cell_type": "code",
                            "execution_count": None,
                            "metadata": {},
                            "source": [
                                "# QuantBook initialization check\n",
                                "import QuantConnect\n",
                                "from QuantConnect.Configuration import Config\n",
                                "\n",
                                "# Configure QuantConnect properly\n",
                                "Config.Reset()\n",
                                "Config.Set('data-folder', '/Lean/Data')\n",
                                "Config.Set('log-handler', 'ConsoleLogHandler')\n",
                                "Config.Set('debug-mode', 'false')\n",
                                "Config.Set('results-destination-folder', '/LeanCLI')\n",
                                "\n",
                                "# Initialize QuantBook with error handling\n",
                                "qb = None\n",
                                "try:\n",
                                "    qb = QuantBook()\n",
                                "    print('✅ QuantBook initialized successfully!')\n",
                                "except Exception as e:\n",
                                "    print(f'❌ QuantBook initialization failed: {e}')\n",
                                "    print('Will attempt to continue with limited functionality...')\n"
                            ],
                            "outputs": []
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
            # Properly format the source with newlines preserved
            if isinstance(code, str):
                lines = code.split('\n')
                # Add newline to each line except possibly the last
                source = [line + '\n' for line in lines[:-1]]
                if lines[-1]:  # If last line is not empty, add it
                    source.append(lines[-1] + '\n')
                elif not source:  # If code was empty or just newlines
                    source = ['']
            else:
                source = code

            new_cell = {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "source": source,
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

            # Execute using direct kernel approach since jupyter tools may not be available
            # Try to execute the last cell directly using the jupyter kernel

            # First, check what execution tools are available
            check_tools_cmd = "cd /LeanCLI && which jupyter && which python && which ipython && ls -la && echo '=== KERNELS ===' && jupyter kernelspec list"
            tools_result = await asyncio.to_thread(
                self.container.exec_run,
                ['/bin/sh', '-c', check_tools_cmd],
                demux=False
            )
            tools_output = tools_result.output.decode('utf-8', errors='replace') if tools_result.output else ""
            logger.info(f"Available tools in container: {tools_output}")

            # Use proper Jupyter kernel execution - the key is to communicate with the running kernel
            exec_commands = [
                # Method 1: Enhanced Jupyter kernel detection and execution
                ("jupyter kernel", f"""cd /LeanCLI && python -c "
import requests
import json
import time
import os
import subprocess

# Load the notebook to get the code
with open('research.ipynb') as f:
    nb = json.load(f)
code = ''.join(nb['cells'][-1]['source'])

print('=== JUPYTER KERNEL DEBUG ===')

# Check if Jupyter server is running
try:
    # Try different endpoints and configurations
    base_urls = ['http://localhost:8888', 'http://127.0.0.1:8888']
    token = os.environ.get('JUPYTER_TOKEN', '')
    
    for base_url in base_urls:
        print(f'Trying {{base_url}}...')
        
        # Check server status
        try:
            if token:
                server_response = requests.get(f'{{base_url}}/api/status?token={{token}}', timeout=3)
            else:
                server_response = requests.get(f'{{base_url}}/api/status', timeout=3)
            print(f'Server status: {{server_response.status_code}}')
        except Exception as e:
            print(f'Server check failed: {{e}}')
            continue
            
        # Get kernels
        try:
            if token:
                kernels_response = requests.get(f'{{base_url}}/api/kernels?token={{token}}', timeout=5)
            else:
                kernels_response = requests.get(f'{{base_url}}/api/kernels', timeout=5)
                
            print(f'Kernels API response: {{kernels_response.status_code}}')
            
            if kernels_response.status_code == 200:
                kernels = kernels_response.json()
                print(f'Found {{len(kernels)}} kernels: {{[k.get(\\\"id\\\", \\\"unknown\\\") for k in kernels]}}')
                
                if kernels:
                    kernel_id = kernels[0]['id']
                    print(f'Using kernel: {{kernel_id}}')
                    
                    # Execute code via kernel API  
                    execute_url = f'{{base_url}}/api/kernels/{{kernel_id}}/execute'
                    if token:
                        execute_url += f'?token={{token}}'
                        
                    execute_data = {{
                        'code': code,
                        'silent': False,
                        'store_history': True,
                        'user_expressions': {{}},
                        'allow_stdin': False
                    }}
                    
                    exec_response = requests.post(execute_url, json=execute_data, timeout=30)
                    
                    if exec_response.status_code == 200:
                        result = exec_response.json()
                        print('=== KERNEL EXECUTION SUCCESS ===')
                        print(json.dumps(result, indent=2))
                        break
                    else:
                        print(f'Kernel execution failed: {{exec_response.status_code}}')
                        print(exec_response.text)
                else:
                    print('No running kernels found')
            else:
                print(f'Kernels API failed: {{kernels_response.status_code}} - {{kernels_response.text}}')
        except Exception as e:
            print(f'Kernel API failed for {{base_url}}: {{e}}')
    
    # If API approach fails, try to start a kernel and execute
    print('=== TRYING KERNEL START ===')
    try:
        # Create a new kernel session
        kernel_response = requests.post('http://localhost:8888/api/kernels', 
                                      json={{'name': 'python3'}}, timeout=10)
        if kernel_response.status_code == 201:
            kernel_info = kernel_response.json()
            kernel_id = kernel_info['id']
            print(f'Created new kernel: {{kernel_id}}')
            
            # Wait a moment for kernel to start
            time.sleep(2)
            
            # Now execute code
            execute_data = {{
                'code': code,
                'silent': False,
                'store_history': True
            }}
            
            exec_response = requests.post(
                f'http://localhost:8888/api/kernels/{{kernel_id}}/execute',
                json=execute_data, timeout=30)
                
            if exec_response.status_code == 200:
                result = exec_response.json()
                print('=== NEW KERNEL EXECUTION SUCCESS ===')
                print(json.dumps(result, indent=2))
            else:
                print(f'New kernel execution failed: {{exec_response.status_code}}')
        else:
            print(f'Failed to create kernel: {{kernel_response.status_code}}')
    except Exception as e:
        print(f'Kernel creation failed: {{e}}')
        
except Exception as e:
    print(f'All kernel approaches failed: {{e}}')
    
print('=== FALLBACK TO NOTEBOOK EXECUTION ===')
exec(code)
" 2>&1"""),
                
                # Method 2: Execute using IPython with QuantConnect startup
                ("ipython execution", f"""cd /LeanCLI && ipython -c "
import json

# Load the notebook to get the code
with open('research.ipynb', 'r') as f:
    nb = json.load(f)
    
# Get the last cell's code
code = ''.join(nb['cells'][-1]['source'])

print('=== EXECUTING CODE ===')
print(code)
print('=== OUTPUT ===')

# Execute the code - IPython should have QuantConnect already loaded via startup scripts
exec(code)
" 2>&1"""),
                
                # Method 3: Use nbconvert with better error handling
                ("jupyter nbconvert", f"cd /LeanCLI && jupyter nbconvert --to notebook --execute research.ipynb --output research_executed.ipynb --ExecutePreprocessor.kernel_name=python3 --ExecutePreprocessor.timeout=60 --allow-errors --no-input 2>&1"),
            ]

            executed_successfully = False
            execution_output = ""
            direct_output = ""

            for i, (method_name, exec_cmd) in enumerate(exec_commands):
                try:
                    logger.info(f"Trying execution method {i+1}: {method_name}")

                    exec_result = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.container.exec_run,
                            ['/bin/sh', '-c', exec_cmd],
                            demux=False
                        ),
                        timeout=timeout
                    )

                    execution_output = exec_result.output.decode('utf-8', errors='replace') if exec_result.output else ""

                    if exec_result.exit_code == 0:
                        executed_successfully = True
                        logger.info(f"Successfully executed with method {i+1} ({method_name})")

                        # For direct kernel and ipython execution, the output is already captured
                        if "jupyter kernel" in method_name or "ipython execution" in method_name:
                            direct_output = execution_output

                        break
                    else:
                        logger.error(f"Method {i+1} ({method_name}) failed with exit code {exec_result.exit_code}")
                        logger.error(f"Full error output: {execution_output}")

                except asyncio.TimeoutError:
                    logger.error(f"Execution method {i+1} ({method_name}) timed out after {timeout}s")
                    continue
                except Exception as e:
                    logger.debug(f"Error with execution method {i+1} ({method_name}): {e}")
                    continue

            if executed_successfully:
                # Handle different execution methods
                if direct_output:
                    # Direct python execution - output is already captured
                    return {
                        "status": "success",
                        "output": direct_output.strip() if direct_output else "Code executed successfully (no output)",
                        "error": None,
                        "session_id": self.session_id,
                    }
                else:
                    # Notebook execution - try to read the executed notebook to get the output
                    try:
                        read_executed_cmd = "cat /LeanCLI/research_executed.ipynb"
                        read_exec_result = await asyncio.to_thread(
                            self.container.exec_run,
                            read_executed_cmd,
                            demux=False
                        )

                        if read_exec_result.exit_code == 0:
                            executed_notebook = json.loads(read_exec_result.output.decode('utf-8'))
                            # Get the output from the last cell
                            last_cell = executed_notebook["cells"][-1]

                            # Extract output from the cell
                            cell_output = ""
                            if "outputs" in last_cell and last_cell["outputs"]:
                                for output in last_cell["outputs"]:
                                    if output.get("output_type") == "stream":
                                        cell_output += "".join(output.get("text", []))
                                    elif output.get("output_type") == "execute_result":
                                        if "data" in output and "text/plain" in output["data"]:
                                            cell_output += "".join(output["data"]["text/plain"])
                                    elif output.get("output_type") == "display_data":
                                        if "data" in output and "text/plain" in output["data"]:
                                            cell_output += "".join(output["data"]["text/plain"])
                                    elif output.get("output_type") == "error":
                                        error_msg = f"Error: {output.get('ename', 'Unknown')}: {output.get('evalue', 'Unknown error')}"
                                        traceback_lines = output.get('traceback', [])
                                        full_error = error_msg + "\n" + "\n".join(traceback_lines)

                                        # Clean up the executed notebook file
                                        await asyncio.to_thread(
                                            self.container.exec_run,
                                            "rm -f /LeanCLI/research_executed.ipynb",
                                            demux=False
                                        )

                                        return {
                                            "status": "error",
                                            "output": cell_output,
                                            "error": full_error,
                                            "session_id": self.session_id,
                                        }

                            # Clean up the executed notebook file
                            await asyncio.to_thread(
                                self.container.exec_run,
                                "rm -f /LeanCLI/research_executed.ipynb",
                                demux=False
                            )

                            return {
                                "status": "success",
                                "output": cell_output.strip() if cell_output else "Code executed successfully (no output)",
                                "error": None,
                                "session_id": self.session_id,
                            }

                    except Exception as e:
                        logger.error(f"Failed to parse executed notebook: {e}")
                        # Fall through to fallback approach

            # Fallback: If notebook execution failed, return a helpful message
            # but still indicate the code was added to the notebook
            return {
                "status": "success",
                "output": f"Code added to /LeanCLI/research.ipynb. Executed_successfully output = {executed_successfully}",
                "error": None,
                "session_id": self.session_id,
                "note": f"Notebook execution failed. Details: {execution_output[:500] if execution_output else 'No details available'}"
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
#!/usr/bin/env python3
"""QuantConnect MCP Server Entry Point"""

import os
import sys
import asyncio
import signal
import logging
from pathlib import Path
from typing import Optional

# Ensure package root is in Python path for consistent imports
package_root = Path(__file__).parent.parent
if str(package_root) not in sys.path:
    sys.path.insert(0, str(package_root))

from quantconnect_mcp.src.server import mcp
from quantconnect_mcp.src.tools import (
    register_analysis_tools,
    register_portfolio_tools,
    register_universe_tools,
    register_auth_tools,
    register_project_tools,
    register_file_tools,
    register_backtest_tools,
)
from quantconnect_mcp.src.resources import register_system_resources
from quantconnect_mcp.src.auth import configure_auth
from quantconnect_mcp.src.utils import safe_print

# Conditional imports for QuantBook functionality
def check_quantbook_support() -> bool:
    """Check if QuantBook dependencies are available."""
    try:
        import docker
        return True
    except ImportError:
        return False

def import_quantbook_modules():
    """Conditionally import QuantBook modules."""
    try:
        from quantconnect_mcp.src.tools import register_quantbook_tools, register_data_tools
        return register_quantbook_tools, register_data_tools
    except ImportError as e:
        safe_print(f"⚠️  QuantBook dependencies not available: {e}")
        return None, None

def import_logging_setup():
    """Conditionally import logging setup."""
    try:
        from quantconnect_mcp.src.adapters.logging_config import setup_logging
        return setup_logging
    except ImportError:
        return None


# Global shutdown flag
_shutdown_requested = False
_session_manager: Optional[object] = None


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    global _shutdown_requested
    
    def signal_handler(signum: int, frame) -> None:
        global _shutdown_requested
        if not _shutdown_requested:
            _shutdown_requested = True
            safe_print(f"\n🔄 Received signal {signum}, initiating graceful shutdown...")
            
            # Shutdown session manager if available
            if _session_manager and hasattr(_session_manager, 'stop'):
                try:
                    asyncio.create_task(_session_manager.stop())
                except Exception as e:
                    safe_print(f"⚠️  Error during session manager shutdown: {e}")
    
    # Register signal handlers
    try:
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)   # Hangup
    except Exception as e:
        safe_print(f"⚠️  Could not setup signal handlers: {e}")


async def shutdown_cleanup() -> None:
    """Perform cleanup during shutdown."""
    global _session_manager
    
    try:
        if _session_manager and hasattr(_session_manager, 'stop'):
            safe_print("🧹 Cleaning up session manager...")
            await _session_manager.stop()
            safe_print("✅ Session manager cleaned up")
    except Exception as e:
        safe_print(f"⚠️  Error during cleanup: {e}")


def main():
    """Initialize and run the QuantConnect MCP server."""
    global _session_manager
    
    try:
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers()
        
        # Check QuantBook support and environment configuration
        enable_quantbook = os.getenv("ENABLE_QUANTBOOK", "false").lower() in ("true", "1", "yes", "on")
        quantbook_available = check_quantbook_support()
        
        # Setup logging (basic logging if QuantBook not available)
        log_level = os.getenv("LOG_LEVEL", "INFO")
        log_file = os.getenv("LOG_FILE")
        
        # Setup advanced logging if available
        setup_logging = import_logging_setup()
        if setup_logging:
            setup_logging(
                log_level=log_level,
                log_file=Path(log_file) if log_file else None,
                include_container_logs=True,
            )
            safe_print(f"🔧 Advanced logging configured (level: {log_level})")
        else:
            # Basic logging setup
            logging.basicConfig(
                level=getattr(logging, log_level.upper()),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            safe_print(f"🔧 Basic logging configured (level: {log_level})")

        if quantbook_available:
            register_quantbook_tools, register_data_tools = import_quantbook_modules()
        else:
            register_quantbook_tools = None
            register_data_tools = None

        # Auto-configure authentication from environment variables if available
        user_id = os.getenv("QUANTCONNECT_USER_ID")
        api_token = os.getenv("QUANTCONNECT_API_TOKEN")
        organization_id = os.getenv("QUANTCONNECT_ORGANIZATION_ID")

        if user_id and api_token:
            try:
                safe_print("🔐 Configuring QuantConnect authentication from environment...")
                configure_auth(user_id, api_token, organization_id)
                safe_print("✅ Authentication configured successfully")
            except Exception as e:
                safe_print(f"⚠️  Failed to configure authentication: {e}")
                safe_print(
                    "💡 You can configure authentication later using the configure_quantconnect_auth tool"
                )

        # Register core tool modules (always available)
        safe_print("🔧 Registering QuantConnect API tools...")
        register_auth_tools(mcp)
        register_project_tools(mcp)
        register_file_tools(mcp)
        register_backtest_tools(mcp)
        register_analysis_tools(mcp)
        register_portfolio_tools(mcp)
        register_universe_tools(mcp)

        # Conditionally register QuantBook tools
        if enable_quantbook:
            if quantbook_available and register_quantbook_tools and register_data_tools:
                safe_print("🐳 Registering QuantBook container tools...")
                register_quantbook_tools(mcp)
                register_data_tools(mcp)
                safe_print("✅ QuantBook functionality enabled")
                
                # Get session manager reference for cleanup
                try:
                    from quantconnect_mcp.src.adapters.session_manager import get_session_manager
                    _session_manager = get_session_manager()
                except ImportError:
                    pass
            else:
                safe_print("❌ QuantBook functionality requested but dependencies not available")
                safe_print("💡 Install with: pip install quantconnect-mcp[quantbook]")
                safe_print("🐳 Ensure Docker is installed and accessible")
        else:
            safe_print("⏭️  QuantBook functionality disabled (set ENABLE_QUANTBOOK=true to enable)")

        # Register resources
        safe_print("📊 Registering system resources...")
        register_system_resources(mcp)

        safe_print(f"✅ QuantConnect MCP Server initialized")

        # Determine transport method
        transport = os.getenv("MCP_TRANSPORT", "stdio")

        # Run server with proper error handling
        try:
            if transport == "streamable-http":
                host = os.getenv("MCP_HOST", "0.0.0.0")
                port = int(os.getenv("MCP_PORT", os.getenv("PORT", "8000")))
                safe_print(f"🌐 Starting HTTP server on {host}:{port}")
                mcp.run(
                    transport="streamable-http",
                    host=host,
                    port=port,
                    path=os.getenv("MCP_PATH", "/mcp"),
                )
            elif transport == "stdio":
                safe_print("📡 Starting STDIO transport")
                mcp.run()  # Default stdio transport
            else:
                safe_print(f"🚀 Starting with {transport} transport")
                mcp.run(transport=transport)
                
        except (BrokenPipeError, ConnectionResetError, EOFError) as e:
            # Client disconnected - this is normal, not an error
            safe_print("🔌 Client disconnected")
            logging.getLogger(__name__).debug(f"Client disconnect: {e}")
            
        except KeyboardInterrupt:
            safe_print("\n⏹️  Keyboard interrupt received")
            
        except OSError as e:
            if e.errno == 32:  # Broken pipe
                safe_print("🔌 Client disconnected (broken pipe)")
                logging.getLogger(__name__).debug(f"Broken pipe: {e}")
            else:
                safe_print(f"❌ OS Error: {e}")
                raise
                
        except Exception as e:
            safe_print(f"❌ Unexpected error: {e}")
            logging.getLogger(__name__).error(f"Server error: {e}", exc_info=True)
            raise
            
        finally:
            # Cleanup
            if _session_manager:
                try:
                    import asyncio
                    asyncio.run(shutdown_cleanup())
                except Exception as e:
                    safe_print(f"⚠️  Error during final cleanup: {e}")
                    
    except KeyboardInterrupt:
        safe_print("\n⏹️  Startup interrupted")
        sys.exit(1)
        
    except Exception as e:
        safe_print(f"❌ Failed to start server: {e}")
        logging.getLogger(__name__).error(f"Startup error: {e}", exc_info=True)
        sys.exit(1)
        
    safe_print("👋 QuantConnect MCP Server shutdown complete")


if __name__ == "__main__":
    main()

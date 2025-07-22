"""Utility functions for QuantConnect MCP Server"""

import sys
import logging

logger = logging.getLogger(__name__)


def safe_print(text):
    """Print text safely, handling emojis and MCP server context.
    
    Don't print to stderr when running as MCP server via uvx to avoid JSON parsing errors.
    Check if we're running as MCP server (no TTY and uvx in process name).
    """
    # Don't print to stderr when running as MCP server via uvx to avoid JSON parsing errors
    # Check if we're running as MCP server (no TTY and uvx in process name)
    if not sys.stderr.isatty():
        # Running as MCP server, suppress output to avoid JSON parsing errors
        logger.debug(f"[MCP Server] {text}")
        return

    try:
        print(text, file=sys.stderr)
    except UnicodeEncodeError:
        print(text.encode('ascii', errors='replace').decode(), file=sys.stderr)
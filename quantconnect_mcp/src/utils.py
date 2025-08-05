"""Utility functions for QuantConnect MCP Server"""

import sys
import logging

logger = logging.getLogger(__name__)


def safe_print(text):
    """Print text safely, handling emojis, broken pipes, and MCP server context.
    
    Don't print to stderr when running as MCP server via uvx to avoid JSON parsing errors.
    Check if we're running as MCP server (no TTY and uvx in process name).
    """
    # Don't print to stderr when running as MCP server via uvx to avoid JSON parsing errors
    # Check if we're running as MCP server (no TTY and uvx in process name)
    if not sys.stderr.isatty():
        # Running as MCP server, suppress output to avoid JSON parsing errors
        try:
            logger.debug(f"[MCP Server] {text}")
        except Exception:
            # If logging fails, just ignore silently
            pass
        return

    try:
        print(text, file=sys.stderr)
        sys.stderr.flush()  # Ensure immediate output
    except (UnicodeEncodeError, OSError, BrokenPipeError):
        try:
            # Handle broken pipes and encoding errors gracefully
            if isinstance(text, str):
                # Try ASCII fallback for encoding issues
                safe_text = text.encode('ascii', errors='replace').decode()
                print(safe_text, file=sys.stderr)
                sys.stderr.flush()
        except (OSError, BrokenPipeError):
            # If we still can't print, log instead
            try:
                logger.info(f"[Output] {text}")
            except:
                # Final fallback - just ignore if nothing works
                pass
"""Logging configuration for QuantConnect MCP Server"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    include_container_logs: bool = True,
) -> None:
    """
    Setup logging configuration for the MCP server.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        include_container_logs: Whether to include container-specific logging
    """
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler - MUST use stderr to avoid contaminating MCP JSON-RPC on stdout
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    
    # Setup specific loggers with appropriate levels
    loggers = {
        'quantconnect_mcp': logging.DEBUG,
        'quantconnect_mcp.adapters': logging.DEBUG,
        'quantconnect_mcp.adapters.research_session': logging.INFO,
        'quantconnect_mcp.adapters.session_manager': logging.INFO,
        'quantconnect_mcp.tools': logging.INFO,
        'docker': logging.WARNING,  # Reduce noise from Docker client
        'urllib3': logging.WARNING,  # Reduce noise from HTTP requests
    }
    
    for logger_name, level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    # Log startup message
    root_logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")


def get_container_logger(session_id: str) -> logging.Logger:
    """Get a logger specific to a container session."""
    return logging.getLogger(f"quantconnect_mcp.container.{session_id}")


class SecurityLogger:
    """Logger for security-related events."""
    
    def __init__(self):
        self.logger = logging.getLogger("quantconnect_mcp.security")
    
    def log_session_created(self, session_id: str, container_id: str) -> None:
        """Log session creation."""
        self.logger.info(
            f"SECURITY: Session created - ID: {session_id}, Container: {container_id}"
        )
    
    def log_session_destroyed(self, session_id: str, reason: str = "normal") -> None:
        """Log session destruction."""
        self.logger.info(
            f"SECURITY: Session destroyed - ID: {session_id}, Reason: {reason}"
        )
    
    def log_code_execution(self, session_id: str, code_hash: str, success: bool) -> None:
        """Log code execution attempts."""
        status = "SUCCESS" if success else "FAILED"
        self.logger.info(
            f"SECURITY: Code execution {status} - Session: {session_id}, Hash: {code_hash}"
        )
    
    def log_security_violation(self, session_id: str, violation_type: str, details: str) -> None:
        """Log security violations."""
        self.logger.warning(
            f"SECURITY VIOLATION: {violation_type} - Session: {session_id}, Details: {details}"
        )
    
    def log_resource_limit_hit(self, session_id: str, resource: str, limit: str) -> None:
        """Log when resource limits are hit."""
        self.logger.warning(
            f"SECURITY: Resource limit hit - Session: {session_id}, Resource: {resource}, Limit: {limit}"
        )


# Global security logger instance
security_logger = SecurityLogger()
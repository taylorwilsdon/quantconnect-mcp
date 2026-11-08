"""FastMCP server wiring and the ``quantconnect-mcp`` command-line entry point."""

import hmac
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any

import httpx2
from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.lifespan import lifespan
from pydantic import ValidationError

from quantconnect_mcp import __version__
from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.settings import Settings
from quantconnect_mcp.tools import ALL_TOOLS

INSTRUCTIONS = """\
Tools for the QuantConnect cloud platform and its LEAN algorithmic trading engine.

Typical research loop:
1. create_project, then create_file / update_file_content to write the algorithm
   (main.py for Python, Main.cs for C#). check_syntax catches errors before compiling.
2. compile_project waits for the build and returns its state; only a BuildSuccess
   compile ID can be backtested, optimized, or deployed.
3. create_backtest, then poll read_backtest until it reports completed; dig in with
   read_backtest_orders, read_backtest_insights, read_backtest_chart, read_backtest_report.
4. For parameter sweeps, estimate_optimization_time before create_optimization.

Use search_quantconnect and enhance_error when unsure about the LEAN API or an error.

Live trading tools act on real brokerage accounts. Confirm with the user before
create_live_algorithm, liquidate_live_algorithm, stop_live_algorithm, or sending
live commands, and prefer the QuantConnectBrokerage paper account unless told otherwise.
"""

logger = logging.getLogger(__name__)


class BearerTokenVerifier(TokenVerifier):
    """Admit HTTP clients that present one shared bearer token."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token.encode()

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(token.encode(), self._token):
            return AccessToken(token=token, client_id="quantconnect-mcp", scopes=[])
        return None


def build_server(
    settings: Settings, transport: httpx2.AsyncBaseTransport | None = None
) -> FastMCP[Any]:
    """Create the MCP server. ``transport`` replaces the network layer in tests."""

    @lifespan
    async def client_lifespan(server: FastMCP[Any]) -> AsyncIterator[dict[str, Any]]:
        async with aclosing(QuantConnectClient(settings, transport)) as client:
            yield {"client": client}

    token = settings.mcp_auth_token
    return FastMCP(
        name="QuantConnect",
        instructions=INSTRUCTIONS,
        version=__version__,
        lifespan=client_lifespan,
        tools=ALL_TOOLS,
        on_duplicate="error",
        mask_error_details=True,
        auth=BearerTokenVerifier(token.get_secret_value()) if token else None,
    )


def load_settings() -> Settings:
    """Read settings, exiting with a readable message when they are incomplete."""
    try:
        return Settings()
    except ValidationError as exc:
        names = sorted({str(error["loc"][0]).upper() for error in exc.errors()})
        sys.exit(
            f"quantconnect-mcp: missing or invalid settings: {', '.join(names)}. "
            "Set them as environment variables."
        )


def main() -> None:
    """Run the server with the configured transport."""
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if settings.mcp_transport == "stdio":
        build_server(settings).run()
        return
    if settings.mcp_auth_token is None and not settings.binds_loopback:
        sys.exit(
            f"quantconnect-mcp: refusing to serve HTTP on {settings.mcp_host} without "
            "MCP_AUTH_TOKEN. These tools can trade live; set a token or bind to 127.0.0.1."
        )
    logger.info(
        "Serving MCP over HTTP at %s:%s%s", settings.mcp_host, settings.mcp_port, settings.mcp_path
    )
    build_server(settings).run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
        path=settings.mcp_path,
    )

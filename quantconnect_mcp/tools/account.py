"""Account, authentication, and platform metadata tools."""

from typing import Any, Literal

from fastmcp.tools import tool

from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.tools._shared import CLIENT, MUTATING, READ_ONLY

OAuthBrokerage = Literal["alpaca", "tradestation", "charlesschwab", "tastytrade"]


@tool(annotations=READ_ONLY)
async def validate_quantconnect_auth(qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """Check that the configured QuantConnect credentials are accepted by the API."""
    await qc.post("authenticate")
    return {"authenticated": True, "user_id": qc.user_id}


@tool(annotations=READ_ONLY)
async def get_auth_status(qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """Show which QuantConnect account the server is configured for, without calling the API."""
    return {"user_id": qc.user_id, "organization_id": qc.configured_organization_id}


@tool(annotations=READ_ONLY)
async def read_account(qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """Read the organization account: organization ID, credit balance, and card on file."""
    return await qc.post("account/read")


@tool(annotations=READ_ONLY)
async def read_lean_versions(qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """List the LEAN engine versions available for backtests and live deployments."""
    return await qc.post("lean/versions/read")


@tool(annotations=MUTATING)
async def authorize_connection(
    brokerage: OAuthBrokerage, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Start the OAuth flow that links an OAuth-based brokerage to QuantConnect.

    Returns an authorization URL. A human must open it in a browser and approve
    access; the brokerage can then be used with create_live_algorithm.

    Args:
        brokerage: The brokerage to authorize.
    """
    url = await qc.redirect_location("live/auth0/authorize", brokerage=brokerage)
    return {"brokerage": brokerage, "authorization_url": url}


TOOLS = (
    validate_quantconnect_auth,
    get_auth_status,
    read_account,
    read_lean_versions,
    authorize_connection,
)

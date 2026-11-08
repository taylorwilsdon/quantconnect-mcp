"""QuantConnectClient: signing, error mapping, retries, and organization lookup."""

from base64 import b64decode
from hashlib import sha256

import httpx2
import pytest

from quantconnect_mcp.client import QuantConnectClient, QuantConnectError
from quantconnect_mcp.settings import Settings
from tests.conftest import ORGANIZATION_ID, FakeQuantConnect, body_of, endpoint_of


@pytest.fixture
def client(settings: Settings, api: FakeQuantConnect) -> QuantConnectClient:
    return QuantConnectClient(settings, api.transport)


async def test_requests_are_signed(client: QuantConnectClient, api: FakeQuantConnect) -> None:
    await client.post("projects/read")

    headers = api.last.headers
    scheme, credentials = headers["Authorization"].split()
    user_id, digest = b64decode(credentials).decode().split(":")
    assert scheme == "Basic"
    assert user_id == "123456"
    assert digest == sha256(f"secret-token:{headers['Timestamp']}".encode()).hexdigest()
    assert headers["User-Agent"].startswith("quantconnect-mcp/")


async def test_none_arguments_are_omitted(
    client: QuantConnectClient, api: FakeQuantConnect
) -> None:
    await client.post("projects/update", projectId=1, name=None, description="d")

    assert body_of(api.last) == {"projectId": 1, "description": "d"}


async def test_payload_is_returned_without_envelope(
    client: QuantConnectClient, api: FakeQuantConnect
) -> None:
    api.reply("projects/read", {"success": True, "errors": [], "projects": []})

    assert await client.post("projects/read") == {"projects": []}


async def test_warnings_on_success_are_kept(
    client: QuantConnectClient, api: FakeQuantConnect
) -> None:
    api.reply("projects/read", {"success": True, "errors": ["careful"], "projects": []})

    assert await client.post("projects/read") == {"errors": ["careful"], "projects": []}


async def test_responses_without_success_flag_are_accepted(
    client: QuantConnectClient, api: FakeQuantConnect
) -> None:
    api.reply("backtests/orders/read", {"orders": [], "length": 0})

    assert await client.post("backtests/orders/read") == {"orders": [], "length": 0}


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx2.Response(401), "rejected the credentials"),
        (httpx2.Response(500, text="boom"), "HTTP 500: boom"),
        (httpx2.Response(200, text="<html>"), "not JSON"),
        (httpx2.Response(200, json={"success": False, "errors": ["a", "b"]}), "failed: a; b"),
        (httpx2.Response(200, json={"success": False}), "no error details"),
    ],
)
async def test_failures_raise_quantconnect_error(
    response: httpx2.Response, message: str, client: QuantConnectClient, api: FakeQuantConnect
) -> None:
    api.reply("projects/read", response)

    with pytest.raises(QuantConnectError, match=message):
        await client.post("projects/read")


async def test_rate_limit_is_retried_once(
    client: QuantConnectClient, api: FakeQuantConnect
) -> None:
    api.reply(
        "projects/read",
        httpx2.Response(429, headers={"Retry-After": "0"}),
        {"success": True, "projects": []},
    )

    assert await client.post("projects/read") == {"projects": []}
    assert len(api.requests) == 2


async def test_network_errors_raise_quantconnect_error(
    client: QuantConnectClient, api: FakeQuantConnect
) -> None:
    def unreachable(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    api.handler = unreachable  # type: ignore[method-assign]

    with pytest.raises(QuantConnectError, match="could not reach QuantConnect"):
        await client.post("projects/read")


async def test_redirect_location(client: QuantConnectClient, api: FakeQuantConnect) -> None:
    api.reply("live/auth0/authorize", httpx2.Response(302, headers={"Location": "https://x"}))

    assert await client.redirect_location("live/auth0/authorize", brokerage="alpaca") == "https://x"


async def test_missing_redirect_raises(client: QuantConnectClient) -> None:
    with pytest.raises(QuantConnectError, match="did not return a redirect"):
        await client.redirect_location("live/auth0/authorize", brokerage="alpaca")


async def test_organization_id_prefers_explicit_then_configured(
    client: QuantConnectClient, api: FakeQuantConnect
) -> None:
    assert await client.organization_id("explicit") == "explicit"
    assert await client.organization_id() == ORGANIZATION_ID
    assert api.requests == []


async def test_organization_id_falls_back_to_account(
    settings: Settings, api: FakeQuantConnect
) -> None:
    settings = settings.model_copy(update={"quantconnect_organization_id": None})
    client = QuantConnectClient(settings, api.transport)
    api.reply("account/read", {"success": True, "organizationId": "from-account"})

    assert await client.organization_id() == "from-account"
    assert await client.organization_id() == "from-account"
    assert [endpoint_of(request) for request in api.requests] == ["account/read"]


async def test_organization_id_requires_account_default(
    settings: Settings, api: FakeQuantConnect
) -> None:
    settings = settings.model_copy(update={"quantconnect_organization_id": None})
    client = QuantConnectClient(settings, api.transport)
    api.reply("account/read", {"success": True})

    with pytest.raises(QuantConnectError, match="QUANTCONNECT_ORGANIZATION_ID"):
        await client.organization_id()

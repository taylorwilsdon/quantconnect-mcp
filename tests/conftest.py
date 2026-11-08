"""Shared fixtures: the MCP server wired to an in-memory fake of the QuantConnect API."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx2
import pytest
from fastmcp import Client

from quantconnect_mcp.server import build_server
from quantconnect_mcp.settings import Settings

API_URL = "https://qc.test/api/v2/"
ORGANIZATION_ID = "org-1"


class FakeQuantConnect:
    """Record every request and answer with canned responses, keyed by endpoint.

    Endpoints without a canned response answer ``{"success": true}``. Queue several
    responses for one endpoint to script a sequence; the last one repeats.
    """

    def __init__(self) -> None:
        self.requests: list[httpx2.Request] = []
        self._replies: dict[str, list[httpx2.Response]] = {}

    def reply(self, endpoint: str, *responses: httpx2.Response | dict[str, Any]) -> None:
        self._replies[endpoint] = [
            response
            if isinstance(response, httpx2.Response)
            else httpx2.Response(200, json=response)
            for response in responses
        ]

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        queue = self._replies.get(endpoint_of(request))
        if not queue:
            return httpx2.Response(200, json={"success": True})
        return queue.pop(0) if len(queue) > 1 else queue[0]

    @property
    def transport(self) -> httpx2.MockTransport:
        # Resolve the handler per request so a test can swap it after the server starts.
        return httpx2.MockTransport(lambda request: self.handler(request))

    @property
    def last(self) -> httpx2.Request:
        return self.requests[-1]


def endpoint_of(request: httpx2.Request) -> str:
    return request.url.path.removeprefix(httpx2.URL(API_URL).path)


def body_of(request: httpx2.Request) -> dict[str, Any]:
    body: dict[str, Any] = json.loads(request.content)
    return body


@pytest.fixture
def settings() -> Settings:
    return Settings(
        quantconnect_user_id="123456",
        quantconnect_api_token="secret-token",
        quantconnect_organization_id=ORGANIZATION_ID,
        quantconnect_api_url=API_URL,
    )


@pytest.fixture
def api() -> FakeQuantConnect:
    return FakeQuantConnect()


@pytest.fixture
async def mcp(settings: Settings, api: FakeQuantConnect) -> AsyncIterator[Client[Any]]:
    async with Client(build_server(settings, api.transport)) as client:
        yield client

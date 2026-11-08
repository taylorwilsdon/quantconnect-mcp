"""Async client for the QuantConnect REST API v2."""

import asyncio
import time
from base64 import b64encode
from collections.abc import Generator
from hashlib import sha256
from typing import Any

import httpx2
from fastmcp.exceptions import ToolError

from quantconnect_mcp import __version__
from quantconnect_mcp.settings import Settings

MAX_ERROR_BODY = 500
MAX_RETRY_AFTER_SECONDS = 30.0


class QuantConnectError(ToolError):
    """The QuantConnect API rejected a request or reported a failure."""


class QuantConnectAuth(httpx2.Auth):
    """Sign each request with QuantConnect's timestamped SHA-256 token scheme."""

    def __init__(self, user_id: str, api_token: str) -> None:
        self._user_id = user_id
        self._api_token = api_token

    def auth_flow(
        self, request: httpx2.Request
    ) -> Generator[httpx2.Request, httpx2.Response, None]:
        timestamp = str(int(time.time()))
        digest = sha256(f"{self._api_token}:{timestamp}".encode()).hexdigest()
        credentials = b64encode(f"{self._user_id}:{digest}".encode()).decode()
        request.headers["Authorization"] = f"Basic {credentials}"
        request.headers["Timestamp"] = timestamp
        yield request


class QuantConnectClient:
    """A pooled, authenticated connection to the QuantConnect API.

    Every call returns the decoded JSON payload with the ``success`` and ``errors``
    envelope removed, or raises :class:`QuantConnectError`.

    Deliberately not an async context manager: FastMCP's ``Depends`` would enter and
    exit it around every tool call, closing the shared pool. Use ``aclosing`` instead.
    """

    def __init__(self, settings: Settings, transport: httpx2.AsyncBaseTransport | None = None):
        self.user_id = settings.quantconnect_user_id
        self.configured_organization_id = settings.quantconnect_organization_id
        self._default_organization_id = settings.quantconnect_organization_id
        self._http = httpx2.AsyncClient(
            base_url=settings.quantconnect_api_url,
            auth=QuantConnectAuth(
                settings.quantconnect_user_id,
                settings.quantconnect_api_token.get_secret_value(),
            ),
            timeout=httpx2.Timeout(settings.request_timeout, connect=10.0),
            transport=transport or httpx2.AsyncHTTPTransport(retries=3),
            headers={"User-Agent": f"quantconnect-mcp/{__version__}"},
        )

    async def aclose(self) -> None:
        """Close the connection pool."""
        await self._http.aclose()

    async def post(self, endpoint: str, **payload: Any) -> dict[str, Any]:
        """POST a JSON body to ``endpoint``. Arguments set to ``None`` are omitted."""
        body = {key: value for key, value in payload.items() if value is not None}
        return await self._send(endpoint, json=body)

    async def upload(
        self, endpoint: str, fields: dict[str, str], files: dict[str, tuple[str, bytes]]
    ) -> dict[str, Any]:
        """POST a multipart form to ``endpoint``."""
        return await self._send(endpoint, data=fields, files=files)

    async def redirect_location(self, endpoint: str, **payload: Any) -> str:
        """POST a JSON body to an endpoint that answers with a redirect; return its target."""
        response = await self._request(endpoint, json=payload)
        if response.is_redirect:
            return response.headers["Location"]
        _parse(endpoint, response)
        raise QuantConnectError(f"{endpoint} did not return a redirect URL")

    async def organization_id(self, explicit: str | None = None) -> str:
        """Resolve an organization ID: explicit, configured, or the account default."""
        if explicit:
            return explicit
        if self._default_organization_id is None:
            account = await self.post("account/read")
            self._default_organization_id = str(account["organizationId"])
        return self._default_organization_id

    async def _send(self, endpoint: str, **request: Any) -> dict[str, Any]:
        return _parse(endpoint, await self._request(endpoint, **request))

    async def _request(self, endpoint: str, **request: Any) -> httpx2.Response:
        try:
            response = await self._http.post(endpoint, **request)
            if response.status_code == httpx2.codes.TOO_MANY_REQUESTS:
                await asyncio.sleep(_retry_after(response))
                response = await self._http.post(endpoint, **request)
        except httpx2.TransportError as exc:
            raise QuantConnectError(
                f"{endpoint}: could not reach QuantConnect ({type(exc).__name__})"
            ) from exc
        return response


def _retry_after(response: httpx2.Response) -> float:
    try:
        delay = float(response.headers.get("Retry-After", 1))
    except ValueError:
        delay = 1.0
    return min(max(delay, 0.0), MAX_RETRY_AFTER_SECONDS)


def _parse(endpoint: str, response: httpx2.Response) -> dict[str, Any]:
    if response.status_code == httpx2.codes.UNAUTHORIZED:
        raise QuantConnectError(
            "QuantConnect rejected the credentials (HTTP 401). Check QUANTCONNECT_USER_ID "
            "and QUANTCONNECT_API_TOKEN, and that the system clock is accurate."
        )
    if response.is_error:
        raise QuantConnectError(
            f"{endpoint} failed with HTTP {response.status_code}: {response.text[:MAX_ERROR_BODY]}"
        )
    try:
        data: dict[str, Any] = response.json()
    except ValueError as exc:
        raise QuantConnectError(f"{endpoint} returned a response that is not JSON") from exc
    errors = data.pop("errors", None) or []
    if data.pop("success", None) is False:
        detail = "; ".join(map(str, errors)) or "no error details were returned"
        raise QuantConnectError(f"{endpoint} failed: {detail}")
    return data

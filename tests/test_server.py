"""Settings loading, startup guards, and HTTP bearer authentication."""

from pathlib import Path

import httpx2
import pytest
from pydantic import SecretStr

from quantconnect_mcp import server
from quantconnect_mcp.server import BearerTokenVerifier, build_server
from quantconnect_mcp.settings import Settings


@pytest.fixture(autouse=True)
def clean_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Isolate tests from the developer's shell and the repo's working directory."""
    monkeypatch.chdir(tmp_path_factory.mktemp("cwd"))
    for name in (
        "QUANTCONNECT_USER_ID",
        "QUANTCONNECT_API_TOKEN",
        "QUANTCONNECT_ORGANIZATION_ID",
        "MCP_TRANSPORT",
        "MCP_HOST",
        "MCP_PORT",
        "PORT",
        "MCP_AUTH_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)


def set_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUANTCONNECT_USER_ID", "123")
    monkeypatch.setenv("QUANTCONNECT_API_TOKEN", "hunter2")


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    set_credentials(monkeypatch)
    monkeypatch.setenv("MCP_PORT", "9000")

    settings = Settings()

    assert settings.quantconnect_user_id == "123"
    assert settings.quantconnect_api_token.get_secret_value() == "hunter2"
    assert "hunter2" not in repr(settings)
    assert settings.mcp_port == 9000


def test_host_project_port_and_dotenv_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """A client may launch the server inside another project with its own PORT and .env."""
    set_credentials(monkeypatch)
    monkeypatch.setenv("PORT", "$APP_PORT")
    Path(".env").write_text("MCP_PORT=$APP_PORT\nLOG_LEVEL=verbose\n")

    settings = Settings()

    assert settings.mcp_transport == "stdio"
    assert settings.mcp_port == 8000


def test_blank_optional_settings_are_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    set_credentials(monkeypatch)
    monkeypatch.setenv("QUANTCONNECT_ORGANIZATION_ID", "")
    monkeypatch.setenv("MCP_AUTH_TOKEN", "")

    settings = Settings()

    assert settings.quantconnect_organization_id is None
    assert settings.mcp_auth_token is None


@pytest.mark.parametrize(
    ("host", "loopback"),
    [
        ("127.0.0.1", True),
        ("::1", True),
        ("localhost", True),
        ("0.0.0.0", False),
        ("10.0.0.5", False),
        ("example.com", False),
    ],
)
def test_binds_loopback(host: str, loopback: bool, settings: Settings) -> None:
    assert settings.model_copy(update={"mcp_host": host}).binds_loopback is loopback


def test_missing_credentials_exit_with_names() -> None:
    with pytest.raises(SystemExit) as exit_info:
        server.main()

    assert "QUANTCONNECT_API_TOKEN" in str(exit_info.value.code)
    assert "QUANTCONNECT_USER_ID" in str(exit_info.value.code)


def test_public_http_without_token_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    set_credentials(monkeypatch)
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_HOST", "0.0.0.0")

    with pytest.raises(SystemExit) as exit_info:
        server.main()

    assert "MCP_AUTH_TOKEN" in str(exit_info.value.code)


async def test_bearer_token_verifier() -> None:
    verifier = BearerTokenVerifier("s3cret")

    assert await verifier.verify_token("s3cret") is not None
    assert await verifier.verify_token("wrong") is None


async def test_http_requires_bearer_token(settings: Settings) -> None:
    secured = settings.model_copy(update={"mcp_auth_token": SecretStr("s3cret")})
    app = build_server(secured).http_app(path="/mcp")
    async with httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app), base_url="http://test"
    ) as http:
        response = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "ping"})

    assert response.status_code == 401

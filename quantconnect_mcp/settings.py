"""Runtime configuration, read from environment variables."""

from ipaddress import ip_address
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

LOOPBACK_HOSTNAMES = frozenset({"localhost"})


class Settings(BaseSettings):
    """Server settings. Field names map to upper-case environment variables."""

    # No env_file: MCP clients launch the server from the user's own project, so a
    # .env there belongs to that project. Use `uv run --env-file` to load one.
    model_config = SettingsConfigDict(env_ignore_empty=True)

    quantconnect_user_id: str
    quantconnect_api_token: SecretStr
    quantconnect_organization_id: str | None = None
    quantconnect_api_url: str = "https://www.quantconnect.com/api/v2/"
    request_timeout: float = Field(60.0, gt=0)

    mcp_transport: Literal["stdio", "streamable-http"] = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8000
    mcp_path: str = "/mcp"
    mcp_auth_token: SecretStr | None = None

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @property
    def binds_loopback(self) -> bool:
        """Whether the HTTP transport only listens on the local machine."""
        if self.mcp_host in LOOPBACK_HOSTNAMES:
            return True
        try:
            return ip_address(self.mcp_host).is_loopback
        except ValueError:
            return False

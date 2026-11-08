"""Building blocks shared by every tool module."""

from typing import Annotated, Any, Literal

from fastmcp.dependencies import Depends
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_context
from mcp_types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from quantconnect_mcp.client import QuantConnectClient

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=True)
MUTATING = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=True)
DESTRUCTIVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)

Language = Literal["Py", "C#"]
Index = Annotated[int, Field(ge=0)]


class ApiModel(BaseModel):
    """A nested request object: snake_case for tool callers, camelCase on the wire."""

    model_config = ConfigDict(extra="forbid")

    def to_api(self) -> dict[str, Any]:
        """Serialize for a request body with camelCase keys, leaving out unset optional fields."""
        return {to_camel(key): value for key, value in self.model_dump(exclude_none=True).items()}


class CodeFile(ApiModel):
    """A source file passed to QuantConnect's AI tools."""

    name: str = Field(description="File name, for example main.py")
    content: str = Field(description="Full file contents")


def get_client() -> QuantConnectClient:
    """Return the QuantConnect client created by the server lifespan."""
    client: QuantConnectClient = get_context().lifespan_context["client"]
    return client


CLIENT = Depends(get_client)


def check_range(start: int, end: int, limit: int | None = None) -> None:
    """Validate a ``[start, end)`` window, optionally capped at ``limit`` items (inclusive)."""
    if end <= start:
        raise ToolError(f"end ({end}) must be greater than start ({start})")
    if limit is not None and end - start > limit:
        raise ToolError(f"end - start must be at most {limit}, got {end - start}")

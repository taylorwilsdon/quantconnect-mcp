"""Check every request the tools send against QuantConnect's published OpenAPI spec.

The spec is vendored from github.com/QuantConnect/Documentation
(QuantConnect-Platform-2.0.0.yaml). Refresh it to pick up API changes.
"""

from functools import cache
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastmcp import Client

from tests.cases import CASES, Case
from tests.conftest import FakeQuantConnect, body_of

SPEC_PATH = Path(__file__).parent / "fixtures" / "quantconnect-openapi.yaml"

# Documented on QuantConnect's authentication page but absent from the OpenAPI file.
UNSPECIFIED_ENDPOINTS = frozenset({"authenticate"})


@cache
def spec() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(SPEC_PATH.read_text())
    return loaded


def resolve(schema: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in schema:
        schema = spec()["components"]["schemas"][schema["$ref"].rsplit("/", 1)[-1]]
    return schema


def alternatives(schema: dict[str, Any]) -> list[dict[str, Any]]:
    schema = resolve(schema)
    return [resolve(option) for option in schema.get("oneOf", [schema])]


def violations(value: Any, schema: dict[str, Any], path: str = "body") -> list[str]:
    """List the ways ``value`` breaks ``schema``: unknown or missing keys and bad enums."""
    schema = resolve(schema)
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path}={value!r} is not one of {schema['enum']}"]
    if isinstance(value, list) and "items" in schema:
        return [
            problem
            for index, item in enumerate(value)
            for problem in violations(item, schema["items"], f"{path}[{index}]")
        ]
    properties = schema.get("properties")
    if not isinstance(value, dict) or properties is None:
        return []
    problems = [f"{path}.{key} is not in the spec" for key in value.keys() - properties.keys()]
    problems += [
        f"{path}.{key} is required" for key in set(schema.get("required", [])) - value.keys()
    ]
    for key in value.keys() & properties.keys():
        problems += violations(value[key], properties[key], f"{path}.{key}")
    return problems


def request_schemas(endpoint: str) -> list[dict[str, Any]]:
    operation = spec()["paths"][f"/{endpoint}"]["post"]
    body = operation.get("requestBody")
    if body is None:
        return [{"type": "object", "properties": {}}]
    return alternatives(body["content"]["application/json"]["schema"])


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.tool)
async def test_request_matches_openapi_spec(
    case: Case, mcp: Client[Any], api: FakeQuantConnect
) -> None:
    if case.endpoint in UNSPECIFIED_ENDPOINTS:
        pytest.skip(f"{case.endpoint} is not described by the OpenAPI spec")
    assert f"/{case.endpoint}" in spec()["paths"], f"{case.endpoint} does not exist"

    await mcp.call_tool(case.tool, case.args)

    results = [violations(body_of(api.last), schema) for schema in request_schemas(case.endpoint)]
    assert any(not problems for problems in results), results


def test_object_store_upload_fields_match_spec() -> None:
    form = spec()["paths"]["/object/set"]["post"]["requestBody"]["content"]["multipart/form-data"]
    assert set(resolve(form["schema"])["required"]) == {"organizationId", "key", "objectData"}

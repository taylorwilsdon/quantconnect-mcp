"""Tool behavior through a real MCP client session against the fake API."""

from typing import Any

import httpx2
import pytest
from fastmcp import Client

from quantconnect_mcp.tools import compile as compile_tools
from tests.cases import CASES, SPECIAL_CASES, Case
from tests.conftest import ORGANIZATION_ID, FakeQuantConnect, body_of, endpoint_of


async def test_every_tool_is_covered(mcp: Client[Any]) -> None:
    tools = {tool.name for tool in await mcp.list_tools()}
    assert tools == {case.tool for case in CASES} | SPECIAL_CASES


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.tool)
async def test_tool_sends_spec_payload(case: Case, mcp: Client[Any], api: FakeQuantConnect) -> None:
    result = await mcp.call_tool(case.tool, case.args)

    assert not result.is_error
    assert endpoint_of(api.last) == case.endpoint
    assert body_of(api.last) == case.body


async def test_client_survives_consecutive_calls(mcp: Client[Any], api: FakeQuantConnect) -> None:
    for _ in range(3):
        result = await mcp.call_tool("read_account", {}, raise_on_error=False)
        assert not result.is_error

    assert len(api.requests) == 3


async def test_tool_returns_payload_without_envelope(
    mcp: Client[Any], api: FakeQuantConnect
) -> None:
    api.reply("backtests/read", {"success": True, "errors": [], "backtest": {"name": "bt"}})

    result = await mcp.call_tool("read_backtest", {"project_id": 1, "backtest_id": "b-1"})

    assert result.data == {"backtest": {"name": "bt"}}


async def test_api_failure_is_an_mcp_error(mcp: Client[Any], api: FakeQuantConnect) -> None:
    api.reply("projects/read", {"success": False, "errors": ["Project not found"]})

    result = await mcp.call_tool("read_project", {"project_id": 9}, raise_on_error=False)

    assert result.is_error
    assert "Project not found" in result.content[0].text  # type: ignore[union-attr]


async def test_unexpected_failure_is_masked(mcp: Client[Any], api: FakeQuantConnect) -> None:
    def explode(request: httpx2.Request) -> httpx2.Response:
        raise RuntimeError("internal detail")

    api.handler = explode  # type: ignore[method-assign]

    result = await mcp.call_tool("read_account", {}, raise_on_error=False)

    assert result.is_error
    assert "internal detail" not in result.content[0].text  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("read_backtest_orders", {"project_id": 1, "backtest_id": "b", "start": 0, "end": 100}),
        ("read_backtest_insights", {"project_id": 1, "backtest_id": "b", "start": 5, "end": 5}),
        ("read_live_insights", {"project_id": 1, "start": 10, "end": 110}),
        ("read_live_logs", {"project_id": 1, "algorithm_id": "L", "end_line": 251}),
        ("read_live_orders", {"project_id": 1, "start": -1, "end": 10}),
        ("read_live_orders", {"project_id": 1, "start": 0, "end": 1001}),
        (
            "read_backtest_chart",
            {"project_id": 1, "backtest_id": "b", "name": "c", "start": 9, "end": 1},
        ),
        ("read_live_chart", {"project_id": 1, "name": "c", "start": 5, "end": 5}),
        ("update_project", {"project_id": 1}),
        ("update_backtest", {"project_id": 1, "backtest_id": "b"}),
        (
            "create_live_algorithm",
            {"project_id": 1, "compile_id": "c", "node_id": "n", "brokerage": {}},
        ),
        ("get_object_store_download", {}),
        ("get_object_store_download", {"keys": ["a"], "job_id": "j"}),
        ("create_project", {"name": "x", "language": "Ruby"}),
    ],
)
async def test_invalid_arguments_are_rejected_before_any_request(
    tool: str, args: dict[str, Any], mcp: Client[Any], api: FakeQuantConnect
) -> None:
    result = await mcp.call_tool(tool, args, raise_on_error=False)

    assert result.is_error
    assert api.requests == []


async def test_compile_project_waits_for_the_build(
    mcp: Client[Any], api: FakeQuantConnect, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(compile_tools, "POLL_INTERVAL_SECONDS", 0)
    api.reply("compile/create", {"success": True, "compileId": "c-1", "state": "InQueue"})
    api.reply(
        "compile/read",
        {"success": True, "compileId": "c-1", "state": "InQueue"},
        {"success": True, "compileId": "c-1", "state": "BuildSuccess", "logs": ["ok"]},
    )

    result = await mcp.call_tool("compile_project", {"project_id": 1})

    assert result.data["state"] == "BuildSuccess"
    assert [endpoint_of(request) for request in api.requests] == [
        "compile/create",
        "compile/read",
        "compile/read",
    ]


async def test_compile_project_fails_when_the_build_outlasts_the_wait(
    mcp: Client[Any], api: FakeQuantConnect, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(compile_tools, "POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(compile_tools, "MAX_POLLS", 2)
    api.reply("compile/create", {"success": True, "compileId": "c-1", "state": "InQueue"})
    api.reply("compile/read", {"success": True, "compileId": "c-1", "state": "InQueue"})

    result = await mcp.call_tool("compile_project", {"project_id": 1}, raise_on_error=False)

    assert result.is_error
    message = result.content[0].text  # type: ignore[union-attr]
    assert "c-1" in message
    assert "read_compilation_result" in message
    assert len(api.requests) == 3


async def test_compile_project_requires_a_compile_id_to_wait(
    mcp: Client[Any], api: FakeQuantConnect
) -> None:
    api.reply("compile/create", {"success": True, "state": "InQueue"})

    result = await mcp.call_tool("compile_project", {"project_id": 1}, raise_on_error=False)

    assert result.is_error
    assert "compileId" in result.content[0].text  # type: ignore[union-attr]
    assert len(api.requests) == 1


async def test_get_auth_status_makes_no_request(mcp: Client[Any], api: FakeQuantConnect) -> None:
    result = await mcp.call_tool("get_auth_status", {})

    assert result.data == {"user_id": "123456", "organization_id": ORGANIZATION_ID}
    assert api.requests == []


async def test_authorize_connection_returns_the_redirect(
    mcp: Client[Any], api: FakeQuantConnect
) -> None:
    api.reply(
        "live/auth0/authorize",
        httpx2.Response(302, headers={"Location": "https://broker.test/oauth"}),
    )

    result = await mcp.call_tool("authorize_connection", {"brokerage": "alpaca"})

    assert result.data == {"brokerage": "alpaca", "authorization_url": "https://broker.test/oauth"}
    assert body_of(api.last) == {"brokerage": "alpaca"}


async def test_upload_object_store_object_posts_multipart(
    mcp: Client[Any], api: FakeQuantConnect
) -> None:
    result = await mcp.call_tool(
        "upload_object_store_object", {"key": "config/a.json", "content": '{"a": 1}'}
    )

    assert not result.is_error
    assert endpoint_of(api.last) == "object/set"
    assert api.last.headers["Content-Type"].startswith("multipart/form-data")
    content = api.last.content
    for part in (b'name="organizationId"', b"org-1", b'name="key"', b'name="objectData"'):
        assert part in content
    assert b'{"a": 1}' in content


async def test_destructive_tools_are_annotated(mcp: Client[Any]) -> None:
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    for name in ("liquidate_live_algorithm", "stop_live_algorithm", "delete_project"):
        assert tools[name].annotations.destructive_hint  # type: ignore[union-attr]
    assert tools["read_backtest"].annotations.read_only_hint  # type: ignore[union-attr]


async def test_nested_arguments_are_snake_case(mcp: Client[Any]) -> None:
    tools = {tool.name: tool for tool in await mcp.list_tools()}

    properties = tools["create_optimization"].input_schema["properties"]

    assert "min_step" in properties["parameters"]["items"]["properties"]
    assert "target_value" in properties["constraints"]["anyOf"][0]["items"]["properties"]

<div align="center">

# ◆ QuantConnect MCP Server

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![FastMCP](https://img.shields.io/badge/FastMCP-4.x-green.svg)](https://gofastmcp.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI Downloads](https://static.pepy.tech/badge/quantconnect-mcp)](https://pepy.tech/projects/quantconnect-mcp)

**Give your AI assistant the QuantConnect cloud: write LEAN algorithms, compile, backtest, optimize, and manage live trading through the Model Context Protocol.**

</div>

<details open>
<summary>Demo: Claude</summary>

<div align="center">
  <video width="832" src="https://github.com/user-attachments/assets/61e96e0e-05b2-482b-8fe3-ccf078d64cc5"></video>
</div>

</details>

## ◈ What it does

61 tools that cover the [QuantConnect REST API v2](https://www.quantconnect.com/docs/v2/cloud-platform/api-reference):

- **Research loop**: create projects and files, check syntax, compile (the tool waits for the build), backtest, and read statistics, orders, insights, charts, and full reports.
- **Optimization**: estimate cost, then run grid-search parameter sweeps on typed parameter ranges and constraints.
- **Live trading**: deploy, monitor portfolio, orders, logs, and charts, send commands, liquidate, and stop.
- **Object Store**: list, inspect, upload, download, and delete organization data.
- **LEAN coding help**: QuantConnect's AI tools for syntax checks, error explanations, documentation search, and code completion.

Every request is validated in CI against QuantConnect's published OpenAPI spec.

## ◈ Quick start

1. Get your **User ID** and **API token** from [quantconnect.com/settings](https://www.quantconnect.com/settings/).
2. Add the server to your MCP client. For Claude Desktop, Claude Code, Cursor, and most clients:

```json
{
  "mcpServers": {
    "quantconnect": {
      "command": "uvx",
      "args": ["quantconnect-mcp"],
      "env": {
        "QUANTCONNECT_USER_ID": "123456",
        "QUANTCONNECT_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

With Claude Code you can run `claude mcp add quantconnect -e QUANTCONNECT_USER_ID=123456 -e QUANTCONNECT_API_TOKEN=your-api-token -- uvx quantconnect-mcp`.

3. Ask for something: *"Create a Python project with an EMA crossover on SPY, backtest it over 2020 to 2024, and summarize the Sharpe ratio and drawdown."*

### Claude Desktop extension

Download `quantconnect-mcp.dxt` from the [Releases](https://github.com/taylorwilsdon/quantconnect-mcp/releases) page, double-click it, and enter your credentials under **Settings > Extensions > QuantConnect MCP**.

## ◈ Configuration

All settings come from environment variables. Credentials are never accepted through tool calls, so they stay out of model transcripts.

The server does not read a `.env` file on its own, because MCP clients start it from inside your project and that project's `.env` is not meant for it. To keep settings in a file, copy [`.env.example`](.env.example) and pass it explicitly, for example `uv run --env-file .env quantconnect-mcp`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `QUANTCONNECT_USER_ID` | required | Your QuantConnect user ID |
| `QUANTCONNECT_API_TOKEN` | required | Your QuantConnect API token |
| `QUANTCONNECT_ORGANIZATION_ID` | your preferred org | Organization for new projects, the Object Store, and broadcasts |
| `REQUEST_TIMEOUT` | `60` | Seconds to wait for a QuantConnect response |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `streamable-http` |
| `MCP_HOST` | `127.0.0.1` | HTTP bind address |
| `MCP_PORT` | `8000` | HTTP port |
| `MCP_PATH` | `/mcp` | HTTP endpoint path |
| `MCP_AUTH_TOKEN` | unset | Bearer token that HTTP clients must send |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` (logs go to stderr) |

## ◈ Security model

These tools can deploy algorithms and liquidate positions on real brokerage accounts. The server is built around that fact:

- **Credentials** live only in the server environment and are held as secrets in memory.
- **HTTP transport** binds to `127.0.0.1` by default. Binding anywhere else requires `MCP_AUTH_TOKEN`, or the server refuses to start. Clients send `Authorization: Bearer <token>`.
- **Tool annotations** mark every tool as read-only, mutating, or destructive, so clients can require confirmation for deletes, liquidation, live deployment, and live commands.
- **Errors** come back as proper MCP tool errors with QuantConnect's message. Unexpected internal failures are masked.

### Running over HTTP

```bash
MCP_TRANSPORT=streamable-http MCP_AUTH_TOKEN=$(openssl rand -hex 32) uvx quantconnect-mcp
```

### Docker

```bash
docker build -t quantconnect-mcp .
docker run -p 8000:8000 \
  -e QUANTCONNECT_USER_ID -e QUANTCONNECT_API_TOKEN -e MCP_AUTH_TOKEN \
  quantconnect-mcp
```

## ◈ Tools

| Area | Tools |
|------|-------|
| Account | `validate_quantconnect_auth`, `get_auth_status`, `read_account`, `read_lean_versions`, `authorize_connection` |
| Projects | `create_project`, `read_project`, `update_project`, `delete_project`, `create_project_collaborator`, `read_project_collaborators`, `update_project_collaborator`, `delete_project_collaborator`, `read_project_nodes`, `update_project_nodes` |
| Files | `create_file`, `read_file`, `update_file_content`, `update_file_name`, `delete_file` |
| Compile | `compile_project`, `read_compilation_result` |
| Backtests | `create_backtest`, `read_backtest`, `list_backtests`, `read_backtest_chart`, `read_backtest_orders`, `read_backtest_insights`, `read_backtest_report`, `update_backtest`, `delete_backtest` |
| Optimizations | `estimate_optimization_time`, `create_optimization`, `read_optimization`, `list_optimizations`, `update_optimization`, `abort_optimization`, `delete_optimization` |
| Live trading | `create_live_algorithm`, `read_live_algorithm`, `list_live_algorithms`, `read_live_logs`, `read_live_chart`, `read_live_portfolio`, `read_live_orders`, `read_live_insights`, `liquidate_live_algorithm`, `stop_live_algorithm`, `create_live_command`, `broadcast_live_command` |
| Object Store | `list_object_store`, `read_object_store_properties`, `get_object_store_download`, `upload_object_store_object`, `delete_object_store_object` |
| LEAN coding help | `check_syntax`, `initialize_backtest`, `enhance_error`, `search_quantconnect`, `complete_code`, `convert_to_pep8` |

Each tool returns QuantConnect's response payload. Paged reads (orders, insights, logs) enforce the API's page limits up front.

## ◈ Upgrading from 0.x

1.0 is a rewrite on FastMCP 4. Tool names are unchanged except as noted below; see [CHANGELOG.md](CHANGELOG.md) for every signature change.

- Removed `configure_quantconnect_auth`, `clear_quantconnect_auth`, `test_quantconnect_api`, and `get_auth_headers_info`. Set credentials through the environment.
- Failed calls now return MCP errors instead of `{"status": "error"}` payloads, and successful calls return the API payload directly.
- Optimization tools take typed `parameters` (`name`, `min`, `max`, `step`), a `target`, and a `target_to`.
- The analytics features previously described in this README (PCA, cointegration, universe screening, portfolio optimization) were never implemented and are no longer advertised.

## ◈ Development

```bash
git clone https://github.com/taylorwilsdon/quantconnect-mcp && cd quantconnect-mcp
uv sync
uv run pytest            # tool, client, server, and OpenAPI contract tests
uv run ruff check && uv run ruff format --check
uv run mypy              # strict
```

The layout is small on purpose:

```
quantconnect_mcp/
  settings.py   configuration (pydantic-settings)
  client.py     signed, pooled QuantConnect API client
  server.py     FastMCP server, bearer auth, entry point
  tools/        one module per API area, one short function per tool
```

To add a tool, write an async function in the matching `tools/` module, decorate it with `@tool(annotations=...)`, take `qc: QuantConnectClient = CLIENT`, add it to that module's `TOOLS`, and add a row to `tests/cases.py`. The contract test checks the payload against `tests/fixtures/quantconnect-openapi.yaml`, which is vendored from [QuantConnect/Documentation](https://github.com/QuantConnect/Documentation).

## ◈ License

MIT. See [LICENSE](LICENSE).

# Changelog

## 1.0.0

A ground-up rewrite on FastMCP 4, validated against QuantConnect's current OpenAPI spec.

### Fixed
- `read_live_insights` called `live/read/insights`, which does not exist; it now calls `live/insights/read`.
- `create_backtest` sent parameters as flattened `parameters[name]` keys; they are now a nested object, so overrides take effect.
- `update_file_name` sent `oldFileName`; it now sends `name` and `newName`.
- `create_optimization` and `estimate_optimization_time` were missing required fields (`target`, `targetTo`, `strategy`, `estimatedCost`, `parallelNodes`) and sent `parameters` in the wrong shape.
- `authorize_connection` called a nonexistent endpoint; it now starts the OAuth flow at `live/auth0/authorize` and returns the authorization URL.
- `update_project_collaborator` omitted the required `write` flag; `delete_project_collaborator` sent `collaboratorUserId` instead of `collaboratorId`.
- `create_live_algorithm` sent `versionId` as a string and an empty `notification` object that the API rejects.
- `read_compilation_result` reported successful builds as failures whenever a log line contained "Warning".
- Page limits now match the API: orders and insights allow `end - start <= 100`; logs allow up to 250 lines with an exclusive `end_line`.
- API failures now surface as MCP tool errors (`isError: true`) with QuantConnect's message, instead of success responses carrying `"status": "error"`.

### Security
- Credentials come only from the environment. Removed `configure_quantconnect_auth`, `clear_quantconnect_auth`, `test_quantconnect_api` (an arbitrary-endpoint passthrough), and `get_auth_headers_info`.
- HTTP transport defaults to `127.0.0.1` and refuses to bind elsewhere without `MCP_AUTH_TOKEN`, which enables bearer authentication. The Docker image requires it.
- Tools carry read-only, mutating, or destructive annotations.

### Added
- LEAN coding help: `check_syntax`, `initialize_backtest`, `enhance_error`, `search_quantconnect`, `complete_code`, `convert_to_pep8`.
- Object Store: `list_object_store`, `read_object_store_properties`, `get_object_store_download`, `upload_object_store_object`, `delete_object_store_object`.
- `read_backtest_report`, `read_lean_versions`, `create_live_command`, `broadcast_live_command`.
- `compile_project` waits for the build by default and reports progress.
- New optional filters: `list_backtests(include_statistics)`, `list_live_algorithms(project_id, latest)`, `read_live_logs(query, deployment_logs)`, `read_live_orders(deploy_id)`, `read_live_insights(algorithm_id)`, and `create_live_algorithm(automatic_redeploy)`.

### Changed
- Tools return QuantConnect's response payload directly.
- Signature changes: `update_file_name(project_id, name, new_name)`; `create_project_collaborator(..., write, live_control)`; `update_project_collaborator(..., write, live_control)` both required; `create_live_algorithm(..., brokerage, version_id: int)` replaces `brokerage_id`/`brokerage_config`; `read_live_algorithm` no longer takes `deploy_id`; `list_live_algorithms` no longer takes `start`/`end`; `read_live_logs` no longer takes `format`; `read_backtest_chart` and `read_live_chart` require `start` and `end`; `authorize_connection(brokerage)` takes one of `alpaca`, `tradestation`, `charlesschwab`, `tastytrade`.
- One pooled HTTP connection with timeouts, connection retries, and a single `Retry-After` retry on HTTP 429.
- Configuration is centralized in `Settings`; blank optional variables are treated as unset. The generic `PORT` variable is no longer read; set `MCP_PORT`.

### Removed
- Unused runtime dependencies: arch, matplotlib, numpy, pandas, psutil, scikit-learn, scipy, seaborn, statsmodels, quantconnect, quantconnect-lean, and pytest-asyncio. Runtime dependencies are now fastmcp, httpx2, pydantic, and pydantic-settings.

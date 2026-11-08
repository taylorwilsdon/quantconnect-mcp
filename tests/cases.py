"""One representative call per tool, with the exact request it must send.

Shared by the payload tests and the OpenAPI contract test.
"""

from dataclasses import dataclass
from typing import Any

from tests.conftest import ORGANIZATION_ID

GRID = "QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy"
SHARPE = "TotalPerformance.PortfolioStatistics.SharpeRatio"
DRAWDOWN = "TotalPerformance.PortfolioStatistics.Drawdown"
FILE = {"name": "main.py", "content": "class A: pass"}


@dataclass(frozen=True)
class Case:
    tool: str
    args: dict[str, Any]
    endpoint: str
    body: dict[str, Any]


OPTIMIZATION_ARGS = {
    "project_id": 1,
    "compile_id": "c-1",
    "name": "sweep",
    "target": "SharpeRatio",
    "target_to": "max",
    "parameters": [{"name": "fast", "min": 5, "max": 20, "step": 5, "min_step": 1}],
    "constraints": [{"target": "Drawdown", "operator": "LessOrEqual", "target_value": 0.2}],
}
OPTIMIZATION_BODY = {
    "projectId": 1,
    "compileId": "c-1",
    "name": "sweep",
    "target": SHARPE,
    "targetTo": "max",
    "strategy": GRID,
    "parameters": [{"name": "fast", "min": 5.0, "max": 20.0, "step": 5.0, "minStep": 1.0}],
    "constraints": [{"target": DRAWDOWN, "operator": "LessOrEqual", "targetValue": 0.2}],
}

CASES = (
    # Account
    Case("validate_quantconnect_auth", {}, "authenticate", {}),
    Case("read_account", {}, "account/read", {}),
    Case("read_lean_versions", {}, "lean/versions/read", {}),
    # Projects
    Case(
        "create_project",
        {"name": "Alpha", "language": "Py"},
        "projects/create",
        {"name": "Alpha", "language": "Py", "organizationId": ORGANIZATION_ID},
    ),
    Case("read_project", {"project_id": 1}, "projects/read", {"projectId": 1}),
    Case(
        "update_project",
        {"project_id": 1, "description": "New"},
        "projects/update",
        {"projectId": 1, "description": "New"},
    ),
    Case("delete_project", {"project_id": 1}, "projects/delete", {"projectId": 1}),
    Case(
        "create_project_collaborator",
        {"project_id": 1, "collaborator_user_id": "u-2"},
        "projects/collaboration/create",
        {
            "projectId": 1,
            "collaboratorUserId": "u-2",
            "collaborationWrite": True,
            "collaborationLiveControl": False,
        },
    ),
    Case(
        "read_project_collaborators",
        {"project_id": 1},
        "projects/collaboration/read",
        {"projectId": 1},
    ),
    Case(
        "update_project_collaborator",
        {"project_id": 1, "collaborator_user_id": "u-2", "write": False, "live_control": True},
        "projects/collaboration/update",
        {"projectId": 1, "collaboratorUserId": "u-2", "write": False, "liveControl": True},
    ),
    Case(
        "delete_project_collaborator",
        {"project_id": 1, "collaborator_user_id": "u-2"},
        "projects/collaboration/delete",
        {"projectId": 1, "collaboratorId": "u-2"},
    ),
    Case("read_project_nodes", {"project_id": 1}, "projects/nodes/read", {"projectId": 1}),
    Case(
        "update_project_nodes",
        {"project_id": 1, "nodes": ["B2-8"]},
        "projects/nodes/update",
        {"projectId": 1, "nodes": ["B2-8"]},
    ),
    # Files
    Case(
        "create_file",
        {"project_id": 1, "name": "a.py", "content": "x = 1"},
        "files/create",
        {"projectId": 1, "name": "a.py", "content": "x = 1"},
    ),
    Case(
        "read_file",
        {"project_id": 1, "name": "a.py"},
        "files/read",
        {"projectId": 1, "name": "a.py"},
    ),
    Case(
        "update_file_content",
        {"project_id": 1, "name": "a.py", "content": "x = 2"},
        "files/update",
        {"projectId": 1, "name": "a.py", "content": "x = 2"},
    ),
    Case(
        "update_file_name",
        {"project_id": 1, "name": "a.py", "new_name": "b.py"},
        "files/update",
        {"projectId": 1, "name": "a.py", "newName": "b.py"},
    ),
    Case(
        "delete_file",
        {"project_id": 1, "name": "a.py"},
        "files/delete",
        {"projectId": 1, "name": "a.py"},
    ),
    # Compile
    Case(
        "compile_project",
        {"project_id": 1, "wait": False},
        "compile/create",
        {"projectId": 1},
    ),
    Case(
        "read_compilation_result",
        {"project_id": 1, "compile_id": "c-1"},
        "compile/read",
        {"projectId": 1, "compileId": "c-1"},
    ),
    # Backtests
    Case(
        "create_backtest",
        {"project_id": 1, "compile_id": "c-1", "backtest_name": "bt", "parameters": {"fast": 10}},
        "backtests/create",
        {"projectId": 1, "compileId": "c-1", "backtestName": "bt", "parameters": {"fast": 10}},
    ),
    Case(
        "read_backtest",
        {"project_id": 1, "backtest_id": "b-1"},
        "backtests/read",
        {"projectId": 1, "backtestId": "b-1"},
    ),
    Case(
        "list_backtests",
        {"project_id": 1},
        "backtests/list",
        {"projectId": 1, "includeStatistics": False},
    ),
    Case(
        "read_backtest_chart",
        {"project_id": 1, "backtest_id": "b-1", "name": "Strategy Equity", "start": 0, "end": 99},
        "backtests/chart/read",
        {
            "projectId": 1,
            "backtestId": "b-1",
            "name": "Strategy Equity",
            "start": 0,
            "end": 99,
            "count": 100,
        },
    ),
    Case(
        "read_backtest_orders",
        {"project_id": 1, "backtest_id": "b-1"},
        "backtests/orders/read",
        {"projectId": 1, "backtestId": "b-1", "start": 0, "end": 99},
    ),
    Case(
        "read_backtest_insights",
        {"project_id": 1, "backtest_id": "b-1", "start": 99, "end": 198},
        "backtests/read/insights",
        {"projectId": 1, "backtestId": "b-1", "start": 99, "end": 198},
    ),
    Case(
        "read_backtest_report",
        {"project_id": 1, "backtest_id": "b-1"},
        "backtests/read/report",
        {"projectId": 1, "backtestId": "b-1"},
    ),
    Case(
        "update_backtest",
        {"project_id": 1, "backtest_id": "b-1", "note": "keep"},
        "backtests/update",
        {"projectId": 1, "backtestId": "b-1", "note": "keep"},
    ),
    Case(
        "delete_backtest",
        {"project_id": 1, "backtest_id": "b-1"},
        "backtests/delete",
        {"projectId": 1, "backtestId": "b-1"},
    ),
    # Optimizations
    Case(
        "estimate_optimization_time",
        OPTIMIZATION_ARGS,
        "optimizations/estimate",
        OPTIMIZATION_BODY,
    ),
    Case(
        "create_optimization",
        {**OPTIMIZATION_ARGS, "estimated_cost": 12.5},
        "optimizations/create",
        {**OPTIMIZATION_BODY, "estimatedCost": 12.5, "nodeType": "O2-8", "parallelNodes": 4},
    ),
    Case(
        "read_optimization",
        {"optimization_id": "o-1"},
        "optimizations/read",
        {"optimizationId": "o-1"},
    ),
    Case("list_optimizations", {"project_id": 1}, "optimizations/list", {"projectId": 1}),
    Case(
        "update_optimization",
        {"optimization_id": "o-1", "name": "renamed"},
        "optimizations/update",
        {"optimizationId": "o-1", "name": "renamed"},
    ),
    Case(
        "abort_optimization",
        {"optimization_id": "o-1"},
        "optimizations/abort",
        {"optimizationId": "o-1"},
    ),
    Case(
        "delete_optimization",
        {"optimization_id": "o-1"},
        "optimizations/delete",
        {"optimizationId": "o-1"},
    ),
    # Live
    Case(
        "create_live_algorithm",
        {
            "project_id": 1,
            "compile_id": "c-1",
            "node_id": "LN-1",
            "brokerage": {"id": "QuantConnectBrokerage"},
        },
        "live/create",
        {
            "projectId": 1,
            "compileId": "c-1",
            "nodeId": "LN-1",
            "versionId": -1,
            "brokerage": {"id": "QuantConnectBrokerage"},
            "dataProviders": {"QuantConnectBrokerage": {"id": "QuantConnectBrokerage"}},
        },
    ),
    Case("read_live_algorithm", {"project_id": 1}, "live/read", {"projectId": 1}),
    Case(
        "list_live_algorithms",
        {"status": "Running"},
        "live/list",
        {"status": "Running"},
    ),
    Case(
        "read_live_logs",
        {"project_id": 1, "algorithm_id": "L-1", "query": "ERROR"},
        "live/logs/read",
        {"projectId": 1, "algorithmId": "L-1", "startLine": 0, "endLine": 250, "query": "ERROR"},
    ),
    Case(
        "read_live_chart",
        {"project_id": 1, "name": "Strategy Equity", "start": 0, "end": 99},
        "live/chart/read",
        {"projectId": 1, "name": "Strategy Equity", "start": 0, "end": 99, "count": 100},
    ),
    Case("read_live_portfolio", {"project_id": 1}, "live/portfolio/read", {"projectId": 1}),
    Case(
        "read_live_orders",
        {"project_id": 1},
        "live/orders/read",
        {"projectId": 1, "start": 0, "end": 100},
    ),
    Case(
        "read_live_insights",
        {"project_id": 1, "algorithm_id": "L-1"},
        "live/insights/read",
        {"projectId": 1, "start": 0, "end": 99, "algorithmId": "L-1"},
    ),
    Case(
        "liquidate_live_algorithm",
        {"project_id": 1},
        "live/update/liquidate",
        {"projectId": 1},
    ),
    Case("stop_live_algorithm", {"project_id": 1}, "live/update/stop", {"projectId": 1}),
    Case(
        "create_live_command",
        {"project_id": 1, "command": {"$type": "Rebalance"}},
        "live/commands/create",
        {"projectId": 1, "command": {"$type": "Rebalance"}},
    ),
    Case(
        "broadcast_live_command",
        {"command": {"$type": "Rebalance"}, "exclude_project_id": 2},
        "live/commands/broadcast",
        {
            "organizationId": ORGANIZATION_ID,
            "excludeProjectId": 2,
            "command": {"$type": "Rebalance"},
        },
    ),
    # Object Store
    Case(
        "list_object_store",
        {"path": "models/"},
        "object/list",
        {"organizationId": ORGANIZATION_ID, "path": "models/"},
    ),
    Case(
        "read_object_store_properties",
        {"key": "models/a.pkl"},
        "object/properties",
        {"organizationId": ORGANIZATION_ID, "key": "models/a.pkl"},
    ),
    Case(
        "get_object_store_download",
        {"keys": ["models/a.pkl"]},
        "object/get",
        {"organizationId": ORGANIZATION_ID, "keys": ["models/a.pkl"]},
    ),
    Case(
        "delete_object_store_object",
        {"key": "models/a.pkl"},
        "object/delete",
        {"organizationId": ORGANIZATION_ID, "key": "models/a.pkl"},
    ),
    # AI tools
    Case(
        "check_syntax",
        {"files": [FILE]},
        "ai/tools/syntax-check",
        {"language": "Py", "files": [FILE]},
    ),
    Case(
        "initialize_backtest",
        {"files": [FILE], "language": "Py"},
        "ai/tools/backtest-init",
        {"language": "Py", "files": [FILE]},
    ),
    Case(
        "enhance_error",
        {"message": "NameError: x"},
        "ai/tools/error-enhance",
        {"language": "Py", "error": {"message": "NameError: x"}},
    ),
    Case(
        "search_quantconnect",
        {"query": "alpha model", "sources": ["Docs"], "count": 3},
        "ai/tools/search",
        {"language": "Py", "criteria": [{"input": "alpha model", "type": "Docs", "count": 3}]},
    ),
    Case(
        "complete_code",
        {"sentence": "self.add_eq"},
        "ai/tools/complete",
        {"language": "Py", "sentence": "self.add_eq"},
    ),
    Case(
        "convert_to_pep8",
        {"files": [FILE]},
        "ai/tools/pep8-convert",
        {"files": [FILE]},
    ),
)

# Tools that are covered by dedicated tests instead of the JSON payload table.
SPECIAL_CASES = frozenset({"get_auth_status", "authorize_connection", "upload_object_store_object"})

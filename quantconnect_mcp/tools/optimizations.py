"""Parameter optimization tools."""

from typing import Annotated, Any, Literal

from fastmcp.tools import tool
from pydantic import Field

from quantconnect_mcp.client import QuantConnectClient
from quantconnect_mcp.tools._shared import CLIENT, DESTRUCTIVE, MUTATING, READ_ONLY, ApiModel

GRID_SEARCH = "QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy"
STATISTIC_PREFIX = "TotalPerformance.PortfolioStatistics."

Statistic = Literal[
    "SharpeRatio", "CompoundingAnnualReturn", "ProbabilisticSharpeRatio", "Drawdown"
]
NodeType = Literal["O2-8", "O4-12", "O8-16"]


class OptimizationParameter(ApiModel):
    """A parameter to sweep, read in the algorithm with get_parameter(name)."""

    name: str
    min: float
    max: float
    step: float = Field(gt=0)
    min_step: float | None = Field(None, gt=0)


class OptimizationConstraint(ApiModel):
    """A filter on backtest results, for example Drawdown LessOrEqual 0.2."""

    target: Statistic
    operator: Literal["LessOrEqual", "Less", "GreaterOrEqual", "Greater", "NotEqual", "Equals"]
    target_value: float

    def to_api(self) -> dict[str, Any]:
        return {**super().to_api(), "target": STATISTIC_PREFIX + self.target}


def _job(
    name: str,
    target: Statistic,
    target_to: Literal["min", "max"],
    parameters: list[OptimizationParameter],
    constraints: list[OptimizationConstraint] | None,
    target_value: float | None,
) -> dict[str, Any]:
    """Build the fields shared by the estimate and create requests."""
    return {
        "name": name,
        "target": STATISTIC_PREFIX + target,
        "targetTo": target_to,
        "targetValue": target_value,
        "strategy": GRID_SEARCH,
        "parameters": [parameter.to_api() for parameter in parameters],
        "constraints": [constraint.to_api() for constraint in constraints or []],
    }


@tool(annotations=READ_ONLY)
async def estimate_optimization_time(
    project_id: int,
    compile_id: str,
    name: str,
    target: Statistic,
    target_to: Literal["min", "max"],
    parameters: list[OptimizationParameter],
    constraints: list[OptimizationConstraint] | None = None,
    target_value: float | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Estimate how long a grid-search optimization would run, and show the QCC balance.

    Args:
        project_id: The project to optimize.
        compile_id: A compile ID whose state is BuildSuccess.
        name: A name for the optimization.
        target: The statistic to optimize.
        target_to: Whether to minimize or maximize the target.
        parameters: The parameters to sweep, each with min, max, and step.
        constraints: Filters that each backtest must pass.
        target_value: Stop once the target reaches this value.
    """
    job = _job(name, target, target_to, parameters, constraints, target_value)
    return await qc.post(
        "optimizations/estimate", projectId=project_id, compileId=compile_id, **job
    )


@tool(annotations=MUTATING)
async def create_optimization(
    project_id: int,
    compile_id: str,
    name: str,
    target: Statistic,
    target_to: Literal["min", "max"],
    parameters: list[OptimizationParameter],
    estimated_cost: float,
    node_type: NodeType = "O2-8",
    parallel_nodes: Annotated[int, Field(ge=1)] = 4,
    constraints: list[OptimizationConstraint] | None = None,
    target_value: float | None = None,
    qc: QuantConnectClient = CLIENT,
) -> dict[str, Any]:
    """Launch a grid-search optimization. This spends QuantConnect Credit (QCC).

    Run estimate_optimization_time first and confirm the cost with the user.

    Args:
        project_id: The project to optimize.
        compile_id: A compile ID whose state is BuildSuccess.
        name: A name for the optimization.
        target: The statistic to optimize.
        target_to: Whether to minimize or maximize the target.
        parameters: The parameters to sweep, each with min, max, and step.
        estimated_cost: The expected cost in QCC, from estimate_optimization_time.
        node_type: Optimization node size: O2-8, O4-12, or O8-16 (cores-GB RAM).
        parallel_nodes: How many nodes to run concurrently.
        constraints: Filters that each backtest must pass.
        target_value: Stop once the target reaches this value.
    """
    job = _job(name, target, target_to, parameters, constraints, target_value)
    return await qc.post(
        "optimizations/create",
        projectId=project_id,
        compileId=compile_id,
        estimatedCost=estimated_cost,
        nodeType=node_type,
        parallelNodes=parallel_nodes,
        **job,
    )


@tool(annotations=READ_ONLY)
async def read_optimization(
    optimization_id: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Read an optimization's status, settings, and backtest results.

    Args:
        optimization_id: The optimization to read.
    """
    return await qc.post("optimizations/read", optimizationId=optimization_id)


@tool(annotations=READ_ONLY)
async def list_optimizations(project_id: int, qc: QuantConnectClient = CLIENT) -> dict[str, Any]:
    """List a project's optimizations.

    Args:
        project_id: The project to inspect.
    """
    return await qc.post("optimizations/list", projectId=project_id)


@tool(annotations=MUTATING)
async def update_optimization(
    optimization_id: str, name: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Rename an optimization.

    Args:
        optimization_id: The optimization to rename.
        name: The new name.
    """
    return await qc.post("optimizations/update", optimizationId=optimization_id, name=name)


@tool(annotations=DESTRUCTIVE)
async def abort_optimization(
    optimization_id: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Abort a running optimization. Completed backtests are kept.

    Args:
        optimization_id: The optimization to abort.
    """
    return await qc.post("optimizations/abort", optimizationId=optimization_id)


@tool(annotations=DESTRUCTIVE)
async def delete_optimization(
    optimization_id: str, qc: QuantConnectClient = CLIENT
) -> dict[str, Any]:
    """Permanently delete an optimization and its results.

    Args:
        optimization_id: The optimization to delete.
    """
    return await qc.post("optimizations/delete", optimizationId=optimization_id)


TOOLS = (
    estimate_optimization_time,
    create_optimization,
    read_optimization,
    list_optimizations,
    update_optimization,
    abort_optimization,
    delete_optimization,
)

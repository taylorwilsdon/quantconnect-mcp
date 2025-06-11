"""Portfolio Optimization and Analysis Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
import json
from .quantbook_tools import get_quantbook_instance


def register_portfolio_tools(mcp: FastMCP):
    """Register portfolio optimization and analysis tools with the MCP server."""

    @mcp.tool()
    async def sparse_optimization(
        portfolio_symbols: List[str],
        benchmark_symbol: str,
        start_date: str,
        end_date: str,
        max_iterations: int = 20,
        tolerance: float = 0.001,
        max_weight: float = 0.1,
        penalty_param: float = 0.5,
        huber_param: float = 0.0001,
        lambda_param: float = 0.01,
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Perform sparse optimization algorithm with Huber Downward Risk minimization.

        Args:
            portfolio_symbols: List of symbols for the portfolio
            benchmark_symbol: Benchmark symbol to track
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_iterations: Maximum iterations for optimization
            tolerance: Convergence tolerance
            max_weight: Maximum weight per asset
            penalty_param: Penalty parameter (p)
            huber_param: Huber statistics M-value
            lambda_param: Penalty weight (l)
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing optimized portfolio weights and performance
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from datetime import datetime
            from QuantConnect import Resolution  # type: ignore

            # Get all symbols including benchmark
            all_symbols = portfolio_symbols + [benchmark_symbol]
            security_keys = []

            for symbol in all_symbols:
                found = False
                for sec_key in qb.Securities.Keys:
                    if str(sec_key).upper() == symbol.upper():
                        security_keys.append(sec_key)
                        found = True
                        break
                if not found:
                    return {
                        "status": "error",
                        "error": f"Symbol '{symbol}' not found. Add it first using add_equity.",
                    }

            # Get historical data
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            history = qb.History(security_keys, start, end, Resolution.Daily)

            if history.empty:
                return {
                    "status": "error",
                    "error": "No historical data found for the specified period",
                }

            # Get close prices and calculate log returns
            close_price = history["close"].unstack(level=0)

            # Separate portfolio and benchmark data
            portfolio_keys = security_keys[:-1]  # All except last (benchmark)
            benchmark_key = security_keys[-1]

            portfolio_prices = close_price[portfolio_keys]
            benchmark_prices = close_price[benchmark_key]

            # Calculate log returns
            pct_change_portfolio = np.log(
                portfolio_prices / portfolio_prices.shift(1)
            ).dropna()
            pct_change_benchmark = np.log(
                benchmark_prices / benchmark_prices.shift(1)
            ).loc[pct_change_portfolio.index]

            # Get dimensions
            m, n = pct_change_portfolio.shape

            if m < 10 or n < 2:
                return {
                    "status": "error",
                    "error": "Insufficient data for optimization",
                }

            # Initialize optimization parameters
            p = penalty_param
            M = huber_param
            l = lambda_param
            tol = tolerance
            max_iter = max_iterations
            u = max_weight

            # Initial weights and placeholders
            w_ = np.array([1 / n] * n).reshape(n, 1)
            weights = pd.Series()
            a = np.array([None] * m).reshape(m, 1)
            c = np.array([None] * m).reshape(m, 1)
            d = np.array([None] * n).reshape(n, 1)

            hdr = 10000.0
            iters = 1

            # Optimization loop
            while iters < max_iter:
                x_k = pct_change_benchmark.values - pct_change_portfolio.values @ w_

                # Update d vector
                for i in range(n):
                    w = w_[i]
                    d[i] = 1 / (np.log(1 + l / p) * (p + w))

                # Update a and c vectors
                for i in range(m):
                    xk = float(x_k[i])
                    if xk < 0:
                        a[i] = M / (M - 2 * xk)
                        c[i] = xk
                    else:
                        c[i] = 0
                        if 0 <= xk <= M:
                            a[i] = 1
                        else:
                            a[i] = M / abs(xk)

                # Calculate L3 matrix
                L3 = (
                    1
                    / m
                    * pct_change_portfolio.T.values
                    @ np.diagflat(a.T)
                    @ pct_change_portfolio.values
                )
                eig_val, eig_vec = np.linalg.eig(L3.astype(float))
                eig_val = np.real(eig_val)
                eig_vec = np.real(eig_vec)

                max_eig = max(eig_val)
                q3 = (
                    1
                    / max_eig
                    * (
                        2 * (L3 - max_eig * np.eye(n)) @ w_
                        + eig_vec @ d
                        - 2
                        / m
                        * pct_change_portfolio.T.values
                        @ np.diagflat(a.T)
                        @ (c - pct_change_benchmark.values.reshape(-1, 1))
                    )
                )

                # Calculate mu
                mu = float(-(np.sum(q3) + 2) / n)
                mu_ = 0.0

                while mu > mu_:
                    mu = mu_
                    index1 = [i for i, q in enumerate(q3) if mu + q < -u * 2]
                    index2 = [i for i, q in enumerate(q3) if -u * 2 < mu + q < 0]
                    if len(index2) > 0:
                        mu_ = float(
                            -(np.sum([q3[i] for i in index2]) + 2 - len(index1) * u * 2)
                            / len(index2)
                        )
                    else:
                        break

                # Update weights
                w_ = np.amax(
                    np.concatenate((-(mu + q3) / 2, u * np.ones((n, 1))), axis=1),
                    axis=1,
                ).reshape(-1, 1)
                w_ = w_ / np.sum(abs(w_))
                hdr_ = float(w_.T @ w_ + q3.T @ w_)

                # Check convergence
                if abs(hdr - hdr_) < tol:
                    break

                iters += 1
                hdr = hdr_

            # Store final weights
            for i in range(n):
                weights[portfolio_symbols[i]] = float(w_[i])

            # Calculate portfolio performance
            portfolio_returns = pct_change_portfolio @ w_.flatten()
            cumulative_returns = (1 + portfolio_returns).cumprod()

            # Calculate tracking error vs benchmark
            active_returns = portfolio_returns - pct_change_benchmark
            tracking_error = float(active_returns.std())

            return {
                "status": "success",
                "portfolio_symbols": portfolio_symbols,
                "benchmark_symbol": benchmark_symbol,
                "optimized_weights": weights.to_dict(),
                "iterations_used": iters,
                "converged": iters < max_iter,
                "final_hdr": float(hdr_),
                "tracking_error": tracking_error,
                "portfolio_return": float(cumulative_returns.iloc[-1] - 1),
                "benchmark_return": float(
                    (1 + pct_change_benchmark).cumprod().iloc[-1] - 1
                ),
                "active_return": float(
                    portfolio_returns.sum() - pct_change_benchmark.sum()
                ),
                "optimization_params": {
                    "max_weight": max_weight,
                    "penalty_param": penalty_param,
                    "huber_param": huber_param,
                    "lambda_param": lambda_param,
                },
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to perform sparse optimization",
            }

    @mcp.tool()
    async def calculate_portfolio_performance(
        symbols: List[str],
        weights: List[float],
        start_date: str,
        end_date: str,
        benchmark_symbol: Optional[str] = None,
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Calculate portfolio performance metrics for given weights.

        Args:
            symbols: List of portfolio symbols
            weights: List of weights corresponding to symbols
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            benchmark_symbol: Optional benchmark for comparison
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing portfolio performance metrics
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from datetime import datetime
            from QuantConnect import Resolution  # type: ignore

            if len(symbols) != len(weights):
                return {
                    "status": "error",
                    "error": "Number of symbols must match number of weights",
                }

            # Normalize weights
            weights_array = np.array(weights)
            weights = weights_array / np.sum(np.abs(weights_array))

            # Get security keys
            all_symbols = symbols + ([benchmark_symbol] if benchmark_symbol else [])
            security_keys = []

            for symbol in all_symbols:
                found = False
                for sec_key in qb.Securities.Keys:
                    if str(sec_key).upper() == symbol.upper():
                        security_keys.append(sec_key)
                        found = True
                        break
                if not found:
                    return {
                        "status": "error",
                        "error": f"Symbol '{symbol}' not found. Add it first using add_equity.",
                    }

            # Get historical data
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            history = qb.History(security_keys, start, end, Resolution.Daily)

            if history.empty:
                return {
                    "status": "error",
                    "error": "No historical data found for the specified period",
                }

            # Get close prices and calculate returns
            close_price = history["close"].unstack(level=0)
            returns = close_price.pct_change().iloc[1:]

            # Calculate portfolio returns
            portfolio_keys = security_keys[: len(symbols)]
            portfolio_returns = returns[portfolio_keys] @ weights

            # Calculate performance metrics
            total_return = float((1 + portfolio_returns).prod() - 1)
            annualized_return = float((1 + portfolio_returns.mean()) ** 252 - 1)
            volatility = float(portfolio_returns.std() * np.sqrt(252))
            sharpe_ratio = (
                float(annualized_return / volatility) if volatility > 0 else 0
            )

            # Downside metrics
            negative_returns = portfolio_returns[portfolio_returns < 0]
            downside_deviation = (
                float(negative_returns.std() * np.sqrt(252))
                if len(negative_returns) > 0
                else 0
            )
            sortino_ratio = (
                float(annualized_return / downside_deviation)
                if downside_deviation > 0
                else 0
            )

            # Maximum drawdown
            cumulative = (1 + portfolio_returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            max_drawdown = float(drawdown.min())

            results = {
                "status": "success",
                "symbols": symbols,
                "weights": weights.tolist() if hasattr(weights, 'tolist') else list(weights),
                "performance_metrics": {
                    "total_return": total_return,
                    "annualized_return": annualized_return,
                    "volatility": volatility,
                    "sharpe_ratio": sharpe_ratio,
                    "sortino_ratio": sortino_ratio,
                    "max_drawdown": max_drawdown,
                    "downside_deviation": downside_deviation,
                },
                "period": {
                    "start_date": start_date,
                    "end_date": end_date,
                    "trading_days": len(portfolio_returns),
                },
            }

            # Add benchmark comparison if provided
            if benchmark_symbol:
                benchmark_key = security_keys[-1]
                benchmark_returns = returns[benchmark_key]

                benchmark_total_return = float((1 + benchmark_returns).prod() - 1)
                benchmark_volatility = float(benchmark_returns.std() * np.sqrt(252))

                # Active return and tracking error
                active_returns = portfolio_returns - benchmark_returns
                tracking_error = float(active_returns.std() * np.sqrt(252))
                information_ratio = (
                    float(active_returns.mean() * 252 / tracking_error)
                    if tracking_error > 0
                    else 0
                )

                # Beta calculation
                covariance = float(np.cov(portfolio_returns, benchmark_returns)[0, 1])
                benchmark_variance = float(benchmark_returns.var())
                beta = covariance / benchmark_variance if benchmark_variance > 0 else 0

                results["benchmark_comparison"] = {
                    "benchmark_symbol": benchmark_symbol,
                    "benchmark_total_return": benchmark_total_return,
                    "benchmark_volatility": benchmark_volatility,
                    "active_return": float(total_return - benchmark_total_return),
                    "tracking_error": tracking_error,
                    "information_ratio": information_ratio,
                    "beta": beta,
                }

            return results

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to calculate portfolio performance",
            }

    @mcp.tool()
    async def optimize_equal_weight_portfolio(
        symbols: List[str],
        start_date: str,
        end_date: str,
        rebalance_frequency: str = "monthly",
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Create and analyze an equal-weight portfolio with rebalancing.

        Args:
            symbols: List of symbols for the portfolio
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            rebalance_frequency: Rebalancing frequency (daily, weekly, monthly, quarterly)
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing equal-weight portfolio analysis
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from datetime import datetime
            from QuantConnect import Resolution  # type: ignore

            # Get security keys
            security_keys = []
            for symbol in symbols:
                found = False
                for sec_key in qb.Securities.Keys:
                    if str(sec_key).upper() == symbol.upper():
                        security_keys.append(sec_key)
                        found = True
                        break
                if not found:
                    return {
                        "status": "error",
                        "error": f"Symbol '{symbol}' not found. Add it first using add_equity.",
                    }

            # Get historical data
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            history = qb.History(security_keys, start, end, Resolution.Daily)

            if history.empty:
                return {
                    "status": "error",
                    "error": "No historical data found for the specified period",
                }

            # Get close prices and calculate returns
            close_price = history["close"].unstack(level=0)
            returns = close_price.pct_change().iloc[1:]

            # Equal weights
            n_assets = len(symbols)
            equal_weights = np.array([1 / n_assets] * n_assets)

            # Calculate portfolio returns
            portfolio_returns = returns[security_keys] @ equal_weights

            # Calculate rebalancing periods
            freq_map = {
                "daily": returns.index,
                "weekly": returns.resample("W").last().index,
                "monthly": returns.resample("M").last().index,
                "quarterly": returns.resample("Q").last().index,
            }

            if rebalance_frequency not in freq_map:
                return {
                    "status": "error",
                    "error": f"Invalid rebalance frequency. Must be one of: {list(freq_map.keys())}",
                }

            rebalance_dates = freq_map[rebalance_frequency]

            # Calculate portfolio performance
            cumulative_returns = (1 + portfolio_returns).cumprod()
            total_return = float(cumulative_returns.iloc[-1] - 1)
            annualized_return = float((1 + portfolio_returns.mean()) ** 252 - 1)
            volatility = float(portfolio_returns.std() * np.sqrt(252))

            # Individual asset statistics
            asset_stats = {}
            for i, symbol in enumerate(symbols):
                asset_returns = returns[security_keys[i]]
                asset_stats[symbol] = {
                    "weight": float(equal_weights[i]),
                    "total_return": float((1 + asset_returns).prod() - 1),
                    "volatility": float(asset_returns.std() * np.sqrt(252)),
                    "contribution_to_return": float(
                        equal_weights[i] * asset_returns.sum()
                    ),
                }

            return {
                "status": "success",
                "symbols": symbols,
                "equal_weights": equal_weights.tolist(),
                "rebalance_frequency": rebalance_frequency,
                "rebalance_dates": len(rebalance_dates),
                "portfolio_performance": {
                    "total_return": total_return,
                    "annualized_return": annualized_return,
                    "volatility": volatility,
                    "sharpe_ratio": (
                        float(annualized_return / volatility) if volatility > 0 else 0
                    ),
                },
                "asset_statistics": asset_stats,
                "diversification_ratio": (
                    float(
                        np.sum(
                            equal_weights
                            * np.array([asset_stats[s]["volatility"] for s in symbols])
                        )
                        / volatility
                    )
                    if volatility > 0
                    else 0
                ),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to optimize equal weight portfolio",
            }

"""Universe Selection and ETF Constituent Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime
from .quantbook_tools import get_quantbook_instance


async def _get_etf_constituents_helper(
    etf_ticker: str, date: str, instance_name: str = "default"
) -> Dict[str, Any]:
    """Helper function to get ETF constituents."""
    qb = get_quantbook_instance(instance_name)
    if qb is None:
        return {
            "status": "error",
            "error": f"QuantBook instance '{instance_name}' not found",
        }

    try:
        from QuantConnect import Resolution  # type: ignore

        # Parse date
        universe_date = datetime.strptime(date, "%Y-%m-%d")
        date_str = universe_date.strftime("%Y%m%d")

        # Construct file path for ETF universe data
        filename = (
            f"/data/equity/usa/universes/etf/{etf_ticker.lower()}/{date_str}.csv"
        )

        try:
            df = pd.read_csv(filename)
            security_ids = df[df.columns[1]].values

            # Create symbols from security IDs
            symbols = []
            symbol_objects = []
            for security_id in security_ids:
                try:
                    symbol_obj = qb.Symbol(security_id)
                    symbols.append(str(symbol_obj))
                    symbol_objects.append(symbol_obj)
                except Exception:
                    continue

            return {
                "status": "success",
                "etf_ticker": etf_ticker,
                "date": date,
                "constituents": symbols,
                "count": len(symbols),
                "security_ids": security_ids.tolist(),
            }

        except FileNotFoundError:
            return {
                "status": "error",
                "error": f"ETF universe file not found for {etf_ticker} on {date}",
                "message": "ETF constituent data may not be available for this date",
            }
        except Exception as file_error:
            return {
                "status": "error",
                "error": f"Failed to read ETF universe file: {str(file_error)}",
            }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": f"Failed to get ETF constituents for {etf_ticker}",
        }


def register_universe_tools(mcp: FastMCP):
    """Register universe selection and ETF constituent tools with the MCP server."""

    @mcp.tool()
    async def get_etf_constituents(
        etf_ticker: str, date: str, instance_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Get ETF constituents for a specific date using ETF universe data.

        Args:
            etf_ticker: ETF ticker symbol (e.g., "QQQ", "SPY")
            date: Date in YYYY-MM-DD format to get constituents for
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing ETF constituent information
        """
        return await _get_etf_constituents_helper(etf_ticker, date, instance_name)

    @mcp.tool()
    async def add_etf_universe_securities(
        etf_ticker: str,
        date: str,
        resolution: str = "Daily",
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Add all ETF constituent securities to the QuantBook instance.

        Args:
            etf_ticker: ETF ticker symbol
            date: Date in YYYY-MM-DD format to get constituents for
            resolution: Data resolution (Minute, Hour, Daily)
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing results of adding securities
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from QuantConnect import Resolution  # type: ignore

            # First get the constituents
            constituents_result = await _get_etf_constituents_helper(
                etf_ticker, date, instance_name
            )

            if constituents_result["status"] != "success":
                return constituents_result

            # Map resolution
            resolution_map = {
                "Minute": Resolution.Minute,
                "Hour": Resolution.Hour,
                "Daily": Resolution.Daily,
            }

            if resolution not in resolution_map:
                return {
                    "status": "error",
                    "error": f"Invalid resolution '{resolution}'. Must be one of: {list(resolution_map.keys())}",
                }

            # Add securities
            universe_date = datetime.strptime(date, "%Y-%m-%d")
            date_str = universe_date.strftime("%Y%m%d")
            filename = (
                f"/data/equity/usa/universes/etf/{etf_ticker.lower()}/{date_str}.csv"
            )

            df = pd.read_csv(filename)
            security_ids = df[df.columns[1]].values

            added_securities = []
            failed_securities = []

            for security_id in security_ids:
                try:
                    symbol = qb.Symbol(security_id)
                    security = qb.AddSecurity(symbol, resolution_map[resolution])
                    added_securities.append(
                        {
                            "security_id": security_id,
                            "symbol": str(symbol),
                            "status": "success",
                        }
                    )
                except Exception as e:
                    failed_securities.append(
                        {"security_id": security_id, "status": "error", "error": str(e)}
                    )

            return {
                "status": "success",
                "etf_ticker": etf_ticker,
                "date": date,
                "resolution": resolution,
                "added_securities": added_securities,
                "failed_securities": failed_securities,
                "total_added": len(added_securities),
                "total_failed": len(failed_securities),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to add ETF universe securities for {etf_ticker}",
            }

    @mcp.tool()
    async def select_uncorrelated_assets(
        symbols: List[str],
        start_date: str,
        end_date: str,
        num_assets: int = 5,
        method: str = "lowest_correlation",
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Select uncorrelated or highly correlated assets from a universe.

        Args:
            symbols: List of symbols to analyze
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            num_assets: Number of assets to select
            method: Selection method ("lowest_correlation", "highest_correlation")
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing selected assets and correlation analysis
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from QuantConnect import Resolution  # type: ignore

            if method not in ["lowest_correlation", "highest_correlation"]:
                return {
                    "status": "error",
                    "error": "Method must be 'lowest_correlation' or 'highest_correlation'",
                }

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

            # Calculate returns and correlation
            close_price = history["close"].unstack(level=0)
            returns = close_price.pct_change().iloc[1:]
            correlation = returns.corr()

            # Calculate correlation rank for each asset
            selected_assets = []
            for symbol in symbols:
                if symbol in correlation.columns:
                    # Sum of absolute correlations (excluding self-correlation)
                    corr_rank = (
                        correlation[symbol].abs().sum() - 1
                    )  # Subtract 1 for self-correlation
                    selected_assets.append((symbol, corr_rank))

            # Sort based on method
            if method == "lowest_correlation":
                selected_assets.sort(key=lambda x: x[1])  # Ascending order
                title = "least correlated"
            else:
                selected_assets.sort(
                    key=lambda x: x[1], reverse=True
                )  # Descending order
                title = "most correlated"

            # Select top N assets
            selected = selected_assets[:num_assets]
            benchmark = (
                selected_assets[-num_assets:]
                if method == "lowest_correlation"
                else selected_assets[num_assets : 2 * num_assets]
            )

            # Get correlation matrix for selected assets
            selected_symbols = [item[0] for item in selected]
            selected_correlation = correlation.loc[selected_symbols, selected_symbols]

            # Calculate portfolio metrics for equal-weight portfolios
            selected_returns = returns[selected_symbols] / len(selected_symbols)
            selected_portfolio_return = selected_returns.sum(axis=1)

            benchmark_symbols = (
                [item[0] for item in benchmark] if len(benchmark) > 0 else []
            )
            benchmark_portfolio_return = None

            if benchmark_symbols:
                benchmark_returns = returns[benchmark_symbols] / len(benchmark_symbols)
                benchmark_portfolio_return = benchmark_returns.sum(axis=1)

            # Calculate performance metrics
            selected_performance = {
                "total_return": float((1 + selected_portfolio_return).prod() - 1),
                "volatility": float(selected_portfolio_return.std() * np.sqrt(252)),
                "sharpe_ratio": (
                    float(
                        selected_portfolio_return.mean()
                        * 252
                        / (selected_portfolio_return.std() * np.sqrt(252))
                    )
                    if selected_portfolio_return.std() > 0
                    else 0
                ),
            }

            benchmark_performance = None
            if benchmark_portfolio_return is not None:
                benchmark_performance = {
                    "total_return": float((1 + benchmark_portfolio_return).prod() - 1),
                    "volatility": float(
                        benchmark_portfolio_return.std() * np.sqrt(252)
                    ),
                    "sharpe_ratio": (
                        float(
                            benchmark_portfolio_return.mean()
                            * 252
                            / (benchmark_portfolio_return.std() * np.sqrt(252))
                        )
                        if benchmark_portfolio_return.std() > 0
                        else 0
                    ),
                }

            return {
                "status": "success",
                "method": method,
                "num_assets": num_assets,
                "selected_assets": {
                    "symbols": selected_symbols,
                    "correlation_ranks": [item[1] for item in selected],
                    "avg_correlation": float(np.mean([item[1] for item in selected])),
                    "performance": selected_performance,
                },
                "benchmark_assets": {
                    "symbols": benchmark_symbols,
                    "correlation_ranks": (
                        [item[1] for item in benchmark] if benchmark else []
                    ),
                    "avg_correlation": (
                        float(np.mean([item[1] for item in benchmark]))
                        if benchmark
                        else None
                    ),
                    "performance": benchmark_performance,
                },
                "correlation_matrix": selected_correlation.to_dict(),
                "selection_title": f"{num_assets} {title} assets",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to select uncorrelated assets",
            }

    @mcp.tool()
    async def screen_assets_by_criteria(
        symbols: List[str],
        start_date: str,
        end_date: str,
        min_return: Optional[float] = None,
        max_volatility: Optional[float] = None,
        min_sharpe: Optional[float] = None,
        max_correlation: Optional[float] = None,
        benchmark_symbol: Optional[str] = None,
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Screen assets based on various performance and risk criteria.

        Args:
            symbols: List of symbols to screen
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            min_return: Minimum annualized return threshold
            max_volatility: Maximum annualized volatility threshold
            min_sharpe: Minimum Sharpe ratio threshold
            max_correlation: Maximum correlation with benchmark threshold
            benchmark_symbol: Optional benchmark symbol for correlation screening
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing screened assets and their metrics
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from QuantConnect import Resolution  # type: ignore

            # Include benchmark if provided
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

            # Calculate returns
            close_price = history["close"].unstack(level=0)
            returns = close_price.pct_change().iloc[1:]

            # Calculate metrics for each asset
            asset_metrics = {}
            benchmark_returns = None

            if benchmark_symbol:
                benchmark_key = security_keys[-1]
                benchmark_returns = returns[benchmark_key]

            for i, symbol in enumerate(symbols):
                asset_key = security_keys[i]
                asset_returns = returns[asset_key]

                # Calculate performance metrics
                total_return = float((1 + asset_returns).prod() - 1)
                annualized_return = float((1 + asset_returns.mean()) ** 252 - 1)
                volatility = float(asset_returns.std() * np.sqrt(252))
                sharpe_ratio = (
                    float(annualized_return / volatility) if volatility > 0 else 0
                )

                # Calculate correlation with benchmark if provided
                correlation_with_benchmark = None
                if benchmark_returns is not None:
                    correlation_with_benchmark = float(
                        asset_returns.corr(benchmark_returns)
                    )

                asset_metrics[symbol] = {
                    "total_return": total_return,
                    "annualized_return": annualized_return,
                    "volatility": volatility,
                    "sharpe_ratio": sharpe_ratio,
                    "correlation_with_benchmark": correlation_with_benchmark,
                }

            # Apply screening criteria
            passed_assets = []
            failed_assets = []

            for symbol, metrics in asset_metrics.items():
                reasons_failed = []

                if min_return is not None and metrics["annualized_return"] is not None and metrics["annualized_return"] < min_return:
                    reasons_failed.append(
                        f"Return {metrics['annualized_return']:.3f} < {min_return}"
                    )

                if (
                    max_volatility is not None
                    and metrics["volatility"] is not None
                    and metrics["volatility"] > max_volatility
                ):
                    reasons_failed.append(
                        f"Volatility {metrics['volatility']:.3f} > {max_volatility}"
                    )

                if min_sharpe is not None and metrics["sharpe_ratio"] is not None and metrics["sharpe_ratio"] < min_sharpe:
                    reasons_failed.append(
                        f"Sharpe {metrics['sharpe_ratio']:.3f} < {min_sharpe}"
                    )

                if (
                    max_correlation is not None
                    and metrics["correlation_with_benchmark"] is not None
                ):
                    if abs(metrics["correlation_with_benchmark"]) > max_correlation:
                        reasons_failed.append(
                            f"Correlation {abs(metrics['correlation_with_benchmark']):.3f} > {max_correlation}"
                        )

                if reasons_failed:
                    failed_assets.append(
                        {
                            "symbol": symbol,
                            "metrics": metrics,
                            "reasons_failed": reasons_failed,
                        }
                    )
                else:
                    passed_assets.append({"symbol": symbol, "metrics": metrics})

            return {
                "status": "success",
                "screening_criteria": {
                    "min_return": min_return,
                    "max_volatility": max_volatility,
                    "min_sharpe": min_sharpe,
                    "max_correlation": max_correlation,
                    "benchmark_symbol": benchmark_symbol,
                },
                "passed_assets": passed_assets,
                "failed_assets": failed_assets,
                "total_screened": len(symbols),
                "total_passed": len(passed_assets),
                "total_failed": len(failed_assets),
                "pass_rate": float(len(passed_assets) / len(symbols)) if symbols else 0,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to screen assets by criteria",
            }

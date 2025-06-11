"""Statistical Analysis Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
import json
from .quantbook_tools import get_quantbook_instance


def register_analysis_tools(mcp: FastMCP):
    """Register statistical analysis tools with the MCP server."""

    @mcp.tool()
    async def perform_pca_analysis(
        symbols: List[str],
        start_date: str,
        end_date: str,
        n_components: Optional[int] = None,
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Perform Principal Component Analysis on historical returns.

        Args:
            symbols: List of symbols to analyze
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            n_components: Number of components to compute (default: all)
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing PCA results
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from sklearn.decomposition import PCA  # type: ignore
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

            if returns.empty:
                return {
                    "status": "error",
                    "error": "Insufficient data to calculate returns",
                }

            # Perform PCA
            pca = PCA(n_components=n_components)
            pca.fit(returns.dropna())

            # Get results
            components = [str(x + 1) for x in range(pca.n_components_)]
            explained_variance_ratio = (pca.explained_variance_ratio_ * 100).tolist()

            # Get component weights
            component_weights = {}
            for i, component in enumerate(components):
                component_weights[f"PC{component}"] = dict(
                    zip(symbols, pca.components_[i, :].tolist())
                )

            return {
                "status": "success",
                "symbols": symbols,
                "n_components": pca.n_components_,
                "explained_variance_ratio": explained_variance_ratio,
                "cumulative_variance_ratio": np.cumsum(
                    explained_variance_ratio
                ).tolist(),
                "component_weights": component_weights,
                "total_variance_explained": sum(explained_variance_ratio),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to perform PCA analysis",
            }

    @mcp.tool()
    async def test_cointegration(
        symbol1: str,
        symbol2: str,
        start_date: str,
        end_date: str,
        trend: str = "c",
        lags: int = 0,
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Perform Engle-Granger cointegration test between two assets.

        Args:
            symbol1: First symbol for cointegration test
            symbol2: Second symbol for cointegration test
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            trend: Trend specification ('c' for constant, 'ct' for constant+trend)
            lags: Number of lags to include
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing cointegration test results
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from arch.unitroot.cointegration import engle_granger  # type: ignore
            from datetime import datetime
            from QuantConnect import Resolution

            # Get security keys
            symbols = [symbol1, symbol2]
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

            # Get close prices and take log
            close_price = history["close"].unstack(level=0)
            log_price = np.log(close_price[[security_keys[0], security_keys[1]]])

            if len(log_price) < 10:
                return {
                    "status": "error",
                    "error": "Insufficient data points for cointegration test",
                }

            # Perform Engle-Granger test
            result = engle_granger(
                log_price.iloc[:, 0], log_price.iloc[:, 1], trend=trend, lags=lags
            )

            # Extract cointegrating vector and calculate spread
            coint_vector = result.cointegrating_vector[:2]
            spread = log_price @ coint_vector

            # Test stationarity of spread with ADF
            from statsmodels.tsa.stattools import adfuller  # type: ignore

            adf_result = adfuller(spread, maxlag=0)
            adf_pvalue = adf_result[1]

            return {
                "status": "success",
                "symbol1": symbol1,
                "symbol2": symbol2,
                "cointegration_statistic": float(result.stat),
                "cointegration_pvalue": float(result.pvalue),
                "cointegration_critical_values": {
                    f"{int(k*100)}%": float(v)
                    for k, v in result.critical_values.items()
                },
                "is_cointegrated": result.pvalue < 0.05,
                "cointegrating_vector": coint_vector.tolist(),
                "spread_adf_pvalue": float(adf_pvalue),
                "spread_is_stationary": adf_pvalue < 0.05,
                "spread_mean": float(spread.mean()),
                "spread_std": float(spread.std()),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to test cointegration between {symbol1} and {symbol2}",
            }

    @mcp.tool()
    async def analyze_mean_reversion(
        symbols: List[str],
        start_date: str,
        end_date: str,
        lookback_period: int = 30,
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Analyze mean reversion signals for given symbols.

        Args:
            symbols: List of symbols to analyze
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            lookback_period: Lookback period for moving average and std
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing mean reversion analysis results
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from scipy.stats import zscore, norm  # type: ignore
            from datetime import datetime
            from QuantConnect import Resolution

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

            # Get close prices
            df = history["close"].unstack(level=0)

            # Calculate mean reversion signals
            rolling_mean = df.rolling(lookback_period).mean()
            rolling_std = df.rolling(lookback_period).std()

            # Identify mean reversion opportunities (price < mean - 1 std)
            classifier = df.le(rolling_mean - rolling_std)

            # Calculate z-scores and expected returns for signals
            z_score = df.apply(zscore)[classifier]
            magnitude = -z_score * rolling_std / df
            confidence = (-z_score).apply(norm.cdf)

            # Fill NaN values
            magnitude = magnitude.fillna(0)
            confidence = confidence.fillna(0)

            # Calculate portfolio weights (long-only, normalized)
            weight = confidence - 1 / (magnitude + 1)
            weight = weight[weight > 0].fillna(0)

            # Normalize weights
            weight_sums = weight.sum(axis=1)
            for i in range(len(weight)):
                if weight_sums.iloc[i] > 0:
                    weight.iloc[i] = weight.iloc[i] / weight_sums.iloc[i]
                else:
                    weight.iloc[i] = 0

            # Get summary statistics
            results = {}
            for symbol in symbols:
                if symbol in df.columns:
                    col_data = df[symbol].dropna()
                    if len(col_data) > lookback_period:
                        current_price = float(col_data.iloc[-1])
                        mean_price = float(rolling_mean[symbol].iloc[-1])
                        std_price = float(rolling_std[symbol].iloc[-1])
                        z_score_current = (
                            (current_price - mean_price) / std_price
                            if std_price > 0
                            else 0
                        )

                        results[symbol] = {
                            "current_price": current_price,
                            "mean_price": mean_price,
                            "std_price": std_price,
                            "z_score": float(z_score_current),
                            "is_mean_reversion_signal": z_score_current < -1,
                            "signal_strength": (
                                abs(float(z_score_current))
                                if z_score_current < -1
                                else 0
                            ),
                        }

            return {
                "status": "success",
                "symbols": symbols,
                "lookback_period": lookback_period,
                "analysis_results": results,
                "total_signals": sum(
                    1
                    for r in results.values()
                    if r.get("is_mean_reversion_signal", False)
                ),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to analyze mean reversion",
            }

    @mcp.tool()
    async def calculate_correlation_matrix(
        symbols: List[str],
        start_date: str,
        end_date: str,
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Calculate correlation matrix for given symbols.

        Args:
            symbols: List of symbols to analyze
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing correlation matrix and statistics
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from datetime import datetime
            from QuantConnect import Resolution

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

            # Calculate returns
            close_price = history["close"].unstack(level=0)
            returns = close_price.pct_change().iloc[1:]

            # Calculate correlation matrix
            correlation = returns.corr()

            # Find most and least correlated pairs
            correlations_list = []
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    if (
                        symbols[i] in correlation.columns
                        and symbols[j] in correlation.columns
                    ):
                        corr_value = correlation.loc[symbols[i], symbols[j]]
                        correlations_list.append(
                            {
                                "symbol1": symbols[i],
                                "symbol2": symbols[j],
                                "correlation": float(corr_value),
                            }
                        )

            # Sort by correlation
            correlations_list.sort(key=lambda x: abs(float(str(x["correlation"]))), reverse=True)

            # Get correlation summary for each asset
            asset_correlations = {}
            for symbol in symbols:
                if symbol in correlation.columns:
                    corr_sum = (
                        correlation[symbol].abs().sum() - 1
                    )  # Exclude self-correlation
                    asset_correlations[symbol] = {
                        "avg_abs_correlation": float(corr_sum / (len(symbols) - 1)),
                        "max_correlation": float(
                            correlation[symbol].drop(symbol).max()
                        ),
                        "min_correlation": float(
                            correlation[symbol].drop(symbol).min()
                        ),
                    }

            return {
                "status": "success",
                "symbols": symbols,
                "correlation_matrix": correlation.to_dict(),
                "highest_correlations": correlations_list[:5],
                "lowest_correlations": sorted(
                    correlations_list, key=lambda x: abs(float(str(x["correlation"])))
                )[:5],
                "asset_correlation_summary": asset_correlations,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to calculate correlation matrix",
            }

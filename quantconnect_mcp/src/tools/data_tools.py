"""Data Retrieval Tools for QuantConnect MCP Server (Container-Based)"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import pandas as pd
import json
import logging
from .quantbook_tools import get_quantbook_session

logger = logging.getLogger(__name__)


def register_data_tools(mcp: FastMCP):
    """Register data retrieval tools with the MCP server."""

    @mcp.tool()
    async def add_equity(
        ticker: str, resolution: str = "Daily", instance_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Add an equity security to the QuantBook instance.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL", "SPY")
            resolution: Data resolution (Minute, Hour, Daily)
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing the added security information
        """
        session = await get_quantbook_session(instance_name)
        if session is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
                "message": "Initialize a QuantBook instance first using initialize_quantbook",
            }

        try:
            # Validate resolution
            valid_resolutions = ["Minute", "Hour", "Daily"]
            if resolution not in valid_resolutions:
                return {
                    "status": "error",
                    "error": f"Invalid resolution '{resolution}'. Must be one of: {valid_resolutions}",
                }

            # Execute code to add equity in container
            add_equity_code = f"""
from QuantConnect import Resolution

# Map string resolution to enum
resolution_map = {{
    "Minute": Resolution.Minute,
    "Hour": Resolution.Hour,
    "Daily": Resolution.Daily,
}}

try:
    # Add equity to QuantBook
    security = qb.AddEquity("{ticker}", resolution_map["{resolution}"])
    symbol = str(security.Symbol)
    
    print(f"Successfully added equity '{ticker}' with {resolution} resolution")
    print(f"Symbol: {{symbol}}")
    
    # Store result for return
    result = {{
        "ticker": "{ticker}",
        "symbol": symbol,
        "resolution": "{resolution}",
        "success": True
    }}
    
except Exception as e:
    print(f"Failed to add equity '{ticker}': {{e}}")
    result = {{
        "ticker": "{ticker}",
        "error": str(e),
        "success": False
    }}
"""

            execution_result = await session.execute(add_equity_code)
            
            if execution_result["status"] != "success":
                return {
                    "status": "error",
                    "error": execution_result.get("error", "Unknown error"),
                    "message": f"Failed to add equity '{ticker}'",
                    "execution_output": execution_result.get("output", ""),
                }

            return {
                "status": "success",
                "ticker": ticker,
                "resolution": resolution,
                "message": f"Successfully added equity '{ticker}' with {resolution} resolution",
                "execution_output": execution_result.get("output", ""),
                "instance_name": instance_name,
            }

        except Exception as e:
            logger.error(f"Failed to add equity '{ticker}' in instance '{instance_name}': {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to add equity '{ticker}'",
            }

    @mcp.tool()
    async def add_multiple_equities(
        tickers: List[str], resolution: str = "Daily", instance_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Add multiple equity securities to the QuantBook instance.

        Args:
            tickers: List of stock ticker symbols
            resolution: Data resolution (Minute, Hour, Daily)
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing results for all added securities
        """
        session = await get_quantbook_session(instance_name)
        if session is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
                "message": "Initialize a QuantBook instance first using initialize_quantbook",
            }

        try:
            # Validate resolution
            valid_resolutions = ["Minute", "Hour", "Daily"]
            if resolution not in valid_resolutions:
                return {
                    "status": "error",
                    "error": f"Invalid resolution '{resolution}'. Must be one of: {valid_resolutions}",
                }

            # Convert tickers list to Python code representation
            tickers_str = str(tickers)

            # Execute code to add multiple equities in container
            add_multiple_code = f"""
from QuantConnect import Resolution

# Map string resolution to enum
resolution_map = {{
    "Minute": Resolution.Minute,
    "Hour": Resolution.Hour,
    "Daily": Resolution.Daily,
}}

tickers = {tickers_str}
resolution = "{resolution}"
results = []
symbols = {{}}

for ticker in tickers:
    try:
        security = qb.AddEquity(ticker, resolution_map[resolution])
        symbol = str(security.Symbol)
        symbols[ticker] = symbol
        results.append({{
            "ticker": ticker,
            "symbol": symbol,
            "status": "success"
        }})
        print(f"Added equity {{ticker}} with symbol {{symbol}}")
    except Exception as e:
        results.append({{
            "ticker": ticker,
            "status": "error",
            "error": str(e)
        }})
        print(f"Failed to add equity {{ticker}}: {{e}}")

print(f"Successfully added {{len([r for r in results if r['status'] == 'success'])}} out of {{len(tickers)}} equities")
"""

            execution_result = await session.execute(add_multiple_code)
            
            if execution_result["status"] != "success":
                return {
                    "status": "error",
                    "error": execution_result.get("error", "Unknown error"),
                    "message": "Failed to add multiple equities",
                    "execution_output": execution_result.get("output", ""),
                }

            return {
                "status": "success",
                "resolution": resolution,
                "message": f"Processed {len(tickers)} equities",
                "execution_output": execution_result.get("output", ""),
                "instance_name": instance_name,
            }

        except Exception as e:
            logger.error(f"Failed to add multiple equities in instance '{instance_name}': {e}")
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to add multiple equities",
            }

    @mcp.tool()
    async def get_history(
        symbols: Union[str, List[str]],
        start_date: str,
        end_date: str,
        resolution: str = "Daily",
        instance_name: str = "default",
        fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve historical data for specified symbols.

        Args:
            symbols: Single ticker or list of tickers to get history for
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            resolution: Data resolution (Minute, Hour, Daily)
            instance_name: QuantBook instance name
            fields: Specific fields to return (open, high, low, close, volume)

        Returns:
            Dictionary containing historical data
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from QuantConnect import Resolution  # type: ignore
            from datetime import datetime

            # Parse dates
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

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

            # Handle single symbol vs multiple symbols
            if isinstance(symbols, str):
                symbols = [symbols]

            # Get securities keys for the symbols
            security_keys = []
            for symbol in symbols:
                # Find the security in qb.Securities
                found = False
                for sec_key in qb.Securities.Keys:
                    if str(sec_key).upper() == symbol.upper():
                        security_keys.append(sec_key)
                        found = True
                        break
                if not found:
                    return {
                        "status": "error",
                        "error": f"Symbol '{symbol}' not found in securities. Add it first using add_equity.",
                    }

            # Get historical data
            history = qb.History(security_keys, start, end, resolution_map[resolution])

            if history.empty:
                return {
                    "status": "success",
                    "data": {},
                    "message": "No data found for the specified period",
                }

            # Convert to dictionary format
            if fields:
                # Filter specific fields
                available_fields = [col for col in history.columns if col in fields]
                if available_fields:
                    history = history[available_fields]

            # Convert to JSON-serializable format
            data = {}
            for col in history.columns:
                if col in ["open", "high", "low", "close", "volume"]:
                    data[col] = history[col].unstack(level=0).to_dict()

            return {
                "status": "success",
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "resolution": resolution,
                "data": data,
                "shape": list(history.shape),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to retrieve history for symbols: {symbols}",
            }

    @mcp.tool()
    async def add_alternative_data(
        data_type: str, symbol: str, instance_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Add alternative data source to a security.

        Args:
            data_type: Type of alternative data (e.g., "SmartInsiderTransaction")
            symbol: Symbol to add alternative data for
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing alternative data subscription info
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            # Map data types to QuantConnect classes
            if data_type == "SmartInsiderTransaction":
                from QuantConnect.DataSource import SmartInsiderTransaction  # type: ignore

                # Find the symbol in securities
                target_symbol = None
                for sec_key in qb.Securities.Keys:
                    if str(sec_key).upper() == symbol.upper():
                        target_symbol = sec_key
                        break

                if target_symbol is None:
                    return {
                        "status": "error",
                        "error": f"Symbol '{symbol}' not found. Add it as equity first.",
                    }

                alt_symbol = qb.AddData(SmartInsiderTransaction, target_symbol).Symbol

                return {
                    "status": "success",
                    "data_type": data_type,
                    "symbol": symbol,
                    "alt_symbol": str(alt_symbol),
                    "message": f"Successfully added {data_type} data for {symbol}",
                }
            else:
                return {
                    "status": "error",
                    "error": f"Unsupported data type '{data_type}'. Currently supported: SmartInsiderTransaction",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to add {data_type} data for {symbol}",
            }

    @mcp.tool()
    async def get_alternative_data_history(
        data_type: str,
        symbols: Union[str, List[str]],
        start_date: str,
        end_date: str,
        instance_name: str = "default",
    ) -> Dict[str, Any]:
        """
        Retrieve historical alternative data.

        Args:
            data_type: Type of alternative data
            symbols: Symbol(s) to get alternative data for
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            instance_name: QuantBook instance name

        Returns:
            Dictionary containing alternative data history
        """
        qb = get_quantbook_instance(instance_name)
        if qb is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
            }

        try:
            from datetime import datetime

            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            if isinstance(symbols, str):
                symbols = [symbols]

            # Get alternative data symbols
            alt_symbols = []
            for symbol in symbols:
                # Find alternative data symbols for this equity
                for sec_key in qb.Securities.Keys:
                    if (
                        data_type.lower() in str(sec_key).lower()
                        and symbol.upper() in str(sec_key).upper()
                    ):
                        alt_symbols.append(sec_key)

            if not alt_symbols:
                return {
                    "status": "error",
                    "error": f"No {data_type} data found for symbols {symbols}. Add alternative data first.",
                }

            # Get history
            from QuantConnect import Resolution  # type: ignore

            history = qb.History(alt_symbols, start, end, Resolution.Daily)

            if history.empty:
                return {
                    "status": "success",
                    "data": {},
                    "message": "No alternative data found for the specified period",
                }

            # Convert to JSON format
            data = {}
            for col in history.columns:
                data[col] = history[col].unstack(level=0).to_dict()

            return {
                "status": "success",
                "data_type": data_type,
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "data": data,
                "shape": list(history.shape),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to retrieve {data_type} history",
            }

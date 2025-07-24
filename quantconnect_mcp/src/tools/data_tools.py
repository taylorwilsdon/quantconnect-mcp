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
    
    # Print result as JSON for MCP to parse
    import json
    print("=== QUANTBOOK_RESULT_START ===")
    print(json.dumps(result))
    print("=== QUANTBOOK_RESULT_END ===")
    
except Exception as e:
    print(f"Failed to add equity '{ticker}': {{e}}")
    result = {{
        "ticker": "{ticker}",
        "error": str(e),
        "success": False
    }}
    
    # Print error result as JSON
    import json
    print("=== QUANTBOOK_RESULT_START ===")
    print(json.dumps(result))
    print("=== QUANTBOOK_RESULT_END ===")
"""

            execution_result = await session.execute(add_equity_code)
            
            if execution_result["status"] != "success":
                return {
                    "status": "error",
                    "error": execution_result.get("error", "Unknown error"),
                    "message": f"Failed to add equity '{ticker}'",
                    "execution_output": execution_result.get("output", ""),
                }

            # Parse the JSON result from container output
            output = execution_result.get("output", "")
            parsed_result = None
            
            try:
                # Extract JSON result from container output
                if "=== QUANTBOOK_RESULT_START ===" in output and "=== QUANTBOOK_RESULT_END ===" in output:
                    start_marker = output.find("=== QUANTBOOK_RESULT_START ===")
                    end_marker = output.find("=== QUANTBOOK_RESULT_END ===")
                    if start_marker != -1 and end_marker != -1:
                        json_start = start_marker + len("=== QUANTBOOK_RESULT_START ===\n")
                        json_content = output[json_start:end_marker].strip()
                        parsed_result = json.loads(json_content)
                
                if parsed_result and parsed_result.get("success"):
                    # Return successful result with parsed data
                    return {
                        "status": "success",
                        "ticker": ticker,
                        "symbol": parsed_result.get("symbol", ticker),
                        "resolution": resolution,
                        "message": f"Successfully added equity '{ticker}' with {resolution} resolution",
                        "execution_output": output,
                        "instance_name": instance_name,
                    }
                elif parsed_result and not parsed_result.get("success"):
                    # Container execution succeeded but equity addition failed
                    return {
                        "status": "error",
                        "error": parsed_result.get("error", "Unknown equity addition error"),
                        "message": f"Failed to add equity '{ticker}'",
                        "execution_output": output,
                        "instance_name": instance_name,
                    }
                else:
                    # Fallback if JSON parsing fails but execution succeeded
                    return {
                        "status": "success",
                        "ticker": ticker,
                        "resolution": resolution,
                        "message": f"Successfully added equity '{ticker}' with {resolution} resolution",
                        "execution_output": output,
                        "instance_name": instance_name,
                    }
                    
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "error": f"Failed to parse container result: {e}",
                    "message": f"Container executed but result parsing failed",
                    "execution_output": output,
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

            # Handle single symbol vs multiple symbols
            if isinstance(symbols, str):
                symbols_list = [symbols]
            else:
                symbols_list = symbols

            # Convert symbols list to Python code representation
            symbols_str = str(symbols_list)
            
            # Build fields filter if specified
            fields_filter = ""
            if fields:
                fields_str = str(fields)
                fields_filter = f"""
    # Filter specific fields if requested
    if not history.empty:
        available_fields = [col for col in history.columns if col in {fields_str}]
        if available_fields:
            history = history[available_fields]
"""

            # Execute code to get historical data in container
            get_history_code = f"""
from QuantConnect import Resolution
from datetime import datetime
import pandas as pd

# Map string resolution to enum
resolution_map = {{
    "Minute": Resolution.Minute,
    "Hour": Resolution.Hour,
    "Daily": Resolution.Daily,
}}

try:
    # Parse dates
    start_date = datetime.strptime("{start_date}", "%Y-%m-%d")
    end_date = datetime.strptime("{end_date}", "%Y-%m-%d")
    
    symbols_list = {symbols_str}
    resolution_val = resolution_map["{resolution}"]
    
    # Get historical data
    history = qb.History(symbols_list, start_date, end_date, resolution_val)
    
    print(f"Retrieved history for {{symbols_list}}: {{len(history)}} data points")
    
    if history.empty:
        print("No data found for the specified period")
        result = {{
            "status": "success",
            "data": {{}},
            "message": "No data found for the specified period",
            "symbols": symbols_list,
            "start_date": "{start_date}",
            "end_date": "{end_date}",
            "resolution": "{resolution}",
            "shape": [0, 0]
        }}
    else:
        {fields_filter}
        
        # Convert to JSON-serializable format
        data = {{}}
        for col in history.columns:
            if col in ["open", "high", "low", "close", "volume"]:
                if len(symbols_list) == 1:
                    # Single symbol - simpler format
                    data[col] = history[col].to_dict()
                else:
                    # Multiple symbols - unstack format
                    data[col] = history[col].unstack(level=0).to_dict()
        
        result = {{
            "status": "success",
            "symbols": symbols_list,
            "start_date": "{start_date}",
            "end_date": "{end_date}",
            "resolution": "{resolution}",
            "data": data,
            "shape": list(history.shape),
        }}
        
        # Print result as JSON for MCP to parse
        import json
        print("=== QUANTBOOK_RESULT_START ===")
        print(json.dumps(result, default=str))  # default=str handles datetime objects
        print("=== QUANTBOOK_RESULT_END ===")
    
    print("Historical data retrieval completed successfully")
    
except Exception as e:
    print(f"Error retrieving historical data: {{e}}")
    result = {{
        "status": "error",
        "error": str(e),
        "message": f"Failed to retrieve history for symbols: {symbols_str}",
    }}
    
    # Print error result as JSON
    import json
    print("=== QUANTBOOK_RESULT_START ===")
    print(json.dumps(result))
    print("=== QUANTBOOK_RESULT_END ===")
"""

            execution_result = await session.execute(get_history_code)
            
            if execution_result["status"] != "success":
                return {
                    "status": "error",
                    "error": execution_result.get("error", "Unknown error"),
                    "message": f"Failed to retrieve history for symbols: {symbols}",
                    "execution_output": execution_result.get("output", ""),
                }

            # Parse the JSON result from container output
            output = execution_result.get("output", "")
            parsed_result = None
            
            try:
                # Extract JSON result from container output
                if "=== QUANTBOOK_RESULT_START ===" in output and "=== QUANTBOOK_RESULT_END ===" in output:
                    start_marker = output.find("=== QUANTBOOK_RESULT_START ===")
                    end_marker = output.find("=== QUANTBOOK_RESULT_END ===")
                    if start_marker != -1 and end_marker != -1:
                        json_start = start_marker + len("=== QUANTBOOK_RESULT_START ===\n")
                        json_content = output[json_start:end_marker].strip()
                        parsed_result = json.loads(json_content)
                
                if parsed_result:
                    # Return the parsed result with additional metadata
                    result = parsed_result.copy()
                    result["execution_output"] = output
                    result["instance_name"] = instance_name
                    return result
                else:
                    # Fallback if JSON parsing fails
                    return {
                        "status": "success",
                        "symbols": symbols,
                        "start_date": start_date,
                        "end_date": end_date,
                        "resolution": resolution,
                        "message": f"Successfully executed but no structured result found",
                        "execution_output": output,
                        "instance_name": instance_name,
                    }
                    
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "error": f"Failed to parse container result: {e}",
                    "message": f"Container executed but result parsing failed",
                    "execution_output": output,
                    "instance_name": instance_name,
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
        session = await get_quantbook_session(instance_name)
        if session is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
                "message": "Initialize a QuantBook instance first using initialize_quantbook",
            }

        try:
            # TODO: Convert to container execution like other functions
            return {
                "status": "error",
                "error": "Alternative data functions need to be updated for container execution",
                "message": f"add_alternative_data is temporarily disabled pending container execution update",
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
        session = await get_quantbook_session(instance_name)
        if session is None:
            return {
                "status": "error",
                "error": f"QuantBook instance '{instance_name}' not found",
                "message": "Initialize a QuantBook instance first using initialize_quantbook",
            }

        try:
            # TODO: Convert to container execution like other functions
            return {
                "status": "error",
                "error": "Alternative data functions need to be updated for container execution",
                "message": f"get_alternative_data_history is temporarily disabled pending container execution update",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to retrieve {data_type} history",
            }

"""Authentication Management Tools for QuantConnect MCP Server"""

from fastmcp import FastMCP
from typing import Dict, Any, Optional
from ..auth import QuantConnectAuth, configure_auth, validate_authentication, get_auth_instance  # type: ignore


def register_auth_tools(mcp: FastMCP):
    """Register authentication management tools with the MCP server."""

    @mcp.tool()
    async def configure_quantconnect_auth(
        user_id: str, api_token: str, organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Configure QuantConnect API authentication credentials.

        Args:
            user_id: Your QuantConnect user ID (from email)
            api_token: Your QuantConnect API token (from Settings page)
            organization_id: Your organization ID (from organization URL)

        Returns:
            Dictionary containing authentication configuration status
        """
        try:
            # Configure authentication
            auth = configure_auth(user_id, api_token, organization_id)

            # Validate the configuration
            is_valid, message = await auth.validate_authentication()

            if is_valid:
                return {
                    "status": "success",
                    "message": "QuantConnect authentication configured and validated successfully",
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "has_organization": organization_id is not None,
                    "authenticated": True,
                }
            else:
                return {
                    "status": "error",
                    "error": f"Authentication validation failed: {message}",
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "authenticated": False,
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to configure QuantConnect authentication",
            }

    @mcp.tool()
    async def validate_quantconnect_auth() -> Dict[str, Any]:
        """
        Validate current QuantConnect authentication configuration.

        Returns:
            Dictionary containing authentication validation results
        """
        try:
            auth = get_auth_instance()

            if auth is None:
                return {
                    "status": "error",
                    "error": "Authentication not configured",
                    "message": "Use configure_quantconnect_auth to set up credentials first",
                    "authenticated": False,
                }

            # Validate authentication
            is_valid, message = await auth.validate_authentication()

            return {
                "status": "success" if is_valid else "error",
                "authenticated": is_valid,
                "message": message,
                "user_id": auth.user_id,
                "organization_id": auth.organization_id,
                "has_organization": auth.organization_id is not None,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to validate authentication",
                "authenticated": False,
            }

    @mcp.tool()
    async def get_auth_status() -> Dict[str, Any]:
        """
        Get current authentication status and configuration.

        Returns:
            Dictionary containing authentication status information
        """
        try:
            auth = get_auth_instance()

            if auth is None:
                return {
                    "status": "not_configured",
                    "authenticated": False,
                    "message": "QuantConnect authentication not configured",
                    "required_credentials": [
                        "user_id - Your QuantConnect user ID",
                        "api_token - Your QuantConnect API token",
                        "organization_id - Your organization ID (optional)",
                    ],
                    "setup_instructions": "Use configure_quantconnect_auth tool to set up credentials",
                }

            return {
                "status": "configured",
                "user_id": auth.user_id,
                "organization_id": auth.organization_id,
                "has_organization": auth.organization_id is not None,
                "api_base_url": auth.base_url,
                "message": "Authentication configured - use validate_quantconnect_auth to test",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to get authentication status",
            }

    @mcp.tool()
    async def test_quantconnect_api(
        endpoint: str = "authenticate", method: str = "POST"
    ) -> Dict[str, Any]:
        """
        Test QuantConnect API connectivity with current authentication.

        Args:
            endpoint: API endpoint to test (default: authenticate)
            method: HTTP method to use (default: POST)

        Returns:
            Dictionary containing API test results
        """
        try:
            auth = get_auth_instance()

            if auth is None:
                return {
                    "status": "error",
                    "error": "Authentication not configured",
                    "message": "Configure authentication first using configure_quantconnect_auth",
                }

            # Make API request
            response = await auth.make_authenticated_request(endpoint, method)

            # Parse response
            try:
                response_data = response.json()
            except:
                response_data = {"raw_content": response.text}

            return {
                "status": "success",
                "endpoint": endpoint,
                "method": method,
                "status_code": response.status_code,
                "response_data": response_data,
                "headers": dict(response.headers),
                "success": response.status_code == 200,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": f"Failed to test API endpoint: {endpoint}",
            }

    @mcp.tool()
    async def clear_quantconnect_auth() -> Dict[str, Any]:
        """
        Clear current QuantConnect authentication configuration.

        Returns:
            Dictionary containing operation status
        """
        try:
            from ..auth import quantconnect_auth  # type: ignore

            # Clear the auth instance
            quantconnect_auth._auth_instance = None

            return {
                "status": "success",
                "message": "QuantConnect authentication cleared successfully",
                "authenticated": False,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to clear authentication",
            }

    @mcp.tool()
    async def get_auth_headers_info() -> Dict[str, Any]:
        """
        Get information about authentication headers (without exposing sensitive data).

        Returns:
            Dictionary containing header information
        """
        try:
            auth = get_auth_instance()

            if auth is None:
                return {"status": "error", "error": "Authentication not configured"}

            # Get headers (but don't expose the actual values)
            headers = auth.get_headers()

            return {
                "status": "success",
                "header_fields": list(headers.keys()),
                "has_authorization": "Authorization" in headers,
                "has_timestamp": "Timestamp" in headers,
                "timestamp_format": "Unix timestamp",
                "auth_method": "Basic Authentication with SHA-256 hashed token",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to get authentication header information",
            }

    @mcp.tool()
    async def read_account() -> Dict[str, Any]:
        """
        Read the organization account status.

        Returns:
            Dictionary containing account status and information
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="account/read", method="POST"
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    account = data.get("account", {})
                    
                    return {
                        "status": "success",
                        "account": account,
                        "message": "Successfully retrieved account information",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to read account information",
                        "details": errors,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to read account: {str(e)}",
            }

    @mcp.tool()
    async def authorize_connection(
        brokerage_id: str, 
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Authorize an external connection with a live brokerage or data provider.

        Args:
            brokerage_id: Brokerage identifier (e.g., "InteractiveBrokersBrokerage")
            credentials: Dictionary containing brokerage-specific credentials

        Returns:
            Dictionary containing authorization result
        """
        auth = get_auth_instance()
        if auth is None:
            return {
                "status": "error",
                "error": "QuantConnect authentication not configured. Use configure_auth() first.",
            }

        try:
            # Prepare request data
            request_data = {
                "id": brokerage_id,
                **credentials  # Spread credentials into the request data
            }

            # Make API request
            response = await auth.make_authenticated_request(
                endpoint="live/connection/authorize", method="POST", json=request_data
            )

            # Parse response
            if response.status_code == 200:
                data = response.json()

                if data.get("success", False):
                    connection = data.get("connection", {})
                    
                    return {
                        "status": "success",
                        "brokerage_id": brokerage_id,
                        "connection": connection,
                        "message": f"Successfully authorized connection to {brokerage_id}",
                    }
                else:
                    # API returned success=false
                    errors = data.get("errors", ["Unknown error"])
                    return {
                        "status": "error",
                        "error": "Failed to authorize connection",
                        "details": errors,
                        "brokerage_id": brokerage_id,
                    }

            elif response.status_code == 401:
                return {
                    "status": "error",
                    "error": "Authentication failed. Check your credentials and ensure they haven't expired.",
                }

            else:
                return {
                    "status": "error",
                    "error": f"API request failed with status {response.status_code}",
                    "response_text": (
                        response.text[:500]
                        if hasattr(response, "text")
                        else "No response text"
                    ),
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to authorize connection: {str(e)}",
                "brokerage_id": brokerage_id,
            }

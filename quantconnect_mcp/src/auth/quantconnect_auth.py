"""QuantConnect API Authentication Implementation"""

import os
from base64 import b64encode
from hashlib import sha256
from time import time
from typing import Dict, Optional, Tuple
import httpx


class QuantConnectAuth:
    """QuantConnect API authentication handler."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        api_token: Optional[str] = None,
        organization_id: Optional[str] = None,
    ):
        """
        Initialize QuantConnect authentication.

        Args:
            user_id: QuantConnect user ID (from email or environment)
            api_token: QuantConnect API token (from settings or environment)
            organization_id: QuantConnect organization ID (from URL or environment)
        """
        self.user_id = user_id or os.getenv("QUANTCONNECT_USER_ID")
        self.api_token = api_token or os.getenv("QUANTCONNECT_API_TOKEN")
        self.organization_id = organization_id or os.getenv(
            "QUANTCONNECT_ORGANIZATION_ID"
        )
        self.base_url = "https://www.quantconnect.com/api/v2/"

        if not self.user_id or not self.api_token:
            raise ValueError(
                "QuantConnect credentials required. Set QUANTCONNECT_USER_ID and QUANTCONNECT_API_TOKEN "
                "environment variables or provide them directly."
            )

    def get_headers(self) -> Dict[str, str]:
        """
        Generate authenticated headers for QuantConnect API requests.

        Returns:
            Dictionary containing Authorization and Timestamp headers
        """
        # Get timestamp
        timestamp = f"{int(time())}"
        time_stamped_token = f"{self.api_token}:{timestamp}".encode("utf-8")

        # Get hashed API token
        hashed_token = sha256(time_stamped_token).hexdigest()
        authentication = f"{self.user_id}:{hashed_token}".encode("utf-8")
        authentication_encoded = b64encode(authentication).decode("ascii")

        # Create headers dictionary
        return {
            "Authorization": f"Basic {authentication_encoded}",
            "Timestamp": timestamp,
            "Content-Type": "application/json",
        }

    async def validate_authentication(self) -> Tuple[bool, str]:
        """
        Validate authentication by calling the /authenticate endpoint.

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}authenticate", headers=self.get_headers()
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", False):
                        return True, "Authentication successful"
                    else:
                        return False, "Authentication failed: Invalid response"
                elif response.status_code == 401:
                    return (
                        False,
                        "Authentication failed: Invalid credentials or expired timestamp",
                    )
                else:
                    return False, f"Authentication failed: HTTP {response.status_code}"

        except Exception as e:
            return False, f"Authentication error: {str(e)}"

    async def make_authenticated_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
    ) -> httpx.Response:
        """
        Make an authenticated request to QuantConnect API.

        Args:
            endpoint: API endpoint (without base URL)
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Form data for the request
            json: JSON data for the request

        Returns:
            HTTP response object
        """
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint.lstrip('/')}"
            headers = self.get_headers()

            if method.upper() == "GET":
                return await client.get(url, headers=headers)
            elif method.upper() == "POST":
                if json is not None:
                    return await client.post(url, headers=headers, json=json)
                else:
                    return await client.post(url, headers=headers, data=data or {})
            elif method.upper() == "PUT":
                if json is not None:
                    return await client.put(url, headers=headers, json=json)
                else:
                    return await client.put(url, headers=headers, data=data or {})
            elif method.upper() == "DELETE":
                return await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")


# Global authentication instance
_auth_instance: Optional[QuantConnectAuth] = None


def get_auth_headers() -> Dict[str, str]:
    """
    Get authentication headers using the global auth instance.

    Returns:
        Dictionary containing authentication headers

    Raises:
        ValueError: If authentication is not configured
    """
    global _auth_instance
    if _auth_instance is None:
        raise ValueError(
            "QuantConnect authentication not configured. Call configure_auth() first."
        )

    return _auth_instance.get_headers()


def configure_auth(
    user_id: Optional[str] = None,
    api_token: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> QuantConnectAuth:
    """
    Configure global QuantConnect authentication.

    Args:
        user_id: QuantConnect user ID
        api_token: QuantConnect API token
        organization_id: QuantConnect organization ID

    Returns:
        Configured QuantConnectAuth instance
    """
    global _auth_instance
    _auth_instance = QuantConnectAuth(user_id, api_token, organization_id)
    return _auth_instance


def get_auth_instance() -> Optional[QuantConnectAuth]:
    """Get the global authentication instance."""
    return _auth_instance


async def validate_authentication() -> Tuple[bool, str]:
    """
    Validate the current authentication configuration.

    Returns:
        Tuple of (is_valid, message)
    """
    global _auth_instance
    if _auth_instance is None:
        return False, "Authentication not configured"

    return await _auth_instance.validate_authentication()

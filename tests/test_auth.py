"""Tests for QuantConnect Authentication System"""

import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.auth.quantconnect_auth import (
    QuantConnectAuth,
    configure_auth,
    get_auth_instance,
)


class TestQuantConnectAuth:
    """Test QuantConnect authentication functionality."""

    def test_auth_initialization_with_credentials(self):
        """Test QuantConnectAuth initialization with direct credentials."""
        auth = QuantConnectAuth(
            user_id="123456", api_token="test_token", organization_id="test_org"
        )

        assert auth.user_id == "123456"
        assert auth.api_token == "test_token"
        assert auth.organization_id == "test_org"
        assert auth.base_url == "https://www.quantconnect.com/api/v2/"

    def test_auth_initialization_missing_credentials(self):
        """Test that initialization fails with missing credentials."""
        with pytest.raises(ValueError, match="QuantConnect credentials required"):
            QuantConnectAuth()

    @patch.dict(
        "os.environ",
        {
            "QUANTCONNECT_USER_ID": "789012",
            "QUANTCONNECT_API_TOKEN": "env_token",
            "QUANTCONNECT_ORGANIZATION_ID": "env_org",
        },
    )
    def test_auth_initialization_from_environment(self):
        """Test QuantConnectAuth initialization from environment variables."""
        auth = QuantConnectAuth()

        assert auth.user_id == "789012"
        assert auth.api_token == "env_token"
        assert auth.organization_id == "env_org"

    def test_get_headers_structure(self):
        """Test that authentication headers have correct structure."""
        auth = QuantConnectAuth(user_id="123456", api_token="test_token")

        headers = auth.get_headers()

        assert "Authorization" in headers
        assert "Timestamp" in headers
        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"].startswith("Basic ")

    def test_get_headers_timestamp_format(self):
        """Test that timestamp is in correct format."""
        auth = QuantConnectAuth(user_id="123456", api_token="test_token")

        headers = auth.get_headers()
        timestamp = headers["Timestamp"]

        # Should be a numeric timestamp
        assert timestamp.isdigit()
        assert len(timestamp) == 10  # Unix timestamp should be 10 digits

    def test_configure_auth_global(self):
        """Test global authentication configuration."""
        auth = configure_auth(
            user_id="123456", api_token="test_token", organization_id="test_org"
        )

        assert auth is not None
        assert get_auth_instance() is auth
        assert auth.user_id == "123456"


@pytest.mark.asyncio
class TestAuthenticationAPI:
    """Test authentication API functionality."""

    async def test_validate_authentication_structure(self):
        """Test authentication validation method structure."""
        auth = QuantConnectAuth(user_id="123456", api_token="test_token")

        # Mock the HTTP response
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = AsyncMock(return_value={"success": True})

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            is_valid, message = await auth.validate_authentication()

            assert isinstance(is_valid, bool)
            assert isinstance(message, str)

    async def test_make_authenticated_request_structure(self):
        """Test authenticated request method structure."""
        auth = QuantConnectAuth(user_id="123456", api_token="test_token")

        # Test that method accepts required parameters
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            response = await auth.make_authenticated_request("test_endpoint", "GET")

            assert response is not None


if __name__ == "__main__":
    pytest.main([__file__])

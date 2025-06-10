"""Basic tests for QuantConnect MCP Server"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.server import mcp
from src.tools.quantbook_tools import get_quantbook_instance

class TestQuantConnectMCPServer:
    """Test class for QuantConnect MCP Server functionality."""
    
    def test_server_initialization(self):
        """Test that the MCP server initializes correctly."""
        assert mcp.name == "QuantConnect MCP Server"
        assert "QuantConnect" in mcp.instructions
    
    def test_quantbook_instance_management(self):
        """Test QuantBook instance management functions."""
        # Test that no instances exist initially
        assert get_quantbook_instance("test") is None
        
        # Test instance management without actual QuantConnect installation
        # This is a structural test only
        assert callable(get_quantbook_instance)
    
    def test_server_has_required_dependencies(self):
        """Test that server declares required dependencies."""
        expected_deps = [
            "pandas", 
            "numpy", 
            "scipy", 
            "scikit-learn", 
            "matplotlib", 
            "seaborn",
            "arch",
            "statsmodels"
        ]
        
        for dep in expected_deps:
            assert dep in mcp.dependencies
    
    def test_server_configuration(self):
        """Test server configuration parameters."""
        assert mcp.host == "127.0.0.1"
        assert mcp.port == 8000
        assert mcp.on_duplicate_tools == "error"

@pytest.mark.asyncio
class TestMCPToolsStructure:
    """Test the structure and availability of MCP tools."""
    
    async def test_tools_can_be_registered(self):
        """Test that tools can be registered without errors."""
        from src.tools import (
            register_quantbook_tools,
            register_data_tools,
            register_analysis_tools,
            register_portfolio_tools,
            register_universe_tools
        )
        
        # Test that all registration functions are callable
        assert callable(register_quantbook_tools)
        assert callable(register_data_tools)
        assert callable(register_analysis_tools)
        assert callable(register_portfolio_tools)
        assert callable(register_universe_tools)
    
    async def test_resources_can_be_registered(self):
        """Test that resources can be registered without errors."""
        from src.resources import register_system_resources
        
        assert callable(register_system_resources)

if __name__ == "__main__":
    pytest.main([__file__])
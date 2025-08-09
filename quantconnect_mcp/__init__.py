"""QuantConnect MCP Server Package"""

import tomlkit
from pathlib import Path

def _get_version():
    """Read version from pyproject.toml"""
    try:
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "r") as f:
            data = tomlkit.load(f)
        return data["project"]["version"]
    except Exception:
        return "unknown"

__version__ = _get_version()
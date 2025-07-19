"""CLI Entry Point"""
import sys
from pathlib import Path

# Add project root to path to allow imports from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import main

if __name__ == "__main__":
    main()
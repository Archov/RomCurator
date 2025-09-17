#!/usr/bin/env python3
"""
ROM Curator Startup Script

This is the main entry point for the ROM Curator application.
Run this script to start the unified interface.
"""

import sys
from pathlib import Path

# Ensure we can import our modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the main application
from rom_curator_main import main

if __name__ == '__main__':
    main()

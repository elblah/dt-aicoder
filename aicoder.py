#!/usr/bin/env python3
"""
AI Coder - An AI-assisted coding tool with MCP support.
This is a single-file version for easy distribution.
"""

# This single-file version imports from the modular package
try:
    from aicoder.app import main
except ImportError:
    # If the package isn't installed, try to run from the current directory
    import sys
    import os

    sys.path.insert(0, os.path.dirname(__file__))
    from aicoder.app import main

if __name__ == "__main__":
    main()

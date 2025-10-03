"""
Tests package initialization.
This file is automatically loaded when unittest runs tests in this directory.
"""

print("🚀 tests/__init__.py LOADED! This should appear before any test runs.")

# Auto-import conftest to trigger network blocking
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import tests.conftest
    print("✅ conftest.py imported successfully from __init__.py")
except Exception as e:
    print(f"❌ Failed to import conftest.py from __init__.py: {e}")
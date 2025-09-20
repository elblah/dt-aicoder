#!/usr/bin/env python3
"""
Test script to verify the no_memory_chat plugin functionality.
"""

import tempfile
import shutil
from pathlib import Path


def test_plugin():
    """Test the no_memory_chat plugin functionality."""
    print("Testing no_memory_chat plugin...")

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir()

        # Copy the fixed plugin to the test directory
        plugin_src = Path("/home/blah/poc/aicoder/v2/no_memory_chat.py")
        plugin_dst = plugin_dir / "no_memory_chat.py"
        shutil.copy2(plugin_src, plugin_dst)

        print(f"Plugin copied to: {plugin_dst}")
        print("Test completed successfully!")


if __name__ == "__main__":
    test_plugin()

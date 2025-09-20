#!/usr/bin/env python3
"""
Test script for the tiered cost display plugin
"""

import os
import sys
import tempfile
import shutil


def test_plugin():
    """Test the tiered cost display plugin functionality."""

    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    cost_file = os.path.join(test_dir, "test_costs.txt")

    try:
        # Set environment variables for testing
        os.environ["TIERED_COST_PLUGIN_ENABLED"] = "true"
        os.environ["TIERED_COST_DATA_FILE"] = cost_file
        os.environ["OPENAI_MODEL"] = "qwen3-coder-plus"
        os.environ["DEBUG"] = "1"

        print("Testing tiered cost display plugin...")
        print(f"Cost data will be saved to: {cost_file}")

        # Import the plugin
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "tiered_cost_display_plugin",
            "./docs/examples/stable/tiered_cost_display/tiered_cost_display_plugin.py",
        )
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)

        print("Plugin loaded successfully!")

        # Simulate some API usage by directly updating the accumulated costs
        plugin_module._accumulated_costs["input_cost"] = 0.05
        plugin_module._accumulated_costs["output_cost"] = 0.03
        plugin_module._accumulated_costs["total_cost"] = 0.08

        # Call the save function directly to test it
        plugin_module.save_cost_data()

        # Check if the file was created and has content
        if os.path.exists(cost_file):
            with open(cost_file, "r") as f:
                content = f.read()
                print("\nContent of cost file:")
                print(content)

                # Verify the content format
                lines = content.strip().split("\n")
                if len(lines) >= 1:
                    # Check if the line contains the expected format
                    if (
                        "Total Costs:" in lines[0]
                        and "[" in lines[0]
                        and "]" in lines[0]
                    ):
                        print("✅ Cost data format is correct!")
                    else:
                        print("❌ Cost data format is incorrect!")
                else:
                    print("❌ Cost file is empty!")
        else:
            print("❌ Cost file was not created!")

        # Test disabling the plugin
        print("\nTesting disabled plugin...")
        del os.environ["TIERED_COST_PLUGIN_ENABLED"]
        os.environ["TIERED_COST_PLUGIN_ENABLED"] = "false"

        # Reload the plugin with disabled setting
        import importlib

        if "tiered_cost_display_plugin" in sys.modules:
            del sys.modules["tiered_cost_display_plugin"]

        spec = importlib.util.spec_from_file_location(
            "tiered_cost_display_plugin",
            "./docs/examples/stable/tiered_cost_display/tiered_cost_display_plugin.py",
        )
        plugin_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plugin_module)

        print("Plugin loaded successfully in disabled mode!")

    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)
        # Clean up environment variables
        for var in [
            "TIERED_COST_PLUGIN_ENABLED",
            "TIERED_COST_DATA_FILE",
            "OPENAI_MODEL",
            "DEBUG",
        ]:
            if var in os.environ:
                del os.environ[var]


if __name__ == "__main__":
    test_plugin()

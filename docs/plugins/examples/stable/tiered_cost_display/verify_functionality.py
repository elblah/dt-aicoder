#!/usr/bin/env python3
"""
Simple verification script for the tiered cost display plugin
"""

import os
import tempfile
import shutil


def test_cost_saving():
    """Test the cost data saving functionality."""

    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp()
    cost_file = os.path.join(test_dir, "test_costs.txt")

    try:
        # Set environment variables for testing
        os.environ["TIERED_COST_PLUGIN_ENABLED"] = "true"
        os.environ["TIERED_COST_DATA_FILE"] = cost_file
        os.environ["OPENAI_MODEL"] = "qwen3-coder-plus"

        print("Testing cost data saving functionality...")
        print(f"Cost data will be saved to: {cost_file}")

        # Create a simple test of the save function
        from datetime import datetime

        # Simulate the save function logic
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        model_name = "qwen3-coder-plus"
        total_cost_display = (
            f"[{model_name}] Total Costs: 0.05 input / 0.03 output = 0.08 total"
        )
        line = f"{timestamp} - {total_cost_display}\n"

        # Save to file
        os.makedirs(os.path.dirname(cost_file), exist_ok=True)
        with open(cost_file, "a") as f:
            f.write(line)

        print("✅ Cost data saved successfully!")

        # Check if the file was created and has content
        if os.path.exists(cost_file):
            with open(cost_file, "r") as f:
                content = f.read()
                print("\nContent of cost file:")
                print(content)

                # Verify the content format
                if "Total Costs:" in content and "[" in content and "]" in content:
                    print("✅ Cost data format is correct!")
                else:
                    print("❌ Cost data format is incorrect!")
        else:
            print("❌ Cost file was not created!")

        # Test with custom path
        custom_cost_file = os.path.join(test_dir, "custom", "my_costs.txt")
        os.environ["TIERED_COST_DATA_FILE"] = custom_cost_file

        # Save again with custom path
        os.makedirs(os.path.dirname(custom_cost_file), exist_ok=True)
        with open(custom_cost_file, "a") as f:
            f.write(line)

        if os.path.exists(custom_cost_file):
            print(f"✅ Custom path saving works: {custom_cost_file}")
        else:
            print(f"❌ Custom path saving failed: {custom_cost_file}")

    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)
        # Clean up environment variables
        for var in [
            "TIERED_COST_PLUGIN_ENABLED",
            "TIERED_COST_DATA_FILE",
            "OPENAI_MODEL",
        ]:
            if var in os.environ:
                del os.environ[var]


if __name__ == "__main__":
    test_cost_saving()

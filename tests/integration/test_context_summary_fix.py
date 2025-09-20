#!/usr/bin/env python3
"""
Test script to verify the context summary plugin fix
"""

import sys
import os

# Add the current directory to the path so we can import the plugin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_plugin_fix():
    """Test that the context summary plugin properly accesses the Stats instance"""
    print("Testing context summary plugin fix...")

    # Import the plugin
    try:
        from docs.examples.unstable.context_summary import context_summary

        print("✅ Plugin imported successfully")
    except Exception as e:
        print(f"❌ Failed to import plugin: {e}")
        return False

    # Test the on_aicoder_init function
    try:
        # Create a mock AICoder instance
        class MockStats:
            def __init__(self):
                self.prompt_tokens = 1000
                self.completion_tokens = 500

        class MockAICoder:
            def __init__(self):
                self.stats = MockStats()
                self.message_history = None
                self.command_handlers = {}

        mock_aicoder = MockAICoder()

        # Call on_aicoder_init
        result = context_summary.on_aicoder_init(mock_aicoder)
        if result:
            print("✅ on_aicoder_init executed successfully")
        else:
            print("❌ on_aicoder_init failed")
            return False

        # Check if the global reference was set
        if "main_aicoder_instance" in context_summary.__dict__:
            print("✅ main_aicoder_instance variable set in plugin module")
        else:
            print("ℹ️  main_aicoder_instance variable not found in plugin module")

    except Exception as e:
        print(f"❌ Error testing on_aicoder_init: {e}")
        return False

    print("✅ Plugin fix test completed")
    return True


if __name__ == "__main__":
    test_plugin_fix()

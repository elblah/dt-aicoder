"""
Test script for the context summary plugin.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from aicoder.message_history import MessageHistory

# Load the plugin
import importlib.util

plugin_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "docs",
    "plugins",
    "examples",
    "unstable",
    "context_summary",
    "context_summary.py",
)
spec = importlib.util.spec_from_file_location("plugin", plugin_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

# Test that the plugin has monkey patched the MessageHistory class

# Check if the method has been replaced
if (
    hasattr(MessageHistory.add_assistant_message, "__name__")
    and MessageHistory.add_assistant_message.__name__
    == "_summarized_add_assistant_message"
):
    print("✅ Plugin successfully monkey patched MessageHistory.add_assistant_message")
else:
    print("❌ Plugin failed to monkey patch MessageHistory.add_assistant_message")


# Test the on_aicoder_init hook
# We need to create a mock AICoder instance with command_handlers
class MockAICoder:
    def __init__(self):
        self.command_handlers = {}


# Create a mock instance
mock_instance = MockAICoder()

# Call the on_aicoder_init hook
try:
    module.on_aicoder_init(mock_instance)
    if "/summarize" in mock_instance.command_handlers:
        print(
            "✅ Plugin successfully registered /summarize command via on_aicoder_init hook"
        )
    else:
        print("❌ Plugin failed to register /summarize command")
        print("Available commands:", list(mock_instance.command_handlers.keys()))
except Exception as e:
    print(f"Error calling on_aicoder_init: {e}")

print("Test completed.")

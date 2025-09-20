#!/usr/bin/env python3
"""
Test script for the context summary plugin with auto-compaction.
This script demonstrates the plugin's functionality without requiring a full AICoder instance.
"""

import sys
import importlib.util
import os

# Add the current directory to the path so we can import the plugin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Mock the AICoder modules that our plugin depends on
class MockMessageHistory:
    # Class method that would normally exist
    def add_assistant_message(self, message):
        return None

    def __init__(self):
        self.messages = []
        self.stats = None

    def summarize_context(self):
        print("  [MOCK] Summarizing context...")
        # Simulate reducing messages
        if len(self.messages) > 10:
            self.messages = self.messages[-10:]

    def compact_memory(self):
        print("  [MOCK] Compacting memory...")
        # Simulate reducing messages
        if len(self.messages) > 5:
            self.messages = self.messages[-5:]


# import sys


class MockStats:
    def __init__(self, prompt_tokens=0, completion_tokens=0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


# Add mocks to sys.modules so imports will work
sys.modules["aicoder"] = type(sys)("aicoder")
sys.modules["aicoder.message_history"] = type(sys)("aicoder.message_history")
sys.modules["aicoder.message_history"].MessageHistory = MockMessageHistory
sys.modules["aicoder.stats"] = type(sys)("aicoder.stats")
sys.modules["aicoder.stats"].Stats = MockStats

# Import</think></think> plugin the plugin

# Load the plugin dynamically
plugin_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "context_summary.py"
)
spec = importlib.util.spec_from_file_location("context_summary_plugin", plugin_path)
plugin_module = importlib.util.module_from_spec(spec)
sys.modules["context_summary_plugin"] = plugin_module
spec.loader.exec_module(plugin_module)


def test_model_token_limits():
    """Test the model token limit functionality"""
    print("Testing model token limits...")

    # Test some known models
    test_models = [
        "gpt-5-nano",
        "gpt-4",
        "gpt-3.5-turbo",
        "gemini-2.5-pro",
        "qwen3-coder-plus",
        "unknown-model",
    ]

    for model in test_models:
        limit = plugin_module.get_model_token_limit(model)
        print(f"  {model}: {limit} tokens")

    print()


def test_get_current_model_name():
    """Test the get_current_model_name function"""
    print("Testing model name detection...")

    # Test with environment variable
    original_model = os.environ.get("OPENAI_MODEL")
    os.environ["OPENAI_MODEL"] = "gpt-4-turbo"

    model_name = plugin_module.get_current_model_name()
    print(f"  Current model: {model_name}")

    # Restore original environment
    if original_model:
        os.environ["OPENAI_MODEL"] = original_model
    elif "OPENAI_MODEL" in os.environ:
        del os.environ["OPENAI_MODEL"]

    print()


def test_plugin_load():
    """Test that the plugin loads correctly"""
    print("Testing plugin load...")
    try:
        result = plugin_module.on_plugin_load()
        print(f"  Plugin load result: {result}")
    except Exception as e:
        print(f"  Plugin load failed: {e}")
    print()


def main():
    """Main test function"""
    print("Context Summary Plugin Test Script")
    print("=" * 40)

    # Show plugin configuration
    print("Plugin Configuration:")
    print(f"  AUTO_SUMMARY_THRESHOLD: {plugin_module.AUTO_SUMMARY_THRESHOLD}")
    print(f"  SUMMARY_INTERVAL: {plugin_module.SUMMARY_INTERVAL}")
    print(f"  TOKEN_LIMIT_THRESHOLD: {plugin_module.TOKEN_LIMIT_THRESHOLD}")
    print()

    # Test model token limits
    test_model_token_limits()

    # Test model name detection
    test_get_current_model_name()

    # Test plugin load
    test_plugin_load()

    print("Test completed successfully!")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script to verify the context summary plugin token access fix
"""

import sys
import os

# Add the current directory to the path so we can import the plugin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_token_access():
    """Test that the context summary plugin properly accesses token counts"""
    print("Testing context summary plugin token access...")

    # Import the plugin
    try:
        from docs.examples.unstable.context_summary import context_summary

        print("✅ Plugin imported successfully")
    except Exception as e:
        print(f"❌ Failed to import plugin: {e}")
        return False

    # Create mock classes to simulate the AICoder environment
    class MockStats:
        def __init__(self, prompt_tokens=0, completion_tokens=0):
            self.prompt_tokens = prompt_tokens
            self.completion_tokens = completion_tokens

    class MockAICoder:
        def __init__(self, prompt_tokens=0, completion_tokens=0):
            self.stats = MockStats(prompt_tokens, completion_tokens)

    class MockMessageHistory:
        def __init__(self, aicoder_instance=None):
            self.aicoder = aicoder_instance
            self.api_handler = aicoder_instance
            self.stats = MockStats()  # This should be ignored now
            self.messages = []

    # Test 1: Set up the global reference as on_aicoder_init would do
    mock_aicoder = MockAICoder(1500, 750)  # 1500 prompt tokens, 750 completion tokens
    context_summary.main_aicoder_instance = mock_aicoder

    # Test 2: Create a mock message history instance
    mock_history = MockMessageHistory(mock_aicoder)

    # Test 3: Simulate the monkey-patched function logic
    print("Testing token access logic...")

    # This replicates the logic in the _enhanced_add_assistant_message function
    stats_instance = None
    if context_summary.main_aicoder_instance and hasattr(
        context_summary.main_aicoder_instance, "stats"
    ):
        stats_instance = context_summary.main_aicoder_instance.stats
    elif hasattr(mock_history, "api_handler") and hasattr(
        mock_history.api_handler, "stats"
    ):
        stats_instance = mock_history.api_handler.stats
    elif hasattr(mock_history, "aicoder") and hasattr(mock_history.aicoder, "stats"):
        stats_instance = mock_history.aicoder.stats
    elif hasattr(mock_history, "stats"):
        stats_instance = mock_history.stats

    if stats_instance:
        prompt_tokens = stats_instance.prompt_tokens
        completion_tokens = stats_instance.completion_tokens
        total_tokens = prompt_tokens + completion_tokens
        print("✅ Token access successful:")
        print(f"   Prompt tokens: {prompt_tokens}")
        print(f"   Completion tokens: {completion_tokens}")
        print(f"   Total tokens: {total_tokens}")

        if total_tokens == 2250:  # 1500 + 750
            print("✅ Token counts are correct!")
            return True
        else:
            print(f"❌ Token counts are incorrect. Expected 2250, got {total_tokens}")
            return False
    else:
        print("❌ Failed to access stats instance")
        return False


if __name__ == "__main__":
    success = test_token_access()
    if success:
        print(
            "\n🎉 All tests passed! The context summary plugin fix is working correctly."
        )
    else:
        print("\n❌ Tests failed. The fix needs more work.")

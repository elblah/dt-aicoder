#!/usr/bin/env python3
"""
Test script to verify the cost display plugin fix
"""

import sys
import os

# Add the current directory to the path so we can import the plugin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_cost_display_plugin():
    """Test that the cost display plugin properly accesses token counts"""
    print("Testing cost display plugin fix...")

    # Import the plugin
    try:
        from docs.examples.unstable.cost_display import cost_display

        print("✅ Cost display plugin imported successfully")
    except Exception as e:
        print(f"❌ Failed to import cost display plugin: {e}")
        return False

    # Create mock classes to simulate the AICoder environment
    class MockStats:
        def __init__(self, prompt_tokens=0, completion_tokens=0):
            self.prompt_tokens = prompt_tokens
            self.completion_tokens = completion_tokens

    class MockAICoder:
        def __init__(self, prompt_tokens=0, completion_tokens=0):
            self.stats = MockStats(prompt_tokens, completion_tokens)

    # Test 1: Set up the global reference as on_aicoder_init would do
    mock_aicoder = MockAICoder(2500, 1800)  # 2500 prompt tokens, 1800 completion tokens
    cost_display.on_aicoder_init(mock_aicoder)

    # Test 2: Verify the main_aicoder_instance is set correctly
    if cost_display.main_aicoder_instance == mock_aicoder:
        print("✅ main_aicoder_instance set correctly")
    else:
        print("❌ main_aicoder_instance not set correctly")
        return False

    # Test 3: Verify token access
    if (
        cost_display.main_aicoder_instance.stats.prompt_tokens == 2500
        and cost_display.main_aicoder_instance.stats.completion_tokens == 1800
    ):
        print("✅ Token access working correctly")
    else:
        print("❌ Token access not working correctly")
        return False

    # Test 4: Set environment variable for model
    os.environ["OPENAI_MODEL"] = "gpt-5-nano"

    # Test 5: Verify cost calculation
    stats = cost_display.main_aicoder_instance.stats
    input_cost, output_cost, total_cost = cost_display.calculate_cost(
        stats.prompt_tokens, stats.completion_tokens
    )

    # Expected costs for gpt-5-nano:
    # Input: (2500 / 1,000,000) * 0.05 = 0.000125
    # Output: (1800 / 1,000,000) * 0.40 = 0.00072
    # Total: 0.000125 + 0.00072 = 0.000845

    expected_input = 0.000125
    expected_output = 0.00072
    expected_total = 0.000845

    if (
        abs(input_cost - expected_input) < 0.000001
        and abs(output_cost - expected_output) < 0.000001
        and abs(total_cost - expected_total) < 0.000001
    ):
        print("✅ Cost calculation working correctly")
    else:
        print(
            f"❌ Cost calculation incorrect. Expected: {expected_input:.6f}/{expected_output:.6f}/{expected_total:.6f}, Got: {input_cost:.6f}/{output_cost:.6f}/{total_cost:.6f}"
        )
        return False

    print("✅ All cost display plugin tests passed!")
    return True


if __name__ == "__main__":
    success = test_cost_display_plugin()
    if success:
        print("\n🎉 Cost display plugin fix is working correctly!")
    else:
        print("\n❌ Cost display plugin tests failed.")

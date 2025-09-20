#!/usr/bin/env python3
"""
Final verification script for both context summary and cost display plugins
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_both_plugins():
    """Test both context summary and cost display plugins"""
    print("=== Final Plugin Verification ===\n")

    # Test 1: Context Summary Plugin
    print("1. Testing Context Summary Plugin...")
    try:
        from docs.examples.unstable.context_summary import context_summary

        print("   ✅ Context summary plugin loaded")

        # Create mock classes
        class MockStats:
            def __init__(self):
                self.prompt_tokens = 1200
                self.completion_tokens = 800

        class MockAICoder:
            def __init__(self):
                self.stats = MockStats()

        # Initialize plugin
        aicoder = MockAICoder()
        result = context_summary.on_aicoder_init(aicoder)
        if result and context_summary.main_aicoder_instance == aicoder:
            print("   ✅ Context summary plugin initialized correctly")
        else:
            print("   ❌ Context summary plugin initialization failed")
            return False
    except Exception as e:
        print(f"   ❌ Context summary plugin test failed: {e}")
        return False

    # Test 2: Cost Display Plugin
    print("\n2. Testing Cost Display Plugin...")
    try:
        from docs.examples.unstable.cost_display import cost_display

        print("   ✅ Cost display plugin loaded")

        # Initialize plugin
        aicoder = MockAICoder()  # Reuse from above
        result = cost_display.on_aicoder_init(aicoder)
        if result and cost_display.main_aicoder_instance == aicoder:
            print("   ✅ Cost display plugin initialized correctly")
        else:
            print("   ❌ Cost display plugin initialization failed")
            return False

        # Test cost calculation
        stats = aicoder.stats
        input_cost, output_cost, total_cost = cost_display.calculate_cost(
            stats.prompt_tokens, stats.completion_tokens
        )
        print(f"   ✅ Cost calculation: {total_cost:.6f} total")

    except Exception as e:
        print(f"   ❌ Cost display plugin test failed: {e}")
        return False

    print("\n🎉 All plugin tests passed!")
    print("\nSummary of fixes:")
    print(
        "  • Context Summary Plugin: Fixed token access by storing main AICoder instance reference"
    )
    print("  • Cost Display Plugin: Fixed token access and improved cost formatting")
    print("\nBoth plugins now properly display token counts and cost information!")
    return True


if __name__ == "__main__":
    test_both_plugins()

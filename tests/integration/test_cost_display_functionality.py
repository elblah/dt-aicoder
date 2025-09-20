#!/usr/bin/env python3
"""
Test script to verify the cost display functionality works in practice
"""

import sys
import os
import builtins

# Add the current directory to the path so we can import the plugin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_cost_display_functionality():
    """Test that the cost display actually shows cost information"""
    print("Testing cost display functionality...")

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

    # Set up the global reference as on_aicoder_init would do
    mock_aicoder = MockAICoder(3000, 1500)  # 3000 prompt tokens, 1500 completion tokens
    cost_display.on_aicoder_init(mock_aicoder)

    # Set environment variable for model
    os.environ["OPENAI_MODEL"] = "gpt-5-nano"

    # Capture print output
    captured_output = []
    original_print = builtins.print

    def mock_print(*args, **kwargs):
        captured_output.append(" ".join(str(arg) for arg in args))
        original_print(*args, **kwargs)

    builtins.print = mock_print

    # Test</think> input function with a prompt containing ">"
    try:
        # This should trigger cost display
        # This should trigger the cost display
        # result = cost_display.cost_displaying_input("Enter your message > ")

        # Check if cost information was displayed
        cost_display_found = any(
            "Cost:" in line and "input" in line and "output" in line
            for line in captured_output
        )

        if cost_display_found:
            print("✅ Cost display functionality working correctly")
            # Print the actual cost display line
            for line in captured_output:
                if "Cost:" in line and "input" in line and "output" in line:
                    print(f"   Displayed: {line.strip()}")
            success = True
        else:
            print(
                "❌ Cost display functionality not working - no cost information shown"
            )
            print("Captured output:")
            for line in captured_output:
                print(f"   {line}")
            success = False

    except Exception as e:
        print(f"❌ Error testing cost display functionality: {e}")
        success = False
    finally:
        # Restore original print function
        builtins.print = original_print

    return success


if __name__ == "__main__":
    success = test_cost_display_functionality()
    if success:
        print("\n🎉 Cost display functionality is working correctly!")
    else:
        print("\n❌ Cost display functionality tests failed.")

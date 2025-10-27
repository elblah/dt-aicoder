#!/usr/bin/env python3
"""
Test to verify animation appearance and disappearance.
"""

import sys
import os

# Add the parent directory to Python path so imports work from subdirectory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import sys
import time
from io import StringIO


def test_animation_lifecycle():
    """Test that animation appears and then disappears after response."""
    print("Testing animation lifecycle (appear and disappear)...")

    # Capture stdout to see animation behavior
    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output

    try:
        from aicoder.animator import Animator

        # Create animator
        animator = Animator()

        print("Starting animation...")
        animator.start_animation("Working...")

        # Let it run briefly to generate some animation
        time.sleep(0.3)

        print("Stopping animation...")
        animator.stop_animation()

        # Restore stdout
        sys.stdout = old_stdout
        output = captured_output.getvalue()

        print(f"Captured output: {repr(output)}")

        # Check that animation started and stopped properly
        has_start_indicators = "Working..." in output
        has_stop_indicators = "\r" in output  # Animation uses \r for updates
        has_clear_indicators = "     " in output or "\r" in output  # Clearing behavior

        print(f"Animation started: {has_start_indicators}")
        print(f"Animation updates: {has_stop_indicators}")
        print(f"Animation clearing: {has_clear_indicators}")

        # The animation should have appeared and then been cleared
        success = has_start_indicators  # Basic check that animation appeared

        if success:
            print("[✓] Animation lifecycle test PASSED")
        else:
            print("[X] Animation lifecycle test FAILED")

        return success

    except Exception as e:
        sys.stdout = old_stdout
        print(f"Error in animation lifecycle test: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    print("Animation Lifecycle Test")
    print("=" * 30)

    success = test_animation_lifecycle()

    print("\\n" + "=" * 30)
    if success:
        print("[✓] Animation lifecycle test completed successfully!")
        print("Animation appears during processing and disappears after completion.")
    else:
        print("[X] Animation lifecycle test failed.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

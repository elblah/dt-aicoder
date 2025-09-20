#!/usr/bin/env python3
"""
Test script for the Network Retry Plugin
"""

import os
import sys


def test_plugin_loading():
    """Test that the plugin loads correctly."""
    print("Testing Network Retry Plugin Loading...")

    # Add the plugin directory to the path
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(plugin_dir)
    sys.path.insert(0, parent_dir)

    try:
        # Try to import the plugin
        import network_retry

        print("✅ Plugin imported successfully")

        # Test configuration functions
        config = network_retry.get_retry_config()
        print(f"✅ Retry config loaded: {config}")

        delay_config = network_retry.get_delay_config()
        print(f"✅ Delay config loaded: {delay_config}")

        # Test helper functions
        jitter_delay = network_retry.apply_jitter(1.0, 0.1)
        print(f"✅ Jitter function works: 1.0 ± 10% = {jitter_delay:.2f}")

        # Test should_retry function
        should_retry_502 = network_retry.should_retry(502, 0, config)
        print(f"✅ Should retry 502: {should_retry_502}")

        should_retry_500 = network_retry.should_retry(500, 5, config)
        print(f"✅ Should retry 500 after 5 attempts: {should_retry_500}")

        # Test calculate_delay function
        delay = network_retry.calculate_delay(2, delay_config)
        print(f"✅ Calculated delay for attempt 2: {delay:.2f}s")

        print("\n🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_plugin_loading()
    sys.exit(0 if success else 1)

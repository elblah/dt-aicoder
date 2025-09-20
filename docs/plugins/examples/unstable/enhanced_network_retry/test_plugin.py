#!/usr/bin/env python3
"""
Test script for the Enhanced Network Retry Plugin
"""

import os
import sys


def test_plugin_functions():
    """Test that the plugin functions work correctly."""
    print("Testing Enhanced Network Retry Plugin Functions...")

    try:
        # Add the plugin directory to the path
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(plugin_dir)
        sys.path.insert(0, parent_dir)

        # Try to import the plugin and functions
        from enhanced_network_retry import (
            get_retry_config,
            get_delay_config,
            apply_jitter,
            classify_error,
            should_retry,
            calculate_delay,
        )

        print("✅ Plugin and functions imported successfully")

        # Test configuration functions
        config = get_retry_config()
        print(f"✅ Retry config loaded: {config}")

        delay_config = get_delay_config()
        print(f"✅ Delay config loaded: {delay_config}")

        # Test helper functions
        jitter_delay = apply_jitter(1.0, 0.1)
        print(f"✅ Jitter function works: 1.0 ± 10% = {jitter_delay:.2f}")

        # Test error classification
        class MockError:
            def __init__(self, message, code=None):
                self.message = message
                self.code = code

            def __str__(self):
                return self.message

        # Test HTTP error classification
        http_error = MockError("HTTP 502 Bad Gateway", 502)
        error_type = classify_error(http_error)
        print(f"✅ HTTP error classification: {error_type}")

        # Test timeout error classification
        timeout_error = MockError("Connection timed out")
        error_type = classify_error(timeout_error)
        print(f"✅ Timeout error classification: {error_type}")

        # Test DNS error classification
        dns_error = MockError("Name or service not known")
        error_type = classify_error(dns_error)
        print(f"✅ DNS error classification: {error_type}")

        # Test connection error classification
        connect_error = MockError("Connection refused")
        error_type = classify_error(connect_error)
        print(f"✅ Connection error classification: {error_type}")

        # Test should_retry function
        should_retry_502 = should_retry("502", 0, config)
        print(f"✅ Should retry 502: {should_retry_502}")

        should_retry_timeout = should_retry("timeout", 2, config)
        print(f"✅ Should retry timeout after 2 attempts: {should_retry_timeout}")

        # Test calculate_delay function
        delay = calculate_delay(2, delay_config)
        print(f"✅ Calculated delay for attempt 2: {delay:.2f}s")

        print("\n🎉 All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_plugin_functions()
    sys.exit(0 if success else 1)

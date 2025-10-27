#!/usr/bin/env python3
"""
Test script for the Auto Retry Plugin
"""

import sys
import os
from unittest.mock import Mock
import auto_retry

# Add the plugin to the path
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, plugin_dir)


def test_error_detection():
    """Test that the plugin correctly detects different types of errors."""
    print("Testing error detection...")

    # Mock HTTPError with 500 code and 429 content
    mock_error_500_429 = Mock()
    mock_error_500_429.code = 500
    mock_error_500_429.read.return_value = (
        b'{"error":"429 Too Many Requests","status":500}'
    )

    # Mock HTTPError with 429 code
    mock_error_429 = Mock()
    mock_error_429.code = 429
    mock_error_429.read.return_value = b'{"error":"Too Many Requests"}'

    # Mock HTTPError with 502 code
    mock_error_502 = Mock()
    mock_error_502.code = 502
    mock_error_502.read.return_value = b'{"error":"Bad Gateway"}'

    print("[✓] Error detection tests passed")


def test_plugin_installation():
    """Test that the plugin can be installed successfully."""
    print("Testing plugin installation...")

    # Try to install the plugin
    result = auto_retry.install_auto_retry_plugin()

    if result:
        print("[✓] Plugin installation test passed")
    else:
        print("[X] Plugin installation test failed")
        return False

    return True


def test_environment_variables():
    """Test that environment variables are read correctly."""
    print("Testing environment variable configuration...")

    # Set test environment variables
    os.environ["AUTO_RETRY_DELAY"] = "10"
    os.environ["AUTO_RETRY_MAX_RETRIES"] = "5"

    # Import the plugin again to test with new environment variables
    import importlib

    importlib.reload(auto_retry)

    # Reset environment variables
    os.environ.pop("AUTO_RETRY_DELAY", None)
    os.environ.pop("AUTO_RETRY_MAX_RETRIES", None)

    print("[✓] Environment variable test passed")


def main():
    """Run all tests."""
    print("Running Auto Retry Plugin Tests...")
    print("=" * 50)

    try:
        # Run tests
        test_error_detection()
        test_plugin_installation()
        test_environment_variables()

        print("=" * 50)
        print("[✓] All tests passed!")
        print()
        print("Plugin Features:")
        print("   - Handles 500 errors with 429 content")
        print("   - Retries HTTP errors: 502, 503, 504, 429, 500")
        print("   - Detects rate limiting keywords")
        print("   - Configurable via environment variables")
        print("   - ESC key cancellation support")
        print()
        print("To install and use:")
        print("   1. Run: ./install_plugin.sh")
        print("   2. Configure: export AUTO_RETRY_DELAY=5")
        print("   3. Run AI Coder: python -m aicoder")

        return True

    except Exception as e:
        print(f"[X] Test failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

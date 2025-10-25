#!/usr/bin/env python3
"""
Test for ConnectionDroppedException retry behavior.
This test verifies that ConnectionDroppedException is properly handled in the retry logic.
"""

import os
import sys
from unittest.mock import patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.retry_utils import (
    ConnectionDroppedException,
    handle_request_error,
    APIRetryHandler,
)


def test_connection_dropped_retry_with_patterns():
    """Test that ConnectionDroppedException is handled correctly with retry patterns."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get("AICODER_TEST_MODE", "")
    os.environ["AICODER_TEST_MODE"] = "1"

    # Don't disable retry patterns - we want to test them
    original_disable_patterns = os.environ.get("DISABLE_RETRY_PATTERNS", "")
    if "DISABLE_RETRY_PATTERNS" in os.environ:
        del os.environ["DISABLE_RETRY_PATTERNS"]

    # Create a ConnectionDroppedException
    exception = ConnectionDroppedException(
        "Connection dropped by server (EOF detected)"
    )

    # Mock the retry handler's _check_retry_patterns method to return "yes" for EOF
    with patch.object(APIRetryHandler, "_check_retry_patterns") as mock_check:
        mock_check.return_value = ("yes", "eof")

        # Test handle_request_error with ConnectionDroppedException
        try:
            handle_request_error(exception)
            assert False, "Should have raised ShouldRetryException"
        except Exception as e:
            # Should have raised ShouldRetryException due to "eof" matching retry_yes.conf
            assert "ShouldRetryException" in str(type(e))
            print("✓ ConnectionDroppedException correctly triggers retry")

    # Restore original environment
    os.environ["AICODER_TEST_MODE"] = original_test_mode if original_test_mode else "1"
    if original_disable_patterns:
        os.environ["DISABLE_RETRY_PATTERNS"] = original_disable_patterns


def test_connection_dropped_retry_without_patterns():
    """Test that ConnectionDroppedException is handled correctly without retry patterns."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get("AICODER_TEST_MODE", "")
    os.environ["AICODER_TEST_MODE"] = "1"

    # Disable retry patterns to test static behavior
    os.environ["DISABLE_RETRY_PATTERNS"] = "1"

    # Create a ConnectionDroppedException
    exception = ConnectionDroppedException(
        "Connection dropped by server (EOF detected)"
    )

    # Test handle_request_error with ConnectionDroppedException
    result = handle_request_error(exception)

    # Without retry patterns, it should return False (no retry, no exception)
    assert result is False
    print("✓ ConnectionDroppedException correctly returns False without retry patterns")

    # Restore original environment
    os.environ["AICODER_TEST_MODE"] = original_test_mode if original_test_mode else "1"
    if "DISABLE_RETRY_PATTERNS" in os.environ:
        del os.environ["DISABLE_RETRY_PATTERNS"]


if __name__ == "__main__":
    test_connection_dropped_retry_with_patterns()
    test_connection_dropped_retry_without_patterns()
    print("\n✓ All ConnectionDroppedException tests passed!")

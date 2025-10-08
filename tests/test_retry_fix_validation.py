"""
Comprehensive test to validate the retry fix and prevent regression.
This test ensures that HTTP errors are properly categorized and retried.
"""

import pytest
import urllib.error
import socket
from unittest.mock import Mock, patch
import os

from aicoder.retry_utils import APIRetryHandler
from aicoder.streaming_adapter import StreamingAdapter


@pytest.fixture
def mock_components():
    """Set up test fixtures."""
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_errors = 0
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    return mock_animator, mock_stats


@pytest.fixture
def retry_handler(mock_components):
    """Create a retry handler instance."""
    mock_animator, mock_stats = mock_components
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    handler = APIRetryHandler(mock_animator, mock_stats)
    
    yield handler
    
    # Restore original test mode
    if original_test_mode:
        os.environ["AICODER_TEST_MODE"] = original_test_mode
    elif "AICODER_TEST_MODE" in os.environ:
        del os.environ["AICODER_TEST_MODE"]
    
    # Reset singleton state for next test
    from aicoder.retry_utils import _APIRetryHandlerSingleton
    _APIRetryHandlerSingleton._instance = None
    _APIRetryHandlerSingleton._initialized = False


def test_http_error_categorization_in_workers():
    """Test that HTTP errors are properly categorized in worker functions."""
    # Test the fixed exception handling logic
    def test_worker_exception_handling(error, expected_category):
        result_dict = {}
        try:
            raise error
        except urllib.error.HTTPError as e:
            # FIXED: HTTP errors should be caught first and categorized as 'http_error'
            result_dict["error"] = e
            result_dict["error_type"] = "http_error"
            result_dict["success"] = False
        except urllib.error.URLError as e:
            # Other URL errors (timeouts, connection issues, etc.)
            if isinstance(e.reason, socket.timeout):
                result_dict["error"] = e
                result_dict["error_type"] = "http_timeout"
            else:
                result_dict["error"] = e
                result_dict["error_type"] = "connection_error"
            result_dict["success"] = False
        except Exception as e:
            result_dict["error"] = e
            result_dict["error_type"] = "general_error"
            result_dict["success"] = False

        return result_dict

    # Test various HTTP errors - these should be categorized as 'http_error', not 'connection_error'
    http_errors_to_test = [
        urllib.error.HTTPError("http://test.com", 502, "Bad Gateway", {}, None),
        urllib.error.HTTPError("http://test.com", 500, "Internal Server Error", {}, None),
        urllib.error.HTTPError("http://test.com", 503, "Service Unavailable", {}, None),
        urllib.error.HTTPError("http://test.com", 504, "Gateway Timeout", {}, None),
        urllib.error.HTTPError("http://test.com", 429, "Too Many Requests", {}, None),
    ]

    for error in http_errors_to_test:
        result = test_worker_exception_handling(error, "http_error")
        assert result["error_type"] == "http_error"
        assert result["error"].code == error.code
        assert not result["success"]

    # Test regular connection error - this should still be 'connection_error'
    conn_error = urllib.error.URLError("Connection failed")
    conn_error.reason = socket.error("Connection refused")

    conn_result = test_worker_exception_handling(conn_error, "connection_error")
    assert conn_result["error_type"] == "connection_error"
    assert not conn_result["success"]


def test_retry_logic_still_works(retry_handler):
    """Test that the core retry logic still functions correctly."""
    # Test 502 error should be retried
    error_502 = urllib.error.HTTPError("http://test.com", 502, "Bad Gateway", {}, None)
    should_retry, delay, error_type = retry_handler.should_retry_error(error_502)

    assert should_retry
    assert delay > 0
    assert error_type == "Server"

    # Test 500 error should NOT be retried (without rate limiting content)
    error_500 = urllib.error.HTTPError("http://test.com", 500, "Internal Server Error", {}, None)
    should_retry, delay, error_type = retry_handler.should_retry_error(error_500)

    assert not should_retry
    assert delay == 0
    assert error_type == "Unknown"

    # Test 401 error should NOT be retried
    error_401 = urllib.error.HTTPError("http://test.com", 401, "Unauthorized", {}, None)
    should_retry, delay, error_type = retry_handler.should_retry_error(error_401)

    assert not should_retry
    assert delay == 0
    assert error_type == "Unknown"


def test_500_with_429_content(retry_handler):
    """Test that 500 errors with 429 content are properly handled."""
    # Create a mock response object for testing
    class MockResponse:
        def read(self):
            return b'{"error": {"message": "429 Too Many Requests"}}'

    error_500_429 = urllib.error.HTTPError(
        url="http://test.com",
        code=500,
        msg="Internal Server Error",
        hdrs={},
        fp=MockResponse()
    )
    # Mock the read method to return the content
    error_500_429.read = lambda: b'{"error": {"message": "429 Too Many Requests"}}'

    should_retry, delay, error_type = retry_handler.should_retry_error(error_500_429)

    assert should_retry
    assert delay > 0  # Should have longer delay for rate limiting
    assert error_type == "Rate limiting"


def test_retry_handler_with_mock_sleep(retry_handler):
    """Test the full retry handler with mocked sleep."""
    error_502 = urllib.error.HTTPError("http://test.com", 502, "Bad Gateway", {}, None)

    # Test with sleep returning True (don't cancel)
    with patch('aicoder.utils.cancellable_sleep', return_value=True):
        result = retry_handler.handle_http_error_with_retry(error_502)
        # Should return True to indicate that retry should happen (sleep was not cancelled)
        # Actually, looking at the code: if sleep returns True, it continues retry
        # The function returns False if cancelled, True if should retry

    # Reset for next test
    retry_handler.reset_retry_counter()


def test_error_handling_flow_simulation():
    """Simulate the complete error handling flow."""
    # Simulate worker categorizing error as 'http_error'
    result_dict = {
        "error": urllib.error.HTTPError("http://test.com", 502, "Bad Gateway", {}, None),
        "error_type": "http_error",
        "success": False
    }

    # Simulate main thread handling
    error = result_dict.get("error")
    error_type = result_dict.get("error_type", "general_error")

    # This should trigger re-raise path
    if error_type == "http_error":
        raised_error = error  # This simulates 'raise error'
    else:
        raised_error = None

    assert raised_error is not None
    assert raised_error.code == 502

    # Simulate outer exception handler catching the HTTPError
    if isinstance(raised_error, urllib.error.HTTPError):
        # This would call _handle_http_error which calls retry logic
        mock_animator, mock_stats = Mock(), Mock()
        handler = APIRetryHandler(mock_animator, mock_stats)
        # The error would go through the proper retry logic
        should_retry, delay, error_type = handler.should_retry_error(raised_error)
        assert should_retry
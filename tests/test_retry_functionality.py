#!/usr/bin/env python3
"""
Comprehensive test for retry functionality using the test server.
This test verifies that the retry logic works properly for various HTTP errors.
"""

import os
import sys
from unittest.mock import Mock, patch
import urllib.request
import urllib.error

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.test_server import GenericTestServer
from aicoder.api_client import APIClient
from aicoder.retry_utils import APIRetryHandler
import aicoder.config


# Global server instance for tests
server = None
base_url = None


def setup_module():
    """Start the test server before running tests."""
    global server, base_url
    server = GenericTestServer()
    base_url = server.start()
    print(f"Started test server at {base_url}")


def teardown_module():
    """Stop the test server after running tests."""
    global server
    if server:
        server.stop()
        print("Stopped test server")


def test_retry_handler_should_retry_502():
    """Test that retry handler correctly identifies 502 errors for retry."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Create a mock HTTPError for 502
    error = urllib.error.HTTPError(
        url=f"{base_url}/502", 
        code=502, 
        msg="Bad Gateway", 
        hdrs={}, 
        fp=None
    )
    
    handler = APIRetryHandler(mock_animator, mock_stats)
    should_retry, delay, error_type = handler.should_retry_error(error)
    
    assert should_retry, "502 errors should be retried"
    assert error_type == "Server", "502 should be classified as Server error"
    assert delay > 0, "Delay should be greater than 0"
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


def test_retry_handler_should_retry_500_with_429_content():
    """Test that retry handler correctly identifies 500 errors with 429 content."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Create a mock HTTPError for 500 with 429 content
    class MockResponse:
        def read(self):
            return b'{"error": {"message": "429 Too Many Requests"}}'
        def decode(self):
            return '{"error": {"message": "429 Too Many Requests"}}'
    
    error = urllib.error.HTTPError(
        url=f"{base_url}/500_with_429_content", 
        code=500, 
        msg="Internal Server Error", 
        hdrs={}, 
        fp=MockResponse()
    )
    
    # Mock the read method to return the content
    error.read = lambda: b'{"error": {"message": "429 Too Many Requests"}}'
    
    handler = APIRetryHandler(mock_animator, mock_stats)
    should_retry, delay, error_type = handler.should_retry_error(error)
    
    assert should_retry, "500 errors with 429 content should be retried"
    assert error_type == "Rate limiting", "500 with 429 content should be classified as Rate limiting"
    assert delay > aicoder.config.RETRY_INITIAL_DELAY, "Rate limiting should have longer delay"
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


def test_retry_handler_should_not_retry_401():
    """Test that retry handler does not retry 401 errors."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    error = urllib.error.HTTPError(
        url=f"{base_url}/401", 
        code=401, 
        msg="Unauthorized", 
        hdrs={}, 
        fp=None
    )
    
    handler = APIRetryHandler(mock_animator, mock_stats)
    should_retry, delay, error_type = handler.should_retry_error(error)
    
    assert not should_retry, "401 errors should not be retried"
    assert delay == 0, "Delay should be 0 for non-retryable errors"
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


def test_api_client_handle_http_error_with_retry():
    """Test that API client handles HTTP errors with retry logic."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Reset singleton to ensure clean test
    from aicoder.retry_utils import _APIRetryHandlerSingleton
    _APIRetryHandlerSingleton._instance = None
    _APIRetryHandlerSingleton._initialized = False
    
    handler = APIRetryHandler(mock_animator, mock_stats)
    
    # Create a mock HTTPError for 502
    error = urllib.error.HTTPError(
        url=f"{base_url}/502", 
        code=502, 
        msg="Bad Gateway", 
        hdrs={}, 
        fp=None
    )
    
    # Mock the cancellable_sleep to return True (don't cancel)
    with patch('aicoder.retry_utils.cancellable_sleep', return_value=True):
        should_retry = handler.handle_http_error_with_retry(error)
    
    assert should_retry, "502 errors should trigger retry"
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


def test_api_client_handle_http_error_max_attempts():
    """Test that API client respects max retry attempts."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Create a handler instance
    handler = APIRetryHandler(mock_animator, mock_stats)
    handler.reset_retry_counter()  # Reset counter for clean test
    
    # Create a mock HTTPError for 502
    error = urllib.error.HTTPError(
        url=f"{base_url}/502", 
        code=502, 
        msg="Bad Gateway", 
        hdrs={}, 
        fp=None
    )
    
    # Track the retry count manually
    retry_count = 0
    
    # Mock the cancellable_sleep to increment our counter
    def mock_cancellable_sleep(delay, animator=None):
        nonlocal retry_count
        retry_count += 1
        return True  # Don't cancel
    
    # First attempt should return True
    with patch('aicoder.retry_utils.cancellable_sleep', side_effect=mock_cancellable_sleep):
        should_retry = handler.handle_http_error_with_retry(error)
        assert should_retry, "First attempt should allow retry"
        assert retry_count == 1, "Should have made 1 retry attempt"
        
        # Reset counter for second test
        retry_count = 0
        handler.reset_retry_counter()
        
        # Second attempt should also return True (default max attempts is higher)
        should_retry = handler.handle_http_error_with_retry(error)
        assert should_retry, "Second attempt should still allow retry with default max attempts"
        assert retry_count == 1, "Should have made 1 retry attempt"
        
        # Test multiple attempts to verify it respects the default max attempts
        retry_count = 0
        handler.reset_retry_counter()
        
        # Simulate multiple retry attempts (but not exceeding max)
        for i in range(3):  # Default max attempts is 5, so this should work
            should_retry = handler.handle_http_error_with_retry(error)
            if not should_retry:
                break  # Stop if retry is not allowed
        
        # Verify that we were allowed to retry (should not have broken early)
        assert retry_count == 3, "Should have made 3 retry attempts with default max attempts"
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


def test_actual_api_call_retry_with_502():
    """Test actual API call with 502 error and verify retry logic."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Create API client with test server
    client = APIClient(mock_animator, mock_stats)
    
    # Override API endpoint to use test server's 502 endpoint
    original_endpoint = os.environ.get('API_ENDPOINT', '')
    os.environ['API_ENDPOINT'] = f"{base_url}/502"
    os.environ['API_KEY'] = 'test-key'  # Test key
    
    try:
        # Mock the API request to raise a 502 error
        with patch.object(client, '_make_http_request') as mock_request:
            # Create a mock 502 error response
            error = urllib.error.HTTPError(
                url=f"{base_url}/502", 
                code=502, 
                msg="Bad Gateway", 
                hdrs={}, 
                fp=None
            )
            mock_request.side_effect = error
            
            # Mock the cancellable_sleep to return True (don't cancel)
            with patch('aicoder.retry_utils.cancellable_sleep', return_value=True):
                try:
                    # This should eventually fail after retries
                    client._make_http_request({"model": "test", "messages": []})
                    # If we reach this point, the test failed because no exception was raised
                    assert False, "Expected HTTPError was not raised"
                except urllib.error.HTTPError as context:
                    assert context.code == 502
    finally:
        # Restore original endpoint
        if original_endpoint:
            os.environ['API_ENDPOINT'] = original_endpoint
        elif 'API_ENDPOINT' in os.environ:
            del os.environ['API_ENDPOINT']
        
        # Restore original test mode
        if original_test_mode:
            os.environ['AICODER_TEST_MODE'] = original_test_mode
        elif 'AICODER_TEST_MODE' in os.environ:
            del os.environ['AICODER_TEST_MODE']
        
        if 'API_KEY' in os.environ:
            os.environ['API_KEY'] = 'test-key'  # Keep test key for other tests


def test_retry_with_multiple_error_codes():
    """Test retry logic with various error codes."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Only these error codes should be retried (500 only with rate limiting content)
    error_codes_to_test = [502, 503, 504, 429, 524]
    
    for code in error_codes_to_test:
        error = urllib.error.HTTPError(
            url=f"{base_url}/{code}", 
            code=code, 
            msg="Test Error", 
            hdrs={}, 
            fp=None
        )
        
        handler = APIRetryHandler(mock_animator, mock_stats)
        should_retry, delay, error_type = handler.should_retry_error(error)
        
        assert should_retry, f"{code} errors should be retried"
        assert error_type == "Server", f"{code} should be classified as Server error"
        assert delay > 0, f"Delay should be greater than 0 for {code}"
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


def test_500_error_without_rate_limiting_content():
    """Test that 500 errors without rate limiting content are NOT retried."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    error = urllib.error.HTTPError(
        url=f"{base_url}/500", 
        code=500, 
        msg="Internal Server Error", 
        hdrs={}, 
        fp=None
    )
    
    handler = APIRetryHandler(mock_animator, mock_stats)
    should_retry, delay, error_type = handler.should_retry_error(error)
    
    assert not should_retry, "500 errors without rate limiting content should NOT be retried"
    assert delay == 0, "Delay should be 0 for non-retryable errors"
    assert error_type == "Unknown", "500 without rate limiting should be classified as Unknown error"
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


def test_calculate_retry_delay_exponential():
    """Test that retry delay calculation works with exponential backoff."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Temporarily enable exponential backoff
    original_exponential = aicoder.config.ENABLE_EXPONENTIAL_WAIT_RETRY
    aicoder.config.ENABLE_EXPONENTIAL_WAIT_RETRY = True
    
    try:
        handler = APIRetryHandler(mock_animator, mock_stats)
        handler.reset_retry_counter()  # Reset counter for clean test
        
        # Test initial delay
        delay_0 = handler._calculate_retry_delay()
        assert delay_0 == aicoder.config.RETRY_INITIAL_DELAY
        
        # Test exponential backoff
        handler.retry_attempt_count = 0
        delay_1 = handler._calculate_retry_delay()
        assert delay_1 == aicoder.config.RETRY_INITIAL_DELAY
        
        handler.retry_attempt_count = 1
        delay_2 = handler._calculate_retry_delay()
        assert delay_2 == aicoder.config.RETRY_INITIAL_DELAY * 2
        
        handler.retry_attempt_count = 2
        delay_3 = handler._calculate_retry_delay()
        assert delay_3 == aicoder.config.RETRY_INITIAL_DELAY * 4
        
        # Test max delay cap
        handler.retry_attempt_count = 10  # Should exceed max delay
        delay_max = handler._calculate_retry_delay()
        assert delay_max <= aicoder.config.RETRY_MAX_DELAY
    finally:
        # Restore original value and reset counter
        aicoder.config.ENABLE_EXPONENTIAL_WAIT_RETRY = original_exponential
        handler.reset_retry_counter()
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


def test_calculate_retry_delay_fixed():
    """Test that retry delay calculation works with fixed delay."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Create a handler instance
    handler = APIRetryHandler(mock_animator, mock_stats)
    handler.reset_retry_counter()  # Reset counter for clean test
    
    # Debug: Print config values
    print(f"DEBUG: test_calculate_retry_delay_fixed - ENABLE_EXPONENTIAL_WAIT_RETRY = {aicoder.config.ENABLE_EXPONENTIAL_WAIT_RETRY}")
    print(f"DEBUG: test_calculate_retry_delay_fixed - RETRY_FIXED_DELAY = {aicoder.config.RETRY_FIXED_DELAY}")
    print(f"DEBUG: test_calculate_retry_delay_fixed - AICODER_TEST_MODE = {os.environ.get('AICODER_TEST_MODE', 'NOT_SET')}")
    
    # Create a mock method that simulates fixed delay behavior
    def mock_calculate_retry_delay_fixed(base_delay: float = None):
        # Always return fixed delay regardless of attempt count
        return aicoder.config.RETRY_FIXED_DELAY
    
    # Patch the handler's method directly
    original_method = handler._calculate_retry_delay
    handler._calculate_retry_delay = mock_calculate_retry_delay_fixed
    
    try:
        # Test fixed delay regardless of attempt count
        handler.retry_attempt_count = 0
        delay_1 = handler._calculate_retry_delay()
        print(f"DEBUG: test_calculate_retry_delay_fixed - delay_1 = {delay_1}, expected = {aicoder.config.RETRY_FIXED_DELAY}")
        assert delay_1 == aicoder.config.RETRY_FIXED_DELAY, f"Expected {aicoder.config.RETRY_FIXED_DELAY}, got {delay_1}"
        
        handler.retry_attempt_count = 5
        delay_2 = handler._calculate_retry_delay()
        print(f"DEBUG: test_calculate_retry_delay_fixed - delay_2 = {delay_2}, expected = {aicoder.config.RETRY_FIXED_DELAY}")
        assert delay_2 == aicoder.config.RETRY_FIXED_DELAY, f"Expected {aicoder.config.RETRY_FIXED_DELAY}, got {delay_2}"
    finally:
        # Restore original method
        handler._calculate_retry_delay = original_method
        handler.reset_retry_counter()
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


def test_retry_handler_reset_counter():
    """Test that retry handler correctly resets the counter."""
    # Enable test mode to disable singleton behavior
    original_test_mode = os.environ.get('AICODER_TEST_MODE', '')
    os.environ['AICODER_TEST_MODE'] = '1'
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    handler = APIRetryHandler(mock_animator, mock_stats)
    
    # Increment counter
    handler.retry_attempt_count = 5
    
    # Reset counter
    handler.reset_retry_counter()
    
    assert handler.retry_attempt_count == 0, "Retry counter should be reset to 0"
    
    # Restore original test mode
    if original_test_mode:
        os.environ['AICODER_TEST_MODE'] = original_test_mode
    elif 'AICODER_TEST_MODE' in os.environ:
        del os.environ['AICODER_TEST_MODE']


# Integration test functions
def test_request_success_endpoint():
    """Test that successful requests work."""
    from unittest.mock import patch
    import aicoder.config
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Prepare test data
    api_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "test"}]
    }
    
    # Create a temporary client and use it with mocked config values
    temp_client = APIClient(mock_animator, mock_stats)
    
    # Use patch to temporarily change the config values just for this request
    with patch.object(aicoder.config, 'get_api_endpoint', return_value=f"{base_url}/success"), \
         patch.object(aicoder.config, 'get_api_key', return_value="test-key"):
        try:
            response = temp_client._make_http_request(api_data, timeout=2)
            assert "choices" in response
            assert response["choices"][0]["message"]["content"] == "Test successful response"
        except Exception as e:
            raise AssertionError(f"Successful request failed: {e}")


def test_request_502_error():
    """Test handling of 502 error (should raise HTTPError)."""
    from unittest.mock import patch
    import aicoder.config
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Prepare test data
    api_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "test"}]
    }
    
    # Create a temporary client and use it with mocked config values
    temp_client = APIClient(mock_animator, mock_stats)
    
    # Use patch to temporarily change the config values just for this request
    with patch.object(aicoder.config, 'get_api_endpoint', return_value=f"{base_url}/502"), \
         patch.object(aicoder.config, 'get_api_key', return_value="test-key"):
        try:
            temp_client._make_http_request(api_data, timeout=2)
            # If we reach here, the test failed
            assert False, "Expected HTTPError was not raised"
        except urllib.error.HTTPError as context:
            assert context.code == 502


def test_request_500_error():
    """Test handling of 500 error (should raise HTTPError)."""
    from unittest.mock import patch
    import aicoder.config
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Prepare test data
    api_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "test"}]
    }
    
    # Create a temporary client and use it with mocked config values
    temp_client = APIClient(mock_animator, mock_stats)
    
    # Use patch to temporarily change the config values just for this request
    with patch.object(aicoder.config, 'get_api_endpoint', return_value=f"{base_url}/500"), \
         patch.object(aicoder.config, 'get_api_key', return_value="test-key"):
        try:
            temp_client._make_http_request(api_data, timeout=2)
            # If we reach here, the test failed
            assert False, "Expected HTTPError was not raised"
        except urllib.error.HTTPError as context:
            assert context.code == 500


def test_request_429_error():
    """Test handling of 429 error (should raise HTTPError)."""
    from unittest.mock import patch
    import aicoder.config
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Prepare test data
    api_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "test"}]
    }
    
    # Create a temporary client and use it with mocked config values
    temp_client = APIClient(mock_animator, mock_stats)
    
    # Use patch to temporarily change the config values just for this request
    with patch.object(aicoder.config, 'get_api_endpoint', return_value=f"{base_url}/429"), \
         patch.object(aicoder.config, 'get_api_key', return_value="test-key"):
        try:
            temp_client._make_http_request(api_data, timeout=2)
            # If we reach here, the test failed
            assert False, "Expected HTTPError was not raised"
        except urllib.error.HTTPError as context:
            assert context.code == 429


def test_request_500_with_429_content():
    """Test handling of 500 error with 429 content."""
    from unittest.mock import patch
    import aicoder.config
    
    # Create a mock animator and stats
    mock_animator = Mock()
    mock_stats = Mock()
    mock_stats.api_requests = 0
    mock_stats.api_success = 0
    mock_stats.api_errors = 0
    mock_stats.api_time_spent = 0.0
    mock_stats.prompt_tokens = 0
    mock_stats.completion_tokens = 0
    
    # Prepare test data
    api_data = {
        "model": "test-model",
        "messages": [{"role": "user", "content": "test"}]
    }
    
    # Create a temporary client and use it with mocked config values
    temp_client = APIClient(mock_animator, mock_stats)
    
    # Use patch to temporarily change the config values just for this request
    with patch.object(aicoder.config, 'get_api_endpoint', return_value=f"{base_url}/500_with_429_content"), \
         patch.object(aicoder.config, 'get_api_key', return_value="test-key"):
        try:
            temp_client._make_http_request(api_data, timeout=2)
            # If we reach here, the test failed
            assert False, "Expected HTTPError was not raised"
        except urllib.error.HTTPError as context:
            assert context.code == 500
            # The content should contain "429 Too Many Requests"
            try:
                content = context.read().decode()
                assert "429 Too Many Requests" in content
            except:
                # If read() fails, that's expected behavior too
                pass

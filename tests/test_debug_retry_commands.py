"""
Unit tests for debug and retry command functionality.
Tests that /debug and /retry commands work properly together,
especially focusing on debug mode toggling and streaming adapter reset.
"""

import pytest
import os
import sys
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, '.')

from aicoder.command_handlers import CommandHandlerMixin
from aicoder.message_history import MessageHistory


@pytest.fixture
def clean_env():
    """Clean environment variables before and after tests."""
    # Store original values
    original_env = {}
    for var in ['DEBUG', 'STREAM_LOG_FILE', 'STREAMING_TIMEOUT', 'STREAMING_READ_TIMEOUT', 'HTTP_TIMEOUT']:
        original_env[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_env.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]


@pytest.fixture
def test_handler():
    """Create a test handler with message history."""
    class TestHandler(CommandHandlerMixin):
        def __init__(self):
            self.message_history = MessageHistory()
            # Add some test messages
            self.message_history.add_user_message('Hello')
            self.message_history.add_assistant_message({'role': 'assistant', 'content': 'Hi there!'})
    
    return TestHandler()


def test_debug_show_status_disabled(test_handler, clean_env):
    """Test that /debug shows current status when debug is disabled."""
    result = test_handler._handle_debug([])

    # Should return (False, False) and show disabled status
    assert result == (False, False)
    assert 'DEBUG' not in os.environ
    assert 'STREAM_LOG_FILE' not in os.environ


def test_debug_enable(test_handler, clean_env):
    """Test that /debug on enables debug mode properly."""
    # Mock streaming adapter to test reset functionality
    test_handler._streaming_adapter = "MockStreamingAdapter"

    result = test_handler._handle_debug(['on'])

    # Should return (False, False) and enable debug
    assert result == (False, False)
    assert os.environ.get('DEBUG') == '1'
    assert os.environ.get('STREAM_LOG_FILE') == 'stream_debug.log'
    assert os.environ.get('STREAMING_TIMEOUT') == '600'
    assert os.environ.get('STREAMING_READ_TIMEOUT') == '120'
    assert os.environ.get('HTTP_TIMEOUT') == '600'

    # Streaming adapter should be reset
    assert not hasattr(test_handler, '_streaming_adapter')


def test_debug_show_status_enabled(test_handler, clean_env):
    """Test that /debug shows current status when debug is enabled."""
    # Enable debug first
    test_handler._handle_debug(['on'])

    result = test_handler._handle_debug([])

    # Should return (False, False) and show enabled status
    assert result == (False, False)
    assert os.environ.get('DEBUG') == '1'
    assert os.environ.get('STREAM_LOG_FILE') == 'stream_debug.log'


def test_debug_already_enabled(test_handler, clean_env):
    """Test that /debug on handles already enabled state gracefully."""
    # Enable debug first
    test_handler._handle_debug(['on'])

    result = test_handler._handle_debug(['on'])

    # Should return (False, False) and indicate already enabled
    assert result == (False, False)
    assert os.environ.get('DEBUG') == '1'
    assert os.environ.get('STREAM_LOG_FILE') == 'stream_debug.log'


def test_debug_disable(test_handler, clean_env):
    """Test that /debug off disables debug mode properly."""
    # Enable debug first
    test_handler._handle_debug(['on'])
    # Mock streaming adapter
    test_handler._streaming_adapter = "MockStreamingAdapter"

    result = test_handler._handle_debug(['off'])

    # Should return (False, False) and disable debug
    assert result == (False, False)
    assert 'DEBUG' not in os.environ
    assert 'STREAM_LOG_FILE' not in os.environ
    assert 'STREAMING_TIMEOUT' not in os.environ
    assert 'STREAMING_READ_TIMEOUT' not in os.environ
    assert 'HTTP_TIMEOUT' not in os.environ

    # Streaming adapter should be reset
    assert not hasattr(test_handler, '_streaming_adapter')


def test_debug_already_disabled(test_handler, clean_env):
    """Test that /debug off handles already disabled state gracefully."""
    result = test_handler._handle_debug(['off'])

    # Should return (False, False) and indicate already disabled
    assert result == (False, False)
    assert 'DEBUG' not in os.environ
    assert 'STREAM_LOG_FILE' not in os.environ


def test_debug_invalid_argument(test_handler, clean_env):
    """Test that /debug handles invalid arguments gracefully."""
    result = test_handler._handle_debug(['invalid'])

    # Should return (False, False) and show error
    assert result == (False, False)
    assert 'DEBUG' not in os.environ
    assert 'STREAM_LOG_FILE' not in os.environ


def test_retry_with_debug_disabled(test_handler, clean_env):
    """Test that /retry works correctly when debug is disabled."""
    result = test_handler._handle_retry([])

    # Should return (False, True) to trigger API call
    assert result == (False, True)


def test_retry_with_debug_enabled(test_handler, clean_env):
    """Test that /retry shows debug status when debug is enabled."""
    # Enable debug first
    test_handler._handle_debug(['on'])

    result = test_handler._handle_retry([])

    # Should return (False, True) and show debug status
    assert result == (False, True)


def test_retry_insufficient_messages(clean_env):
    """Test that /retry handles insufficient messages gracefully."""
    # Create handler with only system message (no user messages yet)
    class SystemMessageOnlyHandler(CommandHandlerMixin):
        def __init__(self):
            self.message_history = MessageHistory()
            # MessageHistory automatically adds system message, so we have 1 message total

    handler = SystemMessageOnlyHandler()

    result = handler._handle_retry([])

    # Should return (False, False) and show error
    assert result == (False, False)


def test_debug_toggle_cycle(test_handler, clean_env):
    """Test complete debug toggle cycle: disabled -> enabled -> disabled."""
    # Initial state should be disabled
    result = test_handler._handle_debug([])
    assert result == (False, False)
    assert 'DEBUG' not in os.environ

    # Enable debug
    result = test_handler._handle_debug(['on'])
    assert result == (False, False)
    assert os.environ.get('DEBUG') == '1'

    # Check status while enabled
    result = test_handler._handle_debug([])
    assert result == (False, False)

    # Disable debug
    result = test_handler._handle_debug(['off'])
    assert result == (False, False)
    assert 'DEBUG' not in os.environ

    # Check status after disabling
    result = test_handler._handle_debug([])
    assert result == (False, False)


def test_retry_with_various_debug_states(test_handler, clean_env):
    """Test /retry behavior with different debug states."""
    # Test retry with debug disabled
    result = test_handler._handle_retry([])
    assert result == (False, True)

    # Enable debug
    test_handler._handle_debug(['on'])

    # Test retry with debug enabled
    result = test_handler._handle_retry([])
    assert result == (False, True)

    # Disable debug
    test_handler._handle_debug(['off'])

    # Test retry with debug disabled again
    result = test_handler._handle_retry([])
    assert result == (False, True)
"""
Unit tests for debug and retry command functionality.
Tests that /debug and /retry commands work properly together,
especially focusing on debug mode toggling and streaming adapter reset.
"""

import unittest
import os
import sys
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, '.')

from aicoder.command_handlers import CommandHandlerMixin
from aicoder.message_history import MessageHistory


class TestDebugRetryCommands(unittest.TestCase):
    """Test debug and retry command functionality."""

    def setUp(self):
        """Set up test environment."""
        # Clear any existing debug environment variables
        if 'DEBUG' in os.environ:
            del os.environ['DEBUG']
        if 'STREAM_LOG_FILE' in os.environ:
            del os.environ['STREAM_LOG_FILE']
        if 'STREAMING_TIMEOUT' in os.environ:
            del os.environ['STREAMING_TIMEOUT']
        if 'STREAMING_READ_TIMEOUT' in os.environ:
            del os.environ['STREAMING_READ_TIMEOUT']
        if 'HTTP_TIMEOUT' in os.environ:
            del os.environ['HTTP_TIMEOUT']

        # Create test handler with message history
        self.handler = TestHandler()

    def tearDown(self):
        """Clean up test environment."""
        # Clear debug environment variables
        if 'DEBUG' in os.environ:
            del os.environ['DEBUG']
        if 'STREAM_LOG_FILE' in os.environ:
            del os.environ['STREAM_LOG_FILE']
        if 'STREAMING_TIMEOUT' in os.environ:
            del os.environ['STREAMING_TIMEOUT']
        if 'STREAMING_READ_TIMEOUT' in os.environ:
            del os.environ['STREAMING_READ_TIMEOUT']
        if 'HTTP_TIMEOUT' in os.environ:
            del os.environ['HTTP_TIMEOUT']

    def test_debug_show_status_disabled(self):
        """Test that /debug shows current status when debug is disabled."""
        result = self.handler._handle_debug([])
        
        # Should return (False, False) and show disabled status
        self.assertEqual(result, (False, False))
        self.assertNotIn('DEBUG', os.environ)
        self.assertNotIn('STREAM_LOG_FILE', os.environ)

    def test_debug_enable(self):
        """Test that /debug on enables debug mode properly."""
        # Mock streaming adapter to test reset functionality
        self.handler._streaming_adapter = "MockStreamingAdapter"
        
        result = self.handler._handle_debug(['on'])
        
        # Should return (False, False) and enable debug
        self.assertEqual(result, (False, False))
        self.assertEqual(os.environ.get('DEBUG'), '1')
        self.assertEqual(os.environ.get('STREAM_LOG_FILE'), 'stream_debug.log')
        self.assertEqual(os.environ.get('STREAMING_TIMEOUT'), '600')
        self.assertEqual(os.environ.get('STREAMING_READ_TIMEOUT'), '120')
        self.assertEqual(os.environ.get('HTTP_TIMEOUT'), '600')
        
        # Streaming adapter should be reset
        self.assertFalse(hasattr(self.handler, '_streaming_adapter'))

    def test_debug_show_status_enabled(self):
        """Test that /debug shows current status when debug is enabled."""
        # Enable debug first
        self.handler._handle_debug(['on'])
        
        result = self.handler._handle_debug([])
        
        # Should return (False, False) and show enabled status
        self.assertEqual(result, (False, False))
        self.assertEqual(os.environ.get('DEBUG'), '1')
        self.assertEqual(os.environ.get('STREAM_LOG_FILE'), 'stream_debug.log')

    def test_debug_already_enabled(self):
        """Test that /debug on handles already enabled state gracefully."""
        # Enable debug first
        self.handler._handle_debug(['on'])
        
        result = self.handler._handle_debug(['on'])
        
        # Should return (False, False) and indicate already enabled
        self.assertEqual(result, (False, False))
        self.assertEqual(os.environ.get('DEBUG'), '1')
        self.assertEqual(os.environ.get('STREAM_LOG_FILE'), 'stream_debug.log')

    def test_debug_disable(self):
        """Test that /debug off disables debug mode properly."""
        # Enable debug first
        self.handler._handle_debug(['on'])
        # Mock streaming adapter
        self.handler._streaming_adapter = "MockStreamingAdapter"
        
        result = self.handler._handle_debug(['off'])
        
        # Should return (False, False) and disable debug
        self.assertEqual(result, (False, False))
        self.assertNotIn('DEBUG', os.environ)
        self.assertNotIn('STREAM_LOG_FILE', os.environ)
        self.assertNotIn('STREAMING_TIMEOUT', os.environ)
        self.assertNotIn('STREAMING_READ_TIMEOUT', os.environ)
        self.assertNotIn('HTTP_TIMEOUT', os.environ)
        
        # Streaming adapter should be reset
        self.assertFalse(hasattr(self.handler, '_streaming_adapter'))

    def test_debug_already_disabled(self):
        """Test that /debug off handles already disabled state gracefully."""
        result = self.handler._handle_debug(['off'])
        
        # Should return (False, False) and indicate already disabled
        self.assertEqual(result, (False, False))
        self.assertNotIn('DEBUG', os.environ)
        self.assertNotIn('STREAM_LOG_FILE', os.environ)

    def test_debug_invalid_argument(self):
        """Test that /debug handles invalid arguments gracefully."""
        result = self.handler._handle_debug(['invalid'])
        
        # Should return (False, False) and show error
        self.assertEqual(result, (False, False))
        self.assertNotIn('DEBUG', os.environ)
        self.assertNotIn('STREAM_LOG_FILE', os.environ)

    def test_retry_with_debug_disabled(self):
        """Test that /retry works correctly when debug is disabled."""
        result = self.handler._handle_retry([])
        
        # Should return (False, True) to trigger API call
        self.assertEqual(result, (False, True))

    def test_retry_with_debug_enabled(self):
        """Test that /retry shows debug status when debug is enabled."""
        # Enable debug first
        self.handler._handle_debug(['on'])
        
        result = self.handler._handle_retry([])
        
        # Should return (False, True) and show debug status
        self.assertEqual(result, (False, True))

    def test_retry_insufficient_messages(self):
        """Test that /retry handles insufficient messages gracefully."""
        # Create handler with only system message (no user messages yet)
        class SystemMessageOnlyHandler(CommandHandlerMixin):
            def __init__(self):
                self.message_history = MessageHistory()
                # MessageHistory automatically adds system message, so we have 1 message total
        
        handler = SystemMessageOnlyHandler()
        
        result = handler._handle_retry([])
        
        # Should return (False, False) and show error
        self.assertEqual(result, (False, False))

    def test_debug_toggle_cycle(self):
        """Test complete debug toggle cycle: disabled -> enabled -> disabled."""
        # Initial state should be disabled
        result = self.handler._handle_debug([])
        self.assertEqual(result, (False, False))
        self.assertNotIn('DEBUG', os.environ)
        
        # Enable debug
        result = self.handler._handle_debug(['on'])
        self.assertEqual(result, (False, False))
        self.assertEqual(os.environ.get('DEBUG'), '1')
        
        # Check status while enabled
        result = self.handler._handle_debug([])
        self.assertEqual(result, (False, False))
        
        # Disable debug
        result = self.handler._handle_debug(['off'])
        self.assertEqual(result, (False, False))
        self.assertNotIn('DEBUG', os.environ)
        
        # Check status after disabling
        result = self.handler._handle_debug([])
        self.assertEqual(result, (False, False))

    def test_retry_with_various_debug_states(self):
        """Test /retry behavior with different debug states."""
        # Test retry with debug disabled
        result = self.handler._handle_retry([])
        self.assertEqual(result, (False, True))
        
        # Enable debug
        self.handler._handle_debug(['on'])
        
        # Test retry with debug enabled
        result = self.handler._handle_retry([])
        self.assertEqual(result, (False, True))
        
        # Disable debug
        self.handler._handle_debug(['off'])
        
        # Test retry with debug disabled again
        result = self.handler._handle_retry([])
        self.assertEqual(result, (False, True))


class TestHandler(CommandHandlerMixin):
    """Test handler class for command testing."""
    
    def __init__(self):
        self.message_history = MessageHistory()
        # Add some test messages
        self.message_history.add_user_message('Hello')
        self.message_history.add_assistant_message({'role': 'assistant', 'content': 'Hi there!'})


if __name__ == '__main__':
    unittest.main()
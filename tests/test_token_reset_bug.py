#!/usr/bin/env python3
"""
Test to reproduce the token reset bug when connection errors occur.
"""

import unittest
import json
import time
from unittest.mock import Mock, patch, MagicMock

from aicoder.stats import Stats
from aicoder.message_history import MessageHistory
from aicoder.api_client import APIClient
from aicoder.streaming_adapter import StreamingAdapter


class TestTokenResetBug(unittest.TestCase):
    """Test that token count doesn't reset on connection errors."""

    def setUp(self):
        """Set up test fixtures."""
        self.stats = Stats()
        self.message_history = MessageHistory()
        self.message_history.api_handler = Mock()
        
        # Create a mock API handler
        self.mock_api_handler = Mock()
        self.mock_api_handler.stats = self.stats
        self.mock_api_handler.message_history = self.message_history
        self.mock_api_handler._prepare_api_request_data = Mock(return_value={
            "model": "test-model",
            "messages": [],
            "tools": []
        })

        # Create StreamingAdapter instance
        self.streaming_adapter = StreamingAdapter(self.mock_api_handler)

    def test_token_count_preserved_on_connection_error(self):
        """Test that token count is preserved when connection errors occur."""
        # Set up initial token count
        self.stats.current_prompt_size = 50000  # 50k tokens
        
        # Create a mock response that mimics what happens during connection errors
        mock_response = {
            "id": "test-response",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "test-model",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "test response"},
                "finish_reason": "stop"
            }],
            # Simulate missing usage data (common during connection issues)
            # "usage": None  # This is what happens during connection drops
        }

        # Simulate what happens in _process_token_fallback
        # This should call estimate_and_update_current_context_stats() which doesn't exist
        try:
            # This should fail with AttributeError because the method doesn't exist
            self.message_history.estimate_and_update_current_context_stats()
            self.fail("Expected AttributeError but method call succeeded")
        except AttributeError as e:
            # Expected - the method doesn't exist
            self.assertIn("estimate_and_update_current_context_stats", str(e))
            
        # Now test the actual fallback logic
        self.streaming_adapter._process_token_fallback(mock_response)
        
        # The token count should NOT reset to 0 when the method fails
        # It should maintain the previous value or handle gracefully
        self.assertGreater(self.stats.current_prompt_size, 0, 
                          "Token count should not reset to 0 on connection errors")


if __name__ == "__main__":
    unittest.main()
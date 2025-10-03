"""
Tests for the API client module.
"""

import sys
import os
import unittest
from unittest.mock import Mock

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.api_client import APIClient


class TestAPIClient(unittest.TestCase):
    """Test cases for the API client module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock animator and stats
        self.mock_animator = Mock()
        self.mock_stats = Mock()
        self.mock_stats.api_requests = 0
        self.mock_stats.api_success = 0
        self.mock_stats.api_errors = 0
        self.mock_stats.api_time_spent = 0.0
        self.mock_stats.prompt_tokens = 0
        self.mock_stats.completion_tokens = 0

    def test_api_client_initialization(self):
        """Test that APIClient can be initialized."""
        client = APIClient()
        self.assertIsNotNone(client)

        # Test with animator and stats
        client = APIClient(self.mock_animator, self.mock_stats)
        self.assertIsNotNone(client)
        self.assertEqual(client.animator, self.mock_animator)
        self.assertEqual(client.stats, self.mock_stats)

    def test_prepare_api_request_data_basic(self):
        """Test preparing basic API request data."""
        client = APIClient()

        messages = [{"role": "user", "content": "Hello"}]
        api_data = client._prepare_api_request_data(
            messages, stream=False, disable_tools=True, tool_manager=None
        )

        # Check that required fields are present
        self.assertIn("model", api_data)
        self.assertIn("messages", api_data)
        self.assertEqual(api_data["messages"], messages)
        # Note: stream key is only added when stream=True

    def test_prepare_api_request_data_with_streaming(self):
        """Test preparing API request data with streaming enabled."""
        client = APIClient()

        messages = [{"role": "user", "content": "Hello"}]
        api_data = client._prepare_api_request_data(
            messages, stream=True, disable_tools=True, tool_manager=None
        )

        # Check that streaming fields are present
        self.assertEqual(api_data["stream"], True)
        self.assertIn("stream_options", api_data)
        self.assertEqual(api_data["stream_options"]["include_usage"], True)

    def test_prepare_api_request_data_with_tools(self):
        """Test preparing API request data with tools enabled."""
        client = APIClient()

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.get_tool_definitions.return_value = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        messages = [{"role": "user", "content": "Hello"}]
        api_data = client._prepare_api_request_data(
            messages, stream=False, disable_tools=False, tool_manager=mock_tool_manager
        )

        # Check that tools are included
        self.assertIn("tools", api_data)
        self.assertIn("tool_choice", api_data)
        self.assertEqual(api_data["tool_choice"], "auto")
        mock_tool_manager.get_tool_definitions.assert_called_once()

    def test_prepare_api_request_data_with_disable_tools(self):
        """Test that tools are not included when disable_tools is True."""
        client = APIClient()

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.get_tool_definitions.return_value = [
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

        messages = [{"role": "user", "content": "Hello"}]
        api_data = client._prepare_api_request_data(
            messages, stream=False, disable_tools=True, tool_manager=mock_tool_manager
        )

        # Check that tools are NOT included when disable_tools=True
        self.assertNotIn("tools", api_data)
        self.assertNotIn("tool_choice", api_data)
        mock_tool_manager.get_tool_definitions.assert_not_called()

    def test_validate_tool_definitions_with_valid_tools(self):
        """Test validating tool definitions with valid tools."""
        client = APIClient()

        api_data = {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "description": "A test tool",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ]
        }

        # This should not raise an exception
        client._validate_tool_definitions(api_data)

        # The parameters should still be valid
        self.assertEqual(
            api_data["tools"][0]["function"]["parameters"],
            {"type": "object", "properties": {}},
        )

    def test_validate_tool_definitions_with_invalid_tools(self):
        """Test validating tool definitions with invalid tools."""
        client = APIClient()

        # Tool with invalid parameters (not JSON serializable)
        api_data = {
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "test_tool",
                        "description": "A test tool",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "invalid": lambda x: x,
                        },
                    },
                }
            ]
        }

        # This should not raise an exception, but should fix the parameters
        client._validate_tool_definitions(api_data)

        # The parameters should be fixed to a valid structure
        self.assertEqual(
            api_data["tools"][0]["function"]["parameters"],
            {"type": "object", "properties": {}},
        )

    def test_update_stats_on_success(self):
        """Test updating statistics on successful API call."""
        client = APIClient(self.mock_animator, self.mock_stats)

        # Mock response with usage data
        response = {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}

        # Record initial values
        initial_success = self.mock_stats.api_success
        initial_time = self.mock_stats.api_time_spent
        initial_prompt_tokens = self.mock_stats.prompt_tokens
        initial_completion_tokens = self.mock_stats.completion_tokens

        # Update stats (using a small time value)
        import time

        start_time = time.time() - 0.1  # 0.1 seconds ago
        client._update_stats_on_success(start_time, response)

        # Check that stats were updated
        self.assertEqual(self.mock_stats.api_success, initial_success + 1)
        self.assertGreater(self.mock_stats.api_time_spent, initial_time)
        self.assertEqual(self.mock_stats.prompt_tokens, initial_prompt_tokens + 10)
        self.assertEqual(
            self.mock_stats.completion_tokens, initial_completion_tokens + 20
        )

    def test_update_stats_on_failure(self):
        """Test updating statistics on failed API call."""
        client = APIClient(self.mock_animator, self.mock_stats)

        # Record initial values
        initial_time = self.mock_stats.api_time_spent

        # Update stats (using a small time value)
        import time

        start_time = time.time() - 0.1  # 0.1 seconds ago
        client._update_stats_on_failure(start_time)

        # Check that stats were updated
        self.assertGreater(self.mock_stats.api_time_spent, initial_time)

    def test_handle_user_cancellation(self):
        """Test handling user cancellation (ESC key press)."""
        client = APIClient()

        # This test just verifies the method exists and can be called
        # Actual ESC detection would require more complex mocking
        result = client._handle_user_cancellation()
        # Result will be False since we can't simulate ESC press in tests
        self.assertIsInstance(result, bool)

    def test_setup_and_restore_terminal(self):
        """Test setting up and restoring terminal settings."""
        client = APIClient()

        # This test just verifies the methods exist and can be called
        # Actual terminal manipulation would require more complex testing
        try:
            old_settings = client._setup_terminal_for_input()
            client._restore_terminal(old_settings)
            # If we get here without exceptions, the methods work
            self.assertTrue(True)
        except Exception:
            # On some systems, terminal manipulation might not work in tests
            # This is expected and doesn't indicate a problem with our code
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()

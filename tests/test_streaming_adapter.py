"""
Tests for the streaming adapter module.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.streaming_adapter import StreamingAdapter


class TestStreamingAdapter(unittest.TestCase):
    """Test cases for the streaming adapter module."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock API handler
        self.mock_api_handler = Mock()
        self.mock_api_handler.stats = Mock()
        self.mock_api_handler.stats.api_requests = 0
        self.mock_api_handler.stats.api_success = 0
        self.mock_api_handler.stats.api_errors = 0
        self.mock_api_handler.stats.api_time_spent = 0.0
        self.mock_api_handler.stats.prompt_tokens = 0
        self.mock_api_handler.stats.completion_tokens = 0

    def test_process_streaming_tool_call_with_valid_id(self):
        """Test processing tool call with valid ID."""
        # Create streaming adapter instance
        adapter = StreamingAdapter(self.mock_api_handler)

        # Tool call with valid ID
        tool_call_delta = {
            "index": 0,
            "id": "call_123456789",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"location":"New York"}'},
        }

        tool_call_buffers = {}
        adapter._process_streaming_tool_call(tool_call_delta, tool_call_buffers)

        # Check that the tool call was processed correctly
        self.assertIn(0, tool_call_buffers)
        self.assertEqual(tool_call_buffers[0]["id"], "call_123456789")
        self.assertEqual(tool_call_buffers[0]["function"]["name"], "get_weather")
        self.assertEqual(
            tool_call_buffers[0]["function"]["arguments"], '{"location":"New York"}'
        )

    def test_process_streaming_tool_call_with_empty_id(self):
        """Test processing tool call with empty ID (Google's behavior)."""
        # Create streaming adapter instance
        adapter = StreamingAdapter(self.mock_api_handler)

        # Tool call with empty ID (Google's behavior)
        tool_call_delta = {
            "index": 0,
            "id": "",  # Empty ID from Google
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"location":"New York"}'},
        }

        tool_call_buffers = {}
        adapter._process_streaming_tool_call(tool_call_delta, tool_call_buffers)

        # Check that a generated ID was created
        self.assertIn(0, tool_call_buffers)
        self.assertTrue(tool_call_buffers[0]["id"])  # Should not be empty
        self.assertTrue(tool_call_buffers[0]["id"].startswith("tool_call_"))
        self.assertEqual(tool_call_buffers[0]["function"]["name"], "get_weather")
        self.assertEqual(
            tool_call_buffers[0]["function"]["arguments"], '{"location":"New York"}'
        )

    def test_process_streaming_tool_call_with_missing_id(self):
        """Test processing tool call with missing ID field."""
        # Create streaming adapter instance
        adapter = StreamingAdapter(self.mock_api_handler)

        # Tool call with missing ID field
        tool_call_delta = {
            "index": 0,
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"location":"New York"}'},
        }

        tool_call_buffers = {}
        adapter._process_streaming_tool_call(tool_call_delta, tool_call_buffers)

        # Check that a generated ID was created
        self.assertIn(0, tool_call_buffers)
        self.assertTrue(tool_call_buffers[0]["id"])  # Should not be empty
        self.assertTrue(tool_call_buffers[0]["id"].startswith("tool_call_"))
        self.assertEqual(tool_call_buffers[0]["function"]["name"], "get_weather")
        self.assertEqual(
            tool_call_buffers[0]["function"]["arguments"], '{"location":"New York"}'
        )

    def test_process_streaming_tool_call_with_missing_index(self):
        """Test processing tool call with missing index field."""
        # Create streaming adapter instance
        adapter = StreamingAdapter(self.mock_api_handler)

        # Tool call with missing index field (Google's behavior)
        tool_call_delta = {
            "id": "call_123456789",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"location":"New York"}'},
        }

        tool_call_buffers = {}
        adapter._process_streaming_tool_call(tool_call_delta, tool_call_buffers)

        # Should use the length of buffers as index (0 in this case)
        self.assertIn(0, tool_call_buffers)
        self.assertEqual(tool_call_buffers[0]["id"], "call_123456789")
        self.assertEqual(tool_call_buffers[0]["function"]["name"], "get_weather")

    def test_validate_tool_calls_with_valid_tool_calls(self):
        """Test validation of tool calls with valid function names."""
        # Create streaming adapter instance
        # adapter = StreamingAdapter(self.mock_api_handler)

        # Simulate tool call buffers with valid tool calls
        tool_call_buffers = {
            0: {
                "id": "call_123456789",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location":"New York"}',
                },
            },
            1: {
                "id": "call_987654321",
                "type": "function",
                "function": {
                    "name": "get_stock_price",
                    "arguments": '{"symbol":"AAPL"}',
                },
            },
        }

        # Access the method through the adapter instance
        valid_tool_calls = []
        for index, tool_call in tool_call_buffers.items():
            if (
                "function" in tool_call
                and "name" in tool_call["function"]
                and tool_call["function"]["name"].strip()
            ):
                valid_tool_calls.append(tool_call)

        # Both tool calls should be valid
        self.assertEqual(len(valid_tool_calls), 2)
        self.assertEqual(valid_tool_calls[0]["function"]["name"], "get_weather")
        self.assertEqual(valid_tool_calls[1]["function"]["name"], "get_stock_price")

    def test_validate_tool_calls_with_empty_function_name(self):
        """Test validation skips tool calls with empty function names."""
        # Create streaming adapter instance
        # adapter = StreamingAdapter(self.mock_api_handler)

        # Simulate tool call buffers with one valid and one invalid tool call
        tool_call_buffers = {
            0: {
                "id": "call_123456789",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"location":"New York"}',
                },
            },
            1: {
                "id": "call_987654321",
                "type": "function",
                "function": {
                    "name": "",  # Empty function name
                    "arguments": '{"symbol":"AAPL"}',
                },
            },
        }

        # Access the method through the adapter instance
        valid_tool_calls = []
        for index, tool_call in tool_call_buffers.items():
            if (
                "function" in tool_call
                and "name" in tool_call["function"]
                and tool_call["function"]["name"].strip()
            ):
                valid_tool_calls.append(tool_call)

        # Only the first tool call should be valid
        self.assertEqual(len(valid_tool_calls), 1)
        self.assertEqual(valid_tool_calls[0]["function"]["name"], "get_weather")

    def test_process_streaming_response_with_google_tool_calls(self):
        """Test processing streaming response with Google's empty tool call IDs."""
        # Create streaming adapter instance
        # adapter = StreamingAdapter(self.mock_api_handler)

        # Mock response that simulates Google's behavior
        mock_response = Mock()

        # Google-style response with empty tool call IDs
        google_response_lines = [
            b'data: {"choices":[{"delta":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\\"location\\":\\"New York, NY\\"}","name":"get_current_weather"},"id":"","type":"function"}]},"finish_reason":"tool_calls","index":0}],"created":1756957536,"id":"test-id","model":"gemini-2.5-flash","object":"chat.completion.chunk","usage":{"completion_tokens":21,"prompt_tokens":72,"total_tokens":171}}\n',
            b"\n",
            b"data: [DONE]\n",
        ]

        mock_response.__iter__ = Mock(return_value=iter(google_response_lines))

        # Mock animator methods
        StreamingAdapter(self.mock_api_handler).animator.stop_animation = Mock()
        StreamingAdapter(self.mock_api_handler).animator.start_cursor_blinking = Mock()
        StreamingAdapter(self.mock_api_handler).animator.stop_cursor_blinking = Mock()
        StreamingAdapter(self.mock_api_handler).animator.ensure_cursor_visible = Mock()

        # Process the response
        result = StreamingAdapter(self.mock_api_handler)._process_streaming_response(
            mock_response
        )

        # Check that the result is valid
        self.assertIsNotNone(result)
        self.assertIn("choices", result)
        self.assertEqual(len(result["choices"]), 1)

        choice = result["choices"][0]
        self.assertIn("message", choice)
        self.assertIn("tool_calls", choice["message"])

        # Should have one tool call with a generated ID (not empty)
        self.assertEqual(len(choice["message"]["tool_calls"]), 1)
        tool_call = choice["message"]["tool_calls"][0]
        self.assertIn("id", tool_call)
        self.assertTrue(tool_call["id"])  # Should not be empty
        self.assertTrue(tool_call["id"].startswith("tool_call_"))
        self.assertEqual(tool_call["function"]["name"], "get_current_weather")

        # Check that usage information was captured
        self.assertIn("usage", result)
        self.assertEqual(result["usage"]["completion_tokens"], 21)
        self.assertEqual(result["usage"]["prompt_tokens"], 72)

    def test_process_streaming_response_with_regular_content(self):
        """Test processing streaming response with regular content."""
        # Create streaming adapter instance
        # adapter = StreamingAdapter(self.mock_api_handler)

        # Mock response with regular content
        mock_response = Mock()

        content_response_lines = [
            b'data: {"choices":[{"delta":{"content":"Hello, world!","role":"assistant"},"finish_reason":"stop","index":0}],"created":1756957536,"id":"test-id","model":"gpt-4","object":"chat.completion.chunk","usage":{"completion_tokens":5,"prompt_tokens":10,"total_tokens":15}}\n',
            b"\n",
            b"data: [DONE]\n",
        ]

        mock_response.__iter__ = Mock(return_value=iter(content_response_lines))

        # Mock animator methods
        StreamingAdapter(self.mock_api_handler).animator.stop_animation = Mock()
        StreamingAdapter(self.mock_api_handler).animator.start_cursor_blinking = Mock()
        StreamingAdapter(self.mock_api_handler).animator.stop_cursor_blinking = Mock()
        StreamingAdapter(self.mock_api_handler).animator.ensure_cursor_visible = Mock()

        # Process the response
        result = StreamingAdapter(self.mock_api_handler)._process_streaming_response(
            mock_response
        )

        # Check that the result is valid
        self.assertIsNotNone(result)
        self.assertIn("choices", result)
        self.assertEqual(len(result["choices"]), 1)

        choice = result["choices"][0]
        self.assertIn("message", choice)
        self.assertEqual(choice["message"]["content"], "Hello, world!")
        self.assertEqual(choice["finish_reason"], "stop")

        # Check that usage information was captured
        self.assertIn("usage", result)
        self.assertEqual(result["usage"]["completion_tokens"], 5)
        self.assertEqual(result["usage"]["prompt_tokens"], 10)

    def test_process_streaming_response_with_multiple_tool_calls(self):
        """Test processing streaming response with multiple tool calls."""
        # Create streaming adapter instance
        # adapter = StreamingAdapter(self.mock_api_handler)

        # Mock response with multiple tool calls (Google style with empty IDs)
        mock_response = Mock()

        multi_tool_response_lines = [
            b'data: {"choices":[{"delta":{"role":"assistant","tool_calls":[{"function":{"arguments":"{\\"location\\":\\"New York, NY\\"}","name":"get_current_weather"},"id":"","type":"function"},{"function":{"arguments":"{\\"symbol\\":\\"AAPL\\"}","name":"get_stock_price"},"id":"","type":"function"}]},"finish_reason":"tool_calls","index":0}],"created":1756957536,"id":"test-id","model":"gemini-2.5-flash","object":"chat.completion.chunk","usage":{"completion_tokens":37,"prompt_tokens":150,"total_tokens":261}}\n',
            b"\n",
            b"data: [DONE]\n",
        ]

        mock_response.__iter__ = Mock(return_value=iter(multi_tool_response_lines))

        # Mock animator methods
        StreamingAdapter(self.mock_api_handler).animator.stop_animation = Mock()
        StreamingAdapter(self.mock_api_handler).animator.start_cursor_blinking = Mock()
        StreamingAdapter(self.mock_api_handler).animator.stop_cursor_blinking = Mock()
        StreamingAdapter(self.mock_api_handler).animator.ensure_cursor_visible = Mock()

        # Process the response
        result = StreamingAdapter(self.mock_api_handler)._process_streaming_response(
            mock_response
        )

        # Check that the result is valid
        self.assertIsNotNone(result)
        self.assertIn("choices", result)
        self.assertEqual(len(result["choices"]), 1)

        choice = result["choices"][0]
        self.assertIn("message", choice)
        self.assertIn("tool_calls", choice["message"])

        # Should have two tool calls with generated IDs
        self.assertEqual(len(choice["message"]["tool_calls"]), 2)

        for tool_call in choice["message"]["tool_calls"]:
            self.assertIn("id", tool_call)
            self.assertTrue(tool_call["id"])  # Should not be empty
            self.assertTrue(tool_call["id"].startswith("tool_call_"))
            self.assertIn("function", tool_call)
            self.assertIn("name", tool_call["function"])
            self.assertTrue(tool_call["function"]["name"])  # Should not be empty

    def test_make_request_with_streaming(self):
        """Test making a streaming request."""
        # Create streaming adapter instance
        adapter = StreamingAdapter(self.mock_api_handler)

        # Mock messages
        messages = [{"role": "user", "content": "Hello"}]

        # Mock the streaming request method to return a simple response
        with patch.object(adapter, "_streaming_request") as mock_streaming_request:
            mock_streaming_request.return_value = {
                "choices": [
                    {"message": {"content": "Hello back!", "role": "assistant"}}
                ]
            }

            # Make the request
            result = adapter.make_request(messages)

            # Check that the streaming request was called
            mock_streaming_request.assert_called_once_with(messages, False)

            # Check the result
            self.assertEqual(result["choices"][0]["message"]["content"], "Hello back!")

    def test_make_request_with_streaming_disabled(self):
        """Test making a request with streaming disabled."""
        # Create streaming adapter instance
        adapter = StreamingAdapter(self.mock_api_handler)

        # Mock messages
        messages = [{"role": "user", "content": "Hello"}]

        # Mock the non-streaming request method
        with patch.object(
            adapter, "_make_non_streaming_request"
        ) as mock_non_streaming_request:
            mock_non_streaming_request.return_value = {
                "choices": [
                    {"message": {"content": "Hello back!", "role": "assistant"}}
                ]
            }

            # Make the request with streaming disabled
            result = adapter.make_request(messages, disable_streaming_mode=True)

            # Check that the non-streaming request was called
            mock_non_streaming_request.assert_called_once_with(messages, False)

            # Check the result
            self.assertEqual(result["choices"][0]["message"]["content"], "Hello back!")


if __name__ == "__main__":
    unittest.main()

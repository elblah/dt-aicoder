#!/usr/bin/env python3
"""
Test script for context summary functionality with compaction
"""

import sys
import os
from unittest.mock import Mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aicoder.message_history import MessageHistory
from aicoder.config import COMPACT_MIN_MESSAGES, COMPACT_RECENT_MESSAGES


def test_context_summary_compact():
    """Test the context summary functionality with enough messages to trigger compaction"""
    # Create a message history instance with mock API handler
    mock_api_handler = Mock()
    mock_api_handler._make_api_request.return_value = {
        "choices": [
            {
                "message": {
                    "content": "Test summary for integration test"
                }
            }
        ]
    }
    
    history = MessageHistory()
    history.api_handler = mock_api_handler

    # Temporarily reduce the compaction thresholds for testing
    original_min = COMPACT_MIN_MESSAGES
    original_recent = COMPACT_RECENT_MESSAGES

    # For testing purposes, we'll modify the thresholds directly
    import aicoder.config

    aicoder.config.COMPACT_MIN_MESSAGES = 5
    aicoder.config.COMPACT_RECENT_MESSAGES = 3

    try:
        # Add multiple test messages to trigger compaction
        history.add_user_message("Hello, can you help me with a task?")

        # Add an assistant message with tool calls
        assistant_msg = {
            "role": "assistant",
            "content": "I'll help you with that task. Let me check the files first.",
            "tool_calls": [
                {
                    "id": "call_12345",
                    "type": "function",
                    "function": {
                        "name": "list_directory",
                        "arguments": '{"path": "."}',
                    },
                }
            ],
        }
        history.add_assistant_message(assistant_msg)

        # Add a tool result
        tool_result = {
            "role": "tool",
            "tool_call_id": "call_12345",
            "content": "Found 10 files in the directory",
        }
        history.add_tool_results([tool_result])

        # Add several more message pairs to reach the threshold
        for i in range(10):
            # Add user message
            history.add_user_message(f"User message {i}")

            # Add assistant message with tool calls
            assistant_msg = {
                "role": "assistant",
                "content": f"Assistant response {i}",
                "tool_calls": [
                    {
                        "id": f"call_{i}",
                        "type": "function",
                        "function": {
                            "name": "list_directory",
                            "arguments": '{"path": "."}',
                        },
                    }
                ],
            }
            history.add_assistant_message(assistant_msg)

            # Add tool result
            tool_result = {
                "role": "tool",
                "tool_call_id": f"call_{i}",
                "content": f"Tool result {i}",
            }
            history.add_tool_results([tool_result])

        print(f"Message count before summary: {len(history.messages)}")

        # Test the summarize_context method
        history.summarize_context()

        print(f"Message count after summary: {len(history.messages)}")

        # Print the messages to verify they're properly formatted
        for i, msg in enumerate(history.messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if len(content) > 50:
                content = content[:50] + "..."
            print(f"Message {i}: {role} - {content}")

        print("Test completed successfully!")

    finally:
        # Restore original thresholds
        aicoder.config.COMPACT_MIN_MESSAGES = original_min
        aicoder.config.COMPACT_RECENT_MESSAGES = original_recent


if __name__ == "__main__":
    test_context_summary_compact()

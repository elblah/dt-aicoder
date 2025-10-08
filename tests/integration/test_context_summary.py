#!/usr/bin/env python3
"""
Test script for context summary functionality
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from aicoder.message_history import MessageHistory


def test_context_summary():
    """Test the context summary functionality"""
    # Create a message history instance
    history = MessageHistory()

    # Add a mock API handler
    from unittest.mock import Mock
    history.api_handler = Mock()
    history.api_handler._make_api_request = Mock(return_value={
        "choices": [{"message": {"content": "Test summary of the conversation"}}]
    })

    # Set low thresholds to trigger compaction
    import aicoder.config as config
    config.COMPACT_MIN_MESSAGES = 4
    config.AUTO_COMPACT_THRESHOLD = 1000
    config.COMPACT_RECENT_MESSAGES = 2

    # Add enough messages to have some that can be compacted
    # First, add some older messages that will be compacted
    history.add_user_message("Initial request: help with task 1")
    history.add_assistant_message({"role": "assistant", "content": "I'll help with task 1"})
    history.add_tool_results([{"role": "tool", "tool_call_id": "call_1", "content": "Result for task 1"}])
    
    history.add_user_message("Request for task 2")
    history.add_assistant_message({"role": "assistant", "content": "Working on task 2"})
    history.add_tool_results([{"role": "tool", "tool_call_id": "call_2", "content": "Result for task 2"}])

    # Add recent messages that will be preserved
    history.add_user_message("Hello, can you help me with a task?")

    # Add an assistant message with tool calls
    assistant_msg = {
        "role": "assistant",
        "content": "I'll help you with that task. Let me check the files first.",
        "tool_calls": [
            {
                "id": "call_12345",
                "type": "function",
                "function": {"name": "list_directory", "arguments": '{"path": "."}'},
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

    # Add another assistant message
    history.add_assistant_message(
        {
            "role": "assistant",
            "content": "I found 10 files in the directory. What would you like to do next?",
        }
    )

    print(f"Message count before summary: {len(history.messages)}")

    # Test the summarize_context method
    history.summarize_context()

    print(f"Message count after summary: {len(history.messages)}")

    # Print the messages to verify they're properly formatted
    for i, msg in enumerate(history.messages):
        print(
            f"Message {i}: {msg.get('role', 'unknown')} - {msg.get('content', '')[:50]}..."
        )

    print("Test completed successfully!")


if __name__ == "__main__":
    test_context_summary()

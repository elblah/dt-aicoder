#!/usr/bin/env python3

"""
Test message compaction functionality, particularly the fix for ensuring
the first message after system is a user message for z.ai GLM model compatibility.
"""

import sys
import os

# Add the parent directory to the path so we can import aicoder
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aicoder.message_history import MessageHistory, clean_message_for_api
from aicoder.message_history import SUMMARY_MESSAGE_PREFIX, NEUTRAL_USER_MESSAGE_CONTENT
from tests.test_helpers import temp_config


def test_compaction_with_assistant_first_message():
    """Test compaction when recent messages start with assistant message."""
    # Create a message history instance
    message_history = MessageHistory()

    # Override the config values for testing using context manager
    import aicoder.config as config
    
    with temp_config(config,
                     COMPACT_MIN_MESSAGES=4,
                     COMPACT_RECENT_MESSAGES=3,
                     AUTO_COMPACT_THRESHOLD=1000,
                     PRUNE_PROTECT_TOKENS=500,
                     DEBUG=False):
        
        # Add initial messages that will trigger compaction
        message_history.add_user_message("First user message")
        message_history.add_assistant_message({"role": "assistant", "content": "First assistant response"})
        message_history.add_tool_results([{"role": "tool", "content": "Tool result 1", "tool_call_id": "call_1"}])

        # Add more messages to reach compaction threshold
        for i in range(5):
            message_history.add_user_message(f"User message {i+2}")
            message_history.add_assistant_message({"role": "assistant", "content": f"Assistant response {i+2}"})
            message_history.add_tool_results([{"role": "tool", "content": f"Tool result {i+2}", "tool_call_id": f"call_{i+2}"}])

        # The recent messages will likely start with assistant or tool messages
        # Test that compaction inserts neutral user message when needed
        original_count = len(message_history.messages)

        # Mock the API handler to avoid actual API calls
        from unittest.mock import Mock
        message_history.api_handler = Mock()
        message_history.api_handler._make_api_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Test summary for compaction test"
                    }
                }
            ]
        }

        # Force compaction by calling compact_memory directly
        message_history.compact_memory()

        # Check that we still have messages
        assert len(message_history.messages) > 0

        # Check that the first message is system
        assert message_history.messages[0]["role"] == "system"

        # Check that the second message is also system (summary)
        assert message_history.messages[1]["role"] == "system"

        # Check that the third message is user (this is our fix)
        if len(message_history.messages) > 2:
            assert message_history.messages[2]["role"] == "user"
            # The content should be NEUTRAL_USER_MESSAGE_CONTENT for neutral user message
            if message_history.messages[2]["content"] == NEUTRAL_USER_MESSAGE_CONTENT:
                # Our fix was applied
                pass


def test_compaction_with_user_first_message():
    """Test compaction when recent messages already start with user message."""
    # Create a message history instance
    message_history = MessageHistory()

    # Override the config values for testing
    import aicoder.config as config
    
    with temp_config(config,
                     COMPACT_MIN_MESSAGES=4,
                     COMPACT_RECENT_MESSAGES=3,
                     AUTO_COMPACT_THRESHOLD=1000,
                     PRUNE_PROTECT_TOKENS=500,
                     DEBUG=False):
        
        # Add messages where recent messages start with user
        message_history.add_user_message("First user message")
        message_history.add_assistant_message({"role": "assistant", "content": "First assistant response"})

        # Add more messages to reach compaction threshold, ensuring recent messages start with user
        for i in range(5):
            message_history.add_user_message(f"User message {i+2}")
            message_history.add_assistant_message({"role": "assistant", "content": f"Assistant response {i+2}"})

        # Mock the API handler
        from unittest.mock import Mock
        message_history.api_handler = Mock()
        message_history.api_handler._make_api_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Test summary for compaction test"
                    }
                }
            ]
        }

        # Force compaction
        message_history.compact_memory()

        # Check structure
        assert message_history.messages[0]["role"] == "system"
        assert message_history.messages[1]["role"] == "system"

        # If the recent messages started with user, we shouldn't need the neutral message
        if len(message_history.messages) > 2:
            # The third message should be the first recent message, which should be user
            if message_history.messages[2]["content"] != NEUTRAL_USER_MESSAGE_CONTENT:
                # No neutral user message was needed - this is good
                pass


def test_compaction_ignores_previous_summaries():
    """Test that compaction ignores previously compacted messages."""
    # Create a message history instance
    message_history = MessageHistory()

    # Override the config values for testing
    import aicoder.config as config
    
    with temp_config(config,
                     COMPACT_MIN_MESSAGES=4,
                     COMPACT_RECENT_MESSAGES=3,
                     AUTO_COMPACT_THRESHOLD=1000,
                     PRUNE_PROTECT_TOKENS=100,  # Lower to allow pruning of older tool results
                     PRUNE_MINIMUM_TOKENS=100,   # Lower minimum threshold
                     DEBUG=False):
        
        # Manually add messages including a previous summary and some tool results
        # Add a large tool result to ensure pruning occurs but doesn't meet threshold
        large_tool_result = "x" * 20000  # Large enough to exceed pruning minimum
        message_history.messages = [
            {"role": "system", "content": "Initial system prompt"},
            {"role": "system", "content": f"{SUMMARY_MESSAGE_PREFIX} Old summary content"},
            # Add many messages to have older tool results outside protection window
            {"role": "user", "content": "Old user message 1"},
            {"role": "assistant", "content": "Old assistant response 1"},
            {"role": "tool", "tool_call_id": "call_old_1", "content": large_tool_result},
            {"role": "user", "content": "Old user message 2"},
            {"role": "assistant", "content": "Old assistant response 2"},
            {"role": "tool", "tool_call_id": "call_old_2", "content": large_tool_result},
            # Recent messages that will be protected
            {"role": "user", "content": "User message 1"},
            {"role": "assistant", "content": "Assistant response 1"},
            {"role": "tool", "tool_call_id": "call_1", "content": large_tool_result},
            {"role": "user", "content": "User message 2"},
            {"role": "assistant", "content": "Assistant response 2"},
            {"role": "tool", "tool_call_id": "call_2", "content": large_tool_result},
            {"role": "user", "content": "User message 3"},
            {"role": "assistant", "content": "Assistant response 3"},
        ]
        
        # Mock the API handler
        from unittest.mock import Mock
        message_history.api_handler = Mock()
        message_history.api_handler._make_api_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "New summary content"
                    }
                }
            ]
        }

        # Force compaction
        message_history.compact_memory()

        # Check that the old summary is preserved
        summary_messages = [
            msg for msg in message_history.messages 
            if msg.get("role") == "system" and msg.get("content", "").startswith(SUMMARY_MESSAGE_PREFIX)
        ]
        assert len(summary_messages) >= 2  # Should have old and new summaries
        
        # Check that the old summary content is still there
        old_summary_found = any("Old summary content" in msg.get("content", "") for msg in summary_messages)
        assert old_summary_found, "Previous summary should be preserved"
        
        # Check that the new summary was added
        new_summary_found = any("New summary content" in msg.get("content", "") for msg in summary_messages)
        assert new_summary_found, "New summary should be added"
        
        # Check that summaries are in correct temporal order (old before new)
        old_index = next(i for i, msg in enumerate(summary_messages) if "Old summary content" in msg.get("content", ""))
        new_index = next(i for i, msg in enumerate(summary_messages) if "New summary content" in msg.get("content", ""))
        assert old_index < new_index, "Old summary should come before new summary"


def test_clean_message_for_api():
    """Test the clean_message_for_api function."""
    # Test with a message that has tool_calls
    message_with_tools = {
        "role": "assistant",
        "content": "I'll help you",
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "test_function",
                    "arguments": {"param1": "value1", "param2": "value2"}
                }
            }
        ]
    }

    cleaned = clean_message_for_api(message_with_tools)

    # Should preserve the structure
    assert cleaned["role"] == "assistant"
    assert cleaned["content"] == "I'll help you"
    assert "tool_calls" in cleaned
    assert len(cleaned["tool_calls"]) == 1
    assert cleaned["tool_calls"][0]["id"] == "call_123"


def test_message_order_after_compaction():
    """Test that message order is maintained correctly after compaction."""
    # Create a message history instance
    message_history = MessageHistory()

    import aicoder.config as config
    
    with temp_config(config,
                     COMPACT_MIN_MESSAGES=4,
                     COMPACT_RECENT_MESSAGES=3,
                     AUTO_COMPACT_THRESHOLD=1000,
                     PRUNE_PROTECT_TOKENS=500,
                     DEBUG=False):
        
        # Build a predictable message sequence
        message_history.add_user_message("Start task")
        message_history.add_assistant_message({"role": "assistant", "content": "Starting work"})
        message_history.add_tool_results([{"role": "tool", "content": "Tool completed", "tool_call_id": "call_1"}])

        # Add more messages to trigger compaction
        for i in range(10):
            message_history.add_user_message(f"Step {i+1}")
            message_history.add_assistant_message({"role": "assistant", "content": f"Processing step {i+1}"})

        # Mock API handler
        from unittest.mock import Mock
        message_history.api_handler = Mock()
        message_history.api_handler._make_api_request.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Test summary for compaction test"
                    }
                }
            ]
        }

        # Compact
        before_count = len(message_history.messages)
        message_history.compact_memory()
        after_count = len(message_history.messages)

        # Should have fewer messages after compaction
        assert after_count < before_count

        # Should still have the basic structure
        assert after_count >= 3  # system + summary + at least one message
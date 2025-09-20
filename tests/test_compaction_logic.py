"""
Unit tests for the dynamic message compaction logic.
Tests that compaction works correctly with any number of initial system messages.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import aicoder modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aicoder.message_history import MessageHistory
from aicoder.config import COMPACT_RECENT_MESSAGES, COMPACT_MIN_MESSAGES


class TestCompactionLogic(unittest.TestCase):
    """Test cases for the dynamic message compaction logic."""

    def test_single_system_message(self):
        """Test compaction with a single initial system message (standard case)."""
        mh = MessageHistory()
        self.assertEqual(len(mh.messages), 1)
        self.assertEqual(mh.messages[0]["role"], "system")

        # Add 5 chat messages (should not compact yet)
        mh.add_user_message("User 1")
        mh.add_assistant_message({"role": "assistant", "content": "Assistant 1"})
        mh.add_user_message("User 2")
        mh.add_assistant_message({"role": "assistant", "content": "Assistant 2"})
        mh.add_user_message("User 3")

        first_chat_index = mh._get_first_chat_message_index()
        chat_count = len(mh.messages) - first_chat_index

        self.assertEqual(first_chat_index, 1)  # First chat message at index 1
        self.assertEqual(chat_count, 5)
        self.assertLess(chat_count, COMPACT_MIN_MESSAGES)  # Should not compact

        # Add 6th chat message (should compact now)
        mh.add_assistant_message({"role": "assistant", "content": "Assistant 3"})
        chat_count = len(mh.messages) - first_chat_index

        self.assertEqual(chat_count, 6)
        self.assertGreaterEqual(chat_count, COMPACT_MIN_MESSAGES)  # Should compact

    def test_multiple_system_messages(self):
        """Test compaction with multiple initial system messages (plugin case)."""
        mh = MessageHistory()

        # Add extra system messages at the beginning (simulating plugins)
        mh.messages.insert(1, {"role": "system", "content": "Plugin system message 1"})
        mh.messages.insert(2, {"role": "system", "content": "Plugin system message 2"})

        self.assertEqual(len(mh.messages), 3)

        first_chat_index = mh._get_first_chat_message_index()
        self.assertEqual(first_chat_index, 3)  # First chat would be at index 3

        # Add 5 chat messages
        mh.add_user_message("User 1")
        mh.add_assistant_message({"role": "assistant", "content": "Assistant 1"})
        mh.add_user_message("User 2")
        mh.add_assistant_message({"role": "assistant", "content": "Assistant 2"})
        mh.add_user_message("User 3")

        chat_count = len(mh.messages) - first_chat_index
        self.assertEqual(chat_count, 5)
        self.assertLess(chat_count, COMPACT_MIN_MESSAGES)  # Should not compact

        # Add 6th chat message
        mh.add_assistant_message({"role": "assistant", "content": "Assistant 3"})
        chat_count = len(mh.messages) - first_chat_index

        self.assertEqual(chat_count, 6)
        self.assertGreaterEqual(chat_count, COMPACT_MIN_MESSAGES)  # Should compact

    def test_preserved_messages_logic(self):
        """Test that _get_preserved_recent_messages works correctly."""
        mh = MessageHistory()

        # Add extra system messages
        mh.messages.insert(1, {"role": "system", "content": "Plugin message"})

        # Add exactly COMPACT_RECENT_MESSAGES chat messages
        for i in range(COMPACT_RECENT_MESSAGES):
            mh.add_user_message(f"User {i + 1}")

        first_chat_index = mh._get_first_chat_message_index()
        chat_count = len(mh.messages) - first_chat_index

        # Should preserve all chat messages since we have exactly COMPACT_RECENT_MESSAGES
        preserved = mh._get_preserved_recent_messages()
        self.assertEqual(len(preserved), chat_count)

        # Add one more chat message
        mh.add_user_message("Extra user message")
        chat_count = len(mh.messages) - first_chat_index

        # Should now preserve only COMPACT_RECENT_MESSAGES messages
        preserved = mh._get_preserved_recent_messages()
        self.assertEqual(len(preserved), COMPACT_RECENT_MESSAGES)

    def test_edge_cases(self):
        """Test edge cases."""
        # Test with only system messages
        mh = MessageHistory()
        mh.messages.extend(
            [
                {"role": "system", "content": "Extra system 1"},
                {"role": "system", "content": "Extra system 2"},
            ]
        )

        first_chat_index = mh._get_first_chat_message_index()
        self.assertEqual(first_chat_index, len(mh.messages))  # No chat messages

        chat_count = len(mh.messages) - first_chat_index
        self.assertEqual(chat_count, 0)

        preserved = mh._get_preserved_recent_messages()
        self.assertEqual(len(preserved), 0)  # No chat messages to preserve

    def test_compaction_decision(self):
        """Test that compaction decision is made correctly based on chat messages only."""
        mh = MessageHistory()

        # Add many system messages
        for i in range(10):
            mh.messages.insert(1, {"role": "system", "content": f"System message {i}"})

        # Add exactly COMPACT_MIN_MESSAGES - 1 chat messages (should not compact)
        for i in range(COMPACT_MIN_MESSAGES - 1):
            mh.add_user_message(f"User message {i}")

        first_chat_index = mh._get_first_chat_message_index()
        chat_count = len(mh.messages) - first_chat_index

        self.assertEqual(chat_count, COMPACT_MIN_MESSAGES - 1)
        self.assertLess(chat_count, COMPACT_MIN_MESSAGES)  # Should not compact

        # Add one more chat message (should compact now)
        mh.add_user_message("Final user message")
        chat_count = len(mh.messages) - first_chat_index

        self.assertEqual(chat_count, COMPACT_MIN_MESSAGES)
        self.assertGreaterEqual(chat_count, COMPACT_MIN_MESSAGES)  # Should compact


if __name__ == "__main__":
    unittest.main()

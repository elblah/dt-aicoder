"""
Test enhanced compact command functionality.
"""

import unittest
from unittest.mock import Mock, patch
from aicoder.commands.compact_command import CompactCommand
from aicoder.message_history import MessageHistory, NoMessagesToCompactError
from aicoder.stats import Stats


class TestEnhancedCompactCommand(unittest.TestCase):
    """Test the enhanced compact command functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = Mock()
        self.app.message_history = Mock(spec=MessageHistory)
        self.app.message_history.stats = Mock(spec=Stats)
        self.app.message_history.api_handler = Mock()
        self.app.message_history.api_handler.stats = Mock(spec=Stats)
        # Set up proper return values for mocked attributes
        self.app.message_history.api_handler.stats.current_prompt_size = (
            100000  # High enough to trigger compaction
        )
        # Add the messages attribute that the new code needs
        self.app.message_history.messages = [1, 2, 3, 4, 5]  # Some messages
        self.app.message_history._compaction_performed = False
        # Mock get_round_count to return 0 rounds
        self.app.message_history.get_round_count.return_value = 5

        self.command = CompactCommand(self.app)

    def test_no_args_tries_auto_compact(self):
        """Test that no arguments triggers auto-compaction attempt."""
        # Mock high token usage to trigger compaction
        self.app.message_history.api_handler = Mock()
        self.app.message_history.api_handler.stats = Mock()
        self.app.message_history.api_handler.stats.current_prompt_size = 200000

        self.app.message_history.compact_memory.return_value = None
        self.app.message_history._compaction_performed = (
            True  # Simulate successful compaction
        )

        result = self.command.execute([])

        self.app.message_history.compact_memory.assert_called_once()
        self.assertEqual(result, (False, False))

    def test_auto_compact_with_no_messages_error(self):
        """Test auto-compaction when no messages available."""
        self.app.message_history.compact_memory.side_effect = NoMessagesToCompactError(
            "No messages"
        )
        self.app.message_history.get_round_count.return_value = 0

        with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
            result = self.command.execute([])

            # Should show enhanced feedback
            mock_wmsg.assert_called()
            self.assertEqual(result, (False, False))

    def test_auto_disable(self):
        """Test auto compaction disable."""
        with patch("os.environ", {}):
            with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
                result = self.command.execute(["auto", "disable"])
                self.assertEqual(result, (False, False))
                mock_wmsg.assert_called()

    def test_auto_enable(self):
        """Test auto compaction enable."""
        with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
            result = self.command.execute(["auto", "enable"])
            self.assertEqual(result, (False, False))
            mock_wmsg.assert_called()

    def test_auto_status(self):
        """Test auto compaction status."""
        with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
            result = self.command.execute(["auto", "status"])
            self.assertEqual(result, (False, False))
            mock_wmsg.assert_called()

    def test_force_compact_default_one_round(self):
        """Test force compaction with default 1 round."""
        self.app.message_history.compact_rounds.return_value = [{"user": "test"}]
        self.app.message_history.get_round_count.return_value = 2

        with patch("aicoder.commands.compact_command.imsg") as mock_imsg:
            result = self.command.execute(["force"])
            self.assertEqual(result, (False, False))
            self.app.message_history.compact_rounds.assert_called_once_with(1)
            mock_imsg.assert_called()

    def test_force_compact_specific_number(self):
        """Test force compaction with specific number."""
        self.app.message_history.compact_rounds.return_value = [
            {"user": "test"},
            {"user": "test2"},
        ]
        self.app.message_history.get_round_count.return_value = 3

        with patch("aicoder.commands.compact_command.imsg") as mock_imsg:
            result = self.command.execute(["force", "2"])
            self.assertEqual(result, (False, False))
            self.app.message_history.compact_rounds.assert_called_once_with(2)
            mock_imsg.assert_called()

    def test_force_compact_invalid_number(self):
        """Test force compaction with invalid number."""
        with patch("aicoder.commands.compact_command.emsg") as mock_emsg:
            result = self.command.execute(["force", "0"])
            self.assertEqual(result, (False, False))
            mock_emsg.assert_called()

    def test_force_compact_no_rounds_available(self):
        """Test force compaction when no rounds available."""
        self.app.message_history.compact_rounds.side_effect = NoMessagesToCompactError(
            "No messages"
        )

        with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
            result = self.command.execute(["force"])
            self.assertEqual(result, (False, False))
            mock_wmsg.assert_called()

    def test_stats_command(self):
        """Test stats command."""
        with patch("aicoder.commands.compact_command.imsg") as mock_imsg:
            with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
                result = self.command.execute(["stats"])
                self.assertEqual(result, (False, False))
                mock_imsg.assert_called()
                mock_wmsg.assert_called()

    def test_help_command(self):
        """Test help command."""
        with patch("aicoder.commands.compact_command.imsg") as mock_imsg:
            with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
                result = self.command.execute(["help"])
                self.assertEqual(result, (False, False))
                mock_imsg.assert_called()
                mock_wmsg.assert_called()

    def test_unknown_subcommand(self):
        """Test unknown subcommand."""
        with patch("aicoder.commands.compact_command.emsg") as mock_emsg:
            with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
                result = self.command.execute(["unknown"])
                self.assertEqual(result, (False, False))
                mock_emsg.assert_called()
                mock_wmsg.assert_called()

    def test_unknown_auto_action(self):
        """Test unknown auto action."""
        with patch("aicoder.commands.compact_command.emsg") as mock_emsg:
            with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
                result = self.command.execute(["auto", "unknown"])
                self.assertEqual(result, (False, False))
                mock_emsg.assert_called()
                mock_wmsg.assert_called()


class TestRoundDetection(unittest.TestCase):
    """Test round detection functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.message_history = MessageHistory()
        # Add mock API handler for compaction tests
        self.message_history.api_handler = Mock()
        self.message_history.api_handler.summarize_conversation = Mock(
            return_value="Summary of old messages"
        )

    def test_identify_conversation_rounds(self):
        """Test basic round detection."""
        # Add a simple conversation: user1 -> asst1 -> user2 -> asst2
        self.message_history.add_user_message("Hello")
        self.message_history.add_assistant_message(
            {"role": "assistant", "content": "Hi there!"}
        )
        self.message_history.add_user_message("How are you?")
        self.message_history.add_assistant_message(
            {"role": "assistant", "content": "I'm good!"}
        )

        rounds = self.message_history.identify_conversation_rounds()
        self.assertEqual(len(rounds), 2)

        # Check first round
        self.assertEqual(rounds[0]["message_count"], 2)
        self.assertEqual(rounds[0]["messages"][0]["content"], "Hello")
        self.assertEqual(rounds[0]["messages"][1]["content"], "Hi there!")

        # Check second round
        self.assertEqual(rounds[1]["message_count"], 2)
        self.assertEqual(rounds[1]["messages"][0]["content"], "How are you?")
        self.assertEqual(rounds[1]["messages"][1]["content"], "I'm good!")

    def test_round_detection_with_tool_calls(self):
        """Test round detection with tool calls."""
        self.message_history.add_user_message("Call a tool")
        # Simulate assistant message with tool call
        self.message_history.messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "tool1", "type": "function"}],
            }
        )
        self.message_history.messages.append(
            {"role": "tool", "content": "Tool result", "tool_call_id": "tool1"}
        )
        self.message_history.add_assistant_message(
            {"role": "assistant", "content": "Tool completed"}
        )

        rounds = self.message_history.identify_conversation_rounds()
        self.assertEqual(len(rounds), 1)
        # Should include user, assistant tool call, tool response, and final assistant message
        self.assertEqual(rounds[0]["message_count"], 4)

    def test_get_round_count(self):
        """Test getting round count."""
        self.message_history.add_user_message("Hello")
        self.message_history.add_assistant_message(
            {"role": "assistant", "content": "Hi!"}
        )

        round_count = self.message_history.get_round_count()
        self.assertEqual(round_count, 1)

    def test_compact_rounds_no_rounds(self):
        """Test compacting rounds when none available."""
        with self.assertRaises(NoMessagesToCompactError):
            self.message_history.compact_rounds()

    def test_compact_rounds_success(self):
        """Test successful round compaction."""
        # Add conversation with enough rounds to compact
        self.message_history.add_user_message("Hello")
        self.message_history.add_assistant_message(
            {"role": "assistant", "content": "Hi there!"}
        )
        self.message_history.add_user_message("Question")
        self.message_history.add_assistant_message(
            {"role": "assistant", "content": "Answer"}
        )

        # Mock the API handler to return a proper response
        self.message_history.api_handler._make_api_request.return_value = {
            "choices": [{"message": {"content": "Summary of old messages"}}]
        }

        compacted_rounds = self.message_history.compact_rounds(1)

        # Should have compacted the oldest round
        self.assertEqual(len(compacted_rounds), 1)
        # compacted_rounds returns round dicts, check that it has the expected structure
        self.assertIn("messages", compacted_rounds[0])
        self.assertEqual(compacted_rounds[0]["messages"][0]["content"], "Hello")


if __name__ == "__main__":
    unittest.main()

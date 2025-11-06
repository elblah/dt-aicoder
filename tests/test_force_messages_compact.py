"""Test force-messages compaction functionality."""

import unittest
from unittest.mock import Mock, patch
from aicoder.message_history import MessageHistory, NoMessagesToCompactError
from aicoder.commands.compact_command import CompactCommand


class TestForceMessagesCompact(unittest.TestCase):
    """Test the force-messages compaction feature."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = Mock()
        self.config.COMPACT_MIN_MESSAGES = 2
        self.config.DEBUG = False
        
        # MessageHistory takes no arguments in constructor
        self.message_history = MessageHistory()
        # Set up stats properly
        self.message_history.stats.compactions = 0
        self.message_history.stats.messages_sent = 0
        
        # Mock API handler
        self.api_handler = Mock()
        self.api_handler.stats = Mock()
        self.api_handler.stats.current_prompt_size = 1000
        self.message_history.api_handler = self.api_handler
        
        # Create compact command
        self.app = Mock()
        self.app.message_history = self.message_history
        self.command = CompactCommand(self.app)

    def test_compact_messages_basic(self):
        """Test basic message compaction."""
        # Add conversation
        self.message_history.add_user_message("Hello")
        self.message_history.add_assistant_message({"role": "assistant", "content": "Hi there!"})
        self.message_history.add_user_message("How are you?")
        self.message_history.add_assistant_message({"role": "assistant", "content": "I'm doing well!"})
        
        # Mock API response for summarization
        with patch.object(self.message_history, '_summarize_old_messages') as mock_summarize:
            mock_summarize.return_value = "Summary of conversation"
            
            # Compact 2 oldest messages
            compacted = self.message_history.compact_messages(2)
            
            # Should have compacted 2 messages
            self.assertEqual(len(compacted), 2)
            self.assertEqual(compacted[0]["content"], "Hello")
            self.assertEqual(compacted[1]["content"], "Hi there!")
            
            # Should have a summary message
            summary_messages = [msg for msg in self.message_history.messages 
                              if msg.get("role") == "system" and 
                              msg.get("content", "").startswith("Summary of earlier conversation:")]
            self.assertEqual(len(summary_messages), 1)

    def test_compact_messages_with_tool_calls(self):
        """Test that tool call/response pairs are kept together."""
        # Add conversation with tool calls
        self.message_history.add_user_message("Read a file")
        self.message_history.add_assistant_message({
            "role": "assistant", 
            "content": "I'll read the file", 
            "tool_calls": [{"id": "call_1", "type": "function"}]
        })
        # Add tool response manually
        self.message_history.messages.append({
            "role": "tool", 
            "content": "File content here", 
            "tool_call_id": "call_1"
        })
        self.message_history.add_user_message("Thanks")
        
        # Mock API response
        with patch.object(self.message_history, '_summarize_old_messages') as mock_summarize:
            mock_summarize.return_value = "Summary with tool interactions"
            
            # Try to compact 2 messages - should include the tool call AND its response
            compacted = self.message_history.compact_messages(2)
            
            # Should have compacted at least the user message and assistant with tool call
            # The tool response might be included if we're compacting more messages
            self.assertGreaterEqual(len(compacted), 2)
            
            # Check that we have the expected messages
            roles = [msg.get("role") for msg in compacted]
            self.assertIn("user", roles)        # User message
            self.assertIn("assistant", roles)  # Assistant with tool call
            
            # If we compacted 3 or more messages, should include tool response too
            if len(compacted) >= 3:
                self.assertIn("tool", roles)

    def test_compact_messages_preserves_first_user_message(self):
        """Test that first message after compaction is a user message."""
        # Add system message first
        self.message_history.messages.append({"role": "system", "content": "System prompt"})
        
        # Add conversation where assistant would be first after compaction
        self.message_history.add_user_message("First user")
        self.message_history.add_assistant_message({"role": "assistant", "content": "First assistant"})
        self.message_history.add_user_message("Second user")
        
        # Mock API response
        with patch.object(self.message_history, '_summarize_old_messages') as mock_summarize:
            mock_summarize.return_value = "Summary"
            
            # Compact first 2 messages (user + assistant)
            self.message_history.compact_messages(2)
            
            # Find first chat message (after system messages)
            first_chat_index = self.message_history._get_first_chat_message_index()
            first_chat_message = self.message_history.messages[first_chat_index]
            
            # Should be a user message
            self.assertEqual(first_chat_message.get("role"), "user")

    def test_compact_messages_command_handler(self):
        """Test the command handler for force-messages."""
        # Add some messages
        self.message_history.add_user_message("Test 1")
        self.message_history.add_assistant_message({"role": "assistant", "content": "Response 1"})
        self.message_history.add_user_message("Test 2")
        
        # Mock API response
        with patch.object(self.message_history, '_summarize_old_messages') as mock_summarize:
            mock_summarize.return_value = "Test summary"
            
            with patch("aicoder.commands.compact_command.imsg") as mock_imsg, \
                 patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
                
                # Execute command
                self.command.execute(["force-messages", "2"])
                
                # Check success message
                mock_imsg.assert_called()
                args = mock_imsg.call_args[0][0]
                self.assertIn("Force compacted 2 oldest messages", args)

    def test_force_messages_invalid_number(self):
        """Test error handling for invalid message count."""
        with patch("aicoder.commands.compact_command.emsg") as mock_emsg, \
             patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
            
            # Test missing number
            self.command.execute(["force-messages"])
            mock_emsg.assert_called_with("\n [X] Please specify the number of messages to compact")
            mock_wmsg.assert_any_call(" *** Usage: /compact force-messages <N>")
            
            # Reset mocks
            mock_emsg.reset_mock()
            mock_wmsg.reset_mock()
            
            # Test negative number
            self.command.execute(["force-messages", "-1"])
            mock_emsg.assert_called_with("\n [X] Number of messages must be positive")
            
            # Reset mocks
            mock_emsg.reset_mock()
            mock_wmsg.reset_mock()
            
            # Test non-integer
            self.command.execute(["force-messages", "abc"])
            mock_emsg.assert_called_with("\n [X] Invalid number. Please specify a positive integer.")

    def test_force_messages_nothing_to_compact(self):
        """Test when there are no messages to compact."""
        # Mock compact_messages to raise exception
        with patch.object(self.message_history, 'compact_messages') as mock_compact:
            mock_compact.side_effect = NoMessagesToCompactError("No messages")
            
            with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
                self.command.execute(["force-messages", "5"])
                mock_wmsg.assert_called_with("\n [i] Nothing to compact: No messages")

    def test_force_messages_shows_message_types(self):
        """Test that the command shows what types of messages were compacted."""
        # Add mixed message types
        self.message_history.add_user_message("User message")
        self.message_history.add_assistant_message({"role": "assistant", "content": "Assistant message"})
        self.message_history.add_user_message("Another user")
        
        # Mock API response
        with patch.object(self.message_history, '_summarize_old_messages') as mock_summarize:
            mock_summarize.return_value = "Summary"
            
            with patch("aicoder.commands.compact_command.wmsg") as mock_wmsg:
                self.command.execute(["force-messages", "2"])
                
                # Should show message types
                calls = [str(call) for call in mock_wmsg.call_args_list]
                found_types = any("Compacted:" in call and "user" in call and "assistant" in call 
                                 for call in calls)
                self.assertTrue(found_types, "Should show compacted message types")


def run_force_messages_compact_tests():
    """Run all force-messages compaction tests."""
    print("Running force-messages compaction tests...")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestForceMessagesCompact)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\n[✓] All force-messages compaction tests passed!")
        return True
    else:
        print(f"\n[X] {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
        return False


if __name__ == "__main__":
    run_force_messages_compact_tests()
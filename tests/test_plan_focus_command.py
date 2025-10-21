"""
Tests for the /plan focus command functionality.
"""

import unittest
from unittest.mock import Mock, patch

from aicoder.commands.plan_command import PlanCommand
from aicoder.message_history import MessageHistory


class TestPlanFocusCommand(unittest.TestCase):
    """Test cases for the /plan focus command."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_app = Mock()
        self.mock_app.message_history = MessageHistory()
        self.plan_command = PlanCommand(self.mock_app)

    def test_handle_focus_command_with_assistant_message(self):
        """Test focus command when assistant message exists."""
        # Add some messages to simulate a conversation
        self.mock_app.message_history.add_user_message("Hello")
        self.mock_app.message_history.add_assistant_message({
            "role": "assistant", 
            "content": "Here's a detailed plan:\n1. Step 1\n2. Step 2\n3. Step 3"
        })
        self.mock_app.message_history.add_user_message("Great!")
        
        original_message_count = len(self.mock_app.message_history.messages)
        
        # Execute focus command
        result = self.plan_command._handle_focus_command()
        
        # Verify results
        self.assertFalse(result[0])  # Should not exit
        self.assertFalse(result[1])  # Should not break
        
        # Should have new session with system + focused message
        self.assertEqual(len(self.mock_app.message_history.messages), 2)
        
        # Last message should be user message with assistant content
        last_message = self.mock_app.message_history.messages[-1]
        self.assertEqual(last_message["role"], "user")
        self.assertIn("Here's a detailed plan:", last_message["content"])
        self.assertIn("1. Step 1", last_message["content"])

    def test_handle_focus_command_no_assistant_message(self):
        """Test focus command when no assistant message exists."""
        # Add only user messages
        self.mock_app.message_history.add_user_message("Hello")
        self.mock_app.message_history.add_user_message("Another message")
        
        original_message_count = len(self.mock_app.message_history.messages)
        
        # Execute focus command
        result = self.plan_command._handle_focus_command()
        
        # Verify results
        self.assertFalse(result[0])  # Should not exit
        self.assertFalse(result[1])  # Should not break
        
        # Session should remain unchanged
        self.assertEqual(len(self.mock_app.message_history.messages), original_message_count)

    def test_get_last_assistant_message_found(self):
        """Test getting last assistant message when it exists."""
        # Add messages
        self.mock_app.message_history.add_user_message("User 1")
        self.mock_app.message_history.add_assistant_message({
            "role": "assistant", 
            "content": "Assistant 1"
        })
        self.mock_app.message_history.add_user_message("User 2")
        self.mock_app.message_history.add_assistant_message({
            "role": "assistant", 
            "content": "Assistant 2 (last)"
        })
        
        # Get last assistant message
        last_message = self.plan_command._get_last_assistant_message()
        
        # Should return the last assistant message
        self.assertIsNotNone(last_message)
        self.assertEqual(last_message["role"], "assistant")
        self.assertEqual(last_message["content"], "Assistant 2 (last)")

    def test_get_last_assistant_message_not_found(self):
        """Test getting last assistant message when none exists."""
        # Add only user messages
        self.mock_app.message_history.add_user_message("User 1")
        self.mock_app.message_history.add_user_message("User 2")
        
        # Get last assistant message
        last_message = self.plan_command._get_last_assistant_message()
        
        # Should return None
        self.assertIsNone(last_message)

    def test_handle_focus_command_empty_assistant_content(self):
        """Test focus command when assistant message has empty content."""
        # Add assistant message with empty content
        self.mock_app.message_history.add_user_message("Hello")
        self.mock_app.message_history.add_assistant_message({
            "role": "assistant", 
            "content": ""
        })
        
        # Execute focus command
        result = self.plan_command._handle_focus_command()
        
        # Should still work with placeholder content
        self.assertEqual(len(self.mock_app.message_history.messages), 2)
        last_message = self.mock_app.message_history.messages[-1]
        self.assertEqual(last_message["role"], "user")
        self.assertEqual(last_message["content"], "Focus on previous assistant response")

    @patch('aicoder.utils.imsg')
    @patch('aicoder.utils.emsg')
    def test_handle_focus_command_messages(self, mock_emsg, mock_imsg):
        """Test that appropriate messages are displayed."""
        # Test with no assistant message
        result = self.plan_command._handle_focus_command()
        
        # Should show error message
        mock_emsg.assert_called_with(
            "\n*** No assistant message found to focus on. Make sure you have received a response from the AI first."
        )
        
        # Reset mocks
        mock_emsg.reset_mock()
        mock_imsg.reset_mock()
        
        # Test with assistant message
        self.mock_app.message_history.add_assistant_message({
            "role": "assistant", 
            "content": "Test message content"
        })
        
        result = self.plan_command._handle_focus_command()
        
        # Should show success messages
        mock_imsg.assert_any_call("\n*** New session created...")
        mock_imsg.assert_any_call(
            "*** Focused on previous assistant message: Test message content"
        )

    @patch('builtins.print')
    def test_handle_help_command(self, mock_print):
        """Test the help command displays correctly."""
        # Execute help command
        result = self.plan_command._handle_help_command()
        
        # Should not exit or break
        self.assertFalse(result[0])
        self.assertFalse(result[1])
        
        # Should have printed help content
        mock_print.assert_called()
        
        # Check that key help sections are included
        print_calls = [str(call) for call in mock_print.call_args_list]
        help_text = ' '.join(print_calls)
        
        self.assertIn("Planning Mode Commands", help_text)
        self.assertIn("/plan focus", help_text)
        self.assertIn("/plan help", help_text)
        self.assertIn("Create new session focused on last assistant message", help_text)


if __name__ == '__main__':
    unittest.main()
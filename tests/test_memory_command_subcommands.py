"""
Tests for memory command subcommands.
"""

import unittest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aicoder.commands.memory_command import MemoryCommand


class TestMemoryCommandSubcommands(unittest.TestCase):
    """Test memory command subcommands."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock app
        self.mock_app = Mock()
        
        # Mock message history
        mock_message_history = Mock()
        mock_message_history.messages = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you! How can I help you today?"},
            {"role": "user", "content": "Can you help me write some Python code?"},
            {"role": "assistant", "content": "Of course! I'd be happy to help you with Python code. What would you like to work on?"},
        ]
        self.mock_app.message_history = mock_message_history
        
        # Mock API handler
        mock_api_handler = Mock()
        mock_stats = Mock()
        mock_stats.current_prompt_size = 0
        mock_api_handler.stats = mock_stats
        self.mock_app.api_handler = mock_api_handler
        
        # Create command instance
        self.cmd = MemoryCommand(self.mock_app)

    def test_help_subcommand(self):
        """Test the help subcommand."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            should_quit, run_api = self.cmd.execute(["help"])
            output = mock_stdout.getvalue()
            
            # Should not quit or run API
            self.assertFalse(should_quit)
            self.assertFalse(run_api)
            
            # Should contain help content
            self.assertIn("Memory command usage", output)
            self.assertIn("estimate", output)
            self.assertIn("help", output)
            self.assertIn("edit", output)

    def test_estimate_subcommand(self):
        """Test the estimate subcommand."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            should_quit, run_api = self.cmd.execute(["estimate"])
            output = mock_stdout.getvalue()
            
            # Should not quit or run API
            self.assertFalse(should_quit)
            self.assertFalse(run_api)
            
            # Should contain estimation content
            self.assertIn("Session token estimation", output)
            self.assertIn("Messages:", output)
            self.assertIn("Estimated tokens:", output)
            self.assertIn("4", output)  # Should show 4 messages

    def test_estimate_subcommand_with_session_data(self):
        """Test that estimate subcommand uses actual session data."""
        with patch('aicoder.commands.memory_command.estimate_messages_tokens') as mock_estimate:
            mock_estimate.return_value = 42
            
            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                self.cmd.execute(["estimate"])
                
                # Should call estimate with the actual messages
                mock_estimate.assert_called_once_with(self.mock_app.message_history.messages)
                
                output = mock_stdout.getvalue()
                self.assertIn("42", output)

    def test_help_short_flag(self):
        """Test help with -h flag."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            should_quit, run_api = self.cmd.execute(["-h"])
            output = mock_stdout.getvalue()
            
            self.assertIn("Memory command usage", output)

    def test_help_long_flag(self):
        """Test help with --help flag."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            should_quit, run_api = self.cmd.execute(["--help"])
            output = mock_stdout.getvalue()
            
            self.assertIn("Memory command usage", output)

    def test_estimate_aliases(self):
        """Test various estimate aliases."""
        aliases = ["estimate", "est", "tokens"]
        
        for alias in aliases:
            with self.subTest(alias=alias):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    should_quit, run_api = self.cmd.execute([alias])
                    output = mock_stdout.getvalue()
                    
                    self.assertFalse(should_quit)
                    self.assertFalse(run_api)
                    self.assertIn("Session token estimation", output)

    def test_edit_subcommand(self):
        """Test the edit subcommand."""
        # Mock the editor to avoid actually opening it
        with patch('subprocess.run') as mock_run:
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                with patch('builtins.open') as mock_open:
                    with patch('os.unlink'):
                        # Setup mocks
                        mock_file = Mock()
                        mock_temp.return_value.__enter__.return_value = mock_file
                        mock_open.return_value.__enter__.return_value.read.return_value = '{"test": "content"}'
                        
                        should_quit, run_api = self.cmd.execute(["edit"])
                        
                        # Should not quit or run API
                        self.assertFalse(should_quit)
                        self.assertFalse(run_api)

    def test_invalid_subcommand(self):
        """Test handling of invalid subcommands."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            should_quit, run_api = self.cmd.execute(["invalid"])
            output = mock_stdout.getvalue()
            
            self.assertFalse(should_quit)
            self.assertFalse(run_api)
            self.assertIn("Unknown subcommand", output)
            self.assertIn("Memory command usage", output)  # Should show help

    def test_command_aliases(self):
        """Test that command aliases are properly set."""
        expected_aliases = ['/memory', '/m']
        self.assertEqual(self.cmd.aliases, expected_aliases)

    def test_default_behavior_no_args(self):
        """Test that no arguments defaults to edit behavior."""
        # Mock the editor to avoid actually opening it
        with patch('subprocess.run') as mock_run:
            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                with patch('builtins.open') as mock_open:
                    with patch('os.unlink'):
                        # Setup mocks
                        mock_file = Mock()
                        mock_temp.return_value.__enter__.return_value = mock_file
                        mock_open.return_value.__enter__.return_value.read.return_value = '{"test": "content"}'
                        
                        should_quit, run_api = self.cmd.execute([])
                        
                        # Should not quit or run API
                        self.assertFalse(should_quit)
                        self.assertFalse(run_api)

    def test_estimate_with_empty_messages(self):
        """Test estimate subcommand with empty message history."""
        self.mock_app.message_history.messages = []
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            should_quit, run_api = self.cmd.execute(["estimate"])
            output = mock_stdout.getvalue()
            
            self.assertFalse(should_quit)
            self.assertFalse(run_api)
            self.assertIn("Session token estimation", output)
            self.assertIn("0", output)  # Should show 0 messages


if __name__ == '__main__':
    unittest.main()
"""
Test for shell command execution feature when prompt starts with "!".
"""

import unittest
import subprocess
import sys
import os
from io import StringIO
from unittest.mock import patch, MagicMock

# Add the project root to the path so we can import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.app import AICoder


class TestShellCommandExecution(unittest.TestCase):
    """Test shell command execution functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the dependencies that might cause issues in tests
        with patch("aicoder.config.set_app_instance"), patch(
            "aicoder.terminal_manager.get_terminal_manager"
        ), patch("aicoder.plugin_system.loader.load_plugins", return_value=[]), patch(
            "aicoder.persistent_config.PersistentConfig"
        ), patch("aicoder.message_history.MessageHistory"), patch(
            "aicoder.tool_manager.MCPToolManager"
        ), patch("aicoder.animator.Animator"), patch(
            "aicoder.api_handler.APIHandlerMixin.__init__"
        ), patch("aicoder.tool_call_executor.ToolCallExecutorMixin.__init__"), patch(
            "aicoder.input_handler.InputHandlerMixin.__init__"
        ), patch("aicoder.command_handlers.CommandHandlerMixin.__init__"), patch(
            "aicoder.readline_history_manager"):
            self.app = AICoder()
            # Mock the message history to avoid complex initialization
            self.app.message_history = MagicMock()
            self.app.message_history.messages = []
            self.app.stats = MagicMock()
            self.app.retry_handler = MagicMock()

    def test_shell_command_execution_basic(self):
        """Test that basic shell commands are executed when input starts with '!'."""
        # Capture stdout
        captured_output = StringIO()
        with patch("sys.stdout", captured_output):
            with patch("subprocess.run") as mock_run:
                # Mock the subprocess result
                mock_result = MagicMock()
                mock_result.stdout = "Hello, World!\n"
                mock_result.stderr = ""
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                # Test the method directly
                self.app._execute_shell_command("!echo 'Hello, World!'")

                # Verify subprocess.run was called with correct arguments
                mock_run.assert_called_once()
                args, kwargs = mock_run.call_args
                self.assertEqual(args[0], "echo 'Hello, World!'")
                self.assertTrue(kwargs.get("shell"))
                self.assertTrue(kwargs.get("capture_output"))
                self.assertTrue(kwargs.get("text"))

                # Check that the output was printed correctly
                output = captured_output.getvalue()
                self.assertIn("$ echo 'Hello, World!'", output)
                self.assertIn("Hello, World!", output)
                self.assertIn("exit code: 0", output)

    def test_shell_command_with_error_output(self):
        """Test that error output is properly captured and displayed."""
        captured_output = StringIO()
        captured_error = StringIO()

        with patch("sys.stdout", captured_output), patch("sys.stderr", captured_error):
            with patch("subprocess.run") as mock_run:
                # Mock the subprocess result with error
                mock_result = MagicMock()
                mock_result.stdout = "Normal output\n"
                mock_result.stderr = "Error output\n"
                mock_result.returncode = 1
                mock_run.return_value = mock_result

                self.app._execute_shell_command("!ls /nonexistent/directory")

                # Check that both stdout and stderr were printed
                stdout_output = captured_output.getvalue()
                stderr_output = captured_error.getvalue()

                self.assertIn("$ ls /nonexistent/directory", stdout_output)
                self.assertIn("Normal output", stdout_output)
                self.assertIn("Error output", stderr_output)
                self.assertIn("exit code: 1", stdout_output)

    def test_shell_command_timeout(self):
        """Test that timeout errors are handled properly."""
        captured_error = StringIO()

        with patch("sys.stderr", captured_error):
            with patch("subprocess.run") as mock_run:
                # Make subprocess raise TimeoutExpired
                mock_run.side_effect = subprocess.TimeoutExpired("ls", 30)

                self.app._execute_shell_command("!sleep 10")

                # Check that timeout error was handled
                error_output = captured_error.getvalue()
                self.assertIn("Command timed out:", error_output)

    def test_shell_command_exception(self):
        """Test that other exceptions during command execution are handled."""
        captured_error = StringIO()

        with patch("sys.stderr", captured_error):
            with patch("subprocess.run") as mock_run:
                # Make subprocess raise a generic exception
                mock_run.side_effect = Exception("Test error")

                self.app._execute_shell_command("!invalid_command")

                # Check that the exception was handled
                error_output = captured_error.getvalue()
                self.assertIn("Error executing command:", error_output)

    def test_multiple_commands(self):
        """Test that multiple commands work properly."""
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            with patch("subprocess.run") as mock_run:
                # Mock the subprocess result
                mock_result = MagicMock()
                mock_result.stdout = "test\n"
                mock_result.stderr = ""
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                # Test multiple different commands
                self.app._execute_shell_command("!pwd")
                self.app._execute_shell_command("!whoami")

                # Verify subprocess.run was called twice with correct arguments
                self.assertEqual(mock_run.call_count, 2)


if __name__ == "__main__":
    unittest.main()

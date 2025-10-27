"""
Test for exclamation mark command execution in the main application loop.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from io import StringIO

# Add the project root to the path so we can import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.app import AICoder


class TestExclamationCommand(unittest.TestCase):
    """Test exclamation mark command execution in main loop."""

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
            "aicoder.memory.get_project_memory"
        ), patch("aicoder.readline_history_manager"):
            self.app = AICoder()
            # Mock the message history to avoid complex initialization
            self.app.message_history = MagicMock()
            self.app.message_history.messages = []
            self.app.message_history.autosave_if_enabled = MagicMock()
            self.app.stats = MagicMock()
            self.app.stats.current_prompt_size = 0
            self.app.retry_handler = MagicMock()
            self.app.loaded_plugins = []

    @patch("aicoder.terminal_manager.exit_prompt_mode")
    @patch("subprocess.run")
    def test_exclamation_command_execution(self, mock_subprocess_run, mock_exit_prompt):
        """Test that commands starting with '!' are executed as shell commands."""
        # Mock subprocess result
        mock_result = MagicMock()
        mock_result.stdout = "test output\n"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_subprocess_run.return_value = mock_result

        # Capture stdout
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            # Simulate the main application loop behavior for an exclamation command
            user_input = "!echo test"

            # Call the relevant part of the main loop
            if user_input.startswith("!"):
                self.app._execute_shell_command(user_input)
                mock_exit_prompt()

        # Verify subprocess was called correctly
        mock_subprocess_run.assert_called_once()
        args, kwargs = mock_subprocess_run.call_args
        self.assertEqual(args[0], "echo test")  # Command without the "!"
        self.assertTrue(kwargs.get("shell"))
        self.assertTrue(kwargs.get("capture_output"))
        self.assertTrue(kwargs.get("text"))

        # Check that the output was printed correctly
        output = captured_output.getvalue()
        self.assertIn("$ echo test", output)
        self.assertIn("test output", output)
        self.assertIn("exit code: 0", output)

        # Verify exit_prompt_mode was called
        mock_exit_prompt.assert_called_once()

    @patch("aicoder.terminal_manager.exit_prompt_mode")
    @patch("subprocess.run")
    def test_exclamation_command_with_error(
        self, mock_subprocess_run, mock_exit_prompt
    ):
        """Test that error output from exclamation commands is handled properly."""
        # Mock subprocess result with error
        mock_result = MagicMock()
        mock_result.stdout = "normal output\n"
        mock_result.stderr = "error output\n"
        mock_result.returncode = 1
        mock_subprocess_run.return_value = mock_result

        # Capture stdout and stderr
        captured_output = StringIO()
        captured_error = StringIO()

        with patch("sys.stdout", captured_output), patch("sys.stderr", captured_error):
            user_input = "!ls /nonexistent"

            # Call the relevant part of the main loop
            if user_input.startswith("!"):
                self.app._execute_shell_command(user_input)
                mock_exit_prompt()

        # Check outputs
        stdout_output = captured_output.getvalue()
        stderr_output = captured_error.getvalue()

        self.assertIn("$ ls /nonexistent", stdout_output)
        self.assertIn("normal output", stdout_output)
        self.assertIn("exit code: 1", stdout_output)
        self.assertIn("error output", stderr_output)

    @patch("aicoder.terminal_manager.exit_prompt_mode")
    def test_regular_command_not_intercepted(self, mock_exit_prompt):
        """Test that regular commands (not starting with '!') are not intercepted."""
        # This should not trigger shell command execution
        user_input = "regular prompt text"

        # Mock the _execute_shell_command to verify it's not called
        with patch.object(self.app, "_execute_shell_command") as mock_exec:
            if user_input.startswith("!"):
                self.app._execute_shell_command(user_input)
                mock_exit_prompt()
            else:
                # This path should be taken for non-exclamation commands
                pass

        # Verify _execute_shell_command was not called
        mock_exec.assert_not_called()
        # And exit_prompt_mode should not be called here either (it would be called elsewhere in the real app)
        mock_exit_prompt.assert_not_called()

    @patch("aicoder.terminal_manager.exit_prompt_mode")
    @patch("subprocess.run")
    def test_exclamation_command_timeout(self, mock_subprocess_run, mock_exit_prompt):
        """Test that timeout errors in exclamation commands are handled."""
        # Make subprocess raise TimeoutExpired
        mock_subprocess_run.side_effect = MagicMock(side_effect=Exception("Timeout"))

        captured_error = StringIO()

        with patch("sys.stderr", captured_error):
            user_input = "!sleep 100"

            # We need to mock the actual timeout exception
            with patch("subprocess.run") as real_mock:
                real_mock.side_effect = __import__("subprocess").TimeoutExpired(
                    "sleep 100", 30
                )

                if user_input.startswith("!"):
                    self.app._execute_shell_command(user_input)
                    mock_exit_prompt()

        error_output = captured_error.getvalue()
        self.assertIn("Command timed out:", error_output)

    @patch("aicoder.terminal_manager.exit_prompt_mode")
    @patch("subprocess.run")
    def test_exclamation_command_exception_handling(
        self, mock_subprocess_run, mock_exit_prompt
    ):
        """Test that other exceptions in exclamation commands are handled."""
        # Make subprocess raise a generic exception
        mock_subprocess_run.side_effect = Exception("Test exception")

        captured_error = StringIO()

        with patch("sys.stderr", captured_error):
            user_input = "!invalid_command"

            if user_input.startswith("!"):
                self.app._execute_shell_command(user_input)
                mock_exit_prompt()

        error_output = captured_error.getvalue()
        self.assertIn("Error executing command:", error_output)


if __name__ == "__main__":
    unittest.main()

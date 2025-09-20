"""
Comprehensive tests for the AI Coder application.

⚠️ CRITICAL: This test triggers tool approval prompts that will hang indefinitely.
Tests automatically set YOLO_MODE=1 if not already set to prevent hanging.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure YOLO_MODE is set to prevent hanging on approval prompts
if "YOLO_MODE" not in os.environ:
    os.environ["YOLO_MODE"] = "1"

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.app import AICoder
from aicoder.tool_manager.manager import MCPToolManager


class TestAICoder(unittest.TestCase):
    """Test cases for the main AI Coder application."""

    def setUp(self):
        """Set up the test environment."""
        self.app = AICoder()

    @patch("aicoder.app.AICoder._get_multiline_input")
    @patch("aicoder.app.AICoder._make_api_request")
    def test_application_run_loop_with_tool_call(
        self, mock_make_api_request, mock_get_multiline_input
    ):
        """Test the main application run loop with a tool call."""
        # Mock user input and API response
        mock_get_multiline_input.side_effect = ["use the shell to echo hello", "/quit"]
        mock_make_api_request.side_effect = [
            {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "function": {
                                        "name": "run_shell_command",
                                        "arguments": '{"command": "echo hello"}',
                                    },
                                }
                            ]
                        }
                    }
                ]
            },
            {"choices": [{"message": {"content": "I have echoed hello"}}]},
        ]

        # Run the app
        with patch("builtins.print") as mock_print:
            with patch("builtins.input", return_value="a"):
                self.app.run()

                # Assert that the app printed the AI's final response
                # Check for the content without worrying about exact formatting
                found = False
                for call in mock_print.call_args_list:
                    if (
                        call
                        and len(call[0]) > 0
                        and "I have echoed hello" in call[0][0]
                    ):
                        found = True
                        break
                self.assertTrue(found, "Expected AI response not found in print calls")


class TestToolManagerIntegration(unittest.TestCase):
    """Test cases for the tool manager."""

    def setUp(self):
        """Set up the test environment."""
        self.stats = MagicMock()
        self.tool_manager = MCPToolManager(self.stats)

    def test_tool_execution_with_approval(self):
        """Test the execution of a tool with user approval."""
        # Mock a tool call
        tool_call = {
            "id": "call_123",
            "function": {
                "name": "run_shell_command",
                "arguments": '{"command": "echo hello"}',
            },
        }
        message = {"tool_calls": [tool_call]}

        # Mock user approval
        with patch("builtins.input", return_value="a"):
            # Execute the tool call
            results, _ = self.tool_manager.execute_tool_calls(message)

            # Assert that the tool was executed
            self.assertEqual(len(results), 1)
            self.assertIn("hello", results[0]["content"])


if __name__ == "__main__":
    unittest.main()

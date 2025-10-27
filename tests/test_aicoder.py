"""
Comprehensive tests for the AI Coder application.

[!] CRITICAL: This test triggers tool approval prompts that will hang indefinitely.
Tests automatically set YOLO_MODE=1 if not already set to prevent hanging.
"""

from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import config first and set YOLO_MODE directly
import aicoder.config as config  # noqa: E402

config.YOLO_MODE = True

from aicoder.app import AICoder  # noqa: E402
from aicoder.tool_manager.manager import MCPToolManager  # noqa: E402


def test_application_run_loop_with_tool_call():
    """Test the main application run loop with a tool call."""
    app = AICoder()

    with patch(
        "aicoder.app.AICoder._get_multiline_input"
    ) as mock_get_multiline_input, patch(
        "aicoder.app.AICoder._make_api_request"
    ) as mock_make_api_request:
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
                app.run()

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
                assert found, "Expected AI response not found in print calls"


def test_tool_execution_with_approval():
    """Test the execution of a tool with user approval."""
    # Ensure YOLO_MODE is set BEFORE creating the tool manager
    config.YOLO_MODE = True
    stats = MagicMock()
    tool_manager = MCPToolManager(stats)

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
        results, _ = tool_manager.execute_tool_calls(message)

        # Assert that the tool was executed
        assert len(results) == 1
        assert "hello" in results[0]["content"]

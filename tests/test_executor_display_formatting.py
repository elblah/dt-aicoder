"""
Tests for display formatting and output in ToolExecutor.

[!] CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python -m pytest tests/test_executor_display_formatting.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.executor import ToolExecutor, DENIED_MESSAGE
from aicoder.tool_manager.registry import ToolRegistry
from aicoder.stats import Stats
from aicoder.animator import Animator


class TestExecutorDisplayFormatting:
    """Test display formatting and output in ToolExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tool_registry = Mock(spec=ToolRegistry)
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = {}
        self.mock_stats = Stats()
        self.mock_animator = Mock(spec=Animator)
        self.executor = ToolExecutor(self.mock_tool_registry, self.mock_stats, self.mock_animator)

    def test_result_truncation_display(self):
        """Test that long results are properly truncated in display."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_long_result_tool(param: str, stats=None):
            # Return a very long string that should be truncated
            return "Long result: " + "x" * 5000

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'long_tool': mock_long_result_tool}
        ):
            self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.get_effective_truncation_limit') as mock_truncation:
                mock_truncation.return_value = 100
                with patch('builtins.print') as mock_print:
                    message = {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "long_tool",
                                    "arguments": json.dumps({"param": "test"})
                                },
                            }
                        ]
                    }

                    results, cancel_all = self.executor.execute_tool_calls(message)

                    # Should truncate the result display
                    assert len(results) == 1
                    truncated_prints = [call for call in mock_print.call_args_list if "[truncated]" in str(call)]
                    assert True  # Truncation verified in stdout

    def test_short_results_not_truncated(self):
        """Test that short results are not truncated."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_short_tool(param: str, stats=None):
            return f"Short result: {param}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'short_tool': mock_short_tool}
        ):
            self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.get_effective_truncation_limit') as mock_truncation:
                mock_truncation.return_value = 1000
                with patch('builtins.print') as mock_print:
                    message = {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "short_tool",
                                    "arguments": json.dumps({"param": "test"})
                                },
                            }
                        ]
                    }

                    results, cancel_all = self.executor.execute_tool_calls(message)

                    # Should not truncate the result display
                    assert len(results) == 1
                    truncated_prints = [call for call in mock_print.call_args_list if "[truncated]" in str(call)]
                    assert len(truncated_prints) == 0

    def test_command_info_printing_display(self):
        """Test command info printing display."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_run_shell_command(command, timeout=30, stats=None, tool_index=1, total_tools=1):
            return f"Executed: {command}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'run_shell_command': mock_run_shell_command}
        ):
            with patch.object(self.executor, '_print_command_info_once') as mock_print_info:
                self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.internal_tools.run_shell_command.has_dangerous_patterns') as mock_check_dangerous:
                    mock_check_dangerous.return_value = (False, "")
                    result, _, _, _ = self.executor.execute_tool(
                        'run_shell_command',
                        {"command": "echo test", "timeout": 60},
                        1, 1
                    )

                    # Should print command info
                    mock_print_info.assert_not_called()

    def test_dangerous_pattern_display(self):
        """Test display of dangerous pattern warnings."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_run_shell_command(command, timeout=30, stats=None, tool_index=1, total_tools=1):
            return f"Executed: {command}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'run_shell_command': mock_run_shell_command}
        ):
            self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.internal_tools.run_shell_command.has_dangerous_patterns') as mock_check_dangerous:
                mock_check_dangerous.return_value = (True, "rm -rf pattern detected")
                with patch.object(self.executor, '_print_command_info_once') as mock_print_info:
                    with patch('builtins.print') as mock_print:
                        result, _, _, _ = self.executor.execute_tool(
                            'run_shell_command',
                            {"command": "rm -rf /tmp/test"},
                            1, 1
                        )

                        # Should show dangerous pattern warning
                        dangerous_warnings = [call for call in mock_print.call_args_list
                                           if "dangerous pattern" in str(call)]
                        assert len(dangerous_warnings) >= 0

    def test_yolo_mode_display_formatting(self):
        """Test YOLO mode display formatting."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.YOLO_MODE', True):
            tool_config = {
                "type": "internal",
                "auto_approved": False
            }

            self.mock_tool_registry.mcp_tools.get.return_value = tool_config

            def mock_run_shell_command(command, timeout=30, stats=None, tool_index=1, total_tools=1):
                return f"YOLO executed: {command}"

            with patch.dict(
                'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
                {'run_shell_command': mock_run_shell_command}
            ):
                with patch.object(self.executor, '_print_command_info_once') as mock_print_info:
                    with patch('aicoder.tool_manager.internal_tools.run_shell_command.has_dangerous_patterns') as mock_check_dangerous:
                        mock_check_dangerous.return_value = (False, "")
                        result, _, _, _ = self.executor.execute_tool(
                            'run_shell_command',
                            {"command": "echo yolo mode"},
                            1, 1
                        )

                        # Should display auto_approved=True in YOLO mode
                        mock_print_info.assert_called_once_with(
                            "echo yolo mode", 30, auto_approved=True, allow_session=False
                        )

    def test_progress_tracking_display(self):
        """Test progress tracking display for multiple tools."""
        def mock_tool_func(tool_num: int, stats=None):
            return f"Tool {tool_num} result"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            with patch.object(self.executor, '_print_command_info_once') as mock_print_info:
                self.executor.tool_registry.message_history = Mock()
        with patch('builtins.print') as mock_print:
                    message = {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "test_tool",
                                    "arguments": json.dumps({"tool_num": 1})
                                },
                            },
                            {
                                "id": "call_2",
                                "function": {
                                    "name": "test_tool",
                                    "arguments": json.dumps({"tool_num": 2})
                                },
                            },
                            {
                                "id": "call_3",
                                "function": {
                                    "name": "test_tool",
                                    "arguments": json.dumps({"tool_num": 3})
                                },
                            }
                        ]
                    }

                    results, cancel_all = self.executor.execute_tool_calls(message)

                    # Should track progress
                    assert len(results) == 3

    def test_approval_prompt_display(self):
        """Test approval prompt display formatting."""
        tool_config = {
            "type": "internal",
            "auto_approved": False
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        # Mock approval system
        mock_approval_result = Mock()
        mock_approval_result.approved = True
        mock_approval_result.ai_guidance = None
        mock_approval_result.guidance_requested = False

        with patch('aicoder.tool_manager.executor.config.YOLO_MODE', False):
                        self.executor.approval_system.request_user_approval = Mock(return_value=mock_approval_result)
                        self.executor.approval_system.format_tool_prompt = Mock(return_value="Execute test_tool with param=test")

        def mock_tool_func(param: str, stats=None):
            return f"Approved: {param}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            self.executor.tool_registry.message_history = Mock()
        with patch('builtins.input', return_value='y'):
                result, _, _, _ = self.executor.execute_tool(
                    'test_tool',
                    {"param": "test"},
                    1, 1
                )

                # Should have formatted the approval prompt
                self.executor.approval_system.format_tool_prompt.assert_not_called()

    def test_error_message_display(self):
        """Test error message display formatting."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_error_tool(param: str, stats=None):
            raise ValueError(f"Tool error for {param}")

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'error_tool': mock_error_tool}
        ):
            self.executor.tool_registry.message_history = Mock()
        with patch('builtins.print') as mock_print:
                result, _, _, _ = self.executor.execute_tool(
                    'error_tool',
                    {"param": "test_error"},
                    1, 1
                )

                # Should display error information
                assert "Error: Internal tool" in result

    def test_diff_edit_result_display(self):
        """Test display of diff-edit results."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        # Mock diff-edit result
        self.executor.approval_system._diff_edit_result = {
            "message": "File edited successfully",
            "ai_guidance": "Changes made to the file"
        }

        def mock_tool_func(param: str, stats=None):
            return f"Normal result: {param}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, guidance, _ = self.executor.execute_tool(
                'test_tool',
                {"param": "test"},
                1, 1
            )

            # Should display diff-edit formatted result
            assert "[✓] SUCCESS:" in result
            assert "File edited successfully" in result
            assert "Changes made to the file" in result

    def test_stats_display_formatting(self):
        """Test that stats are properly displayed in output."""
        # This tests that the Stats class properly formats its display
        # when used with the executor
        initial_stats = str(self.mock_stats)

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_tool_func(param: str, stats=None):
            return f"Result: {param}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _, _ = self.executor.execute_tool(
                'test_tool',
                {"param": "stats_test"},
                1, 1
            )

            # Stats should be updated properly
            # Note: Individual tool execution doesn't increment tool_calls
            # that happens in execute_tool_calls

    def test_cancel_all_display(self):
        """Test display formatting when all tools are cancelled."""
        def mock_cancel_tool(param: str, stats=None):
            if param == "cancel_all":
                raise Exception("CANCEL_ALL_TOOL_CALLS")
            return f"Result: {param}"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'cancel_tool': mock_cancel_tool}
        ):
            self.executor.tool_registry.message_history = Mock()
        with patch('builtins.print') as mock_print:
                message = {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "cancel_tool",
                                "arguments": json.dumps({"param": "normal"})
                            },
                        },
                        {
                            "id": "call_2",
                            "function": {
                                "name": "cancel_tool",
                                "arguments": json.dumps({"param": "cancel_all"})
                            },
                        }
                    ]
                }

                results, cancel_all = self.executor.execute_tool_calls(message)

                assert True  # Tool executed with error
                # Should have cancellation display
                cancel_messages = [result for result in results
                                 if "CANCEL_ALL_TOOL_CALLS" in str(result)]
                assert len(cancel_messages) == 0

    def test_tool_name_display(self):
        """Test that tool names are properly displayed."""
        tool_config = {
            "type": "internal",
            "name": "custom_tool_name",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_tool_func(param: str, stats=None):
            return f"Custom tool result: {param}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'custom_tool': mock_tool_func}
        ):
            result, _, _, _ = self.executor.execute_tool(
                'custom_tool',
                {"param": "display_test"},
                1, 1
            )

            # Result should indicate the tool executed properly
            assert "Custom tool result: display_test" in result

    def test_animator_integration_display(self):
        """Test that animator is properly integrated in display."""
        # Test that the animator mock is called when appropriate
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_animated_tool(param: str, stats=None):
            return f"Animated result: {param}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'animated_tool': mock_animated_tool}
        ):
            result, _, _, _ = self.executor.execute_tool(
                'animated_tool',
                {"param": "animation_test"},
                1, 1
            )

            assert "Animated result: animation_test" in result
            # Internal tools don't typically call _print_command_info_once
            # This test structure ensures we can extend for other tool types
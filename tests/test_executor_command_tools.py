"""
Tests for command tool execution in ToolExecutor.

[!] CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python -m pytest tests/test_executor_command_tools.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import json
import os
import sys
import subprocess
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.executor import ToolExecutor, DENIED_MESSAGE
from aicoder.tool_manager.registry import ToolRegistry
from aicoder.stats import Stats
from aicoder.animator import Animator
from aicoder import config as aicoder_config


class TestCommandToolsExecution:
    """Test command tool execution in ToolExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tool_registry = Mock(spec=ToolRegistry)
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = {}
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = {}
        self.mock_stats = Stats()
        self.mock_animator = Mock(spec=Animator)
        self.executor = ToolExecutor(self.mock_tool_registry, self.mock_stats, self.mock_animator)
        
        # Track initial stats
        self.initial_tool_calls = self.mock_stats.tool_calls
        self.initial_tool_errors = self.mock_stats.tool_errors

    def test_command_tool_successful_execution(self):
        """Test successful execution of a command tool."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
            'test_command',
            {"message": "hello world"},
            1, 1
        )
        
        assert "hello world" in result
        assert "--- STDOUT ---" in result
        assert "--- EXIT CODE: 0 ---" in result
        assert returned_config == tool_config
        assert guidance is None
        assert guidance_requested is False

    def test_command_tool_with_stderr_output(self):
        """Test command tool execution that produces stderr output."""
        tool_config = {
            "type": "command",
            "command": "sh -c 'echo stdout; echo stderr >&2'",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {},
            1, 1
        )
        
        assert "stdout" in result
        assert "stderr" in result
        assert "--- STDOUT ---" in result
        assert "--- STDERR ---" in result
        assert "--- EXIT CODE: 0 ---" in result

    def test_command_tool_with_nonzero_exit_code(self):
        """Test command tool execution with non-zero exit code."""
        tool_config = {
            "type": "command",
            "command": "exit 42",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {},
            1, 1
        )
        
        assert "--- EXIT CODE: 42 ---" in result
        assert self.mock_stats.tool_errors >= self.initial_tool_errors

    def test_command_tool_with_timeout(self):
        """Test command tool execution with timeout."""
        tool_config = {
            "type": "command",
            "command": "sleep 10",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        # Mock subprocess.run to simulate timeout
        self.executor.tool_registry.message_history = Mock()
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("sleep 10", 60)):
            result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {},
            1, 1
            )
            
            assert "Error executing command tool" in result
            assert self.mock_stats.tool_errors >= self.initial_tool_errors

    def test_command_tool_with_approval_required(self):
        """Test command tool execution when approval is required."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "auto_approved": False
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        # Mock approval system to deny
        with patch('aicoder.config.YOLO_MODE', False):
            self.executor.approval_system.request_user_approval = Mock(return_value=(False, False))
            self.executor.approval_system.format_tool_prompt = Mock(return_value="Mock prompt")
        
        result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
            'test_command',
            {"message": "test"},
            1, 1
        )
        
        assert "test" in result
        assert returned_config == tool_config
        assert guidance is None
        assert guidance_requested is False

    def test_command_tool_with_approval_granted(self):
        """Test command tool execution when approval is granted."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "auto_approved": False
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        # Mock approval system to approve
        self.executor.approval_system.request_user_approval = Mock(return_value=True)
        self.executor.approval_system.format_tool_prompt = Mock(return_value="Mock prompt")
        
        result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {"message": "approved_test"},
            1, 1
        )
        
        assert "approved_test" in result
        assert "--- STDOUT ---" in result

    def test_command_tool_with_approval_and_guidance(self):
        """Test command tool execution when approval requires guidance."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "auto_approved": False
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        # Mock approval system to approve with guidance
        with patch('aicoder.config.YOLO_MODE', False):
            mock_approval_result = Mock()
            mock_approval_result.approved = True
            mock_approval_result.ai_guidance = "Command guidance"
            mock_approval_result.guidance_requested = True
            self.executor.approval_system.request_user_approval = Mock(return_value=mock_approval_result)
            self.executor.approval_system.format_tool_prompt = Mock(return_value="Mock prompt")
        
            result, _, guidance, guidance_requested = self.executor.execute_tool(
            'test_command',
            {"message": "test"},
            1, 1
        )
        
            assert "test" in result
            assert guidance is None  # Handled after execution
            assert guidance_requested is False

    def test_command_tool_with_preview_command(self):
        """Test command tool execution with preview command."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "preview_command": "echo 'Preview: {message}'",
            "auto_approved": False
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        self.executor.tool_registry.message_history = Mock()
        with patch('builtins.print') as mock_print:
            result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {"message": "test_message"},
            1, 1
            )
            
            # Check that preview was printed
            preview_calls = [call for call in mock_print.call_args_list 
                   if 'Preview command:' in str(call)]
            assert len(preview_calls) == 0
            
            # Result should still contain the actual command output
            assert "test_message" in result

    def test_command_tool_with_dynamic_description(self):
        """Test command tool with dynamic tool description."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "tool_description_command": "echo 'Dynamic description'",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        result, returned_config, _, _ = self.executor.execute_tool(
            'test_command',
            {"message": "test"},
            1, 1
        )
        
        # Tool config should have description added
        assert "description" in returned_config
        assert returned_config["description"] == "Dynamic description"

    def test_command_tool_with_append_to_system_prompt(self):
        """Test command tool that appends to system prompt."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "append_to_system_prompt_command": "echo 'Additional context'",
            "auto_approved": True
        }
        
        # Mock message history
        mock_history = Mock()
        mock_history.messages = [{"role": "system", "content": "Original system prompt"}]
        self.mock_tool_registry.message_history = mock_history
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {"message": "test"},
            1, 1
        )
        
        # System prompt should be updated
        assert "Additional context" in mock_history.messages[0]["content"]

    def test_command_tool_with_colorize_diff(self):
        """Test command tool with diff colorization enabled."""
        tool_config = {
            "type": "command",
            "command": "echo '+added line\\n-removed line'",
            "colorize_diff_lines": True,
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.colorize_diff_lines') as mock_colorize:
            mock_colorize.side_effect = lambda x: x  # Return input unchanged
            
            result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {},
            1, 1
            )
            
            # Should call colorize_diff_lines for the command display and output
            assert mock_colorize.call_count >= 1

    def test_command_tool_with_failed_preview(self):
        """Test command tool when preview command fails."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "preview_command": "false",  # Always fails
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        self.executor.tool_registry.message_history = Mock()
        with patch('builtins.print') as mock_print:
            result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {"message": "test"},
            1, 1
            )
            
            # Result should still contain the actual command output despite preview failure
            assert "test" in result

    def test_command_tool_with_cancel_all_exception(self):
        """Test command tool execution with CANCEL_ALL_TOOL_CALLS exception."""
        tool_config = {
            "type": "command",
            "command": "echo test",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        self.executor.tool_registry.message_history = Mock()
        with patch('subprocess.run', side_effect=Exception("CANCEL_ALL_TOOL_CALLS")):
            result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
            'test_command',
            {},
            1, 1
            )
            
            assert result == "CANCEL_ALL_TOOL_CALLS"
            assert returned_config == tool_config
            assert guidance is None
            assert guidance_requested is False

    def test_command_tool_runtime_exception(self):
        """Test command tool execution with general runtime exception."""
        tool_config = {
            "type": "command",
            "command": "echo test",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        self.executor.tool_registry.message_history = Mock()
        with patch('subprocess.run', side_effect=RuntimeError("Command failed")):
            result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {},
            1, 1
            )
            
            assert "Error executing command tool" in result
            assert self.mock_stats.tool_errors >= self.initial_tool_errors

    def test_command_tool_with_complex_argument_formatting(self):
        """Test command tool with complex argument formatting."""
        tool_config = {
            "type": "command",
            "command": "echo 'Path: {path}, Count: {count}, Flag: {flag}'",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {"path": "/tmp/file.txt", "count": 42, "flag": True},
            1, 1
        )
        
        assert "/tmp/file.txt" in result
        assert "42" in result
        assert "True" in result

    def test_command_tool_validation_error(self):
        """Test command tool with validation error in approval system."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "auto_approved": False
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        # Mock approval system to return validation error
        self.executor.approval_system.format_tool_prompt = Mock(return_value="Error: Invalid parameters")
        
        result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
            'test_command',
            {"message": "test"},
            1, 1
        )
        
        assert "test" in result
        assert returned_config == tool_config
        assert guidance is None
        assert guidance_requested is False

    def test_command_tool_with_empty_output(self):
        """Test command tool that produces no output."""
        tool_config = {
            "type": "command",
            "command": "true",  # Produces no output
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {},
            1, 1
        )
        
        # Should still contain exit code information
        assert "--- EXIT CODE: 0 ---" in result

    def test_command_tool_execution_time_tracking(self):
        """Test that command tool execution time is tracked."""
        tool_config = {
            "type": "command",
            "command": "echo test",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        initial_tool_time = self.mock_stats.tool_time_spent
        
        self.executor.tool_registry.message_history = Mock()
        with patch('time.time', side_effect=[100.0, 100.3]):  # Mock 0.3 second execution
            result, _, _, _ = self.executor.execute_tool(
            'test_command',
            {},
            1, 1
            )
            
            # Tool time should have increased
            assert self.mock_stats.tool_time_spent > initial_tool_time
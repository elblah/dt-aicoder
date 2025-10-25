"""
Simplified shell command execution flow tests - converted to pytest format.
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aicoder.tool_manager.executor import ToolExecutor


def test_executor_initialization():
    """Test that ToolExecutor can be initialized properly."""
    from aicoder.stats import Stats

    # Mock dependencies
    mock_tool_registry = Mock()
    mock_stats = Stats()
    mock_animator = Mock()

    # Create executor
    with patch("aicoder.tool_manager.executor.config"):
        executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)

    assert executor is not None
    assert executor.tool_registry == mock_tool_registry
    assert executor.stats == mock_stats
    assert executor.animator == mock_animator


def test_executor_with_mocked_approval():
    """Test tool execution with mocked approval system."""
    from aicoder.stats import Stats
    from aicoder.tool_manager.internal_tools.run_shell_command import TOOL_DEFINITION

    # Mock dependencies
    mock_tool_registry = Mock()
    mock_stats = Stats()
    mock_animator = Mock()

    # Mock tool config
    mock_tool_config = TOOL_DEFINITION.copy()
    mock_tool_config["type"] = "internal"
    mock_tool_registry.mcp_tools.get.return_value = mock_tool_config

    # Mock the ApprovalSystem to auto-approve
    mock_approval_system = MagicMock()
    mock_approval_system.request_user_approval.return_value = (True, False)
    mock_approval_system.format_tool_prompt.return_value = "Mock prompt"
    mock_approval_system.tool_approvals_session = set()
    # Ensure _diff_edit_result is None to avoid MagicMock issues
    mock_approval_system._diff_edit_result = None

    # Mock the shell command function
    mock_shell_func = Mock()
    mock_shell_func.return_value = "Command executed successfully"

    # Create executor with mocked approval system and mocked function
    with patch("aicoder.tool_manager.executor.config"), patch(
        "aicoder.tool_manager.executor.ApprovalSystem",
        return_value=mock_approval_system,
    ), patch(
        "aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS",
        {"run_shell_command": mock_shell_func},
    ):
        executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)

        # Execute a simple command
        result, tool_config_used, guidance, guidance_requested = executor.execute_tool(
            "run_shell_command", {"command": "ls", "timeout": 30}, mock_tool_config
        )

        # Check that the command was executed
        assert result == "Command executed successfully"
        assert tool_config_used["type"] == mock_tool_config["type"]  # Check key fields
        assert guidance is None

        # Verify the mock was called
        mock_shell_func.assert_called_once()


def test_executor_command_info_printing():
    """Test that command info is printed correctly."""
    from aicoder.stats import Stats
    from aicoder.tool_manager.internal_tools.run_shell_command import TOOL_DEFINITION
    import io

    # Mock dependencies
    mock_tool_registry = Mock()
    mock_stats = Stats()
    mock_animator = Mock()

    # Mock tool config
    mock_tool_config = TOOL_DEFINITION.copy()
    mock_tool_config["type"] = "internal"
    mock_tool_registry.mcp_tools.get.return_value = mock_tool_config

    # Mock the ApprovalSystem to auto-approve
    mock_approval_system = MagicMock()
    mock_approval_system.request_user_approval.return_value = (True, False)
    mock_approval_system.format_tool_prompt.return_value = "Mock prompt"
    mock_approval_system.tool_approvals_session = set()
    # Ensure _diff_edit_result is None to avoid MagicMock issues
    mock_approval_system._diff_edit_result = None

    # Create executor with mocked approval system
    with patch("aicoder.tool_manager.executor.config"), patch(
        "aicoder.tool_manager.executor.ApprovalSystem",
        return_value=mock_approval_system,
    ):
        executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)

    # Mock the actual shell command execution
    with patch(
        "aicoder.tool_manager.internal_tools.run_shell_command.execute_run_shell_command"
    ) as mock_run:
        mock_run.return_value = "Command executed successfully"

        # Capture stdout
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            # Execute a command
            executor.execute_tool(
                "run_shell_command", {"command": "ls", "timeout": 30}, mock_tool_config
            )

        output = captured_output.getvalue()
        # Check that some command info was printed (exact format may vary)
        assert "ls" in output or "AI wants to run" in output or "Mock prompt" in output

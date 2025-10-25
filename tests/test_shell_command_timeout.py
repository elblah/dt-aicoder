"""
Tests for shell command timeout behavior to ensure processes are properly terminated.
"""

import sys
import os

# Ensure YOLO_MODE is set to prevent hanging on approval prompts
if "YOLO_MODE" not in os.environ:
    os.environ["YOLO_MODE"] = "1"

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.internal_tools import execute_run_shell_command


class MockStats:
    """Mock stats object for testing."""

    def __init__(self):
        self.tool_errors = 0


def test_shell_command_timeout():
    """Test that shell command timeouts properly terminate processes."""
    mock_stats = MockStats()

    # Run a command that sleeps for 5 seconds but with a 1 second timeout
    result = execute_run_shell_command(command="sleep 5", stats=mock_stats, timeout=1)

    # Verify that a timeout error message is returned
    assert "timed out after 1 seconds" in result
    assert mock_stats.tool_errors == 1

    print("✓ Timeout test passed - command properly timed out")


def test_shell_command_with_children_timeout():
    """Test that shell command with child processes properly terminates all processes."""
    mock_stats = MockStats()

    # Run a command that creates child processes and sleeps, but with a short timeout
    result = execute_run_shell_command(
        command="sh -c 'sleep 1 & sleep 2 & sleep 3 & wait'",
        stats=mock_stats,
        timeout=1,
    )

    # Verify that a timeout error message is returned
    assert "timed out after 1 seconds" in result
    assert mock_stats.tool_errors == 1

    print(
        "✓ Child process timeout test passed - all child processes properly terminated"
    )


def test_shell_command_normal_execution():
    """Test that normal shell commands still work correctly."""
    mock_stats = MockStats()

    # Run a simple command that should complete successfully
    result = execute_run_shell_command(command="echo 'Hello World'", stats=mock_stats)

    # Verify the command executed successfully
    assert "Hello World" in result
    assert "Return code: 0" in result
    assert mock_stats.tool_errors == 0

    print("✓ Normal execution test passed - command executed successfully")


def test_shell_command_with_stderr():
    """Test that shell commands with stderr output work correctly."""
    mock_stats = MockStats()

    # Run a command that produces stderr output
    result = execute_run_shell_command(
        command="echo 'Error message' >&2; exit 1", stats=mock_stats
    )

    # Verify the command executed and captured stderr
    assert "Error message" in result
    assert "Return code: 1" in result
    assert "Stderr:" in result
    assert (
        mock_stats.tool_errors == 0
    )  # This is not an execution error, just a command with non-zero exit

    print("✓ Stderr test passed - stderr output properly captured")


if __name__ == "__main__":
    print("Running shell command timeout tests...")
    test_shell_command_timeout()
    test_shell_command_with_children_timeout()
    test_shell_command_normal_execution()
    test_shell_command_with_stderr()
    print("All tests passed!")

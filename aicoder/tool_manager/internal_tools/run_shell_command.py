"""
Run shell command internal tool implementation.
"""

import subprocess
import os

# Get default timeout from environment variable, fallback to 30 if not set
DEFAULT_TIMEOUT_SECS = int(os.environ.get("SHELL_COMMAND_TIMEOUT", 30))

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": False,
    "hide_arguments": True,
    "approval_excludes_arguments": False,
    "approval_key_exclude_arguments": ["reason"],
    "description": "Executes a shell command and returns its output.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "reason": {
                "type": "string",
                "description": "Optional reason for running the command.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 30). Set to a higher value for long-running commands.",
                "default": DEFAULT_TIMEOUT_SECS,
                "minimum": 1,
            },
        },
        "required": ["command"],
    },
}


def execute_run_shell_command(
    command: str,
    stats,
    reason: str = None,
    timeout: int = DEFAULT_TIMEOUT_SECS,
    **kwargs,
) -> str:
    """Executes a shell command and returns its output.

    Args:
        command: The shell command to execute
        stats: Statistics object for tracking tool errors
        reason: Optional reason for running the command
        timeout: Timeout in seconds (default: from SHELL_COMMAND_TIMEOUT env var or 30)
        **kwargs: Additional arguments (tool_index, total_tools, etc.) that may be passed but are not used
    """
    try:
        shell_cmd = ["bash", "-c", command]

        # Execute the command
        result = subprocess.run(
            shell_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,  # Use the provided timeout
        )

        # Format the output
        output = f"Command: {command}\n"
        if reason:
            output += f"Reason: {reason}\n"
        output += f"Return code: {result.returncode}\n"
        if result.stdout:
            output += f"Stdout:\n{result.stdout}\n"
        if result.stderr:
            output += f"Stderr:\n{result.stderr}\n"

        return output
    except subprocess.TimeoutExpired:
        stats.tool_errors += 1
        return f"Error: Command '{command}' timed out after {timeout} seconds.\nTo retry with a longer timeout, use: run_shell_command(command=\"{command}\", timeout=60)"
    except Exception as e:
        stats.tool_errors += 1
        return f"Error executing command '{command}': {e}"

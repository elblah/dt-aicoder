"""
List directory internal tool implementation.
"""

import os
import subprocess

# Import the shared utility function
from ...utils import check_tool_availability

# Default limit for number of files to list
DEFAULT_FILE_LIMIT = 2000

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "approval_excludes_arguments": False,
    "approval_key_exclude_arguments": [],
    "description": f"Lists the contents of a specified directory recursively (limited to {DEFAULT_FILE_LIMIT} files).",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the directory.",
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


def _list_files_with_rg(path: str, file_limit: int = DEFAULT_FILE_LIMIT) -> str:
    """List files recursively using ripgrep."""
    try:
        # Use rg --files piped to head -n file_limit to limit output and prevent hanging on large directories
        cmd = ["bash", "-c", f"rg --files '{path}' | head -n {file_limit}"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            files = result.stdout.strip().split("\n")
            output = "\n".join(files) if files and files[0] else "No files found"
            # Check if we hit the limit
            if len(files) >= file_limit:
                output += f"\n... (showing first {file_limit} files)"
            return output
        else:
            return f"Error running rg: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing rg: {e}"


def _list_files_with_find(path: str, file_limit: int = DEFAULT_FILE_LIMIT) -> str:
    """List files recursively using find."""
    try:
        # Use find piped to head -n file_limit to limit output and prevent hanging on large directories
        cmd = [
            "bash",
            "-c",
            f"find '{path}' -type f -printf '%P\\n' | head -n {file_limit}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            files = [f for f in result.stdout.strip().split("\n") if f]
            output = "\n".join(files) if files and files[0] else "No files found"
            # Check if we hit the limit
            if len(files) >= file_limit:
                output += f"\n... (showing first {file_limit} files)"
            return output
        else:
            return f"Error running find: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing find: {e}"


def execute_list_directory(path: str, stats) -> str:
    """Lists the contents of a specified directory recursively."""
    try:
        if path == "":
            path = "."

        # Check if path exists and is a directory
        if not os.path.exists(path):
            stats.tool_errors += 1
            return f"Error: Directory not found at '{path}'."
        if not os.path.isdir(path):
            stats.tool_errors += 1
            return f"Error: Path '{path}' is not a directory."

        # Try ripgrep first if available
        if check_tool_availability("rg"):
            return _list_files_with_rg(path, DEFAULT_FILE_LIMIT)
        else:
            # Fallback to find
            return _list_files_with_find(path, DEFAULT_FILE_LIMIT)
    except Exception as e:
        stats.tool_errors += 1
        return f"Error listing directory '{path}': {e}"

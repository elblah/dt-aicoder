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
    "description": f"Lists the contents of a specified directory recursively. Uses fd-find when available, ripgrep as second choice, find as fallback. Limited to {DEFAULT_FILE_LIMIT} files.",
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
        # Use rg --files piped to head -n file_limit to limit output and prevent hanging on large directories (safe against injection)
        cmd = [
            "bash",
            "-c",
            f'{{ "$1" --files "$2"; }} | head -n {file_limit}',
            "_",
            "rg",
            path,
        ]

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


def _list_files_with_fd(
    path: str, file_limit: int = DEFAULT_FILE_LIMIT, command_name: str = "fd"
) -> str:
    """List files recursively using fd-find."""
    try:
        # Use fd/fdfind to list files, piped to head -n file_limit to limit output (safe against injection)
        cmd = [
            "bash",
            "-c",
            f'{{ "$1" . "$2" --type f; }} | head -n {file_limit}',
            "_",
            command_name,
            path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if (
            result.returncode == 0 or result.returncode == 1
        ):  # 0 = files found, 1 = no files
            files = [f for f in result.stdout.strip().split("\n") if f]
            output = "\n".join(files) if files and files[0] else "No files found"
            # Check if we hit the limit
            if len(files) >= file_limit:
                output += f"\n... (showing first {file_limit} files)"
            return output
        else:
            return f"Error running {command_name}: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing {command_name}: {e}"


def _list_files_with_find(path: str, file_limit: int = DEFAULT_FILE_LIMIT) -> str:
    """List files recursively using find."""
    try:
        # Use find piped to head -n file_limit to limit output and prevent hanging on large directories (safe against injection)
        cmd = [
            "bash",
            "-c",
            f'{{ "$1" "$2" -type f -printf "%P\\\\n"; }} | head -n {file_limit}',
            "_",
            "find",
            path,
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

        # Try tools in order of preference: fd/fdfind (fastest), ripgrep, find (fallback)
        if check_tool_availability("fd"):
            return _list_files_with_fd(path, DEFAULT_FILE_LIMIT, "fd")
        elif check_tool_availability("fdfind"):
            return _list_files_with_fd(path, DEFAULT_FILE_LIMIT, "fdfind")
        elif check_tool_availability("rg"):
            return _list_files_with_rg(path, DEFAULT_FILE_LIMIT)
        else:
            # Fallback to find
            return _list_files_with_find(path, DEFAULT_FILE_LIMIT)
    except Exception as e:
        stats.tool_errors += 1
        return f"Error listing directory '{path}': {e}"

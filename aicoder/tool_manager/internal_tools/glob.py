"""
Glob internal tool implementation using fd-find when available, Python glob as fallback.
"""

import glob
import os
import subprocess

# Import the shared utility function
from ...utils import check_tool_availability

# Default limit for number of files to return
DEFAULT_FILE_LIMIT = 2000

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "approval_excludes_arguments": False,
    "approval_key_exclude_arguments": [],
    "description": f"Find files matching a pattern using ripgrep when available, Python glob as fallback. Supports ** for recursive matching. Returns max {DEFAULT_FILE_LIMIT} files.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Pattern to search for (e.g., '*.py', 'test_*', '**/*.py', 'aicoder/**/*.py'). Supports ** for recursive directory matching.",
            }
        },
        "required": ["pattern"],
        "additionalProperties": False,
    },
}


def _search_with_rg(pattern: str, file_limit: int = DEFAULT_FILE_LIMIT) -> str:
    """Search for files using ripgrep with glob patterns."""
    try:
        # Use rg --files --glob for file listing with glob patterns (safe against injection)
        cmd = ["bash", "-c", f'{{ "$1" --files --glob "$2"; }} | head -n {file_limit}', "_", "rg", pattern]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 or result.returncode == 1:  # 0 = files found, 1 = no files
            lines = result.stdout.strip().split("\n")
            output = "\n".join(lines) if lines and lines[0] else "No files found matching pattern"
            # Check if we hit the limit
            if len(lines) >= file_limit:
                output += f"\n... (showing first {file_limit} lines)"
            return output
        else:
            return f"Error running rg: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing rg: {e}"


def _search_with_fd(pattern: str, file_limit: int = DEFAULT_FILE_LIMIT, command_name: str = "fd") -> str:
    """Search for files using fd-find."""
    try:
        # Use fd/fdfind with --glob for glob patterns and file count limit
        cmd = ["bash", "-c", f"{command_name} --glob '{pattern}' | head -n {file_limit}"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if (
            result.returncode == 0 or result.returncode == 1
        ):  # 0 = matches found, 1 = no matches
            lines = result.stdout.strip().split("\n")
            output = "\n".join(lines) if lines and lines[0] else "No files found matching pattern"
            # Check if we hit the limit
            if len(lines) >= file_limit:
                output += f"\n... (showing first {file_limit} lines)"
            return output
        else:
            return f"Error running {command_name}: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing {command_name}: {e}"


def _search_with_python_glob(pattern: str, file_limit: int = DEFAULT_FILE_LIMIT) -> str:
    """Search for files using Python's glob module."""
    try:
        # Use recursive=True for patterns containing **
        if "**" in pattern:
            matches = glob.glob(pattern, recursive=True)
        else:
            matches = glob.glob(pattern)

        # Filter to only include files (not directories)
        files = [match for match in matches if os.path.isfile(match)]

        if files:
            # Limit results
            if len(files) > file_limit:
                files = files[:file_limit]
                output = "\n".join(files)
                output += (
                    f"\n... (showing first {file_limit} files of {len(files)} total)"
                )
            else:
                output = "\n".join(files)
            return output
        else:
            return "No files found matching pattern"
    except Exception as e:
        return f"Error searching with glob: {e}"


def execute_glob(pattern: str, stats) -> str:
    """Find files matching a pattern using fd-find when available, Python glob as fallback."""
    try:
        # Validate input
        if not pattern:
            stats.tool_errors += 1
            return "Error: Pattern cannot be empty."

        # Try ripgrep first (compatible glob behavior), fallback to Python glob
        if check_tool_availability("rg"):
            return _search_with_rg(pattern, DEFAULT_FILE_LIMIT)
        else:
            # Fallback to Python glob for consistent behavior
            return _search_with_python_glob(pattern, DEFAULT_FILE_LIMIT)
    except Exception as e:
        stats.tool_errors += 1
        return f"Error searching for files with pattern '{pattern}': {e}"

"""
Glob internal tool implementation using pure Python.
"""

import glob
import os

# Default limit for number of files to return
DEFAULT_FILE_LIMIT = 2000

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "approval_excludes_arguments": False,
    "approval_key_exclude_arguments": [],
    "description": f"Find files matching a pattern using Python's glob. Supports ** for recursive matching. Returns max {DEFAULT_FILE_LIMIT} files.",
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
    """Find files matching a pattern using Python's glob."""
    try:
        # Validate input
        if not pattern:
            stats.tool_errors += 1
            return "Error: Pattern cannot be empty."

        # Use Python glob for cross-platform, reliable pattern matching
        return _search_with_python_glob(pattern, DEFAULT_FILE_LIMIT)
    except Exception as e:
        stats.tool_errors += 1
        return f"Error searching for files with pattern '{pattern}': {e}"

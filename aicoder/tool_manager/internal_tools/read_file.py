"""
Read file internal tool implementation.
"""

import os
from ...file_tracker import record_file_read

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "approval_excludes_arguments": False,
    "approval_key_exclude_arguments": [],
    "hide_results": True,
    "description": "Reads the content from a specified file path.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The file system path to read from.",
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


def execute_read_file(path: str, stats) -> str:
    """Reads the content from a specified file path."""
    try:
        # Convert to absolute path for consistent tracking
        abs_path = os.path.abspath(path)
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Record that we've read this file using absolute path
            record_file_read(abs_path)
            # Return just the content without JSON wrapper for cleaner display
            return content
    except FileNotFoundError:
        stats.tool_errors += 1
        return f"Error: File not found at '{abs_path}'."
    except Exception as e:
        stats.tool_errors += 1
        return f"Error reading file '{abs_path}': {e}"

"""
PWD internal tool implementation.
"""

import os

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "approval_excludes_arguments": False,
    "approval_key_exclude_arguments": [],
    "description": "Returns the current working directory.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


def execute_pwd(stats) -> str:
    """Returns the current working directory."""
    try:
        return os.getcwd()
    except Exception as e:
        stats.tool_errors += 1
        return f"Error getting current directory: {e}"

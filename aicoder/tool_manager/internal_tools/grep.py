"""
Grep internal tool implementation.
"""

import subprocess

# Import the shared utility function
from ...utils import check_tool_availability

# Default limit for number of lines to return
DEFAULT_LINE_LIMIT = 2000

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": True,
    "approval_excludes_arguments": False,
    "approval_key_exclude_arguments": [],
    "description": f"Search text in files in the current directory using ripgrep. Returns max {DEFAULT_LINE_LIMIT} lines.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to search for.",
            }
        },
        "required": ["text"],
        "additionalProperties": False,
    },
}


def _search_with_rg(text: str, line_limit: int = DEFAULT_LINE_LIMIT) -> str:
    """Search text using ripgrep."""
    try:
        # Use rg with line limit
        cmd = ["bash", "-c", f"rg '{text}' | head -n {line_limit}"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if (
            result.returncode == 0 or result.returncode == 1
        ):  # 0 = matches found, 1 = no matches
            lines = result.stdout.strip().split("\n")
            output = "\n".join(lines) if lines and lines[0] else "No matches found"
            # Check if we hit the limit
            if len(lines) >= line_limit:
                output += f"\n... (showing first {line_limit} lines)"
            return output
        else:
            return f"Error running rg: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing rg: {e}"


def _search_with_grep(text: str, line_limit: int = DEFAULT_LINE_LIMIT) -> str:
    """Search text using grep."""
    try:
        # Use grep with line limit
        cmd = ["bash", "-c", f"grep -r '{text}' . | head -n {line_limit}"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if (
            result.returncode == 0 or result.returncode == 1
        ):  # 0 = matches found, 1 = no matches
            lines = result.stdout.strip().split("\n")
            output = "\n".join(lines) if lines and lines[0] else "No matches found"
            # Check if we hit the limit
            if len(lines) >= line_limit:
                output += f"\n... (showing first {line_limit} lines)"
            return output
        else:
            return f"Error running grep: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing grep: {e}"


def execute_grep(text: str, stats) -> str:
    """Search for text in files using ripgrep or fallback to grep."""
    try:
        # Validate input
        if not text:
            stats.tool_errors += 1
            return "Error: Search text cannot be empty."

        # Try ripgrep first if available
        if check_tool_availability("rg"):
            return _search_with_rg(text, DEFAULT_LINE_LIMIT)
        else:
            # Fallback to grep
            return _search_with_grep(text, DEFAULT_LINE_LIMIT)
    except Exception as e:
        stats.tool_errors += 1
        return f"Error searching for '{text}': {e}"

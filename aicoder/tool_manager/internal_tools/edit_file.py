"""
Edit file internal tool implementation - Production-ready version with safety checks.
"""

import os
import difflib
from typing import Dict, Any
from ..file_tracker import record_file_read, check_file_modification_strict

# Environment variable to control write_file suggestions
ENABLE_WRITEFILE_SUGGESTIONS = os.getenv("ENABLE_WRITEFILE_SUGGESTIONS", "true").lower() == "true"

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": False,
    "approval_excludes_arguments": True,
    "approval_key_exclude_arguments": ["old_string", "new_string"],
    "hidden_parameters": ["old_string", "new_string"],
    "available_in_plan_mode": False,
    "description": """Edits files by replacing text, creating new files, or deleting content.

CRITICAL REQUIREMENTS:
- You MUST use read_file to understand the current file content before making edits
- old_string must match the file content exactly, including whitespace and line breaks
- Provide sufficient context to uniquely identify the text to replace

UNIQUE MATCHING:
- old_string must be unique - the tool will fail if it appears multiple times
- Include 3-5 lines of context before/after the change point when possible
- If old_string appears multiple times, provide more context to make it unique

SPECIAL CASES:
- Create new file: old_string="", new_string="content"
- Delete content: new_string=""

WARNING: If old_string doesn't match exactly or appears multiple times, the operation will fail. For multiple edits, consider using write_file instead.""",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The absolute path to the file to modify",
            },
            "old_string": {
                "type": "string",
                "description": "The text to replace (must be unique within the file, and must match the file contents exactly, including all whitespace and indentation)",
            },
            "new_string": {
                "type": "string",
                "description": "The edited text to replace the old_string",
            },
        },
        "required": ["path", "old_string", "new_string"],
    },
    "validate_function": "validate_edit_file",
}


def generate_diff(old_content: str, new_content: str, path: str) -> str:
    """Generate a unified diff between old and new content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile=f"{path} (old)", tofile=f"{path} (new)"
    )

    # Convert generator to list and join properly
    diff_lines = list(diff)
    return "".join(diff_lines)


def execute_edit_file(
    path: str,
    old_string: str,
    new_string: str,
    stats=None,
) -> str:
    """
    Edit a file with safety checks similar to production-ready implementations.

    Args:
        path: Path to the file to edit
        old_string: Text to be replaced (must be unique)
        new_string: Replacement text
        stats: Stats object to track tool usage

    Returns:
        String with results of the operation
    """
    try:
        # Convert to absolute path
        path = os.path.abspath(path)
        
        # Track edit for efficiency optimization
        # We need to pass message_history, but it's not available directly in edit_file
        # The tracking will be handled at the executor level where message_history is available

        # Handle file creation (when old_string is empty)
        if old_string == "":
            return _create_new_file(path, new_string, stats)

        # Handle content deletion (when new_string is empty)
        if new_string == "":
            return _delete_content(path, old_string, stats)

        # Handle content replacement
        return _replace_content(path, old_string, new_string, stats)

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error editing file '{path}': {e}"


def _create_new_file(path: str, content: str, stats) -> str:
    """Create a new file."""
    try:
        # Check if file already exists
        if os.path.exists(path):
            if os.path.isdir(path):
                return f"Error: Path is a directory, not a file: {path}"
            return f"Error: File already exists: {path}"

        # Create parent directories if they don't exist
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        # Write the file
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        # Record file operations
        record_file_read(path)

        return f"Successfully created '{path}' ({len(content)} characters)."

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error creating file '{path}': {e}"


def _delete_content(path: str, old_string: str, stats) -> str:
    """Delete content from a file."""
    try:
        # Check if file exists
        if not os.path.exists(path):
            return f"Error: File not found: {path}"

        # Check if it's a directory
        if os.path.isdir(path):
            return f"Error: Path is a directory, not a file: {path}"

        # Check if file was modified since last read
        mod_check_error = check_file_modification_strict(path)
        if mod_check_error:
            return mod_check_error

        # Read current content
        with open(path, "r", encoding="utf-8") as f:
            old_content = f.read()

        # Check if old_string exists
        if old_string not in old_content:
            error_msg = "Error: old_string not found in file. Make sure it matches exactly, including whitespace and line breaks"
            if ENABLE_WRITEFILE_SUGGESTIONS:
                error_msg += "\nSUGGESTION: Use write_file instead - read the file first, then make comprehensive changes"
            return error_msg

        # Check if old_string is unique
        first_index = old_content.find(old_string)
        last_index = old_content.rfind(old_string)
        if first_index != last_index:
            error_msg = "Error: old_string appears multiple times in the file. Please provide more context to ensure a unique match"
            if ENABLE_WRITEFILE_SUGGESTIONS:
                error_msg += ("\nSUGGESTION: For complex changes with multiple matches, use write_file instead:\n"
                             "1. Read the file with read_file()\n"
                             "2. Make all necessary changes\n"
                             "3. Write back with write_file()")
            return error_msg

        # Create new content
        new_content = (
            old_content[:first_index] + old_content[first_index + len(old_string) :]
        )

        # Write the file
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Record file operations
        record_file_read(path)

        return f"Successfully updated '{path}' ({len(new_content)} characters)."

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error deleting content from file '{path}': {e}"


def _replace_content(path: str, old_string: str, new_string: str, stats) -> str:
    """Replace content in a file."""
    try:
        # Check if file exists
        if not os.path.exists(path):
            return f"Error: File not found: {path}"

        # Check if it's a directory
        if os.path.isdir(path):
            return f"Error: Path is a directory, not a file: {path}"

        # Check if file was modified since last read
        mod_check_error = check_file_modification_strict(path)
        if mod_check_error:
            return mod_check_error

        # Read current content
        with open(path, "r", encoding="utf-8") as f:
            old_content = f.read()

        # Check if old_string exists
        if old_string not in old_content:
            return "Error: old_string not found in file. Make sure it matches exactly, including whitespace and line breaks"

        # Check if old_string is unique
        first_index = old_content.find(old_string)
        last_index = old_content.rfind(old_string)
        if first_index != last_index:
            return "Error: old_string appears multiple times in the file. Please provide more context to ensure a unique match"

        # Check if content is actually changing
        if old_string == new_string:
            return "Error: new content is the same as old content. No changes made."

        # Create new content
        new_content = (
            old_content[:first_index]
            + new_string
            + old_content[first_index + len(old_string) :]
        )

        # Write the file
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Record file operations
        record_file_read(path)

        return f"Successfully updated '{path}' ({len(new_content)} characters)."

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error replacing content in file '{path}': {e}"


def validate_edit_file(arguments: Dict[str, Any]) -> str | bool:
    """Pre-validate edit_file arguments to avoid prompting for operations that will fail.

    Returns:
        True if validation passes
        Error message string if validation fails
    """
    try:
        import os

        path = arguments.get("path", "")
        old_string = arguments.get("old_string", "")
        new_string = arguments.get("new_string", "")

        # Handle file creation (when old_string is empty)
        if old_string == "":
            # For file creation, just check if file already exists
            if os.path.exists(path) and os.path.isdir(path):
                return f"Error: Path is a directory, not a file: {path}"
            return True

        # Handle content deletion or replacement
        # Check if file exists
        if not os.path.exists(path):
            return f"Error: File not found: {path}"

        # Check if it's a directory
        if os.path.isdir(path):
            return f"Error: Path is a directory, not a file: {path}"

        # Read current content
        try:
            with open(path, "r", encoding="utf-8") as f:
                old_content = f.read()
        except Exception as e:
            return f"Error reading file '{path}': {e}"

        # Check if old_string exists (for deletion or replacement)
        if old_string != "" and old_string not in old_content:
            error_msg = "Error: old_string not found in file. Make sure it matches exactly, including whitespace and line breaks"
            if ENABLE_WRITEFILE_SUGGESTIONS:
                error_msg += "\nSUGGESTION: Use write_file instead - read the file first, then make comprehensive changes"
            return error_msg

        # Check if old_string is unique (if it exists)
        if old_string != "":
            first_index = old_content.find(old_string)
            last_index = old_content.rfind(old_string)
            if first_index != last_index:
                error_msg = "Error: old_string appears multiple times in the file. Please provide more context to ensure a unique match"
                if ENABLE_WRITEFILE_SUGGESTIONS:
                    error_msg += ("\nSUGGESTION: For complex changes with multiple matches, use write_file instead:\n"
                                 "1. Read the file with read_file()\n"
                                 "2. Make all necessary changes\n"
                                 "3. Write back with write_file()")
                return error_msg

        # Check if content is actually changing (for replacement)
        if old_string != "" and new_string != "" and old_string == new_string:
            return "Error: new content is the same as old content. No changes made."

        return True

    except Exception as e:
        return f"Error during pre-validation: {e}"

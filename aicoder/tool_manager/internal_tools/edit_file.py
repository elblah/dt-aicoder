"""
Edit file internal tool implementation - Production-ready version with safety checks.
"""

import os
import difflib
from typing import Dict, Any
from ...utils import colorize_diff_lines
from ...file_tracker import record_file_read, check_file_modification_strict

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": False,
    "approval_excludes_arguments": True,
    "approval_key_exclude_arguments": ["old_string", "new_string"],
    "hidden_parameters": ["old_string", "new_string"],
    "description": """Edits files by replacing text, creating new files, or deleting content.

FINANCIAL AWARENESS: Use this tool for small, precise changes (1-20 lines) where you need to maintain context. For large changes or complete rewrites, consider write_file if the edit cost (sending old_content + new_content) is greater than the file size.

CRITICAL FINANCIAL PRINCIPLE: Before making multiple changes to the same file, calculate the total cost. If you plan to make multiple edit_file calls on the same file, compare:
- Total cost of all edit_file calls vs. 
- Single write_file call cost (file size)
If multiple edits cost more than a single write, use write_file instead.

CRITICAL REQUIREMENT - READ FIRST: You MUST use read_file to understand the current file content before making edits. This tool requires exact matching of existing content, including whitespace and line breaks.

CRITICAL REQUIREMENTS FOR USING THIS TOOL:

1. UNIQUENESS: The old_string MUST uniquely identify the specific instance you want to change. This means:
   - Include AT LEAST 3-5 lines of context BEFORE the change point
   - Include AT LEAST 3-5 lines of context AFTER the change point
   - Include all whitespace, indentation, and surrounding code exactly as it appears in the file

2. SINGLE INSTANCE: This tool can only change ONE instance at a time. If you need to change multiple instances:
   - Make separate calls to this tool for each instance
   - Each call must uniquely identify its specific instance using extensive context

3. VERIFICATION: Before using this tool:
   - Check how many instances of the target text exist in the file
   - If multiple instances exist, gather enough context to uniquely identify each one
   - Plan separate tool calls for each instance

WARNING: If you do not follow these requirements:
   - The tool will fail if old_string matches multiple locations
   - The tool will fail if old_string doesn't match exactly (including whitespace)
   - You may change the wrong instance if you don't include enough context

Special cases:
- To create a new file: provide file_path and new_string, leave old_string empty
- To delete content: provide file_path and old_string, leave new_string empty""",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
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
        "required": ["file_path", "old_string", "new_string"],
    },
    "validate_function": "validate_edit_file",
}


def generate_diff(old_content: str, new_content: str, file_path: str) -> str:
    """Generate a unified diff between old and new content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines, new_lines, fromfile=f"{file_path} (old)", tofile=f"{file_path} (new)"
    )

    # Convert generator to list and join properly
    diff_lines = list(diff)
    return "".join(diff_lines)


def execute_edit_file(
    file_path: str,
    old_string: str,
    new_string: str,
    stats=None,
) -> str:
    """
    Edit a file with safety checks similar to production-ready implementations.

    Args:
        file_path: Path to the file to edit
        old_string: Text to be replaced (must be unique)
        new_string: Replacement text
        stats: Stats object to track tool usage

    Returns:
        String with results of the operation
    """
    try:
        # Convert to absolute path
        file_path = os.path.abspath(file_path)

        # Handle file creation (when old_string is empty)
        if old_string == "":
            return _create_new_file(file_path, new_string, stats)

        # Handle content deletion (when new_string is empty)
        if new_string == "":
            return _delete_content(file_path, old_string, stats)

        # Handle content replacement
        return _replace_content(file_path, old_string, new_string, stats)

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error editing file '{file_path}': {e}"


def _create_new_file(file_path: str, content: str, stats) -> str:
    """Create a new file."""
    try:
        # Check if file already exists
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                return f"Error: Path is a directory, not a file: {file_path}"
            return f"Error: File already exists: {file_path}"

        # Create parent directories if they don't exist
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        # Write the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Record file operations
        record_file_read(file_path)

        # Show a diff-like output for consistency with write_file
        # For new files, show the content being created (similar to write_file behavior)
        content_preview = content[:500] + "..." if len(content) > 500 else content
        return f"Successfully created '{file_path}' ({len(content)} characters).\n\nContent:\n{content_preview}"

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error creating file '{file_path}': {e}"


def _delete_content(file_path: str, old_string: str, stats) -> str:
    """Delete content from a file."""
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        # Check if it's a directory
        if os.path.isdir(file_path):
            return f"Error: Path is a directory, not a file: {file_path}"

        # Check if file was modified since last read
        mod_check_error = check_file_modification_strict(file_path)
        if mod_check_error:
            return mod_check_error

        # Read current content
        with open(file_path, "r", encoding="utf-8") as f:
            old_content = f.read()

        # Check if old_string exists
        if old_string not in old_content:
            return "Error: old_string not found in file. Make sure it matches exactly, including whitespace and line breaks"

        # Check if old_string is unique
        first_index = old_content.find(old_string)
        last_index = old_content.rfind(old_string)
        if first_index != last_index:
            return "Error: old_string appears multiple times in the file. Please provide more context to ensure a unique match"

        # Create new content
        new_content = (
            old_content[:first_index] + old_content[first_index + len(old_string) :]
        )

        # Generate diff
        diff = generate_diff(old_content, new_content, file_path)
        # Colorize the diff
        colored_diff = colorize_diff_lines(diff)

        # Write the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Record file operations
        record_file_read(file_path)

        return f"Successfully updated '{file_path}' ({len(new_content)} characters).\n\nChanges:\n{colored_diff}"

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error deleting content from file '{file_path}': {e}"


def _replace_content(file_path: str, old_string: str, new_string: str, stats) -> str:
    """Replace content in a file."""
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        # Check if it's a directory
        if os.path.isdir(file_path):
            return f"Error: Path is a directory, not a file: {file_path}"

        # Check if file was modified since last read
        mod_check_error = check_file_modification_strict(file_path)
        if mod_check_error:
            return mod_check_error

        # Read current content
        with open(file_path, "r", encoding="utf-8") as f:
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

        # Generate diff
        diff = generate_diff(old_content, new_content, file_path)
        # Colorize the diff
        colored_diff = colorize_diff_lines(diff)

        # Write the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Record file operations
        record_file_read(file_path)

        return f"Successfully updated '{file_path}' ({len(new_content)} characters).\n\nChanges:\n{colored_diff}"

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error replacing content in file '{file_path}': {e}"


def validate_edit_file(arguments: Dict[str, Any]) -> str | bool:
    """Pre-validate edit_file arguments to avoid prompting for operations that will fail.

    Returns:
        True if validation passes
        Error message string if validation fails
    """
    try:
        import os

        file_path = arguments.get("file_path", "")
        old_string = arguments.get("old_string", "")
        new_string = arguments.get("new_string", "")

        # Handle file creation (when old_string is empty)
        if old_string == "":
            # For file creation, just check if file already exists
            if os.path.exists(file_path) and os.path.isdir(file_path):
                return f"Error: Path is a directory, not a file: {file_path}"
            return True

        # Handle content deletion or replacement
        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        # Check if it's a directory
        if os.path.isdir(file_path):
            return f"Error: Path is a directory, not a file: {file_path}"

        # Read current content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                old_content = f.read()
        except Exception as e:
            return f"Error reading file '{file_path}': {e}"

        # Check if old_string exists (for deletion or replacement)
        if old_string != "" and old_string not in old_content:
            return "Error: old_string not found in file. Make sure it matches exactly, including whitespace and line breaks"

        # Check if old_string is unique (if it exists)
        if old_string != "":
            first_index = old_content.find(old_string)
            last_index = old_content.rfind(old_string)
            if first_index != last_index:
                return "Error: old_string appears multiple times in the file. Please provide more context to ensure a unique match"

        # Check if content is actually changing (for replacement)
        if old_string != "" and new_string != "" and old_string == new_string:
            return "Error: new content is the same as old content. No changes made."

        return True

    except Exception as e:
        return f"Error during pre-validation: {e}"

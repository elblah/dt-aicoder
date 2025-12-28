"""
Edit file internal tool implementation.
"""

import os
import difflib
from typing import Dict, Any, List
from ..file_tracker import record_file_read, check_file_modification_strict
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": False,
    "approval_excludes_arguments": True,
    "approval_key_exclude_arguments": ["old_string", "new_string"],
    "hidden_parameters": ["old_string", "new_string"],
    "available_in_plan_mode": False,
    "description": """Efficiently edit files by replacing exact text matches.

REQUIREMENTS:
- Must use read_file first to understand file content
- old_string must match file content EXACTLY (including whitespace)
- old_string must be unique within the file

COMMON OPERATIONS:
- Replace text: Provide both old_string and new_string
- Delete text: new_string = "" (empty string)
- Add text: old_string = "" with existing file path

UNIQUE MATCHING:
- If old_string appears multiple times, operation fails
- Add more context to make old_string unique
- Example: Include 2-3 lines before/after the target

PERFORMANCE NOTE:
- More efficient than write_file for single changes
- Avoids rewriting entire file when possible
- Preserves file permissions and metadata""",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to file to edit",
            },
            "old_string": {
                "type": "string",
                "description": "Text to replace (must match file content exactly)",
            },
            "new_string": {
                "type": "string",
                "description": "New text to replace old_string with",
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


def count_occurrences(content: str, substring: str) -> int:
    """Count occurrences of a substring."""
    count = 0
    pos = 0

    while (pos := content.find(substring, pos)) != -1:
        count += 1
        pos += len(substring)

    return count


def get_occurrence_positions(content: str, substring: str) -> List[int]:
    """Get line positions where substring occurs."""
    positions = []
    pos = 0

    while (pos := content.find(substring, pos)) != -1:
        line_num = content[:pos].count('\n') + 1
        positions.append(line_num)
        pos += len(substring)

    return positions


def generate_not_found_suggestion(content: str, old_string: str, path: str) -> str:
    """Generate suggestion when old_string not found."""
    return f"Use read_file('{path}') to see current content and ensure old_string matches exactly."


def execute_edit_file(
    path: str,
    old_string: str,
    new_string: str,
    stats=None,
) -> str:
    """
    Edit a file.

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

        # Handle file creation (when old_string is empty)
        if old_string == "":
            return _create_file(path, new_string, stats)

        # Handle content replacement (including deletion when new_string is empty)
        return _replace_content(path, old_string, new_string, stats)

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error editing file '{path}': {e}"


def _create_file(path: str, content: str, stats) -> str:
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

        return f"Successfully created '{path}' ({len(content)} characters)"

    except Exception as e:
        if stats:
            stats.tool_errors += 1
        return f"Error creating file: {e}"


def _replace_content(
    path: str,
    old_string: str,
    new_string: str,
    stats,
) -> str:
    """Replace content in existing file."""
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
            content = f.read()

        # Check if old_string exists
        if old_string not in content:
            suggestion = generate_not_found_suggestion(content, old_string, path)
            return f"Error: old_string not found in file. {suggestion}"

        # Check for multiple matches
        occurrences = count_occurrences(content, old_string)
        if occurrences > 1:
            positions = get_occurrence_positions(content, old_string)
            return f"Error: old_string appears {occurrences} times in file. Please provide more context to make it unique."

        # Check if content is actually changing
        if old_string == new_string:
            return "Error: new_string is the same as old_string. No changes needed."

        # Perform replacement
        new_content = content.replace(old_string, new_string)

        # Write back to file
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # Record file operations
        record_file_read(path)

        return f"Successfully updated '{path}' ({len(new_content)} characters)"

    except Exception as e:
        return f"Error replacing content in file: {e}"


def validate_edit_file(arguments: Dict[str, Any]) -> str | bool:
    """Pre-validation."""
    try:
        path = arguments.get("path", "")
        old_string = arguments.get("old_string", "")
        new_string = arguments.get("new_string", "")

        # Handle file creation (when old_string is empty)
        if old_string == "":
            # For file creation, just check if file already exists
            if os.path.exists(path) and os.path.isdir(path):
                return f"Error: Path is a directory, not a file: {path}"
            return True

        # Handle content replacement
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
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return f"Error reading file '{path}': {e}"

        # Check if old_string exists
        if old_string not in content:
            suggestion = generate_not_found_suggestion(content, old_string, path)
            return f"Error: old_string not found in file. {suggestion}"

        # Check if old_string is unique
        occurrences = count_occurrences(content, old_string)
        if occurrences > 1:
            return f"Error: old_string appears {occurrences} times in file. Please provide more context to make it unique."

        # Check if content is actually changing
        if old_string == new_string:
            return "Error: new_string is the same as old_string. No changes needed."

        return True

    except Exception as e:
        return f"Error during pre-validation: {e}"
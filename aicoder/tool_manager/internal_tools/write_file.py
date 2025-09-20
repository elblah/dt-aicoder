"""
Write file internal tool implementation.
"""

import os
import difflib
from ...utils import colorize_diff_lines
from ...file_tracker import check_file_modification

# Tool metadata
TOOL_DEFINITION = {
    "type": "internal",
    "auto_approved": False,
    "approval_excludes_arguments": True,
    "approval_key_exclude_arguments": ["content"],
    "hidden_parameters": ["content"],
    "description": """Writes content to a specified file path, creating directories if needed. Checks if file was modified since last read.

FINANCIAL AWARENESS: Use this tool for large changes, complete rewrites, or when edit_file cost (sending old_content + new_content) is greater than the file size. For small, precise changes where you need to maintain context, consider edit_file instead.

CRITICAL REQUIREMENT - READ FIRST: You MUST use read_file to understand the current file content before making significant changes to EXISTING files. This tool checks if the file was modified since it was last read to prevent accidental overwrites. For new files, reading is not required.""",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The file system path where the content should be written.",
            },
            "content": {
                "type": "string",
                "description": "The content to write into the file.",
            },
        },
        "required": ["path", "content"],
    },
}


def execute_write_file(path: str, content: str, stats) -> str:
    """Writes content to a specified file path, creating directories if needed."""
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(path)

        # Check if file already exists and read its content first
        file_existed = os.path.exists(abs_path)
        old_content = ""
        if file_existed:
            try:
                with open(abs_path, "r", encoding="utf-8") as f:
                    old_content = f.read()
            except Exception as e:
                # If we can't read the old content, warn but continue
                print(f"Warning: Could not read existing file '{abs_path}': {e}")
                pass

            # Check if file was modified since last read (if we have tracking)
            mod_check_error = check_file_modification(abs_path)
            if mod_check_error:
                return mod_check_error

        # Create parent directories if they don't exist
        directory = os.path.dirname(abs_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Generate appropriate response based on whether file existed
        if not file_existed:
            return f"Successfully created '{abs_path}' ({len(content)} characters)."
        else:
            # For existing files, show a simple diff if content changed
            if old_content == content:
                return f"File '{abs_path}' unchanged."
            else:
                # Simple line-based diff
                old_lines = old_content.splitlines(keepends=True)
                new_lines = content.splitlines(keepends=True)
                diff = list(
                    difflib.unified_diff(
                        old_lines,
                        new_lines,
                        fromfile=f"{abs_path} (old)",
                        tofile=f"{abs_path} (new)",
                    )
                )

                if diff:
                    # Colorize the diff output using our new function
                    diff_text = colorize_diff_lines("".join(diff))
                    return f"Successfully updated '{abs_path}' ({len(content)} characters).\n\nChanges:\n{diff_text}"
                else:
                    return f"Successfully updated '{abs_path}' ({len(content)} characters)."

    except Exception as e:
        stats.tool_errors += 1
        return f"Error writing to file '{abs_path}': {e}"

"""
Read file internal tool implementation.
"""

import os
from ..file_tracker import record_file_read

# Constants
DEFAULT_READ_LIMIT = 2000
MAX_LINE_LENGTH = 2000

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
            },
            "offset": {
                "type": "integer",
                "description": "The line number to start reading from (0-based).",
                "minimum": 0,
            },
            "limit": {
                "type": "integer",
                "description": f"The number of lines to read (defaults to {DEFAULT_READ_LIMIT}).",
                "minimum": 1,
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


def execute_read_file(path: str, stats, offset: int = None, limit: int = None) -> str:
    """Reads the content from a specified file path with optional pagination."""
    try:
        # Convert to absolute path for consistent tracking
        abs_path = os.path.abspath(path)
        
        # Apply pagination defaults
        start_line = offset if offset is not None else 0
        max_lines = limit if limit is not None else DEFAULT_READ_LIMIT
        
        # Skip to the start line efficiently
        with open(abs_path, "r", encoding="utf-8") as f:
            # Skip lines until we reach the offset
            for _ in range(start_line):
                if f.readline() == "":
                    # File ended before reaching offset
                    record_file_read(abs_path)
                    return ""
            
            # Read only the lines we need
            lines = []
            lines_were_truncated = False
            
            for i in range(max_lines):
                line = f.readline()
                if line == "":
                    break  # End of file
                
                # Truncate lines that are too long
                if len(line) > MAX_LINE_LENGTH:
                    # Remove trailing whitespace before adding "..."
                    truncated_line = line[:MAX_LINE_LENGTH].rstrip() + "..."
                    lines.append(truncated_line)
                    lines_were_truncated = True
                else:
                    # Remove trailing newline for cleaner output
                    lines.append(line.rstrip())
            
            # Check if there are more lines by trying to read one more
            has_more_lines = f.readline() != ""
            
            content = "\n".join(lines)
            
            # Add truncation warnings if needed
            warnings = []
            
            if lines_were_truncated:
                warnings.append(f"⚠️  Some lines were truncated to {MAX_LINE_LENGTH} characters")
            
            if has_more_lines:
                warnings.append(f"📄 File has more lines. Use offset={start_line + len(lines)} to read further")
            
            if warnings:
                content += "\n\n" + " | ".join(warnings)
            
            # Record that we've read this file using absolute path
            record_file_read(abs_path)
            return content
            
    except FileNotFoundError:
        stats.tool_errors += 1
        return f"Error: File not found at '{abs_path}'."
    except Exception as e:
        stats.tool_errors += 1
        return f"Error reading file '{abs_path}': {e}"

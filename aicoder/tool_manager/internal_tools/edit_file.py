"""
Edit file internal tool implementation - Production-ready version with safety checks.
"""

import os
import difflib
from typing import Dict, Any
from ..file_tracker import record_file_read, check_file_modification_strict

# Environment variable to control write_file suggestions
ENABLE_WRITEFILE_SUGGESTIONS = (
    os.getenv("ENABLE_WRITEFILE_SUGGESTIONS", "true").lower() == "true"
)

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
            "metadata": {
                "type": "boolean",
                "description": "Include optional metadata like search suggestions and context (default: False).",
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


def _quick_word_search(content: str, search_text: str) -> str | None:
    """Fast word-based location finding."""
    # Extract meaningful words (skip common words)
    skip_words = {
        "def",
        "if",
        "for",
        "while",
        "return",
        "class",
        "import",
        "from",
        "the",
        "and",
        "or",
        "not",
    }
    words = [
        w for w in search_text.split() if len(w) >= 3 and w.lower() not in skip_words
    ][:3]

    if not words:
        return None

    lines = content.splitlines()
    best_matches = []

    for word in words:
        for i, line in enumerate(lines):
            if word.lower() in line.lower():
                # Calculate relevance score
                score = _calculate_relevance_score(word, line, i)
                best_matches.append((score, i + 1, line.strip(), word))

    if best_matches:
        # Sort by relevance and return the best
        best_matches.sort(reverse=True)
        score, line_num, line, word = best_matches[0]
        confidence = "[HIGH]" if score > 0.8 else "[MEDIUM]"
        return f"{confidence} Found '{word}' near line {line_num}: {line[:60]}..."

    return None


def _should_use_fuzzy_search(search_text: str) -> bool:
    """Determine if fuzzy search is worth the cost."""
    # Use fuzzy search for longer, more specific content
    lines = search_text.splitlines()

    # Skip for very short content
    if len(search_text.strip()) < 20:
        return False

    # Skip for single common words
    if len(lines) == 1 and len(search_text.split()) <= 2:
        return False

    # Use fuzzy for multi-line or longer content
    return len(lines) > 1 or len(search_text) > 50


def _fuzzy_search(content: str, search_text: str) -> str | None:
    """Thorough fuzzy search with SequenceMatcher."""
    from difflib import SequenceMatcher

    lines = content.splitlines()
    old_lines = search_text.splitlines()

    best_match = None
    best_ratio = 0.0

    # Search through the file, but limit scope for performance
    search_limit = min(1000, len(lines))

    for i in range(search_limit):
        for j in range(min(3, len(old_lines) + 1)):
            if i + j >= len(lines):
                break

            content_snippet = "\n".join(lines[i : i + j + 1])

            # Skip very long snippets
            if len(content_snippet) > 300:
                continue

            ratio = SequenceMatcher(
                None, search_text.strip(), content_snippet.strip()
            ).ratio()

            if ratio > best_ratio and ratio > 0.6:  # Threshold for "similar enough"
                best_ratio = ratio
                best_match = (i + 1, content_snippet)

    if best_match:
        line_num, similar_content = best_match
        confidence = "[HIGH]" if best_ratio > 0.8 else "[MEDIUM]"
        return f"{confidence} {best_ratio:.0%} similar content at line {line_num}: {similar_content[:60]}..."

    return None


def _calculate_relevance_score(word: str, line: str, line_index: int) -> float:
    """Calculate relevance score for word matches."""
    word_lower = word.lower()
    line_lower = line.lower()

    score = 0.0

    # Exact match gets bonus
    if word_lower == line_lower.strip():
        score += 1.0

    # Word at start of line gets bonus
    if line_lower.startswith(word_lower):
        score += 0.5

    # Word appears in function/class definition gets bonus
    if any(keyword in line_lower for keyword in ["def ", "class ", "function "]):
        score += 0.3

    # Shorter lines are more specific (less noise)
    score += max(0, (100 - len(line)) / 200)

    return score


def _generate_not_found_error(content: str, old_string: str, path: str, metadata: bool = False) -> str:
    """Generate a helpful error message using hybrid search approach."""
    base_error = f"Error: [X] Match not found"
    
    if not metadata:
        return f"{base_error}. Try read_file('{path}') to see current content"
    
    # With metadata=True, provide all available search information
    
    # Phase 1: Quick word search for common cases
    word_result = _quick_word_search(content, old_string)
    
    # Phase 2: Fuzzy search for substantial searches
    fuzzy_result = None
    if _should_use_fuzzy_search(old_string):
        fuzzy_result = _fuzzy_search(content, old_string)
    
    # Build comprehensive error message
    if word_result or fuzzy_result:
        search_info = []
        if word_result:
            search_info.append(word_result)
        if fuzzy_result:
            search_info.append(fuzzy_result)
        
        return f"{base_error}. {' | '.join(search_info)}"
    
    # Phase 3: Basic suggestion
    return f"{base_error}. Try read_file('{path}') to see current content"


def _generate_multiple_matches_error(content: str, old_string: str, path: str, metadata: bool = False) -> str:
    """Generate a helpful error message when old_string appears multiple times."""
    lines = content.splitlines()
    old_lines = old_string.splitlines()

    # Find occurrences efficiently (limit to avoid performance issues)
    occurrences = []
    content_lower = content.lower()
    old_lower = old_string.lower()

    pos = 0
    max_matches = 20  # Limit to prevent huge outputs
    while pos < len(content) and len(occurrences) < max_matches:
        pos = content_lower.find(old_lower, pos)
        if pos == -1:
            break

        line_num = content[:pos].count("\n") + 1
        occurrences.append(line_num)
        pos += 1

    # Basic error is always shown
    error_msg = f"Error: [X] MULTIPLE MATCHES in '{path}'\n"
    error_msg += (
        f"Found {len(occurrences)}+ occurrences (showing first {len(occurrences)})\n"
    )
    error_msg += f"Lines: {', '.join(map(str, occurrences[:10]))}"
    if len(occurrences) > 10:
        error_msg += " (and more...)"
    
    if not metadata:
        return error_msg
    
    # With metadata=True, provide full context and suggestions
    error_msg += "\n\n"
    error_msg += "TO FIX: Add unique context to identify the specific match\n"
    error_msg += "   • Include 2-3 lines before your change\n"
    error_msg += "   • Include 2-3 lines after your change\n"
    error_msg += "   • Choose a more specific part of the text\n\n"

    # Show minimal context for first 2 matches only
    error_msg += "Example contexts (pick one and add surrounding lines):\n"
    for i, line_num in enumerate(occurrences[:2]):
        start = max(0, line_num - 2)
        end = min(len(lines), line_num + len(old_lines))

        error_msg += f"\n--- Match {i + 1} around line {line_num} ---\n"
        for j in range(start, end):
            marker = (
                ">>> "
                if j >= line_num - 1 and j < line_num - 1 + len(old_lines)
                else "    "
            )
            # Truncate very long lines
            line = lines[j]
            if len(line) > 100:
                line = line[:97] + "..."
            error_msg += f"{marker}{j + 1:3d}: {line}\n"

    if len(occurrences) > 2:
        error_msg += f"... and {len(occurrences) - 2} more matches\n"

    error_msg += "\nALTERNATIVE: Use write_file for multi-location changes:\n"
    error_msg += f"   1. read_file('{path}')\n"
    error_msg += "   2. Make all changes\n"
    error_msg += f"   3. write_file('{path}', modified_content)"

    return error_msg


def execute_edit_file(
    path: str,
    old_string: str,
    new_string: str,
    stats=None,
    metadata: bool = False,
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
            return _delete_content(path, old_string, stats, metadata)

        # Handle content replacement
        return _replace_content(path, old_string, new_string, stats, metadata)

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


def _delete_content(path: str, old_string: str, stats, metadata: bool = False) -> str:
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
            return _generate_not_found_error(old_content, old_string, path, metadata)

        # Check if old_string is unique
        first_index = old_content.find(old_string)
        last_index = old_content.rfind(old_string)
        if first_index != last_index:
            return _generate_multiple_matches_error(old_content, old_string, path, metadata)

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


def _replace_content(path: str, old_string: str, new_string: str, stats, metadata: bool = False) -> str:
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
            return _generate_not_found_error(old_content, old_string, path, metadata)

        # Check if old_string is unique
        first_index = old_content.find(old_string)
        last_index = old_content.rfind(old_string)
        if first_index != last_index:
            return _generate_multiple_matches_error(old_content, old_string, path, metadata)

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
        metadata = arguments.get("metadata", False)

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
            return _generate_not_found_error(old_content, old_string, path, metadata)

        # Check if old_string is unique (if it exists)
        if old_string != "":
            first_index = old_content.find(old_string)
            last_index = old_content.rfind(old_string)
            if first_index != last_index:
                return _generate_multiple_matches_error(old_content, old_string, path, metadata)

        # Check if content is actually changing (for replacement)
        if old_string != "" and new_string != "" and old_string == new_string:
            return "Error: new content is the same as old content. No changes made."

        return True

    except Exception as e:
        return f"Error during pre-validation: {e}"

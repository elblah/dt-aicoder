"""
File tracking utilities for monitoring file read operations.
"""

import time
import os
from typing import Dict, Tuple, Optional

# Track when files were last read
file_read_times: Dict[str, float] = {}

# Track read counts for efficiency optimization
file_read_counts: Dict[
    str, Tuple[float, int]
] = {}  # {file_path: (last_read_time, count)}

# Track edit counts for efficiency optimization
file_edit_counts: Dict[
    str, Tuple[float, int]
] = {}  # {file_path: (last_edit_time, count)}

# Configuration for efficiency detection
MICRO_EDIT_DETECTION = (
    os.environ.get("AICODER_MICRO_EDIT_DETECTION", "false").lower() == "true"
)
MICRO_EDIT_THRESHOLD = int(os.environ.get("AICODER_MICRO_EDIT_THRESHOLD", "3"))
MICRO_EDIT_WINDOW = int(os.environ.get("AICODER_MICRO_EDIT_WINDOW", "300"))  # 5 minutes

READ_DETECTION = os.environ.get("AICODER_READ_DETECTION", "false").lower() == "true"
READ_THRESHOLD = int(os.environ.get("AICODER_READ_THRESHOLD", "5"))
READ_WINDOW = int(os.environ.get("AICODER_READ_WINDOW", "300"))  # 5 minutes


def record_file_read(file_path: str):
    """Record when a file was last read.

    This should be called for any successful file read operation,
    whether it's reading the entire file or just a portion.
    """
    file_read_times[file_path] = time.time()


def get_last_read_time(file_path: str) -> float:
    """Get when a file was last read."""
    return file_read_times.get(file_path, 0)


def check_file_modification(file_path: str) -> str:
    """Check if file has been modified since last read.

    Returns:
        Empty string if no error, error message if file was modified.
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        # Get file modification time
        mod_time = os.path.getmtime(file_path)
        last_read_time = get_last_read_time(file_path)

        # If file was never read, that's a separate error condition
        if last_read_time == 0:
            return ""  # Not an error for write operations - file might not have been read before

        # Check if file was modified since last read
        if mod_time > last_read_time:
            # Format times for error message
            mod_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
            read_time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(last_read_time)
            )
            return f"Error: File {file_path} has been modified since it was last read (mod time: {mod_time_str}, last read: {read_time_str}). You must read the file again using the read_file tool before editing it."

        return ""  # No error
    except Exception as e:
        return f"Error checking file modification time: {e}"


def check_file_modification_strict(file_path: str) -> str:
    """Check if file has been modified since last read (strict version).

    Returns:
        Empty string if no error, error message if file was modified or never read.
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return f"Error: File not found: {file_path}"

        # Get file modification time
        mod_time = os.path.getmtime(file_path)
        last_read_time = get_last_read_time(file_path)

        # If file was never read, that's an error for strict checking
        if last_read_time == 0:
            return "Error: You must read the file using the read_file tool before editing it."

        # Check if file was modified since last read
        if mod_time > last_read_time:
            # Format times for error message
            mod_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
            read_time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(last_read_time)
            )
            return f"Error: File {file_path} has been modified since it was last read (mod time: {mod_time_str}, last read: {read_time_str}). You must read the file again using the read_file tool before editing it."

        return ""  # No error
    except Exception as e:
        return f"Error checking file modification time: {e}"


def track_file_read(file_path: str, message_history=None) -> Optional[str]:
    """Track file reads and suggest efficiency improvements.

    Returns an efficiency tip message if thresholds are exceeded.
    """
    if not READ_DETECTION:
        return None

    current_time = time.time()

    if file_path in file_read_counts:
        last_time, count = file_read_counts[file_path]
        time_diff = current_time - last_time

        if time_diff <= READ_WINDOW:
            # Within the time window, increment count
            count += 1
        else:
            # Too much time passed, reset count
            count = 1
    else:
        # First time reading this file
        count = 1

    # Update tracker
    file_read_counts[file_path] = (current_time, count)

    # Check if we should suggest efficiency improvement
    if count > READ_THRESHOLD and message_history:
        # Inform user we're helping the AI
        print(
            f"💡 Suggesting better reading strategy for {file_path} (read {count} times)"
        )

        efficiency_tip = (
            f"CONTEXT TIP: You've read {file_path} {count} times recently. "
            f"Consider keeping the file content in memory or reading larger sections at once to reduce API requests. "
            f"The file content stays in your context window for reference."
        )

        # Add as system message to guide the AI
        if hasattr(message_history, "messages"):
            message_history.messages.append(
                {"role": "user", "content": f"💡 EFFICIENCY TIP: {efficiency_tip}"}
            )
        return efficiency_tip

    return None


def track_file_edit(file_path: str, message_history=None) -> Optional[str]:
    """Track file edits and suggest write_file for multiple micro-edits.

    Returns an efficiency tip message if thresholds are exceeded.
    """
    if not MICRO_EDIT_DETECTION:
        return None

    current_time = time.time()

    if file_path in file_edit_counts:
        last_time, count = file_edit_counts[file_path]
        time_diff = current_time - last_time

        if time_diff <= MICRO_EDIT_WINDOW:
            # Within the time window, increment count
            count += 1
        else:
            # Too much time passed, reset count
            count = 1
    else:
        # First time editing this file
        count = 1

    # Update tracker
    file_edit_counts[file_path] = (current_time, count)

    # Check if we should suggest write_file
    if count > MICRO_EDIT_THRESHOLD and message_history:
        # Inform user we're helping the AI
        print(f"💡 Suggesting write_file for {file_path} (edited {count} times)")

        efficiency_tip = (
            f"EFFICIENCY TIP: You've made multiple edits to {file_path} recently. "
            f"For multiple changes to the same file, consider using write_file instead - "
            f"it's more efficient as it makes fewer API requests and handles all changes at once. "
            f"If this is your final edit or you only have one more small change, continue using edit_file. "
            f"If you anticipate many more changes to this file, write_file would be more efficient."
        )

        # Add as system message to guide the AI
        if hasattr(message_history, "messages"):
            message_history.messages.append(
                {"role": "user", "content": f"💡 EFFICIENCY TIP: {efficiency_tip}"}
            )
        return efficiency_tip

    return None

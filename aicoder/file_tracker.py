"""
File tracking utilities for monitoring file read operations.
"""

import time
import os
from typing import Dict

# Track when files were last read
file_read_times: Dict[str, float] = {}


def record_file_read(file_path: str):
    """Record when a file was last read."""
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
            return f"Error: File {file_path} has been modified since it was last read (mod time: {mod_time_str}, last read: {read_time_str}). You must read the ENTIRE file again using the read_file tool before editing it."

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
            return "Error: You must read the ENTIRE file using the read_file tool before editing it."

        # Check if file was modified since last read
        if mod_time > last_read_time:
            # Format times for error message
            mod_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mod_time))
            read_time_str = time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(last_read_time)
            )
            return f"Error: File {file_path} has been modified since it was last read (mod time: {mod_time_str}, last read: {read_time_str}). You must read the ENTIRE file again using the read_file tool before editing it."

        return ""  # No error
    except Exception as e:
        return f"Error checking file modification time: {e}"

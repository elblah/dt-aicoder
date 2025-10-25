#!/usr/bin/env python3
"""
Test that partial file reads integrate properly with file tracking for editing.
"""

import os
import tempfile
import sys

# Ensure YOLO_MODE is set to prevent hanging on approval prompts
if "YOLO_MODE" not in os.environ:
    os.environ["YOLO_MODE"] = "1"

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.internal_tools.read_file import execute_read_file
from aicoder.tool_manager.internal_tools.edit_file import execute_edit_file
from aicoder.tool_manager.file_tracker import (
    check_file_modification_strict,
    get_last_read_time,
)


class MockStats:
    def __init__(self):
        self.tool_errors = 0


def test_partial_read_enables_editing():
    """Test that reading only part of a file still allows editing."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write 100 lines
        for i in range(100):
            f.write(f"Line {i + 1}: This is the original content\n")
        temp_path = f.name

    try:
        # First, check that we can't edit without reading
        error = check_file_modification_strict(temp_path)
        assert error != ""  # Should get an error about needing to read first

        # Now read just a small portion (lines 10-12)
        result = execute_read_file(temp_path, stats, offset=10, limit=3)

        # Should have read lines 11-13
        assert "Line 11" in result
        assert "Line 12" in result
        assert "Line 13" in result

        # Now file should be trackable for editing
        last_read_time = get_last_read_time(temp_path)
        assert last_read_time > 0  # Should have been recorded

        # Should pass the modification check now
        error = check_file_modification_strict(temp_path)
        assert error == ""  # Should be no error

        # Test that we can edit the file
        edit_result = execute_edit_file(
            temp_path,
            "Line 50: This is the original content",
            "Line 50: This is the modified content",
            stats,
        )

        assert "Successfully updated" in edit_result

    finally:
        os.unlink(temp_path)


def test_modified_after_partial_read():
    """Test that modification is detected after partial read."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Original content line 1\nOriginal content line 2\n")
        temp_path = f.name

    try:
        # Read first line only
        result = execute_read_file(temp_path, stats, offset=0, limit=1)
        assert "Original content line 1" in result

        # Wait a bit to ensure different timestamp
        import time

        time.sleep(0.1)

        # Modify the file externally
        with open(temp_path, "w") as f:
            f.write("Modified content line 1\nModified content line 2\n")

        # Should detect modification
        error = check_file_modification_strict(temp_path)
        assert error != ""  # Should detect modification
        assert "has been modified since it was last read" in error

    finally:
        os.unlink(temp_path)


def test_multiple_partial_reads():
    """Test that multiple partial reads update the tracking time."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write 50 lines
        for i in range(50):
            f.write(f"Line {i + 1}\n")
        temp_path = f.name

    try:
        # First partial read
        result1 = execute_read_file(temp_path, stats, offset=0, limit=10)
        first_read_time = get_last_read_time(temp_path)

        # Wait a bit (file system time resolution)
        import time

        time.sleep(0.01)

        # Second partial read
        result2 = execute_read_file(temp_path, stats, offset=20, limit=10)
        second_read_time = get_last_read_time(temp_path)

        # Should have updated the read time
        assert second_read_time > first_read_time

        # Both reads should have worked
        assert "Line 1" in result1
        assert "Line 21" in result2

    finally:
        os.unlink(temp_path)

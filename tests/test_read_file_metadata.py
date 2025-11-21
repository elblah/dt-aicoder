#!/usr/bin/env python3
"""
Test the read_file metadata parameter functionality.
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


class MockStats:
    def __init__(self):
        self.tool_errors = 0


def test_metadata_false_by_default():
    """Test that metadata is False by default and pagination info is not shown."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write 10 lines
        for i in range(10):
            f.write(f"Line {i + 1}\n")
        temp_path = f.name

    try:
        # Test offset=2, limit=3 (should get lines 3,4,5)
        result = execute_read_file(temp_path, stats, offset=2, limit=3)
        lines = result.split("\n")

        # Should have 3 content lines
        assert "Line 3" in lines[0]
        assert "Line 4" in lines[1]
        assert "Line 5" in lines[2]

        # Should NOT indicate more lines available (metadata=False by default)
        assert "File has more lines" not in result
        assert "offset=5" not in result

    finally:
        os.unlink(temp_path)


def test_metadata_true_shows_pagination():
    """Test that metadata=True shows pagination info."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write 10 lines
        for i in range(10):
            f.write(f"Line {i + 1}\n")
        temp_path = f.name

    try:
        # Test offset=2, limit=3 with metadata=True
        result = execute_read_file(temp_path, stats, offset=2, limit=3, metadata=True)
        lines = result.split("\n")

        # Should have 3 content lines
        assert "Line 3" in lines[0]
        assert "Line 4" in lines[1]
        assert "Line 5" in lines[2]

        # Should indicate more lines available
        assert "File has more lines" in result
        assert "offset=5" in result

    finally:
        os.unlink(temp_path)


def test_mandatory_truncation_warnings():
    """Test that truncation warnings are always shown regardless of metadata setting."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write a very long line (longer than MAX_LINE_LENGTH)
        long_line = "A" * 2500
        f.write(f"{long_line}\n")
        f.write("Short line\n")
        temp_path = f.name

    try:
        # Test with metadata=False (default)
        result = execute_read_file(temp_path, stats, metadata=False)
        
        # Should show truncation warning even with metadata=False
        assert "Some lines were truncated to 2000 characters" in result
        assert "..." in result  # The truncated line should end with ...

        # Test with metadata=True
        result = execute_read_file(temp_path, stats, metadata=True)
        
        # Should still show truncation warning with metadata=True
        assert "Some lines were truncated to 2000 characters" in result
        assert "..." in result

    finally:
        os.unlink(temp_path)


def test_mandatory_file_truncation_warning():
    """Test that file truncation warning is shown when no pagination is specified and file is larger than default limit."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write 2100 lines (more than DEFAULT_READ_LIMIT of 2000)
        for i in range(2100):
            f.write(f"Line {i + 1}\n")
        temp_path = f.name

    try:
        # Test reading without offset/limit (should hit default limit and show warning)
        result = execute_read_file(temp_path, stats)
        
        # Should show mandatory file truncation warning
        assert "File has more lines than the default limit of 2000" in result
        assert "Use offset and limit to read specific ranges" in result

        # Test with metadata=False explicitly
        result = execute_read_file(temp_path, stats, metadata=False)
        
        # Should still show mandatory warning
        assert "File has more lines than the default limit of 2000" in result

        # Test with metadata=True
        result = execute_read_file(temp_path, stats, metadata=True)
        
        # Should show both mandatory warning and optional pagination info
        assert "File has more lines than the default limit of 2000" in result
        assert "offset=2000" in result  # Optional pagination info

    finally:
        os.unlink(temp_path)


def test_clean_small_file():
    """Test that small files return clean content with no warnings."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Line 1\n")
        f.write("Line 2\n")
        f.write("Line 3\n")
        temp_path = f.name

    try:
        # Test with metadata=False (default)
        result = execute_read_file(temp_path, stats)
        
        # Should be exactly the content with no warnings
        expected = "Line 1\nLine 2\nLine 3"
        assert result == expected

        # Test with metadata=True
        result = execute_read_file(temp_path, stats, metadata=True)
        
        # Should still be exactly the content with no warnings
        assert result == expected

    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    test_metadata_false_by_default()
    test_metadata_true_shows_pagination()
    test_mandatory_truncation_warnings()
    test_mandatory_file_truncation_warning()
    test_clean_small_file()
    print("All tests passed!")
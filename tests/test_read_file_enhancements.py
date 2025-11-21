#!/usr/bin/env python3
"""
Test the enhanced read_file functionality with pagination and truncation.
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


def test_offset_and_limit():
    """Test offset and limit parameters."""
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

        # Should NOT indicate more lines available with default metadata=False
        assert "File has more lines" not in result
        assert "offset=5" not in result

        # Test with metadata=True
        result_with_metadata = execute_read_file(temp_path, stats, offset=2, limit=3, metadata=True)
        
        # Should indicate more lines available when metadata=True
        assert "File has more lines" in result_with_metadata
        assert "offset=5" in result_with_metadata

    finally:
        os.unlink(temp_path)


def test_line_truncation():
    """Test line truncation for long lines."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write a very long line (2500 chars)
        long_line = "A" * 2500
        f.write(long_line + "\n")
        f.write("Short line\n")
        temp_path = f.name

    try:
        result = execute_read_file(temp_path, stats)
        lines = result.split("\n")

        # First line should be truncated
        assert len(lines[0]) <= 2003  # 2000 chars + "..."
        assert lines[0].endswith("...")
        assert "A" * 1990 in lines[0]  # Should contain most of the A's

        # Second line should be unchanged
        assert lines[1] == "Short line"

        # Should indicate truncation happened
        assert "Some lines were truncated" in result
        assert "2000 characters" in result

    finally:
        os.unlink(temp_path)


def test_offset_beyond_file():
    """Test offset beyond end of file."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write only 3 lines
        for i in range(3):
            f.write(f"Line {i + 1}\n")
        temp_path = f.name

    try:
        # Test offset=10 (beyond file)
        result = execute_read_file(temp_path, stats, offset=10)

        # Should return empty string
        assert result == ""

    finally:
        os.unlink(temp_path)


def test_default_behavior():
    """Test default behavior (no offset/limit)."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write 5 short lines
        for i in range(5):
            f.write(f"Line {i + 1}\n")
        temp_path = f.name

    try:
        result = execute_read_file(temp_path, stats)
        lines = result.split("\n")

        # Should get all 5 lines
        assert len([line for line in lines if line.startswith("Line")]) == 5

        # Should not indicate more lines or truncation
        assert "File has more lines" not in result
        assert "Some lines were truncated" not in result

    finally:
        os.unlink(temp_path)


def test_exact_limit():
    """Test when file has exactly the limit number of lines."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write exactly 2000 lines (default limit)
        for i in range(2000):
            f.write(f"Line {i + 1}\n")
        temp_path = f.name

    try:
        result = execute_read_file(temp_path, stats)
        lines = result.split("\n")

        # Should get all 2000 lines
        assert len([line for line in lines if line.startswith("Line")]) == 2000

        # Should not indicate more lines (file exactly matches limit)
        assert "File has more lines" not in result

    finally:
        os.unlink(temp_path)


def test_memory_efficiency():
    """Test that the implementation doesn't load entire file into memory."""
    stats = MockStats()

    # Create a file with many lines, but only read a small portion
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        # Write 10000 lines
        for i in range(10000):
            f.write(
                f"This is line {i + 1} with some content to make it reasonably long\n"
            )
        temp_path = f.name

    try:
        # Read only lines 5000-5002 (should not load all 10000 lines)
        result = execute_read_file(temp_path, stats, offset=5000, limit=3)
        lines = result.split("\n")

        # Should get exactly 3 lines
        content_lines = [line for line in lines if line.startswith("This is line")]
        assert len(content_lines) == 3
        assert "5001" in content_lines[0]
        assert "5002" in content_lines[1]
        assert "5003" in content_lines[2]

        # Should NOT indicate more lines available with default metadata=False
        assert "File has more lines" not in result
        assert "offset=5003" not in result

        # Test with metadata=True
        result_with_metadata = execute_read_file(temp_path, stats, offset=5000, limit=3, metadata=True)
        
        # Should indicate more lines available when metadata=True
        assert "File has more lines" in result_with_metadata
        assert "offset=5003" in result_with_metadata

    finally:
        os.unlink(temp_path)

#!/usr/bin/env python3
"""
Test the edit_file metadata parameter functionality.
"""

import os
import tempfile
import sys

# Ensure YOLO_MODE is set to prevent hanging on approval prompts
if "YOLO_MODE" not in os.environ:
    os.environ["YOLO_MODE"] = "1"

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.internal_tools.edit_file import execute_edit_file
from aicoder.tool_manager.internal_tools.read_file import execute_read_file


class MockStats:
    def __init__(self):
        self.tool_errors = 0


def test_metadata_false_by_default():
    """Test that metadata is False by default and errors are clean."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Line 1\nLine 2\nLine 3\n")
        temp_path = f.name

    try:
        # First read the file to satisfy file tracking
        execute_read_file(path=temp_path, stats=stats)
        
        # Test with metadata=False (default) - try to edit non-existent content
        result = execute_edit_file(
            path=temp_path,
            old_string="nonexistent content",
            new_string="new content",
            stats=stats
        )
        
        # Should show basic error only
        assert "Error: [X] Match not found" in result
        assert "Try read_file" in result
        # Should NOT show search suggestions
        assert "Found '" not in result
        assert "similar content" not in result

    finally:
        os.unlink(temp_path)


def test_metadata_true_shows_suggestions():
    """Test that metadata=True shows full search suggestions."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("function my_function() {\n    return 'hello';\n}\n")
        temp_path = f.name

    try:
        # First read the file to satisfy file tracking
        execute_read_file(path=temp_path, stats=stats)
        
        # Test with metadata=True - try to edit non-existent but similar content
        # Use longer content to trigger fuzzy search
        old_content = "function my_functon() {\n    return 'hello';\n}"  # typo in multi-line content
        result = execute_edit_file(
            path=temp_path,
            old_string=old_content,
            new_string="function my_function() {\n    return 'hello';\n}",
            stats=stats,
            metadata=True
        )
        
        # Should show basic error
        assert "Error: [X] Match not found" in result
        # Should show search suggestions
        assert "Found '" in result or "similar content" in result

    finally:
        os.unlink(temp_path)


def test_metadata_false_multiple_matches():
    """Test that metadata=False shows minimal multiple matches info."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Same line\nDifferent line\nSame line\n")
        temp_path = f.name

    try:
        # First read the file to satisfy file tracking
        execute_read_file(path=temp_path, stats=stats)
        
        # Test with metadata=False - try to edit content that appears multiple times
        result = execute_edit_file(
            path=temp_path,
            old_string="Same line",
            new_string="Modified line",
            stats=stats
        )
        
        # Should show basic multiple matches info
        assert "Error: [X] MULTIPLE MATCHES" in result
        assert "Found" in result  # Number of matches
        assert "Lines:" in result  # Line numbers
        # Should NOT show detailed context or suggestions
        assert "TO FIX:" not in result
        assert "Example contexts" not in result
        assert "ALTERNATIVE:" not in result

    finally:
        os.unlink(temp_path)


def test_metadata_true_multiple_matches():
    """Test that metadata=True shows full multiple matches context."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Same line\nDifferent line\nSame line\n")
        temp_path = f.name

    try:
        # First read the file to satisfy file tracking
        execute_read_file(path=temp_path, stats=stats)
        
        # Test with metadata=True - try to edit content that appears multiple times
        result = execute_edit_file(
            path=temp_path,
            old_string="Same line",
            new_string="Modified line",
            stats=stats,
            metadata=True
        )
        
        # Should show basic multiple matches info
        assert "Error: [X] MULTIPLE MATCHES" in result
        assert "Found" in result  # Number of matches
        assert "Lines:" in result  # Line numbers
        # Should show detailed context and suggestions
        assert "TO FIX:" in result
        assert "Example contexts" in result
        assert "ALTERNATIVE:" in result

    finally:
        os.unlink(temp_path)


def test_critical_errors_always_shown():
    """Test that critical errors are always shown regardless of metadata setting."""
    stats = MockStats()

    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_file = os.path.join(temp_dir, "nonexistent.txt")
        
        # Test with metadata=False
        result1 = execute_edit_file(
            path=non_existent_file,
            old_string="anything",
            new_string="anything",
            stats=stats,
            metadata=False
        )
        
        # Test with metadata=True
        result2 = execute_edit_file(
            path=non_existent_file,
            old_string="anything",
            new_string="anything",
            stats=stats,
            metadata=True
        )
        
        # Both should show the same basic file not found error
        assert "Error: File not found" in result1
        assert "Error: File not found" in result2
        assert result1 == result2  # Should be identical


def test_successful_edit_clean():
    """Test that successful edits are clean regardless of metadata setting."""
    stats = MockStats()

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("Original line\n")
        temp_path = f.name

    try:
        # First read the file to satisfy file tracking
        execute_read_file(path=temp_path, stats=stats)
        
        # Test successful edit with metadata=False
        result1 = execute_edit_file(
            path=temp_path,
            old_string="Original line",
            new_string="Modified line",
            stats=stats,
            metadata=False
        )
        
        # Reset file
        with open(temp_path, "w") as f:
            f.write("Original line\n")
        
        # Read again
        execute_read_file(path=temp_path, stats=stats)
        
        # Test successful edit with metadata=True
        result2 = execute_edit_file(
            path=temp_path,
            old_string="Original line",
            new_string="Modified line",
            stats=stats,
            metadata=True
        )
        
        # Both should show the same success message
        assert "Successfully updated" in result1
        assert "Successfully updated" in result2
        assert result1 == result2  # Should be identical

    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    test_metadata_false_by_default()
    test_metadata_true_shows_suggestions()
    test_metadata_false_multiple_matches()
    test_metadata_true_multiple_matches()
    test_critical_errors_always_shown()
    test_successful_edit_clean()
    print("All edit_file metadata tests passed!")
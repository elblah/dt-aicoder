"""
Comprehensive tests for internal tools that were missing tests.

[!] CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python tests/test_internal_tools_comprehensive.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import sys
import os
import tempfile

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.internal_tools import (
    execute_edit_file,
    execute_grep,
    execute_glob,
    execute_pwd,
    execute_read_file,
)


class MockStats:
    """Mock stats object for testing."""

    def __init__(self):
        self.tool_errors = 0


def test_pwd_tool():
    """Test the pwd tool."""
    mock_stats = MockStats()
    # Test getting current working directory
    result = execute_pwd(stats=mock_stats)

    # Verify the result is a valid path
    assert isinstance(result, str)
    assert os.path.exists(result)
    assert result == os.getcwd()


def test_glob_tool():
    """Test the glob tool."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save current directory and change to temp directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create some test files
            test_files = ["file1.txt", "file2.txt", "test.py", "script.sh"]
            for filename in test_files:
                with open(os.path.join(temp_dir, filename), "w") as f:
                    f.write("test content")

            # Test finding txt files
            result = execute_glob(pattern="*.txt", stats=mock_stats)

            # Verify txt files are found
            assert "file1.txt" in result
            assert "file2.txt" in result
            assert "test.py" not in result

            # Test finding py files
            result = execute_glob(pattern="*.py", stats=mock_stats)

            # Verify py files are found
            assert "test.py" in result
            assert "file1.txt" not in result

            # Test finding all files
            result = execute_glob(pattern="*", stats=mock_stats)

            # Verify all files are found
            for filename in test_files:
                assert filename in result

        finally:
            # Restore original directory
            os.chdir(original_dir)


def test_glob_tool_empty_pattern():
    """Test the glob tool with empty pattern."""
    mock_stats = MockStats()
    result = execute_glob(pattern="", stats=mock_stats)
    assert "Error" in result


def test_glob_tool_no_matches():
    """Test the glob tool with pattern that matches nothing."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save current directory and change to temp directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Test pattern that matches nothing
            result = execute_glob(pattern="nonexistent*.txt", stats=mock_stats)
            assert result == "No files found matching pattern"
        finally:
            # Restore original directory
            os.chdir(original_dir)


def test_grep_tool():
    """Test the grep tool."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save current directory and change to temp directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create test files with content
            with open(os.path.join(temp_dir, "file1.txt"), "w") as f:
                f.write(
                    "This is a test file\nWith multiple lines\nContaining the word test"
                )

            with open(os.path.join(temp_dir, "file2.py"), "w") as f:
                f.write("def test_function():\n    pass\n# This is a test comment")

            with open(os.path.join(temp_dir, "file3.txt"), "w") as f:
                f.write("Another file\nWithout the search term")

            # Test searching for "test"
            result = execute_grep(text="test", stats=mock_stats)

            # Verify matches are found
            assert "file1.txt" in result
            assert "file2.py" in result
            assert "test" in result.lower()

            # Test searching for something that doesn't exist
            result = execute_grep(text="nonexistent", stats=mock_stats)
            assert result == "No matches found"

        finally:
            # Restore original directory
            os.chdir(original_dir)


def test_grep_tool_empty_text():
    """Test the grep tool with empty search text."""
    mock_stats = MockStats()
    result = execute_grep(text="", stats=mock_stats)
    assert "Error" in result


def test_edit_file_create_new_file():
    """Test the edit_file tool for creating a new file."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "new_file.txt")
        content = "Hello, World!\nThis is a new file."

        # Test creating a new file
        result = execute_edit_file(
            path=test_file,
            old_string="",
            new_string=content,
            stats=mock_stats,
        )

        # Verify the file was created with correct content
        assert os.path.exists(test_file)
        with open(test_file, "r") as f:
            assert f.read() == content

        # Verify the tool returns a success message
        assert "Successfully created" in result
        assert "new_file.txt" in result


def test_edit_file_create_new_file_existing_file():
    """Test the edit_file tool when trying to create a file that already exists."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "existing_file.txt")

        # Create the file first
        with open(test_file, "w") as f:
            f.write("Existing content")

        # Try to create the same file again
        result = execute_edit_file(
            path=test_file,
            old_string="",
            new_string="New content",
            stats=mock_stats,
        )

        # Should return an error
        assert "Error" in result
        assert "already exists" in result


def test_edit_file_delete_content():
    """Test the edit_file tool for deleting content."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test_file.txt")
        original_content = "Line 1\nLine 2\nLine 3\nLine 4\n"

        # Create a test file
        with open(test_file, "w") as f:
            f.write(original_content)

        # Read the file first to satisfy the file tracking requirement
        execute_read_file(path=test_file, stats=mock_stats)

        # Delete "Line 2\n"
        result = execute_edit_file(
            path=test_file,
            old_string="Line 2\n",
            new_string="",
            stats=mock_stats,
        )

        # Verify content was deleted
        with open(test_file, "r") as f:
            new_content = f.read()

        expected_content = "Line 1\nLine 3\nLine 4\n"
        assert new_content == expected_content

        # Verify the tool returns a success message with diff
        assert "Successfully updated" in result


def test_edit_file_replace_content():
    """Test the edit_file tool for replacing content."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test_file.txt")
        original_content = "First line\nSecond line\nThird line\n"

        # Create a test file
        with open(test_file, "w") as f:
            f.write(original_content)

        # Read the file first to satisfy the file tracking requirement
        execute_read_file(path=test_file, stats=mock_stats)

        # Replace "Second line" with "New second line"
        result = execute_edit_file(
            path=test_file,
            old_string="Second line",
            new_string="New second line",
            stats=mock_stats,
        )

        # Verify content was replaced
        with open(test_file, "r") as f:
            new_content = f.read()

        expected_content = "First line\nNew second line\nThird line\n"
        assert new_content == expected_content

        # Verify the tool returns a success message with diff
        assert "Successfully updated" in result


def test_edit_file_nonexistent_file():
    """Test the edit_file tool with a nonexistent file for replacement."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "nonexistent.txt")

        # Try to replace content in a nonexistent file
        result = execute_edit_file(
            path=test_file,
            old_string="old content",
            new_string="new content",
            stats=mock_stats,
        )

        # Should return an error
        assert "Error" in result
        assert "not found" in result


def test_edit_file_old_string_not_found():
    """Test the edit_file tool when old_string is not found."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test_file.txt")
        content = "This is the file content\n"

        # Create a test file
        with open(test_file, "w") as f:
            f.write(content)

        # Read the file first to satisfy the file tracking requirement
        execute_read_file(path=test_file, stats=mock_stats)

        # Try to replace content that doesn't exist
        result = execute_edit_file(
            path=test_file,
            old_string="nonexistent content",
            new_string="new content",
            stats=mock_stats,
        )

        # Should return an error
        assert "Error:" in result
        assert "not found" in result
        # Should provide helpful guidance (either word match or suggestion)
        assert any(
            phrase in result
            for phrase in ["Found '", "Try read_file", "similar content"]
        )


def test_edit_file_multiple_instances():
    """Test the edit_file tool when old_string appears multiple times."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test_file.txt")
        content = "Same line\nDifferent line\nSame line\n"

        # Create a test file with duplicate content
        with open(test_file, "w") as f:
            f.write(content)

        # Read the file first to satisfy the file tracking requirement
        execute_read_file(path=test_file, stats=mock_stats)

        # Try to replace content that appears multiple times
        result = execute_edit_file(
            path=test_file,
            old_string="Same line",
            new_string="New line",
            stats=mock_stats,
        )

        # Should return an error about multiple instances
        assert "Error:" in result
        assert "MULTIPLE MATCHES" in result
        assert "Lines:" in result


def test_edit_file_same_content():
    """Test the edit_file tool when old_string and new_string are the same."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, "test_file.txt")
        content = "This is the file content\n"

        # Create a test file
        with open(test_file, "w") as f:
            f.write(content)

        # Read the file first to satisfy the file tracking requirement
        execute_read_file(path=test_file, stats=mock_stats)

        # Try to replace content with the same content
        result = execute_edit_file(
            path=test_file,
            old_string="This is the file content",
            new_string="This is the file content",
            stats=mock_stats,
        )

        # Should return an error about no changes
        assert "Error" in result
        assert "same" in result


def test_edit_file_directory_path():
    """Test the edit_file tool with a directory path."""
    mock_stats = MockStats()
    with tempfile.TemporaryDirectory() as temp_dir:
        # Try to edit a directory as if it were a file
        result = execute_edit_file(
            path=temp_dir,
            old_string="",
            new_string="content",
            stats=mock_stats,
        )

        # Should return an error
        assert "Error" in result
        assert "directory" in result

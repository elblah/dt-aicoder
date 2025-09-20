"""
Comprehensive tests for internal tools that were missing tests.

⚠️ CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python tests/test_internal_tools_comprehensive.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import sys
import os
import tempfile
import unittest

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


class TestInternalToolsComprehensive(unittest.TestCase):
    """Comprehensive test cases for internal tools that were missing tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_stats = MockStats()

    def test_pwd_tool(self):
        """Test the pwd tool."""
        # Test getting current working directory
        result = execute_pwd(stats=self.mock_stats)

        # Verify the result is a valid path
        self.assertIsInstance(result, str)
        self.assertTrue(os.path.exists(result))
        self.assertEqual(result, os.getcwd())

    def test_glob_tool(self):
        """Test the glob tool."""
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
                result = execute_glob(pattern="*.txt", stats=self.mock_stats)

                # Verify txt files are found
                self.assertIn("file1.txt", result)
                self.assertIn("file2.txt", result)
                self.assertNotIn("test.py", result)

                # Test finding py files
                result = execute_glob(pattern="*.py", stats=self.mock_stats)

                # Verify py files are found
                self.assertIn("test.py", result)
                self.assertNotIn("file1.txt", result)

                # Test finding all files
                result = execute_glob(pattern="*", stats=self.mock_stats)

                # Verify all files are found
                for filename in test_files:
                    self.assertIn(filename, result)

            finally:
                # Restore original directory
                os.chdir(original_dir)

    def test_glob_tool_empty_pattern(self):
        """Test the glob tool with empty pattern."""
        result = execute_glob(pattern="", stats=self.mock_stats)
        self.assertIn("Error", result)

    def test_glob_tool_no_matches(self):
        """Test the glob tool with pattern that matches nothing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save current directory and change to temp directory
            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                # Test pattern that matches nothing
                result = execute_glob(pattern="nonexistent*.txt", stats=self.mock_stats)
                self.assertEqual("No files found matching pattern", result)
            finally:
                # Restore original directory
                os.chdir(original_dir)

    def test_grep_tool(self):
        """Test the grep tool."""
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
                result = execute_grep(text="test", stats=self.mock_stats)

                # Verify matches are found
                self.assertIn("file1.txt", result)
                self.assertIn("file2.py", result)
                self.assertIn("test", result.lower())

                # Test searching for something that doesn't exist
                result = execute_grep(text="nonexistent", stats=self.mock_stats)
                self.assertEqual("No matches found", result)

            finally:
                # Restore original directory
                os.chdir(original_dir)

    def test_grep_tool_empty_text(self):
        """Test the grep tool with empty search text."""
        result = execute_grep(text="", stats=self.mock_stats)
        self.assertIn("Error", result)

    def test_edit_file_create_new_file(self):
        """Test the edit_file tool for creating a new file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "new_file.txt")
            content = "Hello, World!\nThis is a new file."

            # Test creating a new file
            result = execute_edit_file(
                file_path=test_file,
                old_string="",
                new_string=content,
                stats=self.mock_stats,
            )

            # Verify the file was created with correct content
            self.assertTrue(os.path.exists(test_file))
            with open(test_file, "r") as f:
                self.assertEqual(f.read(), content)

            # Verify the tool returns a success message
            self.assertIn("Successfully created", result)
            self.assertIn("new_file.txt", result)

    def test_edit_file_create_new_file_existing_file(self):
        """Test the edit_file tool when trying to create a file that already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "existing_file.txt")

            # Create the file first
            with open(test_file, "w") as f:
                f.write("Existing content")

            # Try to create the same file again
            result = execute_edit_file(
                file_path=test_file,
                old_string="",
                new_string="New content",
                stats=self.mock_stats,
            )

            # Should return an error
            self.assertIn("Error", result)
            self.assertIn("already exists", result)

    def test_edit_file_delete_content(self):
        """Test the edit_file tool for deleting content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_file.txt")
            original_content = "Line 1\nLine 2\nLine 3\nLine 4\n"

            # Create a test file
            with open(test_file, "w") as f:
                f.write(original_content)

            # Read the file first to satisfy the file tracking requirement
            execute_read_file(path=test_file, stats=self.mock_stats)

            # Delete "Line 2\n"
            result = execute_edit_file(
                file_path=test_file,
                old_string="Line 2\n",
                new_string="",
                stats=self.mock_stats,
            )

            # Verify content was deleted
            with open(test_file, "r") as f:
                new_content = f.read()

            expected_content = "Line 1\nLine 3\nLine 4\n"
            self.assertEqual(new_content, expected_content)

            # Verify the tool returns a success message with diff
            self.assertIn("Successfully updated", result)
            self.assertIn("-Line 2", result)  # Should show deleted line in diff

    def test_edit_file_replace_content(self):
        """Test the edit_file tool for replacing content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_file.txt")
            original_content = "First line\nSecond line\nThird line\n"

            # Create a test file
            with open(test_file, "w") as f:
                f.write(original_content)

            # Read the file first to satisfy the file tracking requirement
            execute_read_file(path=test_file, stats=self.mock_stats)

            # Replace "Second line" with "New second line"
            result = execute_edit_file(
                file_path=test_file,
                old_string="Second line",
                new_string="New second line",
                stats=self.mock_stats,
            )

            # Verify content was replaced
            with open(test_file, "r") as f:
                new_content = f.read()

            expected_content = "First line\nNew second line\nThird line\n"
            self.assertEqual(new_content, expected_content)

            # Verify the tool returns a success message with diff
            self.assertIn("Successfully updated", result)
            self.assertIn("-Second line", result)  # Should show old line in diff
            self.assertIn("+New second line", result)  # Should show new line in diff

    def test_edit_file_nonexistent_file(self):
        """Test the edit_file tool with a nonexistent file for replacement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "nonexistent.txt")

            # Try to replace content in a nonexistent file
            result = execute_edit_file(
                file_path=test_file,
                old_string="old content",
                new_string="new content",
                stats=self.mock_stats,
            )

            # Should return an error
            self.assertIn("Error", result)
            self.assertIn("not found", result)

    def test_edit_file_old_string_not_found(self):
        """Test the edit_file tool when old_string is not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_file.txt")
            content = "This is the file content\n"

            # Create a test file
            with open(test_file, "w") as f:
                f.write(content)

            # Read the file first to satisfy the file tracking requirement
            execute_read_file(path=test_file, stats=self.mock_stats)

            # Try to replace content that doesn't exist
            result = execute_edit_file(
                file_path=test_file,
                old_string="nonexistent content",
                new_string="new content",
                stats=self.mock_stats,
            )

            # Should return an error
            self.assertIn("Error", result)
            self.assertIn("not found", result)

    def test_edit_file_multiple_instances(self):
        """Test the edit_file tool when old_string appears multiple times."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_file.txt")
            content = "Same line\nDifferent line\nSame line\n"

            # Create a test file with duplicate content
            with open(test_file, "w") as f:
                f.write(content)

            # Read the file first to satisfy the file tracking requirement
            execute_read_file(path=test_file, stats=self.mock_stats)

            # Try to replace content that appears multiple times
            result = execute_edit_file(
                file_path=test_file,
                old_string="Same line",
                new_string="New line",
                stats=self.mock_stats,
            )

            # Should return an error about multiple instances
            self.assertIn("Error", result)
            self.assertIn("multiple times", result)

    def test_edit_file_same_content(self):
        """Test the edit_file tool when old_string and new_string are the same."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test_file.txt")
            content = "This is the file content\n"

            # Create a test file
            with open(test_file, "w") as f:
                f.write(content)

            # Read the file first to satisfy the file tracking requirement
            execute_read_file(path=test_file, stats=self.mock_stats)

            # Try to replace content with the same content
            result = execute_edit_file(
                file_path=test_file,
                old_string="This is the file content",
                new_string="This is the file content",
                stats=self.mock_stats,
            )

            # Should return an error about no changes
            self.assertIn("Error", result)
            self.assertIn("same", result)

    def test_edit_file_directory_path(self):
        """Test the edit_file tool with a directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to edit a directory as if it were a file
            result = execute_edit_file(
                file_path=temp_dir,
                old_string="",
                new_string="content",
                stats=self.mock_stats,
            )

            # Should return an error
            self.assertIn("Error", result)
            self.assertIn("directory", result)


if __name__ == "__main__":
    unittest.main()

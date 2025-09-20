"""
Tests for internal tools.
"""

import sys
import os
import tempfile
import unittest

# Ensure YOLO_MODE is set to prevent hanging on approval prompts
if "YOLO_MODE" not in os.environ:
    os.environ["YOLO_MODE"] = "1"

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.internal_tools import (
    execute_write_file,
    execute_read_file,
    execute_list_directory,
    execute_run_shell_command,
)


class MockStats:
    """Mock stats object for testing."""

    def __init__(self):
        self.tool_errors = 0


class TestInternalTools(unittest.TestCase):
    """Test cases for internal tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_stats = MockStats()

    def test_write_file_tool(self):
        """Test the write_file tool."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            content = "Hello, World!"

            # Test writing a file
            result = execute_write_file(
                path=test_file, content=content, stats=self.mock_stats
            )

            # Verify the file was created with correct content
            self.assertTrue(os.path.exists(test_file))
            with open(test_file, "r") as f:
                self.assertEqual(f.read(), content)

            # Verify the tool returns a success message
            self.assertIn("Successfully", result)

    def test_read_file_tool(self):
        """Test the read_file tool."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "test.txt")
            content = "Hello, World!"

            # Create a test file
            with open(test_file, "w") as f:
                f.write(content)

            # Test reading the file
            result = execute_read_file(path=test_file, stats=self.mock_stats)

            # Verify the content is correct
            self.assertEqual(result, content)

    def test_read_nonexistent_file(self):
        """Test reading a file that doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = os.path.join(temp_dir, "nonexistent.txt")

            # Test reading a nonexistent file
            result = execute_read_file(path=test_file, stats=self.mock_stats)

            # Should return an error message
            self.assertTrue("Error" in result or "not found" in result)

    def test_list_directory_tool(self):
        """Test the list_directory tool."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            test_files = ["file1.txt", "file2.txt", "file3.py"]
            for filename in test_files:
                with open(os.path.join(temp_dir, filename), "w") as f:
                    f.write("test content")

            # Test listing directory contents
            result = execute_list_directory(path=temp_dir, stats=self.mock_stats)

            # Verify all files are listed
            for filename in test_files:
                self.assertIn(filename, result)

    def test_run_shell_command_tool(self):
        """Test the run_shell_command tool."""
        # Test a simple command
        result = execute_run_shell_command(
            command="echo 'Hello World'", stats=self.mock_stats
        )

        # Verify the command output is in the result
        self.assertIn("Hello World", result)

    def test_run_shell_command_with_reason(self):
        """Test the run_shell_command tool with a reason."""
        result = execute_run_shell_command(
            command="echo 'Test'",
            reason="Testing shell command execution",
            stats=self.mock_stats,
        )

        # Verify the command executed successfully
        self.assertIn("Test", result)


if __name__ == "__main__":
    unittest.main()

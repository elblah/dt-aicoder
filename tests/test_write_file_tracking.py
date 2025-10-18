"""
Tests for write_file file tracking functionality.
"""

import unittest
import tempfile
import os
import sys

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aicoder.tool_manager.file_tracker import get_last_read_time, check_file_modification_strict
from aicoder.tool_manager.internal_tools.write_file import execute_write_file


class TestWriteFileTracking(unittest.TestCase):
    """Test cases for write_file file tracking."""

    def setUp(self):
        """Set up temporary directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test_file.py')

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_file_marks_file_as_read(self):
        """Test that write_file marks the file as read."""
        # Initially, file should not be marked as read
        self.assertEqual(get_last_read_time(self.test_file), 0)
        
        # Write file
        result = execute_write_file(self.test_file, "test content", None)
        self.assertIn("Successfully created", result)
        
        # File should now be marked as read
        self.assertGreater(get_last_read_time(self.test_file), 0)

    def test_write_file_allows_immediate_edit(self):
        """Test that edit_file works immediately after write_file without reading."""
        # Write file
        result = execute_write_file(self.test_file, "original content", None)
        self.assertIn("Successfully created", result)
        
        # Try to edit immediately (should work without reading first)
        error = check_file_modification_strict(self.test_file)
        self.assertEqual(error, "")  # No error means file is considered "read"

    def test_write_file_update_marks_as_read(self):
        """Test that updating existing file also marks it as read."""
        # Create file first
        execute_write_file(self.test_file, "original content", None)
        initial_read_time = get_last_read_time(self.test_file)
        
        # Wait a moment to ensure different timestamp
        import time
        time.sleep(0.1)
        
        # Update file
        result = execute_write_file(self.test_file, "updated content", None)
        self.assertIn("Successfully updated", result)
        
        # File should be marked as read again (timestamp should be newer)
        updated_read_time = get_last_read_time(self.test_file)
        self.assertGreater(updated_read_time, initial_read_time)

    def test_write_file_integration_with_edit(self):
        """Test complete workflow: write_file -> edit_file."""
        from aicoder.tool_manager.internal_tools.edit_file import execute_edit_file
        
        # Write file
        execute_write_file(self.test_file, "start content", None)
        
        # Edit immediately (should work)
        result = execute_edit_file(self.test_file, "start content", "modified content", None)
        self.assertIn("Successfully updated", result)
        
        # Verify content
        with open(self.test_file, 'r') as f:
            content = f.read()
        self.assertEqual(content, "modified content")

    def test_write_file_unchanged_marks_as_read(self):
        """Test that writing unchanged content still marks file as read."""
        # Create file
        execute_write_file(self.test_file, "same content", None)
        initial_read_time = get_last_read_time(self.test_file)
        
        # Wait a moment to ensure different timestamp
        import time
        time.sleep(0.1)
        
        # Write same content
        result = execute_write_file(self.test_file, "same content", None)
        self.assertIn("unchanged", result)
        
        # File should still be marked as read (timestamp should be newer)
        updated_read_time = get_last_read_time(self.test_file)
        self.assertGreater(updated_read_time, initial_read_time)


if __name__ == '__main__':
    unittest.main()
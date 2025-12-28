"""Test that edit_file validation errors are properly returned without approval prompts."""

import unittest
import tempfile
import os
from unittest.mock import patch, MagicMock
from aicoder.tool_manager.internal_tools import edit_file


class TestEditFileValidationErrors(unittest.TestCase):
    """Test edit_file validation error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_file.txt")
        
        # Create a test file with known content
        with open(self.test_file, 'w') as f:
            f.write("line 1\nline 2\nline 3\n")

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        os.rmdir(self.test_dir)

    def test_validation_error_starts_with_error(self):
        """Test that validation errors start with 'Error:' prefix."""
        # Test old_string not found
        args = {
            "path": self.test_file,
            "old_string": "not found text",
            "new_string": "replacement"
        }
        result = edit_file.validate_edit_file(args)
        self.assertTrue(result.startswith("Error:"), f"Validation error should start with 'Error:': {result}")
        
        # Test multiple occurrences
        with open(self.test_file, 'w') as f:
            f.write("duplicate\nduplicate\n")
        
        args = {
            "path": self.test_file,
            "old_string": "duplicate",
            "new_string": "replacement"
        }
        result = edit_file.validate_edit_file(args)
        self.assertTrue(result.startswith("Error:"), f"Validation error should start with 'Error:': {result}")
        
        # Test same old_string and new_string
        args = {
            "path": self.test_file,
            "old_string": "duplicate",
            "new_string": "duplicate"
        }
        result = edit_file.validate_edit_file(args)
        self.assertTrue(result.startswith("Error:"), f"Validation error should start with 'Error:': {result}")

    def test_approval_system_catches_validation_errors(self):
        """Test that approval system properly catches validation errors."""
        from aicoder.tool_manager.approval_system import ApprovalSystem
        
        # Create mock objects
        mock_tool_registry = MagicMock()
        mock_stats = MagicMock()
        mock_animator = MagicMock()
        
        approval_system = ApprovalSystem(mock_tool_registry, mock_stats, mock_animator)
        
        # Test with validation error (old_string not found)
        validation_error = "Error: old_string not found in file. Use read_file to see current content."
        
        # This should return (False, False) without prompting user
        approved, with_guidance = approval_system.request_user_approval(
            validation_error,
            "edit_file",
            {"path": self.test_file, "old_string": "not found", "new_string": "replacement"},
            {"auto_approved": False}
        )
        
        self.assertFalse(approved, "Validation error should not be approved")
        self.assertFalse(with_guidance, "Validation error should not have guidance")

    def test_successful_validation_passes_through(self):
        """Test that successful validation returns True."""
        args = {
            "path": self.test_file,
            "old_string": "line 2\n",
            "new_string": "modified line 2\n"
        }
        result = edit_file.validate_edit_file(args)
        self.assertTrue(result, "Valid edit should return True")

    def test_file_not_found_error(self):
        """Test that file not found errors start with 'Error:'."""
        args = {
            "path": "/nonexistent/file.txt",
            "old_string": "some text",
            "new_string": "replacement"
        }
        result = edit_file.validate_edit_file(args)
        self.assertTrue(result.startswith("Error:"), f"File not found error should start with 'Error:': {result}")


if __name__ == '__main__':
    unittest.main()
#!/usr/bin/env python3
"""
Test script for the glob plugin functionality.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

# Add the plugin directory to the path so we can import it
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import glob_tool as glob


class TestGlobPlugin(unittest.TestCase):
    """Test cases for the glob plugin."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create test files
        with open("test1.py", "w") as f:
            f.write("print('test1')")
        with open("test2.py", "w") as f:
            f.write("print('test2')")
        with open("main.js", "w") as f:
            f.write("console.log('main')")
        
        # Create subdirectory with files
        os.makedirs("subdir", exist_ok=True)
        with open("subdir/nested.py", "w") as f:
            f.write("print('nested')")
        with open("subdir/readme.md", "w") as f:
            f.write("# README")

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_glob_basic(self):
        """Test basic glob functionality."""
        result = glob.execute_glob("*.py")
        self.assertIn("test1.py", result)
        self.assertIn("test2.py", result)
        self.assertNotIn("main.js", result)

    def test_execute_glob_recursive(self):
        """Test recursive glob functionality."""
        result = glob.execute_glob("**/*.py")
        self.assertIn("test1.py", result)
        self.assertIn("test2.py", result)
        self.assertIn("subdir/nested.py", result)

    def test_execute_glob_no_matches(self):
        """Test glob with no matching files."""
        result = glob.execute_glob("nonexistent*.xyz")
        self.assertEqual(result, "No files found matching pattern")

    def test_execute_glob_empty_pattern(self):
        """Test glob with empty pattern."""
        result = glob.execute_glob("")
        self.assertEqual(result, "Error: Pattern cannot be empty.")

    def test_search_with_python_glob(self):
        """Test Python glob fallback functionality."""
        result = glob._search_with_python_glob("*.py")
        self.assertIn("test1.py", result)
        self.assertIn("test2.py", result)
        self.assertNotIn("main.js", result)

    def test_search_with_python_glob_recursive(self):
        """Test Python glob recursive functionality."""
        result = glob._search_with_python_glob("**/*.py")
        self.assertIn("test1.py", result)
        self.assertIn("test2.py", result)
        self.assertIn("subdir/nested.py", result)

    def test_glob_tool_definition(self):
        """Test that the tool definition is properly structured."""
        tool_def = glob.GLOB_TOOL_DEFINITION
        self.assertEqual(tool_def["type"], "internal")
        self.assertEqual(tool_def["auto_approved"], True)
        self.assertEqual(tool_def["name"], "glob")
        self.assertIn("pattern", tool_def["parameters"]["properties"])
        self.assertEqual(tool_def["parameters"]["required"], ["pattern"])

    def test_handle_glob_command_no_args(self):
        """Test handling /glob command with no arguments."""
        # Mock the tool availability check
        with patch('glob_tool.check_tool_availability', return_value=False):
            # This should not raise an exception
            try:
                glob._handle_glob_command([])
            except Exception as e:
                self.fail(f"_handle_glob_command raised an exception: {e}")

    def test_handle_glob_command_help(self):
        """Test handling /glob help command."""
        # This should not raise an exception
        try:
            glob._handle_glob_command(["help"])
        except Exception as e:
            self.fail(f"_handle_glob_command help raised an exception: {e}")

    def test_handle_glob_command_with_pattern(self):
        """Test handling /glob command with pattern."""
        # This should not raise an exception
        try:
            glob._handle_glob_command(["*.py"])
        except Exception as e:
            self.fail(f"_handle_glob_command with pattern raised an exception: {e}")

    @patch('glob_tool.check_tool_availability')
    def test_execute_glob_tool_preference(self, mock_check_tool):
        """Test that ripgrep is preferred over Python glob."""
        # Mock ripgrep as available
        mock_check_tool.return_value = True
        
        # Mock the _search_with_rg function to avoid actual subprocess calls
        with patch('glob_tool._search_with_rg', return_value="ripgrep result"):
            result = glob.execute_glob("*.py")
            self.assertEqual(result, "ripgrep result")
            mock_check_tool.assert_called_with("rg")

    @patch('glob_tool.check_tool_availability')
    def test_execute_glob_fallback_order(self, mock_check_tool):
        """Test fallback order when tools are not available."""
        # Mock all external tools as unavailable
        mock_check_tool.side_effect = lambda tool: False
        
        result = glob.execute_glob("*.py")
        # Should use Python glob as fallback
        self.assertIn("test1.py", result)
        self.assertIn("test2.py", result)

    def test_file_limit_enforcement(self):
        """Test that file limit is enforced."""
        # Create many files to test the limit
        for i in range(10):
            with open(f"file_{i}.py", "w") as f:
                f.write(f"print('file {i}')")
        
        result = glob.execute_glob("*.py")
        # Should include some files and not exceed limit
        self.assertTrue(len(result.split('\n')) <= glob.DEFAULT_FILE_LIMIT + 2)  # +2 for header/footer


class TestGlobPluginIntegration(unittest.TestCase):
    """Integration tests for the glob plugin."""

    def test_plugin_metadata(self):
        """Test that plugin metadata is properly defined."""
        self.assertEqual(glob.PLUGIN_NAME, "glob")
        self.assertEqual(glob.PLUGIN_VERSION, "1.0.0")
        self.assertIn("File pattern matching", glob.PLUGIN_DESCRIPTION)

    def test_on_aicoder_init_structure(self):
        """Test that the on_aicoder_init function exists and is callable."""
        self.assertTrue(callable(getattr(glob, 'on_aicoder_init', None)))

    def test_execute_glob_function_structure(self):
        """Test that execute_glob function has the right signature."""
        import inspect
        sig = inspect.signature(glob.execute_glob)
        # Should accept pattern parameter
        self.assertIn('pattern', sig.parameters)


if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestGlobPlugin))
    suite.addTests(loader.loadTestsFromTestCase(TestGlobPluginIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
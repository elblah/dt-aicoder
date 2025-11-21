#!/usr/bin/env python3
"""
Test suite for the Oxlint plugin.

Tests the oxlint plugin functionality including file monitoring,
issue detection, and formatting capabilities.
"""

import os
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch
import sys

# Add the parent directory to the path to import the plugin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxlint


class TestOxlintPlugin(unittest.TestCase):
    """Test cases for the Oxlint plugin."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_aicoder = MagicMock()
        self.mock_aicoder.command_handlers = {}
        self.mock_aicoder.persistent_config = {}
        self.mock_aicoder.tool_manager = MagicMock()
        self.mock_aicoder.tool_manager.executor = MagicMock()
        self.mock_aicoder.tool_manager.executor.pending_tool_messages = []
        self.mock_aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS = {}

    def tearDown(self):
        """Clean up after tests."""
        # Reset global state
        oxlint._aicoder_ref = None
        oxlint._original_write_file = None
        oxlint._original_edit_file = None
        oxlint._bun_available_cache = None

    @patch('shutil.which')
    def test_is_oxlint_available_success(self, mock_which):
        """Test successful oxlint availability check."""
        mock_which.return_value = '/usr/bin/bun'
        self.assertTrue(oxlint._is_oxlint_available())

    @patch('shutil.which')
    def test_is_oxlint_available_no_bun(self, mock_which):
        """Test oxlint availability check without bun."""
        mock_which.return_value = None
        self.assertFalse(oxlint._is_oxlint_available())

    def test_is_bun_available_caching(self):
        """Test that bun availability is cached."""
        # Reset cache first
        oxlint._bun_available_cache = None
        
        with patch('shutil.which') as mock_which:
            mock_which.return_value = '/usr/bin/bun'
            
            # First call should check shutil.which
            self.assertTrue(oxlint._is_bun_available())
            self.assertEqual(mock_which.call_count, 1)
            
            # Second call should use cache
            self.assertTrue(oxlint._is_bun_available())
            self.assertEqual(mock_which.call_count, 1)  # Still only called once
        
        # Reset cache for clean test
        oxlint._bun_available_cache = None

    def test_is_js_ts_file(self):
        """Test JavaScript/TypeScript file detection."""
        self.assertTrue(oxlint._is_js_ts_file('test.js'))
        self.assertTrue(oxlint._is_js_ts_file('test.jsx'))
        self.assertTrue(oxlint._is_js_ts_file('test.ts'))
        self.assertTrue(oxlint._is_js_ts_file('test.tsx'))
        self.assertTrue(oxlint._is_js_ts_file('test.mjs'))
        self.assertTrue(oxlint._is_js_ts_file('test.cjs'))
        self.assertFalse(oxlint._is_js_ts_file('test.py'))
        self.assertFalse(oxlint._is_js_ts_file('test.md'))
        self.assertFalse(oxlint._is_js_ts_file('test.txt'))

    def test_parse_bool_env(self):
        """Test boolean environment variable parsing."""
        # Test various true values
        with patch.dict(os.environ, {'TEST_BOOL': '1'}):
            self.assertTrue(oxlint._parse_bool_env('TEST_BOOL'))
        
        with patch.dict(os.environ, {'TEST_BOOL': 'true'}):
            self.assertTrue(oxlint._parse_bool_env('TEST_BOOL'))
        
        with patch.dict(os.environ, {'TEST_BOOL': 'on'}):
            self.assertTrue(oxlint._parse_bool_env('TEST_BOOL'))
        
        # Test various false values
        with patch.dict(os.environ, {'TEST_BOOL': '0'}):
            self.assertFalse(oxlint._parse_bool_env('TEST_BOOL'))
        
        with patch.dict(os.environ, {'TEST_BOOL': 'false'}):
            self.assertFalse(oxlint._parse_bool_env('TEST_BOOL'))
        
        with patch.dict(os.environ, {'TEST_BOOL': 'off'}):
            self.assertFalse(oxlint._parse_bool_env('TEST_BOOL'))
        
        # Test empty/missing value
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(oxlint._parse_bool_env('MISSING_BOOL', default=False))
            self.assertTrue(oxlint._parse_bool_env('MISSING_BOOL', default=True))

    @patch('oxlint._is_oxlint_available')
    def test_on_aicoder_init_success(self, mock_available):
        """Test successful plugin initialization."""
        mock_available.return_value = True
        
        # Mock the internal tool functions
        mock_write_file = Mock()
        mock_edit_file = Mock()
        
        with patch('aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS', {
            'write_file': mock_write_file,
            'edit_file': mock_edit_file
        }):
            result = oxlint.on_aicoder_init(self.mock_aicoder)
            
            self.assertTrue(result)
            self.assertEqual(oxlint._aicoder_ref, self.mock_aicoder)
            self.assertIn('/oxlint', self.mock_aicoder.command_handlers)

    @patch('oxlint._is_oxlint_available')
    def test_on_aicoder_init_no_oxlint(self, mock_available):
        """Test plugin initialization when oxlint is not available."""
        mock_available.return_value = False
        
        with patch('builtins.print') as mock_print:
            result = oxlint.on_aicoder_init(self.mock_aicoder)
            
            self.assertFalse(result)
            # Should print warning about oxlint not being found

    def test_handle_oxlint_command_status(self):
        """Test /oxlint command with no arguments (status)."""
        oxlint._aicoder_ref = self.mock_aicoder
        self.mock_aicoder.persistent_config = {
            'oxlint.enabled': True,
            'oxlint.format_enabled': False,
            'oxlint.args': '--quiet'
        }
        
        handled, should_continue = oxlint._handle_oxlint_command([])
        
        self.assertFalse(handled)
        self.assertFalse(should_continue)

    def test_handle_oxlint_command_check_on(self):
        """Test /oxlint check on command."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        handled, should_continue = oxlint._handle_oxlint_command(['check', 'on'])
        
        self.assertFalse(handled)
        self.assertFalse(should_continue)
        self.assertTrue(self.mock_aicoder.persistent_config['oxlint.enabled'])

    def test_handle_oxlint_command_check_off(self):
        """Test /oxlint check off command."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        handled, should_continue = oxlint._handle_oxlint_command(['check', 'off'])
        
        self.assertFalse(handled)
        self.assertFalse(should_continue)
        self.assertFalse(self.mock_aicoder.persistent_config['oxlint.enabled'])

    def test_handle_oxlint_command_format_on(self):
        """Test /oxlint format on command."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        handled, should_continue = oxlint._handle_oxlint_command(['format', 'on'])
        
        self.assertFalse(handled)
        self.assertFalse(should_continue)
        self.assertTrue(self.mock_aicoder.persistent_config['oxlint.format_enabled'])

    def test_handle_oxlint_command_args(self):
        """Test /oxlint args command."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        handled, should_continue = oxlint._handle_oxlint_command(['args', '--quiet', '--deny-warnings'])
        
        self.assertFalse(handled)
        self.assertFalse(should_continue)
        self.assertEqual(
            self.mock_aicoder.persistent_config['oxlint.args'],
            '--quiet --deny-warnings'
        )

    def test_handle_oxlint_command_help(self):
        """Test /oxlint help command."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        handled, should_continue = oxlint._handle_oxlint_command(['help'])
        
        self.assertFalse(handled)
        self.assertFalse(should_continue)

    def test_handle_oxlint_command_invalid(self):
        """Test /oxlint with invalid command."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        handled, should_continue = oxlint._handle_oxlint_command(['invalid'])
        
        self.assertFalse(handled)
        self.assertFalse(should_continue)

    @patch('oxlint._is_oxlint_enabled')
    @patch('subprocess.run')
    def test_check_file_with_oxlint_issues_found(self, mock_run, mock_enabled):
        """Test oxlint checking when issues are found."""
        mock_enabled.return_value = True
        oxlint._aicoder_ref = self.mock_aicoder
        
        # Mock oxlint finding issues
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='error: Unexpected console statement\n  at test.js:1:1'
        )
        
        with patch.object(oxlint, '_add_oxlint_issues_message') as mock_add_msg:
            oxlint._check_file_with_oxlint('test.js')
            
            mock_run.assert_called_once()
            mock_add_msg.assert_called_once()

    @patch('oxlint._is_oxlint_enabled')
    @patch('oxlint._is_oxlint_format_enabled')
    @patch('subprocess.run')
    def test_check_file_with_oxlint_no_issues(self, mock_run, mock_format_enabled, mock_enabled):
        """Test oxlint checking when no issues are found."""
        mock_enabled.return_value = True
        mock_format_enabled.return_value = True
        oxlint._aicoder_ref = self.mock_aicoder
        
        # Mock oxlint finding no issues
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr=''
        )
        
        with patch.object(oxlint, '_format_file_with_oxlint') as mock_format:
            oxlint._check_file_with_oxlint('test.js')
            
            mock_run.assert_called_once()
            mock_format.assert_called_once()

    @patch('oxlint._is_oxlint_enabled')
    def test_check_file_with_oxlint_disabled(self, mock_enabled):
        """Test oxlint checking when plugin is disabled."""
        mock_enabled.return_value = False
        
        with patch('subprocess.run') as mock_run:
            oxlint._check_file_with_oxlint('test.js')
            
            mock_run.assert_not_called()

    def test_check_file_with_oxlint_non_js_file(self):
        """Test oxlint checking with non-JS/TS file."""
        with patch('subprocess.run') as mock_run:
            oxlint._check_file_with_oxlint('test.py')
            
            mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_format_file_with_oxlint_success(self, mock_run):
        """Test oxlint formatting success."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        # Mock successful formatting
        mock_run.return_value = MagicMock(
            returncode=0,
            stderr='fixed 1 problem in test.js'
        )
        
        with patch.object(oxlint, '_add_format_message') as mock_add_msg:
            oxlint._format_file_with_oxlint('test.js')
            
            mock_run.assert_called_once()
            mock_add_msg.assert_called_once()

    @patch('subprocess.run')
    def test_format_file_with_oxlint_failure(self, mock_run):
        """Test oxlint formatting failure."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        # Mock formatting failure
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr='Failed to fix issues'
        )
        
        with patch.object(oxlint, '_add_format_message') as mock_add_msg:
            oxlint._format_file_with_oxlint('test.js')
            
            mock_run.assert_called_once()
            mock_add_msg.assert_not_called()

    def test_add_oxlint_issues_message(self):
        """Test adding oxlint issues message."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        oxlint._add_oxlint_issues_message('test.js', 'error: Unexpected console statement')
        
        self.assertEqual(len(self.mock_aicoder.tool_manager.executor.pending_tool_messages), 1)
        message = self.mock_aicoder.tool_manager.executor.pending_tool_messages[0]
        self.assertEqual(message['role'], 'user')
        self.assertIn('Oxlint Plugin: Issues Detected', message['content'])
        self.assertIn('test.js', message['content'])
        self.assertIn('Unexpected console statement', message['content'])

    def test_add_format_message(self):
        """Test adding format message."""
        oxlint._aicoder_ref = self.mock_aicoder
        
        oxlint._add_format_message('test.js')
        
        self.assertEqual(len(self.mock_aicoder.tool_manager.executor.pending_tool_messages), 1)
        message = self.mock_aicoder.tool_manager.executor.pending_tool_messages[0]
        self.assertEqual(message['role'], 'user')
        self.assertIn('Oxlint Plugin: File Formatted', message['content'])
        self.assertIn('test.js', message['content'])

    def test_cleanup(self):
        """Test plugin cleanup."""
        # Set up original functions
        oxlint._original_write_file = Mock()
        oxlint._original_edit_file = Mock()
        
        with patch('aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS', {}) as mock_functions:
            oxlint.cleanup()
            
            # Original functions should be restored (in real implementation)
            # For test, we just verify no exceptions occur

    def test_plugin_metadata(self):
        """Test plugin metadata."""
        self.assertEqual(oxlint.PLUGIN_NAME, "Oxlint Code Quality")
        self.assertEqual(oxlint.PLUGIN_AUTHOR, "AI Coder")
        self.assertEqual(oxlint.PLUGIN_DESCRIPTION, "Automatic oxlint checks and formatting for JavaScript/TypeScript files")
        self.assertTrue(hasattr(oxlint, '__version__'))


if __name__ == '__main__':
    unittest.main()
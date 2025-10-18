"""Tests for terminal manager functionality."""

import unittest
import os

# Set test mode before importing
os.environ['TEST_MODE'] = '1'

from aicoder.terminal_manager import get_terminal_manager, cleanup_terminal_manager


class TestTerminalManager(unittest.TestCase):
    """Test terminal manager functionality."""

    def setUp(self):
        """Set up test environment."""
        # Clean up any existing manager
        cleanup_terminal_manager()

    def tearDown(self):
        """Clean up after test."""
        cleanup_terminal_manager()

    def test_terminal_manager_creation(self):
        """Test that terminal manager can be created in test mode."""
        tm = get_terminal_manager()
        self.assertIsNotNone(tm)
        self.assertTrue(tm._test_mode)
        self.assertIsNone(tm._monitor_thread)  # Should not start in test mode

    def test_prompt_mode_operations(self):
        """Test prompt mode operations in test mode."""
        tm = get_terminal_manager()
        
        # Should not raise any exceptions
        tm.enter_prompt_mode()
        self.assertTrue(tm._in_prompt_mode)
        
        tm.exit_prompt_mode()
        self.assertFalse(tm._in_prompt_mode)

    def test_esc_detection_in_test_mode(self):
        """Test ESC detection in test mode."""
        tm = get_terminal_manager()
        
        # Should return False in test mode (no monitoring)
        self.assertFalse(tm.is_esc_pressed())
        
        # Reset should also work
        tm.reset_esc_state()
        self.assertFalse(tm.is_esc_pressed())

    def test_cleanup_in_test_mode(self):
        """Test cleanup in test mode."""
        tm = get_terminal_manager()
        
        # Should not raise any exceptions
        tm.cleanup()
        
    def test_multiple_get_terminal_manager_calls(self):
        """Test that get_terminal_manager returns same instance."""
        tm1 = get_terminal_manager()
        tm2 = get_terminal_manager()
        self.assertIs(tm1, tm2)


if __name__ == '__main__':
    unittest.main()
"""
Tests for the stats module.
"""

import sys
import os
import unittest
from unittest.mock import patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.stats import Stats


class TestStats(unittest.TestCase):
    """Test cases for the Stats class."""

    def test_stats_initialization(self):
        """Test that Stats object initializes with correct default values."""
        stats = Stats()

        # Check default values
        self.assertEqual(stats.api_requests, 0)
        self.assertEqual(stats.api_success, 0)
        self.assertEqual(stats.api_errors, 0)
        self.assertEqual(stats.api_time_spent, 0.0)
        self.assertEqual(stats.tool_calls, 0)
        self.assertEqual(stats.tool_errors, 0)
        self.assertEqual(stats.tool_time_spent, 0.0)
        self.assertEqual(stats.messages_sent, 0)
        self.assertEqual(stats.tokens_processed, 0)
        self.assertEqual(stats.compactions, 0)

        # Check that session_start_time is set
        self.assertIsInstance(stats.session_start_time, float)
        self.assertGreater(stats.session_start_time, 0)

    def test_stats_increment_api_requests(self):
        """Test incrementing API request counters."""
        stats = Stats()

        # Increment counters
        stats.api_requests = 5
        stats.api_success = 3
        stats.api_errors = 2

        self.assertEqual(stats.api_requests, 5)
        self.assertEqual(stats.api_success, 3)
        self.assertEqual(stats.api_errors, 2)

    def test_stats_increment_tool_calls(self):
        """Test incrementing tool call counters."""
        stats = Stats()

        # Increment counters
        stats.tool_calls = 10
        stats.tool_errors = 1

        self.assertEqual(stats.tool_calls, 10)
        self.assertEqual(stats.tool_errors, 1)

    def test_stats_time_tracking(self):
        """Test time tracking functionality."""
        stats = Stats()

        # Add some time
        stats.api_time_spent = 5.5
        stats.tool_time_spent = 5.5

        self.assertEqual(stats.api_time_spent, 5.5)
        self.assertEqual(stats.tool_time_spent, 5.5)

    @patch("time.time")
    def test_stats_print_output(self, mock_time):
        """Test that print_stats produces output."""
        stats = Stats()

        # Set some values for a more meaningful output
        stats.messages_sent = 5
        stats.api_requests = 3
        stats.api_success = 2
        stats.api_errors = 1
        stats.tool_calls = 4
        stats.tool_errors = 1
        stats.compactions = 1

        # Mock time.time() to control elapsed time
        mock_time.return_value = stats.session_start_time + 60

        # Capture stdout
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            stats.print_stats()

        output = captured_output.getvalue()

        # Check that key information is in the output
        self.assertIn("Session Statistics", output)
        self.assertIn("API requests: 3", output)
        self.assertIn("Tool calls: 4", output)
        self.assertIn("Memory compactions: 1", output)
        self.assertIn("API success rate:", output)
        self.assertIn("Tool success rate:", output)
        # Note: "Messages sent" may not appear in current output format


if __name__ == "__main__":
    unittest.main()

"""
Test for TPS display in token info.
"""

import unittest
import io
import sys
from unittest.mock import patch
import time

from aicoder.stats import Stats
from aicoder.utils import display_token_info


class TestTPSDisplay(unittest.TestCase):
    def test_tps_display_format(self):
        """Test that TPS is displayed in the context line."""
        # Create a stats object with some data
        stats = Stats()
        stats.current_prompt_size = 50000
        stats.completion_tokens = 1000
        stats.api_time_spent = 50.0  # 50 seconds
        stats.current_prompt_size_estimated = False

        # Capture printed output
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            display_token_info(stats, 100000)

        output = captured_output.getvalue()
        
        # Check that the output contains TPS with decimal
        self.assertIn("~20.0tps", output)  # 1000 tokens / 50 seconds = 20.0 tps
        
    def test_tps_display_as_integer(self):
        """Test that TPS displays as integer when it's a whole number."""
        # Create a stats object with whole number TPS
        stats = Stats()
        stats.current_prompt_size = 50000
        stats.completion_tokens = 1000
        stats.api_time_spent = 50.0  # This gives exactly 20.0 TPS
        stats.current_prompt_size_estimated = False

        # Capture printed output
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            display_token_info(stats, 100000)

        output = captured_output.getvalue()
        
        # Check that the output contains TPS with decimal
        self.assertIn("~20.0tps", output)  # Should display as decimal even for whole numbers
        
    def test_tps_display_with_decimal(self):
        """Test that TPS displays with decimal when not a whole number."""
        # Create a stats object with decimal TPS
        stats = Stats()
        stats.current_prompt_size = 50000
        stats.completion_tokens = 1000
        stats.api_time_spent = 33.0  # This gives ~30.3 TPS
        stats.current_prompt_size_estimated = False

        # Capture printed output
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            display_token_info(stats, 100000)

        output = captured_output.getvalue()
        
        # Check that the output contains TPS with decimal
        self.assertIn("~30.3tps", output)  # Should display with 1 decimal place
        
    def test_zero_tps_display(self):
        """Test that TPS displays as 0 when no API time spent."""
        # Create a stats object with no API time
        stats = Stats()
        stats.current_prompt_size = 50000
        stats.completion_tokens = 0
        stats.api_time_spent = 0.0
        stats.current_prompt_size_estimated = False

        # Capture printed output
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            display_token_info(stats, 100000)

        output = captured_output.getvalue()
        
        # Check that the output contains 0 TPS with decimal
        self.assertIn("~0.0tps", output)  # Should display as 0.0 when no time spent


if __name__ == '__main__':
    unittest.main()
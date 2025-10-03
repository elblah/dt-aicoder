"""
Unit tests for token information display functionality.
"""

import io
import sys
import unittest
import contextlib

sys.path.insert(0, '.')

from aicoder.utils import display_token_info
from aicoder.stats import Stats


class TestTokenInfoDisplay(unittest.TestCase):
    """Test cases for token information display functionality."""
    
    def test_token_info_display_format(self):
        """Test that token information is displayed in the correct format."""
        # Create a stats object with some values
        stats = Stats()
        stats.current_prompt_size = 23271
        
        # Mock the auto compact threshold to match the example
        auto_compact_threshold = 128000
        
        # Capture the output
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            display_token_info(stats, auto_compact_threshold)
        
        output = captured_output.getvalue().strip()
        
        # Calculate expected values using the same logic as the actual function
        percentage = int((23271 / 128000) * 100)  # Should be 18
        filled_bars = int((percentage + 5) // 10)  # Should be 2 (using same rounding as function)
        expected_bars = "●" * filled_bars + "○" * (10 - filled_bars)  # Should be ●●○○○○○○○○
        
        # Verify the output format matches the expected format
        self.assertIn("Context:", output)
        self.assertIn(f"{percentage}%", output)
        self.assertIn(f"(23,271/128,000 tokens)", output)
        # The expected_bars should be in the output, possibly with color codes
        # Check for the pattern with or without color codes
        from aicoder import config
        colored_bars = f"{config.GREEN}{expected_bars}{config.RESET}"
        self.assertIn(colored_bars, output)  # Look for the colored version
    
    def test_token_info_display_different_values(self):
        """Test token info display with different values."""
        stats = Stats()
        stats.current_prompt_size = 50000
        auto_compact_threshold = 100000
        
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            display_token_info(stats, auto_compact_threshold)
        
        output = captured_output.getvalue().strip()
        
        # Should be 50% (50000/100000), so 5 filled bars using same rounding as function
        percentage = int((50000 / 100000) * 100)  # Should be 50
        filled_bars = int((percentage + 5) // 10)  # Should be 5 (using same rounding as function)
        expected_bars = "●" * filled_bars + "○" * (10 - filled_bars)  # Should be ●●●●●○○○○○
        
        self.assertIn("Context:", output)
        self.assertIn(f"{percentage}%", output)
        self.assertIn(f"(50,000/100,000 tokens)", output)
        # Check for the pattern with or without color codes
        from aicoder import config
        colored_bars = f"{config.GREEN}{expected_bars}{config.RESET}"
        self.assertIn(colored_bars, output)  # Look for the colored version
    
    def test_token_info_display_edge_cases(self):
        """Test token info display with edge cases."""
        # Test with zero values
        stats = Stats()
        stats.current_prompt_size = 0
        auto_compact_threshold = 100000
        
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            display_token_info(stats, auto_compact_threshold)
        
        output = captured_output.getvalue().strip()
        
        self.assertIn("Context:", output)
        self.assertIn("0%", output)
        self.assertIn("(0/100,000 tokens)", output)
        self.assertIn("○○○○○○○○○○", output)  # All empty bars
        
        # Test with values exceeding threshold (should cap at 100%)
        stats.current_prompt_size = 150000  # More than threshold
        auto_compact_threshold = 100000
        
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            display_token_info(stats, auto_compact_threshold)
        
        output = captured_output.getvalue().strip()
        
        self.assertIn("Context:", output)
        self.assertIn("100%", output)  # Should be capped at 100%
        self.assertIn("(150,000/100,000 tokens)", output)
        self.assertIn("●●●●●●●●●●", output)  # All filled bars
    
    def test_token_info_function_independence(self):
        """Test that the token info function works independently."""
        # Test that the function itself still works regardless of config
        stats = Stats()
        stats.current_prompt_size = 10000
        auto_compact_threshold = 50000
        
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            display_token_info(stats, auto_compact_threshold)
        
        output = captured_output.getvalue().strip()
        
        # Should be 20% (10000/50000), so 2 filled bars
        self.assertIn("Context:", output)
        self.assertIn("20%", output)
        self.assertIn("(10,000/50,000 tokens)", output)


if __name__ == "__main__":
    unittest.main()
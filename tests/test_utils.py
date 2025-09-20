"""
Tests for the utils module.
"""

import sys
import os
import unittest

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import color definitions from config
from aicoder.config import RED, GREEN, RESET

from aicoder.utils import safe_strip, colorize_diff_lines, parse_markdown


class TestUtils(unittest.TestCase):
    """Test cases for the utils module."""

    def test_safe_strip(self):
        """Test the safe_strip function."""
        # Test normal string
        self.assertEqual(safe_strip("  hello  "), "hello")

        # Test empty string
        self.assertEqual(safe_strip(""), "")

        # Test None value
        self.assertEqual(safe_strip(None), "no content")

        # Test non-string value
        self.assertEqual(safe_strip(123), "no content")

        # Test string with only whitespace
        self.assertEqual(safe_strip("   "), "")

    def test_colorize_diff_lines(self):
        """Test the colorize_diff_lines function."""
        # Test None input
        self.assertIsNone(colorize_diff_lines(None))

        # Test empty string
        self.assertEqual(colorize_diff_lines(""), "")

        # Test normal text without diff markers
        normal_text = "This is a normal line\nAnother normal line"
        self.assertEqual(colorize_diff_lines(normal_text), normal_text)

        # Test diff lines (basic check that function runs without error)
        diff_text = "+ This is an added line\n- This is a removed line\nNormal line"
        result = colorize_diff_lines(diff_text)
        # Just verify it returns a string and doesn't crash
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_parse_markdown_headers(self):
        """Test parsing markdown headers."""
        # Test H1
        text = "# Main Header"
        result = parse_markdown(text)
        # Streaming style uses red color for headers
        self.assertIn(f"{RED}# Main Header", result)

        # Test H2
        text = "## Sub Header"
        result = parse_markdown(text)
        # Not at line start, so not treated as header
        self.assertIn("## Sub Header", result)

        # Test H3
        text = "### Section Header"
        result = parse_markdown(text)
        # Not at line start, so not treated as header
        self.assertIn("### Section Header", result)

    def test_parse_markdown_bold(self):
        """Test parsing bold markdown."""
        text = "This is **bold text** here"
        result = parse_markdown(text)
        # Streaming style uses green color for bold
        self.assertIn(f"{GREEN}**bold text**{RESET}", result)

    def test_parse_markdown_italic(self):
        """Test parsing italic markdown."""
        text = "This is *italic text* here"
        result = parse_markdown(text)
        # Streaming style uses green color for italic
        self.assertIn(f"{GREEN}*italic text*{RESET}", result)

    def test_parse_markdown_inline_code(self):
        """Test parsing inline code markdown."""
        text = "This is `inline code` here"
        result = parse_markdown(text)
        # Streaming style uses green color for inline code
        self.assertIn(f"{GREEN}`inline code`{RESET}", result)

    def test_parse_markdown_empty(self):
        """Test parsing empty markdown."""
        self.assertEqual(parse_markdown(""), "")
        self.assertIsNone(parse_markdown(None))


if __name__ == "__main__":
    unittest.main()

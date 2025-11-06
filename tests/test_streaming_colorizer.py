"""
Tests for the MarkdownColorizer component.
"""

import unittest
from unittest.mock import patch
import io

from aicoder.streaming_colorizer import MarkdownColorizer


class TestMarkdownColorizer(unittest.TestCase):
    """Test cases for MarkdownColorizer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.colorizer = MarkdownColorizer()

    def capture_print_output(self, func, *args, **kwargs):
        """Capture stdout output from a function call."""
        captured_output = io.StringIO()
        with patch("sys.stdout", captured_output):
            func(*args, **kwargs)
        return captured_output.getvalue()

    def assert_contains_color(self, output, color_variants):
        """Assert that output contains one of the expected color codes."""
        self.assertTrue(
            any(color in output for color in color_variants),
            f"Expected one of {color_variants} in output: {repr(output)}",
        )

    def test_reset_state(self):
        """Test state reset functionality."""
        # Initialize some state
        self.colorizer._in_code = True
        self.colorizer._code_tick_count = 3
        self.colorizer._in_star = True
        self.colorizer._star_count = 2
        self.colorizer._at_line_start = False
        self.colorizer._in_header = True

        # Reset state
        self.colorizer.reset_state()

        # Verify all state is reset
        self.assertFalse(self.colorizer._in_code)
        self.assertEqual(self.colorizer._code_tick_count, 0)
        self.assertFalse(self.colorizer._in_star)
        self.assertEqual(self.colorizer._star_count, 0)
        self.assertTrue(self.colorizer._at_line_start)
        self.assertFalse(self.colorizer._in_header)

    def test_empty_content(self):
        """Test handling of empty content."""
        output = self.capture_print_output(self.colorizer.print_with_colorization, "")
        self.assertEqual(output, "")

    def test_none_content(self):
        """Test handling of None content."""
        output = self.capture_print_output(self.colorizer.print_with_colorization, None)
        self.assertEqual(output, "None")

    def test_plain_text(self):
        """Test plain text without markdown."""
        text = "Hello world"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        self.assertEqual(output, text)

    def test_single_backtick_code(self):
        """Test single backtick code span."""
        text = "`code`"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should contain the text
        self.assertIn("code", output)
        # Should contain some ANSI color codes
        self.assertTrue(
            "\x1b[" in output,
            f"Expected ANSI color codes in output: {repr(output)}"
        )
        # Should contain reset code
        self.assertIn("\x1b[0m", output)  # RESET

    def test_multiple_backticks(self):
        """Test multiple backticks."""
        text = "```code```"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should contain the text
        self.assertIn("```", output)
        # Should contain some ANSI color codes
        self.assertTrue(
            "\x1b[" in output,
            f"Expected ANSI color codes in output: {repr(output)}"
        )
        # Should contain reset code
        self.assertIn("\x1b[0m", output)  # RESET

    def test_asterisk_bold(self):
        """Test asterisk for emphasis."""
        text = "*bold*"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should contain the text
        self.assertIn("bold", output)
        # Should contain some ANSI color codes (not necessarily specific ones)
        self.assertTrue(
            "\x1b[" in output,
            f"Expected ANSI color codes in output: {repr(output)}"
        )
        # Should contain reset code
        self.assertIn("\x1b[0m", output)  # RESET

    def test_multiple_asterisks(self):
        """Test multiple asterisks."""
        text = "**very bold**"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should contain the text
        self.assertIn("**", output)
        # Should contain some ANSI color codes
        self.assertTrue(
            "\x1b[" in output,
            f"Expected ANSI color codes in output: {repr(output)}"
        )
        # Should contain reset code
        self.assertIn("\x1b[0m", output)  # RESET

    def test_header_at_line_start(self):
        """Test header at line start."""
        text = "# Header"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should contain the text
        self.assertIn("# Header", output)
        # Should contain some ANSI color codes
        self.assertTrue(
            "\x1b[" in output,
            f"Expected ANSI color codes in output: {repr(output)}"
        )
        # Note: No reset expected since no newline in text

    def test_header_not_at_line_start(self):
        """Test hash not at line start should not be colored as header."""
        text = "Not # a header"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should not contain red color codes
        red_variants = ["\x1b[31m", "\x1b[38;5;219m"]
        self.assertTrue(
            all(red not in output for red in red_variants)
        )  # No RED variants
        self.assertEqual(output, text)

    def test_newline_resets_state(self):
        """Test that newline resets appropriate state."""
        # Start with header
        text = "# Header\n"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        self.assertIn("\x1b[0m", output)  # Should reset on newline
        self.assertFalse(self.colorizer._in_header)

    def test_newline_resets_star_mode(self):
        """Test that newline resets star mode."""
        # Start with star
        text = "*text\n"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        self.assertIn("\x1b[0m", output)  # Should reset on newline
        self.assertFalse(self.colorizer._in_star)

    def test_code_mode_precedence(self):
        """Test that code mode takes precedence over other modes."""
        text = "`code *not bold*`"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should contain the text
        self.assertIn("code *not bold*", output)
        # Should contain some ANSI color codes
        self.assertTrue(
            "\x1b[" in output,
            f"Expected ANSI color codes in output: {repr(output)}"
        )

    def test_star_mode_precedence(self):
        """Test that star mode takes precedence over header."""
        text = "*#not header*"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should contain the text
        self.assertIn("#not header", output)
        # Should contain some ANSI color codes
        self.assertTrue(
            "\x1b[" in output,
            f"Expected ANSI color codes in output: {repr(output)}"
        )

    def test_complex_markdown(self):
        """Test complex markdown with multiple elements."""
        text = "# Header\nSome `code` and *text*\n## Another header"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should contain the text
        self.assertIn("Header", output)
        self.assertIn("code", output)
        self.assertIn("text", output)
        # Should contain some ANSI color codes
        self.assertTrue(
            "\x1b[" in output,
            f"Expected ANSI color codes in output: {repr(output)}"
        )
        self.assertIn("\x1b[0m", output)  # RESET

    def test_state_preservation_across_calls(self):
        """Test that state is preserved across multiple calls."""
        # Start code in first call
        self.colorizer.print_with_colorization("`unclosed")
        self.assertTrue(self.colorizer._in_code)
        self.assertEqual(self.colorizer._code_tick_count, 1)

        # Close code in second call
        output = self.capture_print_output(
            self.colorizer.print_with_colorization, "code`"
        )
        self.assertIn("\x1b[0m", output)  # Should reset
        self.assertFalse(self.colorizer._in_code)

    def test_mixed_content_with_newlines(self):
        """Test mixed content with newlines."""
        text = "Line 1\n`code`\nLine 3\n# Header\nLine 5"
        output = self.capture_print_output(self.colorizer.print_with_colorization, text)
        # Should contain the text
        self.assertIn("Line 1", output)
        self.assertIn("code", output)
        self.assertIn("Line 3", output)
        self.assertIn("Header", output)
        self.assertIn("Line 5", output)
        # Should contain some ANSI color codes
        self.assertTrue(
            "\x1b[" in output,
            f"Expected ANSI color codes in output: {repr(output)}"
        )
        self.assertEqual(output.count("\n"), 4)  # All newlines preserved


if __name__ == "__main__":
    unittest.main()

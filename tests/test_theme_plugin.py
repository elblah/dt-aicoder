#!/usr/bin/env python3
"""
Unit tests for the theme plugin functionality.
"""

import unittest
import sys
from unittest.mock import patch

# Add the project root to the path
sys.path.insert(0, "/home/blah/poc/aicoder/v2")


class MockAICoder:
    """Mock AICoder instance for testing."""

    def __init__(self):
        self.command_handlers = {}


class TestThemePlugin(unittest.TestCase):
    """Test cases for theme plugin functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Import theme plugin functions
        from docs.plugins.examples.stable.theme.theme import (
            THEMES,
            apply_theme,
            get_current_theme,
            handle_theme_command,
            on_aicoder_init,
        )

        self.THEMES = THEMES
        self.apply_theme = apply_theme
        self.get_current_theme = get_current_theme
        self.handle_theme_command = handle_theme_command
        self.on_aicoder_init = on_aicoder_init

        # Create mock AICoder instance
        self.mock_aicoder = MockAICoder()

        # Initialize the plugin
        self.on_aicoder_init(self.mock_aicoder)

    def test_command_registration(self):
        """Test that the /theme command is properly registered."""
        self.assertIn("/theme", self.mock_aicoder.command_handlers)
        self.assertTrue(callable(self.mock_aicoder.command_handlers["/theme"]))

    def test_apply_valid_theme(self):
        """Test applying a valid theme."""
        result = self.apply_theme("nord")
        self.assertTrue(result)
        current = self.get_current_theme()
        self.assertEqual(current, "nord")

    def test_apply_invalid_theme(self):
        """Test applying an invalid theme."""
        with patch("builtins.print") as mock_print:
            result = self.apply_theme("invalid_theme")
            self.assertFalse(result)
            mock_print.assert_called()

    def test_theme_command_show_current(self):
        """Test /theme command with no arguments."""
        with patch("builtins.print") as mock_print:
            should_quit, run_api_call = self.handle_theme_command(self.mock_aicoder, [])
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            mock_print.assert_called()

    def test_theme_command_list(self):
        """Test /theme list command."""
        with patch("builtins.print") as mock_print:
            should_quit, run_api_call = self.handle_theme_command(
                self.mock_aicoder, ["list"]
            )
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            mock_print.assert_called()

    def test_theme_command_random(self):
        """Test /theme random command."""
        with patch("builtins.print") as mock_print:
            should_quit, run_api_call = self.handle_theme_command(
                self.mock_aicoder, ["random"]
            )
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            mock_print.assert_called()

    def test_theme_command_specific(self):
        """Test /theme <specific_theme> command."""
        with patch("builtins.print") as mock_print:
            should_quit, run_api_call = self.handle_theme_command(
                self.mock_aicoder, ["dracula"]
            )
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            mock_print.assert_called()

        # Verify the theme was actually applied
        current = self.get_current_theme()
        self.assertEqual(current, "dracula")

    def test_theme_command_invalid(self):
        """Test /theme with invalid theme name."""
        with patch("builtins.print") as mock_print:
            should_quit, run_api_call = self.handle_theme_command(
                self.mock_aicoder, ["invalid_theme"]
            )
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            mock_print.assert_called()

    def test_theme_navigation_next(self):
        """Test /theme next command."""
        # Start with a known theme
        self.apply_theme("nord")

        with patch("builtins.print") as mock_print:
            should_quit, run_api_call = self.handle_theme_command(
                self.mock_aicoder, ["next"]
            )
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            mock_print.assert_called()

        # Should be next theme in the list
        current = self.get_current_theme()
        theme_list = list(self.THEMES.keys())
        nord_index = theme_list.index("nord")
        expected_next = theme_list[(nord_index + 1) % len(theme_list)]
        self.assertEqual(current, expected_next)

    def test_theme_navigation_previous(self):
        """Test /theme previous command."""
        # Start with a known theme
        self.apply_theme("nord")

        with patch("builtins.print") as mock_print:
            should_quit, run_api_call = self.handle_theme_command(
                self.mock_aicoder, ["previous"]
            )
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            mock_print.assert_called()

        # Should be previous theme in the list
        current = self.get_current_theme()
        theme_list = list(self.THEMES.keys())
        nord_index = theme_list.index("nord")
        expected_prev = theme_list[(nord_index - 1) % len(theme_list)]
        self.assertEqual(current, expected_prev)

    def test_theme_command_help(self):
        """Test /theme help command."""
        with patch("builtins.print") as mock_print:
            should_quit, run_api_call = self.handle_theme_command(
                self.mock_aicoder, ["help"]
            )
            self.assertFalse(should_quit)
            self.assertFalse(run_api_call)
            mock_print.assert_called()

    def test_themes_data_structure(self):
        """Test that themes data structure is valid."""
        self.assertIsInstance(self.THEMES, dict)
        self.assertGreater(len(self.THEMES), 0)

        # Check that each theme has required color keys
        required_colors = [
            "RED",
            "GREEN",
            "YELLOW",
            "BLUE",
            "MAGENTA",
            "CYAN",
            "WHITE",
            "RESET",
        ]
        for theme_name, theme_colors in self.THEMES.items():
            self.assertIsInstance(theme_colors, dict)
            for color in required_colors:
                self.assertIn(color, theme_colors)
                self.assertTrue(theme_colors[color].startswith("\033["))


if __name__ == "__main__":
    unittest.main()

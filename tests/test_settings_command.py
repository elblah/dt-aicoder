"""
Tests for settings command functionality.
"""

import tempfile
import unittest
from unittest.mock import Mock
from io import StringIO
import sys

from aicoder.commands.settings_command import SettingsCommand
from aicoder.persistent_config import PersistentConfig


class TestSettingsCommand(unittest.TestCase):
    """Test cases for SettingsCommand class."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.persistent_config = PersistentConfig(self.test_dir)

        # Create mock app instance
        self.app = Mock()
        self.app.persistent_config = self.persistent_config

        # Create command instance
        self.command = SettingsCommand(self.app)

        # Capture stdout
        self.captured_output = StringIO()
        self.original_stdout = sys.stdout
        sys.stdout = self.captured_output

    def tearDown(self):
        """Clean up test environment."""
        sys.stdout = self.original_stdout
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    def get_output(self):
        """Get captured stdout output."""
        return self.captured_output.getvalue().strip()

    def test_show_all_settings_empty(self):
        """Test showing all settings when none are set."""
        self.command.execute([])
        output = self.get_output()
        self.assertIn("No persistent settings configured.", output)

    def test_show_all_settings_with_values(self):
        """Test showing all settings when some are set."""
        self.persistent_config["todo.enabled"] = True
        self.persistent_config["ui.theme"] = "dark"

        self.command.execute([])
        output = self.get_output()
        self.assertIn("Current persistent settings:", output)
        self.assertIn("todo.enabled: True", output)
        self.assertIn("ui.theme: dark", output)

    def test_show_specific_setting_exists(self):
        """Test showing a specific setting that exists."""
        self.persistent_config["todo.enabled"] = False

        self.command.execute(["todo.enabled"])
        output = self.get_output()
        self.assertIn("todo.enabled: False", output)

    def test_show_specific_setting_not_exists(self):
        """Test showing a specific setting that doesn't exist."""
        self.command.execute(["nonexistent.key"])
        output = self.get_output()
        self.assertIn("Setting 'nonexistent.key' not found.", output)

    def test_set_setting_boolean_true(self):
        """Test setting a boolean value to true."""
        self.command.execute(["todo.enabled", "true"])
        self.assertEqual(self.persistent_config["todo.enabled"], True)
        output = self.get_output()
        self.assertIn("Set todo.enabled: True", output)

    def test_set_setting_boolean_false(self):
        """Test setting a boolean value to false."""
        self.command.execute(["todo.enabled", "false"])
        self.assertEqual(self.persistent_config["todo.enabled"], False)
        output = self.get_output()
        self.assertIn("Set todo.enabled: False", output)

    def test_set_setting_variations(self):
        """Test various boolean value representations."""
        test_cases = [
            ("on", True),
            ("yes", True),
            ("1", True),
            ("off", False),
            ("no", False),
            ("0", False),
        ]

        for value, expected in test_cases:
            with self.subTest(value=value, expected=expected):
                self.command.execute(["test.key", value])
                self.assertEqual(self.persistent_config["test.key"], expected)

    def test_set_setting_numeric(self):
        """Test setting numeric values."""
        # Integer
        self.command.execute(["test.int", "42"])
        self.assertEqual(self.persistent_config["test.int"], 42)

        # Float
        self.command.execute(["test.float", "3.14"])
        self.assertEqual(self.persistent_config["test.float"], 3.14)

    def test_set_setting_string(self):
        """Test setting string values."""
        self.command.execute(["test.string", "hello"])
        self.assertEqual(self.persistent_config["test.string"], "hello")

    def test_set_setting_with_spaces(self):
        """Test setting a value with spaces."""
        self.command.execute(["test.message", "hello", "world", "with", "spaces"])
        self.assertEqual(
            self.persistent_config["test.message"], "hello world with spaces"
        )

    def test_update_existing_setting(self):
        """Test updating an existing setting."""
        # Set initial value
        self.persistent_config["test.key"] = "initial"

        self.command.execute(["test.key", "updated"])
        self.assertEqual(self.persistent_config["test.key"], "updated")
        output = self.get_output()
        self.assertIn("Updated test.key: initial → updated", output)

    def test_show_help(self):
        """Test showing help."""
        self.command.execute(["help"])
        output = self.get_output()
        self.assertIn("Settings command usage:", output)

    def test_aliases(self):
        """Test that command has correct aliases."""
        expected_aliases = ["/settings", "/setting", "/config"]
        self.assertEqual(self.command.aliases, expected_aliases)

    def test_persistence(self):
        """Test that settings persist across config instances."""
        # Set a value
        self.command.execute(["persistent.test", "value123"])

        # Create new config instance
        new_config = PersistentConfig(self.test_dir)
        self.assertEqual(new_config["persistent.test"], "value123")

    def test_return_values(self):
        """Test that execute returns correct values."""
        should_quit, run_api_call = self.command.execute(["test.key", "value"])
        self.assertFalse(should_quit)
        self.assertFalse(run_api_call)


if __name__ == "__main__":
    unittest.main()

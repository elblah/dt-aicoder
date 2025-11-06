"""
Test for the truncation settings fix.
"""

import unittest
from unittest.mock import Mock
from aicoder.commands.settings_command import SettingsCommand
from aicoder import config


class TestTruncationSettingsFix(unittest.TestCase):
    """Test cases for the truncation settings fix."""

    def setUp(self):
        """Set up test environment."""
        # Clear global app instance to avoid test pollution
        config.set_app_instance(None)
        
        self.mock_app = Mock()
        self.mock_app.persistent_config = {}
        self.command = SettingsCommand(self.mock_app)

    def tearDown(self):
        """Clean up test environment."""
        # Clear global app instance to avoid test pollution
        config.set_app_instance(None)

    def test_parse_value_truncation_with_integer_string(self):
        """Test that truncation with integer string works."""
        result = self.command._parse_value("500", "truncation")
        self.assertEqual(result, 500)
        self.assertIsInstance(result, int)

    def test_parse_value_truncation_with_float_string(self):
        """Test that truncation with float string converts to int."""
        result = self.command._parse_value("500.0", "truncation")
        self.assertEqual(result, 500)
        self.assertIsInstance(result, int)

    def test_parse_value_truncation_with_float_decimal(self):
        """Test that truncation with decimal float converts to int."""
        result = self.command._parse_value("750.5", "truncation")
        self.assertEqual(result, 750)
        self.assertIsInstance(result, int)

    def test_parse_value_truncation_with_invalid_string(self):
        """Test that invalid truncation value returns None."""
        result = self.command._parse_value("invalid", "truncation")
        self.assertIsNone(result)

    def test_parse_value_non_truncation_with_float(self):
        """Test that non-truncation values still work with floats."""
        result = self.command._parse_value("0.5", "temperature")
        self.assertEqual(result, 0.5)
        self.assertIsInstance(result, float)

    def test_set_setting_truncation_valid(self):
        """Test setting truncation with valid value."""
        self.command._set_setting("truncation", "750.0")
        
        # Should be stored as integer
        self.assertEqual(self.mock_app.persistent_config["truncation"], 750)
        self.assertIsInstance(self.mock_app.persistent_config["truncation"], int)

    def test_set_setting_truncation_invalid(self):
        """Test setting truncation with invalid value."""
        self.command._set_setting("truncation", "invalid")
        
        # Should not be stored
        self.assertNotIn("truncation", self.mock_app.persistent_config)

    def test_set_setting_other_numeric_unchanged(self):
        """Test that other numeric settings are unaffected."""
        self.command._set_setting("temperature", "0.7")
        
        # Should still be stored as float
        self.assertEqual(self.mock_app.persistent_config["temperature"], 0.7)
        self.assertIsInstance(self.mock_app.persistent_config["temperature"], float)


if __name__ == "__main__":
    unittest.main()
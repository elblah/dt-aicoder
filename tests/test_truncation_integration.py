"""
Integration tests for truncation override functionality.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from aicoder.app import AICoder
from aicoder import config


class TestTruncationIntegration(unittest.TestCase):
    """Integration tests for truncation functionality."""

    def setUp(self):
        """Set up test environment."""
        # Save original environment and working directory
        self.original_env = os.environ.get("DEFAULT_TRUNCATION_LIMIT")
        self.original_cwd = os.getcwd()
        os.environ["DEFAULT_TRUNCATION_LIMIT"] = "300"
        
        # Clear global app instance to avoid test pollution
        config.set_app_instance(None)

    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment and working directory
        if self.original_env is not None:
            os.environ["DEFAULT_TRUNCATION_LIMIT"] = self.original_env
        elif "DEFAULT_TRUNCATION_LIMIT" in os.environ:
            del os.environ["DEFAULT_TRUNCATION_LIMIT"]
        
        os.chdir(self.original_cwd)
        
        # Clear global app instance to avoid test pollution
        config.set_app_instance(None)

    def test_app_sets_config_instance(self):
        """Test that app instance is properly set in config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            # Create app in isolated temp directory
            app = AICoder()
            
            # Set truncation in persistent config
            app.persistent_config["truncation"] = "500"

            # Check that config now uses the override
            limit = config.get_effective_truncation_limit()
            self.assertEqual(limit, 500)

    def test_truncation_override_with_invalid_value(self):
        """Test that invalid truncation value falls back to env."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            app = AICoder()

            # Set invalid truncation value
            app.persistent_config["truncation"] = "invalid"

            # Should fall back to environment
            limit = config.get_effective_truncation_limit()
            self.assertEqual(limit, 300)

    def test_truncation_override_with_numeric_values(self):
        """Test that numeric truncation values work correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            
            app = AICoder()

            # Test float
            app.persistent_config["truncation"] = 750.5
            limit = config.get_effective_truncation_limit()
            self.assertEqual(limit, 750)  # Should be converted to int


if __name__ == "__main__":
    unittest.main()
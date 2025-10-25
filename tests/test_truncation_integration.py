"""
Integration tests for truncation override functionality.
"""

import os
import tempfile
import unittest

from aicoder.app import AICoder
from aicoder import config


class TestTruncationIntegration(unittest.TestCase):
    """Integration tests for truncation functionality."""

    def setUp(self):
        """Set up test environment."""
        # Save original environment
        self.original_env = os.environ.get("DEFAULT_TRUNCATION_LIMIT")
        os.environ["DEFAULT_TRUNCATION_LIMIT"] = "300"

    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        if self.original_env is not None:
            os.environ["DEFAULT_TRUNCATION_LIMIT"] = self.original_env
        elif "DEFAULT_TRUNCATION_LIMIT" in os.environ:
            del os.environ["DEFAULT_TRUNCATION_LIMIT"]

    def test_app_sets_config_instance(self):
        """Test that app instance is properly set in config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory to avoid existing config
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Create app
                app = AICoder()
                
                # Check that config has the app instance
                limit = config.get_effective_truncation_limit()
                self.assertEqual(limit, 300)  # Default from env
                
                # Set truncation in persistent config
                app.persistent_config["truncation"] = "500"
                
                # Check that config now uses the override
                limit = config.get_effective_truncation_limit()
                self.assertEqual(limit, 500)
            finally:
                os.chdir(original_cwd)

    def test_truncation_override_with_invalid_value(self):
        """Test that invalid truncation value falls back to env."""
        with tempfile.TemporaryDirectory():
            app = AICoder()
            
            # Set invalid truncation value
            app.persistent_config["truncation"] = "invalid"
            
            # Should fall back to environment
            limit = config.get_effective_truncation_limit()
            self.assertEqual(limit, 300)

    def test_truncation_override_with_numeric_values(self):
        """Test that numeric truncation values work correctly."""
        with tempfile.TemporaryDirectory():
            app = AICoder()
            
            # Test integer
            app.persistent_config["truncation"] = 1000
            limit = config.get_effective_truncation_limit()
            self.assertEqual(limit, 1000)
            
            # Test float
            app.persistent_config["truncation"] = 750.5
            limit = config.get_effective_truncation_limit()
            self.assertEqual(limit, 750)  # Should be converted to int


if __name__ == "__main__":
    unittest.main()
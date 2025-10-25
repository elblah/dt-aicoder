"""
Tests for truncation configuration functionality.
"""

import os
import unittest
from unittest.mock import Mock

from aicoder import config


class TestTruncationConfig(unittest.TestCase):
    """Test cases for truncation configuration."""

    def setUp(self):
        """Set up test environment."""
        # Save original environment
        self.original_env = os.environ.get("DEFAULT_TRUNCATION_LIMIT")
        os.environ["DEFAULT_TRUNCATION_LIMIT"] = "300"
        
        # Clear any existing app instance
        config.set_app_instance(None)

    def tearDown(self):
        """Clean up test environment."""
        # Restore original environment
        if self.original_env is not None:
            os.environ["DEFAULT_TRUNCATION_LIMIT"] = self.original_env
        elif "DEFAULT_TRUNCATION_LIMIT" in os.environ:
            del os.environ["DEFAULT_TRUNCATION_LIMIT"]
        
        # Clear app instance
        config.set_app_instance(None)

    def test_get_effective_truncation_limit_env_only(self):
        """Test that truncation limit comes from environment when no setting exists."""
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 300)

    def test_get_effective_truncation_limit_with_app_setting(self):
        """Test that truncation limit comes from persistent config when set."""
        # Mock the app with persistent config
        mock_app = Mock()
        mock_app.persistent_config = {"truncation": "500"}
        
        config.set_app_instance(mock_app)
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 500)

    def test_get_effective_truncation_limit_with_int_setting(self):
        """Test that integer truncation setting works."""
        mock_app = Mock()
        mock_app.persistent_config = {"truncation": 1000}
        
        config.set_app_instance(mock_app)
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 1000)

    def test_get_effective_truncation_limit_with_float_setting(self):
        """Test that float truncation setting is converted to int."""
        mock_app = Mock()
        mock_app.persistent_config = {"truncation": 750.5}
        
        config.set_app_instance(mock_app)
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 750)

    def test_get_effective_truncation_limit_invalid_string(self):
        """Test that invalid string falls back to environment."""
        mock_app = Mock()
        mock_app.persistent_config = {"truncation": "invalid"}
        
        config.set_app_instance(mock_app)
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 300)

    def test_get_effective_truncation_limit_no_app(self):
        """Test that missing app falls back to environment."""
        config.set_app_instance(None)
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 300)

    def test_get_effective_truncation_limit_no_persistent_config(self):
        """Test that missing persistent config falls back to environment."""
        mock_app = Mock()
        del mock_app.persistent_config  # Remove the attribute
        
        config.set_app_instance(mock_app)
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 300)

    def test_get_effective_truncation_limit_no_truncation_key(self):
        """Test that missing truncation key falls back to environment."""
        mock_app = Mock()
        mock_app.persistent_config = {"other.setting": "value"}
        
        config.set_app_instance(mock_app)
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 300)

    def test_set_app_instance_functionality(self):
        """Test that set_app_instance works correctly."""
        mock_app = Mock()
        mock_app.persistent_config = {"truncation": "999"}
        
        # Set app instance
        config.set_app_instance(mock_app)
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 999)
        
        # Clear app instance
        config.set_app_instance(None)
        limit = config.get_effective_truncation_limit()
        self.assertEqual(limit, 300)


if __name__ == "__main__":
    unittest.main()
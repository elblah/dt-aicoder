"""
Unit tests for TOP_K configuration functionality.
"""

import os
import unittest
from unittest.mock import patch

from aicoder import config


class TestTopKConfiguration(unittest.TestCase):
    """Test cases for TOP_K environment variable configuration."""

    def setUp(self):
        """Clean up environment before each test."""
        if "TOP_K" in os.environ:
            del os.environ["TOP_K"]

    def tearDown(self):
        """Clean up environment after each test."""
        if "TOP_K" in os.environ:
            del os.environ["TOP_K"]

    def test_default_top_k_value(self):
        """Test that TOP_K defaults to 0 when not set."""
        top_k = int(os.environ.get("TOP_K", "0"))
        self.assertEqual(top_k, 0)

    def test_top_k_environment_variable_read(self):
        """Test that TOP_K is correctly read from environment variable."""
        os.environ["TOP_K"] = "50"
        top_k = int(os.environ.get("TOP_K", "0"))
        self.assertEqual(top_k, 50)

    def test_top_k_invalid_value_handled(self):
        """Test that invalid TOP_K values are handled gracefully."""
        os.environ["TOP_K"] = "invalid"
        # This should raise ValueError when converting to int
        with self.assertRaises(ValueError):
            int(os.environ.get("TOP_K", "0"))

    @patch.dict(os.environ, {"TOP_K": "40"})
    def test_top_k_with_environment_variable(self):
        """Test TOP_K configuration when environment variable is set."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)
        top_k = int(os.environ.get("TOP_K", "0"))
        self.assertEqual(top_k, 40)

    @patch.dict(os.environ, {"TOP_K": "40"})
    def test_top_k_config_value_matches_environment(self):
        """Test that config.TOP_K matches environment variable value."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)
        self.assertEqual(config.TOP_K, 40)

    @patch.dict(os.environ, {"TOP_K": "100"})
    def test_top_k_high_value(self):
        """Test TOP_K with a high value."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)
        top_k = int(os.environ.get("TOP_K", "0"))
        self.assertEqual(top_k, 100)

    @patch.dict(os.environ, {"TOP_K": "0"})
    def test_top_k_zero_value(self):
        """Test TOP_K when explicitly set to 0 (should be treated as disabled)."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)
        top_k = int(os.environ.get("TOP_K", "0"))
        self.assertEqual(top_k, 0)


class TestTopKInAPIRequest(unittest.TestCase):
    """Test cases for TOP_K inclusion in API requests."""

    def setUp(self):
        """Clean up environment before each test."""
        if "TOP_K" in os.environ:
            del os.environ["TOP_K"]
        # Reload config to ensure clean state
        from importlib import reload

        reload(config)

    def tearDown(self):
        """Clean up environment after each test."""
        if "TOP_K" in os.environ:
            del os.environ["TOP_K"]
        # Reload config to clean up
        from importlib import reload

        reload(config)

    def test_top_k_not_included_when_not_set(self):
        """Test that top_k is not included in API data when TOP_K is not set."""
        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertNotIn("top_k", api_data)

    @patch.dict(os.environ, {"TOP_K": "40"})
    def test_top_k_included_when_set(self):
        """Test that top_k is included in API data when TOP_K is set."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)

        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertIn("top_k", api_data)
        self.assertEqual(api_data["top_k"], 40)

    @patch.dict(os.environ, {"TOP_K": "0"})
    def test_top_k_not_included_when_zero(self):
        """Test that top_k is not included when TOP_K is 0 (disabled)."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)

        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertNotIn("top_k", api_data)


class TestTopKWithTopP(unittest.TestCase):
    """Test cases for TOP_K interaction with TOP_P."""

    def setUp(self):
        """Clean up environment before each test."""
        for env_var in ["TOP_K", "TOP_P"]:
            if env_var in os.environ:
                del os.environ[env_var]
        # Reload config to ensure clean state
        from importlib import reload

        reload(config)

    def tearDown(self):
        """Clean up environment after each test."""
        for env_var in ["TOP_K", "TOP_P"]:
            if env_var in os.environ:
                del os.environ[env_var]
        # Reload config to clean up
        from importlib import reload

        reload(config)

    @patch.dict(os.environ, {"TOP_K": "40", "TOP_P": "0.95"})
    def test_both_top_k_and_top_p_included(self):
        """Test that both top_k and top_p are included when both are set."""
        # Reload config to pick up environment variables
        from importlib import reload

        reload(config)

        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertIn("top_k", api_data)
        self.assertIn("top_p", api_data)
        self.assertEqual(api_data["top_k"], 40)
        self.assertEqual(api_data["top_p"], 0.95)

    @patch.dict(os.environ, {"TOP_K": "40"})
    def test_only_top_k_included(self):
        """Test that only top_k is included when only TOP_K is set."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)

        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertIn("top_k", api_data)
        self.assertNotIn("top_p", api_data)
        self.assertEqual(api_data["top_k"], 40)


if __name__ == "__main__":
    unittest.main()

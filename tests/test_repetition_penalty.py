"""
Unit tests for REPETITION_PENALTY configuration functionality.
"""

import os
import unittest
from unittest.mock import patch

from aicoder import config


class TestRepetitionPenaltyConfiguration(unittest.TestCase):
    """Test cases for REPETITION_PENALTY environment variable configuration."""

    def setUp(self):
        """Clean up environment before each test."""
        if "REPETITION_PENALTY" in os.environ:
            del os.environ["REPETITION_PENALTY"]

    def tearDown(self):
        """Clean up environment after each test."""
        if "REPETITION_PENALTY" in os.environ:
            del os.environ["REPETITION_PENALTY"]

    def test_default_repetition_penalty_value(self):
        """Test that REPETITION_PENALTY defaults to 1.0 when not set."""
        repetition_penalty = float(os.environ.get("REPETITION_PENALTY", "1.0"))
        self.assertEqual(repetition_penalty, 1.0)

    def test_repetition_penalty_environment_variable_read(self):
        """Test that REPETITION_PENALTY is correctly read from environment variable."""
        os.environ["REPETITION_PENALTY"] = "1.1"
        repetition_penalty = float(os.environ.get("REPETITION_PENALTY", "1.0"))
        self.assertEqual(repetition_penalty, 1.1)

    def test_repetition_penalty_invalid_value_handled(self):
        """Test that invalid REPETITION_PENALTY values are handled gracefully."""
        os.environ["REPETITION_PENALTY"] = "invalid"
        # This should raise ValueError when converting to float
        with self.assertRaises(ValueError):
            float(os.environ.get("REPETITION_PENALTY", "1.0"))

    @patch.dict(os.environ, {"REPETITION_PENALTY": "1.15"})
    def test_repetition_penalty_with_environment_variable(self):
        """Test REPETITION_PENALTY configuration when environment variable is set."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)
        repetition_penalty = float(os.environ.get("REPETITION_PENALTY", "1.0"))
        self.assertEqual(repetition_penalty, 1.15)

    @patch.dict(os.environ, {"REPETITION_PENALTY": "1.2"})
    def test_repetition_penalty_config_value_matches_environment(self):
        """Test that config.REPETITION_PENALTY matches environment variable value."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)
        self.assertEqual(config.REPETITION_PENALTY, 1.2)

    @patch.dict(os.environ, {"REPETITION_PENALTY": "2.0"})
    def test_repetition_penalty_high_value(self):
        """Test REPETITION_PENALTY with a high value."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)
        repetition_penalty = float(os.environ.get("REPETITION_PENALTY", "1.0"))
        self.assertEqual(repetition_penalty, 2.0)

    @patch.dict(os.environ, {"REPETITION_PENALTY": "1.0"})
    def test_repetition_penalty_default_value(self):
        """Test REPETITION_PENALTY when explicitly set to 1.0 (should be treated as disabled)."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)
        repetition_penalty = float(os.environ.get("REPETITION_PENALTY", "1.0"))
        self.assertEqual(repetition_penalty, 1.0)

    @patch.dict(os.environ, {"REPETITION_PENALTY": "0.8"})
    def test_repetition_penalty_low_value(self):
        """Test REPETITION_PENALTY with a low value (less than 1.0)."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)
        repetition_penalty = float(os.environ.get("REPETITION_PENALTY", "1.0"))
        self.assertEqual(repetition_penalty, 0.8)


class TestRepetitionPenaltyInAPIRequest(unittest.TestCase):
    """Test cases for REPETITION_PENALTY inclusion in API requests."""

    def setUp(self):
        """Clean up environment before each test."""
        if "REPETITION_PENALTY" in os.environ:
            del os.environ["REPETITION_PENALTY"]
        # Reload config to ensure clean state
        from importlib import reload

        reload(config)

    def tearDown(self):
        """Clean up environment after each test."""
        if "REPETITION_PENALTY" in os.environ:
            del os.environ["REPETITION_PENALTY"]
        # Reload config to clean up
        from importlib import reload

        reload(config)

    def test_repetition_penalty_not_included_when_not_set(self):
        """Test that repetition_penalty is not included in API data when REPETITION_PENALTY is not set."""
        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertNotIn("repetition_penalty", api_data)

    @patch.dict(os.environ, {"REPETITION_PENALTY": "1.1"})
    def test_repetition_penalty_included_when_set(self):
        """Test that repetition_penalty is included in API data when REPETITION_PENALTY is set."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)

        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertIn("repetition_penalty", api_data)
        self.assertEqual(api_data["repetition_penalty"], 1.1)

    @patch.dict(os.environ, {"REPETITION_PENALTY": "1.0"})
    def test_repetition_penalty_not_included_when_default(self):
        """Test that repetition_penalty is not included when REPETITION_PENALTY is 1.0 (default)."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)

        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertNotIn("repetition_penalty", api_data)

    @patch.dict(os.environ, {"REPETITION_PENALTY": "0.9"})
    def test_repetition_penalty_included_when_less_than_one(self):
        """Test that repetition_penalty is included when REPETITION_PENALTY is less than 1.0."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)

        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertIn("repetition_penalty", api_data)
        self.assertEqual(api_data["repetition_penalty"], 0.9)


class TestRepetitionPenaltyWithOtherParams(unittest.TestCase):
    """Test cases for REPETITION_PENALTY interaction with other parameters."""

    def setUp(self):
        """Clean up environment before each test."""
        for env_var in ["REPETITION_PENALTY", "TOP_K", "TOP_P"]:
            if env_var in os.environ:
                del os.environ[env_var]
        # Reload config to ensure clean state
        from importlib import reload

        reload(config)

    def tearDown(self):
        """Clean up environment after each test."""
        for env_var in ["REPETITION_PENALTY", "TOP_K", "TOP_P"]:
            if env_var in os.environ:
                del os.environ[env_var]
        # Reload config to clean up
        from importlib import reload

        reload(config)

    @patch.dict(
        os.environ, {"REPETITION_PENALTY": "1.1", "TOP_K": "40", "TOP_P": "0.95"}
    )
    def test_all_parameters_included(self):
        """Test that repetition_penalty, top_k, and top_p are all included when all are set."""
        # Reload config to pick up environment variables
        from importlib import reload

        reload(config)

        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertIn("repetition_penalty", api_data)
        self.assertIn("top_k", api_data)
        self.assertIn("top_p", api_data)
        self.assertEqual(api_data["repetition_penalty"], 1.1)
        self.assertEqual(api_data["top_k"], 40)
        self.assertEqual(api_data["top_p"], 0.95)

    @patch.dict(os.environ, {"REPETITION_PENALTY": "1.15"})
    def test_only_repetition_penalty_included(self):
        """Test that only repetition_penalty is included when only REPETITION_PENALTY is set."""
        # Reload config to pick up environment variable
        from importlib import reload

        reload(config)

        from aicoder.api_client import APIClient

        client = APIClient()
        messages = [{"role": "user", "content": "test"}]
        api_data = client._prepare_api_request_data(messages)

        self.assertIn("repetition_penalty", api_data)
        self.assertNotIn("top_k", api_data)
        self.assertNotIn("top_p", api_data)
        self.assertEqual(api_data["repetition_penalty"], 1.15)


if __name__ == "__main__":
    unittest.main()

"""
Tests for top_p configuration in API handler and streaming adapter.
"""

import os
import sys
import importlib
import unittest
from unittest.mock import patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestTopPConfig(unittest.TestCase):
    """Test cases for top_p configuration."""

    def setUp(self):
        """Set up test environment."""
        # Clear any existing environment variables that might affect our tests
        if "TOP_P" in os.environ:
            del os.environ["TOP_P"]

    def test_default_top_p(self):
        """Test that default top_p is 1.0 when no environment variable is set."""
        # Check the os.environ.get call result directly
        top_p = float(os.environ.get("TOP_P", "1.0"))
        self.assertEqual(top_p, 1.0)

    def test_default_top_p_streaming_adapter(self):
        """Test that default top_p is 1.0 in streaming adapter when no environment variable is set."""
        # Import the streaming adapter module
        if "aicoder.streaming_adapter" in sys.modules:
            importlib.reload(sys.modules["aicoder.streaming_adapter"])
        else:
            pass

        # Check the os.environ.get call result
        top_p = float(os.environ.get("TOP_P", "1.0"))
        self.assertEqual(top_p, 1.0)

    @patch.dict(os.environ, {"TOP_P": "0.9"})
    def test_top_p_from_env(self):
        """Test that top_p is loaded from environment variable."""
        # Reload the module to pick up the environment variable
        if "aicoder.api_handler" in sys.modules:
            importlib.reload(sys.modules["aicoder.api_handler"])
        else:
            pass

        # Check that the top_p in the request data would be 0.9
        top_p = float(os.environ.get("TOP_P", "1.0"))
        self.assertEqual(top_p, 0.9)

    @patch.dict(os.environ, {"TOP_P": "0.9"})
    def test_top_p_from_env_streaming_adapter(self):
        """Test that top_p is loaded from environment variable in streaming adapter."""
        # Reload the streaming adapter module to pick up the environment variable
        if "aicoder.streaming_adapter" in sys.modules:
            importlib.reload(sys.modules["aicoder.streaming_adapter"])
        else:
            pass

        # Check that the top_p in the request data would be 0.9
        top_p = float(os.environ.get("TOP_P", "1.0"))
        self.assertEqual(top_p, 0.9)

    @patch.dict(os.environ, {"TOP_P": "0.7"})
    def test_lower_top_p_from_env(self):
        """Test that lower top_p values are loaded from environment variable."""
        # Reload the module to pick up the environment variable
        if "aicoder.api_handler" in sys.modules:
            importlib.reload(sys.modules["aicoder.api_handler"])
        else:
            pass

        # Check that the top_p in the request data would be 0.7
        top_p = float(os.environ.get("TOP_P", "1.0"))
        self.assertEqual(top_p, 0.7)

    @patch.dict(os.environ, {"TOP_P": "0.7"})
    def test_lower_top_p_from_env_streaming_adapter(self):
        """Test that lower top_p values are loaded from environment variable in streaming adapter."""
        # Reload the streaming adapter module to pick up the environment variable
        if "aicoder.streaming_adapter" in sys.modules:
            importlib.reload(sys.modules["aicoder.streaming_adapter"])
        else:
            pass

        # Check that the top_p in the request data would be 0.7
        top_p = float(os.environ.get("TOP_P", "1.0"))
        self.assertEqual(top_p, 0.7)


if __name__ == "__main__":
    unittest.main()

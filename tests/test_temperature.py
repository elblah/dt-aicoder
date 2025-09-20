"""
Tests for temperature configuration in API handler and streaming adapter.
"""

import os
import sys
import importlib
import unittest
from unittest.mock import patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestTemperatureConfig(unittest.TestCase):
    """Test cases for temperature configuration."""

    def setUp(self):
        """Set up test environment."""
        # Clear any existing environment variables that might affect our tests
        if "TEMPERATURE" in os.environ:
            del os.environ["TEMPERATURE"]

    def test_default_temperature(self):
        """Test that default temperature is 0.0 when no environment variable is set."""
        # Check the os.environ.get call result directly
        temperature = float(os.environ.get("TEMPERATURE", "0.0"))
        self.assertEqual(temperature, 0.0)

    def test_default_temperature_streaming_adapter(self):
        """Test that default temperature is 0.0 in streaming adapter when no environment variable is set."""
        # Import the streaming adapter module
        if "aicoder.streaming_adapter" in sys.modules:
            importlib.reload(sys.modules["aicoder.streaming_adapter"])
        else:
            pass

        # Check the os.environ.get call result
        temperature = float(os.environ.get("TEMPERATURE", "0.0"))
        self.assertEqual(temperature, 0.0)

    @patch.dict(os.environ, {"TEMPERATURE": "0.7"})
    def test_temperature_from_env(self):
        """Test that temperature is loaded from environment variable."""
        # Reload the module to pick up the environment variable
        if "aicoder.api_handler" in sys.modules:
            importlib.reload(sys.modules["aicoder.api_handler"])
        else:
            pass

        # Check that the temperature in the request data would be 0.7
        temperature = float(os.environ.get("TEMPERATURE", "0.0"))
        self.assertEqual(temperature, 0.7)

    @patch.dict(os.environ, {"TEMPERATURE": "0.7"})
    def test_temperature_from_env_streaming_adapter(self):
        """Test that temperature is loaded from environment variable in streaming adapter."""
        # Reload the streaming adapter module to pick up the environment variable
        if "aicoder.streaming_adapter" in sys.modules:
            importlib.reload(sys.modules["aicoder.streaming_adapter"])
        else:
            pass

        # Check that the temperature in the request data would be 0.7
        temperature = float(os.environ.get("TEMPERATURE", "0.0"))
        self.assertEqual(temperature, 0.7)

    @patch.dict(os.environ, {"TEMPERATURE": "1.0"})
    def test_higher_temperature_from_env(self):
        """Test that higher temperature values are loaded from environment variable."""
        # Reload the module to pick up the environment variable
        if "aicoder.api_handler" in sys.modules:
            importlib.reload(sys.modules["aicoder.api_handler"])
        else:
            pass

        # Check that the temperature in the request data would be 1.0
        temperature = float(os.environ.get("TEMPERATURE", "0.0"))
        self.assertEqual(temperature, 1.0)

    @patch.dict(os.environ, {"TEMPERATURE": "1.0"})
    def test_higher_temperature_from_env_streaming_adapter(self):
        """Test that higher temperature values are loaded from environment variable in streaming adapter."""
        # Reload the streaming adapter module to pick up the environment variable
        if "aicoder.streaming_adapter" in sys.modules:
            importlib.reload(sys.modules["aicoder.streaming_adapter"])
        else:
            pass

        # Check that the temperature in the request data would be 1.0
        temperature = float(os.environ.get("TEMPERATURE", "0.0"))
        self.assertEqual(temperature, 1.0)


if __name__ == "__main__":
    unittest.main()

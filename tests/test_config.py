"""
Tests for the config module.
"""

import os
import sys
import importlib
import unittest
from unittest.mock import patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.config import (
    DEBUG,
    API_KEY,
    API_MODEL,
    YOLO_MODE,
    SHELL_COMMANDS_DENY_ALL,
    SHELL_COMMANDS_ALLOW_ALL,
    ENABLE_STREAMING,
)


class TestConfig(unittest.TestCase):
    """Test cases for the config module."""

    def test_default_config_values(self):
        """Test that default config values are set correctly."""
        # Test default values (without environment variables)
        self.assertFalse(DEBUG)
        # API_KEY and API_MODEL might be set from environment, so we just check they're strings
        self.assertIsInstance(API_KEY, str)
        self.assertIsInstance(API_MODEL, str)
        # YOLO_MODE might be set by test runner, so we check it's a boolean
        self.assertIsInstance(YOLO_MODE, bool)
        self.assertFalse(SHELL_COMMANDS_DENY_ALL)
        self.assertFalse(SHELL_COMMANDS_ALLOW_ALL)
        self.assertTrue(ENABLE_STREAMING)  # Streaming is enabled by default

    @patch.dict(os.environ, {"DEBUG": "1"})
    def test_debug_mode_enabled(self):
        """Test that debug mode is enabled when environment variable is set."""
        # Reload the config module to pick up the environment variable
        import aicoder.config

        importlib.reload(aicoder.config)

        self.assertTrue(aicoder.config.DEBUG)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123"})
    def test_api_key_from_env(self):
        """Test that API key is loaded from environment variable."""
        import aicoder.config

        importlib.reload(aicoder.config)

        self.assertEqual(aicoder.config.API_KEY, "test-key-123")

    @patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4-turbo"})
    def test_model_from_env(self):
        """Test that model is loaded from environment variable."""
        import aicoder.config

        importlib.reload(aicoder.config)

        self.assertEqual(aicoder.config.API_MODEL, "gpt-4-turbo")

    @patch.dict(os.environ, {"DISABLE_STREAMING": "1"})
    def test_streaming_disabled(self):
        """Test that streaming is disabled when environment variable is set."""
        import aicoder.config

        importlib.reload(aicoder.config)

        self.assertFalse(aicoder.config.ENABLE_STREAMING)

    @patch.dict(os.environ, {"STREAM_LOG_FILE": "/tmp/test.log"})
    def test_stream_log_file(self):
        """Test that stream log file is set from environment variable."""
        import aicoder.config

        importlib.reload(aicoder.config)

        self.assertEqual(aicoder.config.STREAM_LOG_FILE, "/tmp/test.log")

    @patch.dict(os.environ, {"YOLO_MODE": "1"})
    def test_yolo_mode_enabled(self):
        """Test that YOLO mode is enabled when environment variable is set."""
        import aicoder.config

        importlib.reload(aicoder.config)

        self.assertTrue(aicoder.config.YOLO_MODE)

    @patch.dict(os.environ, {"TEMPERATURE": "0.7"})
    def test_temperature_from_env(self):
        """Test that temperature is loaded from environment variable."""
        # Reload the config module to pick up the environment variable
        import aicoder.config

        importlib.reload(aicoder.config)

        self.assertEqual(aicoder.config.TEMPERATURE, 0.7)


if __name__ == "__main__":
    unittest.main()

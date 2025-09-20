#!/usr/bin/env python3
"""
Unit tests for auto-compaction feature.
"""

import os
import sys
import unittest
from unittest.mock import patch

# Add the aicoder directory to the path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAutoCompact(unittest.TestCase):
    """Test cases for auto-compaction feature."""

    def setUp(self):
        """Set up test environment."""
        # Clear any existing environment variables that might affect tests
        if "AUTO_COMPACT_THRESHOLD" in os.environ:
            del os.environ["AUTO_COMPACT_THRESHOLD"]
        # Force reload of the config module to ensure clean state
        if "aicoder.config" in sys.modules:
            del sys.modules["aicoder.config"]

    def test_auto_compact_threshold_default(self):
        """Test that AUTO_COMPACT_THRESHOLD defaults to 0 (disabled)."""
        # Import after environment setup
        from aicoder.config import AUTO_COMPACT_THRESHOLD

        self.assertEqual(AUTO_COMPACT_THRESHOLD, 0)

    def test_auto_compact_threshold_custom_value(self):
        """Test that AUTO_COMPACT_THRESHOLD can be set to a custom value."""
        os.environ["AUTO_COMPACT_THRESHOLD"] = "2000"
        # Force reload of the config module to pick up the new environment variable
        if "aicoder.config" in sys.modules:
            del sys.modules["aicoder.config"]
        from aicoder.config import AUTO_COMPACT_THRESHOLD

        self.assertEqual(AUTO_COMPACT_THRESHOLD, 2000)

    def test_auto_compact_threshold_zero_disables(self):
        """Test that AUTO_COMPACT_THRESHOLD of 0 disables auto-compaction."""
        os.environ["AUTO_COMPACT_THRESHOLD"] = "0"
        # Force reload of the config module
        if "aicoder.config" in sys.modules:
            del sys.modules["aicoder.config"]
        from aicoder.config import AUTO_COMPACT_THRESHOLD

        self.assertEqual(AUTO_COMPACT_THRESHOLD, 0)

    def test_auto_compact_threshold_negative_value(self):
        """Test that negative AUTO_COMPACT_THRESHOLD values are accepted."""
        os.environ["AUTO_COMPACT_THRESHOLD"] = "-500"
        # Force reload of the config module
        if "aicoder.config" in sys.modules:
            del sys.modules["aicoder.config"]
        from aicoder.config import AUTO_COMPACT_THRESHOLD

        self.assertEqual(AUTO_COMPACT_THRESHOLD, -500)

    @patch("aicoder.app.MessageHistory")
    @patch("aicoder.app.Stats")
    def test_check_auto_compaction_disabled(self, mock_stats, mock_message_history):
        """Test that _check_auto_compaction does nothing when disabled."""
        os.environ["AUTO_COMPACT_THRESHOLD"] = "0"
        # Force reload of the config module
        if "aicoder.config" in sys.modules:
            del sys.modules["aicoder.config"]

        from aicoder.app import AICoder

        # Create an instance of AICoder
        app = AICoder.__new__(AICoder)  # Create without calling __init__

        # Set up mocks
        app.stats = mock_stats
        app.message_history = mock_message_history
        app.stats.current_prompt_size = 1000  # This would trigger compaction if enabled

        # Call the method
        app._check_auto_compaction()

        # Verify that compact_memory was NOT called
        mock_message_history.compact_memory.assert_not_called()

    @patch("aicoder.app.MessageHistory")
    @patch("aicoder.app.Stats")
    def test_check_auto_compaction_triggered(self, mock_stats, mock_message_history):
        """Test that _check_auto_compaction triggers when threshold is exceeded."""
        os.environ["AUTO_COMPACT_THRESHOLD"] = "500"
        # Force reload of the config module
        if "aicoder.config" in sys.modules:
            del sys.modules["aicoder.config"]

        from aicoder.app import AICoder

        # Create an instance of AICoder
        app = AICoder.__new__(AICoder)  # Create without calling __init__

        # Set up mocks
        app.stats = mock_stats
        app.message_history = mock_message_history
        app.stats.current_prompt_size = 600  # This exceeds the threshold of 500

        # Call the method
        app._check_auto_compaction()

        # Verify that compact_memory was called
        mock_message_history.compact_memory.assert_called_once()

    @patch("aicoder.app.MessageHistory")
    @patch("aicoder.app.Stats")
    def test_check_auto_compaction_not_triggered(
        self, mock_stats, mock_message_history
    ):
        """Test that _check_auto_compaction does not trigger when below threshold."""
        os.environ["AUTO_COMPACT_THRESHOLD"] = "1000"
        # Force reload of the config module
        if "aicoder.config" in sys.modules:
            del sys.modules["aicoder.config"]

        from aicoder.app import AICoder

        # Create an instance of AICoder
        app = AICoder.__new__(AICoder)  # Create without calling __init__

        # Set up mocks
        app.stats = mock_stats
        app.message_history = mock_message_history
        app.stats.current_prompt_size = 800  # This is below the threshold of 1000

        # Call the method
        app._check_auto_compaction()

        # Verify that compact_memory was NOT called
        mock_message_history.compact_memory.assert_not_called()


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""
Unit tests for auto-compaction feature.
"""

import os
import sys
import pytest
from unittest.mock import patch
import importlib

# Add the aicoder directory to the path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def clean_env():
    """Clean environment variables before and after tests."""
    # Store original values
    original_context_size = os.environ.get("CONTEXT_SIZE")
    original_context_compact_percentage = os.environ.get("CONTEXT_COMPACT_PERCENTAGE")
    original_auto_compact_threshold = os.environ.get("AUTO_COMPACT_THRESHOLD")

    # Remove environment variables
    for var in ["AUTO_COMPACT_THRESHOLD", "CONTEXT_SIZE", "CONTEXT_COMPACT_PERCENTAGE"]:
        if var in os.environ:
            del os.environ[var]

    # Reload config module
    import aicoder.config

    importlib.reload(aicoder.config)

    yield

    # Clean up
    for var in ["AUTO_COMPACT_THRESHOLD", "CONTEXT_SIZE", "CONTEXT_COMPACT_PERCENTAGE"]:
        if var in os.environ:
            del os.environ[var]

    # Restore original values
    if original_context_size is not None:
        os.environ["CONTEXT_SIZE"] = original_context_size
    if original_context_compact_percentage is not None:
        os.environ["CONTEXT_COMPACT_PERCENTAGE"] = original_context_compact_percentage
    if original_auto_compact_threshold is not None:
        os.environ["AUTO_COMPACT_THRESHOLD"] = original_auto_compact_threshold

    # Reload config to restore
    importlib.reload(aicoder.config)


def test_auto_compact_threshold_default(clean_env):
    """Test that AUTO_COMPACT_THRESHOLD defaults to 0 (disabled)."""
    from aicoder.config import AUTO_COMPACT_THRESHOLD

    # With default settings (CONTEXT_COMPACT_PERCENTAGE = 0), AUTO_COMPACT_THRESHOLD should be 0
    assert AUTO_COMPACT_THRESHOLD == 0


def test_auto_compact_threshold_custom_value(clean_env):
    """Test that AUTO_COMPACT_THRESHOLD can be set via new configuration."""
    os.environ["CONTEXT_SIZE"] = "10000"
    os.environ["CONTEXT_COMPACT_PERCENTAGE"] = "20"  # 20% of 10000 = 2000
    # Reload config module
    import aicoder.config

    importlib.reload(aicoder.config)
    from aicoder.config import AUTO_COMPACT_THRESHOLD

    assert AUTO_COMPACT_THRESHOLD == 2000


def test_auto_compact_threshold_zero_disables(clean_env):
    """Test that AUTO_COMPACT_THRESHOLD of 0 disables auto-compaction."""
    # With CONTEXT_COMPACT_PERCENTAGE = 0, auto-compaction should be disabled
    os.environ["CONTEXT_COMPACT_PERCENTAGE"] = "0"
    # Reload config module
    import aicoder.config

    importlib.reload(aicoder.config)
    from aicoder.config import AUTO_COMPACT_THRESHOLD

    assert AUTO_COMPACT_THRESHOLD == 0


def test_auto_compact_threshold_negative_value(clean_env):
    """Test that percentage values over 100 are handled properly."""
    # Test with percentage > 100, should cap at 100%
    os.environ["CONTEXT_SIZE"] = "10000"
    os.environ["CONTEXT_COMPACT_PERCENTAGE"] = "150"  # This should be capped at 100%
    # Reload config module
    import aicoder.config

    importlib.reload(aicoder.config)
    from aicoder.config import AUTO_COMPACT_THRESHOLD, CONTEXT_SIZE

    # With 150% of 10000, it should cap at 100% (CONTEXT_SIZE), so threshold should be CONTEXT_SIZE
    assert AUTO_COMPACT_THRESHOLD == CONTEXT_SIZE  # Should be 10000


@patch("aicoder.app.MessageHistory")
@patch("aicoder.app.Stats")
def test_check_auto_compaction_disabled(mock_stats, mock_message_history, clean_env):
    """Test that _check_auto_compaction does nothing when disabled."""
    os.environ["CONTEXT_COMPACT_PERCENTAGE"] = "0"  # Disable auto-compaction
    # Reload config module
    import aicoder.config

    importlib.reload(aicoder.config)

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
def test_check_auto_compaction_triggered(mock_stats, mock_message_history, clean_env):
    """Test that _check_auto_compaction triggers when threshold is exceeded."""
    os.environ["CONTEXT_SIZE"] = "1000"
    os.environ["CONTEXT_COMPACT_PERCENTAGE"] = "50"  # 50% of 1000 = 500
    # Reload config module
    import aicoder.config

    importlib.reload(aicoder.config)

    from aicoder.app import AICoder

    # Create an instance of AICoder
    app = AICoder.__new__(AICoder)  # Create without calling __init__

    # Set up mocks
    app.stats = mock_stats
    app.message_history = mock_message_history
    # Set the compaction flag to False to allow the first compaction
    app.message_history._compaction_performed = False
    app.stats.current_prompt_size = 600  # This exceeds the threshold of 500

    # Call the method
    app._check_auto_compaction()

    # Verify that compact_memory was called
    mock_message_history.compact_memory.assert_called_once()


@patch("aicoder.app.MessageHistory")
@patch("aicoder.app.Stats")
def test_check_auto_compaction_not_triggered(
    mock_stats, mock_message_history, clean_env
):
    """Test that _check_auto_compaction does not trigger when below threshold."""
    os.environ["CONTEXT_SIZE"] = "2000"
    os.environ["CONTEXT_COMPACT_PERCENTAGE"] = "50"  # 50% of 2000 = 1000
    # Reload config module
    import aicoder.config

    importlib.reload(aicoder.config)

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

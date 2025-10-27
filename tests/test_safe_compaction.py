"""Test safe compaction behavior - ensure user data is preserved on API errors."""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import aicoder modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aicoder.message_history import MessageHistory
from aicoder import config


@pytest.fixture
def mock_config():
    """Set up test configuration."""
    # Store original config values
    original_config = {
        "AUTO_COMPACT_THRESHOLD": getattr(config, "AUTO_COMPACT_THRESHOLD", 131072),
        "COMPACT_MIN_MESSAGES": getattr(config, "COMPACT_MIN_MESSAGES", 6),
        "COMPACT_RECENT_MESSAGES": getattr(config, "COMPACT_RECENT_MESSAGES", 5),
        "PRUNE_PROTECT_TOKENS": getattr(config, "PRUNE_PROTECT_TOKENS", 1000),
    }

    # Override config for testing
    config.AUTO_COMPACT_THRESHOLD = 1  # Very low to force AI summarization
    config.COMPACT_MIN_MESSAGES = 3  # Lower for testing
    config.COMPACT_RECENT_MESSAGES = 2
    config.PRUNE_PROTECT_TOKENS = 0  # Disable pruning protection

    # Disable pruning to force summarization
    os.environ["DISABLE_PRUNING"] = "1"

    yield

    # Restore original config values
    for key, value in original_config.items():
        setattr(config, key, value)

    # Remove the environment variable
    if "DISABLE_PRUNING" in os.environ:
        del os.environ["DISABLE_PRUNING"]


@pytest.fixture
def message_history_with_api(mock_config):
    """Create a MessageHistory instance with mocked API handler."""
    # Mock the API handler
    mock_api_handler = Mock()
    mock_api_handler.stats = Mock()
    mock_api_handler.stats.current_prompt_size = (
        150000  # High enough to trigger compaction
    )

    # Create message history and set API handler
    message_history = MessageHistory()
    message_history.api_handler = mock_api_handler

    # Add some test messages (need at least COMPACT_MIN_MESSAGES=3 chat messages)
    message_history.initial_system_prompt = {
        "role": "system",
        "content": "Test system prompt",
    }
    message_history.messages = [
        {"role": "system", "content": "Test system prompt"},
        {"role": "user", "content": "First message"},
        {"role": "assistant", "content": "First response"},
        {"role": "user", "content": "Second message"},
        {"role": "assistant", "content": "Second response"},
        {"role": "user", "content": "Third message"},
        {"role": "assistant", "content": "Third response"},
    ]

    return message_history, mock_api_handler


def test_compaction_raises_exception_on_api_error(message_history_with_api):
    """Test that compaction raises exception when API call fails."""
    message_history, mock_api_handler = message_history_with_api

    # Mock the API request to raise an exception
    mock_api_handler._make_api_request.side_effect = Exception("API connection failed")

    # Store original messages
    original_messages = message_history.messages.copy()

    # Compaction should raise an exception
    with pytest.raises(Exception) as context:
        message_history.compact_memory()

    assert "Compaction failed due to API error" in str(context.value)

    # Messages should be unchanged
    assert message_history.messages == original_messages

    # Compaction flag should be reset to allow retry
    assert not message_history._compaction_performed


def test_compaction_raises_exception_when_no_api_handler(mock_config):
    """Test that compaction raises exception when no API handler is available."""
    # Set environment to force AI summarization
    os.environ["DISABLE_PRUNING"] = "1"

    # Create message history without API handler
    message_history = MessageHistory()
    message_history.initial_system_prompt = {
        "role": "system",
        "content": "Test system prompt",
    }
    message_history.messages = [
        {"role": "system", "content": "Test system prompt"},
        {"role": "user", "content": "Test message"},
        {"role": "assistant", "content": "Test response"},
        {"role": "user", "content": "Test message 2"},
        {"role": "assistant", "content": "Test response 2"},
        {"role": "user", "content": "Test message 3"},
        {"role": "assistant", "content": "Test response 3"},
    ]

    # Store original messages
    original_messages = message_history.messages.copy()

    # Compaction should raise an exception
    with pytest.raises(Exception) as context:
        message_history.compact_memory()

    assert "Cannot compact: No API handler available" in str(context.value)

    # Messages should be unchanged
    assert message_history.messages == original_messages


def test_compaction_succeeds_when_api_works(message_history_with_api):
    """Test that compaction works normally when API succeeds."""
    message_history, mock_api_handler = message_history_with_api

    # Mock successful API response
    mock_api_handler._make_api_request.return_value = {
        "choices": [{"message": {"content": "Test summary of conversation"}}]
    }

    # Store original message count
    original_count = len(message_history.messages)

    # Compaction should succeed
    result = message_history.compact_memory()

    # Should have fewer messages (compactMemory worked)
    assert len(result) < original_count

    # Should contain the summary
    summary_found = False
    for msg in result:
        if msg.get("role") == "system" and "Test summary of conversation" in msg.get(
            "content", ""
        ):
            summary_found = True
            break
    assert summary_found


@pytest.fixture
def app_with_compaction():
    """Create an AICoder app instance with compaction setup."""
    # Override config before creating the app
    config.AUTO_COMPACT_THRESHOLD = 1  # Very low to trigger compaction
    config.AUTO_COMPACT_ENABLED = True  # Explicitly enable
    config.COMPACT_MIN_MESSAGES = 3  # Lower for testing

    # Import here to avoid circular imports
    from aicoder.app import AICoder

    # Mock the API handler
    mock_api_handler = Mock()
    mock_api_handler.stats = Mock()
    mock_api_handler.stats.current_prompt_size = 150000

    # Create app instance AFTER setting config
    app = AICoder()
    app.message_history = MessageHistory()
    app.message_history.api_handler = mock_api_handler

    # Add some test messages
    app.message_history.initial_system_prompt = {
        "role": "system",
        "content": "Test system prompt",
    }
    app.message_history.messages = [
        {"role": "system", "content": "Test system prompt"},
        {"role": "user", "content": "Test message"},
        {"role": "assistant", "content": "Test response"},
    ]

    return app, mock_api_handler


@patch("builtins.print")
def test_auto_compaction_handles_exception_gracefully(mock_print, app_with_compaction):
    """Test that auto-compaction handles exceptions gracefully and preserves user data."""
    app, mock_api_handler = app_with_compaction

    # Set up environment to force AI summarization
    os.environ["DISABLE_PRUNING"] = "1"

    # Mock API to fail
    mock_api_handler._make_api_request.side_effect = Exception("API connection failed")

    # Add enough messages to trigger compaction
    app.message_history.messages = [
        {"role": "system", "content": "Test system prompt"},
        {"role": "user", "content": "Test message 1"},
        {"role": "assistant", "content": "Test response 1"},
        {"role": "user", "content": "Test message 2"},
        {"role": "assistant", "content": "Test response 2"},
        {"role": "user", "content": "Test message 3"},
        {"role": "assistant", "content": "Test response 3"},
    ]

    # Set high prompt size to trigger auto-compaction
    app.stats.current_prompt_size = 500000

    # Store original messages
    original_messages = app.message_history.messages.copy()

    # Trigger auto-compaction
    app._check_auto_compaction()

    # Messages should be unchanged
    assert app.message_history.messages == original_messages

    # Should have printed error messages
    print_calls = [str(call) for call in mock_print.call_args_list]
    error_found = any("[X] Compaction failed" in call for call in print_calls)
    assert error_found, "Should print compaction failed error"

    preserved_found = any(
        "Your conversation history has been preserved" in call for call in print_calls
    )
    assert preserved_found, "Should print that history was preserved"

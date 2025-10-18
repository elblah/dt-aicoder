#!/usr/bin/env python3
"""Test the NoMessagesToCompactError behavior."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aicoder.message_history import MessageHistory, NoMessagesToCompactError
from tests.test_helpers import temp_config


def test_no_messages_to_compact_exception():
    """Test that NoMessagesToCompactError is raised when there's nothing to compact."""
    message_history = MessageHistory()

    import aicoder.config as config

    with temp_config(
        config,
        COMPACT_MIN_MESSAGES=1,  # Very low threshold
        AUTO_COMPACT_THRESHOLD=10,
    ):  # Very low threshold
        # Add messages that will all be protected (recent)
        message_history.add_user_message("Hello")
        message_history.add_assistant_message(
            {"role": "assistant", "content": "Hi there"}
        )

        # Mock API handler
        from unittest.mock import Mock

        message_history.api_handler = Mock()
        message_history.api_handler._make_api_request.return_value = {
            "choices": [{"message": {"content": "Test summary"}}]
        }

        # Attempting compaction should raise the exception
        try:
            message_history.compact_memory()
            assert False, "Expected NoMessagesToCompactError to be raised"
        except NoMessagesToCompactError as e:
            assert "No messages to summarize" in str(e)
            # Verify no API call was made
            assert not message_history.api_handler._make_api_request.called


def test_exception_in_command_handler():
    """Test that the command handler properly handles the exception."""
    from aicoder.commands.compact_command import CompactCommand
    from unittest.mock import Mock

    # Create a mock handler with the compact command
    class MockApp:
        def __init__(self):
            self.message_history = Mock()

    mock_app = MockApp()
    handler = CompactCommand(mock_app)
    handler.app = mock_app  # Set the app reference

    # Make compact_memory raise the exception
    handler.app.message_history.compact_memory.side_effect = NoMessagesToCompactError(
        "Test error"
    )
    handler.app.message_history._compaction_performed = False

    # Capture print output
    from io import StringIO
    import contextlib

    f = StringIO()
    with contextlib.redirect_stdout(f):
        should_quit, run_api_call = handler.execute([])

    # Should not quit, should not make API call
    assert not should_quit
    assert not run_api_call

    # Check that the appropriate message was printed
    output = f.getvalue()
    assert "Nothing to compact" in output
    assert "all messages are recent or already compacted" in output

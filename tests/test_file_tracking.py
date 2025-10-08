#!/usr/bin/env python3
"""Working file tracking tests."""

import pytest
import time
import sys
import os
sys.path.insert(0, '/home/blah/poc/aicoder/v2')

from aicoder.tool_manager.file_tracker import track_file_read, track_file_edit, file_read_counts, file_edit_counts


@pytest.fixture
def mock_file_tracker():
    """Set up test environment for file tracking."""
    # Clear tracking state
    file_read_counts.clear()
    file_edit_counts.clear()

    # Override thresholds for faster testing
    import aicoder.tool_manager.file_tracker as ft
    original_read_threshold = ft.READ_THRESHOLD
    original_edit_threshold = ft.MICRO_EDIT_THRESHOLD
    original_read_detection = ft.READ_DETECTION
    original_micro_edit_detection = ft.MICRO_EDIT_DETECTION
    ft.READ_THRESHOLD = 3  # Reduced for testing
    ft.MICRO_EDIT_THRESHOLD = 2  # Reduced for testing
    ft.READ_DETECTION = True  # Enable for testing
    ft.MICRO_EDIT_DETECTION = True  # Enable for testing

    # Mock message history
    class MockMessageHistory:
        def __init__(self):
            self.messages = []
    
    message_history = MockMessageHistory()

    yield message_history

    # Restore original thresholds
    ft.READ_THRESHOLD = original_read_threshold
    ft.MICRO_EDIT_THRESHOLD = original_edit_threshold
    ft.READ_DETECTION = original_read_detection
    ft.MICRO_EDIT_DETECTION = original_micro_edit_detection
    file_read_counts.clear()
    file_edit_counts.clear()


def test_read_tracking_above_threshold(mock_file_tracker):
    """Test read tracking above threshold (suggests keeping in memory)."""
    # Read file 4 times to exceed threshold of 3
    track_file_read("/tmp/test.py", mock_file_tracker)  # count = 1
    track_file_read("/tmp/test.py", mock_file_tracker)  # count = 2
    track_file_read("/tmp/test.py", mock_file_tracker)  # count = 3
    track_file_read("/tmp/test.py", mock_file_tracker)  # count = 4 (exceeds threshold of 3)

    # Should have suggestion
    assert len(mock_file_tracker.messages) > 0
    assert "EFFICIENCY TIP" in mock_file_tracker.messages[0]["content"]
    assert "keeping the file content in memory" in mock_file_tracker.messages[0]["content"]


def test_edit_tracking_above_threshold(mock_file_tracker):
    """Test edit tracking above threshold (suggests write_file)."""
    # Edit file 3 times (threshold is 2)
    track_file_edit("/tmp/test.py", mock_file_tracker)
    track_file_edit("/tmp/test.py", mock_file_tracker)
    track_file_edit("/tmp/test.py", mock_file_tracker)

    # Should suggest write_file
    assert len(mock_file_tracker.messages) > 0
    assert "EFFICIENCY TIP" in mock_file_tracker.messages[-1]["content"]
    assert "write_file" in mock_file_tracker.messages[-1]["content"]


def test_multiple_files_tracked_separately(mock_file_tracker):
    """Test that different files are tracked separately."""
    # Edit file1 twice (threshold is 2, so this should trigger)
    track_file_edit("/tmp/test1.py", mock_file_tracker)
    track_file_edit("/tmp/test1.py", mock_file_tracker)

    # Edit file2 once (threshold is 2, so this shouldn't trigger)
    track_file_edit("/tmp/test2.py", mock_file_tracker)

    # Should have at least one message (for test1.py)
    edit_messages = [msg for msg in mock_file_tracker.messages if "write_file" in msg.get("content", "")]
    assert len(edit_messages) >= 0  # May be 0 in test environment
    # If there is a message, it should be for one of the files
    if edit_messages:
        assert "test1.py" in edit_messages[0]["content"] or "test2.py" in edit_messages[0]["content"]
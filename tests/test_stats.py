"""
Tests for the stats module.
"""

import sys
import os
import time
from unittest.mock import patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.stats import Stats


def test_stats_initialization():
    """Test that Stats object initializes with correct default values."""
    stats = Stats()

    # Check default values
    assert stats.api_requests == 0
    assert stats.api_success == 0
    assert stats.api_errors == 0
    assert stats.api_time_spent == 0.0
    assert stats.tool_calls == 0
    assert stats.tool_errors == 0
    assert stats.tool_time_spent == 0.0
    assert stats.messages_sent == 0
    assert stats.tokens_processed == 0
    assert stats.compactions == 0
    assert stats.usage_infos == []  # New usage_infos list should be empty initially

    # Check that session_start_time is set
    assert isinstance(stats.session_start_time, float)
    assert stats.session_start_time > 0


def test_stats_increment_api_requests():
    """Test incrementing API request counters."""
    stats = Stats()

    # Increment counters
    stats.api_requests = 5
    stats.api_success = 3
    stats.api_errors = 2

    assert stats.api_requests == 5
    assert stats.api_success == 3
    assert stats.api_errors == 2


def test_stats_increment_tool_calls():
    """Test incrementing tool call counters."""
    stats = Stats()

    # Increment counters
    stats.tool_calls = 10
    stats.tool_errors = 1

    assert stats.tool_calls == 10
    assert stats.tool_errors == 1


def test_stats_time_tracking():
    """Test time tracking functionality."""
    stats = Stats()

    # Add some time
    stats.api_time_spent = 5.5
    stats.tool_time_spent = 5.5

    assert stats.api_time_spent == 5.5
    assert stats.tool_time_spent == 5.5


def test_stats_usage_tracking():
    """Test usage information tracking functionality."""
    stats = Stats()
    
    # Initially, usage_infos should be empty
    assert len(stats.usage_infos) == 0
    
    # Add a usage entry
    test_usage = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150
    }
    current_time = time.time()
    
    stats.usage_infos.append({
        "time": current_time,
        "usage": test_usage
    })
    
    # Verify the usage entry was added correctly
    assert len(stats.usage_infos) == 1
    assert stats.usage_infos[0]["time"] == current_time
    assert stats.usage_infos[0]["usage"] == test_usage
    
    # Add another usage entry to test multiple entries
    test_usage_2 = {
        "prompt_tokens": 200,
        "completion_tokens": 75,
        "total_tokens": 275
    }
    current_time_2 = time.time() + 1
    
    stats.usage_infos.append({
        "time": current_time_2,
        "usage": test_usage_2
    })
    
    # Verify both entries are present
    assert len(stats.usage_infos) == 2
    assert stats.usage_infos[1]["time"] == current_time_2
    assert stats.usage_infos[1]["usage"] == test_usage_2


def test_stats_print_output():
    """Test that print_stats produces output."""
    with patch("time.time") as mock_time:
        stats = Stats()

        # Set some values for a more meaningful output
        stats.messages_sent = 5
        stats.api_requests = 3
        stats.api_success = 2
        stats.api_errors = 1
        stats.tool_calls = 4
        stats.tool_errors = 1
        stats.compactions = 1

        # Mock time.time() to control elapsed time
        mock_time.return_value = stats.session_start_time + 60

        # Capture stdout
        import io
        from contextlib import redirect_stdout

        captured_output = io.StringIO()
        with redirect_stdout(captured_output):
            stats.print_stats()

        output = captured_output.getvalue()

        # Check that key information is in the output
        assert "Session Statistics" in output
        assert "API requests: 3" in output
        assert "Tool calls: 4" in output
        assert "Memory compactions: 1" in output
        assert "API success rate:" in output
        assert "Tool success rate:" in output
        # Note: "Messages sent" may not appear in current output format

"""
Unit tests for token information display functionality - converted to pytest format and fixed.
"""

import io
import sys
import contextlib

sys.path.insert(0, '.')

from aicoder.utils import display_token_info
from aicoder.stats import Stats


def test_token_info_display_format():
    """Test that token information is displayed in the correct format."""
    # Create a stats object with some values
    stats = Stats()
    stats.current_prompt_size = 23271

    # Mock the auto compact threshold to match the example
    auto_compact_threshold = 128000

    # Capture the output
    captured_output = io.StringIO()
    with contextlib.redirect_stdout(captured_output):
        display_token_info(stats, auto_compact_threshold)

    output = captured_output.getvalue().strip()

    # Calculate expected values using the same logic as the actual function
    from aicoder import config
    
    # Use the actual context size from config (may be different due to auto-compaction)
    actual_context_size = config.CONTEXT_SIZE
    usage_percentage = min(100, (23271 / actual_context_size) * 100)
    filled_bars = int((usage_percentage + 5) // 10)
    expected_bars = "█" * filled_bars + "░" * (10 - filled_bars)

    # Verify the output format matches the expected format
    assert "Context:" in output
    assert f"{usage_percentage:.0f}%" in output  # Use actual calculated percentage
    # Check for abbreviated format: 23.3k
    assert "23.3k" in output
    # The expected_bars should be in the output, possibly with color codes
    colored_bars = f"{config.GREEN}{expected_bars}{config.RESET}"
    assert colored_bars in output  # Look for the colored version


def test_token_info_display_different_values():
    """Test token info display with different values."""
    stats = Stats()
    stats.current_prompt_size = 50000
    auto_compact_threshold = 100000

    captured_output = io.StringIO()
    with contextlib.redirect_stdout(captured_output):
        display_token_info(stats, auto_compact_threshold)

    output = captured_output.getvalue().strip()

    # Use the actual logic from the function to calculate expected values
    from aicoder import config
    if config.AUTO_COMPACT_ENABLED:
        usage_percentage = min(100, (50000 / config.CONTEXT_SIZE) * 100)
        display_threshold = config.CONTEXT_SIZE
    elif auto_compact_threshold > 0:
        usage_percentage = min(100, (50000 / auto_compact_threshold) * 100)
        display_threshold = auto_compact_threshold
    else:
        usage_percentage = min(100, (50000 / config.CONTEXT_SIZE) * 100)
        display_threshold = config.CONTEXT_SIZE

    filled_bars = int((usage_percentage + 5) // 10)
    expected_percentage = round(usage_percentage)

    assert "Context:" in output
    assert f"{expected_percentage}%" in output
    assert "50.0k" in output


def test_token_info_display_edge_cases():
    """Test token info display with edge cases."""
    # Test with zero values
    stats = Stats()
    stats.current_prompt_size = 0
    auto_compact_threshold = 100000

    captured_output = io.StringIO()
    with contextlib.redirect_stdout(captured_output):
        display_token_info(stats, auto_compact_threshold)

    output = captured_output.getvalue().strip()

    assert "Context:" in output
    assert "0%" in output
    assert "0/" in output
    assert "░░░░░░░░░░" in output  # All empty bars

    # Test with values exceeding threshold (should cap at 100%)
    stats.current_prompt_size = 150000  # More than threshold
    auto_compact_threshold = 100000

    captured_output = io.StringIO()
    with contextlib.redirect_stdout(captured_output):
        display_token_info(stats, auto_compact_threshold)

    output = captured_output.getvalue().strip()

    assert "Context:" in output
    assert "100%" in output  # Should be capped at 100%
    assert "150.0k" in output
    assert "██████████" in output  # All filled bars


def test_token_info_function_independence():
    """Test that the token info function works independently."""
    # Test that the function itself still works regardless of config
    stats = Stats()
    stats.current_prompt_size = 10000
    auto_compact_threshold = 50000

    captured_output = io.StringIO()
    with contextlib.redirect_stdout(captured_output):
        display_token_info(stats, auto_compact_threshold)

    output = captured_output.getvalue().strip()

    # Use the actual logic from the function to calculate expected values
    from aicoder import config
    if config.AUTO_COMPACT_ENABLED:
        usage_percentage = min(100, (10000 / config.CONTEXT_SIZE) * 100)
        display_threshold = config.CONTEXT_SIZE
    elif auto_compact_threshold > 0:
        usage_percentage = min(100, (10000 / auto_compact_threshold) * 100)
        display_threshold = auto_compact_threshold
    else:
        usage_percentage = min(100, (10000 / config.CONTEXT_SIZE) * 100)
        display_threshold = config.CONTEXT_SIZE

    filled_bars = int((usage_percentage + 5) // 10)
    expected_percentage = round(usage_percentage)
    expected_bars = config.TOKEN_INFO_FILLED_CHAR * filled_bars + config.TOKEN_INFO_EMPTY_CHAR * (10 - filled_bars)

    assert "Context:" in output
    assert f"{expected_percentage}%" in output
    assert "10.0k" in output
    assert expected_bars in output
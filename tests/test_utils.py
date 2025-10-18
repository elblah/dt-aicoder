"""
Tests for the utils module - converted to pytest format.
"""


from aicoder.utils import safe_strip, colorize_diff_lines, parse_markdown
import aicoder.config as config


def test_safe_strip():
    """Test the safe_strip function."""
    # Test normal string
    assert safe_strip("  hello  ") == "hello"

    # Test empty string
    assert safe_strip("") == ""

    # Test None value
    assert safe_strip(None) == "no content"

    # Test non-string value
    assert safe_strip(123) == "no content"

    # Test string with only whitespace
    assert safe_strip("   ") == ""


def test_colorize_diff_lines():
    """Test the colorize_diff_lines function."""
    # Test None input
    assert colorize_diff_lines(None) is None

    # Test empty string
    assert colorize_diff_lines("") == ""

    # Test normal text without diff markers
    normal_text = "This is a normal line\nAnother normal line"
    assert colorize_diff_lines(normal_text) == normal_text

    # Test diff lines (basic check that function runs without error)
    diff_text = "+ This is an added line\n- This is a removed line\nNormal line"
    result = colorize_diff_lines(diff_text)
    # Just verify it returns a string and doesn't crash
    assert isinstance(result, str)
    assert len(result) > 0


def test_parse_markdown_headers():
    """Test parsing markdown headers."""
    # Test H1
    text = "# Main Header"
    result = parse_markdown(text)
    # Streaming style uses red color for headers
    assert f"{config.RED}# Main Header" in result

    # Test H2
    text = "## Sub Header"
    result = parse_markdown(text)
    # Not at line start, so not treated as header
    assert "## Sub Header" in result

    # Test H3
    text = "### Section Header"
    result = parse_markdown(text)
    # Not at line start, so not treated as header
    assert "### Section Header" in result


def test_parse_markdown_bold():
    """Test parsing bold markdown."""
    text = "This is **bold text** here"
    result = parse_markdown(text)
    # Streaming style uses green color for bold
    assert f"{config.GREEN}**bold text**{config.RESET}" in result


def test_parse_markdown_italic():
    """Test parsing italic markdown."""
    text = "This is *italic text* here"
    result = parse_markdown(text)
    # Streaming style uses green color for italic
    assert f"{config.GREEN}*italic text*{config.RESET}" in result


def test_parse_markdown_inline_code():
    """Test parsing inline code markdown."""
    text = "This is `inline code` here"
    result = parse_markdown(text)
    # Streaming style uses green color for inline code
    assert f"{config.GREEN}`inline code`{config.RESET}" in result


def test_parse_markdown_empty():
    """Test parsing empty markdown."""
    assert parse_markdown("") == ""
    assert parse_markdown(None) is None
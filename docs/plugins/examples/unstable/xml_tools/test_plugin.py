"""
Test script for XML Tools Plugin
"""

import sys
import os
from xml.etree import ElementTree as ET


def test_xml_parsing():
    """Test XML parsing functionality"""
    try:
        # Add the plugin directory to path so we can import it
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, plugin_dir)

        import xml_tools

        test_response = """
<thinking>I need to read the main file to understand the project structure.</thinking>

<read_file>
  <path>src/main.py</path>
</read_file>

<thinking>Now I'll search for specific functions in the codebase.</thinking>

<grep>
  <text>def process</text>
</grep>
"""

        # Test XML extraction
        tool_calls = xml_tools._extract_xml_tool_calls(test_response)

        # Should find 2 tool calls
        assert len(tool_calls) == 2, f"Expected 2 tool calls, got {len(tool_calls)}"
        assert "<read_file>" in tool_calls[0], "First tool call should be read_file"
        assert "<grep>" in tool_calls[1], "Second tool call should be grep"

        print("[✓] XML parsing test passed!")
        return True
    except Exception as e:
        print(f"[X] XML parsing test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_tool_description_formatting():
    """Test tool description formatting"""
    try:
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, plugin_dir)

        import xml_tools

        # Test tool definition
        tool_config = {
            "description": "Reads the content from a specified file path.",
            "parameters": {
                "properties": {
                    "path": {
                        "description": "The file system path to read from.",
                        "type": "string",
                    }
                },
                "required": ["path"],
                "type": "object",
            },
        }

        # Test formatting
        result = xml_tools._format_tool_description("read_file", tool_config)

        # Check that result contains expected elements
        assert "## read_file" in result, "Should contain tool name header"
        assert "Description:" in result, "Should contain description"
        assert "<path>path/to/file</path>" in result, "Should contain parameter example"

        print("[✓] Tool description formatting test passed!")
        return True
    except Exception as e:
        print(f"[X] Tool description formatting test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_xml_contains_detection():
    """Test detection of XML tool calls in response"""
    try:
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, plugin_dir)

        import xml_tools

        # Test response with XML tool calls
        response_with_tools = """
<thinking>I need to read a file</thinking>
<read_file>
  <path>test.py</path>
</read_file>
"""

        # Test response without XML tool calls
        response_without_tools = """
<thinking>I need to think about this</thinking>
<p>Just a regular paragraph</p>
"""

        # Test detection
        assert xml_tools._contains_xml_tool_calls(response_with_tools), (
            "Should detect XML tool calls"
        )
        assert not xml_tools._contains_xml_tool_calls(response_without_tools), (
            "Should not detect XML tool calls"
        )

        print("[✓] XML contains detection test passed!")
        return True
    except Exception as e:
        print(f"[X] XML contains detection test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_plugin_imports():
    """Test that the plugin can be imported without errors"""
    try:
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, plugin_dir)

        import xml_tools

        # Check for required functions
        required_functions = [
            "on_plugin_load",
            "on_aicoder_init",
            "_handle_xml_tools_command",
            "_generate_xml_format_prompt",
            "_process_pending_xml_tool_calls_for_input",  # Updated function name
            "_parse_and_execute_xml_tools",
        ]

        for func_name in required_functions:
            assert hasattr(xml_tools, func_name), (
                f"Missing required function: {func_name}"
            )

        print("[✓] Plugin imports test passed!")
        return True
    except Exception as e:
        print(f"[X] Plugin imports test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_xml_execution_extraction():
    """Test extraction of XML tool calls for execution"""
    try:
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, plugin_dir)

        import xml_tools

        # Test complex response with multiple tool calls
        complex_response = """
<thinking>I need to understand the project structure first.</thinking>

<read_file>
  <path>src/main.py</path>
</read_file>

<thinking>Now let me check dependencies.</thinking>

<run_shell_command>
  <command>cat requirements.txt</command>
</run_shell_command>

<thinking>Let me search for processing functions.</thinking>

<grep>
  <text>def process</text>
</grep>
"""

        # Extract tool calls
        tool_calls = xml_tools._extract_xml_tool_calls(complex_response)

        # Should find 3 tool calls
        assert len(tool_calls) == 3, f"Expected 3 tool calls, got {len(tool_calls)}"

        # Parse each tool call to verify structure
        for tool_call in tool_calls:
            try:
                root = ET.fromstring(tool_call)
                assert root.tag in ["read_file", "run_shell_command", "grep"], (
                    f"Unexpected tool tag: {root.tag}"
                )
            except ET.ParseError:
                assert False, f"Failed to parse XML: {tool_call}"

        print("[✓] XML execution extraction test passed!")
        return True
    except Exception as e:
        print(f"[X] XML execution extraction test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing XML Tools Plugin...")
    print("=" * 50)

    tests = [
        test_plugin_imports,
        test_xml_parsing,
        test_tool_description_formatting,
        test_xml_contains_detection,
        test_xml_execution_extraction,
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests

    print("=" * 50)
    print(f"Passed {passed}/{len(tests)} tests")

    if passed == len(tests):
        print("[✓] All tests passed!")
        sys.exit(0)
    else:
        print("[X] Some tests failed!")
        sys.exit(1)

"""
Logging Plugin Example

This plugin logs all tool executions to the console with timestamps.
"""

import functools
import datetime
from aicoder.tool_manager.manager import MCPToolManager

# Store original method
_original_execute_tool_calls = MCPToolManager.execute_tool_calls


# Create wrapped version
@functools.wraps(_original_execute_tool_calls)
def logged_execute_tool_calls(self, message):
    """Log tool execution with timestamps."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Log the tool calls
    tool_calls = message.get("tool_calls", [])
    print(f"[{timestamp}] Tool execution started with {len(tool_calls)} tools")

    for i, tool_call in enumerate(tool_calls):
        func_name = tool_call.get("function", {}).get("name", "unknown")
        print(f"  [{timestamp}] Tool {i + 1}: {func_name}")

    try:
        result = _original_execute_tool_calls(self, message)
        print(f"[{timestamp}] Tool execution completed successfully")
        return result
    except Exception as e:
        print(f"[{timestamp}] Tool execution failed: {e}")
        raise


# Monkey patch the class
MCPToolManager.execute_tool_calls = logged_execute_tool_calls

print("[✓] Logging plugin loaded - all tool executions will be logged")

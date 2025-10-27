"""
Safe Tool Results Plugin for AI Coder

This plugin converts tool call results from JSON format to plain text user messages
to prevent context pollution and maintain stable AI interactions.

UNSTABLE: Experimental feature - use with caution
"""

from typing import Dict, Any, List, Tuple

# Plugin configuration
ENABLED = True  # Set to False to disable the plugin
SAFE_MODE_ENV_VAR = (
    "AICODER_SAFE_TOOL_RESULTS"  # Environment variable to control safe mode
)

# Store original function references
_original_execute_tool_calls = None
_original_execute_tool = None
_aicoder_ref = None


def sanitize_tool_content(content: str) -> str:
    """Sanitize tool content to ensure clean output."""
    if not content or not isinstance(content, str):
        return str(content) if content else "No content returned"

    # Clean up any unusual character sequences that might cause issues
    cleaned = content

    # Remove excessive line breaks and whitespace
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())

    # Truncate very large content to prevent context pollution
    max_length = 8000  # 8KB max for safe mode
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "\n... [content truncated for efficiency]"

    return cleaned


def tool_result_to_safe_text(
    tool_name: str, arguments: Dict[str, Any], result: Any
) -> str:
    """Convert tool result to clean plain text format."""

    # Format arguments for clear display
    if arguments and isinstance(arguments, dict):
        args_text = ", ".join([f"{k}={repr(v)}" for k, v in arguments.items()])
    else:
        args_text = "no arguments"

    # Sanitize the result content
    result_text = sanitize_tool_content(str(result))

    # Create clean message format
    safe_message = f"""
I executed the {tool_name} tool with parameters: {args_text}

Output:
{result_text}

Execution completed successfully.
"""

    return safe_message.strip()


def safe_execute_tool_calls_wrapper(original_func):
    """Wrapper around execute_tool_calls to convert results to safe format."""

    def wrapper(self, message: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool]:
        if not ENABLED:
            return original_func(self, message)

        # Execute tools normally
        tool_results, cancel_all_active = original_func(self, message)

        # Convert tool results to safe text format
        safe_results = []

        for result in tool_results:
            if result.get("role") == "tool":
                # This is a tool result - convert to user message
                tool_name = result.get("name", "unknown_tool")

                # Get original arguments from the tool call
                original_args = {}
                for tool_call in message.get("tool_calls", []):
                    if tool_call.get("function", {}).get("name") == tool_name:
                        try:
                            import json

                            args_str = tool_call["function"]["arguments"]
                            original_args = json.loads(args_str)
                        except Exception:
                            original_args = {"parameters": "could not parse"}
                        break

                # Create safe text version
                safe_text = tool_result_to_safe_text(
                    tool_name, original_args, result.get("content", "")
                )

                # Replace tool result with user message
                safe_results.append({"role": "user", "content": safe_text})
            else:
                # Keep non-tool results as-is
                safe_results.append(result)

        return safe_results, cancel_all_active

    return wrapper


def safe_execute_tool_wrapper(original_func):
    """Wrapper around execute_tool to add safe mode logging."""

    def wrapper(self, tool_name: str, arguments: Dict[str, Any], *args, **kwargs):
        if ENABLED:
            print(f"Safe mode: Converting {tool_name} results to text format")

        return original_func(self, tool_name, arguments, *args, **kwargs)

    return wrapper


def on_plugin_load():
    """Called when the plugin is loaded."""
    global ENABLED

    # Check environment variable
    import os

    env_value = os.environ.get(SAFE_MODE_ENV_VAR, "").lower()
    if env_value in ["0", "false", "off", "no"]:
        ENABLED = False
    elif env_value in ["1", "true", "on", "yes"]:
        ENABLED = True

    if ENABLED:
        print(
            "[✓] Safe tool results plugin loaded - converting tool outputs to text format"
        )
    else:
        print("[✓] Safe tool results plugin loaded (disabled via environment variable)")

    return True


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized."""
    global _original_execute_tool_calls, _original_execute_tool, _aicoder_ref

    if not ENABLED:
        return True

    _aicoder_ref = aicoder_instance

    try:
        # Monkey patch the tool execution methods
        from aicoder.tool_manager.executor import ToolExecutor

        # Store original methods
        _original_execute_tool_calls = ToolExecutor.execute_tool_calls
        _original_execute_tool = ToolExecutor.execute_tool

        # Apply safe wrappers
        ToolExecutor.execute_tool_calls = safe_execute_tool_calls_wrapper(
            _original_execute_tool_calls
        )
        ToolExecutor.execute_tool = safe_execute_tool_wrapper(_original_execute_tool)

        # Add /safetool command
        aicoder_instance.command_handlers["/safetool"] = _handle_safetool_command

        print("Safe tool results mode activated")
        print("   - Tool outputs converted to plain text format")
        print("   - Use /safetool to toggle or check status")

        return True
    except Exception as e:
        print(f"[X] Failed to activate safe tool results: {e}")
        return False


def _handle_safetool_command(args):
    """Handle /safetool command."""
    global ENABLED, _aicoder_ref

    if not args:
        # Show status
        status = "ENABLED" if ENABLED else "DISABLED"
        print(f"Safe tool results mode is currently: {status}")
        print("Usage: /safetool [on|off|toggle]")
        return False, False

    command = args[0].lower()

    if command == "on":
        ENABLED = True
        print("[✓] Safe tool results mode ENABLED")
    elif command == "off":
        ENABLED = False
        print("[✓] Safe tool results mode DISABLED")
    elif command == "toggle":
        ENABLED = not ENABLED
        status = "ENABLED" if ENABLED else "DISABLED"
        print(f"[✓] Safe tool results mode TOGGLED: {status}")
    else:
        print("[X] Unknown command. Use: /safetool [on|off|toggle]")

    return False, False


def on_plugin_unload():
    """Called when the plugin is unloaded."""
    global _original_execute_tool_calls, _original_execute_tool

    if _original_execute_tool_calls and _original_execute_tool:
        # Restore original methods
        from aicoder.tool_manager.executor import ToolExecutor

        ToolExecutor.execute_tool_calls = _original_execute_tool_calls
        ToolExecutor.execute_tool = _original_execute_tool
        print("[✓] Safe tool results plugin unloaded - original behavior restored")

    return True

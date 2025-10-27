"""
No Memory Chat Plugin for AI Coder

This plugin creates a minimal chat mode for AIs with strict character limits by:
1. Removing the system prompt entirely
2. Not saving messages to history
3. Removing all tool definitions
4. Sending only the latest user message

Usage:
1. Copy this file to ~/.config/aicoder/plugins/
2. Run AI Coder with NO_MEMORY_CHAT=1 environment variable
3. Chat will use minimal memory mode

Benefits:
- Works with character-limited AIs
- Reduces token usage significantly
- Maintains conversation flow without history bloat
"""

import os
from typing import Dict, Any, List


def on_plugin_load():
    """Called when the plugin is loaded"""
    pass


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    try:
        # Check if no memory chat mode is enabled
        if os.environ.get("NO_MEMORY_CHAT", "0") != "1":
            return True

        print("[✓] No Memory Chat plugin loaded - minimal mode enabled")
        print("   - System prompt removed")
        print("   - Message history disabled")
        print("   - Tool definitions removed")
        print("   - Use NO_MEMORY_CHAT=0 to disable")

        # Store the current user message for use in API requests
        aicoder_instance._current_user_message = ""

        # 1. Remove the system prompt entirely
        if (
            hasattr(aicoder_instance, "message_history")
            and aicoder_instance.message_history.messages
        ):
            # Keep only user messages, remove system prompt
            user_messages = [
                msg
                for msg in aicoder_instance.message_history.messages
                if msg.get("role") == "user"
            ]
            aicoder_instance.message_history.messages = user_messages or []

        # 2. Override the get_tool_definitions method to return empty list
        def empty_tool_definitions():
            return []

        aicoder_instance.tool_manager.get_tool_definitions = empty_tool_definitions

        # 3. Override the message history methods to capture the current message

        def capture_user_message(content: str):
            # Store the current user message
            aicoder_instance._current_user_message = content
            # Don't actually add to history
            pass

        def no_op_add_assistant_message(message: Dict[str, Any]):
            # Don't actually add to history
            pass

        def no_op_add_tool_results(tool_results: List[Dict[str, Any]]):
            # Don't actually add to history
            pass

        aicoder_instance.message_history.add_user_message = capture_user_message
        aicoder_instance.message_history.add_assistant_message = (
            no_op_add_assistant_message
        )
        aicoder_instance.message_history.add_tool_results = no_op_add_tool_results

        # 4. Override the API request method to send only the current message
        original_make_api_request = aicoder_instance._make_api_request

        def minimal_api_request(
            messages, disable_streaming_mode=False, disable_tools=False
        ):
            # Create a minimal message list with just the current user message
            if (
                hasattr(aicoder_instance, "_current_user_message")
                and aicoder_instance._current_user_message
            ):
                minimal_messages = [
                    {"role": "user", "content": aicoder_instance._current_user_message}
                ]
            else:
                # Fallback to the last message if we don't have the current one
                user_messages = [msg for msg in messages if msg.get("role") == "user"]
                if user_messages:
                    minimal_messages = [user_messages[-1]]
                else:
                    minimal_messages = messages[-1:] if messages else []

            # Call original method with minimal messages
            return original_make_api_request(
                minimal_messages, disable_streaming_mode, disable_tools
            )

        aicoder_instance._make_api_request = minimal_api_request

        return True
    except Exception as e:
        print(f"[X] Failed to load No Memory Chat plugin: {e}")
        return False

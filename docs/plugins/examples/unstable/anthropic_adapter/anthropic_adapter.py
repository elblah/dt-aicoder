"""
Anthropic Adapter Plugin for AI Coder

This plugin transforms OpenAI-style API calls to Anthropic-compatible ones
by intercepting API requests and converting them to use the Anthropic API.

Features:
- Converts OpenAI chat completions API calls to Anthropic Messages API
- Handles tool calling conversion
- Manages API key and endpoint configuration
- Provides debug output for transformation process

Requirements:
- anthropic Python library (pip install anthropic)
"""

import os
import json
from typing import List, Dict, Any

# Global variables to store plugin state
_anthropic_client = None
_anthropic_api_key = None
_anthropic_model = None
_debug_mode = False


def on_plugin_load():
    """Called when the plugin is loaded"""
    global _debug_mode
    _debug_mode = os.environ.get("DEBUG", "0") == "1"

    if _debug_mode:
        print("Anthropic Adapter plugin loading...")


def on_aicoder_init(aicoder_instance):
    """Called when AICoder instance is initialized"""
    global _anthropic_api_key, _anthropic_model, _debug_mode

    try:
        # Check if anthropic library is available
        try:
            import anthropic
        except ImportError:
            print("[X] Anthropic library not found. Install with: pip install anthropic")
            return False

        # Get Anthropic API key from environment
        _anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not _anthropic_api_key:
            print("[!]  ANTHROPIC_API_KEY not set. Plugin will not be active.")
            return False

        # Get model from environment or use default
        _anthropic_model = os.environ.get(
            "ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"
        )

        # Initialize Anthropic client
        import anthropic

        global _anthropic_client
        _anthropic_client = anthropic.Anthropic(api_key=_anthropic_api_key)

        # Override the API handler method
        aicoder_instance._make_api_request = _make_anthropic_api_request

        if _debug_mode:
            print("[✓] Anthropic Adapter plugin loaded successfully")
            print(f"   - Model: {_anthropic_model}")
            print(
                f"   - API Key: {'*' * len(_anthropic_api_key) if _anthropic_api_key else 'None'}"
            )

        print("[✓] Anthropic Adapter plugin loaded successfully")
        return True
    except Exception as e:
        print(f"[X] Failed to load Anthropic Adapter plugin: {e}")
        return False


def _convert_openai_to_anthropic_messages(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert OpenAI messages format to Anthropic messages format"""
    anthropic_messages = []

    for message in messages:
        # Skip system messages as they're handled separately in Anthropic
        if message.get("role") == "system":
            continue

        # Convert user and assistant messages
        if message.get("role") in ["user", "assistant"]:
            anthropic_message = {"role": message["role"], "content": []}

            # Handle string content
            if isinstance(message.get("content"), str):
                anthropic_message["content"].append(
                    {"type": "text", "text": message["content"]}
                )
            # Handle array content (like tool calls)
            elif isinstance(message.get("content"), list):
                for content_item in message["content"]:
                    if content_item.get("type") == "text":
                        anthropic_message["content"].append(content_item)
                    elif content_item.get("type") == "tool_use":
                        # Convert tool use to Anthropic format
                        anthropic_message["content"].append(
                            {
                                "type": "tool_use",
                                "id": content_item.get("id", ""),
                                "name": content_item.get("name", ""),
                                "input": content_item.get("input", {}),
                            }
                        )
                    elif content_item.get("type") == "tool_result":
                        # Convert tool result to Anthropic format
                        anthropic_message["content"].append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content_item.get("tool_call_id", ""),
                                "content": content_item.get("content", ""),
                            }
                        )

            anthropic_messages.append(anthropic_message)

        # Handle tool messages
        elif message.get("role") == "tool":
            # Convert tool results to assistant message with tool_result content
            anthropic_messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": message.get("tool_call_id", ""),
                            "content": message.get("content", ""),
                        }
                    ],
                }
            )

    return anthropic_messages


def _extract_system_message(messages: List[Dict[str, Any]]) -> str:
    """Extract system message from OpenAI messages"""
    for message in messages:
        if message.get("role") == "system":
            return message.get("content", "")
    return ""


def _convert_openai_tools_to_anthropic(
    tools: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert OpenAI tools format to Anthropic tools format"""
    anthropic_tools = []

    for tool in tools:
        if "function" in tool:
            function = tool["function"]
            anthropic_tool = {
                "name": function.get("name", ""),
                "description": function.get("description", ""),
                "input_schema": function.get("parameters", {}),
            }
            anthropic_tools.append(anthropic_tool)

    return anthropic_tools


def _make_anthropic_api_request(
    aicoder_instance,
    messages: List[Dict[str, Any]],
    disable_streaming_mode: bool = False,
    disable_tools: bool = False,
):
    """Make an Anthropic API request instead of OpenAI API request"""
    global _anthropic_client, _anthropic_model, _debug_mode

    try:
        if _debug_mode:
            print("*** Converting OpenAI request to Anthropic format...")

        # Convert messages
        anthropic_messages = _convert_openai_to_anthropic_messages(messages)
        system_message = _extract_system_message(messages)

        # Prepare request parameters
        request_params = {
            "model": _anthropic_model,
            "messages": anthropic_messages,
            "max_tokens": 1024,  # Default max tokens for Anthropic
        }

        # Add system message if present
        if system_message:
            request_params["system"] = system_message

        # Add tools if not disabled
        if not disable_tools and hasattr(aicoder_instance, "tool_manager"):
            openai_tools = aicoder_instance.tool_manager.get_tool_definitions()
            anthropic_tools = _convert_openai_tools_to_anthropic(openai_tools)
            if anthropic_tools:
                request_params["tools"] = anthropic_tools

        # Handle temperature from config
        if hasattr(aicoder_instance, "TEMPERATURE"):
            request_params["temperature"] = aicoder_instance.TEMPERATURE

        if _debug_mode:
            print(f"*** Anthropic API Request: {json.dumps(request_params, indent=2)}")

        # Make the API call
        response = _anthropic_client.messages.create(**request_params)

        if _debug_mode:
            print(f"*** Anthropic API Response: {response}")

        # Convert Anthropic response back to OpenAI format
        openai_response = _convert_anthropic_to_openai_response(response)

        if _debug_mode:
            print(f"*** Converted Response: {json.dumps(openai_response, indent=2)}")

        return openai_response

    except Exception as e:
        print(f"[X] Error in Anthropic API request: {e}")
        # Fall back to original OpenAI request
        original_make_api_request = aicoder_instance.__class__._make_api_request
        return original_make_api_request(
            aicoder_instance, messages, disable_streaming_mode, disable_tools
        )


def _convert_anthropic_to_openai_response(anthropic_response) -> Dict[str, Any]:
    """Convert Anthropic response format to OpenAI response format"""
    # Extract content from Anthropic response
    content = ""
    tool_calls = []

    for content_block in anthropic_response.content:
        if content_block.type == "text":
            content += content_block.text
        elif content_block.type == "tool_use":
            tool_calls.append(
                {
                    "id": content_block.id,
                    "type": "function",
                    "function": {
                        "name": content_block.name,
                        "arguments": json.dumps(content_block.input),
                    },
                }
            )

    # Build OpenAI-style response
    openai_response = {
        "id": anthropic_response.id,
        "object": "chat.completion",
        "created": int(anthropic_response.stop_sequence)
        if anthropic_response.stop_sequence
        else 0,
        "model": anthropic_response.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": anthropic_response.stop_reason
                if anthropic_response.stop_reason
                else "stop",
            }
        ],
    }

    # Add tool calls if present
    if tool_calls:
        openai_response["choices"][0]["message"]["tool_calls"] = tool_calls

    # Add usage information if available
    if hasattr(anthropic_response, "usage"):
        openai_response["usage"] = {
            "prompt_tokens": anthropic_response.usage.input_tokens
            if hasattr(anthropic_response.usage, "input_tokens")
            else 0,
            "completion_tokens": anthropic_response.usage.output_tokens
            if hasattr(anthropic_response.usage, "output_tokens")
            else 0,
        }

    return openai_response

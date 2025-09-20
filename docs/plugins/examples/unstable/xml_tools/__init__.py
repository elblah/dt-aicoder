"""
XML Tools Plugin - Unified XML system prompt generation and tool execution

This plugin provides both XML system prompt generation (/xml_tools command)
and XML tool call execution functions for LLMs that don't support native tool calling.

Key functions:
- _process_pending_xml_tool_calls_for_input(): Process AI responses for XML tool calls via input() monkey patching
- _handle_xml_tools_command(): Handle /xml_tools command for system prompt generation
"""

# Make key functions available at package level
from .xml_tools import _process_pending_xml_tool_calls_for_input

__all__ = ["_process_pending_xml_tool_calls_for_input"]

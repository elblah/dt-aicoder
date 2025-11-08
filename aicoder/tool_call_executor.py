"""
Tool call execution handling for AI Coder.
"""

from typing import Tuple, List, Dict, Any


class ToolCallExecutorMixin:
    """Mixin class for tool call execution handling."""

    def _execute_tool_calls(
        self, message: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], bool, bool]:
        """Executes tool calls from an AI message and returns the results."""
        return self.tool_manager.execute_tool_calls(message)

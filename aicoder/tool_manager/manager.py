"""
Main Tool Manager for AI Coder - Combines registry and execution functionality.
"""

from typing import Dict, Any, List, Tuple
from .registry import ToolRegistry
from .executor import ToolExecutor


class MCPToolManager:
    """Main tool manager that combines registry and execution functionality."""

    def __init__(self, stats, message_history=None, animator=None):
        self.animator = animator
        self.registry = ToolRegistry(message_history)
        self.executor = ToolExecutor(self.registry, stats, animator)
        # Expose commonly used attributes
        self.mcp_tools = self.registry.mcp_tools
        self.mcp_servers = self.registry.mcp_servers
        self.approval_system = self.executor.approval_system

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get tool definitions for the API."""
        return self.registry.get_tool_definitions()

    

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_index: int = 0,
        total_tools: int = 0,
    ) -> str:
        """Execute a single tool."""
        result, _, _ = self.executor.execute_tool(
            tool_name, arguments, tool_index, total_tools
        )
        return result

    def execute_tool_calls(
        self, message: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Execute multiple tool calls from an AI message."""
        return self.executor.execute_tool_calls(message)

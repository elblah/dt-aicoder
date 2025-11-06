"""
Tool Manager Package for AI Coder.
"""

from typing import Optional
from .manager import MCPToolManager

__all__ = ["MCPToolManager"]

# Global tool manager instance (singleton pattern)
_tool_manager_instance: Optional[MCPToolManager] = None


def get_tool_manager() -> Optional[MCPToolManager]:
    """Get the global tool manager instance.
    
    Returns None if the tool manager hasn't been initialized yet.
    This allows for clean access without ugly hasattr checks.
    """
    return _tool_manager_instance


def set_tool_manager(tool_manager: MCPToolManager):
    """Set the global tool manager instance.
    
    Called during app initialization to register the singleton.
    """
    global _tool_manager_instance
    _tool_manager_instance = tool_manager

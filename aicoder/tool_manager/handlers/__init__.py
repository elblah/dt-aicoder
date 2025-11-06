"""
Tool handlers package for AI Coder - modular tool type processing.
"""

from .base import BaseToolHandler, ToolExecutionContext
from .internal import InternalToolHandler
from .command import CommandToolHandler
from .jsonrpc import JSONRPCToolHandler
from .mcp_stdio import MCPStdioToolHandler

# Registry of tool type handlers
TOOL_HANDLERS = {
    "internal": InternalToolHandler,
    "command": CommandToolHandler,
    "jsonrpc": JSONRPCToolHandler,
    "mcp-stdio": MCPStdioToolHandler,
}
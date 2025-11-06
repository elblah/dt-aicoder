"""
Tests for error handling in ToolExecutor.

[!] CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python -m pytest tests/test_executor_error_handling.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import os
import sys
from unittest.mock import Mock

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.executor import ToolExecutor
from aicoder.tool_manager.registry import ToolRegistry
from aicoder.stats import Stats
from aicoder.animator import Animator


class TestExecutorErrorHandling:
    """Test error handling in ToolExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tool_registry = Mock(spec=ToolRegistry)
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = {}
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = {}
        self.mock_stats = Stats()
        self.mock_animator = Mock(spec=Animator)
        self.executor = ToolExecutor(self.mock_tool_registry, self.mock_stats, self.mock_animator)
        
        # Track initial stats
        self.initial_tool_calls = self.mock_stats.tool_calls
        self.initial_tool_errors = self.mock_stats.tool_errors

    def test_unknown_tool_type(self):
        """Test execution of unknown tool type."""
        tool_config = {
            "type": "unknown_type",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
            'unknown_tool',
            {"param": "test"},
            1, 1
        )
        
        assert "Unknown tool type" in result
        assert "unknown_type" in result
        assert returned_config == tool_config
        assert guidance is None
        assert guidance_requested is False
        assert self.mock_stats.tool_errors >= self.initial_tool_errors

    def test_tool_config_not_found(self):
        """Test execution when tool configuration is not found."""
        self.mock_tool_registry.mcp_tools.get.return_value = None
        self.mock_tool_registry.mcp_servers = {}  # No MCP servers
        
        result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
            'nonexistent_tool',
            {"param": "test"},
            1, 1
        )
        
        assert "Tool 'nonexistent_tool' not found" in result
        assert isinstance(returned_config, dict)
        assert guidance is None
        assert guidance_requested is False
        assert self.mock_stats.tool_errors == self.initial_tool_errors  # Tool not found doesn't increment errors

    def test_execution_with_none_tool_name(self):
        """Test execution with None tool name."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
            None,  # None tool name
            {"param": "test"},
            1, 1
        )
        
        # Should handle gracefully and still attempt to process
        assert returned_config == tool_config

    
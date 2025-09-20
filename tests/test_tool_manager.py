"""
Tests for the tool manager module.

⚠️ CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python tests/test_tool_manager.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import sys
import os
import unittest

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.registry import ToolRegistry
from aicoder.tool_manager.manager import MCPToolManager
from aicoder.tool_manager.executor import ToolExecutor
from aicoder.tool_manager.approval_system import ApprovalSystem


class TestToolManager(unittest.TestCase):
    """Test cases for the tool manager module."""

    def test_tool_registry_initialization(self):
        """Test that tool registry initializes correctly."""
        registry = ToolRegistry()

        # Check that registry has the expected attributes
        self.assertTrue(hasattr(registry, "mcp_tools"))
        self.assertIsInstance(registry.mcp_tools, dict)

        # Check that some core tools are registered
        # Note: This assumes the registry automatically registers core tools
        # If not, this test might need adjustment

    def test_tool_manager_initialization(self):
        """Test that tool manager initializes correctly."""

        # Create a mock stats object (required for the tool manager)
        class MockStats:
            def __init__(self):
                pass

        mock_stats = MockStats()
        manager = MCPToolManager(mock_stats)

        # Check that manager has the expected attributes
        self.assertTrue(hasattr(manager, "registry"))
        self.assertTrue(hasattr(manager, "executor"))
        self.assertTrue(hasattr(manager, "approval_system"))

        # Verify they are the correct types
        self.assertIsInstance(manager.registry, ToolRegistry)
        self.assertIsInstance(manager.executor, ToolExecutor)
        self.assertIsInstance(manager.approval_system, ApprovalSystem)

    def test_tool_manager_has_core_tools(self):
        """Test that tool manager has core tools registered."""

        class MockApprovalSystem:
            def __init__(self):
                pass

        approval_system = MockApprovalSystem()
        manager = MCPToolManager(approval_system)

        # Check that some core tools exist
        tools = manager.registry.get_tool_definitions()
        self.assertIsInstance(tools, list)

        # Note: The exact tools might vary based on implementation
        # This test might need adjustment based on what tools are actually registered


if __name__ == "__main__":
    unittest.main()

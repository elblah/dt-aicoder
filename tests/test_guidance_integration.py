"""
Integration test for the simplified guidance system.

This test verifies that the guidance system works end-to-end with real components
rather than complex mocking.
"""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.executor import ToolExecutor
from aicoder.tool_manager.registry import ToolRegistry
from aicoder.stats import Stats
from aicoder.animator import Animator
from aicoder.tool_manager.internal_tools import INTERNAL_TOOL_FUNCTIONS


class TestGuidanceIntegration:
    """Test the simplified guidance system with real components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tool_registry = Mock(spec=ToolRegistry)
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = Mock()
        self.mock_stats = Stats()
        self.mock_animator = Mock(spec=Animator)
        self.executor = ToolExecutor(self.mock_tool_registry, self.mock_stats, self.mock_animator)

    def test_guidance_flag_with_internal_tool(self):
        """Test that guidance flag is properly handled for internal tools."""
        def mock_tool_func(param: str, stats=None):
            return f"Executed with {param}"

        tool_config = {
            "type": "internal",
            "auto_approved": False  # Requires approval
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        # Mock approval system to approve with guidance (the + option)
        # Need to make sure we're not in YOLO mode to trigger the guidance logic
        with patch('aicoder.tool_manager.executor.config.YOLO_MODE', False):
            self.executor.approval_system.request_user_approval = Mock(return_value=(True, True))  # (approved, with_guidance)
            self.executor.approval_system.format_tool_prompt = Mock(return_value="Mock prompt")

            with patch.dict(
                'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
                {'mock_tool': mock_tool_func}
            ):
                result, config, show_main_prompt = self.executor.execute_tool(
                    'mock_tool',
                    {"param": "test"},
                    1, 1
                )

                assert result == "Executed with test"
                assert config == tool_config
                assert show_main_prompt is True  # Should show main prompt when guidance requested

    def test_guidance_flag_with_denied_tool(self):
        """Test that guidance flag is properly handled for denied tools."""
        def mock_tool_func(param: str, stats=None):
            return f"Should not execute: {param}"

        tool_config = {
            "type": "internal",
            "auto_approved": False  # Requires approval
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        # Mock approval system to deny with guidance (the + option after denial)
        # Need to make sure we're not in YOLO mode to trigger the denial logic
        with patch('aicoder.tool_manager.executor.config.YOLO_MODE', False):
            self.executor.approval_system.request_user_approval = Mock(return_value=(False, True))  # (approved, with_guidance)
            self.executor.approval_system.format_tool_prompt = Mock(return_value="Mock prompt")

            with patch.dict(
                'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
                {'mock_tool': mock_tool_func}
            ):
                result, config, show_main_prompt = self.executor.execute_tool(
                    'mock_tool',
                    {"param": "test"},
                    1, 1
                )

                # Should be denied but still show main prompt for guidance
                assert "EXECUTION DENIED" in result or "DENIED" in result.upper()
                assert config == tool_config
                assert show_main_prompt is True  # Should show main prompt when guidance requested even after denial

    def test_no_guidance_flag_normal_execution(self):
        """Test normal execution without guidance flag."""
        def mock_tool_func(param: str, stats=None):
            return f"Executed with {param}"

        tool_config = {
            "type": "internal",
            "auto_approved": True  # Auto-approved
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'mock_tool': mock_tool_func}
        ):
            result, config, show_main_prompt = self.executor.execute_tool(
                'mock_tool',
                {"param": "test"},
                1, 1
            )

            assert result == "Executed with test"
            assert config == tool_config
            assert show_main_prompt is False  # Should not show main prompt when no guidance requested

    def test_tool_calls_return_format(self):
        """Test that execute_tool_calls returns the correct format."""
        # Mock a simple tool call
        message = {
            "tool_calls": [
                {
                    "id": "test_call_1",
                    "function": {
                        "name": "nonexistent_tool",
                        "arguments": "{}"
                    }
                }
            ]
        }

        # Set up mock to return a basic tool config
        self.mock_tool_registry.mcp_tools.get.return_value = {
            "type": "internal",
            "auto_approved": True
        }

        results, cancel_all, show_main_prompt = self.executor.execute_tool_calls(message)

        # Verify return format
        assert isinstance(results, list)
        assert isinstance(cancel_all, bool)
        assert isinstance(show_main_prompt, bool)
        assert len(results) == 1  # Should have one result entry
        assert results[0]["role"] == "tool"
        assert results[0]["name"] == "nonexistent_tool"
        assert "Error" in results[0]["content"]  # Tool should fail since it doesn't exist
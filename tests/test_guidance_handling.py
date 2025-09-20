"""
Unit tests for guidance handling in tool calls.
"""

import unittest
import json
from unittest.mock import Mock, patch

from aicoder.tool_manager.executor import ToolExecutor
from aicoder.tool_manager.registry import ToolRegistry
from aicoder.stats import Stats
from aicoder.animator import Animator


class TestGuidanceHandling(unittest.TestCase):
    """Test guidance handling in tool calls."""

    def setUp(self):
        """Set up test fixtures."""
        self.stats = Stats()
        self.animator = Animator()
        self.tool_registry = ToolRegistry(None)
        self.executor = ToolExecutor(self.tool_registry, self.stats, self.animator)

        # Mock the approval system to auto-approve tools
        self.executor.approval_system.request_user_approval = Mock(
            return_value=(True, False)
        )

        # Add a mock internal tool for testing
        def mock_tool_function(param1: str, param2: int, stats=None):
            return f"Mock tool result: {param1}, {param2}"

        self.tool_registry.mcp_tools["mock_tool"] = {
            "type": "internal",
            "auto_approved": True,
            "function": mock_tool_function,
        }

    def test_single_tool_call_with_guidance(self):
        """Test guidance handling for a single tool call."""
        message = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "mock_tool",
                        "arguments": json.dumps({"param1": "test", "param2": 42}),
                    },
                }
            ]
        }

        # Mock execute_tool to return guidance content
        with patch.object(
            self.executor,
            "execute_tool",
            return_value=("result", {}, "This is guidance"),
        ):
            tool_results, cancel_all = self.executor.execute_tool_calls(message)

            # Should have 2 entries: 1 tool result + 1 guidance message
            self.assertEqual(len(tool_results), 2)

            # First should be tool result
            self.assertEqual(tool_results[0]["role"], "tool")
            self.assertEqual(tool_results[0]["tool_call_id"], "call_1")

            # Second should be guidance message with proper ID reference
            self.assertEqual(tool_results[1]["role"], "user")
            self.assertIn("call_1", tool_results[1]["content"])
            self.assertIn("This is guidance", tool_results[1]["content"])

    def test_multiple_tool_calls_with_guidance(self):
        """Test guidance handling for multiple tool calls."""
        message = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "mock_tool",
                        "arguments": json.dumps({"param1": "test1", "param2": 1}),
                    },
                },
                {
                    "id": "call_2",
                    "function": {
                        "name": "mock_tool",
                        "arguments": json.dumps({"param1": "test2", "param2": 2}),
                    },
                },
                {
                    "id": "call_3",
                    "function": {
                        "name": "mock_tool",
                        "arguments": json.dumps({"param1": "test3", "param2": 3}),
                    },
                },
            ]
        }

        # Mock execute_tool to return different guidance for each call
        def mock_execute_tool(tool_name, arguments, tool_index, total_tools):
            guidance_content = f"Guidance for call {tool_index}"
            return (f"result_{tool_index}", {}, guidance_content)

        with patch.object(self.executor, "execute_tool", side_effect=mock_execute_tool):
            tool_results, cancel_all = self.executor.execute_tool_calls(message)

            # Should have 6 entries: 3 tool results + 3 guidance messages
            self.assertEqual(len(tool_results), 6)

            # Check that all tool results come first
            for i in range(3):
                self.assertEqual(tool_results[i]["role"], "tool")
                self.assertEqual(tool_results[i]["tool_call_id"], f"call_{i + 1}")

            # Check that all guidance messages come after tool results
            for i in range(3, 6):
                self.assertEqual(tool_results[i]["role"], "user")
                self.assertIn(f"Guidance for call {i - 2}", tool_results[i]["content"])
                self.assertIn(f"call_{i - 2}", tool_results[i]["content"])

    def test_tool_calls_with_mixed_guidance(self):
        """Test guidance handling when some tool calls have guidance and others don't."""
        message = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "mock_tool",
                        "arguments": json.dumps({"param1": "test1", "param2": 1}),
                    },
                },
                {
                    "id": "call_2",
                    "function": {
                        "name": "mock_tool",
                        "arguments": json.dumps({"param1": "test2", "param2": 2}),
                    },
                },
                {
                    "id": "call_3",
                    "function": {
                        "name": "mock_tool",
                        "arguments": json.dumps({"param1": "test3", "param2": 3}),
                    },
                },
            ]
        }

        # Mock execute_tool to return guidance for some calls only
        def mock_execute_tool(tool_name, arguments, tool_index, total_tools):
            if tool_index == 2:  # Only middle call has guidance
                return (f"result_{tool_index}", {}, f"Guidance for call {tool_index}")
            return (f"result_{tool_index}", {}, None)

        with patch.object(self.executor, "execute_tool", side_effect=mock_execute_tool):
            tool_results, cancel_all = self.executor.execute_tool_calls(message)

            # Should have 4 entries: 3 tool results + 1 guidance message
            self.assertEqual(len(tool_results), 4)

            # Check that all tool results come first
            for i in range(3):
                self.assertEqual(tool_results[i]["role"], "tool")

            # Check that guidance message comes last
            self.assertEqual(tool_results[3]["role"], "user")
            self.assertIn("Guidance for call 2", tool_results[3]["content"])
            self.assertIn("call_2", tool_results[3]["content"])

    def test_tool_call_without_guidance(self):
        """Test that tool calls without guidance work correctly."""
        message = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        "name": "mock_tool",
                        "arguments": json.dumps({"param1": "test", "param2": 42}),
                    },
                }
            ]
        }

        # Mock execute_tool to return no guidance
        with patch.object(
            self.executor, "execute_tool", return_value=("result", {}, None)
        ):
            tool_results, cancel_all = self.executor.execute_tool_calls(message)

            # Should have 1 entry: 1 tool result (no guidance)
            self.assertEqual(len(tool_results), 1)

            # Should be tool result only
            self.assertEqual(tool_results[0]["role"], "tool")
            self.assertEqual(tool_results[0]["tool_call_id"], "call_1")


if __name__ == "__main__":
    unittest.main()

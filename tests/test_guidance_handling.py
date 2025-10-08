"""
Unit tests for guidance handling in tool calls.
"""

import json
from unittest.mock import Mock, patch

from aicoder.tool_manager.executor import ToolExecutor
from aicoder.tool_manager.registry import ToolRegistry
from aicoder.stats import Stats
from aicoder.animator import Animator


def test_single_tool_call_with_guidance():
    """Test guidance handling for a single tool call."""
    stats = Stats()
    animator = Animator()
    tool_registry = ToolRegistry(None)
    executor = ToolExecutor(tool_registry, stats, animator)

    # Mock the approval system to auto-approve tools
    executor.approval_system.request_user_approval = Mock(
        return_value=(True, False)
    )

    # Add a mock internal tool for testing
    def mock_tool_function(param1: str, param2: int, stats=None):
        return f"Mock tool result: {param1}, {param2}"

    tool_registry.mcp_tools["mock_tool"] = {
        "type": "internal",
        "auto_approved": True,
        "function": mock_tool_function,
    }

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
        executor,
        "execute_tool",
        return_value=("result", {}, "This is guidance", False),
    ):
        tool_results, cancel_all = executor.execute_tool_calls(message)

        # Should have 2 entries: 1 tool result + 1 guidance message
        assert len(tool_results) == 2

        # First should be tool result
        assert tool_results[0]["role"] == "tool"
        assert tool_results[0]["tool_call_id"] == "call_1"

        # Second should be guidance message with proper ID reference
        assert tool_results[1]["role"] == "user"
        assert "call_1" in tool_results[1]["content"]
        assert "This is guidance" in tool_results[1]["content"]


def test_multiple_tool_calls_with_guidance():
    """Test guidance handling for multiple tool calls."""
    stats = Stats()
    animator = Animator()
    tool_registry = ToolRegistry(None)
    executor = ToolExecutor(tool_registry, stats, animator)

    # Mock the approval system to auto-approve tools
    executor.approval_system.request_user_approval = Mock(
        return_value=(True, False)
    )

    # Add a mock internal tool for testing
    def mock_tool_function(param1: str, param2: int, stats=None):
        return f"Mock tool result: {param1}, {param2}"

    tool_registry.mcp_tools["mock_tool"] = {
        "type": "internal",
        "auto_approved": True,
        "function": mock_tool_function,
    }

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
        return (f"result_{tool_index}", {}, guidance_content, True)  # guidance_requested=True

    with patch.object(executor, "execute_tool", side_effect=mock_execute_tool):
        tool_results, cancel_all = executor.execute_tool_calls(message)

        # Should have 6 entries: 3 tool results + 3 guidance messages
        assert len(tool_results) == 6

        # Check that all tool results come first
        for i in range(3):
            assert tool_results[i]["role"] == "tool"
            assert tool_results[i]["tool_call_id"] == f"call_{i + 1}"

        # Check that all guidance messages come after tool results
        for i in range(3, 6):
            assert tool_results[i]["role"] == "user"
            assert f"Guidance for call {i - 2}" in tool_results[i]["content"]
            assert f"call_{i - 2}" in tool_results[i]["content"]


def test_tool_calls_with_mixed_guidance():
    """Test guidance handling when some tool calls have guidance and others don't."""
    stats = Stats()
    animator = Animator()
    tool_registry = ToolRegistry(None)
    executor = ToolExecutor(tool_registry, stats, animator)

    # Mock the approval system to auto-approve tools
    executor.approval_system.request_user_approval = Mock(
        return_value=(True, False)
    )

    # Add a mock internal tool for testing
    def mock_tool_function(param1: str, param2: int, stats=None):
        return f"Mock tool result: {param1}, {param2}"

    tool_registry.mcp_tools["mock_tool"] = {
        "type": "internal",
        "auto_approved": True,
        "function": mock_tool_function,
    }

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
            return (f"result_{tool_index}", {}, f"Guidance for call {tool_index}", True)  # guidance_requested=True
        return (f"result_{tool_index}", {}, None, False)  # guidance_requested=False

    with patch.object(executor, "execute_tool", side_effect=mock_execute_tool):
        tool_results, cancel_all = executor.execute_tool_calls(message)

        # Should have 4 entries: 3 tool results + 1 guidance message
        assert len(tool_results) == 4

        # Check that all tool results come first
        for i in range(3):
            assert tool_results[i]["role"] == "tool"

        # Check that guidance message comes last
        assert tool_results[3]["role"] == "user"
        assert "Guidance for call 2" in tool_results[3]["content"]
        assert "call_2" in tool_results[3]["content"]


def test_tool_call_without_guidance():
    """Test that tool calls without guidance work correctly."""
    stats = Stats()
    animator = Animator()
    tool_registry = ToolRegistry(None)
    executor = ToolExecutor(tool_registry, stats, animator)

    # Mock the approval system to auto-approve tools
    executor.approval_system.request_user_approval = Mock(
        return_value=(True, False)
    )

    # Add a mock internal tool for testing
    def mock_tool_function(param1: str, param2: int, stats=None):
        return f"Mock tool result: {param1}, {param2}"

    tool_registry.mcp_tools["mock_tool"] = {
        "type": "internal",
        "auto_approved": True,
        "function": mock_tool_function,
    }

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
        executor, "execute_tool", return_value=("result", {}, None, False)
    ):
        tool_results, cancel_all = executor.execute_tool_calls(message)

        # Should have 1 entry: 1 tool result (no guidance)
        assert len(tool_results) == 1

        # Should be tool result only
        assert tool_results[0]["role"] == "tool"
        assert tool_results[0]["tool_call_id"] == "call_1"

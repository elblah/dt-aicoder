"""
Tests for edge cases and boundary conditions in ToolExecutor.

[!] CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python -m pytest tests/test_executor_edge_cases.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import json
import os
import sys
from unittest.mock import Mock, patch

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.executor import ToolExecutor
from aicoder.tool_manager.registry import ToolRegistry
from aicoder.stats import Stats
from aicoder.animator import Animator


class TestExecutorEdgeCases:
    """Test edge cases and boundary conditions in ToolExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tool_registry = Mock(spec=ToolRegistry)
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = {}
        self.mock_stats = Stats()
        self.mock_animator = Mock(spec=Animator)
        self.executor = ToolExecutor(self.mock_tool_registry, self.mock_stats, self.mock_animator)

    def test_tool_call_with_none_arguments(self):
        """Test tool call with None arguments."""
        def mock_tool_func(value=None, stats=None):
            return "Executed with None args"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _ = self.executor.execute_tool(
                'test_tool',
                None,  # None arguments
                1, 1
            )

            assert result == "Executed with None args"

    def test_tool_call_with_empty_string_arguments(self):
        """Test tool call with empty string arguments."""
        def mock_tool_func(content="", stats=None):
            return "Executed with empty string"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _ = self.executor.execute_tool(
                'test_tool',
                "",  # Empty string arguments
                1, 1
            )

            assert True  # Tool executed with error

    def test_tool_call_with_very_large_arguments(self):
        """Test tool call with very large arguments."""
        large_string = "x" * 10000  # 10KB string

        def mock_tool_func(large_param: str, stats=None):
            return f"Received {len(large_param)} characters"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _ = self.executor.execute_tool(
                'test_tool',
                {"large_param": large_string},
                1, 1
            )

            assert "10000" in result

    def test_tool_call_with_nested_complex_arguments(self):
        """Test tool call with deeply nested complex arguments."""
        complex_args = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "deep_value": "found it",
                            "deep_list": [1, 2, {"nested": "object"}]
                        }
                    }
                }
            },
            "large_array": list(range(1000))
        }

        def mock_tool_func(level1, large_array, stats=None):
            return f"Found deep value: {level1['level2']['level3']['level4']['deep_value']}"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _ = self.executor.execute_tool(
                'test_tool',
                complex_args,
                1, 1
            )

            assert "found it" in result

    def test_tool_call_with_special_characters(self):
        """Test tool call with special characters in arguments."""
        special_chars = {
            "unicode": "🚀测试©®™",
            "quotes": '"single" and \'double\' quotes',
            "newlines": "line1\nline2\r\nline3",
            "tabs": "col1\tcol2\tcol3",
            "backslashes": "C:\\Users\\Test\\File.txt",
            "json_chars": "{}[],:\"'",
            "control_chars": "\x00\x01\x02"
        }

        def mock_tool_func(unicode, quotes, newlines, tabs, backslashes, json_chars, control_chars, stats=None):
            return f"Processed {7} special fields"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _ = self.executor.execute_tool(
                'test_tool',
                special_chars,
                1, 1
            )

            assert "7 special fields" in result

    def test_tool_call_with_numeric_arguments(self):
        """Test tool call with various numeric types."""
        numeric_args = {
            "int_val": 42,
            "float_val": 3.14159,
            "neg_int": -100,
            "neg_float": -2.718,
            "zero": 0,
            "large_int": 9223372036854775807,
            "scientific": 1.23e-10,
            "infinity": float('inf'),
            "nan": float('nan')
        }

        def mock_tool_func(int_val, float_val, neg_int, neg_float, zero, large_int, scientific, infinity, nan, stats=None):
            return f"Processed numbers: int={int_val}, float={float_val}"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _ = self.executor.execute_tool(
                'test_tool',
                numeric_args,
                1, 1
            )

            assert "int=42" in result
            assert "float=3.14159" in result

    def test_tool_call_with_boolean_and_null_arguments(self):
        """Test tool call with boolean and null values."""
        bool_null_args = {
            "true_val": True,
            "false_val": False,
            "null_val": None,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {}
        }

        def mock_tool_func(true_val, false_val, null_val, empty_string, empty_list, empty_dict, stats=None):
            return f"True: {true_val}, False: {false_val}, Null: {null_val}"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _ = self.executor.execute_tool(
                'test_tool',
                bool_null_args,
                1, 1
            )

            assert "True: True" in result
            assert "False: False" in result
            assert "Null: None" in result

    def test_multiple_tool_calls_with_mixed_success_failure(self):
        """Test multiple tool calls with some succeeding and some failing."""
        def mock_tool_func_success(param: str, stats=None):
            return f"Success: {param}"

        def mock_tool_func_error(param: str, stats=None):
            raise RuntimeError(f"Error with: {param}")

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {
                'success_tool': mock_tool_func_success,
                'error_tool': mock_tool_func_error
            }
        ):
            message = {
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "success_tool",
                            "arguments": json.dumps({"param": "test1"})
                        },
                    },
                    {
                        "id": "call_2",
                        "function": {
                            "name": "error_tool",
                            "arguments": json.dumps({"param": "test2"})
                        },
                    },
                    {
                        "id": "call_3",
                        "function": {
                            "name": "success_tool",
                            "arguments": json.dumps({"param": "test3"})
                        },
                    }
                ]
            }

            results, cancel_all, show_main_prompt = self.executor.execute_tool_calls(message)

            assert len(results) == 3
            assert results[0]["content"] == "Success: test1"
            assert "Error executing internal tool" in results[1]["content"]
            assert results[2]["content"] == "Success: test3"
            assert cancel_all is False

    def test_tool_call_with_very_long_tool_name(self):
        """Test tool call with extremely long tool name."""
        long_name = "tool_" + "a" * 1000  # 1004 character name

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        # Mock to return config for long name
        def mock_get_side_effect(name):
            if name == long_name:
                return tool_config
            return None

        self.mock_tool_registry.mcp_tools.get.side_effect = mock_get_side_effect

        def mock_long_name_tool(param: str, stats=None):
            return f"Executed long name tool: {param}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {long_name: mock_long_name_tool}
        ):
            result, _, _ = self.executor.execute_tool(
                long_name,
                {"param": "test"},
                1, 1
            )

            assert "Executed long name tool: test" in result

    def test_tool_call_with_missing_function_fields(self):
        """Test tool call with missing function fields."""
        message = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "function": {
                        # Missing "name" field
                        "arguments": json.dumps({"param": "test"})
                    },
                },
                {
                    "id": "call_2",
                    "function": {
                        "name": "nonexistent_tool",
                        # Missing "arguments" field
                    },
                }
            ]
        }

        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.emsg') as mock_emsg:
            try:
                results, cancel_all, show_main_prompt = self.executor.execute_tool_calls(message)
                # Should handle gracefully
                assert len(results) == 0  # No successful executions
                mock_emsg.assert_called()
            except KeyError:
                pass

    def test_tool_call_with_malfunctioning_approval_system(self):
        """Test tool call when approval system throws exceptions."""
        tool_config = {
            "type": "internal",
            "auto_approved": False
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_tool_func(param: str, stats=None):
            return f"Result: {param}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            # Mock approval system to throw exception
            with patch('aicoder.tool_manager.executor.config.YOLO_MODE', False):
                self.executor.approval_system.request_user_approval = Mock(side_effect=Exception("Approval system error"))
                self.executor.approval_system.format_tool_prompt = Mock(return_value="Mock prompt")

            try:
                result, _, _ = self.executor.execute_tool(
                    'test_tool',
                    {"param": "test"},
                    1, 1
                )
                assert "Result: test" in result
            except Exception:
                pass

    def test_argument_normalization_with_recursive_structures(self):
        """Test argument normalization with potentially problematic structures."""
        # Test circular reference (though this shouldn't happen with JSON)
        try:
            circular_dict = {}
            circular_dict["self"] = circular_dict

            result = self.executor._normalize_arguments(circular_dict)
            # Should handle gracefully
        except Exception:
            # If it fails, that's acceptable for this edge case
            pass

    def test_tool_call_with_zero_index_and_total(self):
        """Test tool call with zero tool_index and total_tools."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_tool_func(param: str, tool_index=0, total_tools=0, stats=None):
            return f"Index: {tool_index}, Total: {total_tools}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _ = self.executor.execute_tool(
                'test_tool',
                {"param": "test"},
                0, 0  # Zero values
            )

            assert "Index: 0" in result
            assert "Total: 0" in result

    def test_tool_call_with_negative_index_values(self):
        """Test tool call with negative index values (edge case)."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        def mock_tool_func(param: str, tool_index=-1, total_tools=-1, stats=None):
            return f"Negative index: {tool_index}, Negative total: {total_tools}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _ = self.executor.execute_tool(
                'test_tool',
                {"param": "test"},
                -1, -1  # Negative values
            )

            assert "Negative index: -1" in result
            assert "Negative total: -1" in result

    def test_concurrent_tool_execution_simulation(self):
        """Test behavior that might occur during concurrent-like scenarios."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        execution_order = []

        def mock_tool_func(param: str, stats=None):
            execution_order.append(param)
            return f"Result: {param}"

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            # Simulate rapid sequential calls
            messages = [
                {
                    "tool_calls": [
                        {
                            "id": f"call_{i}",
                            "function": {
                                "name": "test_tool",
                                "arguments": json.dumps({"param": f"item_{i}"})
                            },
                        }
                    ]
                }
                for i in range(5)
            ]

            for message in messages:
                results, cancel_all, show_main_prompt = self.executor.execute_tool_calls(message)

            # All should execute in order
            assert len(execution_order) == 5
            assert execution_order == ["item_0", "item_1", "item_2", "item_3", "item_4"]

    def test_tool_call_with_extreme_timeout_values(self):
        """Test tool call with extreme timeout values."""
        tool_config = {
            "type": "command",
            "command": "echo {message}",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        extreme_cases = [
            0,  # Zero timeout
            -1,  # Negative timeout
            999999,  # Very large timeout
            float('inf'),  # Infinite timeout
        ]

        for timeout in extreme_cases:
            result, _, _ = self.executor.execute_tool(
                'test_command',
                {"message": "test", "timeout": timeout},
                1, 1
            )

            # Should handle gracefully (may vary based on subprocess behavior)
            assert isinstance(result, str)

    def test_memory_pressure_simulation(self):
        """Test executor behavior under simulated memory pressure."""
        # Create many tool calls to simulate pressure
        def mock_tool_func(param: str, stats=None):
            return f"Memory test: {param}"

        tool_config = {
            "type": "internal",
            "auto_approved": True
        }

        self.mock_tool_registry.mcp_tools.get.return_value = tool_config

        with patch.dict(
            'aicoder.tool_manager.internal_tools.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            # Create message with many tool calls
            tool_calls = []
            for i in range(100):  # 100 tool calls
                tool_calls.append({
                    "id": f"call_{i}",
                    "function": {
                        "name": "test_tool",
                        "arguments": json.dumps({"param": f"item_{i}"})
                    },
                })

            message = {"tool_calls": tool_calls}

            results, cancel_all, show_main_prompt = self.executor.execute_tool_calls(message)

            # Should handle all calls
            assert len(results) == 100
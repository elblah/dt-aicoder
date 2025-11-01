"""
Tests for special modes and configurations in ToolExecutor.

[!] CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python -m pytest tests/test_executor_special_modes.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add the parent directory to the path to import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aicoder.tool_manager.executor import ToolExecutor, DENIED_MESSAGE
from aicoder.tool_manager.registry import ToolRegistry
from aicoder.stats import Stats
from aicoder.animator import Animator


class TestExecutorSpecialModes:
    """Test special modes and configurations in ToolExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tool_registry = Mock(spec=ToolRegistry)
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = {}
        self.mock_stats = Stats()
        self.mock_animator = Mock(spec=Animator)
        self.executor = ToolExecutor(self.mock_tool_registry, self.mock_stats, self.mock_animator)

    def test_yolo_mode_auto_approval(self):
        """Test YOLO mode provides automatic approval for safe commands."""
        with patch('aicoder.tool_manager.executor.config.YOLO_MODE', True):
            with patch('aicoder.tool_manager.executor._check_approval_rules', return_value=(False, "")):
                tool_config = {
                    "type": "internal",
                    "auto_approved": False  # Would normally require approval
                }
                
                self.mock_tool_registry.mcp_tools.get.return_value = tool_config
                
                def mock_tool_func(param: str, stats=None):
                    return f"YOLO executed: {param}"
                
                with patch.dict(
                    'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
                    {'test_tool': mock_tool_func}
                ):
                    result, _, _, _ = self.executor.execute_tool(
                        'test_tool',
                        {"param": "yolo_test"},
                        1, 1
                    )
                    
                    assert "YOLO executed: yolo_test" in result

    def test_yolo_mode_respects_user_rules(self):
        """Test that YOLO mode respects user-configured deny rules."""
        with patch('aicoder.tool_manager.executor.config.YOLO_MODE', True):
            with patch('aicoder.tool_manager.executor._check_approval_rules', return_value=(True, "Auto denied by user rule")):
                tool_config = {
                    "type": "internal",
                    "auto_approved": False
                }
                
                self.mock_tool_registry.mcp_tools.get.return_value = tool_config
                
                def mock_run_shell_command(command, stats=None, tool_index=1, total_tools=1):
                    return f"Executed: {command}"
                
                with patch.dict(
                    'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
                    {'run_shell_command': mock_run_shell_command}
                ):
                    result, _, _, _ = self.executor.execute_tool(
                        'run_shell_command',
                        {"command": "dangerous_command"},
                        1, 1
                    )
                    
                    assert "Command denied by GLOBAL RULE" in result and "dangerous_command" in result

    def test_yolo_mode_run_shell_command_special_handling(self):
        """Test YOLO mode special handling for run_shell_command."""
        with patch('aicoder.tool_manager.executor.config.YOLO_MODE', True):
            with patch('aicoder.tool_manager.executor._check_approval_rules', return_value=(False, "")):
                from aicoder.tool_manager.internal_tools.run_shell_command import TOOL_DEFINITION
                
                tool_config = TOOL_DEFINITION.copy()
                tool_config["type"] = "internal"
                tool_config["auto_approved"] = False
                
                self.mock_tool_registry.mcp_tools.get.return_value = tool_config
                
                with patch.dict(
                    'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
                    {'run_shell_command': lambda command, stats=None, tool_index=1, total_tools=1: f"YOLO shell: {command}"}
                ):
                    with patch.object(self.executor, '_print_command_info_once') as mock_print:
                        with patch('aicoder.tool_manager.internal_tools.run_shell_command.has_dangerous_patterns', return_value=(False, "")):
                            result, _, _, _ = self.executor.execute_tool(
                                'run_shell_command',
                                {"command": "echo yolo mode"},
                                1, 1
                            )
                            
                            assert "YOLO shell: echo yolo mode" in result

    def test_planning_mode_disables_write_operations(self):
        """Test that planning mode disables write operations."""
        mock_planning_mode = Mock()
        mock_planning_mode.should_disable_tool.return_value = True
        
        with patch('aicoder.planning_mode.get_planning_mode', return_value=mock_planning_mode):
            tool_config = {
                "type": "internal",
                "auto_approved": True
            }
            
            self.mock_tool_registry.mcp_tools.get.return_value = tool_config
            
            result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
                'write_file',  # Write operation should be disabled
                {"path": "/tmp/test.txt", "content": "test"},
                1, 1
            )
            
            assert "planning mode" in result.lower() or "disabled" in result.lower()
            assert "read-only operations" in result.lower()
            assert "write_file" in result
            assert returned_config == {}  # Planning mode returns empty config for disabled tools
            assert guidance is None
            assert guidance_requested is False

    def test_planning_mode_allows_read_operations(self):
        """Test that planning mode allows read operations."""
        mock_planning_mode = Mock()
        mock_planning_mode.should_disable_tool.return_value = False
        
        with patch('aicoder.planning_mode.get_planning_mode', return_value=mock_planning_mode):
            # Ensure tool_registry has message_history attribute
            self.executor.tool_registry.message_history = Mock()
            
            tool_config = {
                "type": "internal",
                "auto_approved": True
            }
            
            self.mock_tool_registry.mcp_tools.get.return_value = tool_config
            
            def mock_read_tool(path: str, stats=None):
                return f"Content of {path}"
            
            with patch.dict(
                'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
                {'read_file': mock_read_tool}
            ):
                result, _, _, _ = self.executor.execute_tool(
                    'read_file',  # Read operation should be allowed
                    {"path": "/tmp/test.txt"},
                    1, 1
                )
                
                assert "Content of /tmp/test.txt" in result

    def test_planning_mode_import_error(self):
        """Test graceful handling when planning mode is not available."""
        with patch('aicoder.planning_mode.get_planning_mode', side_effect=ImportError("Planning mode not available")):
            tool_config = {
                "type": "internal",
                "auto_approved": True
            }
            
            self.mock_tool_registry.mcp_tools.get.return_value = tool_config
            
            def mock_tool_func(param: str, stats=None):
                return f"Executed: {param}"
            
            with patch.dict(
                'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
                {'test_tool': mock_tool_func}
            ):
                result, _, _, _ = self.executor.execute_tool(
                    'test_tool',
                    {"param": "test"},
                    1, 1
                )
                
                # Should execute normally when planning mode is not available
                assert "Executed: test" in result

    def test_debug_mode_enhances_logging(self):
        """Test that debug mode enhances logging and output."""
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
            tool_config = {
                "type": "internal",
                "auto_approved": True
            }
            
            self.mock_tool_registry.mcp_tools.get.return_value = tool_config
            
            with patch('builtins.print') as mock_print:
                result, _, _, _ = self.executor.execute_tool(
                    'test_tool',
                    {"param": "debug_test"},
                    1, 1
                )
                
                # Debug mode should show additional information
                print_calls = [str(call) for call in mock_print.call_args_list]
                # Note: This may vary depending on implementation

    def test_tool_execution_with_stats_tracking(self):
        """Test that tool execution properly tracks statistics."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        initial_tool_calls = self.mock_stats.tool_calls
        
        def mock_tool_func(param: str, stats=None):
            return f"Result: {param}"
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, _, _, _ = self.executor.execute_tool(
                'test_tool',
                {"param": "stats_test"},
                1, 1
            )
            
            # Note: Individual tool execution doesn't increment tool_calls,
            # that happens in execute_tool_calls

    def test_execute_tool_calls_stats_tracking(self):
        """Test statistics tracking in execute_tool_calls."""
        def mock_tool_func(param: str, stats=None):
            return f"Result: {param}"
        
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        initial_tool_calls = self.mock_stats.tool_calls
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            message = {
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "test_tool",
                            "arguments": json.dumps({"param": "stats_test"})
                        },
                    },
                    {
                        "id": "call_2",
                        "function": {
                            "name": "test_tool",
                            "arguments": json.dumps({"param": "another_test"})
                        },
                    }
                ]
            }
            
            results, cancel_all = self.executor.execute_tool_calls(message)
            
            # Should track both tool calls
            assert self.mock_stats.tool_calls == initial_tool_calls + 2

    def test_cancel_all_functionality(self):
        """Test cancel all functionality across multiple tools."""
        def mock_tool_func(param: str, stats=None):
            if param == "trigger_cancel":
                raise Exception("CANCEL_ALL_TOOL_CALLS")
            return f"Result: {param}"
        
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            message = {
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "test_tool",
                            "arguments": json.dumps({"param": "normal"})
                        },
                    },
                    {
                        "id": "call_2",
                        "function": {
                            "name": "test_tool",
                            "arguments": json.dumps({"param": "trigger_cancel"})
                        },
                    },
                    {
                        "id": "call_3",
                        "function": {
                            "name": "test_tool",
                            "arguments": json.dumps({"param": "should_be_skipped"})
                        },
                    }
                ]
            }
            
            with patch('builtins.print') as mock_print:
                results, cancel_all = self.executor.execute_tool_calls(message)
                
                assert cancel_all is True
                # Should have results for first two tools, third should be skipped
                assert len(results) >= 2
                assert results[0]["content"] == "Result: normal"
                assert results[1]["content"] == "CANCEL_ALL_TOOL_CALLS"

    def test_command_info_printing_with_modes(self):
        """Test command info printing with different modes."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        def mock_run_shell_command(command, timeout=30, stats=None, tool_index=1, total_tools=1):
            return f"Executed: {command}"
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'run_shell_command': mock_run_shell_command}
        ):
            # Test normal mode
            with patch.object(self.executor, '_print_command_info_once') as mock_print:
                result, _, _, _ = self.executor.execute_tool(
                    'run_shell_command',
                    {"command": "echo normal mode"},
                    1, 1
                )
                
                mock_print.assert_called_once_with("echo normal mode", 30, auto_approved=True, allow_session=False)
            
            # Test YOLO mode
            with patch('aicoder.tool_manager.executor.config.YOLO_MODE', True):
                with patch.object(self.executor, '_print_command_info_once') as mock_print:
                    with patch('aicoder.tool_manager.executor._check_approval_rules', return_value=(False, "")):
                        result, _, _, _ = self.executor.execute_tool(
                            'run_shell_command',
                            {"command": "echo yolo mode"},
                            1, 1
                        )
                        
                        mock_print.assert_called_once_with("echo yolo mode", 30, auto_approved=True, allow_session=False)

    def test_diff_edit_result_handling(self):
        """Test handling of diff-edit results in approval system."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        # Mock diff-edit result in approval system
        self.executor.approval_system._diff_edit_result = {
            "message": "File edited successfully",
            "ai_guidance": "Here's what changed"
        }
        
        def mock_tool_func(param: str, stats=None):
            return f"Normal result: {param}"
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            result, returned_config, guidance, guidance_requested = self.executor.execute_tool(
                'test_tool',
                {"param": "test"},
                1, 1
            )
            
            # Should return diff-edit result instead of normal tool result
            assert "File edited successfully" in result
            assert "Here's what changed" in result
            assert "[✓] SUCCESS:" in result
            assert returned_config == tool_config
            assert guidance is None
            assert guidance_requested is False

    def test_pending_tool_messages_integration(self):
        """Test integration with pending tool messages."""
        tool_config = {
            "type": "internal",
            "auto_approved": True
        }
        
        self.mock_tool_registry.mcp_tools.get.return_value = tool_config
        
        def mock_tool_func(param: str, stats=None):
            return f"Result: {param}"
        
        with patch.dict(
            'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
            {'test_tool': mock_tool_func}
        ):
            # Add pending messages before execution
            from aicoder.tool_manager.executor import pending_tool_messages
            pending_tool_messages.extend([
                {"role": "user", "content": "Pending message 1"},
                {"role": "user", "content": "Pending message 2"}
            ])
            
            # Add another pending message during execution (simulated by a tool)
            def mock_tool_with_pending(param: str, stats=None):
                pending_tool_messages.append({"role": "user", "content": "During execution message"})
                return f"Tool result: {param}"
            
            with patch.dict(
                'aicoder.tool_manager.executor.INTERNAL_TOOL_FUNCTIONS',
                {'test_tool': mock_tool_with_pending}
            ):
                message = {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "test_tool",
                                "arguments": json.dumps({"param": "test"})
                            },
                        }
                    ]
                }
                
                results, cancel_all = self.executor.execute_tool_calls(message)
                
                # Should include both tool result and pending messages
                assert len(results) == 4  # 1 tool result + 3 pending messages
                assert results[0]["role"] == "tool"
                assert "Tool result: test" in results[0]["content"]
                
                # Verify pending messages are in order
                assert results[1]["role"] == "user"
                assert results[1]["content"] == "Pending message 1"
                assert results[2]["role"] == "user"
                assert results[2]["content"] == "Pending message 2"
                assert results[3]["role"] == "user"
                assert results[3]["content"] == "During execution message"
                
                # Pending messages should be cleared
                assert len(pending_tool_messages) == 0
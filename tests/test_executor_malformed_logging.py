"""
Tests for malformed tool call logging in ToolExecutor.

[!] CRITICAL: ALWAYS run this test with YOLO_MODE=1 to prevent hanging:

YOLO_MODE=1 python -m pytest tests/test_executor_malformed_logging.py

This test triggers tool approval prompts that will hang indefinitely without YOLO_MODE=1.
"""

import json
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


class TestExecutorMalformedLogging:
    """Test malformed tool call logging functionality in ToolExecutor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_tool_registry = Mock(spec=ToolRegistry)
        self.mock_tool_registry.mcp_tools = Mock()
        self.mock_tool_registry.mcp_servers = {}
        self.mock_stats = Stats()
        self.mock_animator = Mock(spec=Animator)
        self.executor = ToolExecutor(self.mock_tool_registry, self.mock_stats, self.mock_animator)

    def test_malformed_tool_call_logging_enabled(self):
        """Test that malformed tool calls are logged when DEBUG is enabled."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
            with tempfile.TemporaryDirectory() as temp_dir:
                test_filename = os.path.join(temp_dir, "test_log.json")
                
                # Mock the datetime and file operations
                with patch('aicoder.tool_manager.executor.datetime') as mock_datetime:
                    mock_now = Mock()
                    mock_datetime.now.return_value = mock_now
                    mock_now.strftime.side_effect = [
                        "20231201_120000",  # For filename
                        "2023-12-01T12:00:00"  # For timestamp
                    ]
                    mock_now.isoformat.return_value = "2023-12-01T12:00:00"
                    
                    with patch('builtins.open', create=True) as mock_open:
                        mock_file = Mock()
                        mock_open.return_value.__enter__.return_value = mock_file
                        
                        # Mock wmsg to capture the log message
                        with patch('aicoder.tool_manager.executor.wmsg') as mock_wmsg:
                            self.executor._log_malformed_tool_call(
                                "test_tool",
                                '{"invalid": json}'
                            )
                            
                            # Verify file was created and written
                            mock_open.assert_called_once_with(
                                "/tmp/malformed_tool_call_20231201_120000.log", "w"
                            )
                            # json.dump() calls write() multiple times with indentation
                            assert mock_file.write.call_count > 0
                            
                            # Verify log content - combine all write calls
                            all_writes = ''.join(call[0][0] for call in mock_file.write.call_args_list)
                            log_data = json.loads(all_writes)
                            
                            assert log_data["tool_name"] == "test_tool"
                            assert log_data["raw_arguments"] == '{"invalid": json}'
                            assert log_data["error_type"] == "Malformed JSON"
                            assert log_data["timestamp"] == "2023-12-01T12:00:00"
                            
                            # Verify user notification
                            mock_wmsg.assert_called_once()
                            wmsg_args = mock_wmsg.call_args[0][0]
                            assert "Malformed tool call logged to" in wmsg_args
                            assert "/tmp/malformed_tool_call_20231201_120000.log" in wmsg_args

    def test_malformed_tool_call_logging_disabled(self):
        """Test that malformed tool calls are not logged when DEBUG is disabled."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', False):
            with patch('builtins.open', create=True) as mock_open:
                with patch('aicoder.tool_manager.executor.wmsg') as mock_wmsg:
                    self.executor._log_malformed_tool_call(
                        "test_tool",
                        '{"invalid": json}'
                    )
                    
                    # Should not attempt to open file when DEBUG is False
                    mock_open.assert_not_called()
                    mock_wmsg.assert_not_called()

    def test_malformed_logging_with_file_write_error(self):
        """Test handling of file write errors during malformed logging."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
            with patch('aicoder.tool_manager.executor.datetime') as mock_datetime:
                mock_now = Mock()
                mock_datetime.now.return_value = mock_now
                mock_now.strftime.side_effect = [
                    "20231201_120000",
                    "2023-12-01T12:00:00"
                ]
                mock_now.isoformat.return_value = "2023-12-01T12:00:00"
                
                # Mock file write to fail
                with patch('builtins.open', side_effect=IOError("Permission denied")):
                    with patch('aicoder.tool_manager.executor.emsg') as mock_emsg:
                        self.executor._log_malformed_tool_call(
                            "test_tool",
                            '{"invalid": json}'
                        )
                        
                        # Should log error message instead of crashing
                        mock_emsg.assert_called_once()
                        emsg_args = mock_emsg.call_args[0][0]
                        assert "Failed to log malformed tool call" in emsg_args

    def test_malformed_logging_with_json_serialization_error(self):
        """Test handling of JSON serialization errors during malformed logging."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
            with patch('aicoder.tool_manager.executor.datetime') as mock_datetime:
                mock_now = Mock()
                mock_datetime.now.return_value = mock_now
                mock_now.strftime.side_effect = [
                    "20231201_120000",
                    "2023-12-01T12:00:00"
                ]
                mock_now.isoformat.return_value = "2023-12-01T12:00:00"
                
                # Mock json.dump to fail
                with patch('builtins.open', create=True):
                    with patch('json.dump', side_effect=TypeError("Cannot serialize")):
                        with patch('aicoder.tool_manager.executor.emsg') as mock_emsg:
                            self.executor._log_malformed_tool_call(
                                "test_tool",
                                '{"invalid": json}'
                            )
                            
                            # Should log error message instead of crashing
                            mock_emsg.assert_called_once()
                            emsg_args = mock_emsg.call_args[0][0]
                            assert "Failed to log malformed tool call" in emsg_args

    def test_malformed_logging_with_datetime_error(self):
        """Test handling of datetime errors during malformed logging."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
            # Mock datetime to fail
            with patch('aicoder.tool_manager.executor.datetime', side_effect=Exception("DateTime error")):
                with patch('aicoder.tool_manager.executor.emsg') as mock_emsg:
                    self.executor._log_malformed_tool_call(
                        "test_tool",
                        '{"invalid": json}'
                    )
                    
                    # Should log error message instead of crashing
                    mock_emsg.assert_called_once()
                    emsg_args = mock_emsg.call_args[0][0]
                    assert "Failed to log malformed tool call" in emsg_args

    def test_malformed_logging_various_tool_names(self):
        """Test malformed logging with various tool name types."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
            with tempfile.TemporaryDirectory() as temp_dir:
                test_cases = [
                    "simple_tool",
                    "tool_with_underscores",
                    "tool-with-hyphens",
                    "tool123",
                    "TOOL_IN_CAPS",
                    "very_long_tool_name_that_might_be_used_in_production"
                ]
                
                for tool_name in test_cases:
                    with patch('aicoder.tool_manager.executor.datetime') as mock_datetime:
                        mock_now = Mock()
                        mock_datetime.now.return_value = mock_now
                        mock_now.strftime.side_effect = [
                            "20231201_120000",
                            "2023-12-01T12:00:00"
                        ]
                        mock_now.isoformat.return_value = "2023-12-01T12:00:00"
                        
                        with patch('builtins.open', create=True) as mock_open:
                            mock_file = Mock()
                            mock_open.return_value.__enter__.return_value = mock_file
                            
                            self.executor._log_malformed_tool_call(
                                tool_name,
                                '{"invalid": json}'
                            )
                            
                            # Verify the tool name is correctly logged
                            all_writes = ''.join(call[0][0] for call in mock_file.write.call_args_list)
                            log_data = json.loads(all_writes)
                            assert log_data["tool_name"] == tool_name

    def test_malformed_logging_various_argument_types(self):
        """Test malformed logging with various argument types."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
            test_cases = [
                '{"invalid": json}',
                '{unclosed: "string"',
                'not json at all',
                '{"key": undefined}',
                '{"key": function(){}}',
                'null',
                'undefined',
                '{"unicode": "🚀测试"}',
                '{"escaped": "line\\nbreak"}'
            ]
            
            for malformed_args in test_cases:
                with patch('aicoder.tool_manager.executor.datetime') as mock_datetime:
                    mock_now = Mock()
                    mock_datetime.now.return_value = mock_now
                    mock_now.strftime.side_effect = [
                        "20231201_120000",
                        "2023-12-01T12:00:00"
                    ]
                    mock_now.isoformat.return_value = "2023-12-01T12:00:00"
                    
                    with patch('builtins.open', create=True) as mock_open:
                        mock_file = Mock()
                        mock_open.return_value.__enter__.return_value = mock_file
                        
                        self.executor._log_malformed_tool_call(
                            "test_tool",
                            malformed_args
                        )
                        
                        # Verify the malformed arguments are correctly logged
                        # Combine all write calls to reconstruct the JSON
                        all_writes = ''.join(call[0][0] for call in mock_file.write.call_args_list)
                        log_data = json.loads(all_writes)
                        assert log_data["raw_arguments"] == malformed_args

    def test_malformed_logging_timestamp_uniqueness(self):
        """Test that each log gets a unique timestamp."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
            with tempfile.TemporaryDirectory() as temp_dir:
                log_files = []
                
                # Create multiple malformed logs
                for i in range(3):
                    with patch('aicoder.tool_manager.executor.datetime') as mock_datetime:
                        mock_now = Mock()
                        mock_datetime.now.return_value = mock_now
                        
                        # Generate different timestamps for each call
                        timestamp = f"20231201_12000{i}"
                        iso_timestamp = f"2023-12-01T12:00:0{i}"
                        mock_now.strftime.side_effect = [timestamp, iso_timestamp]
                        mock_now.isoformat.return_value = iso_timestamp
                        
                        with patch('builtins.open', create=True) as mock_open:
                            mock_file = Mock()
                            mock_open.return_value.__enter__.return_value = mock_file
                            
                            self.executor._log_malformed_tool_call(
                                f"test_tool_{i}",
                                f'{{"invalid": "json_{i}"}}'
                            )
                            
                            # Capture the filename
                            filename = mock_open.call_args[0][0]
                            log_files.append(filename)
                
                # Verify all filenames are unique
                assert len(set(log_files)) == len(log_files)
                for i, filename in enumerate(log_files):
                    assert f"20231201_12000{i}" in filename

    def test_malformed_logging_integration_with_execute_tool_calls(self):
        """Test malformed logging integration with execute_tool_calls."""
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
            message = {
                "tool_calls": [
                    {
                        "id": "call_1",
                        "function": {
                            "name": "test_tool",
                            "arguments": '{"valid": "json"}',  # Valid
                        },
                    },
                    {
                        "id": "call_2",
                        "function": {
                            "name": "test_tool",
                            "arguments": '{"invalid": json}',  # Invalid
                        },
                    },
                    {
                        "id": "call_3",
                        "function": {
                            "name": "test_tool",
                            "arguments": '{also: invalid}',  # Invalid
                        },
                    }
                ]
            }
            
            self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
                with patch.object(self.executor, '_log_malformed_tool_call') as mock_log:
                    results, cancel_all, show_main_prompt = self.executor.execute_tool_calls(message)
                    
                    # Should log the two malformed calls
                    assert mock_log.call_count == 2
                    
                    # Check what was logged
                    log_calls = mock_log.call_args_list
                    logged_args = [call[0][1] for call in log_calls]
                    
                    assert '{"invalid": json}' in logged_args
                    assert '{also: invalid}' in logged_args
                    
                    # Should have educational messages for malformed calls
                    educational_messages = [
                        r for r in results 
                        if r.get("role") == "user" and "SYSTEM ERROR" in r.get("content", "")
                    ]
                    assert len(educational_messages) == 2

    def test_malformed_logging_file_permissions_edge_case(self):
        """Test malformed logging when directory doesn't exist or has permission issues."""
        self.executor.tool_registry.message_history = Mock()
        with patch('aicoder.tool_manager.executor.config.DEBUG', True):
            with patch('aicoder.tool_manager.executor.datetime') as mock_datetime:
                mock_now = Mock()
                mock_datetime.now.return_value = mock_now
                mock_now.strftime.side_effect = [
                    "20231201_120000",
                    "2023-12-01T12:00:00"
                ]
                mock_now.isoformat.return_value = "2023-12-01T12:00:00"
                
                # Test various file system errors
                error_cases = [
                    PermissionError("Permission denied"),
                    FileNotFoundError("Directory not found"),
                    OSError("Disk full"),
                    UnicodeEncodeError("utf-8", "", 0, 1, "encoding error")
                ]
                
                for error in error_cases:
                    with patch('builtins.open', side_effect=error):
                        with patch('aicoder.tool_manager.executor.emsg') as mock_emsg:
                            try:
                                self.executor._log_malformed_tool_call(
                                    "test_tool",
                                    '{"invalid": json}'
                                )
                            except:
                                pass  # We expect the logging to handle the error gracefully
                            
                            # Should log error message instead of crashing
                            mock_emsg.assert_called()
                            emsg_args = mock_emsg.call_args[0][0]
                            assert "Failed to log malformed tool call" in emsg_args
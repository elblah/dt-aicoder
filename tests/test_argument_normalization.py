"""
Unit tests for the argument normalization functionality in ToolExecutor.
"""
import json
from unittest.mock import Mock
import sys
import os

# Add the parent directory to the path so we can import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aicoder.tool_manager.executor import ToolExecutor


def test_normal_dict_unchanged():
    """Test that a normal dictionary remains unchanged."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    input_args = {"path": "test.go", "content": "package main"}
    result = executor._normalize_arguments(input_args)
    
    assert result == input_args
    assert isinstance(result, dict)


def test_double_encoded_json_string():
    """Test that double-encoded JSON strings are properly decoded."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    # Create a double-encoded JSON string like what AI models might send
    inner_dict = {"path": "test.go", "content": "package main"}
    double_encoded = json.dumps(json.dumps(inner_dict))
    
    result = executor._normalize_arguments(double_encoded)
    
    assert isinstance(result, dict)
    assert result["path"] == "test.go"
    assert result["content"] == "package main"


def test_triple_encoded_json_string():
    """Test that triple-encoded JSON strings are properly decoded."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    # Create a triple-encoded JSON string
    inner_dict = {"path": "test.go", "content": "package main"}
    temp = json.dumps(inner_dict)
    temp2 = json.dumps(temp)
    triple_encoded = json.dumps(temp2)
    
    result = executor._normalize_arguments(triple_encoded)
    
    assert isinstance(result, dict)
    assert result["path"] == "test.go"
    assert result["content"] == "package main"


def test_simple_string_wrapped_in_content():
    """Test that simple strings are wrapped in a content field."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    input_string = "just a string"
    result = executor._normalize_arguments(input_string)
    
    assert isinstance(result, dict)
    assert result["content"] == input_string


def test_list_with_dict_uses_first_element():
    """Test that lists containing dictionaries use the first dictionary."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    input_list = [{"path": "test.go", "content": "package main"}, {"other": "value"}]
    result = executor._normalize_arguments(input_list)
    
    assert isinstance(result, dict)
    assert result["path"] == "test.go"
    assert result["content"] == "package main"


def test_list_without_dict_wrapped_in_value():
    """Test that lists without dictionaries are wrapped in a value field."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    input_list = ["item1", "item2", "item3"]
    result = executor._normalize_arguments(input_list)
    
    assert isinstance(result, dict)
    assert result["value"] == input_list


def test_primitive_types_wrapped_in_value():
    """Test that primitive types are wrapped in a value field."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    # Test integer
    result_int = executor._normalize_arguments(42)
    assert isinstance(result_int, dict)
    assert result_int["value"] == 42
    
    # Test float
    result_float = executor._normalize_arguments(3.14)
    assert isinstance(result_float, dict)
    assert result_float["value"] == 3.14
    
    # Test boolean
    result_bool = executor._normalize_arguments(True)
    assert isinstance(result_bool, dict)
    assert result_bool["value"] is True
    
    # Test None
    result_none = executor._normalize_arguments(None)
    assert isinstance(result_none, dict)
    assert result_none["value"] is None


def test_malformed_json_remains_as_string_content():
    """Test that malformed JSON strings are treated as content."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    # This simulates the problematic case from DeepSeek
    malformed_json = '"{\\"path\": \"test.go\", \"content\": \"package main\"}"'  # Malformed
    result = executor._normalize_arguments(malformed_json)
    
    assert isinstance(result, dict)
    assert "content" in result
    # The malformed string should be preserved as content
    assert result["content"] == malformed_json


def test_empty_string_handling():
    """Test that empty strings are handled properly."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    result = executor._normalize_arguments("")
    assert isinstance(result, dict)
    assert result["content"] == ""


def test_empty_dict_handling():
    """Test that empty dictionaries remain unchanged."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    empty_dict = {}
    result = executor._normalize_arguments(empty_dict)
    assert result == empty_dict
    assert isinstance(result, dict)


def test_nested_structure_preserved():
    """Test that nested structures in dictionaries are preserved."""
    # Create a mock for the dependencies
    mock_tool_registry = Mock()
    mock_stats = Mock()
    mock_animator = Mock()
    
    # Create the executor instance
    executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)
    
    nested_dict = {
        "path": "test.go",
        "config": {
            "options": ["opt1", "opt2"],
            "settings": {
                "debug": True,
                "level": 5
            }
        }
    }
    result = executor._normalize_arguments(nested_dict)
    assert result == nested_dict
    assert isinstance(result, dict)
    assert result["config"]["settings"]["level"] == 5
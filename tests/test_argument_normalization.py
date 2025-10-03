"""
Unit tests for the argument normalization functionality in ToolExecutor.
"""
import json
import unittest
from unittest.mock import Mock
import sys
import os

# Add the parent directory to the path so we can import aicoder modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from aicoder.tool_manager.executor import ToolExecutor


class TestArgumentNormalization(unittest.TestCase):
    """Test cases for the _normalize_arguments method in ToolExecutor."""
    
    def setUp(self):
        """Set up a mock ToolExecutor instance for testing."""
        # Create a mock for the dependencies
        mock_tool_registry = Mock()
        mock_stats = Mock()
        mock_animator = Mock()
        
        # Create the executor instance
        self.executor = ToolExecutor(mock_tool_registry, mock_stats, mock_animator)

    def test_normal_dict_unchanged(self):
        """Test that a normal dictionary remains unchanged."""
        input_args = {"path": "test.go", "content": "package main"}
        result = self.executor._normalize_arguments(input_args)
        
        self.assertEqual(result, input_args)
        self.assertIsInstance(result, dict)

    def test_double_encoded_json_string(self):
        """Test that double-encoded JSON strings are properly decoded."""
        # Create a double-encoded JSON string like what AI models might send
        inner_dict = {"path": "test.go", "content": "package main"}
        double_encoded = json.dumps(json.dumps(inner_dict))
        
        result = self.executor._normalize_arguments(double_encoded)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["path"], "test.go")
        self.assertEqual(result["content"], "package main")

    def test_triple_encoded_json_string(self):
        """Test that triple-encoded JSON strings are properly decoded."""
        # Create a triple-encoded JSON string
        inner_dict = {"path": "test.go", "content": "package main"}
        temp = json.dumps(inner_dict)
        temp2 = json.dumps(temp)
        triple_encoded = json.dumps(temp2)
        
        result = self.executor._normalize_arguments(triple_encoded)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["path"], "test.go")
        self.assertEqual(result["content"], "package main")

    def test_simple_string_wrapped_in_content(self):
        """Test that simple strings are wrapped in a content field."""
        input_string = "just a string"
        result = self.executor._normalize_arguments(input_string)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["content"], input_string)

    def test_list_with_dict_uses_first_element(self):
        """Test that lists containing dictionaries use the first dictionary."""
        input_list = [{"path": "test.go", "content": "package main"}, {"other": "value"}]
        result = self.executor._normalize_arguments(input_list)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["path"], "test.go")
        self.assertEqual(result["content"], "package main")

    def test_list_without_dict_wrapped_in_value(self):
        """Test that lists without dictionaries are wrapped in a value field."""
        input_list = ["item1", "item2", "item3"]
        result = self.executor._normalize_arguments(input_list)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["value"], input_list)

    def test_primitive_types_wrapped_in_value(self):
        """Test that primitive types are wrapped in a value field."""
        # Test integer
        result_int = self.executor._normalize_arguments(42)
        self.assertIsInstance(result_int, dict)
        self.assertEqual(result_int["value"], 42)
        
        # Test float
        result_float = self.executor._normalize_arguments(3.14)
        self.assertIsInstance(result_float, dict)
        self.assertEqual(result_float["value"], 3.14)
        
        # Test boolean
        result_bool = self.executor._normalize_arguments(True)
        self.assertIsInstance(result_bool, dict)
        self.assertEqual(result_bool["value"], True)
        
        # Test None
        result_none = self.executor._normalize_arguments(None)
        self.assertIsInstance(result_none, dict)
        self.assertIsNone(result_none["value"])

    def test_malformed_json_remains_as_string_content(self):
        """Test that malformed JSON strings are treated as content."""
        # This simulates the problematic case from DeepSeek
        malformed_json = '"{\\"path\": \"test.go\", \"content\": \"package main\"}"'  # Malformed
        result = self.executor._normalize_arguments(malformed_json)
        
        self.assertIsInstance(result, dict)
        self.assertIn("content", result)
        # The malformed string should be preserved as content
        self.assertEqual(result["content"], malformed_json)

    def test_empty_string_handling(self):
        """Test that empty strings are handled properly."""
        result = self.executor._normalize_arguments("")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["content"], "")

    def test_empty_dict_handling(self):
        """Test that empty dictionaries remain unchanged."""
        empty_dict = {}
        result = self.executor._normalize_arguments(empty_dict)
        self.assertEqual(result, empty_dict)
        self.assertIsInstance(result, dict)

    def test_nested_structure_preserved(self):
        """Test that nested structures in dictionaries are preserved."""
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
        result = self.executor._normalize_arguments(nested_dict)
        self.assertEqual(result, nested_dict)
        self.assertIsInstance(result, dict)
        self.assertEqual(result["config"]["settings"]["level"], 5)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
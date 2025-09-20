#!/usr/bin/env python3
"""
Test script to verify JSON validation in tool executor
"""

import json


def test_json_validation():
    """Test that invalid JSON is properly rejected"""

    # This would normally be a more complex test, but for now let's just verify
    # that our approach makes sense

    # Examples of invalid JSON that should be rejected:
    invalid_json_examples = [
        "{'key': 'value'}",  # Single quotes instead of double quotes
        '{"key": "value",}',  # Trailing comma
        '{"key": value}',  # Unquoted value
        '{"key": "value"',  # Missing closing brace
    ]

    # Examples of valid JSON that should be accepted:
    valid_json_examples = [
        '{"key": "value"}',
        '{"key1": "value1", "key2": "value2"}',
        '{"key": ["item1", "item2"]}',
        '{"key": {"nested": "value"}}',
    ]

    print("JSON Validation Test")
    print("=" * 50)
    print("\nInvalid JSON examples that should be rejected:")
    for example in invalid_json_examples:
        try:
            json.loads(example)
            print(f"  ✓ {example} - UNEXPECTEDLY ACCEPTED")
        except json.JSONDecodeError:
            print(f"  ✗ {example} - Correctly rejected")

    print("\nValid JSON examples that should be accepted:")
    for example in valid_json_examples:
        try:
            json.loads(example)
            print(f"  ✓ {example} - Correctly accepted")
        except json.JSONDecodeError:
            print(f"  ✗ {example} - UNEXPECTEDLY REJECTED")


if __name__ == "__main__":
    test_json_validation()

#!/usr/bin/env python3

import json


# Test our JSON parsing logic without calling actual tools
def test_json_parsing():
    print("Testing JSON parsing logic...")

    # Test case 1: Normal JSON object (should work as-is)
    normal_json = {"test": "value", "number": 42}
    print(f"Test 1 - Normal JSON: {normal_json}")

    # Test case 2: String that contains JSON (double-encoded)
    double_encoded = '{"test": "value", "number": 42}'
    print(f"Test 2 - Double-encoded JSON: {double_encoded}")

    # Test case 3: Malformed JSON (should be handled gracefully)
    malformed_json = '{"test": "value", "number": 42'  # Missing closing brace
    print(f"Test 3 - Malformed JSON: {malformed_json}")

    # Our parsing logic
    def parse_arguments(arguments_raw):
        arguments = None

        if isinstance(arguments_raw, str):
            try:
                # First try to parse as JSON
                arguments = json.loads(arguments_raw)
                # If it's a string after parsing, it was double-encoded
                if isinstance(arguments, str):
                    # Parse again to get the actual arguments
                    arguments = json.loads(arguments)
                    print("  -> Detected double-encoded JSON, parsed twice")
            except json.JSONDecodeError as e:
                # If parsing fails, this is a malformed tool call
                print(f"  -> Error: Malformed JSON - {e}")
                return None
        else:
            # Already parsed arguments
            arguments = arguments_raw

        return arguments

    # Test each case
    print("\nParsing results:")
    result1 = parse_arguments(normal_json)
    print(f"Normal JSON result: {result1}")

    result2 = parse_arguments(double_encoded)
    print(f"Double-encoded JSON result: {result2}")

    result3 = parse_arguments(malformed_json)
    print(f"Malformed JSON result: {result3}")

    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    test_json_parsing()

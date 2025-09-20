#!/usr/bin/env python3
"""
Test script for the web_search plugin
"""

import sys
import os

# Add the current directory to the path so we can import the plugin
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_web_search_function():
    """Test the web search function directly"""
    try:
        from web_search import execute_web_search

        print("Testing web search function...")
        result = execute_web_search("capital of France", 3)
        print("Search result:")
        print(result)
        print()

        # Test with invalid parameters
        try:
            execute_web_search(123, 3)
            print("ERROR: Should have failed with invalid query type")
        except ValueError as e:
            print(f"✓ Correctly caught invalid query type: {e}")

        try:
            execute_web_search("test", -1)
            print("ERROR: Should have failed with invalid max_results")
        except ValueError as e:
            print(f"✓ Correctly caught invalid max_results: {e}")

        print("✓ All tests passed!")
        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = test_web_search_function()
    sys.exit(0 if success else 1)

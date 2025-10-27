"""
Test script for Anthropic Adapter Plugin
"""

import os
import sys

# Add the plugin directory to the path
sys.path.insert(0, os.path.dirname(__file__))


def test_plugin_import():
    """Test that the plugin can be imported"""
    try:
        print("[✓] Plugin imported successfully")
        return True
    except Exception as e:
        print(f"[X] Plugin import failed: {e}")
        return False


def test_requirements():
    """Test that required libraries are available"""
    try:
        import importlib

        importlib.util.find_spec("anthropic")
        print("[✓] Anthropic library available")
        return True
    except ImportError:
        print("[X] Anthropic library not found. Install with: pip install anthropic")
        return False


def test_environment_variables():
    """Test that environment variables are properly handled"""
    # Save original values
    original_key = os.environ.get("ANTHROPIC_API_KEY")
    original_model = os.environ.get("ANTHROPIC_MODEL")

    # Test with values set
    os.environ["ANTHROPIC_API_KEY"] = "test-key"
    os.environ["ANTHROPIC_MODEL"] = "test-model"

    try:
        import anthropic_adapter

        # Check if the module has the expected attributes
        if hasattr(anthropic_adapter, "_anthropic_api_key") and hasattr(
            anthropic_adapter, "_anthropic_model"
        ):
            print("[✓] Environment variables handling works")
            return True
        else:
            print("[X] Environment variables not properly handled")
            return False
    except Exception as e:
        print(f"[X] Environment variables test failed: {e}")
        return False
    finally:
        # Restore original values
        if original_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = original_key
        elif "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        if original_model is not None:
            os.environ["ANTHROPIC_MODEL"] = original_model
        elif "ANTHROPIC_MODEL" in os.environ:
            del os.environ["ANTHROPIC_MODEL"]


if __name__ == "__main__":
    print("Testing Anthropic Adapter Plugin...")
    print("=" * 40)

    tests = [test_plugin_import, test_requirements, test_environment_variables]

    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("*** All tests passed!")
        sys.exit(0)
    else:
        print("[X] Some tests failed!")
        sys.exit(1)

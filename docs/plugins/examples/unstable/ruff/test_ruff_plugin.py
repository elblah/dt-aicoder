#!/usr/bin/env python3
"""
Test script for the Ruff plugin functionality.

This script tests the plugin's behavior without requiring a full AI Coder instance.
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

# Add the plugin directory to Python path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

try:
    import ruff
except ImportError as e:
    print(f"Failed to import ruff plugin: {e}")
    sys.exit(1)


def test_ruff_availability():
    """Test if ruff is available on the system."""
    print("Testing ruff availability...")

    try:
        result = subprocess.run(
            ["ruff", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Ruff is available: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ruff not available")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"❌ Ruff not available: {e}")
        return False


def test_plugin_import():
    """Test if the plugin can be imported."""
    print("\nTesting plugin import...")

    try:
        # Test basic import
        print("✅ Plugin imported successfully")
        print(f"   - Version: {ruff.__version__}")

        # Test plugin info
        info = ruff.get_plugin_info()
        print(f"   - Name: {info['name']}")
        print(f"   - Version: {info['version']}")
        print(f"   - Ruff available: {info['ruff_available']}")
        print(f"   - Auto-format enabled: {info['auto_format_enabled']}")

        return True
    except Exception as e:
        print(f"❌ Plugin import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ruff_check_on_file():
    """Test ruff check functionality on a problematic Python file."""
    print("\nTesting ruff check on problematic code...")

    # Create a temporary Python file with common issues
    problematic_code = """
def hello():
    print('Hello World')
    x=1+2; y=3+4
    return x

def unused_function():
    pass
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(problematic_code)
        temp_file = f.name

    try:
        # Run ruff check directly
        check_args = ["ruff", "check", temp_file]
        result = subprocess.run(check_args, capture_output=True, text=True, timeout=30)

        if result.returncode != 0 and result.stdout.strip():
            print("✅ Ruff found issues as expected:")
            for line in result.stdout.strip().split("\n")[:5]:  # Show first 5 lines
                print(f"   - {line}")
            return True
        else:
            print("⚠️  Ruff didn't find issues (unexpected)")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Ruff check timed out")
        return False
    except Exception as e:
        print(f"❌ Error running ruff check: {e}")
        return False
    finally:
        # Clean up
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_ruff_format():
    """Test ruff format functionality."""
    print("\nTesting ruff format...")

    # Create a temporary Python file with formatting issues
    unformatted_code = """
def hello(    ):
    x=1+2
    y=3+4
    return x,y
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(unformatted_code)
        temp_file = f.name

    try:
        # Run ruff format
        format_args = ["ruff", "format", temp_file]
        result = subprocess.run(format_args, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ Ruff format succeeded")
            return True
        else:
            print(f"❌ Ruff format failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Ruff format timed out")
        return False
    except Exception as e:
        print(f"❌ Error running ruff format: {e}")
        return False
    finally:
        # Clean up
        try:
            os.unlink(temp_file)
        except OSError:
            pass


def test_environment_variables():
    """Test environment variable handling."""
    print("\nTesting environment variable handling...")

    test_values = ["1", "true", "on"]
    success = True

    for test_value in test_values:
        # Save current environment
        old_env = os.environ.get("RUFF_FORMAT")
        os.environ["RUFF_FORMAT"] = test_value

        try:
            # Re-import to test environment variable
            import importlib

            importlib.reload(ruff)

            info = ruff.get_plugin_info()
            if info["auto_format_enabled"]:
                print(f"✅ Environment variable RUFF_FORMAT={test_value} detected")
            else:
                print(f"❌ Environment variable RUFF_FORMAT={test_value} not detected")
                success = False

        except Exception as e:
            print(f"❌ Error testing environment variable {test_value}: {e}")
            success = False
        finally:
            # Restore original environment
            if old_env is not None:
                os.environ["RUFF_FORMAT"] = old_env
            elif "RUFF_FORMAT" in os.environ:
                del os.environ["RUFF_FORMAT"]

    return success


def main():
    """Run all tests."""
    print("=== Ruff Plugin Test Suite ===\n")

    tests = [
        ("Ruff Availability", test_ruff_availability),
        ("Plugin Import", test_plugin_import),
        ("Ruff Check", test_ruff_check_on_file),
        ("Ruff Format", test_ruff_format),
        ("Environment Variables", test_environment_variables),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n=== Test Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

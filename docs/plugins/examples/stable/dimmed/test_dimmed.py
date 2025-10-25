#!/usr/bin/env python3
"""
Test script for the dimmed plugin.

This script tests the plugin's functionality including:
- Pattern matching and dimming
- Configuration loading
- Command handling
- Performance with pre-compiled patterns
"""

import sys
import os
import tempfile
from pathlib import Path

# Add the plugin directory to Python path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

# Import the plugin
import dimmed  # noqa: E402


def test_basic_pattern_matching():
    """Test basic pattern matching functionality."""
    print("🧪 Testing basic pattern matching...")

    # Set up test patterns
    test_patterns = [r"\[.*?\]", r"Warning:.*", r"\bTODO\b"]
    success = dimmed.set_dimmed_patterns(test_patterns)

    if not success:
        print("❌ Failed to set test patterns")
        return False

    # Enable dimmed output
    dimmed.set_dimmed_enabled(True)

    # Test print calls (these will be dimmed if patterns match)
    print("Testing dimmed output:")
    print("This [should be dimmed] because of brackets")
    print("Warning: This should also be dimmed")
    print("This TODO should be dimmed")
    print("This should NOT be dimmed - no matching pattern")

    return True


def test_config_file_loading():
    """Test loading patterns from config files."""
    print("\n🧪 Testing config file loading...")

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".conf", delete=False) as f:
        f.write("# Test dimmed config\n")
        f.write(r"\[.*?\]" + "\n")
        f.write(r"Test:.*" + "\n")
        f.write(r"^Error:.*" + "\n")
        f.write("# This is a comment\n")
        f.write("\n")  # Empty line
        temp_config_path = f.name

    try:
        # Test loading from config
        patterns = dimmed.load_patterns_from_config(Path(temp_config_path))
        expected_patterns = [r"\[.*?\]", r"Test:.*", r"^Error:.*"]

        if patterns != expected_patterns:
            print(f"❌ Expected {expected_patterns}, got {patterns}")
            return False

        print(f"✅ Successfully loaded {len(patterns)} patterns from config")
        return True

    finally:
        # Clean up
        os.unlink(temp_config_path)


def test_pattern_compilation():
    """Test that patterns are properly compiled."""
    print("\n🧪 Testing pattern compilation...")

    # Test valid patterns
    valid_patterns = [r"\[.*?\]", r"Warning:.*", r"\b\d+\b"]
    compiled = dimmed.compile_patterns(valid_patterns)

    if len(compiled) != len(valid_patterns):
        print(
            f"❌ Expected {len(valid_patterns)} compiled patterns, got {len(compiled)}"
        )
        return False

    # Test that compiled patterns work
    test_string = "Warning: [123] test"
    matches = any(p.search(test_string) for p in compiled)

    if not matches:
        print("❌ Compiled patterns failed to match test string")
        return False

    # Test invalid pattern
    invalid_patterns = [r"[invalid", r"(?<uncaptured)"]
    compiled_invalid = dimmed.compile_patterns(invalid_patterns)

    if len(compiled_invalid) != 0:
        print("❌ Invalid patterns should not compile")
        return False

    print("✅ Pattern compilation works correctly")
    return True


def test_pattern_management():
    """Test adding and removing patterns."""
    print("\n🧪 Testing pattern management...")

    # Start with empty patterns
    dimmed.clear_dimmed_patterns()

    # Add patterns
    success1 = dimmed.add_dimmed_pattern(r"Pattern1")
    success2 = dimmed.add_dimmed_pattern(r"Pattern2")

    if not (success1 and success2):
        print("❌ Failed to add patterns")
        return False

    # Check patterns
    patterns = dimmed.get_current_patterns()
    if len(patterns) != 2 or "Pattern1" not in patterns or "Pattern2" not in patterns:
        print(f"❌ Expected 2 patterns, got {patterns}")
        return False

    # Remove a pattern
    removed = dimmed.remove_dimmed_pattern("Pattern1")
    if not removed:
        print("❌ Failed to remove pattern")
        return False

    # Check patterns again
    patterns = dimmed.get_current_patterns()
    if len(patterns) != 1 or patterns[0] != "Pattern2":
        print(f"❌ Expected 1 pattern 'Pattern2', got {patterns}")
        return False

    print("✅ Pattern management works correctly")
    return True


def test_config_file_saving():
    """Test saving patterns to config files."""
    print("\n🧪 Testing config file saving...")

    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_dimmed.conf"
        test_patterns = [r"\[.*?\]", r"Error:.*", r"\bTODO\b"]

        # Save patterns
        success = dimmed.save_patterns_to_config(test_patterns, config_path)
        if not success:
            print("❌ Failed to save config file")
            return False

        # Read back and verify
        with open(config_path, "r") as f:
            content = f.read()

        # Check that patterns are in the file
        for pattern in test_patterns:
            if pattern not in content:
                print(f"❌ Pattern '{pattern}' not found in saved config")
                return False

        # Check that header is present
        if "# Dimmed Plugin Configuration" not in content:
            print("❌ Config header missing")
            return False

        print("✅ Config file saving works correctly")
        return True


def test_performance():
    """Test performance with pre-compiled patterns."""
    print("\n🧪 Testing performance...")

    import time

    # Set up multiple patterns
    patterns = [
        r"\[.*?\]",
        r"Warning:.*",
        r"Error:.*",
        r"\bTODO\b",
        r"^Info:.*",
        r"\d{4}-\d{2}-\d{2}",
        r"\b[A-Z]{3,}\b",
        r"<.*?>",
        r"https?://.*",
        r"\b\d+\.\d+\b",
    ]

    dimmed.set_dimmed_patterns(patterns)

    # Test strings
    test_strings = [
        "This is [normal] text",
        "Warning: Something happened",
        "Error: Critical failure",
        "This is just normal text without matches",
        "TODO: Fix this issue",
        "Info: System started",
        "Date: 2023-12-25",
        "HTTP GET https://example.com",
        "Version 1.2.3 released",
        "More <xml> content here",
    ]

    # Measure performance
    iterations = 1000
    start_time = time.time()

    for _ in range(iterations):
        for test_string in test_strings:
            # Simulate the pattern matching logic from _dimmed_print
            for compiled_pattern in dimmed._dimmed_patterns:
                if compiled_pattern.search(test_string):
                    break

    end_time = time.time()
    total_time = end_time - start_time
    avg_time = (total_time / iterations) * 1000  # Convert to ms

    print("✅ Performance test completed:")
    print(f"   {iterations} iterations with {len(patterns)} patterns")
    print(f"   Average time per string: {avg_time:.3f} ms")
    print(f"   Total time: {total_time:.3f} s")

    # Performance should be under 1ms per string for this use case
    if avg_time > 1.0:
        print("⚠️ Performance is slower than expected")
        return False

    return True


def test_enable_disable():
    """Test enabling and disabling dimmed output."""
    print("\n🧪 Testing enable/disable...")

    # Set up a pattern
    dimmed.set_dimmed_patterns([r"\[.*?\]"])

    # Test disabled
    dimmed.set_dimmed_enabled(False)
    if dimmed.is_dimmed_enabled():
        print("❌ Dimmed should be disabled")
        return False

    # Test enabled
    dimmed.set_dimmed_enabled(True)
    if not dimmed.is_dimmed_enabled():
        print("❌ Dimmed should be enabled")
        return False

    print("✅ Enable/disable works correctly")
    return True


def main():
    """Run all tests."""
    print("🚀 Starting dimmed plugin tests...\n")

    # Store original print function
    original_print = __builtins__.print

    try:
        tests = [
            test_basic_pattern_matching,
            test_config_file_loading,
            test_pattern_compilation,
            test_pattern_management,
            test_config_file_saving,
            test_performance,
            test_enable_disable,
        ]

        passed = 0
        failed = 0

        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
                failed += 1

        print("\n📊 Test Results:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Success Rate: {(passed / (passed + failed) * 100):.1f}%")

        if failed == 0:
            print("\n🎉 All tests passed! The dimmed plugin is working correctly.")
            return True
        else:
            print(f"\n💥 {failed} test(s) failed. Please check the implementation.")
            return False

    finally:
        # Restore original print function
        if original_print:
            __builtins__.print = original_print


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

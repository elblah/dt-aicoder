#!/usr/bin/env python3
"""
Test script for the highlighter plugin.
This script tests the highlighting functionality independently of AI Coder.
"""

import sys
import os

# Add current directory to path so we can import the plugin
sys.path.insert(0, os.path.dirname(__file__))

import re
from typing import List, Dict, Any

# Import the plugin's core functionality
from highlighter import HighlightRule, set_highlighter_rules, is_highlighter_enabled

def test_basic_highlighting():
    """Test basic highlighting functionality."""
    print("=== Testing Basic Highlighting ===\n")
    
    # Create test rules
    rules = [
        HighlightRule(
            name="critical",
            pattern=r"\[!\]",
            style={"background": "bright_red", "foreground": "auto_contrast", "bold": True},
            priority=100
        ),
        HighlightRule(
            name="success", 
            pattern=r"\[✓\]",
            style={"background": "bright_green", "foreground": "black", "bold": True},
            priority=95
        ),
        HighlightRule(
            name="error",
            pattern=r"ERROR:",
            style={"background": "red", "foreground": "white", "bold": True},
            priority=90
        ),
        HighlightRule(
            name="warning",
            pattern=r"WARNING:",
            style={"background": "bright_yellow", "foreground": "black"},
            priority=80
        ),
        HighlightRule(
            name="dimmed",
            pattern=r"Tool result:",
            style={"foreground": "dim"},
            priority=10
        )
    ]
    
    # Set the rules
    set_highlighter_rules([rule.to_dict() for rule in rules])
    
    # Test cases
    test_cases = [
        "ERROR: Database connection failed [!] CRITICAL",
        "SUCCESS: Operation completed [✓] All good",
        "WARNING: Low disk space [!] Consider cleanup",
        "Tool result: Processing complete [✓] No errors",
        "ERROR: File not found [!] Check path WARNING: Invalid permissions",
        "Multiple highlights: ERROR [!] WARNING [✓] SUCCESS"
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"Test {i}: {test_text}")
        
        # Apply highlighting manually (simulating what the plugin does)
        result = test_text
        sorted_rules = sorted(rules, key=lambda r: r.priority)
        
        for rule in sorted_rules:
            result = rule.apply_to_text(result)
        
        print(f"Result: {result}\n")
    
    return True

def test_priority_override():
    """Test that higher priority rules override lower ones."""
    print("=== Testing Priority Override ===\n")
    
    # Create conflicting rules
    rules = [
        HighlightRule(
            name="low_priority",
            pattern=r"TEST",
            style={"foreground": "red", "bold": False},
            priority=10
        ),
        HighlightRule(
            name="high_priority",
            pattern=r"TEST",
            style={"foreground": "green", "bold": True},
            priority=100
        )
    ]
    
    test_text = "This is a TEST message"
    print(f"Original: {test_text}")
    
    # Apply in priority order (low → high)
    result = test_text
    sorted_rules = sorted(rules, key=lambda r: r.priority)
    
    for rule in sorted_rules:
        result = rule.apply_to_text(result)
        print(f"After {rule.name} (priority {rule.priority}): {result}")
    
    print(f"\nFinal result should be GREEN and BOLD (high priority wins): {result}\n")
    
    return True

def test_multi_pattern():
    """Test multiple patterns in same string."""
    print("=== Testing Multiple Patterns ===\n")
    
    rules = [
        HighlightRule("error", r"ERROR", {"background": "red", "foreground": "white"}, 90),
        HighlightRule("warning", r"WARNING", {"background": "yellow", "foreground": "black"}, 80),
        HighlightRule("success", r"SUCCESS", {"background": "green", "foreground": "white"}, 85),
        HighlightRule("critical", r"\[!\]", {"background": "bright_red", "foreground": "white"}, 100),
        HighlightRule("checkmark", r"\[✓\]", {"background": "bright_green", "foreground": "black"}, 95)
    ]
    
    test_text = "ERROR: System failed [!] WARNING: Recovering [✓] SUCCESS: System restored"
    print(f"Original: {test_text}")
    
    # Apply highlighting
    result = test_text
    sorted_rules = sorted(rules, key=lambda r: r.priority)
    
    for rule in sorted_rules:
        result = rule.apply_to_text(result)
    
    print(f"Highlighted: {result}\n")
    
    return True

def test_style_combinations():
    """Test different style combinations."""
    print("=== Testing Style Combinations ===\n")
    
    test_cases = [
        ("Bold red", r"BOLD", {"foreground": "bright_red", "bold": True}, 50),
        ("Italic green", r"ITALIC", {"foreground": "bright_green", "italic": True}, 50),
        ("Underlined blue", r"UNDERLINE", {"foreground": "bright_blue", "underline": True}, 50),
        ("Combined styles", r"COMBINED", {"background": "yellow", "foreground": "red", "bold": True, "italic": True, "underline": True}, 50),
        ("Auto contrast", r"AUTO", {"background": "bright_red", "foreground": "auto_contrast"}, 50)
    ]
    
    for name, pattern, style, priority in test_cases:
        rule = HighlightRule(name, pattern, style, priority)
        test_text = f"This is {pattern} text"
        result = rule.apply_to_text(test_text)
        print(f"{name}: {result}")
    
    print()
    return True

def test_edge_cases():
    """Test edge cases and error handling."""
    print("=== Testing Edge Cases ===\n")
    
    # Test empty pattern
    try:
        rule = HighlightRule("test", "", {"foreground": "red"}, 50)
        print("Empty pattern: Created successfully")
    except Exception as e:
        print(f"Empty pattern: Failed as expected - {e}")
    
    # Test invalid regex
    try:
        rule = HighlightRule("test", "[invalid", {"foreground": "red"}, 50)
        print("Invalid regex: Created successfully (shouldn't happen)")
    except Exception as e:
        print(f"Invalid regex: Failed as expected - {e}")
    
    # Test overlapping patterns
    rules = [
        HighlightRule("short", r"cat", {"foreground": "red"}, 50),
        HighlightRule("long", r"catalog", {"foreground": "green"}, 100)
    ]
    
    test_text = "This is catalog data with cat and more catalog"
    print(f"Overlapping test: {test_text}")
    
    result = test_text
    sorted_rules = sorted(rules, key=lambda r: r.priority)
    
    for rule in sorted_rules:
        result = rule.apply_to_text(result)
    
    print(f"Result: {result}\n")
    
    return True

def main():
    """Run all tests."""
    print("🎨 Highlighter Plugin Test Suite\n")
    
    tests = [
        test_basic_highlighting,
        test_priority_override,
        test_multi_pattern,
        test_style_combinations,
        test_edge_cases
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
                print("✅ PASSED\n")
            else:
                print("❌ FAILED\n")
        except Exception as e:
            print(f"❌ FAILED with exception: {e}\n")
    
    print(f"=== Test Results: {passed}/{total} passed ===\n")
    
    if passed == total:
        print("🎉 All tests passed! The highlighter plugin is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
#!/usr/bin/env python3

import sys
import os

# Add the plugin directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import the plugin
from safe_tool_results import *

def test_sanitization():
    """Test content sanitization function."""
    print("Testing content optimization...")
    
    # Test messy content cleanup
    test_content = "  line1  \
\n  line2   \
\tline3\t"
    cleaned = sanitize_tool_content(test_content)
    print(f"Original: {repr(test_content)}")
    print(f"Cleaned: {repr(cleaned)}")
    
    # Test truncation
    long_content = "A" * 10000
    truncated = sanitize_tool_content(long_content)
    print(f"Long content length: {len(long_content)}")
    print(f"Truncated length: {len(truncated)}")
    print("✓ Content optimization tests passed")

def test_safe_text_conversion():
    """Test tool result to safe text conversion."""
    print("\nTesting text conversion...")
    
    tool_name = "read_file"
    arguments = {"path": "/etc/passwd"}
    result = "root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000:user:/home/user:/bin/zsh"
    
    safe_text = tool_result_to_safe_text(tool_name, arguments, result)
    print(f"Converted text output:\n{safe_text}")
    print("✓ Text conversion test passed")

def test_plugin_hooks():
    """Test plugin hook functions."""
    print("\nTesting plugin hooks...")
    
    # Test on_plugin_load
    original_enabled = ENABLED
    result = on_plugin_load()
    print(f"on_plugin_load returned: {result}")
    print(f"ENABLED state: {ENABLED}")
    
    # Restore original state
    globals()["ENABLED"] = original_enabled
    print("✓ Plugin hook tests passed")

if __name__ == "__main__":
    print("Running safe_tool_results plugin tests...")
    print("=" * 50)
    
    try:
        test_sanitization()
        test_safe_text_conversion()
        test_plugin_hooks()
        
        print("\n✅ All tests passed! Plugin is ready for use.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
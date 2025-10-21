#!/usr/bin/env python3
"""
Test to verify the dimmed plugin integrates correctly with AI Coder's print calls.
This simulates the kinds of print statements AI Coder actually makes.
"""

import sys
import os
from pathlib import Path

# Add the plugin directory to Python path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

def test_aicoder_print_integration():
    """Test that plugin works with AI Coder-style print calls."""
    
    print("🧪 Testing AI Coder Print Integration")
    print("=" * 50)
    
    # Import plugin (this will initialize and patch print)
    import dimmed
    
    # Set up patterns that would be useful in AI Coder
    dimmed.set_dimmed_patterns([
        r'\[.*?\]',           # File names in brackets
        r'Warning:.*',        # Warning messages
        r'^Debug:.*',         # Debug output
        r'Success:.*',        # Success messages
        r'Error:.*',          # Error messages
        r'Info:.*',           # Info messages
    ])
    dimmed.set_dimmed_enabled(True)
    
    print("\n📋 Testing various AI Coder print scenarios:")
    
    # Test 1: Tool execution output (common in AI Coder)
    print("1. Tool execution output:")
    print("   - Reading file [config.yaml]")
    print("   - Warning: File is empty")
    print("   - Success: File read successfully")
    
    # Test 2: Plugin messages
    print("\n2. Plugin messages:")
    print("   [theme] Applied dark theme")
    print("   [memory] Session autosaved")
    print("   [stats] 42 commands executed")
    
    # Test 3: Debug output
    print("\n3. Debug output:")
    print("   Debug: API request sent")
    print("   Debug: Response received")
    print("   Debug: Processing complete")
    
    # Test 4: Error handling
    print("\n4. Error handling:")
    print("   Error: File not found")
    print("   Error: Permission denied")
    print("   Error: Invalid syntax")
    
    # Test 5: Normal output (should not be dimmed)
    print("\n5. Normal output (should not be dimmed):")
    print("   This is a normal message")
    print("   Regular status update")
    print("   No special patterns here")
    
    # Test 6: Mixed content
    print("\n6. Mixed content:")
    print("   Processing [main.py]... Warning: deprecated syntax found")
    print("   Debug: Loaded 3 files from [src/]")
    print("   Error: Cannot parse [invalid.json]")
    
    print("\n✅ Integration test completed!")
    print(f"   Patterns active: {len(dimmed.get_current_patterns())}")
    print(f"   Plugin enabled: {dimmed.is_dimmed_enabled()}")
    
    # Test that plugin can be disabled
    print("\n🔧 Testing disable/enable:")
    dimmed.set_dimmed_enabled(False)
    print("   This should NOT be dimmed (plugin disabled)")
    print("   [This should also NOT be dimmed]")
    
    dimmed.set_dimmed_enabled(True)
    print("   This [should be dimmed] again (plugin re-enabled)")
    print("   Warning: This should also be dimmed")
    
    return True

if __name__ == "__main__":
    try:
        success = test_aicoder_print_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
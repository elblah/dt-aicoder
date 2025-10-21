#!/usr/bin/env python3
"""
Demo script showing the dimmed plugin in action.
"""

import sys
import os
from pathlib import Path

# Add the plugin directory to Python path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

# Import and initialize the plugin
import dimmed

def demo():
    """Demonstrate the dimmed plugin functionality."""
    
    # Store original print to avoid recursion
    original_print = __builtins__.print
    
    # Initialize the plugin (this monkey patches print)
    dimmed.initialize_dimmed_plugin()
    
    # Use original print for setup to avoid recursion
    original_print("🎬 Dimmed Plugin Demo")
    original_print("=" * 50)
    
    # Set up some demo patterns
    demo_patterns = [
        r'\[.*?\]',           # Text in brackets
        r'Warning:.*',        # Warning messages
        r'\bTODO\b',          # TODO items
        r'^Info:.*',          # Info messages
        r'^Error:.*'          # Error messages
    ]
    
    dimmed.set_dimmed_patterns(demo_patterns)
    dimmed.set_dimmed_enabled(True)
    
    # Use original print for status info
    original_print(f"\n📝 Current patterns: {len(dimmed.get_current_patterns())}")
    for i, pattern in enumerate(dimmed.get_current_patterns(), 1):
        original_print(f"   {i}. {pattern}")
    
    original_print(f"\n🔅 Dimmed enabled: {dimmed.is_dimmed_enabled()}")
    original_print("\n" + "=" * 50)
    original_print("DEMO OUTPUT:")
    original_print("=" * 50)
    
    print(f"\n📝 Current patterns: {len(dimmed.get_current_patterns())}")
    for i, pattern in enumerate(dimmed.get_current_patterns(), 1):
        print(f"   {i}. {pattern}")
    
    print(f"\n🔅 Dimmed enabled: {dimmed.is_dimmed_enabled()}")
    print("\n" + "=" * 50)
    print("DEMO OUTPUT:")
    print("=" * 50)
    
    # These should be dimmed (matching patterns)
    print("This [text in brackets] should be dimmed")
    print("Warning: This warning should be dimmed")
    print("TODO: This TODO should be dimmed")
    print("Info: This info should be dimmed")
    print("Error: This error should be dimmed")
    
    print("\n--- Normal output (should not be dimmed) ---")
    # These should NOT be dimmed (no pattern matches)
    print("This is normal text")
    print("Regular output without special patterns")
    print("Just plain text here")
    
    print("\n--- Mixed examples ---")
    print("Normal text [but this part] should be dimmed")
    print("Warning: entire line dimmed even with [brackets]")
    print("Mixed TODO and normal text")
    
    print("\n--- Testing disable/enable ---")
    dimmed.set_dimmed_enabled(False)
    print("This [should NOT be dimmed] because dimmed is disabled")
    
    dimmed.set_dimmed_enabled(True)
    print("This [SHOULD be dimmed] because dimmed is re-enabled")
    
    print("\n" + "=" * 50)
    print("✅ Demo completed!")
    print("Notice how matching text appears dimmed in your terminal.")

if __name__ == "__main__":
    demo()
#!/usr/bin/env python3
"""
Simple demo of the dimmed plugin without initialization conflicts.
"""

# Import without initializing by mocking the environment
import os
os.environ['AICODER_DIMMED_PATTERNS'] = r'\[.*?\],Warning:.*,TODO'

# Now import the plugin
import sys
from pathlib import Path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

# Import after setting environment
import dimmed

# Manually set up patterns without full initialization
dimmed.set_dimmed_patterns([r'\[.*?\]', r'Warning:.*', r'TODO'])
dimmed.set_dimmed_enabled(True)

print("🎬 Simple Dimmed Plugin Demo")
print("=" * 50)

# These should be dimmed (matching patterns)
print("This [text in brackets] should be dimmed")
print("Warning: This warning should be dimmed") 
print("TODO: This TODO should be dimmed")

print("\n--- Normal output (should not be dimmed) ---")
# These should NOT be dimmed (no pattern matches)
print("This is normal text")
print("Regular output without special patterns")

print("\n--- Mixed examples ---")
print("Normal text [but this part] should be dimmed")
print("Warning: entire line dimmed even with normal text")

print("\n✅ Demo completed!")
print("Notice how matching text appears dimmed in your terminal.")
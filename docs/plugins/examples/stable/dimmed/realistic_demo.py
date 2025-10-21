#!/usr/bin/env python3
"""
Realistic demo showing what the dimmed plugin actually affects in AI Coder.
This demonstrates the standard print() calls that get dimmed.
"""

import sys
from pathlib import Path

# Add the plugin directory to Python path
plugin_dir = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

# Import and set up the plugin
import dimmed

def demo_realistic_usage():
    """Demonstrate what actually gets dimmed in AI Coder."""
    
    # Initialize plugin
    dimmed.set_dimmed_patterns([
        r'\[.*?\]',           # Text in brackets (like file names)
        r'Warning:.*',        # Warning messages
        r'\bTODO\b',          # TODO items
        r'^Info:.*',          # Info messages
        r'^Error:.*',         # Error messages
        r'Debug:.*',          # Debug output
        r'Success:.*',        # Success messages
    ])
    dimmed.set_dimmed_enabled(True)
    
    print("🎬 Realistic AI Coder Usage Demo")
    print("=" * 50)
    print("This shows what actually gets dimmed by the plugin:")
    print("(AI responses themselves are NOT affected)")
    print()
    
    # Simulate tool execution output
    print("🔧 Tool Execution Output:")
    print("Executing command: [ls -la]")
    print("Warning: File already exists, skipping")
    print("Success: Operation completed successfully")
    print("Error: Permission denied")
    print()
    
    # Simulate command handler output
    print("💬 Command Handler Output:")
    print("Info: Loading configuration from [config.yaml]")
    print("Debug: Plugin initialization complete")
    print("TODO: Implement error handling")
    print()
    
    # Simulate plugin messages
    print("🔌 Plugin Messages:")
    print("[theme] Applied theme: dark-mode")
    print("[memory] Autosave enabled")
    print("[stats] Session duration: 00:15:32")
    print()
    
    # Simulate status messages
    print("📊 Status Messages:")
    print("Connection: [established]")
    print("API rate limit: [120/1000 requests]")
    print("Memory usage: [256MB]")
    print()
    
    # Show what doesn't get dimmed (AI responses)
    print("🤖 AI Response (NOT AFFECTED):")
    print("I'll help you with that task. First, let me check the current")
    print("directory structure and then we can proceed with the implementation.")
    print()
    
    # Show mixed content
    print("🔀 Mixed Content Examples:")
    print("Processing file [main.py]... done")
    print("Found TODO items in [utils.py] - please review")
    print("Warning: [deprecated.py] uses outdated syntax")
    print()
    
    print("✅ Demo completed!")
    print()
    print("📝 Summary:")
    print("- Tool output, commands, and plugin messages get dimmed")
    print("- AI responses remain normal (streaming bypasses print)")
    print("- This is intentional to preserve streaming functionality")
    print(f"- Current patterns: {len(dimmed.get_current_patterns())}")
    print("- Use /dimmed command to configure patterns")

if __name__ == "__main__":
    demo_realistic_usage()
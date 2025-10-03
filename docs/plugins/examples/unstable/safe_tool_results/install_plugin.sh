#!/bin/bash
# Install script for safe_tool_results plugin

PLUGIN_NAME="safe_tool_results"
PLUGIN_DIR="$HOME/.config/aicoder/plugins"

# Create plugins directory if it doesn't exist
mkdir -p "$PLUGIN_DIR"

# Copy the plugin file
cp "safe_tool_results.py" "$PLUGIN_DIR/"

echo "✅ $PLUGIN_NAME plugin installed to $PLUGIN_DIR/"
echo ""
echo "To use the plugin, restart AI Coder or run:"
echo "AICODER_SAFE_TOOL_RESULTS=1 aicoder"
echo ""
echo "Or use the command inside AI Coder:"
echo "/safetool on"
echo ""
echo "Plugin features:"
echo "- Converts tool results to plain text messages"
echo "- Prevents JSON pattern pollution in context"
echo "- Sanitizes problematic content patterns"
echo "- Toggle with /safetool command"
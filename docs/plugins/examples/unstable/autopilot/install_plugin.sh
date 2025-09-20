#!/bin/bash

# Autopilot Plugin Installation Script

PLUGIN_NAME="autopilot"
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AICODER_DIR="$(dirname "$PLUGIN_DIR")/../../.."

echo "Installing $PLUGIN_NAME plugin..."

# Check if we're in the right directory
if [ ! -f "$AICODER_DIR/aicoder.py" ]; then
    echo "Error: This script must be run from the AI Coder plugins directory."
    echo "Please run it from: docs/plugins/examples/unstable/$PLUGIN_NAME/"
    exit 1
fi

# Create symlink to plugin directory
PLUGIN_TARGET="$AICODER_DIR/plugins/$PLUGIN_NAME"
PLUGIN_SOURCE="$PLUGIN_DIR"

# Create plugins directory if it doesn't exist
mkdir -p "$AICODER_DIR/plugins"

# Remove existing symlink if it exists
if [ -L "$PLUGIN_TARGET" ]; then
    rm "$PLUGIN_TARGET"
fi

# Create symlink
ln -sf "$PLUGIN_SOURCE" "$PLUGIN_TARGET"

echo "Plugin $PLUGIN_NAME installed successfully!"
echo "To use the plugin, run AI Coder with:"
echo "  python aicoder.py --plugin $PLUGIN_NAME"
echo ""
echo "Or to load all plugins:"
echo "  python aicoder.py --plugin all"
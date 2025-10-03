#!/bin/bash
# Install script for char_filter plugin

PLUGIN_NAME="char_filter"
PLUGIN_DIR="$HOME/.config/aicoder/plugins"

# Create plugins directory if it does not exist
mkdir -p "$PLUGIN_DIR"

# Copy the plugin file
cp "char_filter.py" "$PLUGIN_DIR/"

echo "Character filter plugin installed to $PLUGIN_DIR/"
echo ""
echo "The plugin will filter ALL message content to prevent these character ranges:"
echo "- Chinese (\u4e00-\u9fff)"
echo "- Cyrillic (\u0400-\u04FF)"
echo "- Arabic (\u0600-\u06FF)"
echo "- Devanagari (\u0900-\u097F)"
echo "- Hangul (\u1100-\u11FF)"
echo ""
echo "No problematic characters will enter the message history context."

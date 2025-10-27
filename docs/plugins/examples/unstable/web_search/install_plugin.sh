#!/bin/bash

# Web Search Plugin Installation Script

PLUGIN_NAME="web_search"
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.config/aicoder/plugins"

echo "Installing $PLUGIN_NAME plugin..."

# Create plugins directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Copy plugin files
cp -r "$PLUGIN_DIR/$PLUGIN_NAME" "$INSTALL_DIR/"

if [ $? -eq 0 ]; then
    echo "[✓] $PLUGIN_NAME plugin installed successfully!"
    echo "   The plugin will be automatically loaded when you run AI Coder"
    echo "   To uninstall, run: rm -rf \"$INSTALL_DIR/$PLUGIN_NAME\""
else
    echo "[X] Failed to install $PLUGIN_NAME plugin"
    exit 1
fi
#!/bin/bash

# Installation script for Planning Plugin

echo "🚀 Installing Planning Plugin for AI Coder..."

# Get the directory where this script is located
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AICODER_DIR="$HOME/.config/aicoder"

# Create plugins directory if it doesn't exist
echo "📁 Creating plugins directory..."
mkdir -p "$AICODER_DIR/plugins"

# Copy the plugin files
echo "📋 Copying plugin files..."
cp -r "$PLUGIN_DIR" "$AICODER_DIR/plugins/"

# Check if installation was successful
if [ -d "$AICODER_DIR/plugins/planning_plugin" ]; then
    echo "✅ Planning plugin installed successfully!"
    echo ""
    echo "📖 Usage:"
    echo "   /plan      - Start planning mode"
    echo "   /showplan  - Display current plan"
    echo "   /approveplan - Approve and execute plan"
    echo "   /endplan   - Exit planning mode"
    echo ""
    echo "🔧 Location: $AICODER_DIR/plugins/planning_plugin/"
    echo ""
    echo "🚀 Restart AI Coder to start using the plugin!"
else
    echo "❌ Installation failed. Please check permissions."
    exit 1
fi

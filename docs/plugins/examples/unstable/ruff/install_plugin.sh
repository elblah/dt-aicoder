#!/bin/bash

# Install script for the Ruff plugin
# This script installs the ruff tool and copies the plugin to the correct location

set -e

echo "🚀 Installing Ruff Plugin for AI Coder..."

# Check if we're in the right directory
if [ ! -f "ruff.py" ]; then
    echo "❌ Error: ruff.py not found. Please run this script from the plugin directory."
    exit 1
fi

# Create plugin directory if it doesn't exist
PLUGIN_DIR="$HOME/.config/aicoder/plugins"
echo "📁 Creating plugin directory: $PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR"

# Copy the plugin
echo "📋 Copying plugin to $PLUGIN_DIR"
cp ruff.py "$PLUGIN_DIR/"

# Check if ruff is installed
echo "🔍 Checking if ruff is installed..."
if ! command -v ruff &> /dev/null; then
    echo "⚠️  Ruff is not installed. Installing ruff..."
    
    # Try to install ruff
    if command -v pip &> /dev/null; then
        pip install ruff
    elif command -v pip3 &> /dev/null; then
        pip3 install ruff
    else
        echo "❌ Error: pip not found. Please install ruff manually:"
        echo "   pip install ruff"
        exit 1
    fi
else
    echo "✅ Ruff is already installed"
    ruff --version
fi

# Verify installation
echo "🔧 Verifying plugin installation..."
if [ -f "$PLUGIN_DIR/ruff.py" ]; then
    echo "✅ Plugin installed successfully"
else
    echo "❌ Error: Plugin installation failed"
    exit 1
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "📝 Usage Notes:"
echo "   - The plugin will activate automatically when you start AI Coder"
echo "   - It will check Python files for issues when you save/edit them"
echo "   - Set RUFF_FORMAT=true to enable auto-formatting"
echo ""
echo "🔧 Configuration Options:"
echo "   export RUFF_FORMAT=1                      # Enable auto-formatting (also accepts true/on)"
echo "   export RUFF_CHECK_ARGS='--config=...\"     # Custom ruff check args"
echo "   export RUFF_FORMAT_ARGS='--config=...'    # Custom ruff format args"
echo ""
echo "🧪 Test the plugin:"
echo "   python3 test_ruff_plugin.py"
echo ""
echo "📖 For more information, see README.md"
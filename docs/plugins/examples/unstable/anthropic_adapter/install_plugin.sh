#!/bin/bash

# Anthropic Adapter Plugin Installation Script

echo "Installing Anthropic Adapter Plugin..."

# Check if we're in the right directory
if [ ! -f "anthropic_adapter.py" ]; then
    echo "Error: This script must be run from the anthropic_adapter directory"
    exit 1
fi

# Check if pip is available
if ! command -v pip &> /dev/null; then
    echo "Error: pip is not installed"
    exit 1
fi

# Install anthropic library
echo "Installing anthropic library..."
pip install anthropic

# Check if installation was successful
if ! python -c "import anthropic" &> /dev/null; then
    echo "Error: Failed to install anthropic library"
    exit 1
fi

echo "Anthropic library installed successfully!"

# Show installation instructions
echo ""
echo "✅ Installation complete!"
echo ""
echo "To use this plugin:"
echo "1. Copy this directory to your AI Coder plugins directory:"
echo "   cp -r . ~/.config/aicoder/plugins/anthropic_adapter"
echo ""
echo "2. Set your Anthropic API key:"
echo "   export ANTHROPIC_API_KEY='your-api-key-here'"
echo ""
echo "3. Optionally specify a model:"
echo "   export ANTHROPIC_MODEL='claude-3-opus-20240229'"
echo ""
echo "4. Run AI Coder:"
echo "   python -m aicoder"
echo ""
echo "For more information, see README.md"
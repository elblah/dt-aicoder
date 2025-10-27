#!/bin/bash

# Auto Retry Plugin Installation Script

echo "Installing Auto Retry Plugin..."

# Get the plugin directory
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AICODER_DIR="$(dirname "$(dirname "$(dirname "$(dirname "$PLUGIN_DIR")")")")"

echo "Plugin directory: $PLUGIN_DIR"
echo "AI Coder directory: $AICODER_DIR"

# Check if we're in the right place
if [ ! -f "$AICODER_DIR/aicoder/__init__.py" ]; then
    echo "[X] Error: Could not find AI Coder installation at $AICODER_DIR"
    echo "Please run this script from the plugin directory within the AI Coder project."
    exit 1
fi

# Create plugins directory if it doesn't exist
PLUGINS_DIR="$AICODER_DIR/plugins"
if [ ! -d "$PLUGINS_DIR" ]; then
    echo "Creating plugins directory..."
    mkdir -p "$PLUGINS_DIR"
fi

# Copy the plugin to the plugins directory
echo "Copying plugin to plugins directory..."
cp -r "$PLUGIN_DIR" "$PLUGINS_DIR/"

# Create a symlink in the aicoder directory for easier importing
if [ ! -L "$AICODER_DIR/aicoder/auto_retry" ]; then
    echo "Creating symlink in aicoder directory..."
    ln -sf "$PLUGINS_DIR/auto_retry" "$AICODER_DIR/aicoder/auto_retry"
fi

# Test the plugin
echo "Testing plugin..."
cd "$AICODER_DIR"
if python -c "import sys; sys.path.insert(0, 'plugins'); import auto_retry; print('[✓] Plugin test successful')" 2>/dev/null; then
    echo "[✓] Auto Retry Plugin installed successfully!"
    echo ""
    echo "Usage:"
    echo "   The plugin will automatically work when you run AI Coder"
    echo "   Configure with environment variables:"
    echo "   - AUTO_RETRY_DELAY=5       # Delay between retries in seconds"
    echo "   - AUTO_RETRY_MAX_RETRIES=3  # Maximum number of retries"
    echo ""
    echo "Configuration:"
    echo "   Add these to your ~/.bashrc or ~/.zshrc:"
    echo "   export AUTO_RETRY_DELAY=5"
    echo "   export AUTO_RETRY_MAX_RETRIES=3"
    echo ""
    echo "Run AI Coder:"
    echo "   cd $AICODER_DIR && python -m aicoder"
else
    echo "[X] Plugin test failed. Please check the installation."
    exit 1
fi
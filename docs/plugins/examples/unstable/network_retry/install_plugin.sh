#!/bin/bash

# Network Retry Plugin Installation Script

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_NAME="network_retry"

echo "Installing $PLUGIN_NAME plugin..."

# Check if we're in the right directory
if [[ ! -f "$PLUGIN_DIR/$PLUGIN_NAME.py" ]]; then
    echo "Error: Cannot find plugin files. Please run this script from the plugin directory."
    exit 1
fi

# Check if AI Coder is installed
if ! python -c "import aicoder" 2>/dev/null; then
    echo "Warning: AI Coder not found in Python path. Plugin may not work correctly."
fi

# Show installation instructions
echo ""
echo "✅ Plugin files are ready in: $PLUGIN_DIR"
echo ""
echo "To use this plugin with AI Coder, add it to your plugins configuration."
echo "You can configure retry behavior with these environment variables:"
echo ""
echo "  export NETWORK_RETRY_500=3     # Number of retries for 500 errors"
echo "  export NETWORK_RETRY_502=-1    # Infinite retry for 502 errors"
echo "  export NETWORK_RETRY_503=3     # Number of retries for 503 errors"
echo "  export NETWORK_RETRY_504=3     # Number of retries for 504 errors"
echo "  export NETWORK_RETRY_DELAY=1   # Initial delay in seconds"
echo "  export NETWORK_RETRY_MAX_DELAY=60  # Maximum delay in seconds"
echo ""
echo "Example usage:"
echo "  export NETWORK_RETRY_502=-1  # Retry 502 errors infinitely"
echo "  python -m aicoder"
echo ""
echo "For more information, see the README.md file in this directory."
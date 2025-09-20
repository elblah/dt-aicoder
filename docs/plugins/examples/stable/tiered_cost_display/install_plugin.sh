#!/bin/bash
# Installation script for the tiered cost display plugin

PLUGIN_DIR="./docs/examples/stable/tiered_cost_display"
PLUGIN_FILE="tiered_cost_display_plugin.py"

# Check if we're in the right directory
if [ ! -f "$PLUGIN_DIR/$PLUGIN_FILE" ]; then
    echo "Error: Plugin file not found. Please run this script from the aicoder root directory."
    exit 1
fi

echo "Installing tiered cost display plugin..."

# Create plugins directory if it doesn't exist
mkdir -p ./plugins

# Copy the plugin to the plugins directory
cp "$PLUGIN_DIR/$PLUGIN_FILE" ./plugins/

echo "Plugin installed to ./plugins/$PLUGIN_FILE"

# Create a sample configuration file
cat > ./tiered_cost_plugin.conf << EOF
# Tiered Cost Display Plugin Configuration
# Uncomment and modify the following lines to customize the plugin

# Enable or disable the plugin
# TIERED_COST_PLUGIN_ENABLED=true

# Path to save cost data (will be created if it doesn't exist)
# TIERED_COST_DATA_FILE=./cost_data.txt

# Example usage:
# TIERED_COST_PLUGIN_ENABLED=true TIERED_COST_DATA_FILE=./my_costs.txt python -m aicoder
EOF

echo "Configuration template created at ./tiered_cost_plugin.conf"

echo ""
echo "To use the plugin:"
echo "1. Load it with: python -m aicoder --load-plugin ./plugins/$PLUGIN_FILE"
echo "2. Or set the PYTHONPATH to include the plugins directory"
echo "3. Or copy it to your Python path"
echo ""
echo "To configure the plugin, set these environment variables:"
echo "  TIERED_COST_PLUGIN_ENABLED=true|false"
echo "  TIERED_COST_DATA_FILE=./path/to/cost_data.txt"
echo ""
echo "Example:"
echo "  TIERED_COST_PLUGIN_ENABLED=true TIERED_COST_DATA_FILE=./costs.txt python -m aicoder"
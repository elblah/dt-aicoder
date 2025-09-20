#!/bin/bash
# install_plugin.sh - Example installation script for the context summary plugin

# Check if AICoder plugins directory is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <aicoder_plugins_directory>"
  echo "Example: $0 ~/.aicoder/plugins"
  exit 1
fi

# Get the plugins directory
PLUGINS_DIR="$1"

# Check if the directory exists
if [ ! -d "$PLUGINS_DIR" ]; then
  echo "Error: Directory $PLUGINS_DIR does not exist"
  exit 1
fi

# Copy the plugin file
cp context_summary.py "$PLUGINS_DIR/"

# Check if copy was successful
if [ $? -eq 0 ]; then
  echo "✅ Context Summary plugin installed successfully to $PLUGINS_DIR"
  echo "The plugin will be automatically loaded when AICoder starts"
else
  echo "❌ Failed to install plugin"
  exit 1
fi
#!/bin/bash
# AI Coder Uninstallation Script
#
# This script removes AI Coder installation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default installation paths
DEFAULT_BIN_DIR="$HOME/.local/bin"
DEFAULT_CONFIG_DIR="$HOME/.config/aicoder"

echo -e "${BLUE}=== AI Coder Uninstallation Script ===${NC}"
echo

# Ask user for installation directory
echo -e "${BLUE}Where are the launcher scripts installed?${NC}"
echo "Press Enter for default ($DEFAULT_BIN_DIR) or enter custom path:"
read -r BIN_DIR
BIN_DIR=${BIN_DIR:-$DEFAULT_BIN_DIR}

echo
echo -e "${YELLOW}This will remove:${NC}"
echo "  - Launcher scripts from $BIN_DIR"
echo "  - Zipapp from $DEFAULT_CONFIG_DIR"
echo "  - Plugin directory $DEFAULT_CONFIG_DIR/plugins"
echo

echo -e "${BLUE}Are you sure you want to uninstall? (y/N):${NC}"
read -r CONFIRM

if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

# Remove launcher scripts
echo "Removing launcher scripts..."
for script in aicoder-start aicoder-gemini aicoder-openai aicoder-glm aicoder-cerebras aicoder-qwen; do
    if [ -f "$BIN_DIR/$script" ]; then
        rm "$BIN_DIR/$script"
        echo -e "${GREEN}  ✓ Removed $script${NC}"
    fi
done

# Remove zipapp
if [ -f "$DEFAULT_CONFIG_DIR/aicoder.pyz" ]; then
    rm "$DEFAULT_CONFIG_DIR/aicoder.pyz"
    echo -e "${GREEN}  ✓ Removed zipapp${NC}"
fi

# Remove plugins directory
if [ -d "$DEFAULT_CONFIG_DIR/plugins" ]; then
    rm -rf "$DEFAULT_CONFIG_DIR/plugins"
    echo -e "${GREEN}  ✓ Removed plugins directory${NC}"
fi

# Remove config directory if empty
if [ -d "$DEFAULT_CONFIG_DIR" ] && [ -z "$(ls -A "$DEFAULT_CONFIG_DIR")" ]; then
    rmdir "$DEFAULT_CONFIG_DIR"
    echo -e "${GREEN}  ✓ Removed config directory${NC}"
fi

echo
echo -e "${GREEN}=== Uninstallation Complete ===${NC}"
echo
echo "Note: This script does not remove:"
echo "  - Any PATH modifications you may have made"
echo "  - firejail or other system dependencies"
echo
echo -e "${GREEN}AI Coder has been uninstalled.${NC}"
#!/bin/bash
# AI Coder Installation Script
#
# This script installs AI Coder with the following features:
# - Builds and installs the zipapp version
# - Installs launcher scripts with proper paths
# - Checks for required dependencies (firejail)
# - Asks user where to install scripts
# - Suggests stable plugins for installation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default installation paths
DEFAULT_BIN_DIR="$HOME/.local/bin"
DEFAULT_CONFIG_DIR="$HOME/.config/aicoder"
ZIPAPP_PATH="$SCRIPT_DIR/aicoder.pyz"

echo -e "${BLUE}=== AI Coder Installation Script ===${NC}"
echo

# Check if we're in the right directory
if [ ! -f "$SCRIPT_DIR/aicoder.py" ] || [ ! -d "$SCRIPT_DIR/aicoder" ]; then
    echo -e "${RED}Error: This script must be run from the AI Coder root directory${NC}"
    echo "Please cd to the directory containing aicoder.py and aicoder/ folder"
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found${NC}"

# Check for firejail
FIREJAIL_INSTALLED=true
if ! command -v firejail &> /dev/null; then
    echo -e "${YELLOW}Note: firejail is not installed${NC}"
    echo "The launcher scripts will automatically run without sandboxing"
    echo "To enable sandboxing, please install firejail:"
    echo "  Ubuntu/Debian: sudo apt install firejail"
    echo "  Fedora: sudo dnf install firejail"
    echo "  Arch: sudo pacman -S firejail"
    echo
    FIREJAIL_INSTALLED=false
fi

# Ask user for installation directory
echo -e "${BLUE}Where would you like to install the launcher scripts?${NC}"
echo "Press Enter for default ($DEFAULT_BIN_DIR) or enter a custom path:"
read -r BIN_DIR
BIN_DIR=${BIN_DIR:-$DEFAULT_BIN_DIR}

# Create installation directory
mkdir -p "$BIN_DIR"

# Build zipapp
echo
echo -e "${BLUE}Building zipapp version...${NC}"
python3 "$SCRIPT_DIR/build_zipapp.py"

if [ ! -f "$ZIPAPP_PATH" ]; then
    echo -e "${RED}Error: Failed to build zipapp${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Zipapp built successfully${NC}"

# Install launcher scripts
echo
echo -e "${BLUE}Installing launcher scripts...${NC}"

# Copy zipapp to a standard location
ZIPAPP_INSTALL_PATH="$DEFAULT_CONFIG_DIR/aicoder.pyz"
mkdir -p "$DEFAULT_CONFIG_DIR"
cp "$ZIPAPP_PATH" "$ZIPAPP_INSTALL_PATH"

# Update and install launcher scripts
for script in "$SCRIPT_DIR/docs/extras"/aicoder-*; do
    if [ -f "$script" ]; then
        script_name=$(basename "$script")
        echo "Installing $script_name..."
        
        # Create temporary file for updated script
        temp_script=$(mktemp)
        
        # Update the AICODER_PYZ_PATH in aicoder-start
        if [ "$script_name" = "aicoder-start" ]; then
            sed "s|AICODER_PYZ_PATH=.*|AICODER_PYZ_PATH=\"$ZIPAPP_INSTALL_PATH\"|" "$script" > "$temp_script"
        else
            cp "$script" "$temp_script"
        fi
        
        # Make executable and copy to installation directory
        chmod +x "$temp_script"
        cp "$temp_script" "$BIN_DIR/$script_name"
        rm "$temp_script"
        
        echo -e "${GREEN}  ✓ Installed $script_name to $BIN_DIR${NC}"
    fi
done

echo
echo -e "${GREEN}✓ Launcher scripts installed${NC}"

# Check if we need to add to PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo
    echo -e "${YELLOW}Warning: $BIN_DIR is not in your PATH${NC}"
    echo "Add this line to your shell configuration file (~/.bashrc, ~/.zshrc, etc.):"
    echo "  export PATH=\"\$PATH:$BIN_DIR\""
    echo
fi

# Suggest stable plugins
echo
echo -e "${BLUE}Available stable plugins:${NC}"
echo "1. plan - Integrated plan management with /plan command and update_plan tool"
echo "2. theme - Dynamic color themes"
echo "3. tools_manager - Plugin management tools"
echo "4. ignore_newlines - Ignore newlines in responses"
echo "5. no_memory_chat - Disable memory in chat"
echo "6. tiered_cost_display - Display token usage costs"
echo "7. notify_prompt_sound - Text-to-speech notifications (Linux only, requires espeak and pulseaudio)"

echo
echo -e "${BLUE}Would you like to install any stable plugins? (y/N):${NC}"
read -r INSTALL_PLUGINS

if [[ $INSTALL_PLUGINS =~ ^[Yy]$ ]]; then
    PLUGIN_INSTALL_DIR="$DEFAULT_CONFIG_DIR/plugins"
    mkdir -p "$PLUGIN_INSTALL_DIR"
    
    echo "Installing stable plugins to $PLUGIN_INSTALL_DIR"
    
    # Install plan plugin (most useful)
    echo "Installing plan plugin..."
    cp -r "$SCRIPT_DIR/docs/plugins/examples/stable/plan" "$PLUGIN_INSTALL_DIR/"
    echo -e "${GREEN}  ✓ Installed plan plugin${NC}"
    
    # Install theme plugin
    echo "Installing theme plugin..."
    cp -r "$SCRIPT_DIR/docs/plugins/examples/stable/theme" "$PLUGIN_INSTALL_DIR/"
    echo -e "${GREEN}  ✓ Installed theme plugin${NC}"
    
    # Install tools_manager plugin
    echo "Installing tools_manager plugin..."
    cp -r "$SCRIPT_DIR/docs/plugins/examples/stable/tools_manager" "$PLUGIN_INSTALL_DIR/"
    echo -e "${GREEN}  ✓ Installed tools_manager plugin${NC}"
    
    echo
    echo -e "${GREEN}✓ Plugins installed${NC}"
    echo "Plugins will be automatically loaded when you run AI Coder"
    echo "To manage plugins, use the tools_manager plugin or manually edit:"
    echo "  $PLUGIN_INSTALL_DIR"
fi

# Final instructions
echo
echo -e "${BLUE}=== Installation Complete ===${NC}"
echo

echo "To run AI Coder:"
echo "  export OPENAI_API_KEY='your-api-key-here'"
echo "  aicoder-start"
echo
echo "To use specific AI providers:"
echo "  aicoder-gemini     # For Google Gemini"
echo "  aicoder-openai     # For OpenAI models"
echo "  aicoder-glm        # For Zhipu AI GLM"
echo "  aicoder-cerebras   # For Cerebras models"
echo "  aicoder-qwen       # For Qwen models"
echo
echo "The launcher scripts will automatically use sandboxing if firejail is available."
echo "To explicitly disable sandboxing: SANDBOX=0 aicoder-start"
echo
echo "Alternative: Install as a uv tool (without sandboxing):"
echo "  uv tool install aicoder --editable"
echo "  uvx aicoder"
echo
echo "To use installed plugins, they will be automatically loaded."
echo
echo -e "${GREEN}Enjoy AI Coder!${NC}"
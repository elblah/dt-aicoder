#!/bin/bash
# AI Coder Installation Script (UV-First)
#
# This script installs AI Coder using uv (modern Python package manager)
# with fallback to traditional zipapp installation.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}=== AI Coder Installation Script ===${NC}"
echo

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found${NC}"

# Function to check/install uv
check_and_install_uv() {
    if command -v uv >/dev/null 2>&1; then
        echo -e "${GREEN}✓ uv is already installed${NC}"
        return 0
    fi
    
    echo -e "${BLUE}Installing uv (modern Python package manager)...${NC}"
    echo "This will provide faster installs and automatic dependency management."
    
    # Install uv using the official installer
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        # Add to PATH for current session
        export PATH="$HOME/.cargo/bin:$PATH"
        echo -e "${GREEN}✓ uv installed successfully${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to install uv${NC}"
        echo -e "${YELLOW}You can install it manually with: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
        return 1
    fi
}

# Install AI Coder using uv (preferred method)
install_with_uv() {
    echo
    echo -e "${BLUE}Installing AI Coder using uv (recommended method)...${NC}"
    
    if uv tool install git+https://github.com/elblah/dt-aicoder; then
        echo -e "${GREEN}✓ AI Coder installed successfully via uv!${NC}"
        echo
        echo -e "${BLUE}To run AI Coder:${NC}"
        echo "  uvx aicoder"
        echo "  # Or add ~/.local/bin to your PATH and run: aicoder"
        echo
        echo -e "${BLUE}To update in the future:${NC}"
        echo "  uv tool upgrade aicoder"
        echo
        echo -e "${BLUE}To uninstall:${NC}"
        echo "  uv tool uninstall aicoder"
        return 0
    else
        echo -e "${RED}✗ Failed to install via uv${NC}"
        return 1
    fi
}

# Try uv installation first
echo -e "${BLUE}=== Installing AI Coder ===${NC}"

if check_and_install_uv; then
    if install_with_uv; then
        echo -e "${GREEN}=== Installation Complete! ===${NC}"
        echo
        echo -e "${BLUE}Next steps:${NC}"
        echo "1. Set your OpenAI API key:"
        echo "   export OPENAI_API_KEY='your-api-key-here'"
        echo
        echo "2. Run AI Coder:"
        echo "   uvx aicoder"
        echo
        echo -e "${BLUE}For plugin development and customization, see:${NC}"
        echo "  docs/plugins/README.md - Build custom plugins"
        echo "  docs/mcp/configuration_guide.md - Add external tools"
        exit 0
    else
        echo -e "${YELLOW}uv installation failed${NC}"
        echo -e "${BLUE}Please try manual installation:${NC}"
        echo "  uv tool install git+https://github.com/elblah/dt-aicoder"
        exit 1
    fi
fi

echo -e "${RED}Installation failed${NC}"
exit 1
#!/bin/bash

# Installation script for the dimmed plugin
# Usage: ./install_plugin.sh [global|user]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_FILE="$SCRIPT_DIR/dimmed.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if plugin file exists
if [ ! -f "$PLUGIN_FILE" ]; then
    print_error "Plugin file not found: $PLUGIN_FILE"
    exit 1
fi

# Determine installation type
INSTALL_TYPE="${1:-user}"

if [ "$INSTALL_TYPE" = "global" ]; then
    # Global installation
    PLUGIN_DIR="/usr/local/lib/aicoder/plugins"
    SUDO="sudo"
    
    print_status "Installing dimmed plugin globally..."
    
    # Create directory if needed
    $SUDO mkdir -p "$PLUGIN_DIR"
    
    # Copy plugin
    $SUDO cp "$PLUGIN_FILE" "$PLUGIN_DIR/"
    $SUDO chmod 644 "$PLUGIN_DIR/dimmed.py"
    
    print_success "Plugin installed globally to: $PLUGIN_DIR"
    
elif [ "$INSTALL_TYPE" = "user" ]; then
    # User installation
    CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
    PLUGIN_DIR="$CONFIG_HOME/aicoder/plugins"
    
    print_status "Installing dimmed plugin for user..."
    
    # Create directory if needed
    mkdir -p "$PLUGIN_DIR"
    
    # Copy plugin
    cp "$PLUGIN_FILE" "$PLUGIN_DIR/"
    chmod 644 "$PLUGIN_DIR/dimmed.py"
    
    print_success "Plugin installed to: $PLUGIN_DIR"
    
else
    print_error "Invalid installation type: $INSTALL_TYPE"
    echo "Usage: $0 [global|user]"
    exit 1
fi

# Create example config
print_status "Creating example configuration..."
EXAMPLE_CONFIG_DIR="$(pwd)/.aicoder"
mkdir -p "$EXAMPLE_CONFIG_DIR"

cat > "$EXAMPLE_CONFIG_DIR/dimmed.conf" << 'EOF'
# Dimmed Plugin Configuration
# One regex pattern per line - if any matches, print is dimmed
# Lines starting with # are comments

# Dim text in brackets
\[.*?\]

# Dim warning messages
Warning:.*

# Dim TODO comments
\bTODO\b

# Dim error messages
^Error:.*

# Dim debug output
\[DEBUG\].*
EOF

print_success "Example config created: $EXAMPLE_CONFIG_DIR/dimmed.conf"

# Test installation
print_status "Testing plugin installation..."
if python3 -c "import sys; sys.path.insert(0, '$PLUGIN_DIR'); import dimmed; print('✅ Plugin imports successfully')" 2>/dev/null; then
    print_success "Plugin test passed!"
else
    print_warning "Plugin test failed - check Python path and permissions"
fi

print_status "Installation completed!"
echo ""
echo "📖 Usage:"
echo "   1. Restart AI Coder"
echo "   2. Use /dimmed command to configure patterns"
echo "   3. Copy .aicoder/dimmed.conf to your projects as needed"
echo ""
echo "🔧 Configuration options:"
echo "   - Project config: .aicoder/dimmed.conf"
echo "   - Global config: ~/.config/aicoder/dimmed.conf"
echo "   - Environment: AICODER_DIMMED_PATTERNS='pattern1,pattern2'"
echo ""
echo "💡 Example patterns:"
echo "   \\[.*?\\]           # Text in brackets"
echo "   Warning:.*        # Warning messages"
echo "   \\bTODO\\b          # TODO items"
echo "   ^Error:.*          # Error messages"
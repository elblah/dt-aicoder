#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v python3 &> /dev/null; then
    echo -e "ERROR: Python 3 is required but not installed"
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "UV is REQUIRED to install the application but is not installed."
    read -p "Do you want to install uv? (Y/n): "
    if [[ $REPLY =~ [Nn] ]]; then
        echo "ERROR: UV is not installed... abort..."
        exit 1
    fi
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    if ! command -v uv > /dev/null; then
        echo "ERROR: uv was not installed or there is something wrong... abort..."
        exit 1
    fi
fi

if ! command -v aicoder > /dev/null; then
    if grep dt-aicoder .git/config; then
        echo "*** Installing aicoder (LOCAL VERSION)..."
        uv tool install $SCRIPT_DIR
    else
        echo "*** Installing aicoder..."
        uv tool install git+https://github.com/elblah/dt-aicoder
    fi
    if ! command -v aicoder > /dev/null; then
        echo "ERROR: aicoder was not installed or there is something wrong... abort..."
        exit 1
    fi
else
    echo "*** Upgrading aicoder..."
    uv tool upgrade aicoder
fi

if [[ -d ~/.config ]]; then
    mkdir -p ~/.config/aicoder/plugins
    echo "You can install plugins on ~/.config/aicoder/plugins..."
fi

echo -e "\naicoder is ready...\n"
echo -e "Run:\n$ aicoder\n"
echo -e "To upgrade it use:"
echo -e "  uv tool upgrade aicoder\n"
echo -e "To uninstall it use:"
echo -e "  uv tool uninstall aicoder"

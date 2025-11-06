#!/bin/bash

plugins=$(find docs/plugins/examples -name "*.py" | grep -v __init__ \
    | grep -v 'test_')

sels=$(echo "$plugins" | fzf -m -e)

mkdir -p ~/.config/aicoder/plugins

while read -r LINE; do
    echo "Installing: $LINE"
    cp $LINE ~/.config/aicoder/plugins
done <<< "$sels"

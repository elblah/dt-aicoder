#!/bin/bash

# Run pytest with proper settings
set -e

echo "Running pytest tests..."
echo "=================================="

# Run pytest with all tests
python -m pytest tests/ "$@"

echo ""
echo "[✓] All pytest tests completed!"
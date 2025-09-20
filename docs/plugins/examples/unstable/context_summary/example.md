# Context Summary Plugin Example

This directory contains a complete example of a context summary plugin with auto-compaction for AICoder.

## Files

- `context_summary.py` - The main plugin implementation
- `README.md` - Documentation for the plugin
- `test_plugin.py` - Test script to verify plugin functionality
- `__init__.py` - Makes this a Python package
- `requirements.txt` - Lists plugin dependencies (none for this plugin)

## Features

- **Automatic Summarization**: Automatically summarizes conversation context when message count exceeds threshold
- **Model-aware Auto Compaction**: Automatically compacts memory when approaching model-specific token limits
- **Detailed Reason Messages**: Clear messages explaining why compaction/summarization is being triggered
- **Enhanced Manual Commands**: Provides `/summarize` and `/compact` commands with detailed feedback
- **Configurable Thresholds**: Adjustable message count and token usage thresholds

## Installation

1. Copy `context_summary.py` to your AICoder plugins directory:
   ```bash
   cp context_summary.py /path/to/aicoder/plugins/
   ```

2. The plugin will be automatically loaded when AICoder starts.

## Testing

Run the test script to verify the plugin works correctly:
```bash
python test_plugin.py
```
# Safe Tool Results Plugin

## Overview

This plugin converts tool call results from JSON format to plain text user messages to maintain stable AI interactions and prevent context pollution.

**Status**: Experimental (Unstable)

## Purpose

Some AI models can experience context instability when processing certain patterns in tool call results. This plugin provides a cleaner interaction format that maintains conversation flow.

## Installation

```bash
cd docs/plugins/examples/unstable/safe_tool_results
./install_plugin.sh
```

## Usage

### Environment Variable
```bash
# Enable safe mode
AICODER_SAFE_TOOL_RESULTS=1 aicoder

# Disable safe mode
AICODER_SAFE_TOOL_RESULTS=0 aicoder
```

### Command Inside AI Coder
```
/safetool on      # Enable safe mode
/safetool off     # Disable safe mode
/safetool toggle  # Toggle safe mode
/safetool         # Show current status
```

## Features

- **Clean Text Conversion**: Converts JSON tool results to plain text user messages
- **Content Optimization**: Cleans up excessive whitespace and formatting
- **Size Management**: Truncates very large results efficiently
- **Toggleable**: Can be enabled/disabled at runtime
- **Non-destructive**: Original tool functionality preserved when disabled

## How It Works

1. **Intercepts** tool call execution
2. **Executes** tools normally
3. **Converts** JSON results to clean text format
4. **Optimizes** content for better context management
5. **Returns** formatted text instead of raw JSON

### Example Conversion

**Before (JSON tool result):**
```json
{
  "tool_call_id": "call_123",
  "role": "tool",
  "name": "read_file",
  "content": "line1\nline2\nline3"
}
```

**After (Clean text message):**
```
User: I executed the read_file tool with parameters: path='/etc/passwd'

Output:
line1
line2
line3

Execution completed successfully.
```

## Configuration

- `AICODER_SAFE_TOOL_RESULTS`: Enable/disable (1/0)
- Max result size: 8,000 characters
- Truncation suffix: `... [content truncated for efficiency]`

## Testing

Run the test suite:
```bash
python test_plugin.py
```

## Stability

⚠️ **Experimental**: This plugin uses monkey patching and may interfere with other plugins. Test thoroughly before production use.

## License

Apache 2.0 (same as main project)

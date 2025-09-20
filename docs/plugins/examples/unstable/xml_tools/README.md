# XML Tools Plugin

This unified plugin enables AI Coder to work with LLMs that don't support native tool calling by providing both XML system prompt generation and XML tool call execution capabilities.

## Overview

Some LLMs don't support native tool/function calling capabilities. This plugin bridges that gap by combining two essential functions in one plugin:

1. **System Prompt Generation**: Creates XML format system prompts to teach the AI how to use tools
2. **Tool Call Execution**: Provides functions for executing XML-format tool calls

This replaces the need for two separate plugins (`xml_tools_format` and `xml_tool_executor`) that were tightly coupled and created installation complexity.

## How It Works

### System Prompt Generation
Use the `/xml_tools` command with various subcommands:

```
/xml_tools help     # Show help
/xml_tools print    # Print XML system prompt to terminal  
/xml_tools enable   # Enable XML tools for current conversation
/xml_tools disable  # Disable XML tools for current conversation
/xml_tools status   # Show XML tools status
```

### Tool Call Execution
The plugin provides functions that can be integrated into AI Coder's response processing to execute XML tool calls like:

```xml
<read_file>
  <path>src/main.py</path>
</read_file>

<write_file>
  <path>new_file.txt</path>
  <content>Hello, World!</content>
</write_file>
```

## Installation

1. Copy the plugin to your AI Coder plugins directory:
   ```bash
   mkdir -p ~/.config/aicoder/plugins
   cp xml_tools.py ~/.config/aicoder/plugins/
   ```

2. Restart AI Coder to load the plugin

## Usage

### Enable XML Tools for Conversation
```
/xml_tools enable
```
This automatically adds XML tool instructions to the conversation so the AI can use them immediately.

### Print XML System Prompt (Manual)
```
/xml_tools print
```

### Check Status
```
/xml_tools status
```

### Manual XML Tool Execution (for testing)
```
/execute_xml <read_file><path>test.txt</path></read_file>
```

### Integration with AI Response Processing
To automatically execute XML tool calls from AI responses, the plugin uses a monkey-patching approach that intercepts the `input()` function. When the AI generates XML tool calls, they are automatically executed and the results are returned directly to the AI Coder app as if the user had typed them.

This approach provides seamless integration without requiring changes to the main AI Coder application code.

## Features

- **Easy Enable/Disable**: Simple commands to activate XML tools for conversations
- **Automatic Integration**: `/xml_tools enable` adds instructions directly to conversation
- **Manual Testing**: `/execute_xml` command for testing XML tool calls
- **Seamless Execution**: Monkey-patched `input()` automatically processes XML tool calls
- **Status Checking**: `/xml_tools status` shows current activation state

## Benefits

This approach allows:
- **Compatibility**: Works with any LLM that can output XML
- **Simplicity**: One plugin instead of two separate ones
- **Transparency**: AI can see exactly what tools are being called and their results
- **Control**: Easy to understand and debug tool execution
- **Zero Integration Required**: Works automatically through monkey-patching without modifying AI Coder core
- **Seamless Flow**: Tool execution happens automatically with results returned as user input

## Requirements

- AI Coder v2.0 or later
- Python 3.8+

## Notes

- The plugin works automatically through monkey-patching
- No changes needed to AI Coder core application
- Manual testing is available through the `/execute_xml` command
- Works with all AI Coder internal tools and MCP tools

## Implementation Details

This unified plugin combines the functionality of two previous separate plugins:
- `xml_tools_format` - Generated XML system prompts to teach AI how to use tools
- `xml_tool_executor` - Executed XML tool calls that the AI generated in responses

The unified implementation provides a better user experience with a single installation and clean API for integration.
# Tools Manager Plugin

This plugin provides commands to temporarily list, enable, and disable tools during a session.

## Features

- List all available tools with their status (enabled/disabled)
- Show detailed information about specific tools
- Temporarily enable/disable tools during the current session

## Installation

1. Copy the `tools_manager` directory to your AI Coder plugins directory:
   ```bash
   cp -r tools_manager ~/.config/aicoder/plugins/
   ```

2. Run AI Coder - the tools manager will be automatically available

## Usage

The plugin adds the `/tools` command with the following subcommands:

### List Tools
```
/tools
/tools list
/tools ls
```
Lists all available tools with their status and brief descriptions.

### Tool Information
```
/tools info <tool_name>
```
Shows detailed information about a specific tool, including parameters.

### Enable Tool
```
/tools enable <tool_name>
```
Re-enables a tool that was previously disabled in the current session.

### Disable Tool
```
/tools disable <tool_name>
```
Temporarily disables a tool for the remainder of the current session.

## Example Output

```
📋 Available Tools:
================================================================================
edit_file                 ✅ Enabled   Edit files by replacing text, creating new files, or deleting content
glob                      ✅ Enabled   Find files matching a pattern using the find command
grep                      ✅ Enabled   Search text in files in the current directory using ripgrep
list_directory            ✅ Enabled   Lists the contents of a specified directory recursively
pwd                       ✅ Enabled   Returns the current working directory
read_file                 ✅ Enabled   Reads the content from a specified file path
run_shell_command         ✅ Enabled   Executes a shell command and returns its output
web_search                ❌ Disabled  Perform a web search to find information about a topic using DuckDuckGo
write_file                ✅ Enabled   Writes content to a specified file path, creating directories if needed
```

## Benefits

- Easy visibility into available tools and their current status
- Quick access to tool documentation
- Temporary tool management without file modifications
- No external dependencies required
- Works with all tool types (internal, command, JSON-RPC, plugin-registered)

## How It Works

The plugin manages tools by moving them between active and disabled dictionaries in memory:
- When you disable a tool, it's moved from the active registry to a temporary disabled storage
- When you enable a tool, it's moved back from the disabled storage to the active registry
- Changes are temporary and only affect the current session
- No files are modified, making it safe and reversible

## Limitations

- Changes are temporary and only last for the current session
- MCP-stdio tools require a restart to be properly re-enabled
- Tools disabled in this session cannot be re-enabled if they were originally loaded from mcp_tools.json with "disabled": true
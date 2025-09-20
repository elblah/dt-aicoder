# MCP (Model Context Protocol) Configuration

This directory contains documentation for configuring and using MCP tools with AI Coder.

## Table of Contents
1. [MCP Overview](#mcp-overview)
2. [Configuration File Structure](#configuration-file-structure)
3. [Command Configuration](#command-configuration)
4. [MCP-STDIO Configuration](#mcp-stdio-configuration)
5. [JSON-RPC Configuration](#json-rpc-configuration)
6. [Tool Parameters](#tool-parameters)
7. [Tool Registration](#tool-registration)
8. [Examples](#examples)

## MCP Overview

The Model Context Protocol (MCP) is a standardized way to define and interact with tools that can be used by AI models. In AI Coder, MCP tools allow extending the functionality available to the AI assistant.

## Configuration File Structure

The MCP tools configuration file (`mcp_tools.json`) follows a specific structure where each tool is defined as a key-value pair:

```json
{
  "tool_name": {
    "type": "command|mcp-stdio|jsonrpc",
    "description": "Description of what the tool does",
    "command": "executable_name",
    "parameters": {
      "type": "object",
      "properties": {
        "param_name": {
          "type": "string|number",
          "description": "Description of the parameter"
        }
      },
      "required": ["param_name"]
    }
  }
}
```

## Command Configuration

AI Coder supports configuring external commands as MCP tools. This allows you to expose system commands or custom scripts as tools that the AI can use.

### Basic Command Tool

```json
{
  "list_directory": {
    "type": "command",
    "description": "List files in the current directory",
    "command": "ls -la"
  }
}
```

### Command Tool with Parameters

```json
{
  "search_files": {
    "type": "command",
    "description": "Search for files matching a pattern",
    "command": "find . -name \"{pattern}\"",
    "parameters": {
      "type": "object",
      "properties": {
        "pattern": {
          "type": "string",
          "description": "Pattern to search for"
        }
      },
      "required": ["pattern"]
    }
  }
}
```

### Advanced Command Tool Options

Command tools support several additional options:

- `auto_approved`: Whether the tool can be used without user approval
- `disabled`: Whether the tool is disabled
- `truncated_chars`: Number of characters to truncate output
- `preview_command`: Command to show what the tool will do
- `approval_excludes_arguments`: Whether arguments are excluded from approval

```json
{
  "example_tool": {
    "type": "command",
    "auto_approved": true,
    "disabled": false,
    "truncated_chars": 1000,
    "command": "echo \"{message}\"",
    "preview_command": "echo \"This tool will echo: {message}\"",
    "approval_excludes_arguments": true,
    "description": "Example tool with all options",
    "parameters": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "Message to echo"
        }
      },
      "required": ["message"]
    }
  }
}
```

## MCP-STDIO Configuration

MCP-STDIO tools communicate with AI Coder through standard input/output streams. This is useful for more complex tools that need to maintain state or perform multiple operations.

### Basic MCP-STDIO Tool

```json
{
  "code_linter": {
    "type": "mcp-stdio",
    "description": "Lint code files for issues",
    "command": "/usr/local/bin/code_linter --format json"
  }
}
```

### MCP-STDIO Tool with Additional Options

```json
{
  "database_client": {
    "type": "mcp-stdio",
    "disabled": false,
    "truncated_chars": 500,
    "command": "/usr/local/bin/db_client --connection-string postgresql://localhost:5432/mydb",
    "description": "Interact with the database"
  }
}
```

## JSON-RPC Configuration

JSON-RPC tools communicate with remote services using the JSON-RPC protocol.

### Basic JSON-RPC Tool

```json
{
  "get_weather": {
    "type": "jsonrpc",
    "url": "http://localhost:8000/weather",
    "method": "get_weather",
    "truncated_chars": 300,
    "disabled": true,
    "description": "Gets the weather for a given city (example).",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "The city to get the weather for."
        }
      },
      "required": [
        "city"
      ]
    }
  }
}
```

## Tool Parameters

Tools can accept parameters that are passed by the AI. Parameters are defined in the `parameters` section using JSON Schema format.

### String Parameter

```json
{
  "file_path": {
    "type": "string",
    "description": "Path to the file to process"
  }
}
```

### Number Parameter

```json
{
  "line_count": {
    "type": "number",
    "description": "Number of lines to process"
  }
}
```

### Required Parameters

Parameters can be marked as required:

```json
"parameters": {
  "type": "object",
  "properties": {
    "file_path": {
      "type": "string",
      "description": "Path to the file"
    },
    "search_term": {
      "type": "string",
      "description": "Term to search for"
    }
  },
  "required": ["file_path", "search_term"]
}
```

## Tool Registration

Tools are automatically registered from the `mcp_tools.json` file located in the configuration directory. The default location is `~/.config/aicoder/mcp_tools.json`, but this can be overridden with the `MCP_TOOLS_CONF_PATH` environment variable.

## Examples

### Real-World Command Tool

```json
{
  "create_backup": {
    "type": "command",
    "command": "cp {source_file} {source_file}.bak",
    "preview_command": "echo \"This tool will create a backup of '{source_file}' as '{source_file}.bak'\"",
    "truncated_chars": 0,
    "description": "Creates a backup of a file with .bak extension.",
    "disabled": false,
    "auto_approved": true,
    "parameters": {
      "type": "object",
      "properties": {
        "source_file": {
          "type": "string",
          "description": "Path to the file to backup."
        }
      },
      "required": [
        "source_file"
      ]
    }
  }
}
```

### Real-World MCP-STDIO Tool

```json
{
  "fetch_server": {
    "type": "mcp-stdio",
    "disabled": true,
    "truncated_chars": 500,
    "command": "uvx mcp-server-fetch",
    "description": "MCP server for fetching resources"
  }
}
```

### JSON-RPC Tool

```json
{
  "get_weather": {
    "type": "jsonrpc",
    "url": "http://localhost:8000/weather",
    "method": "get_weather",
    "truncated_chars": 300,
    "disabled": true,
    "description": "Gets the weather for a given city (example).",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "The city to get the weather for."
        }
      },
      "required": [
        "city"
      ]
    }
  }
}
```

## Environment Variables

- `MCP_TOOLS_CONF_PATH`: Override the default path to the mcp_tools.json file
- `MCP_DEBUG`: Enable debug output for MCP tools

## Best Practices

1. Provide clear, concise descriptions for each tool
2. Use specific names that clearly indicate the tool's function
3. Test your tools independently before adding them to the configuration
4. Handle errors gracefully in your tools
5. Document any environment variables or special requirements
6. Use appropriate truncation limits for tools with verbose output
7. Consider security implications when creating tools that can modify the system
8. Use `auto_approved` judiciously - only for safe, read-only operations
9. Provide meaningful preview commands so users understand what will happen
10. Mark tools as `disabled` by default if they require special setup
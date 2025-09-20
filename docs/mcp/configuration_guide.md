# MCP Tool Configuration Guide

This guide provides detailed information on how to configure MCP tools for use with AI Coder.

## Configuration File Structure

The MCP tools configuration file (`mcp_tools.json`) follows a specific structure:

```json
{
  "tools": [
    {
      "name": "tool_name",
      "type": "command|mcp-stdio",
      "description": "Tool description",
      "command": "executable_path",
      "args": ["argument1", "argument2"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  ]
}
```

## Command Tools

Command tools execute a system command and return the output. They are suitable for simple, stateless operations.

### Basic Command Tool

```json
{
  "name": "list_directory",
  "type": "command",
  "description": "List files in the current directory",
  "command": "ls",
  "args": ["-la"]
}
```

### Command Tool with Environment Variables

```json
{
  "name": "git_status",
  "type": "command",
  "description": "Show git repository status",
  "command": "git",
  "args": ["status"],
  "env": {
    "GIT_PAGER": "cat"
  }
}
```

### Parameterized Command Tool

Some tools may need to accept parameters from the AI. These are defined using placeholders:

```json
{
  "name": "search_files",
  "type": "command",
  "description": "Search for files matching a pattern",
  "command": "find",
  "args": [".", "-name", "{pattern}"]
}
```

## MCP-STDIO Tools

MCP-STDIO tools communicate through standard input/output streams and can maintain state between calls.

### Basic MCP-STDIO Tool

```json
{
  "name": "code_linter",
  "type": "mcp-stdio",
  "description": "Lint code files for issues",
  "command": "/usr/local/bin/code_linter",
  "args": ["--format", "json"]
}
```

### MCP-STDIO Tool with Environment

```json
{
  "name": "database_client",
  "type": "mcp-stdio",
  "description": "Interact with the database",
  "command": "/usr/local/bin/db_client",
  "args": ["--connection-string", "postgresql://localhost:5432/mydb"],
  "env": {
    "DB_PASSWORD": "secret_password"
  }
}
```

## Advanced Configuration

### Working Directory

You can specify a working directory for tools:

```json
{
  "name": "project_build",
  "type": "command",
  "description": "Build the project",
  "command": "make",
  "args": ["build"],
  "working_dir": "/path/to/project"
}
```

### Timeout Configuration

Set timeouts for long-running tools:

```json
{
  "name": "long_process",
  "type": "command",
  "description": "Run a long process",
  "command": "/usr/local/bin/long_process",
  "args": [],
  "timeout": 300
}
```

### Conditional Execution

Some tools may only be available on certain platforms:

```json
{
  "name": "system_info",
  "type": "command",
  "description": "Get system information",
  "command": "uname",
  "args": ["-a"],
  "platforms": ["linux", "darwin"]
}
```

## Security Considerations

1. Only add trusted executables to your MCP configuration
2. Be cautious with tools that can modify the file system
3. Use environment variables for sensitive data rather than hardcoding
4. Regularly review and audit your configured tools
5. Consider using sandboxing for untrusted tools

## Troubleshooting

### Common Issues

1. **Tool not found**: Ensure the command path is correct and the executable is in PATH
2. **Permission denied**: Check that the executable has proper permissions
3. **Timeout errors**: Increase the timeout value for long-running tools
4. **Environment issues**: Verify that required environment variables are set

### Debugging

Enable debug output by setting the `MCP_DEBUG` environment variable:

```bash
MCP_DEBUG=1 python -m aicoder
```

### Logging

MCP tools will log their execution to the standard AI Coder logs, which can be enabled with:

```bash
DEBUG=1 python -m aicoder
```

## Best Practices

1. **Clear Descriptions**: Write descriptions that clearly explain what the tool does
2. **Error Handling**: Ensure your tools handle errors gracefully and return meaningful error messages
3. **Documentation**: Document any special requirements or dependencies for your tools
4. **Testing**: Test tools independently before adding them to the configuration
5. **Versioning**: Keep track of tool versions, especially for custom tools
6. **Security**: Regularly review and audit your configured tools for security issues
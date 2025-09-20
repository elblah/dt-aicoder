# MCP Documentation Summary

This document provides an overview of the MCP (Model Context Protocol) documentation available in this directory.

## Documentation Files

1. [README.md](README.md) - Main documentation covering:
   - MCP overview and configuration file structure
   - Command, MCP-STDIO, and JSON-RPC tool configurations
   - Tool parameters and registration
   - Real-world examples
   - Best practices

2. [configuration_guide.md](configuration_guide.md) - Detailed configuration guide (deprecated - see README.md for updated information)

3. [examples_and_best_practices.md](examples_and_best_practices.md) - Practical examples and best practices covering:
   - Real-world file operation tools
   - System information tools
   - Text processing tools
   - Security considerations
   - Error handling
   - Resource management
   - User experience improvements
   - Advanced configuration examples
   - Testing methodologies
   - Troubleshooting common issues
   - Performance optimization

## Key Concepts

### Tool Types

AI Coder supports three types of MCP tools:

1. **Command Tools** - Execute system commands
2. **MCP-STDIO Tools** - Communicate through standard input/output streams
3. **JSON-RPC Tools** - Communicate with remote services using JSON-RPC protocol

### Configuration Structure

Tools are defined in `mcp_tools.json` with the following structure:

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

### Important Options

- `auto_approved`: Whether the tool can be used without user approval
- `disabled`: Whether the tool is disabled
- `truncated_chars`: Number of characters to truncate output
- `preview_command`: Command to show what the tool will do
- `approval_excludes_arguments`: Whether arguments are excluded from approval

## Best Practices Summary

1. **Security First**: Always consider the security implications of tools
2. **Clear Descriptions**: Provide detailed descriptions for each tool
3. **Error Handling**: Ensure tools handle errors gracefully
4. **Resource Management**: Set appropriate timeouts and output limits
5. **User Experience**: Provide clear preview commands
6. **Testing**: Test tools thoroughly before deployment
7. **Documentation**: Maintain clear documentation for complex tools

## Getting Started

1. Review the [README.md](README.md) for comprehensive documentation
2. Examine the [examples_and_best_practices.md](examples_and_best_practices.md) for practical implementations
3. Create your `mcp_tools.json` configuration file
4. Test your tools manually before using them with AI Coder
5. Monitor tool performance and adjust configurations as needed

## Additional Resources

- Real configuration example: `/home/blah/.config/aicoder/mcp_tools.json`
- AI Coder main documentation: [../README.md](../README.md)
- Plugin documentation: [../plugins/plugins.md](../plugins/plugins.md)
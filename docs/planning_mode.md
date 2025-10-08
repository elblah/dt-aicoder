# Planning Mode Configuration

Planning mode allows users to restrict AI to read-only operations, providing a safe environment for analysis and planning without making changes.

## How Planning Mode Works

1. **Toggle with `/plan toggle`** - Switch between planning (read-only) and build (read-write) modes
2. **Visual indicators** - `[PLAN]` appears in prompts when planning mode is active
3. **Tool filtering** - Only tools marked as available in plan mode can be used
4. **Error handling** - Attempts to use disabled tools return clear error messages

## Configuration

### Internal Tools

Internal tools are defined in their respective Python files with a `TOOL_DEFINITION` dictionary:

```python
TOOL_DEFINITION = {
    "type": "internal",
    "description": "Tool description",
    "available_in_plan_mode": false,  # Only set this for tools that should be BLOCKED
    # ... other configuration
}
```

**Default behavior**: All tools are available in plan mode unless explicitly marked with `available_in_plan_mode: false`.

### External/MCP Tools

External tools in `mcp_tools.json` use the same flag:

```json
{
  "tools": [
    {
      "name": "write_file",
      "type": "command",
      "description": "Write to a file",
      "available_in_plan_mode": false,
      "command": "echo"
    },
    {
      "name": "read_file", 
      "type": "command",
      "description": "Read a file",
      // Note: No available_in_plan_mode flag means it's allowed (default behavior)
      "command": "cat"
    }
  ]
}
```

## Examples

### Tools That Should Be Blocked in Plan Mode

```python
# File writing tools
TOOL_DEFINITION = {
    "name": "write_file",
    "available_in_plan_mode": false,
    # ...
}

# File modification tools
TOOL_DEFINITION = {
    "name": "edit_file", 
    "available_in_plan_mode": false,
    # ...
}

# System modification commands
{
  "name": "delete_file",
  "command": "rm",
  "available_in_plan_mode": false,
  # ...
}
```

### Tools That Should Be Allowed in Plan Mode (No Flag Needed)

```python
# Read-only tools don't need the flag
TOOL_DEFINITION = {
    "name": "read_file",
    // No available_in_plan_mode needed - defaults to allowed
    # ...
}

# Search and analysis tools
{
  "name": "grep_search",
  "command": "grep",
  // No available_in_plan_mode needed - defaults to allowed
  # ...
}
```

## Security Considerations

- **Default to allow**: Tools are available in plan mode unless explicitly blocked
- **Explicit blocking**: Only mark tools that can modify files or system state
- **User tools**: User-added MCP tools should use `available_in_plan_mode: false` for potentially dangerous operations
- **Bash commands**: The AI is instructed to avoid using write operations in plan mode, but tool-level restrictions provide additional safety

## Error Messages

When a disabled tool is called in plan mode, the AI receives a clear error:

```
Error: Tool 'write_file' is disabled in planning mode. Planning mode only allows read-only operations. Use '/plan toggle' to disable planning mode.
```

This helps both the AI and user understand what's happening and how to resolve it.
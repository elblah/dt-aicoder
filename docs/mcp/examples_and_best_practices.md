# MCP Examples and Best Practices

This document provides practical examples and best practices for configuring and using MCP tools with AI Coder.

## Real-World Examples

### File Operations

#### Backup Tool
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
      "required": ["source_file"]
    }
  }
}
```

#### Tree View Tool
```json
{
  "tree_view": {
    "type": "command",
    "auto_approved": true,
    "command": "tree -L {levels} {directory}",
    "preview_command": "echo \"This tool will show directory tree for '{directory}' up to {levels} levels\"",
    "truncated_chars": 1000,
    "description": "Shows directory structure as a tree.",
    "disabled": false,
    "parameters": {
      "type": "object",
      "properties": {
        "directory": {
          "type": "string",
          "description": "Path to the directory to show."
        },
        "levels": {
          "type": "number",
          "description": "Maximum depth levels to show."
        }
      },
      "required": ["directory", "levels"]
    }
  }
}
```

### System Information Tools

#### Working Directory Tool
```json
{
  "pwd": {
    "type": "command",
    "auto_approved": true,
    "command": "pwd",
    "truncated_chars": 1000,
    "description": "Get the current working directory.",
    "disabled": true
  }
}
```

#### File Listing with Ripgrep
```json
{
  "ripgrep_list_files": {
    "type": "command",
    "auto_approved": true,
    "command": "timeout 60 rg --files | head -n 2000",
    "preview_command": "echo \"This tool will list files limited by 2000 lines of output. This tool might be more interesting then grep because it lists all dirs recursively while list_files list only one dir at the time.\"",
    "truncated_chars": 1000,
    "description": "List files in the current directory tree using ripgrep. Returns max 2000 lines.",
    "disabled": true
  }
}
```

### Text Processing Tools

#### Text Search with Ripgrep
```json
{
  "ripgrep_search": {
    "type": "command",
    "auto_approved": true,
    "command": "txt=$(cat <<'EOF'\n{text}\nEOF\n)\ntimeout 60 rg -- \"$txt\" | head -n 2000",
    "preview_command": "echo \"This tool will search for text in files using ripgrep: {text}\"",
    "truncated_chars": 1000,
    "description": "Search text in files in the current directory using ripgrep. Returns max 2000 lines.",
    "disabled": true,
    "parameters": {
      "type": "object",
      "properties": {
        "text": {
          "type": "string",
          "description": "Text to search for."
        }
      },
      "required": ["text"]
    }
  }
}
```

#### Line Extraction Tool
```json
{
  "extract_lines": {
    "type": "command",
    "auto_approved": true,
    "command": "sed -n '{start_line},{end_line}p' {file_path}",
    "preview_command": "echo \"This tool will extract lines {start_line} to {end_line} from file '{file_path}'\"",
    "truncated_chars": 0,
    "description": "Extracts specific lines from a file. Prefer using read_file or ripgrep_search other than this tool instead you REALLY KNOW what you are doing. The use of this function to explore the code may generate make requests and create a lot of back and forth that makes the coding experience very slow for the user. Use this tool if you really know the like range you want.",
    "disabled": true,
    "parameters": {
      "type": "object",
      "properties": {
        "file_path": {
          "type": "string",
          "description": "Path to the file to extract from."
        },
        "start_line": {
          "type": "number",
          "description": "Starting line number."
        },
        "end_line": {
          "type": "number",
          "description": "Ending line number."
        }
      },
      "required": ["file_path", "start_line", "end_line"]
    }
  }
}
```

## Best Practices

### 1. Security Considerations

Always consider the security implications of the tools you're adding:

```json
{
  "safe_list_files": {
    "type": "command",
    "auto_approved": true,
    "command": "ls -la {directory}",
    "description": "List files in a directory",
    "disabled": false,
    "parameters": {
      "type": "object",
      "properties": {
        "directory": {
          "type": "string",
          "description": "Directory to list (relative to current working directory)"
        }
      },
      "required": ["directory"]
    }
  }
}
```

Avoid tools that can execute arbitrary commands:

```json
// DON'T DO THIS - SECURITY RISK
{
  "dangerous_shell": {
    "type": "command",
    "command": "sh -c '{command}'",
    "description": "Execute arbitrary shell command",
    "disabled": true
  }
}
```

### 2. Error Handling

Ensure your tools handle errors gracefully:

```json
{
  "safe_file_read": {
    "type": "command",
    "command": "if [ -f \"{file_path}\" ]; then cat \"{file_path}\"; else echo \"Error: File not found: {file_path}\" >&2; fi",
    "description": "Safely read a file with error handling",
    "parameters": {
      "type": "object",
      "properties": {
        "file_path": {
          "type": "string",
          "description": "Path to the file to read"
        }
      },
      "required": ["file_path"]
    }
  }
}
```

### 3. Resource Management

Set appropriate timeouts and output limits:

```json
{
  "limited_search": {
    "type": "command",
    "command": "timeout 30s find . -name \"{pattern}\" | head -n 100",
    "description": "Search for files with timeout and output limit",
    "truncated_chars": 500,
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

### 4. User Experience

Provide clear preview commands and descriptions:

```json
{
  "git_diff": {
    "type": "command",
    "approval_excludes_arguments": true,
    "command": "git diff {file_path}",
    "preview_command": "echo \"This tool will show git diff for file '{file_path}'\"",
    "truncated_chars": 0,
    "description": "Shows git diff for a specific file.",
    "disabled": true,
    "parameters": {
      "type": "object",
      "properties": {
        "file_path": {
          "type": "string",
          "description": "Path to the file to show diff for."
        }
      },
      "required": ["file_path"]
    }
  }
}
```

## Advanced Configuration Examples

### Complex Parameter Handling

```json
{
  "replace_lines": {
    "type": "command",
    "approval_excludes_arguments": true,
    "command": "new_content=$(cat <<'EOF'\n{new_content}\nEOF\n) && escaped_content=$(echo \"$new_content\" | sed ':a;N;$!ba;s/\\n/\\\\n/g') && eval \"sed -i '{start_line},{end_line}c\\\\$escaped_content' {file_path}\"",
    "preview_command": "echo \"This tool will replace lines {start_line} to {end_line} in file '{file_path}' with new content\"",
    "truncated_chars": 0,
    "description": "Replace specific lines in a file with new content. MUCH faster than write_file for large files. Use \\\\n for newlines in the new_content. Example: to replace lines 5-7 with 'line1\\\\nline2\\\\nline3', use start_line=5, end_line=7, new_content='line1\\\\nline2\\\\nline3'",
    "disabled": true,
    "parameters": {
      "type": "object",
      "properties": {
        "file_path": {
          "type": "string",
          "description": "Path to the file to modify."
        },
        "start_line": {
          "type": "number",
          "description": "Starting line number (1-based)."
        },
        "end_line": {
          "type": "number",
          "description": "Ending line number (1-based)."
        },
        "new_content": {
          "type": "string",
          "description": "New content to replace the lines with. Use \\\\n for newlines."
        }
      },
      "required": ["file_path", "start_line", "end_line", "new_content"]
    }
  }
}
```

### Custom Tool with Special Handling

```json
{
  "apply_patch": {
    "type": "command",
    "approval_excludes_arguments": true,
    "auto_approved": false,
    "command": "patch_content=$(cat <<'EOF'\n{patch}\nEOF\n)\necho \"$patch_content\" | apply_patch.py",
    "preview_command": "patch_content=$(cat <<'EOF'\n{patch}\nEOF\n)\necho \"$patch_content\"",
    "truncated_chars": 0,
    "colorize_diff_lines": true,
    "tool_description_command": "apply_patch.py --tool-description",
    "append_to_system_prompt_command": "apply_patch.py --append-to-system-prompt",
    "disabled": true,
    "parameters": {
      "type": "object",
      "properties": {
        "patch": {
          "type": "string",
          "description": "The patch content to apply in our custom patch format."
        }
      },
      "required": ["patch"]
    }
  }
}
```

## Testing Your Tools

### Manual Testing

Before adding a tool to your configuration, test it manually:

```bash
# Test a simple command tool
echo "test content" > test.txt
cp test.txt test.txt.bak
cat test.txt.bak

# Test a tool with parameters
tree -L 2 .

# Test error handling
ls -la /nonexistent/path
```

### Integration Testing

Create a simple test configuration:

```json
{
  "test_tool": {
    "type": "command",
    "command": "echo \"Test successful: {message}\"",
    "description": "Test tool for validation",
    "parameters": {
      "type": "object",
      "properties": {
        "message": {
          "type": "string",
          "description": "Test message"
        }
      },
      "required": ["message"]
    }
  }
}
```

## Troubleshooting Common Issues

### 1. Tool Not Found

Ensure the command is in your PATH or use absolute paths:

```json
{
  "absolute_path_tool": {
    "type": "command",
    "command": "/usr/local/bin/specific_tool",
    "description": "Tool using absolute path"
  }
}
```

### 2. Permission Issues

Make sure the executable has proper permissions:

```bash
chmod +x /path/to/your/tool
```

### 3. Parameter Substitution Issues

Use proper escaping for special characters:

```json
{
  "safe_text_replace": {
    "type": "command",
    "command": "sed 's/{search}/{replace}/g' {file}",
    "description": "Safely replace text in a file",
    "parameters": {
      "type": "object",
      "properties": {
        "search": {
          "type": "string",
          "description": "Text to search for (special characters should be escaped)"
        },
        "replace": {
          "type": "string",
          "description": "Replacement text"
        },
        "file": {
          "type": "string",
          "description": "File to modify"
        }
      },
      "required": ["search", "replace", "file"]
    }
  }
}
```

## Performance Optimization

### 1. Output Truncation

For tools with verbose output, use `truncated_chars`:

```json
{
  "log_tail": {
    "type": "command",
    "command": "tail -n 100 {log_file}",
    "truncated_chars": 2000,
    "description": "Show last 100 lines of a log file",
    "parameters": {
      "type": "object",
      "properties": {
        "log_file": {
          "type": "string",
          "description": "Path to log file"
        }
      },
      "required": ["log_file"]
    }
  }
}
```

### 2. Timeouts

Set appropriate timeouts for long-running tools:

```json
{
  "timed_operation": {
    "type": "command",
    "command": "timeout 60s long_running_process",
    "description": "Run a process with a 60-second timeout"
  }
}
```

## Conclusion

When configuring MCP tools for AI Coder:

1. Start with simple, well-tested tools
2. Always consider security implications
3. Provide clear descriptions and preview commands
4. Handle errors gracefully
5. Set appropriate resource limits
6. Test thoroughly before deployment
7. Monitor tool usage and performance
8. Regularly review and update your tool configurations

By following these examples and best practices, you can create a robust and secure MCP tool configuration that enhances the capabilities of AI Coder while maintaining safety and performance.
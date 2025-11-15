# Glob Plugin

A file pattern matching plugin for AI Coder that provides glob-style file searching capabilities.

## Features

- **File Pattern Matching**: Find files using glob patterns like `*.py`, `**/*.md`, `test_*`
- **Recursive Search**: Support for `**` pattern to search subdirectories recursively
- **Multiple Tools**: Uses ripgrep (`rg`) when available, falls back to fd-find (`fd`), then Python glob
- **AI Integration**: Provides a `glob` tool that the AI can use to find files
- **User Commands**: `/glob` and `/g` commands for manual file searching
- **Performance**: Limits results to prevent overwhelming output (default: 2000 files)

## Installation

The plugin is automatically loaded when placed in the plugins directory. No additional configuration needed.

## Usage

### AI Tool Usage
The AI can use the `glob` tool to find files:
```
AI: Let me find all Python files in the project.
[glob(pattern="**/*.py")]
```

### User Commands

#### Basic Pattern Matching
```bash
/glob *.py              # Find all Python files in current directory
/glob **/*.py           # Find all Python files recursively
/glob test_*            # Find files starting with 'test_'
/glob *.md              # Find all Markdown files
```

#### Advanced Patterns
```bash
/glob aicoder/**/*.py  # All Python files in aicoder directory
/glob src/**/*.js       # All JavaScript files in src directory
/glob **/*test*         # Files with 'test' in the name
```

#### Help and Status
```bash
/glob help              # Show help and examples
/glob                   # Show tool status and available search tools
```

## Pattern Syntax

The plugin supports standard glob patterns:

- `*` - Match any characters (except directory separators)
- `**` - Match any characters, including directory separators (recursive)
- `?` - Match any single character
- `[abc]` - Match any character in the set
- `[a-z]` - Match any character in the range

## Tool Priority

The plugin tries tools in this order for best performance:

1. **ripgrep (rg)** - Fastest, best for large codebases
2. **fd-find (fd/fdfind)** - Very fast, user-friendly
3. **Python glob** - Always available, fallback option

## Examples

### Common Development Patterns
```bash
# Find configuration files
/glob **/*.json
/glob **/*.yaml
/glob **/*.yml
/glob **/*.toml

# Find test files
/glob **/test_*.py
/glob **/*_test.py
/glob **/tests/**/*.py

# Find documentation
/glob **/*.md
/glob **/*.rst
/glob **/*.txt

# Find specific file types
/glob **/*.js
/glob **/*.ts
/glob **/*.jsx
/glob **/*.tsx
```

### Project Structure Analysis
```bash
# Find main source files
/glob src/**/*.py
/glob lib/**/*.py

# Find build files
/glob **/Makefile
/glob **/CMakeLists.txt
/glob **/package.json
/glob **/requirements.txt
```

## Configuration

The plugin uses these default settings:
- **File Limit**: 2000 files (to prevent overwhelming output)
- **Timeout**: 30 seconds per search
- **Tools**: ripgrep → fd-find → Python glob

## Error Handling

The plugin provides clear error messages for:
- Empty patterns
- Permission errors
- Search timeouts
- Tool unavailability

## Performance Notes

- ripgrep (`rg`) is preferred for large codebases due to its speed
- fd-find (`fd`) provides the most intuitive user experience
- Python glob works everywhere but may be slower on large directories
- Results are automatically limited to prevent terminal flooding

## Integration

The plugin integrates seamlessly with AI Coder:
- Automatically registers the `glob` tool for AI use
- Adds `/glob` and `/g` commands to the command interface
- Uses the same pattern syntax as traditional shell globbing
- Respects AI Coder's approval and security systems

## Troubleshooting

### Tool Not Found
If ripgrep or fd-find are not available, the plugin automatically falls back to Python glob. Install the tools for better performance:
```bash
# Install ripgrep
sudo apt-get install ripgrep  # Ubuntu/Debian
brew install ripgrep          # macOS

# Install fd-find
sudo apt-get install fd-find  # Ubuntu/Debian
brew install fd               # macOS
```

### No Results
- Check your pattern syntax
- Verify files exist in the expected location
- Try broader patterns first, then refine

### Performance Issues
- Use more specific patterns to reduce search scope
- Consider installing ripgrep or fd-find for better performance
- Use the file limit to control output size
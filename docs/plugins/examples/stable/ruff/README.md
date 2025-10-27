# Ruff Plugin

Automatic Python code quality checks for AI Coder using [Ruff](https://github.com/astronomer/ruff).

## Features

- **Automatic Quality Checks**: Runs `ruff check` on Python files when they are saved or edited
- **Issue Reporting**: Creates user messages asking the AI to fix any ruff issues found
- **Optional Auto-Formatting**: Can automatically format code with `ruff format`
- **Graceful Fallback**: Plugin deactivates gracefully if ruff is not installed
- **Persistent Settings**: Configuration persists across sessions using `/ruff` commands
- **Configurable**: Customize behavior via commands, environment variables, or plugin constants

## Installation

1. Install ruff (required):
   ```bash
   pip install ruff
   ```

2. Copy the plugin to your plugins directory:
   ```bash
   cp docs/plugins/examples/unstable/ruff/ruff.py ~/.config/aicoder/plugins/
   ```

3. Restart AI Coder

## Configuration

### Commands

The plugin can be controlled using `/ruff` commands:

- **/ruff** - Show current status and settings
- **/ruff help** - Show help for ruff commands
- **/ruff on** - Enable ruff checking
- **/ruff off** - Disable ruff checking
- **/ruff format on** - Enable auto-formatting
- **/ruff format off** - Disable auto-formatting
- **/ruff check args <args>** - Set ruff check arguments
- **/ruff format args <args>** - Set ruff format arguments

Examples:
```bash
/ruff                    # Show status
/ruff on                 # Enable checking
/ruff format on          # Enable auto-formatting
/ruff check args --fix   # Set check args to include fixes
/ruff format args --line-length=100  # Set format args
```

Settings are persisted across sessions.

### Environment Variables

The plugin can also be configured using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RUFF_FORMAT` | `false` | Enable auto-formatting with ruff format (accepts: `1`, `true`, `on`) |
| `RUFF_CHECK_ARGS` | `""` | Additional arguments for `ruff check` |
| `RUFF_FORMAT_ARGS` | `""` | Additional arguments for `ruff format` |

### Examples

Enable auto-formatting (any of these work):
```bash
export RUFF_FORMAT=1
# or
export RUFF_FORMAT=true
# or
export RUFF_FORMAT=on
```

Use specific ruff configuration:
```bash
export RUFF_CHECK_ARGS="--config=pyproject.toml"
export RUFF_FORMAT_ARGS="--config=pyproject.toml"
```

### Priority Order

Settings are applied in this priority order:
1. `/ruff` commands (highest priority, persistent)
2. Environment variables (fallback)
3. Plugin defaults (lowest priority)

## Usage

The plugin works automatically in the background:

1. When you create or edit a `.py` file using `write_file` or `edit_file`
2. The plugin runs `ruff check` on the file
3. If issues are found, it creates a user message asking you to fix them
4. If auto-format is enabled, it runs `ruff format` before the check

### Example Workflow

```python
# AI creates a file with some issues
write_file("example.py", """
def hello():
    print('Hello')
    x=1+2
    return x
""")

# Plugin output:
# ✨ Auto-formatted example.py
#
# 🔍 **Ruff Issues Detected in /path/to/example.py**
#
# Please fix all the problems found by ruff in the file just saved:
# ```
# example.py:2:11: FURB118 Use f-string instead of .format() or %...
# example.py:3:5: E701 Multiple statements on one line (colon)
# example.py:3:5: E702 Multiple statements on one line (semicolon)
# ```
#
# Use the appropriate tools to fix these issues. The file has already been saved, so you need to edit it again to resolve the problems.
```

## Behavior

### When Ruff is Not Installed

- The plugin will detect this during initialization
- It will print a warning and **not** monkey patch the tools
- No functionality will be affected

### When Ruff is Installed

- The plugin monkey patches `write_file` and `edit_file`
- After each file operation, it runs ruff checks on `.py` files
- Issues are reported as user messages in the conversation
- Auto-formatting runs before checks if enabled (set `RUFF_FORMAT=1/true/on`)
- **Transparent alerts**: When issues are found, the plugin displays clear console alerts explaining that it's asking the AI to fix the problems

### User Transparency

The plugin provides clear feedback when it takes action:

```
============================================================
🤖 **RUFF PLUGIN ACTION**
============================================================
⚠️  Code quality issues detected! The Ruff plugin is now
   asking the AI to automatically fix these problems.
============================================================

🔍 **Ruff Plugin: Issues Detected in file.py**
[... detailed ruff output ...]

🤖 **Plugin Action**: The AI will now attempt to fix these issues automatically.
📁 **File**: file.py
🔧 **Tool**: Use edit_file or write_file to resolve the problems
============================================================
✅ Ruff plugin message added to conversation
============================================================
```

This ensures you're always aware when the plugin is asking the AI to make changes to your code.

### Format Notifications

When auto-formatting actually changes a file, the plugin will notify you:

```
🎨 **Ruff Plugin: File Formatted**

The Ruff plugin automatically formatted the file:

📁 **File**: /path/to/file.py
✨ **Action**: Code formatting applied
📝 **Details**: 1 file reformatted

The file has been reformatted in-place to improve code style and consistency.
```

### File Types

- Only files ending with `.py` are checked
- Other file types are ignored

## Troubleshooting

### Plugin Not Loading

1. Check if ruff is installed: `ruff --version`
2. Verify the plugin is in the correct directory
3. Check AI Coder startup messages for plugin loading status

### Ruff Check Issues

1. Verify ruff configuration in `pyproject.toml` or `.ruff.toml`
2. Check file permissions
3. Ensure the file is valid Python syntax

### Auto-Format Not Working

1. Enable with `/ruff format on` or set `RUFF_FORMAT=1` (or `true`/`on`) environment variable
2. Check that ruff format works manually: `ruff format yourfile.py`

### Commands Not Working

1. Use `/ruff help` to see available commands
2. Check that the plugin loaded successfully during AI Coder startup
3. Verify persistent config is available

## Development

The plugin follows AI Coder's plugin system patterns:

- Uses `on_aicoder_init` for initialization
- Monkey patches internal tool functions
- Integrates with the message history system
- Handles errors gracefully
- Supports persistent configuration

### File Structure

```
ruff/
├── ruff.py          # Main plugin implementation
├── test_ruff_plugin.py  # Test suite
├── install_plugin.sh     # Installation script
└── README.md        # This file
```

## Testing

Run the test suite:
```bash
cd docs/plugins/examples/unstable/ruff
python test_ruff_plugin.py
```

## Installation Script

Use the provided installation script:
```bash
cd docs/plugins/examples/unstable/ruff
bash install_plugin.sh
```

## License

This plugin follows the same license as AI Coder.
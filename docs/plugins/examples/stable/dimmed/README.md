# Dimmed Plugin

A plugin for AI Coder that automatically applies dimmed formatting to print statements that match configurable regex patterns.

## Features

- **Multiple regex patterns** - Configure as many patterns as you need
- **High performance** - Pre-compiled regex patterns for fast matching
- **Hybrid configuration** - Project-local, global, and environment variable support
- **Runtime control** - Add/remove patterns without restarting
- **Simple config format** - One regex per line in plain text files
- **Non-intrusive** - Falls back gracefully if patterns are invalid

## How It Works

1. **Monkey patches** the built-in `print()` function
2. **Checks each string argument** against all configured regex patterns
3. **If ANY pattern matches**, the entire string is wrapped with ANSI dim codes
4. **Preserves all original print behavior** (sep, end, file, flush)

## What It Affects

The plugin affects **standard Python `print()` calls** in AI Coder, including:

✅ **What Gets Dimmed:**
- Tool execution output (`Reading file [config.yaml]`)
- Command handler status messages (`Success: Operation complete`)
- Plugin messages (`[theme] Applied dark theme`)
- Debug output (`Debug: API request sent`)
- Warning and error messages (`Warning: File exists`, `Error: Permission denied`)
- File operations in brackets (`[main.py]`, `[src/utils.py]`)

❌ **What Does NOT Get Dimmed:**
- AI assistant responses (streamed directly, bypassing `print()`)
- User input display
- Real-time token counts and usage stats

**This is intentional** - AI responses use a custom streaming system that would be complex and fragile to patch. The plugin focuses on system output where it can provide reliable value without interfering with core functionality.

## Configuration

### Priority Order

The plugin loads patterns in this priority order:

1. **Project-local config** (`.dt-aicoder/dimmed.conf`) - Highest priority
2. **Global config** (`~/.config/aicoder/dimmed.conf`) - Fallback
3. **Environment variables** (`AICODER_DIMMED_PATTERNS`) - Final fallback
4. **Default pattern** (`r'\[.*?\]'`) - Ultimate fallback

### Config File Format

Create `.dt-aicoder/dimmed.conf` in your project:

```
# Dimmed Plugin Configuration
# One regex pattern per line - if any matches, print is dimmed
# Lines starting with # are comments

# Dim text in brackets
\[.*?\]

# Dim warning messages
Warning:.*

# Dim TODO comments
\bTODO\b

# Dim error messages
^Error:.*

# Dim debug output
\[DEBUG\].*
```

### Environment Variables

```bash
# Multiple patterns (comma-separated)
export AICODER_DIMMED_PATTERNS='\[.*?\],Warning:.*,\bTODO\b'

# Enable/disable plugin
export AICODER_DIMMED_ENABLED=true
```

## Commands

Use `/dimmed` command in AI Coder:

```
/dimmed                    # Show current patterns and status
/dimmed add <pattern>      # Add a new pattern (temporary)
/dimmed remove <pattern>   # Remove a pattern (temporary)
/dimmed clear              # Clear all patterns (temporary)
/dimmed save               # Save to project config (.dt-aicoder/dimmed.conf)
/dimmed save global        # Save to global config (~/.config/aicoder/dimmed.conf)
/dimmed reload             # Reload from config files
/dimmed on                 # Enable dimmed output
/dimmed off                # Disable dimmed output
/dimmed help               # Show help
```

## Pattern Examples

Common useful patterns:

```regex
# Text in brackets [like this]
\[.*?\]

# Text in parentheses (like this)
\(.*?\)

# Warning messages
Warning:.*

# Error messages
^Error:.*

# TODO comments
\bTODO\b

# Debug output
\[DEBUG\].*

# Log levels
^(INFO|WARN|ERROR|DEBUG):.*

# File paths
/[\w/.-]+\.(py|js|ts|md|txt|json|yaml|yml)$

# URLs
https?://[^\s]+

# Numbers
\b\d+\.?\d*\b

# IP addresses
\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b
```

## Installation

1. **Copy the plugin** to your AI Coder plugins directory:
   ```bash
   # For system-wide installation
   sudo cp dimmed.py /usr/local/lib/aicoder/plugins/
   
   # Or user installation
   mkdir -p ~/.config/aicoder/plugins
   cp dimmed.py ~/.config/aicoder/plugins/
   ```

2. **Restart AI Coder** or reload plugins

3. **Configure patterns** using commands or config files

## Usage Examples

### Basic Usage

```python
# With default pattern r'\[.*?\]'
print("This [is dimmed] text")           # Dimmed: [is dimmed]
print("This is normal text")              # Normal
print("Warning: [attention needed]")      # Dimmed: Warning: [attention needed]
```

### Multiple Patterns

```python
# With patterns: r'\[.*?\]', r'Warning:.*', r'\bTODO\b'
print("This [is dimmed]")                 # Dimmed (brackets)
print("Warning: system low memory")       # Dimmed (Warning:)
print("TODO: fix this bug")               # Dimmed (TODO)
print("Normal output")                    # Normal
```

### Project-Specific Configuration

Create `.dt-aicoder/dimmed.conf` in your project:

```
# Python-specific patterns
\bimport\b
\bfrom\b
\bdef\b
\bclass\b
^\s*#.*$

# JSON/API patterns
\{.*?\}
\[.*?\]
"status":.*
```

## Performance

The plugin is optimized for performance:

- **Pre-compiled regex patterns** - Compiled once at startup
- **Early exit** - Stops checking after first match
- **Minimal overhead** - Only processes string arguments
- **Cached pattern objects** - No re-compilation during print calls

Typical performance: ~0.1-0.5ms per print call with 10 patterns.

## Troubleshooting

### Debug Mode

Set `DEBUG=1` to see startup information:

```bash
DEBUG=1 aicoder
```

### Invalid Patterns

Invalid regex patterns are skipped with warnings:
```
⚠️ Warning: Invalid regex pattern '[invalid': missing ]
```

### Pattern Not Working

1. **Check regex syntax** - Use online regex testers
2. **Test with /dimmed add** - Add pattern temporarily first
3. **Verify escaping** - Use raw strings or proper escaping
4. **Check pattern order** - First match wins

### Plugin Not Loading

1. **Check file location** - Must be in plugins directory
2. **Check file name** - Must end with `.py`
3. **Check permissions** - Must be readable
4. **Check syntax** - Run `python dimmed.py` to test

## Testing

Run the test suite:

```bash
cd /path/to/dimmed/plugin
python test_dimmed.py
```

Tests cover:
- Pattern matching and dimming
- Configuration loading/saving
- Pattern compilation and caching
- Performance benchmarks
- Command handling

## Contributing

To contribute:

1. **Test thoroughly** - Add tests for new features
2. **Maintain performance** - Keep regex pre-compilation
3. **Preserve compatibility** - Don't break existing configs
4. **Document changes** - Update README and help text

## License

This plugin follows the same license as AI Coder.
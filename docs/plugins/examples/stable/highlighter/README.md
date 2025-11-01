# Dynamic Highlighting Plugin

A powerful text highlighting plugin for AI Coder that provides rule-based pattern matching with advanced styling capabilities. This plugin can replace the dimmed plugin and offers much more flexible text styling.

## Features

- **Multiple highlighting rules** with priority-based application
- **Background and foreground colors** with automatic contrast calculation
- **Text formatting** (bold, italic, underline, and combinations)
- **Sequential rule application** - lower priority rules applied first, higher priority rules override
- **Hybrid configuration system** - project > global > environment > runtime
- **Backward compatibility** with existing dimmed plugin configurations
- **JSON-based rule configuration** for complex styling
- **Runtime rule management** with comprehensive command interface

## Installation

Copy the `highlighter.py` file to your plugins directory (typically `~/.config/aicoder/plugins/`).

## Configuration

### Configuration Files

The plugin follows this priority order:

1. **Project config**: `.aicoder/highlighter.json` (highest priority)
2. **Global config**: `~/.config/aicoder/highlighter.json` (fallback)
3. **Environment variables** (final fallback)
4. **Runtime commands** (temporary changes)

### JSON Configuration Format

```json
{
  "version": "1.0",
  "rules": [
    {
      "name": "critical_error",
      "pattern": "\\[!\\]",
      "style": {
        "background": "bright_red",
        "foreground": "auto_contrast",
        "bold": true
      },
      "priority": 100
    },
    {
      "name": "error_text",
      "pattern": "ERROR:",
      "style": {
        "background": "red",
        "foreground": "white",
        "bold": true
      },
      "priority": 90
    },
    {
      "name": "success",
      "pattern": "\\[✓\\]",
      "style": {
        "background": "bright_green",
        "foreground": "black",
        "bold": true
      },
      "priority": 95
    },
    {
      "name": "warning",
      "pattern": "WARNING:",
      "style": {
        "background": "bright_yellow",
        "foreground": "black"
      },
      "priority": 80
    },
    {
      "name": "dim_tool_output",
      "pattern": "^Tool result:|Running command:|File modified:",
      "style": {
        "foreground": "dim"
      },
      "priority": 10
    }
  ]
}
```

### Environment Variables

- `AICODER_HIGHLIGHTER_ENABLED` - Enable/disable highlighting (default: 'true')
- `AICODER_HIGHLIGHTER_RULES` - Simple comma-separated rules (fallback)
- `AICODER_HIGHLIGHTER_CONFIG` - JSON configuration string (fallback)

Simple format example:
```bash
AICODER_HIGHLIGHTER_RULES="\\[!\\]:bright_red:auto_contrast:true,\\[✓\\]:bright_green:black:true"
```

## Commands

### Basic Commands

- `/highlight` - Show current rules and status
- `/highlight list` - List all current rules with details
- `/highlight help` - Show command help

### Rule Management

- `/highlight add <pattern> [options]` - Add a new rule (temporary)
- `/highlight remove <name>` - Remove a rule (temporary)
- `/highlight clear` - Clear all rules (temporary)

### Configuration

- `/highlight save` - Save current rules to project config
- `/highlight save global` - Save current rules to global config
- `/highlight reload` - Reload from config files

### Control

- `/highlight on` - Enable highlighting
- `/highlight off` - Disable highlighting

### Migration

- `/highlight migrate-dimmed` - Import existing dimmed plugin configurations

## Rule Options

### Style Options

- `--foreground=<color>` - Text color
- `--background=<color>` - Background color
- `--bold` - Make text bold
- `--italic` - Make text italic
- `--underline` - Make text underlined
- `--priority=<number>` - Rule priority (higher wins conflicts)
- `--name=<name>` - Rule name (required for some operations)

### Color Options

#### Foreground Colors
- `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`
- `bright_red`, `bright_green`, `bright_yellow`, `bright_blue`
- `bright_magenta`, `bright_cyan`, `bright_white`
- `dim` - Dimmed text
- `auto_contrast` - Automatically calculates contrast for background color

#### Background Colors
- `none` (default/transparent)
- `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`
- `bright_red`, `bright_green`, `bright_yellow`, `bright_blue`
- `bright_magenta`, `bright_cyan`, `bright_white`

## Examples

### Basic Highlighting

```bash
# Critical errors with bright red background
/highlight add "\\[!\\]" --background=bright_red --foreground=auto_contrast --bold --priority=100

# Success indicators with green background
/highlight add "\\[✓\\]" --background=bright_green --foreground=black --bold --priority=95

# Error text with red background
/highlight add "ERROR:" --background=red --foreground=white --bold --priority=90

# Warnings with yellow background
/highlight add "WARNING:" --background=bright_yellow --foreground=black --priority=80

# Information with blue foreground
/highlight add "INFO:" --foreground=bright_blue --priority=70

# Dim tool output (like dimmed plugin)
/highlight add "Tool result:" --foreground=dim --priority=10
```

### Advanced Styling

```bash
# Combined styling
/highlight add "CRITICAL" --background=bright_red --foreground=white --bold --underline --priority=100

# Multiple formatting options
/highlight add "IMPORTANT" --foreground=bright_yellow --bold --italic --priority=85
```

### Named Rules

```bash
# Add rule with custom name for easier management
/highlight add "\\[!\\]" --name=critical_alert --background=bright_red --foreground=auto_contrast --bold --priority=100

# Remove by name
/highlight remove critical_alert
```

## How It Works

### Priority-Based Application

The plugin applies rules in **priority order** (low → high):

1. **Lower priority rules** are applied first
2. **Higher priority rules** are applied later
3. **Higher priority rules override** lower ones naturally
4. **Last ANSI code wins** (terminal behavior)

### Example

For text: `"ERROR: Database failed [!] WARNING: Retrying"`

With rules:
- `ERROR:` (priority 50) → red background
- `[!]` (priority 100) → bright red background  
- `WARNING:` (priority 40) → yellow background

Result:
1. Apply ERROR: (red) → `"{RED}ERROR:{RESET} Database failed [!] WARNING: Retrying"`
2. Apply WARNING: (yellow) → `"{RED}ERROR:{RESET} Database failed [!] {YELLOW}WARNING:{RESET} Retrying"`
3. Apply [!] (bright red) → `"{RED}ERROR:{RESET} Database failed {BRIGHT_RED}[!]{RESET} {YELLOW}WARNING:{RESET} Retrying"`

### Multi-Rule per String

Multiple rules can apply to the same string. Non-overlapping matches all get their styling, while overlapping regions use the higher priority rule.

## Migration from Dimmed Plugin

### Automatic Import

The plugin can automatically import existing dimmed plugin configurations:

```bash
/highlight migrate-dimmed
```

This converts dimmed patterns to highlighting rules with:
- Style: `{"foreground": "dim"}`
- Priority: `10` (low, so highlighting rules win)
- Name: `dimmed_<filename>_<number>`

### Manual Migration

Your existing `.aicoder/dimmed.conf` or `~/.config/aicoder/dimmed.conf` files will be automatically detected and imported with low priority.

## Compatibility

- **Compatible with dimmed plugin** - Can run alongside and will auto-import dimmed rules
- **Compatible with theme plugin** - Works with all color themes
- **Terminal compatibility** - Uses standard ANSI escape codes
- **Performance optimized** - Pre-compiled patterns and efficient string operations

## Troubleshooting

### Rules Not Applying

1. Check if highlighting is enabled: `/highlight`
2. Verify rule syntax: `/highlight list`
3. Check priority ordering: Higher priority rules override lower ones
4. Test pattern separately: Use simple patterns first

### Color Issues

1. Use `auto_contrast` for foreground color with backgrounds
2. Check terminal color support
3. Try basic colors first, then bright colors

### Performance

1. Use specific patterns over general ones (`ERROR:` vs `.*`)
2. Set appropriate priorities to avoid unnecessary rule processing
3. Clear unused rules: `/highlight clear`

## Tips

- Use **descriptive names** for rules to make management easier
- Set **logical priorities** (critical errors: 100, warnings: 80, info: 60)
- Use **auto_contrast** for automatic readability
- **Save frequently** to preserve configurations: `/highlight save`
- **Test patterns** with temporary rules before making permanent
- **Use the dimmed import** to preserve existing functionality while adding new features

## Integration

The plugin integrates seamlessly with:

- **Streaming adapter** - Highlights real-time AI responses
- **Tool output** - Styles command results and file operations
- **Error messages** - Makes critical information stand out
- **Success indicators** - Highlights completed operations
- **Warning messages** - Makes important notices visible

For developers looking to extend the plugin, the core logic is in the `HighlightRule` class and the `_highlighter_print` function, which can be easily modified for additional features.
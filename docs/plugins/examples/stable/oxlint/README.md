# Oxlint Plugin

Automatic JavaScript/TypeScript code quality checks using oxlint for AI Coder.

## Features

- **Automatic checking**: Runs `bun x oxlint` on JavaScript/TypeScript files when saved
- **AI notification**: Automatically asks AI to fix detected issues
- **Optional auto-formatting**: Can automatically fix issues with `bun x oxlint --fix`
- **Configurable**: Configure via commands, environment variables, or persistent config
- **Graceful fallback**: Works even when oxlint is not installed

## Supported File Types

- `.js` - JavaScript files
- `.jsx` - React JavaScript files
- `.ts` - TypeScript files
- `.tsx` - React TypeScript files
- `.mjs` - ES modules
- `.cjs` - CommonJS modules

## Installation

1. Install oxlint in your project:
```bash
bun add -D oxlint
```

2. Install the oxlint plugin:
```bash
# Run from aicoder directory
./install-plugins.sh
# Then select oxlint.py from the list
```

3. The plugin will automatically activate when bun is available.

## Usage

The plugin automatically runs oxlint checks when you save JavaScript/TypeScript files through AI Coder's file operations.

### Commands

- `/oxlint` - Show current plugin status
- `/oxlint check on|off` - Enable/disable checking
- `/oxlint format on|off` - Enable/disable auto-formatting
- `/oxlint args <arguments>` - Set custom oxlint arguments
- `/oxlint help` - Show help information

### Example

```
/oxlint check on
/oxlint format on
/oxlint args --deny-warnings --quiet
```

## Configuration

### Environment Variables

- `OXLINT_FORMAT` - Enable auto-formatting (default: False)
- `OXLINT_ARGS` - Additional oxlint arguments (default: "")

### Configuration Priority

1. Plugin commands (highest priority)
2. Environment variables
3. Plugin constants (default values)

## How It Works

1. **File Detection**: Monitors `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs` files
2. **Automatic Checking**: Runs `bun x oxlint <file>` on file changes
3. **Issue Reporting**: If issues found, creates user message asking AI to fix them
4. **Auto-formatting**: Optionally runs `bun x oxlint --fix <file>` if no issues exist

## Default Behavior

- Checking is **enabled** by default
- Auto-formatting is **disabled** by default
- Uses default oxlint configuration
- Reports all issues found by oxlint

## Requirements

- Bun runtime (`bun` command must be available)
- oxlint package installed (`bun add -D oxlint`)

## Error Handling

- Gracefully handles missing bun or oxlint
- Provides clear installation instructions
- Falls back to disabled mode when tools unavailable
- Timeout protection for long-running lint operations

## Troubleshooting

### Oxlint not found
```
[!] Oxlint not found - plugin will be disabled
[i] Install with: bun add -D oxlint
```

Install oxlint as a dev dependency in your project.

### Bun not available
The plugin requires Bun runtime. Install Bun from https://bun.sh

### Slow performance
For large projects, consider using oxlint arguments to limit scope:
```
/oxlint args --quiet --deny-warnings
```

## Examples

### Enable auto-formatting
```
/oxlint format on
```

### Set custom oxlint arguments
```
/oxlint args --deny-warnings --quiet --rule unicorn/no-typeof-undefined
```

### Check current status
```
/oxlint
```

This will show:
- Whether checking is enabled
- Whether auto-formatting is enabled
- Current oxlint arguments
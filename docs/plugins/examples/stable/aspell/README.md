# Aspell Spell Check Plugin

This plugin automatically checks the spelling of user input and guidance text using the aspell spell checker. If any misspelled words are found, it displays them in red with suggestions.

## Features

- **Automatic spell checking**: Checks user prompts before they're sent to the AI
- **Guidance text checking**: Also checks spelling in guidance text
- **Red error display**: Shows misspelled words in red with suggestions
- **Minimal performance**: Uses caching to avoid repeated checks
- **Graceful fallback**: Works even if aspell is not available
- **Configurable**: Environment variables to control behavior

## Installation

### Option 1: Install Script (Recommended)
```bash
bash docs/plugins/examples/stable/aspell/install_plugin.sh
```

### Option 2: Manual Installation
```bash
mkdir -p ~/.config/aicoder/plugins
cp docs/plugins/examples/stable/aspell/aspell.py ~/.config/aicoder/plugins/
```

## Configuration

### Environment Variables

- `ASPELL_CHECK`: Enable/disable spell checking (default: `true`)
- `ASPELL_LANG`: Language to use (default: `en`)

### Examples

```bash
# Disable spell checking
export ASPELL_CHECK=false

# Use Spanish dictionary
export ASPELL_LANG=es

# Use American English
export ASPELL_LANG=en_US
```

## Usage

Once installed, the plugin automatically activates when you start AI Coder:

1. **User prompts**: Every time you enter text, it's spell-checked
2. **Guidance text**: When you provide guidance for tool execution, it's also checked
3. **Error display**: Misspelled words show in red with suggestions

### Example Output

```
User: This is a mispelled word and anotr one
Spell check: mispelled → misspelled; anotr → another
Note: These words may be misspelled. Please verify before sending.

AI: I'll help you with your request. I noticed some potential spelling issues...
```

## Requirements

- **aspell**: The aspell spell checker must be installed on your system
- **Python**: Standard library modules only (no additional dependencies)

### Installing aspell

#### Ubuntu/Debian
```bash
sudo apt-get install aspell aspell-en
```

#### macOS
```bash
brew install aspell
```

#### Arch Linux
```bash
sudo pacman -S aspell
```

## How It Works

1. **Input interception**: The plugin monkey-patches Python's `builtins.input` function
2. **Spell checking**: Uses `aspell list` to find misspelled words
3. **Suggestions**: Uses `aspell -a` to get spelling suggestions for each error
4. **Display**: Shows errors in red with suggestions
5. **Caching**: Results are cached to improve performance

## Plugin Architecture

This plugin follows AI Coder's plugin system:
- Uses `on_aicoder_init()` hook for initialization
- Implements graceful fallback when aspell is unavailable
- Uses environment variables for configuration
- Provides user-friendly status messages

## Troubleshooting

### Plugin loads but no spell checking
- Check if aspell is installed: `which aspell`
- Verify spell checking is enabled: `echo $ASPELL_CHECK`
- Check language setting: `echo $ASPELL_LANG`

### Performance issues
- The plugin uses caching to minimize aspell calls
- Large texts may take longer to check
- Consider disabling for very long prompts

### Colors not displaying correctly
- The plugin uses standard ANSI color codes
- Ensure your terminal supports colors
- Colors fallback gracefully if config module is unavailable

## Development

### Testing the Plugin
```bash
# Test spell checking manually
echo "This is mispelled" | aspell list -a

# Test with specific language
echo "mispelled" | aspell -a -l en
```

### Debug Mode
```bash
export DEBUG=1
# Run AI Coder to see plugin loading messages
```

## License

This plugin is part of AI Coder and follows the same licensing terms.
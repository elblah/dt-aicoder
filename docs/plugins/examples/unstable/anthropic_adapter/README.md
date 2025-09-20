# Anthropic Adapter Plugin

This plugin transforms OpenAI-style API calls to Anthropic-compatible ones by intercepting API requests and converting them to use the Anthropic API.

## Features

- Converts OpenAI chat completions API calls to Anthropic Messages API
- Handles tool calling conversion between OpenAI and Anthropic formats
- Manages API key and endpoint configuration
- Seamless integration with existing AI Coder functionality
- Automatic fallback to OpenAI if Anthropic fails

## Requirements

- anthropic Python library: `pip install anthropic`

## Installation

1. Copy the `anthropic_adapter` directory to your AI Coder plugins directory:
   ```bash
   cp -r anthropic_adapter ~/.config/aicoder/plugins/
   ```

2. Install the required dependency:
   ```bash
   pip install anthropic
   ```

## Configuration

Set the following environment variables:

```bash
# Required: Your Anthropic API key
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Optional: Specify which Anthropic model to use (default: claude-3-5-sonnet-20240620)
export ANTHROPIC_MODEL="claude-3-opus-20240229"
```

## How It Works

The plugin works by intercepting AI Coder's internal `_make_api_request` method and replacing it with a custom implementation that:

1. Converts OpenAI-style messages to Anthropic Messages API format
2. Extracts system messages (handled separately in Anthropic)
3. Converts tool definitions between OpenAI and Anthropic formats
4. Makes the actual API call to Anthropic
5. Converts the Anthropic response back to OpenAI format for compatibility

## Supported Models

The plugin works with all Anthropic Claude models:
- `claude-3-5-sonnet-20240620` (default)
- `claude-3-opus-20240229`
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307`

## Example Usage

```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-api-key-here"

# Optionally specify a model
export ANTHROPIC_MODEL="claude-3-opus-20240229"

# Run AI Coder - it will automatically use Anthropic
python -m aicoder
```
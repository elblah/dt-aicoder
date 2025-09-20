# Extra Scripts and Utilities

This directory contains helpful scripts and utilities for working with AI Coder.

## aicoder-start

A convenient launcher script for AI Coder that:
- Runs AI Coder in a sandboxed environment using firejail for security
- Creates a temporary copy of the aicoder.pyz file for execution
- Automatically cleans up temporary files on exit
- Can be run without sandboxing by setting `SANDBOX=0`

### Usage

```bash
# Run with sandboxing (default)
./aicoder-start

# Run without sandboxing
SANDBOX=0 ./aicoder-start
```

### Configuration

The script uses the following environment variables:
- `AICODER_PYZ_PATH`: Path to the aicoder.pyz file (defaults to `~/poc/aicoder/v2/aicoder.pyz`)

## aicoder-gemini

A specialized launcher for using AI Coder with Google's Gemini models:
- Provides an interactive model selection interface using fzf
- Sets up the proper environment variables for Gemini API access
- Configures token limits for optimal performance

### Usage

```bash
# Run with interactive model selection
./aicoder-gemini

# The script will prompt you to select from available models:
# - gemini-2.5-pro
# - gemini-2.5-flash
```

### Prerequisites

- `fzf` must be installed for interactive model selection
- `GEMINI_API_KEY` environment variable must be set with your Gemini API key

### Configuration

The script uses the following environment variables:
- `GEMINI_API_KEY`: Your Gemini API key
- `AUTO_COMPACT_THRESHOLD`: Token threshold for auto-compaction (defaults to 131072)

## aicoder-openai

A specialized launcher for using AI Coder with OpenAI models:
- Sets up the proper environment variables for OpenAI API access
- Configures token limits for optimal performance

### Usage

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your_openai_api_key_here

# Optionally specify a model (defaults to gpt-4o)
export MODEL=gpt-4o-mini

# Run with OpenAI models
./aicoder-openai
```

### Configuration

The script uses the following environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `MODEL`: OpenAI model to use (optional, defaults to gpt-4o)
- `AUTO_COMPACT_THRESHOLD`: Token threshold for auto-compaction (defaults to 131072)

## aicoder-glm

A specialized launcher for using AI Coder with Zhipu AI's GLM models:
- Sets up the proper environment variables for GLM API access
- Configures token limits for optimal performance

### Usage

```bash
# Set your GLM API key
export GLM_API_KEY=your_glm_api_key_here

# Run with GLM models
./aicoder-glm
```

### Configuration

The script uses the following environment variables:
- `GLM_API_KEY`: Your GLM API key (required)
- `AUTO_COMPACT_THRESHOLD`: Token threshold for auto-compaction (defaults to 131072)

## aicoder-cerebras

A specialized launcher for using AI Coder with Cerebras models:
- Provides an interactive model selection interface using fzf
- Sets up the proper environment variables for Cerebras API access
- Configures token limits for optimal performance

### Usage

```bash
# Set your Cerebras API key
export CEREBRAS_API_KEY=your_cerebras_api_key_here

# Run with interactive model selection
./aicoder-cerebras

# The script will prompt you to select from available models:
# - qwen-3-coder-480b
# - qwen-3-235b-a22b-instruct-2507
# - qwen-3-235b-a22b-thinking-2507
# - gpt-oss-120b
# - llama-4-maverick-17b-128e-instruct
# - llama-4-scout-17b-16e-instruct
```

### Prerequisites

- `fzf` must be installed for interactive model selection
- `CEREBRAS_API_KEY` environment variable must be set with your Cerebras API key

### Configuration

The script uses the following environment variables:
- `CEREBRAS_API_KEY`: Your Cerebras API key (required)
- `AUTO_COMPACT_THRESHOLD`: Token threshold for auto-compaction (defaults to 131072)

## aicoder-qwen

A specialized launcher for using AI Coder with Qwen models:
- Handles OAuth token management for Qwen API access
- Sets up the proper environment variables for Qwen API access
- Automatically checks and refreshes OAuth tokens
- Configures token limits for optimal performance

### Usage

```bash
# Ensure you have a valid OAuth JSON file at ~/.qwen/oauth_creds.json
# Run with Qwen models
./aicoder-qwen
```

### Prerequisites

- Valid OAuth credentials file at `~/.qwen/oauth_creds.json`
- `gojq` must be installed for JSON processing
- Token refresh script at `~/poc/renew-oauth-token/renew_oauth_token.py` (if token refresh is needed)

### Configuration

The script uses the following environment variables/files:
- `~/.qwen/oauth_creds.json`: OAuth credentials file (required)
- `AUTO_COMPACT_THRESHOLD`: Token threshold for auto-compaction (defaults to 131072)

## Security Notes

All scripts have been designed to avoid hardcoding API keys:
- API keys should be set as environment variables
- Scripts will check for required environment variables and exit with helpful error messages if missing
- OAuth tokens are read from secure credential files

## Customization

You can create your own launcher scripts based on these examples:
- Copy and modify the scripts for different AI providers
- Adjust sandboxing parameters for your security requirements
- Add custom environment variables for specific workflows
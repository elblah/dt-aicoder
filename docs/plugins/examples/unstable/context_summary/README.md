# Context Summary Plugin with Auto Compaction for AICoder

This enhanced plugin automatically summarizes long conversation contexts and compacts memory based on model-specific token limits to prevent token overflow. It provides both automatic context management and manual commands (`/summarize` and `/compact`) for users.

## Features

- **Automatic Summarization**: Automatically summarizes conversation context when message count exceeds threshold
- **Model-aware Auto Compaction**: Automatically compacts memory when approaching model-specific token limits
- **Detailed Reason Messages**: Clear messages explaining why compaction/summarization is being triggered
- **Enhanced Manual Commands**: Provides `/summarize` and `/compact` commands with detailed feedback including message counts and token usage
- **Configurable Thresholds**: Adjustable message count and token usage thresholds
- **Model-specific Token Limits**: Supports different token limits for various AI models

## Installation

1. Copy the plugin file to your AICoder plugins directory:
   ```bash
   cp context_summary.py /path/to/aicoder/plugins/
   ```

2. The plugin will be automatically loaded when AICoder starts.

## Configuration

The plugin can be configured by modifying these constants in the plugin file:

- `AUTO_SUMMARY_THRESHOLD`: Number of messages before auto-summarization (default: 50)
- `SUMMARY_INTERVAL`: Summarize every N messages after threshold (default: 20)
- `TOKEN_LIMIT_THRESHOLD`: Percentage of model token limit that triggers auto-compaction (default: 0.9)

## Supported Models and Token Limits

The plugin includes token limits for popular models:

- **OpenAI Models**:
  - gpt-5-nano: 128,000 tokens
  - gpt-4: 128,000 tokens
  - gpt-4-turbo: 128,000 tokens
  - gpt-4o: 128,000 tokens
  - gpt-3.5-turbo: 16,385 tokens

- **Qwen Models** (first tier):
  - qwen3-coder-plus: 32,768 tokens
  - qwen3-coder-flash: 32,768 tokens

- **Google Models**:
  - gemini-2.5-flash: 1,000,000 tokens
  - gemini-2.5-pro: 2,000,000 tokens

- **Cerebras Models**:
  - qwen-3-coder-480b: 32,768 tokens

## Usage

### Automatic Context Management

The plugin automatically manages context in two ways:

1. **Message Count Monitoring**: Summarizes context every 20 messages after reaching 50 messages
2. **Token Usage Monitoring**: Compacts memory when token usage exceeds 90% of the model's limit

### Manual Commands

Use the `/summarize` command to manually trigger context summarization:
```
/summarize
```

Use the `/compact` command to manually trigger context compaction:
```
/compact
```

## How It Works

1. **Monkey Patching**: The plugin monkey patches the `MessageHistory.add_assistant_message` method to add auto-summarization and auto-compaction functionality with detailed messaging.

2. **Enhanced Context Management**: 
   - Summarization uses the existing `summarize_context()` method to generate and add a context summary
   - Compaction uses the existing `compact_memory()` method to reduce memory usage while preserving context
   - Both operations provide clear feedback about why they were triggered and their impact

3. **Command Registration**: The plugin registers the `/summarize` and `/compact` commands with the AICoder instance after initialization, with enhanced feedback.

4. **Model Detection**: The plugin automatically detects the current model from environment variables and applies the appropriate token limits.

## Requirements

- AICoder v2.0 or later
- Access to the configured AI model for summarization

## Troubleshooting

If the plugin fails to load:
1. Ensure the plugin file is in the correct plugins directory
2. Check that AICoder has permission to read the plugin file
3. Verify that the AICoder version is compatible with the plugin

If the commands are not available:
1. Check that the plugin loaded successfully
2. Verify that the AICoder instance was properly initialized
3. Ensure no other plugins are conflicting with the command registration
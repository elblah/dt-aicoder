# Context Summary Plugin for AICoder

This plugin automatically summarizes long conversation contexts to prevent token overflow and provides a manual `/summarize` command for users to trigger context summarization.

## Features

- **Automatic Summarization**: Automatically summarizes conversation context when message count exceeds threshold
- **Manual Summarization**: Provides `/summarize` command for manual context summarization
- **Configurable Thresholds**: Adjustable message count thresholds for auto-summarization
- **Memory Management**: Automatically compacts memory after summarization

## Installation

1. Copy the plugin file to your AICoder plugins directory:
   ```bash
   cp 09_context_summary_plugin_final.py /path/to/aicoder/plugins/
   ```

2. The plugin will be automatically loaded when AICoder starts.

## Configuration

The plugin can be configured by modifying these constants in the plugin file:

- `AUTO_SUMMARY_THRESHOLD`: Number of messages before auto-summarization (default: 50)
- `SUMMARY_INTERVAL`: Summarize every N messages after threshold (default: 20)

## Usage

### Automatic Summarization

The plugin automatically summarizes the conversation context when:
- Message count exceeds `AUTO_SUMMARY_THRESHOLD`
- Every `SUMMARY_INTERVAL` messages after the threshold

### Manual Summarization

Use the `/summarize` command to manually trigger context summarization:
```
/summarize
```

## How It Works

1. **Monkey Patching**: The plugin monkey patches the `MessageHistory.add_assistant_message` method to add auto-summarization functionality.

2. **Command Registration**: The plugin registers the `/summarize` command with the AICoder instance after initialization.

3. **Context Summarization**: When triggered, the plugin uses the existing `summarize_context()` method of the `MessageHistory` class to generate and add a context summary.

## Requirements

- AICoder v2.0 or later
- Access to the configured AI model for summarization

## Troubleshooting

If the plugin fails to load:
1. Ensure the plugin file is in the correct plugins directory
2. Check that AICoder has permission to read the plugin file
3. Verify that the AICoder version is compatible with the plugin

If the `/summarize` command is not available:
1. Check that the plugin loaded successfully
2. Verify that the AICoder instance was properly initialized
3. Ensure no other plugins are conflicting with the command registration
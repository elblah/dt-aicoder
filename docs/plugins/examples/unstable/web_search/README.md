# Web Search Plugin

This plugin adds web search capability to AI Coder using DuckDuckGo. The AI can call the `web_search` tool to find information online.

## Features

- Performs web searches using DuckDuckGo's Instant Answer API
- Returns relevant search results directly to the AI
- No external dependencies required
- Automatically integrated with the AI Coder tool system
- Follows modern plugin architecture with proper tool registration

## Installation

1. Copy the `web_search` directory to your AI Coder plugins directory:
   ```bash
   cp -r web_search ~/.config/aicoder/plugins/
   ```

2. Run AI Coder - the web search tool will be automatically available

## Usage

The AI can use the `web_search` tool by calling it with a query parameter:

```json
{
  "name": "web_search",
  "arguments": {
    "query": "current population of Tokyo",
    "max_results": 3
  }
}
```

## Parameters

- `query` (string, required): The search query
- `max_results` (integer, optional, default: 5): Maximum number of results to return

## Example Output

```
Definition: Tokyo is the capital and most populous city of Japan.
- Tokyo has a population of approximately 13.96 million residents
- The greater Tokyo area has a population of over 37 million
```

## Benefits

- Access to current information not in AI training data
- Fact verification capabilities
- Up-to-date statistics and data
- No API key required (uses free DuckDuckGo service)
- Automatic system prompt integration for AI awareness

## Technical Details

- Uses modern plugin architecture with `on_aicoder_init` function
- Properly registers with the tool manager and registry
- Includes comprehensive error handling and parameter validation
- Adds web search capability information to the system prompt
- Compatible with current AI Coder versions

## Limitations

- Dependent on DuckDuckGo's Instant Answer API
- May not return results for all queries
- Rate limits may apply (handled gracefully)
- Results quality depends on API responses
# Web Search Plugin Summary

## Overview
The Web Search plugin adds internet search capabilities to AI Coder, allowing the AI to access current information not available in its training data.

## Key Features
- **No API Keys Required**: Uses DuckDuckGo's free Instant Answer API
- **Automatic Integration**: Seamlessly integrates with AI Coder's tool system
- **Real-time Information**: Access current data, news, and statistics
- **Zero Dependencies**: No additional Python packages required

## Tool Definition
```json
{
  "name": "web_search",
  "description": "Perform a web search to find information about a topic using DuckDuckGo",
  "parameters": {
    "query": "The search query",
    "max_results": "Maximum number of results to return (default: 5)"
  }
}
```

## When to Use
- Need current information (news, recent events)
- Require specific factual data (statistics, definitions)
- Want to verify information accuracy
- Working on tasks requiring up-to-date knowledge

## Example Usage
```json
{
  "name": "web_search",
  "arguments": {
    "query": "current population of Tokyo",
    "max_results": 3
  }
}
```

## Output Format
Returns a formatted string with search results, typically including:
- Definitions/Abstract information
- Related topics and facts
- Relevant data points

## Technical Details
- Uses DuckDuckGo Instant Answer API
- Timeout protection (10 seconds)
- Error handling for network issues
- JSON response parsing
- Result limiting to prevent information overload

## Benefits
- Extends AI knowledge beyond training data
- Enables fact-checking capabilities
- Provides access to real-time information
- Works without additional setup

## Limitations
- Dependent on DuckDuckGo API availability
- May not return results for all queries
- Rate limits may apply
- Results quality depends on API responses
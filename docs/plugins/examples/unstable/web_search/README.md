# Enhanced Web Search Plugin for AI Coder

This plugin adds **enhanced** web search capability to AI Coder using DuckDuckGo Lite HTML parsing instead of the limited DuckDuckGo API. The AI can call the `web_search` tool to find better information online.

## ✨ Enhanced Features

- **Better results** than DuckDuckGo API
- **No API dependencies** - Uses HTML parsing of DuckDuckGo Lite
- **No external dependencies** - Only Python standard library
- **Direct URLs** - Provides actual source URLs
- **Proper descriptions** - Extracts meaningful content snippets
- **Robust parsing** - Handles both search result formats
- **Error handling** - Graceful fallback and error messages

## Installation

1. Copy the plugin directory to your plugins folder:
   ```bash
   cp -r docs/plugins/examples/unstable/web_search ~/.config/aicoder/plugins/
   ```

2. Run AI Coder - the web search tool will be automatically available

## Usage

The AI can automatically use web search when needed, but you can also call it directly:

```python
{
  "name": "web_search",
  "arguments": {
    "query": "current population of Tokyo",
    "max_results": 3
  }
}
```

## Example Results

```
1. 3I/ATLAS Facts and FAQS - NASA Science
   Discovery Comet 3I/ATLAS was discovered by the NASA-funded ATLAS survey telescope in Rio Hurtado, Chile, and reported to the Minor Planet Center on July 1, 2025.
   URL: https://science.nasa.gov/solar-system/comets/3i-atlas/3i-atlas-facts-and-faqs/

2. 3I/ATLAS - Wikipedia
   3I/ATLAS was discovered in a starry region of the sky. The discovery image by ATLAS is shown in the inset image, which is a zoomed in view of the location where 3I/ATLAS was discovered.
   URL: https://en.wikipedia.org/wiki/3I/ATLAS
```

## Technical Details

### How It Works

1. **Search Query**: Sends query to DuckDuckGo Lite (text-based interface)
2. **HTML Parsing**: Extracts search results from HTML response
3. **URL Extraction**: Decodes DuckDuckGo redirect URLs to get actual destinations
4. **Description Parsing**: Extracts meaningful content snippets
5. **Formatting**: Returns clean, numbered results with titles, descriptions, and URLs

### Search Process

- **Page 1**: Uses GET request with DuckDuckGo redirect URLs (`uddg` parameter)
- **Page 2+**: Uses POST request with form parameters and direct URLs
- **Parsing**: Different regex patterns for different page formats
- **Pagination**: Handles DuckDuckGo's form-based pagination system

### Error Handling

- Network timeouts and connection errors
- HTML parsing failures
- Rate limiting detection
- Invalid input parameters
- Missing or malformed responses

## Benefits over DuckDuckGo API

| Feature | DuckDuckGo API | Enhanced Plugin |
|---------|------------------|----------------|
| Result Quality | Limited instant answers | Full search results |
| Dependencies | External API | None (HTML parsing) |
| URLs | Sometimes missing | Always included |
| Descriptions | Basic/varied | Properly extracted |
| Pagination | Limited | Full support |
| Reliability | Rate limited | More robust |

## Troubleshooting

### Getting 0 Results?
- DuckDuckGo may be rate-limiting automated requests
- Try simpler or different search queries
- Check network connectivity

### Error Messages?
- Network issues will show descriptive error messages
- Parsing errors fall back gracefully
- Invalid queries are validated upfront

### Performance?
- Search typically takes 1-3 seconds
- Page 1 (GET) is faster than subsequent pages (POST)
- Caching is not implemented to ensure fresh results

## File Structure

```
web_search/
├── __init__.py          # Plugin metadata
├── web_search.py        # Main plugin (single file with embedded library)
├── README.md           # This documentation
└── test_plugin.py      # Test script (optional)
```

## Configuration

No configuration required. The plugin works out of the box with:

- Default user agent header
- 10-second timeout
- Standard DuckDuckGo Lite interface
- Automatic retry logic (built into urllib)

## Security & Privacy

- **No API keys** required
- **No tracking** or user data collection
- **Standard HTTP requests** only
- **Rate limiting** respected through delays

## Updates

The plugin automatically handles DuckDuckGo's HTML structure changes through robust regex patterns. If parsing breaks:

1. DuckDuckGo likely updated their HTML structure
2. Plugin may need regex pattern updates
3. Fallback to basic DuckDuckGo API could be implemented

## Testing

The plugin includes comprehensive testing capabilities:

```bash
# Run the built-in unit tests (no network access required)
cd docs/plugins/examples/unstable/web_search
python test_plugin.py

# Run the built-in self-test in the plugin
python web_search.py

# Test with specific scenarios
python -c "
from web_search import execute_web_search
print(execute_web_search('python programming', 3))
"

# Test URL content fetching (requires lynx installation)
python -c "
from web_search import execute_get_url_content
print(execute_get_url_content('https://httpbin.org/html'))
"
```

### Test Coverage

The test suite includes:

1. **DuckDuckGo Search Tests**
   - Search initialization and validation
   - Query handling and result formatting
   - Error handling for network issues

2. **Web Search Tool Tests**
   - Tool definition validation
   - Parameter validation (query, max_results)
   - Result formatting and edge cases

3. **URL Content Tool Tests**
   - URL validation and security checks
   - Lynx integration and error handling
   - Content truncation for large responses
   - Timeout and network error handling

4. **Integration Tests**
   - Plugin import and structure validation
   - Tool registration verification

### Security Testing

The URL content tool includes extensive security testing:
- URL format validation (must be http/https)
- Timeout protection (30 second limit)
- Content length limits (8000 character max)
- Lynx installation verification
- Command error handling

All unit tests pass without requiring network access, making them suitable for CI/CD environments.

## License

This plugin is provided as-is for educational and development purposes. Uses only publicly accessible DuckDuckGo Lite interface.
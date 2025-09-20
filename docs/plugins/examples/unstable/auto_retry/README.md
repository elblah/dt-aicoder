# Auto Retry Plugin

This plugin provides automatic retry functionality for API errors, specifically designed to handle the case where you get "500 Internal Server Error" with "429 Too Many Requests" content, as well as other common API errors.

## Features

- **Smart Error Detection**: Automatically detects and retries common API errors
- **Rate Limiting Support**: Handles 429 errors and rate limiting scenarios
- **Server Error Recovery**: Retries 500, 502, 503, 504 server errors
- **Configurable**: Customize retry behavior with environment variables
- **User-Friendly**: Clear error messages and ESC key cancellation support

## Installation

1. Navigate to the plugin directory:
   ```bash
   cd /home/blah/poc/aicoder/v2/docs/plugins/examples/unstable/auto_retry
   ```

2. Run the installation script:
   ```bash
   ./install_plugin.sh
   ```

3. Or install manually by adding to your AI Coder configuration:
   ```bash
   export PYTHONPATH="/home/blah/poc/aicoder/v2/docs/plugins/examples/unstable/auto_retry:$PYTHONPATH"
   ```

## Configuration

Configure the plugin using environment variables:

```bash
# Set retry delay in seconds (default: 5)
export AUTO_RETRY_DELAY=5

# Set maximum number of retries (default: 3)
export AUTO_RETRY_MAX_RETRIES=3
```

## Usage

Once installed, the plugin automatically works in the background:

- When an API error occurs, it will automatically retry the request
- You'll see clear messages like: "🔄 Rate limiting error detected. Retrying in 10s (attempt 1/3)"
- Press ESC at any time to cancel retries
- The plugin handles your specific case of "500 Internal Server Error" with "429 Too Many Requests" content

## Error Types Handled

The plugin automatically retries these types of errors:

1. **HTTP 500** - Internal Server Error (especially with 429 content)
2. **HTTP 502** - Bad Gateway
3. **HTTP 503** - Service Unavailable
4. **HTTP 504** - Gateway Timeout
5. **HTTP 429** - Too Many Requests
6. **Rate limiting** - Any error containing rate limiting keywords
7. **Connection timeouts** - Network-related timeouts

## Example Output

```
API Error: 500 Internal Server Error
{"error":"429 Too Many Requests","status":500}

🔄 Rate limiting error detected. Retrying in 10s (attempt 1/3) (Press ESC to cancel)
```

## Troubleshooting

If the plugin doesn't work:

1. Check that it's properly installed:
   ```bash
   python -c "import auto_retry; print('Plugin loaded successfully')"
   ```

2. Verify environment variables:
   ```bash
   echo $AUTO_RETRY_DELAY
   echo $AUTO_RETRY_MAX_RETRIES
   ```

3. Check for conflicts with other retry plugins

## Advanced Configuration

For more advanced retry scenarios, consider using the enhanced network retry plugin which provides:
- Per-error-type retry configuration
- Exponential backoff with jitter
- Infinite retry options
- More detailed logging
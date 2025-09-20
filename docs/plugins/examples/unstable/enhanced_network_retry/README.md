# Enhanced Network Retry Plugin

This plugin enhances AI Coder's network error handling by implementing configurable retry logic for various types of network errors including connection timeouts, DNS failures, and HTTP errors. It provides different retry strategies for different types of errors with comprehensive configuration options.

## Features

- Configurable retry counts for different HTTP error codes
- Configurable retry counts for different connection error types
- Infinite retry for specific errors
- Exponential backoff with jitter
- Detailed logging of retry attempts
- Easy configuration via environment variables
- Support for connection timeouts, DNS failures, and other network issues

## Configuration

Set these environment variables to customize retry behavior:

| Variable | Description | Default |
|----------|-------------|---------|
| `NETWORK_RETRY_500` | Number of retries for 500 errors | 3 |
| `NETWORK_RETRY_502` | Number of retries for 502 errors (-1 = infinite) | -1 |
| `NETWORK_RETRY_503` | Number of retries for 503 errors | 3 |
| `NETWORK_RETRY_504` | Number of retries for 504 errors | 3 |
| `NETWORK_RETRY_TIMEOUT` | Number of retries for timeout errors | 3 |
| `NETWORK_RETRY_DNS` | Number of retries for DNS errors | 3 |
| `NETWORK_RETRY_CONNECT` | Number of retries for connection errors | 3 |
| `NETWORK_RETRY_DEFAULT` | Default retry count for other errors | 3 |
| `NETWORK_RETRY_DELAY` | Initial delay in seconds | 1.0 |
| `NETWORK_RETRY_MAX_DELAY` | Maximum delay in seconds | 60.0 |
| `NETWORK_RETRY_MULTIPLIER` | Backoff multiplier | 2.0 |
| `NETWORK_RETRY_JITTER` | Jitter factor (0.1 = 10%) | 0.1 |

## Examples

To enable infinite retry for 500 errors:
```bash
export NETWORK_RETRY_500=-1
```

To set a longer initial delay:
```bash
export NETWORK_RETRY_DELAY=2.0
```

To disable retries for timeout errors:
```bash
export NETWORK_RETRY_TIMEOUT=0
```

To configure 5 retries for DNS errors:
```bash
export NETWORK_RETRY_DNS=5
```

## Error Types Handled

The plugin can detect and handle various types of network errors:

1. **HTTP Errors**: 500, 502, 503, 504 status codes
2. **Timeout Errors**: Connection timeouts, read timeouts
3. **DNS Errors**: DNS resolution failures, unknown host errors
4. **Connection Errors**: Connection refused, connection reset

## How It Works

The plugin monkey-patches the `_make_api_request` method in `APIHandlerMixin` to intercept network errors and apply retry logic based on the configuration. When a network error occurs, the plugin will:

1. Classify the error into a category (HTTP error, timeout, DNS, connection, etc.)
2. Check if the error type is configured for retry
3. If configured to retry, wait for a calculated delay period
4. Retry the request
5. Continue retrying until success or the maximum retry count is reached
6. For errors configured with -1 retries, it will retry infinitely

The delay between retries uses exponential backoff with jitter to prevent the thundering herd problem.
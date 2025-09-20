# Network Retry Plugin

This plugin enhances AI Coder's network error handling by implementing configurable retry logic for different types of network errors. It can automatically retry failed API requests based on error codes, with different strategies for different types of errors.

## Features

- Configurable retry counts for different HTTP error codes
- Infinite retry for specific errors (like 502 Bad Gateway)
- Exponential backoff with jitter
- Detailed logging of retry attempts
- Easy configuration via environment variables

## Configuration

Set these environment variables to customize retry behavior:

| Variable | Description | Default |
|----------|-------------|---------|
| `NETWORK_RETRY_500` | Number of retries for 500 errors | 3 |
| `NETWORK_RETRY_502` | Number of retries for 502 errors (-1 = infinite) | -1 |
| `NETWORK_RETRY_503` | Number of retries for 503 errors | 3 |
| `NETWORK_RETRY_504` | Number of retries for 504 errors | 3 |
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

To disable retries for 503 errors:
```bash
export NETWORK_RETRY_503=0
```

## How It Works

The plugin monkey-patches the `_make_api_request` method in `APIHandlerMixin` to intercept network errors and apply retry logic based on the configuration. When a network error occurs, the plugin will:

1. Check if the error code is configured for retry
2. If configured to retry, wait for a calculated delay period
3. Retry the request
4. Continue retrying until success or the maximum retry count is reached
5. For errors configured with -1 retries, it will retry infinitely

The delay between retries uses exponential backoff with jitter to prevent the thundering herd problem.
"""
Enhanced Network Retry Plugin

This plugin enhances AI Coder's network error handling by implementing configurable
retry logic for various types of network errors including connection timeouts,
DNS failures, and HTTP errors. It provides different retry strategies for different
types of errors with comprehensive configuration options.

Features:
- Configurable retry counts for different HTTP error codes
- Configurable retry counts for different connection error types
- Infinite retry for specific errors
- Exponential backoff with jitter
- Detailed logging of retry attempts
- Easy configuration via environment variables
- Support for connection timeouts, DNS failures, and other network issues

Configuration:
Set these environment variables to customize retry behavior:
- NETWORK_RETRY_500=N     # Number of retries for 500 errors (default: 3)
- NETWORK_RETRY_502=-1    # Number of retries for 502 errors (-1 = infinite)
- NETWORK_RETRY_503=5     # Number of retries for 503 errors (default: 3)
- NETWORK_RETRY_504=3     # Number of retries for 504 errors (default: 3)
- NETWORK_RETRY_TIMEOUT=3 # Number of retries for timeout errors (default: 3)
- NETWORK_RETRY_DNS=3     # Number of retries for DNS errors (default: 3)
- NETWORK_RETRY_CONNECT=3 # Number of retries for connection errors (default: 3)
- NETWORK_RETRY_DEFAULT=3 # Default retry count for other errors (default: 3)
- NETWORK_RETRY_DELAY=1   # Initial delay in seconds (default: 1.0)
- NETWORK_RETRY_MAX_DELAY=60  # Maximum delay in seconds (default: 60.0)
"""

import os
import time
import random
import functools
from typing import Dict

# Default configuration
DEFAULT_RETRY_CONFIG = {
    500: 3,  # Internal Server Error
    502: -1,  # Bad Gateway (infinite retry)
    503: 3,  # Service Unavailable
    504: 3,  # Gateway Timeout
    "timeout": 3,  # Connection timeout
    "dns": 3,  # DNS resolution errors
    "connect": 3,  # Connection errors
    "default": 3,
}

DEFAULT_DELAY_CONFIG = {"initial": 1.0, "max": 60.0, "multiplier": 2.0, "jitter": 0.1}

# Error patterns for different types of network errors
ERROR_PATTERNS = {
    "timeout": [
        "timeout",
        "timed out",
        "time out",
        "connection timed out",
        "read timed out",
        "connect timed out",
    ],
    "dns": [
        "name or service not known",
        "nodename nor servname provided",
        "dns resolution failed",
        "cannot resolve",
        "unknown host",
    ],
    "connect": [
        "connection refused",
        "connection reset",
        "connection aborted",
        "connection failed",
        "unable to connect",
        "could not connect",
    ],
}


def get_retry_config() -> Dict[str, int]:
    """Get retry configuration from environment variables."""
    config = DEFAULT_RETRY_CONFIG.copy()

    # Override with environment variables
    for key, default_value in DEFAULT_RETRY_CONFIG.items():
        env_key = (
            f"NETWORK_RETRY_{key}"
            if isinstance(key, int)
            else f"NETWORK_RETRY_{key.upper()}"
        )
        env_value = os.environ.get(env_key)
        if env_value is not None:
            try:
                config[key] = int(env_value)
            except ValueError:
                print(f"⚠️  Invalid value for {env_key}, using default: {default_value}")

    return config


def get_delay_config() -> Dict[str, float]:
    """Get delay configuration from environment variables."""
    config = DEFAULT_DELAY_CONFIG.copy()

    # Override with environment variables
    env_mappings = {
        "NETWORK_RETRY_DELAY": "initial",
        "NETWORK_RETRY_MAX_DELAY": "max",
        "NETWORK_RETRY_MULTIPLIER": "multiplier",
        "NETWORK_RETRY_JITTER": "jitter",
    }

    for env_key, config_key in env_mappings.items():
        env_value = os.environ.get(env_key)
        if env_value is not None:
            try:
                config[config_key] = float(env_value)
            except ValueError:
                print(
                    f"⚠️  Invalid value for {env_key}, using default: {config[config_key]}"
                )

    return config


def apply_jitter(delay: float, jitter: float) -> float:
    """Apply jitter to delay to prevent thundering herd problem."""
    jitter_amount = delay * jitter
    return delay + random.uniform(-jitter_amount, jitter_amount)


def classify_error(error: Exception) -> str:
    """Classify an error into a category for retry logic."""
    error_str = str(error).lower()

    # Check for HTTP error codes first
    if hasattr(error, "code"):
        return str(error.code)

    # Check for specific error patterns
    for error_type, patterns in ERROR_PATTERNS.items():
        for pattern in patterns:
            if pattern in error_str:
                return error_type

    # Check for HTTP status codes in the error message
    http_codes = [500, 502, 503, 504]
    for code in http_codes:
        if str(code) in error_str:
            return str(code)

    return "default"


def should_retry(error_type: str, attempt: int, retry_config: Dict[str, int]) -> bool:
    """Determine if we should retry based on error type and attempt count."""
    # Check specific error type config
    if error_type in retry_config:
        max_retries = retry_config[error_type]
        # -1 means infinite retry
        if max_retries == -1:
            return True
        return attempt < max_retries

    # Check default config
    max_retries = retry_config.get("default", 3)
    if max_retries == -1:
        return True
    return attempt < max_retries


def calculate_delay(attempt: int, delay_config: Dict[str, float]) -> float:
    """Calculate delay with exponential backoff."""
    initial = delay_config["initial"]
    max_delay = delay_config["max"]
    multiplier = delay_config["multiplier"]
    jitter = delay_config["jitter"]

    delay = min(initial * (multiplier**attempt), max_delay)
    return apply_jitter(delay, jitter)


def patched_make_api_request(original_method):
    """Patch for _make_api_request to add retry logic."""

    @functools.wraps(original_method)
    def wrapper(self, messages, disable_streaming_mode=False, disable_tools=False):
        # Get configuration
        retry_config = get_retry_config()
        delay_config = get_delay_config()

        attempt = 0
        # last_error = None

        while True:
            try:
                # Try the original API request
                return original_method(
                    self, messages, disable_streaming_mode, disable_tools
                )
            except Exception as e:
                # last_error = e

                # Classify the error
                error_type = classify_error(e)

                # Determine if we should retry
                if should_retry(error_type, attempt, retry_config):
                    attempt += 1

                    # Calculate delay
                    delay = calculate_delay(attempt - 1, delay_config)

                    # Log retry attempt
                    error_name = (
                        f"{error_type.upper()} Error"
                        if not error_type.isdigit()
                        else f"HTTP {error_type}"
                    )
                    max_retries = retry_config.get(
                        error_type, retry_config.get("default", 3)
                    )
                    retry_info = (
                        "infinite retries"
                        if max_retries == -1
                        else f"{max_retries} max retries"
                    )

                    print(
                        f"🔄 {error_name} - Retrying in {delay:.1f}s (attempt {attempt}, {retry_info}) (Press ESC to cancel)"
                    )
                    print(f"   Error details: {str(e)[:100]}...")

                    # Try to import cancellable_sleep, fall back to time.sleep if not available
                    try:
                        from aicoder.utils import cancellable_sleep

                        # Use cancellable sleep to allow user to cancel retries
                        if not cancellable_sleep(
                            delay, getattr(self, "animator", None)
                        ):
                            print("\n Retry cancelled by user (ESC).")
                            return None
                    except ImportError:
                        # Fall back to regular sleep if cancellable_sleep is not available
                        time.sleep(delay)

                    continue
                else:
                    # Don't retry - re-raise the exception
                    raise

    return wrapper


def install_enhanced_network_retry_plugin():
    """Install the enhanced network retry plugin by patching the API handler."""
    try:
        # Import the API handler class
        from aicoder.api_handler import APIHandlerMixin

        # Check if we've already patched
        if hasattr(
            APIHandlerMixin._make_api_request, "_enhanced_network_retry_patched"
        ):
            print("✅ Enhanced network retry plugin already installed")
            return True

        # Store reference to original method
        original_method = APIHandlerMixin._make_api_request

        # Create patched method
        patched_method = patched_make_api_request(original_method)
        patched_method._enhanced_network_retry_patched = True
        patched_method._original_method = original_method

        # Apply the patch
        APIHandlerMixin._make_api_request = patched_method

        print("✅ Enhanced network retry plugin installed successfully")
        print("   Features:")
        print("   - Automatic retry for HTTP 500, 502, 503, 504 errors")
        print("   - Automatic retry for connection timeouts")
        print("   - Automatic retry for DNS resolution failures")
        print("   - Automatic retry for connection errors")
        print("   - Infinite retry for 502 Bad Gateway errors")
        print("   - Exponential backoff with jitter")
        print("   - Configurable retry counts per error type")
        print("   - Detailed retry logging")
        print("   - ESC key support to cancel retries")
        print()
        print("   Configuration environment variables:")
        print("   - NETWORK_RETRY_500=N        # Retries for 500 errors (default: 3)")
        print(
            "   - NETWORK_RETRY_502=-1       # Retries for 502 errors (-1 = infinite)"
        )
        print("   - NETWORK_RETRY_503=N        # Retries for 503 errors (default: 3)")
        print("   - NETWORK_RETRY_504=N        # Retries for 504 errors (default: 3)")
        print(
            "   - NETWORK_RETRY_TIMEOUT=N    # Retries for timeout errors (default: 3)"
        )
        print("   - NETWORK_RETRY_DNS=N        # Retries for DNS errors (default: 3)")
        print(
            "   - NETWORK_RETRY_CONNECT=N    # Retries for connection errors (default: 3)"
        )
        print("   - NETWORK_RETRY_DEFAULT=N    # Default retry count (default: 3)")
        print(
            "   - NETWORK_RETRY_DELAY=S      # Initial delay in seconds (default: 1.0)"
        )
        print("   - NETWORK_RETRY_MAX_DELAY=S  # Max delay in seconds (default: 60.0)")

        return True

    except ImportError as e:
        # This is expected when running outside of AI Coder
        print(
            f"ℹ️  Enhanced network retry plugin loaded (API handler not available: {e})"
        )
        return True
    except Exception as e:
        print(f"❌ Failed to install enhanced network retry plugin: {e}")
        return False


# Install the plugin when loaded
if install_enhanced_network_retry_plugin():
    print("✅ Enhanced network retry plugin loaded")
else:
    print("❌ Enhanced network retry plugin failed to load")
